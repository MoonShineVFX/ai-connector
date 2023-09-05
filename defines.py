from dataclasses import dataclass
from typing import Literal, List


JobType = Literal["TXT2IMG", "IMG2IMG", "EXTRA"]


@dataclass
class PostProcess:
    type: Literal[
        "ADD_TEXT",
        "WATERMARK",
        "LETTERBOX",
    ]
    args: dict | None = None


@dataclass
class Job:
    type: JobType
    payload: dict
    format: Literal["JPEG", "PNG", "WEBP", "WEBP_LOSSLESS"] = "WEBP"
    postprocess: List[PostProcess] | None = None
    status: Literal["PENDING", "PROCESSING", "FAILED", "DONE"] = "PENDING"
    webhook: str | None = None
