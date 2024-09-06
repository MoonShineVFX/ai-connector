import meilisearch
from pydantic import BaseModel, HttpUrl
from typing import List
from datetime import datetime

from job import Job
from loguru import logger
from defines import Settings


# Pydantic models
class InfoModel(BaseModel):
    prompt: str
    negative_prompt: str
    sd_model_name: str


class ResultModel(BaseModel):
    info: InfoModel
    images: List[HttpUrl]


class MeiliJobInputSchema(BaseModel):
    id: str
    created_at: datetime
    result: ResultModel


# MeiliSearch client
client = meilisearch.Client(
    Settings.MEILISEARCH_HOST,
    Settings.MEILISEARCH_MASTER_KEY,
)
index = client.index(
    "ai-generations" if not Settings.DEV else "ai-generations-dev"
)


class Meili:
    @staticmethod
    def add(job: Job):
        if job.status != "DONE" or job.type not in ["TXT2IMG", "IMG2IMG"]:
            return

        # Validate job
        try:
            input = MeiliJobInputSchema(
                id=job.id, created_at=job.create_time, result=job.result
            )
            if len(input.result.images) == 0:
                return
            index.add_documents(
                [
                    {
                        "id": input.id,
                        "created_at": input.created_at,
                        "prompt": input.result.info.prompt,
                        "negative_prompt": input.result.info.negative_prompt,
                        "model": input.result.info.sd_model_name,
                        "image": input.result.images[0],
                        "created_at_timestamp": round(
                            input.created_at.timestamp()
                        ),
                    }
                ]
            )

        except Exception as e:
            logger.warning(f"Failed to validate meili job: {job.id}")
            logger.warning(e)
            return
