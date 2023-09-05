import redis

from loguru import logger
import json
from settings import Settings
from defines import Job, PostProcess


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

    def get_job(self) -> tuple[str, Job] | None:
        blpop_tuple = self.__db.blpop([self.__key])
        job_id: str = blpop_tuple[1]

        job_dict = self.__db.hgetall(job_id)
        if not job_dict:
            logger.error(f"Job not found: {job_id}")
            return None

        self.__db.hset(
            job_id,
            mapping={"status": "PROCESSING", "worker": Settings.WORKER_NAME},
        )

        # Convert postprocess to dict
        if job_dict.get("postprocess"):
            job_dict["postprocess"] = [
                PostProcess(**process)
                for process in json.loads(job_dict["postprocess"])
            ]

        # Convert payload to dict
        job_dict["payload"] = json.loads(job_dict["payload"])

        job = Job(**job_dict)
        return job_id, job

    def close_job(self, job_id: str, result=None, is_failed=False):
        if result is None:
            result = {}

        self.__db.hset(
            job_id,
            "status",
            "DONE" if not is_failed else "FAILED",
            mapping={"result": json.dumps(result)},
        )
