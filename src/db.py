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
from datetime import datetime, timezone
from elastic import elastic_client


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

        self.__worker = Settings.WORKER_NAME.strip().replace(" ", "_").lower()
        logger.debug("Register worker name: " + self.__worker)

        # Keys
        self.__command_key = f"command_{self.__worker}"
        self.__worker_key = f"worker_{self.__worker}"

        # Queue
        self.__queue_worker_key = f"queue_{self.__worker}"
        self.__queue_key_list = []
        self.update_queue_key_list()
        logger.debug(f"Queue keys: {self.__queue_key_list}")

        # Register worker and clean previous commands
        self.__db.delete(self.__command_key)
        self.update_worker_status("INITIAL")

    def update_queue_key_list(self):
        try:
            # Load queue config
            queue_config_str = self.__db.get("queue:config")

            if queue_config_str is None:
                raise ValueError("Queue config not found")

            queue_config = json.loads(str(queue_config_str))
            # [
            #     {"name": "gif", "workers": ["mscgp32", "mscgp33"]},
            #     {"name": "_global", "workers": ["mscgp46", "mscgp47"]},
            # ]

            # Filter and Sort by order
            group_queue_keys = [
                "queue"
                if queue_info["name"] == "_global"
                else f"queue_group_{queue_info['name']}"
                for queue_info in queue_config
                if self.__worker in queue_info["workers"]
            ]

            self.__queue_key_list = [self.__queue_worker_key]
            self.__queue_key_list += group_queue_keys
            logger.debug(f"Queue keys: {self.__queue_key_list}")

        except Exception as e:
            logger.error(
                f"Failed to load queue config, use default queue: {e}"
            )
            logger.error(traceback.format_exc())
            self.__queue_key_list = [self.__queue_worker_key, "queue"]
            return

    def update_worker_status(self, status: WorkerStatus):
        self.__db.setex(
            self.__worker_key,
            self.WORKER_TIMEOUT,
            json.dumps(
                {
                    "status": status,
                    "version": Settings.WORKER_VERSION,
                    "queue_list": self.__queue_key_list,
                }
            ),
        )

    def wait_signal(self) -> tuple[SignalType, str | CommandType, str] | None:
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
            return "COMMAND", payload, key

        if key == "queue" or key.startswith("queue_"):
            return "JOB", payload, key

        raise Exception(f"Unknown signal: {key} {payload}")

    def get_job(self, job_id: str, queue_key: str) -> Job | None:
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

        # Convert created_at from timestamp
        if job_dict.get("created_at"):
            job_dict["created_at"] = datetime.fromisoformat(
                job_dict["created_at"]
            )
        else:
            job_dict["created_at"] = datetime.now(timezone.utc)

        # Create job
        try:
            job = Job(
                on_close=self.end_job,
                _id=job_id,
                _type=job_dict["type"],
                payload=job_dict["payload"],
                create_time=job_dict["created_at"],
                queue_key=queue_key,
                image_format=job_dict["format"],
                process_list=job_dict.get("postprocess", []),
                status=job_dict["status"],
                webhook=job_dict.get("webhook", None),
                tag=job_dict.get("tag", None),
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

        now = datetime.now(timezone.utc)

        # Update job
        self.__db.hset(
            job.id,
            "status",
            job.status,
            mapping={
                "updated_at": now.isoformat(),
                "result": result,
            },
        )

        # Log to elastic
        self.log_job(job, now)

    def log_job(self, job: Job, timestamp: datetime):
        # move prompt from payload
        prompts = {}
        if "prompt" in job.payload_raw:
            prompts["prompt"] = job.payload_raw["prompt"]
            del job.payload_raw["prompt"]
        if "negative_prompt" in job.payload_raw:
            prompts["negative_prompt"] = job.payload_raw["negative_prompt"]
            del job.payload_raw["negative_prompt"]

        # remove prompts from result
        if "info" in job.result:
            job.result["info"].pop("prompt", None)
            job.result["info"].pop("negative_prompt", None)

            # remove infotexts
            job.result["info"].pop("infotexts", None)

        try:
            elastic_client.index(
                id=job.id,
                index=f"{'dev_' if Settings.DEV else ''}"
                + f"worker_{Settings.WORKER_NAME.lower()}"
                + f"_{timestamp.strftime('%Y%m%d')}",
                document={
                    "@timestamp": timestamp,
                    "worker": Settings.WORKER_NAME,
                    "status": job.status,
                    "type": job.type,
                    "format": job.image_format,
                    "payload": job.payload_raw,
                    "tag": job.tag,
                    "postprocess": [
                        process.type for process in job.process_list
                    ],
                    **job.result,
                    **prompts,
                },
            )
        except Exception as e:
            logger.error(f"Failed to log to elastic: {job.id}")
            logger.error(traceback.format_exc())

    def flush_queue(self):
        self.__db.delete(self.__queue_worker_key)

    def close(self):
        self.__db.delete(self.__worker_key)
        self.__db.delete(self.__command_key)
        self.flush_queue()
        self.__db.close()
