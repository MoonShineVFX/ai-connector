from PIL.Image import Image
from io import BytesIO
from defines import Settings
from loguru import logger
from typing import List
import boto3


r2_client = boto3.client(
    service_name="s3",
    endpoint_url=Settings.R2_ENDPOINT_URL,
    region_name="apac",
)


def upload_r2(
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

    filename = f"{'dev_' if Settings.DEV else ''}{image_id}.{fmt.lower()}"

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

    logger.debug(f"Uploading image to R2: {filename}")
    r2_client.upload_fileobj(
        byte_io,
        Settings.R2_BUCKET_NAME,
        filename,
    )

    return f"{Settings.R2_PUBLIC_URL}/{filename}"
