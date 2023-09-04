from dotenv import load_dotenv
import os
from dataclasses import dataclass
import platform


load_dotenv()


@dataclass
class Settings:
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
    WORKER_NAME = os.environ.get("WORKER_NAME", platform.node())
    BUNNY_API_KEY = os.environ.get("BUNNY_API_KEY", "")
    BUNNY_UPLOAD_URL = os.environ.get("BUNNY_UPLOAD_URL", "")
    BUNNY_PUBLIC_URL = os.environ.get("BUNNY_PUBLIC_URL", "")
