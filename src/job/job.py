from defines import (
    JobType,
    PostProcess,
    JobStatus,
    ImageFormat,
    Settings,
    Webhook,
)
import webuiapi
from .payload import normalize_payload
from loguru import logger
from typing import List, Callable
import traceback
from postprocess import postprocess
import requests
from time import perf_counter


api = webuiapi.WebUIApi(port=Settings.A1111_PORT)


class Job:
    def __init__(
        self,
        on_close: Callable[[object, bool], None],
        _id: str,
        _type: JobType,
        payload: dict,
        image_format: ImageFormat = "WEBP",
        process_list: List[PostProcess] = None,
        status: JobStatus = "PENDING",
        webhook: Webhook = None,
    ):
        self.on_close = on_close

        self.id = _id
        self.type = _type
        self.payload = payload
        self.image_format = image_format
        self.status = status
        self.webhook = webhook
        self.result = {}

        self.generate_images = []

        self.start_time = perf_counter()

        self.process_list: List[PostProcess]
        if process_list is None:
            self.process_list = []
        else:
            self.process_list = process_list

        # Add default upload process
        self.process_list.append(
            PostProcess(
                type="UPLOAD",
                args={
                    "fmt": self.image_format,
                },
            )
        )
        # Add nsfw detection process for image generation
        if self.type in ["TXT2IMG", "IMG2IMG", "EXTRA"]:
            self.process_list.append(PostProcess(type="NSFW_DETECTION"))

        # Normalize payload
        normalize_payload(self.payload)

    def generate(self):
        logger.info(f"Generating [{self.type}]: {self.id}")

        api_result = None
        try:
            if self.type == "TXT2IMG":
                api_result = api.txt2img(
                    **self.payload,
                )
            elif self.type == "IMG2IMG":
                api_result = api.img2img(
                    **self.payload,
                )
            elif self.type == "EXTRA":
                api_result = api.extra_single_image(
                    **self.payload,
                )
            elif self.type == "INTERROGATE":
                api_result = api.interrogate(
                    **self.payload,
                )
            elif self.type == "CONTROLNET_DETECT":
                api_result = api.controlnet_detect(
                    **self.payload,
                )

            if api_result is None:
                raise Exception("No result returned")

            self.generate_images = api_result.images
            self.dump_result("info", api_result.info)

            return True

        except Exception as e:
            logger.error(traceback.format_exc())
            self.dump_result("error", str(e))
            self.close(is_failed=True)
            return False

    def postprocess(self):
        logger.info("Postprocessing...")
        try:
            for image in self.generate_images:
                postprocess(
                    image,
                    self.image_format,
                    self.process_list,
                    self.dump_result,
                )

            self.dump_result("generate_time", perf_counter() - self.start_time)
            return True

        except Exception as e:
            logger.error(traceback.format_exc())
            self.dump_result("error", str(e))
            self.close(is_failed=True)
            return False

    def emit_webhook(self):
        if not self.webhook:
            return
        logger.info(f"Emitting webhook: {self.webhook}")
        try:
            requests.post(
                self.webhook.url,
                headers={
                    "authorization": f"Bearer {self.webhook.token}",
                }
                if self.webhook.token
                else {},
                json={
                    "id": self.id,
                    "worker": Settings.WORKER_NAME,
                    "status": self.status,
                    "result": self.result,
                },
                timeout=3,
            )
        except Exception as e:
            logger.warning(f"Webhook failed: {e}")

    def dump_result(
        self, key: str, value: any, is_append=False, inside_info=False
    ):
        content = self.result
        if inside_info:
            if "info" not in self.result:
                self.result["info"] = {}
            content = self.result["info"]

        if is_append:
            if key not in content:
                content[key] = []
            content[key].append(value)
        else:
            content[key] = value

    def close(self, is_failed=False):
        self.status = "FAILED" if is_failed else "DONE"
        if not is_failed:
            logger.info(f"Job done.")
        else:
            logger.error(f"Job failed.")

        self.emit_webhook()
        self.on_close(self)
