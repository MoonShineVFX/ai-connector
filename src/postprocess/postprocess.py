from defines import PostProcess, ImageFormat
from PIL.Image import Image as PILImage
from typing import List, Callable
from cuid2 import cuid_wrapper
from loguru import logger
from time import perf_counter

from .add_text import add_text
from .bunny import upload_bunny
from .letterbox import letterbox
from .nsfw import nsfw_check
from .watermark import watermark
from .hash import encode_blurhash

cuid_generator: Callable[[], str] = cuid_wrapper()


def postprocess(
    image: PILImage,
    image_format: ImageFormat,
    process_list: List[PostProcess],
    dump_result: Callable[[str, any, bool, bool], None],
):
    image_id = cuid_generator()

    # Hack args for animate diff (GIF)
    if image.is_animated:
        image_format = "GIF"
        process_list = [
            process
            for process in process_list
            if process.type not in ["ADD_TEXT", "WATERMARK", "LETTERBOX"]
        ]

    for process in process_list:
        logger.debug(f"Processing [{process.type}]")
        time_start = perf_counter()

        if process.type == "ADD_TEXT":
            image = add_text(
                image,
                **process.args,
            )

        elif process.type == "WATERMARK":
            image = watermark(image)

        elif process.type == "LETTERBOX":
            new_image = letterbox(image)
            letterbox_url = upload_bunny(
                new_image,
                image_id + "_letterbox",
                fmt=image_format,
            )
            dump_result("letterboxes", letterbox_url, True, True)

        elif process.type == "UPLOAD":
            image_url = upload_bunny(
                image,
                image_id,
                fmt=image_format,
            )
            dump_result("images", image_url, True, False)

        elif process.type == "NSFW_DETECTION":
            nsfw_stat = nsfw_check(image)
            dump_result("nsfw", nsfw_stat, True, False)

        elif process.type == "BLURHASH":
            blurhash = encode_blurhash(image)
            dump_result("blurhashes", blurhash, True, True)

        logger.debug(f"Done in {perf_counter() - time_start:.3f}s")
