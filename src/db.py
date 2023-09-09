import redis

from loguru import logger
import json
from defines import PostProcess, Settings, Webhook
from job import Job
import traceback


class RedisDatabase(object):
    def __init__(self):
        logger.info(
            f"Connecting to Redis: {Settings.REDIS_HOST}:{Settings.REDIS_PORT}"
        )
        self.__db = redis.Redis(
            host=Settings.REDIS_HOST,
            port=Settings.REDIS_PORT,
            decode_responses=True,
        )
        self.__key = "queue"

    def get_job(self) -> Job | None:
        blpop_tuple = self.__db.blpop([self.__key])
        job_id: str = blpop_tuple[1]

        job_dict = self.__db.hgetall(job_id)
        if not job_dict:
            logger.error(f"Job not found: {job_id}")
            return None

        self.__db.hset(
            job_id,
            mapping={
                "status": "PROCESSING",
                "worker": Settings.WORKER_NAME,
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
                job.id,
                "status",
                "FAILED",
                mapping={"result": json.dumps({"error": str(e)})},
            )
            return None

    def end_job(self, job: Job):
        self.__db.hset(
            job.id,
            "status",
            job.status,
            mapping={"result": json.dumps(job.result)},
        )
