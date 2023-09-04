from PIL.Image import Image
import requests
from typing import Callable
from cuid2 import cuid_wrapper
from io import BytesIO
from loguru import logger
from settings import Settings


cuid_generator: Callable[[], str] = cuid_wrapper()


def upload_bunny(images: [Image], fmt: str = "WEBP"):
    logger.info("Uploading image...")
    image_urls = []

    is_lossless = fmt == "WEBP_LOSSLESS"
    if fmt == "WEBP_LOSSLESS":
        fmt = "WEBP"

    for image in images:
        filename = f"{cuid_generator()}.{fmt.lower()}"

        byte_io = BytesIO()
        save_options = {
            "format": fmt,
            "lossless": is_lossless,
        }
        image.save(byte_io, **save_options)
        byte_io.seek(0)

        requests.put(
            f"{Settings.BUNNY_UPLOAD_URL}/{filename}",
            data=byte_io.read(),
            headers={
                "AccessKey": Settings.BUNNY_API_KEY,
                "content-type": "application/octet-stream",
            },
        )

        image_urls.append(f"{Settings.BUNNY_PUBLIC_URL}/{filename}")

    return image_urls
