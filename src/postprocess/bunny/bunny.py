from PIL.Image import Image
import requests
from io import BytesIO
from defines import Settings
from loguru import logger
from typing import List


def upload_bunny(
    images: List[Image], image_id: str, fmt: str = "WEBP", duration: int = 125
):
    # Check lossless
    is_lossless = fmt == "WEBP_LOSSLESS"
    if fmt == "WEBP_LOSSLESS":
        fmt = "WEBP"

    # Check sequence
    is_sequence = len(images) > 1
    if is_sequence:
        fmt = "GIF" if fmt != "WEBP" else "WEBP"

    filename = f"{image_id}.{fmt.lower()}"

    byte_io = BytesIO()
    save_options = {
        "format": fmt,
        "lossless": is_lossless,
        "quality": 90,
        "optimize": True,
    }

    # Save all frames if sequence
    if is_sequence:
        save_options.update(
            {
                "save_all": True,
                "append_images": images[1:],
                "duration": duration,
                "loop": 0,
            }
        )
        if fmt == "WEBP":
            save_options.update(
                {
                    "minimize_size": True,
                }
            )

    # Convert to RGB if JPEG
    if fmt == "JPEG":
        images[0] = images[0].convert("RGB")

    images[0].save(byte_io, **save_options)
    byte_io.seek(0)

    logger.debug(f"Uploading image to BunnyCDN: {filename}")
    response = requests.put(
        f"{Settings.BUNNY_UPLOAD_URL}/{filename}",
        data=byte_io.read(),
        headers={
            "AccessKey": Settings.BUNNY_API_KEY,
            "content-type": "application/octet-stream",
        },
        # 5 minutes
        timeout=300,
    )
    response.raise_for_status()

    return f"{Settings.BUNNY_PUBLIC_URL}/{filename}"
