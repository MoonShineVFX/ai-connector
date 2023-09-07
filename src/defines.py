import os
import platform
from dataclasses import dataclass
from typing import Literal
from dotenv import load_dotenv

load_dotenv()


JobType = Literal["TXT2IMG", "IMG2IMG", "EXTRA"]
JobStatus = Literal["PENDING", "PROCESSING", "FAILED", "DONE"]
ImageFormat = Literal["JPEG", "PNG", "WEBP", "WEBP_LOSSLESS"]


@dataclass
class PostProcess:
    type: Literal["ADD_TEXT", "WATERMARK", "LETTERBOX", "UPLOAD"]
    args: dict | None = None


@dataclass
class Settings:
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
    WORKER_NAME = os.environ.get("WORKER_NAME", platform.node())
    BUNNY_API_KEY = os.environ.get("BUNNY_API_KEY", "")
    BUNNY_UPLOAD_URL = os.environ.get("BUNNY_UPLOAD_URL", "")
    BUNNY_PUBLIC_URL = os.environ.get("BUNNY_PUBLIC_URL", "")
    A1111_PORT = os.environ.get("A1111_PORT", 7860)
    VERSION = os.environ.get("VERSION", "unknown")


@dataclass
class Webhook:
    url: str
    token: str | None = None
