from webuiapi import ControlNetUnit
import requests
from io import BytesIO
from PIL import Image
from loguru import logger
import re
import base64


REQUESTS_HEADERS = headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
}


def normalize_image(image: str):
    pil_image = None
    if image.startswith("data:image"):
        pil_image = Image.open(
            BytesIO(
                base64.b64decode(re.sub("^data:image/.+;base64,", "", image))
            )
        )
    elif image.startswith("https://"):
        logger.debug(f"Downloading image: {image}")
        response = requests.get(image, headers=REQUESTS_HEADERS, timeout=60)
        if response.status_code == 200:
            pil_image = Image.open(BytesIO(response.content))
        else:
            logger.error(f"Failed to download image: {response.status_code}")
            raise Exception(f"Invalid image requested: {image[:100]}")

    if pil_image is None:
        raise Exception(f"Invalid image: {image[:100]}")

    # change to RGB if CMYK
    if pil_image.mode == "CMYK":
        pil_image = pil_image.convert("RGB")

    return pil_image


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

    # AnimateDiff
    try:
        is_animatediff = payload["alwayson_scripts"]["AnimateDiff"]["args"][0][
            "enable"
        ]

        if is_animatediff:
            payload["alwayson_scripts"]["AnimateDiff"]["args"][0]["format"] = [
                "Frame",
                "PNG",
            ]

            # Try to set optimize settings but don't touch if it's already set
            if "override_settings" not in payload:
                payload["override_settings"] = {}
            override_settings = payload["override_settings"]
            override_settings["pad_cond_uncond"] = override_settings.get(
                "pad_cond_uncond", True
            )
            override_settings["batch_cond_uncond"] = override_settings.get(
                "batch_cond_uncond", True
            )
            override_settings[
                "always_discard_next_to_last_sigma"
            ] = override_settings.get(
                "always_discard_next_to_last_sigma", False
            )

    except:
        pass
