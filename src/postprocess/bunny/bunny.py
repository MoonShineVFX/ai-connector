from PIL.Image import Image
import requests
from io import BytesIO
from defines import Settings
from loguru import logger


def upload_bunny(image: Image, image_id: str, fmt: str = "WEBP"):
    is_lossless = fmt == "WEBP_LOSSLESS"
    if fmt == "WEBP_LOSSLESS":
        fmt = "WEBP"

    filename = f"{image_id}.{fmt.lower()}"

    byte_io = BytesIO()
    save_options = {
        "format": fmt,
        "lossless": is_lossless,
        "quality": 90,
        "optimize": True,
    }

    if fmt == "GIF":
        save_options["save_all"] = True

    if fmt == "JPEG":
        image = image.convert("RGB")

    image.save(byte_io, **save_options)
    byte_io.seek(0)

    logger.debug(f"Uploading image to BunnyCDN: {filename}")
    requests.put(
        f"{Settings.BUNNY_UPLOAD_URL}/{filename}",
        data=byte_io.read(),
        headers={
            "AccessKey": Settings.BUNNY_API_KEY,
            "content-type": "application/octet-stream",
        },
    )

    return f"{Settings.BUNNY_PUBLIC_URL}/{filename}"
