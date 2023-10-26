import os
import platform
from dataclasses import dataclass
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

WorkerStatus = Literal[
    "INITIAL", "STANDBY", "RESTART", "PROCESSING", "DISCONNECTED"
]

SignalType = Literal["COMMAND", "JOB"]

CommandType = Literal["STOP", "RESTART_WEBUI", "FLUSH_QUEUE"]

JobType = Literal[
    "TXT2IMG", "IMG2IMG", "EXTRA", "INTERROGATE", "CONTROLNET_DETECT"
]
JobStatus = Literal["PENDING", "PROCESSING", "FAILED", "DONE"]
ImageFormat = Literal["JPEG", "PNG", "WEBP", "WEBP_LOSSLESS", "GIF"]


@dataclass
class PostProcess:
    type: Literal[
        "ADD_TEXT",
        "WATERMARK",
        "LETTERBOX",
        "UPLOAD",
        "NSFW_DETECTION",
        "BLURHASH",
    ]
    args: dict | None = None


@dataclass
class Settings:
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
    WORKER_NAME = os.environ.get("WORKER_NAME", platform.node())
    WORKER_INFO = (
        os.environ.get("WORKER_NAME", platform.node())
        + " | v:"
        + os.environ.get("VERSION", "unknown")
    )
    A1111_PORT = os.environ.get("A1111_PORT", 7860)
    QUEUE_GROUP = os.environ.get("QUEUE_GROUP", None)
    EXCLUDE_GLOBAL_QUEUE = (
        os.environ.get("EXCLUDE_GLOBAL_QUEUE", "false").lower() == "true"
    )
    ELASTIC_CLOUD_ID = os.environ["ELASTIC_CLOUD_ID"]
    ELASTIC_API_KEY = os.environ["ELASTIC_API_KEY"]
    R2_ENDPOINT_URL = os.environ["R2_ENDPOINT_URL"]
    R2_BUCKET_NAME = os.environ["R2_BUCKET_NAME"]
    R2_PUBLIC_URL = os.environ["R2_PUBLIC_URL"]
    AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
    DEV = os.environ.get("DEV", "false").lower() == "true"

    @staticmethod
    def get_queue_groups():
        if Settings.QUEUE_GROUP is None:
            return []
        return Settings.QUEUE_GROUP.split(" ")


@dataclass
class Webhook:
    url: str
    token: str | None = None
