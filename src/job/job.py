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
from datetime import datetime, timezone


api = webuiapi.WebUIApi(port=Settings.A1111_PORT)


class Job:
    def __init__(
        self,
        on_close: Callable[[object, bool], None],
        _id: str,
        _type: JobType,
        payload: dict,
        create_time: datetime,
        queue_key: str,
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
        self.__buffers = []

        self.generate_images = []

        self.start_time = perf_counter()
        self.create_time = create_time
        self.queue_key = queue_key

        self.process_list: List[PostProcess]
        if process_list is None:
            self.process_list = []
        else:
            self.process_list = process_list

        # Normalize payload
        normalize_payload(self.payload)

        # Add default upload process
        upload_args = None
        if self.is_using_animate_diff():
            fps = 8
            try:
                fps = self.payload["alwayson_scripts"]["AnimateDiff"]["args"][
                    0
                ]["fps"]
            except:
                pass
            upload_args = {
                "duration": int(1000 / fps),
            }
            logger.debug(f"AnimateDiff detected, using {fps} FPS for upload")
        self.process_list.append(PostProcess(type="UPLOAD", args=upload_args))

        # Add nsfw detection process for image generation
        if self.type in ["TXT2IMG", "IMG2IMG", "EXTRA"]:
            self.process_list.append(PostProcess(type="NSFW_DETECTION"))

    def generate(self):
        logger.info(f"Generating [{self.type}]: {self.id}")

        api_result = None
        try:
            # If animate diff, set model first
            if self.is_using_animate_diff():
                try:
                    sd_model = self.payload["override_settings"][
                        "sd_model_checkpoint"
                    ]
                    logger.debug(
                        f"Setting sd_model_checkpoint first ({sd_model})"
                    )
                    api.set_options({"sd_model_checkpoint": sd_model})
                    logger.debug("Done")
                except Exception as e:
                    logger.warning(f"Failed to set sd_model first: {e}")
                    pass

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

            # If using AnimateDiff, put all images into one item
            if self.is_using_animate_diff():
                self.generate_images = [api_result.images]
            else:
                self.generate_images = api_result.images

            self.prune_info(api_result.info)
            self.dump_result("info", api_result.info)

            return True

        except Exception as e:
            logger.error(traceback.format_exc())
            self.dump_result("error", str(e))
            self.close(is_failed=True)
            return False

    def is_using_animate_diff(self) -> bool:
        try:
            is_animatediff = self.payload["alwayson_scripts"]["AnimateDiff"][
                "args"
            ][0]["enable"]
            return is_animatediff is True
        except:
            return False

    def prune_info(self, info: dict):
        info.pop("all_prompts", None)
        info.pop("all_negative_prompts", None)
        info.pop("all_subseeds", None)

        if "infotexts" in info:
            info["infotexts"] = [info["infotexts"][0]]

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
                    "worker": Settings.WORKER_INFO,
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

        # Record process time
        self.dump_result(
            "process_time",
            (datetime.now(timezone.utc) - self.create_time).total_seconds(),
        )
        self.dump_result("queue_pool", self.queue_key)

        # Close all buffers
        for buffer in self.__buffers:
            buffer.close()

        self.emit_webhook()
        self.on_close(self)
