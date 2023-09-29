import os
import platform
from dataclasses import dataclass
from typing import Literal
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


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
    WORKER_NAME = (
        os.environ.get("WORKER_NAME", platform.node())
        + " | v:"
        + os.environ.get("VERSION", "unknown")
    )
    BUNNY_API_KEY = os.environ.get("BUNNY_API_KEY", "")
    BUNNY_UPLOAD_URL = os.environ.get("BUNNY_UPLOAD_URL", "")
    BUNNY_PUBLIC_URL = os.environ.get("BUNNY_PUBLIC_URL", "")
    A1111_PORT = os.environ.get("A1111_PORT", 7860)
    WEBUI_OUTPUTS_DIR = Path(os.environ["WEBUI_OUTPUTS_DIR"])

    @staticmethod
    def get_animate_diff_path(job_type: JobType):
        if job_type == "TXT2IMG":
            return (
                Settings.WEBUI_OUTPUTS_DIR / "txt2img-images" / "AnimateDiff"
            )
        elif job_type == "IMG2IMG":
            return (
                Settings.WEBUI_OUTPUTS_DIR / "img2img-images" / "AnimateDiff"
            )
        return None


@dataclass
class Webhook:
    url: str
    token: str | None = None
