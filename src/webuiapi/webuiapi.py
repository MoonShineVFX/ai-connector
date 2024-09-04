import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any


class Upscaler(str, Enum):
    none = "None"
    Lanczos = "Lanczos"
    Nearest = "Nearest"
    LDSR = "LDSR"
    BSRGAN = "BSRGAN"
    ESRGAN_4x = "ESRGAN_4x"
    R_ESRGAN_General_4xV3 = "R-ESRGAN General 4xV3"
    ScuNET_GAN = "ScuNET GAN"
    ScuNET_PSNR = "ScuNET PSNR"
    SwinIR_4x = "SwinIR 4x"


class HiResUpscaler(str, Enum):
    none = "None"
    Latent = "Latent"
    LatentAntialiased = "Latent (antialiased)"
    LatentBicubic = "Latent (bicubic)"
    LatentBicubicAntialiased = "Latent (bicubic antialiased)"
    LatentNearest = "Latent (nearist)"
    LatentNearestExact = "Latent (nearist-exact)"
    Lanczos = "Lanczos"
    Nearest = "Nearest"
    ESRGAN_4x = "ESRGAN_4x"
    LDSR = "LDSR"
    ScuNET_GAN = "ScuNET GAN"
    ScuNET_PSNR = "ScuNET PSNR"
    SwinIR_4x = "SwinIR 4x"


@dataclass
class WebUIApiResult:
    images: list
    parameters: dict
    info: dict

    @property
    def image(self):
        return self.images[0]


class ControlNetUnionControlType(Enum):
    """
    ControlNet control type for ControlNet union model.
    https://github.com/xinsir6/ControlNetPlus/tree/main
    """

    OPENPOSE = "OpenPose"
    DEPTH = "Depth"
    # hed/pidi/scribble/ted
    SOFT_EDGE = "Soft Edge"
    # canny/lineart/anime_lineart/mlsd
    HARD_EDGE = "Hard Edge"
    NORMAL_MAP = "Normal Map"
    SEGMENTATION = "Segmentation"
    TILE = "Tile"
    INPAINT = "Inpaint"

    UNKNOWN = "Unknown"

    @staticmethod
    def all_tags() -> List[str]:
        """Tags can be handled by union ControlNet"""
        return [
            "openpose",
            "depth",
            "softedge",
            "scribble",
            "canny",
            "lineart",
            "mlsd",
            "normalmap",
            "segmentation",
            "inpaint",
            "tile",
        ]

    @staticmethod
    def from_str(s: str):
        s = s.lower()

        if s == "openpose":
            return ControlNetUnionControlType.OPENPOSE
        elif s == "depth":
            return ControlNetUnionControlType.DEPTH
        elif s in ["scribble", "softedge"]:
            return ControlNetUnionControlType.SOFT_EDGE
        elif s in ["canny", "lineart", "mlsd"]:
            return ControlNetUnionControlType.HARD_EDGE
        elif s == "normal":
            return ControlNetUnionControlType.NORMAL_MAP
        elif s == "segmentation":
            return ControlNetUnionControlType.SEGMENTATION
        elif s in ["tile", "blur"]:
            return ControlNetUnionControlType.TILE
        elif s == "inpaint":
            return ControlNetUnionControlType.INPAINT

        return ControlNetUnionControlType.UNKNOWN

    def int_value(self) -> int:
        if self == ControlNetUnionControlType.UNKNOWN:
            raise ValueError("Unknown control type cannot be encoded.")

        return list(ControlNetUnionControlType).index(self)


class ControlNetUnit:
    def __init__(
        self,
        input_image: Image = None,
        mask: Image = None,
        module: str = "none",
        model: str = "None",
        weight: float = 1.0,
        resize_mode: str = "Resize and Fill",
        low_vram: bool = False,
        processor_res: int = 512,
        threshold_a: float = 64,
        threshold_b: float = 64,
        guidance_start: float = 0.0,
        guidance_end: float = 1.0,
        control_mode: int = 0,
        pixel_perfect: bool = False,
        guessmode: int = None,  # deprecated: use control_mode
        enabled: bool = True,
        hr_option: str = "Both",  # Both, Low res only, High res only
        union_control_type: str = None,  # Moonland Type
    ):
        self.input_image = input_image
        self.mask = mask
        self.module = module
        self.model = model
        self.weight = weight
        self.resize_mode = resize_mode
        self.low_vram = low_vram
        self.processor_res = processor_res
        self.threshold_a = threshold_a
        self.threshold_b = threshold_b
        self.guidance_start = guidance_start
        self.guidance_end = guidance_end

        if guessmode:
            print(
                "ControlNetUnit guessmode is deprecated. Please use control_mode instead."
            )
            control_mode = guessmode

        if control_mode == 0:
            self.control_mode = "Balanced"
        elif control_mode == 1:
            self.control_mode = "My prompt is more important"
        elif control_mode == 2:
            self.control_mode = "ControlNet is more important"
        else:
            self.control_mode = control_mode

        self.pixel_perfect = pixel_perfect
        self.enabled = enabled
        self.hr_option = hr_option
        self.union_control_type: ControlNetUnionControlType = (
            ControlNetUnionControlType.from_str(union_control_type)
            if union_control_type
            else ControlNetUnionControlType.UNKNOWN
        )

    def to_dict(self):
        payload = {
            "image": raw_b64_img(self.input_image) if self.input_image else "",
            "mask": raw_b64_img(self.mask) if self.mask is not None else None,
            "module": self.module,
            "model": self.model,
            "weight": self.weight,
            "resize_mode": self.resize_mode,
            "low_vram": self.low_vram,
            "processor_res": self.processor_res,
            "threshold_a": self.threshold_a,
            "threshold_b": self.threshold_b,
            "guidance_start": self.guidance_start,
            "guidance_end": self.guidance_end,
            "control_mode": self.control_mode,
            "pixel_perfect": self.pixel_perfect,
            "hr_option": self.hr_option,
            "enabled": self.enabled,
        }

        if self.union_control_type != ControlNetUnionControlType.UNKNOWN:
            payload["union_control_type"] = self.union_control_type.value

        return payload


def b64_img(image: Image) -> str:
    return "data:image/png;base64," + raw_b64_img(image)


def raw_b64_img(image: Image) -> str:
    # XXX controlnet only accepts RAW base64 without headers
    with io.BytesIO() as output_bytes:
        metadata = None
        for key, value in image.info.items():
            if isinstance(key, str) and isinstance(value, str):
                if metadata is None:
                    metadata = PngImagePlugin.PngInfo()
                metadata.add_text(key, value)
        image.save(output_bytes, format="PNG", pnginfo=metadata)

        bytes_data = output_bytes.getvalue()

    return str(base64.b64encode(bytes_data), "utf-8")


class WebUIApi:
    def __init__(
        self,
        host="127.0.0.1",
        port=7860,
        baseurl=None,
        sampler="Euler a",
        steps=20,
        use_https=False,
        username=None,
        password=None,
    ):
        if baseurl is None:
            if use_https:
                rooturl = f"https://{host}:{port}"
                baseurl = f"{rooturl}/sdapi/v1"
            else:
                rooturl = f"http://{host}:{port}"
                baseurl = f"{rooturl}/sdapi/v1"

        self.rooturl = rooturl
        self.baseurl = baseurl
        self.default_sampler = sampler
        self.default_steps = steps

        self.session = requests.Session()

        if username and password:
            self.set_auth(username, password)

    def set_auth(self, username, password):
        self.session.auth = (username, password)

    def _to_api_result(self, response):
        if response.status_code != 200:
            raise RuntimeError(response.status_code, response.text)

        r = response.json()
        images = []
        if "images" in r.keys():
            images = [
                Image.open(io.BytesIO(base64.b64decode(i)))
                for i in r["images"]
            ]
        elif "image" in r.keys():
            images = [Image.open(io.BytesIO(base64.b64decode(r["image"])))]

        info = {}
        if "info" in r.keys():
            try:
                info = json.loads(r["info"])
            except:
                info = {
                    "info": r["info"],
                }
        elif "html_info" in r.keys():
            info = {
                "html_info": r["html_info"],
            }
        elif "caption" in r.keys():
            info = {
                "caption": r["caption"],
            }

        parameters = ""
        if "parameters" in r.keys():
            parameters = r["parameters"]

        return WebUIApiResult(images, parameters, info)

    async def _to_api_result_async(self, response):
        if response.status != 200:
            raise RuntimeError(response.status, await response.text())

        r = await response.json()
        images = []
        if "images" in r.keys():
            images = [
                Image.open(io.BytesIO(base64.b64decode(i)))
                for i in r["images"]
            ]
        elif "image" in r.keys():
            images = [Image.open(io.BytesIO(base64.b64decode(r["image"])))]

        info = ""
        if "info" in r.keys():
            try:
                info = json.loads(r["info"])
            except:
                info = r["info"]
        elif "html_info" in r.keys():
            info = r["html_info"]
        elif "caption" in r.keys():
            info = r["caption"]

        parameters = ""
        if "parameters" in r.keys():
            parameters = r["parameters"]

        return WebUIApiResult(images, parameters, info)

    def txt2img(
        self,
        enable_hr=False,
        denoising_strength=0.7,
        firstphase_width=0,
        firstphase_height=0,
        hr_scale=2,
        hr_upscaler=HiResUpscaler.Latent,
        hr_second_pass_steps=0,
        hr_resize_x=0,
        hr_resize_y=0,
        prompt="",
        styles=[],
        seed=-1,
        subseed=-1,
        subseed_strength=0.0,
        seed_resize_from_h=0,
        seed_resize_from_w=0,
        sampler_name=None,  # use this instead of sampler_index
        batch_size=1,
        n_iter=1,
        steps=None,
        cfg_scale=7.0,
        width=512,
        height=512,
        restore_faces=False,
        tiling=False,
        do_not_save_samples=False,
        do_not_save_grid=False,
        negative_prompt="",
        eta=1.0,
        s_churn=0,
        s_tmax=0,
        s_tmin=0,
        s_noise=1,
        override_settings={},
        override_settings_restore_afterwards=True,
        script_args=None,  # List of arguments for the script "script_name"
        script_name=None,
        send_images=True,
        save_images=False,
        alwayson_scripts={},
        controlnet_units: List[ControlNetUnit] = [],
        sampler_index=None,  # deprecated: use sampler_name
        use_deprecated_controlnet=False,
        use_async=False,
        # 1.6
        refiner_checkpoint=None,
        refiner_switch_at=0,
        # 1.9
        scheduler=None,
    ):
        if sampler_index is None:
            sampler_index = self.default_sampler
        if sampler_name is None:
            sampler_name = self.default_sampler
        if steps is None:
            steps = self.default_steps
        if script_args is None:
            script_args = []
        payload = {
            "enable_hr": enable_hr,
            "hr_scale": hr_scale,
            "hr_upscaler": hr_upscaler,
            "hr_second_pass_steps": hr_second_pass_steps,
            "hr_resize_x": hr_resize_x,
            "hr_resize_y": hr_resize_y,
            "denoising_strength": denoising_strength,
            "firstphase_width": firstphase_width,
            "firstphase_height": firstphase_height,
            "prompt": prompt,
            "styles": styles,
            "seed": seed,
            "subseed": subseed,
            "subseed_strength": subseed_strength,
            "seed_resize_from_h": seed_resize_from_h,
            "seed_resize_from_w": seed_resize_from_w,
            "batch_size": batch_size,
            "n_iter": n_iter,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "width": width,
            "height": height,
            "restore_faces": restore_faces,
            "tiling": tiling,
            "do_not_save_samples": do_not_save_samples,
            "do_not_save_grid": do_not_save_grid,
            "negative_prompt": negative_prompt,
            "eta": eta,
            "s_churn": s_churn,
            "s_tmax": s_tmax,
            "s_tmin": s_tmin,
            "s_noise": s_noise,
            "override_settings": override_settings,
            "override_settings_restore_afterwards": override_settings_restore_afterwards,
            "sampler_name": sampler_name,
            "sampler_index": sampler_index,
            "script_name": script_name,
            "script_args": script_args,
            "send_images": send_images,
            "save_images": save_images,
            "alwayson_scripts": alwayson_scripts,
            # 1.6
            "refiner_checkpoint": refiner_checkpoint,
            "refiner_switch_at": refiner_switch_at,
        }

        # 1.9
        if scheduler:
            payload["scheduler"] = scheduler

        if controlnet_units and len(controlnet_units) > 0:
            payload["alwayson_scripts"]["ControlNet"] = {
                "args": [x.to_dict() for x in controlnet_units]
            }
        else:
            payload["alwayson_scripts"]["ControlNet"] = {"args": []}

        return self.post_and_get_api_result(
            f"{self.baseurl}/txt2img", payload, use_async
        )

    def post_and_get_api_result(self, url, json, use_async):
        if use_async:
            raise RuntimeError("use_async is not supported yet")
        else:
            response = self.session.post(url=url, json=json)
            return self._to_api_result(response)

    async def async_post(self, url, json):
        return

    def img2img(
        self,
        images=[],  # list of PIL Image
        resize_mode=0,
        denoising_strength=0.75,
        image_cfg_scale=1.5,
        mask_image=None,  # PIL Image mask
        mask_blur=4,
        inpainting_fill=0,
        inpaint_full_res=True,
        inpaint_full_res_padding=0,
        inpainting_mask_invert=0,
        initial_noise_multiplier=1,
        prompt="",
        styles=[],
        seed=-1,
        subseed=-1,
        subseed_strength=0,
        seed_resize_from_h=0,
        seed_resize_from_w=0,
        sampler_name=None,  # use this instead of sampler_index
        batch_size=1,
        n_iter=1,
        steps=None,
        cfg_scale=7.0,
        width=512,
        height=512,
        restore_faces=False,
        tiling=False,
        do_not_save_samples=False,
        do_not_save_grid=False,
        negative_prompt="",
        eta=1.0,
        s_churn=0,
        s_tmax=0,
        s_tmin=0,
        s_noise=1,
        override_settings={},
        override_settings_restore_afterwards=True,
        script_args=None,  # List of arguments for the script "script_name"
        sampler_index=None,  # deprecated: use sampler_name
        include_init_images=False,
        script_name=None,
        send_images=True,
        save_images=False,
        alwayson_scripts={},
        controlnet_units: List[ControlNetUnit] = [],
        use_async=False,
        # 1.6
        refiner_checkpoint=None,
        refiner_switch_at=0,
        # 1.9
        scheduler=None,
    ):
        if sampler_name is None:
            sampler_name = self.default_sampler
        if sampler_index is None:
            sampler_index = self.default_sampler
        if steps is None:
            steps = self.default_steps
        if script_args is None:
            script_args = []

        payload = {
            "init_images": [b64_img(x) for x in images],
            "resize_mode": resize_mode,
            "denoising_strength": denoising_strength,
            "mask_blur": mask_blur,
            "inpainting_fill": inpainting_fill,
            "inpaint_full_res": inpaint_full_res,
            "inpaint_full_res_padding": inpaint_full_res_padding,
            "inpainting_mask_invert": inpainting_mask_invert,
            "initial_noise_multiplier": initial_noise_multiplier,
            "prompt": prompt,
            "styles": styles,
            "seed": seed,
            "subseed": subseed,
            "subseed_strength": subseed_strength,
            "seed_resize_from_h": seed_resize_from_h,
            "seed_resize_from_w": seed_resize_from_w,
            "batch_size": batch_size,
            "n_iter": n_iter,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "image_cfg_scale": image_cfg_scale,
            "width": width,
            "height": height,
            "restore_faces": restore_faces,
            "tiling": tiling,
            "do_not_save_samples": do_not_save_samples,
            "do_not_save_grid": do_not_save_grid,
            "negative_prompt": negative_prompt,
            "eta": eta,
            "s_churn": s_churn,
            "s_tmax": s_tmax,
            "s_tmin": s_tmin,
            "s_noise": s_noise,
            "override_settings": override_settings,
            "override_settings_restore_afterwards": override_settings_restore_afterwards,
            "sampler_name": sampler_name,
            "sampler_index": sampler_index,
            "include_init_images": include_init_images,
            "script_name": script_name,
            "script_args": script_args,
            "send_images": send_images,
            "save_images": save_images,
            "alwayson_scripts": alwayson_scripts,
            # 1.6
            "refiner_checkpoint": refiner_checkpoint,
            "refiner_switch_at": refiner_switch_at,
        }

        # 1.9
        if scheduler is not None:
            payload["scheduler"] = scheduler

        if mask_image is not None:
            payload["mask"] = b64_img(mask_image)

        if controlnet_units and len(controlnet_units) > 0:
            payload["alwayson_scripts"]["ControlNet"] = {
                "args": [x.to_dict() for x in controlnet_units]
            }
        else:
            payload["alwayson_scripts"]["ControlNet"] = {"args": []}

        return self.post_and_get_api_result(
            f"{self.baseurl}/img2img", payload, use_async
        )

    def extra_single_image(
        self,
        image,  # PIL Image
        resize_mode=0,
        show_extras_results=True,
        gfpgan_visibility=0,
        codeformer_visibility=0,
        codeformer_weight=0,
        upscaling_resize=2,
        upscaling_resize_w=512,
        upscaling_resize_h=512,
        upscaling_crop=True,
        upscaler_1="None",
        upscaler_2="None",
        extras_upscaler_2_visibility=0,
        upscale_first=False,
        use_async=False,
    ):
        payload = {
            "resize_mode": resize_mode,
            "show_extras_results": show_extras_results,
            "gfpgan_visibility": gfpgan_visibility,
            "codeformer_visibility": codeformer_visibility,
            "codeformer_weight": codeformer_weight,
            "upscaling_resize": upscaling_resize,
            "upscaling_resize_w": upscaling_resize_w,
            "upscaling_resize_h": upscaling_resize_h,
            "upscaling_crop": upscaling_crop,
            "upscaler_1": upscaler_1,
            "upscaler_2": upscaler_2,
            "extras_upscaler_2_visibility": extras_upscaler_2_visibility,
            "upscale_first": upscale_first,
            "image": b64_img(image),
        }

        return self.post_and_get_api_result(
            f"{self.baseurl}/extra-single-image", payload, use_async
        )

    def extra_batch_images(
        self,
        images,  # list of PIL images
        name_list=None,  # list of image names
        resize_mode=0,
        show_extras_results=True,
        gfpgan_visibility=0,
        codeformer_visibility=0,
        codeformer_weight=0,
        upscaling_resize=2,
        upscaling_resize_w=512,
        upscaling_resize_h=512,
        upscaling_crop=True,
        upscaler_1="None",
        upscaler_2="None",
        extras_upscaler_2_visibility=0,
        upscale_first=False,
        use_async=False,
    ):
        if name_list is not None:
            if len(name_list) != len(images):
                raise RuntimeError("len(images) != len(name_list)")
        else:
            name_list = [f"image{i + 1:05}" for i in range(len(images))]
        images = [b64_img(x) for x in images]

        image_list = []
        for name, image in zip(name_list, images):
            image_list.append({"data": image, "name": name})

        payload = {
            "resize_mode": resize_mode,
            "show_extras_results": show_extras_results,
            "gfpgan_visibility": gfpgan_visibility,
            "codeformer_visibility": codeformer_visibility,
            "codeformer_weight": codeformer_weight,
            "upscaling_resize": upscaling_resize,
            "upscaling_resize_w": upscaling_resize_w,
            "upscaling_resize_h": upscaling_resize_h,
            "upscaling_crop": upscaling_crop,
            "upscaler_1": upscaler_1,
            "upscaler_2": upscaler_2,
            "extras_upscaler_2_visibility": extras_upscaler_2_visibility,
            "upscale_first": upscale_first,
            "imageList": image_list,
        }

        return self.post_and_get_api_result(
            f"{self.baseurl}/extra-batch-images", payload, use_async
        )

    # XXX 500 error (2022/12/26)
    def png_info(self, image):
        payload = {
            "image": b64_img(image),
        }

        response = self.session.post(
            url=f"{self.baseurl}/png-info", json=payload
        )
        return self._to_api_result(response)

    """
    :param image pass base64 encoded image or PIL Image
    :param model "clip" or "deepdanbooru"
    """

    def interrogate(self, image, model="clip"):
        payload = {
            "image": b64_img(image)
            if isinstance(image, Image.Image)
            else image,
            "model": model,
        }

        response = self.session.post(
            url=f"{self.baseurl}/interrogate", json=payload
        )
        return self._to_api_result(response)

    def promptgen(self, startingText: str = "", generateType: str = "normal"):
        payload = {
            "startingText": startingText,
            "generateType": generateType,
        }
        response = self.session.post(
            url=f"{self.rooturl}/moonland/promptgen", json=payload
        )
        return self._to_api_result(response)

    def interrupt(self):
        response = self.session.post(url=f"{self.baseurl}/interrupt")
        return response.json()

    def skip(self):
        response = self.session.post(url=f"{self.baseurl}/skip")
        return response.json()

    def get_options(self):
        response = self.session.get(url=f"{self.baseurl}/options")
        return response.json()

    def set_options(self, options):
        response = self.session.post(
            url=f"{self.baseurl}/options", json=options
        )
        return response.json()

    def get_cmd_flags(self):
        response = self.session.get(url=f"{self.baseurl}/cmd-flags")
        return response.json()

    def get_progress(self):
        response = self.session.get(url=f"{self.baseurl}/progress")
        return response.json()

    def get_samplers(self):
        response = self.session.get(url=f"{self.baseurl}/samplers")
        return response.json()

    def get_sd_vae(self):
        response = self.session.get(url=f"{self.baseurl}/sd-vae")
        return response.json()

    def get_upscalers(self):
        response = self.session.get(url=f"{self.baseurl}/upscalers")
        return response.json()

    def get_latent_upscale_modes(self):
        response = self.session.get(url=f"{self.baseurl}/latent-upscale-modes")
        return response.json()

    def get_loras(self):
        response = self.session.get(url=f"{self.baseurl}/loras")
        return response.json()

    def get_sd_models(self):
        response = self.session.get(url=f"{self.baseurl}/sd-models")
        return response.json()

    def get_hypernetworks(self):
        response = self.session.get(url=f"{self.baseurl}/hypernetworks")
        return response.json()

    def get_face_restorers(self):
        response = self.session.get(url=f"{self.baseurl}/face-restorers")
        return response.json()

    def get_realesrgan_models(self):
        response = self.session.get(url=f"{self.baseurl}/realesrgan-models")
        return response.json()

    def get_prompt_styles(self):
        response = self.session.get(url=f"{self.baseurl}/prompt-styles")
        return response.json()

    def get_artist_categories(self):  # deprecated ?
        response = self.session.get(url=f"{self.baseurl}/artist-categories")
        return response.json()

    def get_artists(self):  # deprecated ?
        response = self.session.get(url=f"{self.baseurl}/artists")
        return response.json()

    def refresh_checkpoints(self):
        response = self.session.post(url=f"{self.baseurl}/refresh-checkpoints")
        return response.json()

    def get_scripts(self):
        response = self.session.get(url=f"{self.baseurl}/scripts")
        return response.json()

    def get_embeddings(self):
        response = self.session.get(url=f"{self.baseurl}/embeddings")
        return response.json()

    def get_memory(self):
        response = self.session.get(url=f"{self.baseurl}/memory")
        return response.json()

    def get_endpoint(self, endpoint, baseurl):
        if baseurl:
            return f"{self.baseurl}/{endpoint}"
        else:
            from urllib.parse import urlparse, urlunparse

            parsed_url = urlparse(self.baseurl)
            basehost = parsed_url.netloc
            parsed_url2 = (parsed_url[0], basehost, endpoint, "", "", "")
            return urlunparse(parsed_url2)

    def custom_get(self, endpoint, baseurl=False):
        url = self.get_endpoint(endpoint, baseurl)
        response = self.session.get(url=url)
        return response.json()

    def custom_post(
        self, endpoint, payload={}, baseurl=False, use_async=False
    ):
        url = self.get_endpoint(endpoint, baseurl)
        if use_async:
            import asyncio

            return asyncio.ensure_future(
                self.async_post(url=url, json=payload)
            )
        else:
            response = self.session.post(url=url, json=payload)
            return self._to_api_result(response)

    def controlnet_version(self):
        r = self.custom_get("controlnet/version")
        return r["version"]

    def controlnet_model_list(self):
        r = self.custom_get("controlnet/model_list")
        return r["model_list"]

    def controlnet_module_list(self):
        r = self.custom_get("controlnet/module_list")
        return r["module_list"]

    def controlnet_detect(
        self,
        images,
        module="none",
        processor_res=512,
        threshold_a=64,
        threshold_b=64,
    ):
        input_images = [b64_img(x) for x in images]
        payload = {
            "controlnet_module": module,
            "controlnet_input_images": input_images,
            "controlnet_processor_res": processor_res,
            "controlnet_threshold_a": threshold_a,
            "controlnet_threshold_b": threshold_b,
        }
        r = self.custom_post("controlnet/detect", payload=payload)
        return r

    def util_get_model_names(self):
        return sorted([x["title"] for x in self.get_sd_models()])

    def util_set_model(self, name, find_closest=True):
        if find_closest:
            name = name.lower()
        models = self.util_get_model_names()
        found_model = None
        if name in models:
            found_model = name
        elif find_closest:
            import difflib

            def str_simularity(a, b):
                return difflib.SequenceMatcher(None, a, b).ratio()

            max_sim = 0.0
            max_model = models[0]
            for model in models:
                sim = str_simularity(name, model)
                if sim >= max_sim:
                    max_sim = sim
                    max_model = model
            found_model = max_model
        if found_model:
            print(f"loading {found_model}")
            options = {}
            options["sd_model_checkpoint"] = found_model
            self.set_options(options)
            print(f"model changed to {found_model}")
        else:
            print("model not found")

    def util_get_current_model(self):
        options = self.get_options()
        if "sd_model_checkpoint" in options:
            return options["sd_model_checkpoint"]
        else:
            sd_models = self.get_sd_models()
            sd_model = [
                model
                for model in sd_models
                if model["sha256"] == options["sd_checkpoint_hash"]
            ]
            return sd_model[0]["title"]

    def util_wait_for_ready(self, check_interval=5.0):
        import time

        while True:
            result = self.get_progress()
            progress = result["progress"]
            job_count = result["state"]["job_count"]
            if progress == 0.0 and job_count == 0:
                break
            else:
                print(
                    f"[WAIT]: progress = {progress:.4f}, job_count = {job_count}"
                )
                time.sleep(check_interval)

    # Connector implementation
    def get_queue_status(self):
        response = self.session.get(
            url=f"{self.baseurl}/queue/status",
            headers={"Cache-Control": "no-cache"},
        )
        return response.json()

    def restart_server(self):
        response = self.session.post(url=f"{self.baseurl}/server-restart")
        return response.json()

    def stop_server(self):
        response = self.session.post(url=f"{self.baseurl}/server-stop")
        return response.json()

    def kill_server(self):
        response = self.session.post(url=f"{self.baseurl}/server-kill")
        return response.json()
