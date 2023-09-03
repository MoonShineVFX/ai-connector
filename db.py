import redis
from dataclasses import dataclass
from typing import Literal
from loguru import logger
import json
import os


JobType = Literal["TXT2IMG", "IMG2IMG", "EXTRA"]
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
WORKER_NAME = os.environ.get("WORKER_NAME", "worker")


@dataclass
class Job:
    type: JobType
    payload: dict
    model: str | None = None
    status: Literal["PENDING", "PROCESSING", "FAILED", "DONE"] = "PENDING"


class RedisDatabase(object):
    def __init__(self):
        self.__db = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.__key = "queue"

    def get_job(self) -> tuple[str, Job] | None:
        blpop_tuple = self.__db.blpop([self.__key])
        job_id: str = blpop_tuple[1]

        job_dict = self.__db.hgetall(job_id)
        if not job_dict:
            logger.error(f"Job not found: {job_id}")
            return None

        self.__db.hset(
            job_id, mapping={"status": "PROCESSING", "worker": WORKER_NAME}
        )

        job_dict["payload"] = json.loads(job_dict["payload"])
        job = Job(**job_dict)
        return job_id, job

    def done_job(self, job_id: str, data=None):
        if data is None:
            data = {}
        self.__db.hset(
            job_id, "status", "DONE", mapping={"result": json.dumps(data)}
        )

    def fail_job(self, job_id: str, message: str):
        self.__db.hset(job_id, "status", "FAILED", mapping={"error": message})
