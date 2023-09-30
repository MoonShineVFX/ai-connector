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
    image: PILImage | List[PILImage],
    image_format: ImageFormat,
    process_list: List[PostProcess],
    dump_result: Callable[[str, any, bool, bool], None],
):
    image_id = cuid_generator()

    # Convert to list for gif compatibility
    this_images = image if isinstance(image, list) else [image]

    for process in process_list:
        logger.debug(f"Processing [{process.type}]")
        time_start = perf_counter()

        args = process.args if process.args is not None else {}

        # Loop back process
        if process.type == "ADD_TEXT":
            this_images = [
                add_text(
                    image,
                    **args,
                )
                for image in this_images
            ]

        # Loop back process
        elif process.type == "WATERMARK":
            this_images = [watermark(image) for image in this_images]

        # Loop back process
        elif process.type == "LETTERBOX":
            new_image = letterbox(this_images[0])
            letterbox_url = upload_bunny(
                [new_image],
                image_id + "_letterbox",
                fmt=image_format,
            )
            dump_result("letterboxes", letterbox_url, True, True)

        # One way process
        elif process.type == "UPLOAD":
            image_url = upload_bunny(
                this_images,
                image_id,
                fmt=image_format,
                **args,
            )
            dump_result("images", image_url, True, False)

        # One way process
        elif process.type == "NSFW_DETECTION":
            nsfw_stat = nsfw_check(this_images[0])
            dump_result("nsfw", nsfw_stat, True, False)

        # One way process
        elif process.type == "BLURHASH":
            blurhash = encode_blurhash(this_images[0])
            dump_result("blurhashes", blurhash, True, True)

        logger.debug(f"Done in {perf_counter() - time_start:.3f}s")
