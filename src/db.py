import redis

from loguru import logger
import json
from defines import (
    PostProcess,
    Settings,
    Webhook,
    SignalType,
    CommandType,
    WorkerStatus,
)
from job import Job
import traceback


class RedisDatabase(object):
    WORKER_TIMEOUT = 60 * 30  # 30 minutes

    def __init__(self):
        logger.info(
            f"Connecting to Redis: {Settings.REDIS_HOST}:{Settings.REDIS_PORT}"
        )
        self.__db = redis.Redis(
            host=Settings.REDIS_HOST,
            port=Settings.REDIS_PORT,
            decode_responses=True,
        )

        self.__worker = worker_name_normalized = (
            Settings.WORKER_NAME.strip().replace(" ", "_").lower()
        )
        logger.debug("Register worker name: " + self.__worker)

        # Keys
        self.__command_key = f"command_{self.__worker}"
        self.__worker_key = f"worker_{self.__worker}"

        # Queue
        self.__global_queue_key = "queue"
        self.__queue_key = f"queue_{self.__worker}"
        self.__queue_group_keys = [
            f"queue_group_{group.strip().replace(' ', '_').lower()}"
            for group in Settings.get_queue_groups()
        ]

        self.__queue_key_list = []
        self.__queue_key_list.append(self.__queue_key)
        self.__queue_key_list.extend(self.__queue_group_keys)
        if not Settings.EXCLUDE_GLOBAL_QUEUE:
            self.__queue_key_list.append(self.__global_queue_key)
        logger.debug(f"Queue keys: {self.__queue_key_list}")

        # Register worker and clean previous commands
        self.__db.delete(self.__command_key)
        self.update_worker_status("INITIAL")

    def update_worker_status(self, status: WorkerStatus):
        self.__db.setex(self.__worker_key, self.WORKER_TIMEOUT, status)

    def wait_signal(self) -> tuple[SignalType, str | CommandType] | None:
        """
        Wait for a signal from redis and return the payload.

        - Watch command first, then queue.
        - Worker key first, then global key.
        """
        self.update_worker_status("STANDBY")
        blopo_result = self.__db.blpop(
            [
                self.__command_key,
                *self.__queue_key_list,
            ],
            timeout=5,
        )
        if blopo_result is None:
            return None

        key, payload = blopo_result

        if key == self.__command_key:
            return "COMMAND", payload

        if key == "queue" or key.startswith("queue_"):
            return "JOB", payload

        raise Exception(f"Unknown signal: {key} {payload}")

    def get_job(self, job_id: str) -> Job | None:
        job_dict = self.__db.hgetall(job_id)
        if not job_dict:
            logger.error(f"Job not found: {job_id}")
            return None

        self.__db.hset(
            job_id,
            mapping={
                "status": "PROCESSING",
                "worker": Settings.WORKER_INFO,
            },
        )

        # Convert postprocess from dict
        if job_dict.get("postprocess"):
            job_dict["postprocess"] = [
                PostProcess(**process)
                for process in json.loads(job_dict["postprocess"])
            ]

        # Convert payload from dict
        job_dict["payload"] = json.loads(job_dict["payload"])

        # Convert webhook from dict
        if job_dict.get("webhook"):
            job_dict["webhook"] = Webhook(**json.loads(job_dict["webhook"]))

        # Create job
        try:
            job = Job(
                on_close=self.end_job,
                _id=job_id,
                _type=job_dict["type"],
                payload=job_dict["payload"],
                image_format=job_dict["format"],
                process_list=job_dict.get("postprocess", []),
                status=job_dict["status"],
                webhook=job_dict.get("webhook", None),
            )
            return job
        except Exception as e:
            logger.error(f"Failed to create job: {job_id}")
            logger.error(traceback.format_exc())
            self.__db.hset(
                job_id,
                "status",
                "FAILED",
                mapping={"result": json.dumps({"error": str(e)})},
            )
            return None

    def end_job(self, job: Job):
        try:
            result = json.dumps(job.result)
        except Exception as e:
            logger.error(f"Failed to dump result: {job.id}")
            logger.error(traceback.format_exc())
            result = json.dumps({"error": str(e)})

        self.__db.hset(
            job.id,
            "status",
            job.status,
            mapping={"result": result},
        )

    def flush_queue(self):
        self.__db.delete(self.__queue_key)

    def close(self):
        self.__db.delete(self.__worker_key)
        self.__db.delete(self.__command_key)
        self.flush_queue()
        self.__db.close()
