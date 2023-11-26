from PIL.Image import Image, Resampling
from io import BytesIO
from defines import Settings
from loguru import logger
from typing import List
import boto3
import imageio.v3 as imageio
import numpy as np
from pathlib import Path


r2_client = boto3.client(
    service_name="s3",
    endpoint_url=Settings.R2_ENDPOINT_URL,
    region_name="apac",
)


def upload_r2(
    images: List[Image],
    image_id: str,
    fmt: str = "WEBP",
    duration: int = 125,
    resize: int | None = None,
    fps: int = 8,
) -> tuple[str, int]:
    # Check lossless
    is_lossless = fmt == "WEBP_LOSSLESS"
    if fmt == "WEBP_LOSSLESS":
        fmt = "WEBP"

    # Check sequence
    is_sequence = len(images) > 1
    if is_sequence:
        # Default to GIF if not specified, for moonshot
        fmt = "GIF" if fmt not in ["WEBP", "MP4"] else fmt

    filename = f"{'dev/' if Settings.DEV else ''}{image_id}.{fmt.lower()}"

    bytes_io = BytesIO()
    save_options = {
        "format": fmt,
        "lossless": is_lossless,
        "quality": 90,
        "optimize": True,
    }

    # Resize if specified
    if resize is not None:
        for image in images:
            image.thumbnail((resize, 4096), Resampling.LANCZOS)

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

    # Convert to RGB if JPEG
    if fmt == "JPEG":
        images[0] = images[0].convert("RGB")

    # Pillow save
    if fmt != "MP4":
        images[0].save(bytes_io, **save_options)
    else:
        # imageio save
        imageio.imwrite(
            bytes_io,
            [np.array(image) for image in images],
            format_hint=".mp4",
            plugin="pyav",
            fps=fps,
            codec="h264",
            out_pixel_format="yuv420p",
        )

    bytes_io.seek(0)
    size = bytes_io.getbuffer().nbytes

    # Upload to R2
    logger.debug(
        f"Uploading resource to R2: {filename} ({size / 1024 / 1024:.2f}MB)"
    )
    r2_client.upload_fileobj(
        bytes_io,
        Settings.R2_BUCKET_NAME,
        filename,
    )

    # Save file if dev
    if Settings.DEV:
        dev_path = Path("dev")
        dev_path.mkdir(exist_ok=True)

        save_file = dev_path / f"{image_id}.{fmt.lower()}"

        if fmt != "MP4":
            with open(save_file, "wb") as f:
                images[0].save(f, **save_options)
        else:
            imageio.imwrite(
                save_file,
                [np.array(image) for image in images],
                format_hint=".mp4",
                plugin="pyav",
                fps=fps,
                codec="h264",
                out_pixel_format="yuv420p",
            )

    return f"{Settings.R2_PUBLIC_URL}/{filename}", size
