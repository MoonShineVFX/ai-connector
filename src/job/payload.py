from webuiapi import ControlNetUnit
import requests
from io import BytesIO
from PIL import Image
from loguru import logger
import re
import base64
import requests_cache


# Cache requests for 7 days
requests_cache.install_cache("cache", expire_after=60 * 60 * 24 * 7)

REQUESTS_HEADERS = headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
}


def normalize_image(image: str):
    if image.startswith("data:image"):
        return Image.open(
            BytesIO(
                base64.b64decode(re.sub("^data:image/.+;base64,", "", image))
            )
        )

    if image.startswith("https://"):
        logger.debug(f"Downloading image: {image}")
        response = requests.get(image, headers=REQUESTS_HEADERS)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
        else:
            logger.error(f"Failed to download image: {response.status_code}")
            raise Exception(f"Invalid image requested: {image[:100]}")

    raise Exception(f"Invalid image: {image[:100]}")


def normalize_payload(payload: dict):
    if "image" in payload:
        payload["image"] = normalize_image(payload["image"])

    if "mask_image" in payload:
        payload["mask_image"] = normalize_image(payload["mask_image"])

    if "images" in payload:
        payload["images"] = [
            normalize_image(image) for image in payload["images"]
        ]

    if "controlnet_units" in payload and isinstance(
        payload["controlnet_units"], list
    ):
        normalized_controlnet_units = []
        for controlnet_unit_dict in payload["controlnet_units"]:
            if (
                "input_image" in controlnet_unit_dict
                and controlnet_unit_dict["input_image"] is not None
            ):
                controlnet_unit_dict["input_image"] = normalize_image(
                    controlnet_unit_dict["input_image"]
                )

            if (
                "mask" in controlnet_unit_dict
                and controlnet_unit_dict["mask"] is not None
            ):
                controlnet_unit_dict["mask"] = normalize_image(
                    controlnet_unit_dict["mask"]
                )

            normalized_controlnet_units.append(
                ControlNetUnit(**controlnet_unit_dict)
            )

        payload["controlnet_units"] = normalized_controlnet_units
