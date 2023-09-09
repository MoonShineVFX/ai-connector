from defines import PostProcess, ImageFormat
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Image as PILImage
from typing import List
import textwrap
from typing import Callable
from cuid2 import cuid_wrapper
from .bunny import upload_bunny
from .nsfw import nsfw_check


cuid_generator: Callable[[], str] = cuid_wrapper()


def postprocess(
    image: PILImage,
    image_format: ImageFormat,
    process_list: List[PostProcess],
    dump_result: Callable[[str, any, bool], None],
):
    image_id = cuid_generator()

    for process in process_list:
        if process.type == "ADD_TEXT":
            image = add_text(
                image,
                **process.args,
            )

        elif process.type == "WATERMARK":
            image = watermark(image)

        elif process.type == "LETTERBOX":
            new_image = letterbox(image)
            upload_bunny(
                new_image,
                image_id + "_letterbox",
                fmt=image_format,
            )

        elif process.type == "UPLOAD":
            image_url = upload_bunny(
                image,
                image_id,
                fmt=image_format,
            )
            dump_result("images", image_url, True)

        elif process.type == "NSFW_DETECTION":
            nsfw_stat = nsfw_check(image)
            dump_result("nsfw", nsfw_stat, True)


def add_text(
    image: PILImage,
    text="moonshine",
    font_size=16,
    text_color=(255, 255, 255),
    outline_color=(0, 0, 0),
    stroke_width=1,
    x_ratio=0.1,
    y_ratio=0.1,
    line_width=10,
    letter_spacing=0,
    line_spacing=5,
    text_align="left",
):
    image_draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("postprocess/ff.ttc", font_size)
    lines = textwrap.wrap(text, width=line_width)
    width, height = image.size
    x = int(width * x_ratio)
    y = int(height * y_ratio)

    for line in lines:
        w = 0
        for c in line:
            bbox = font.getbbox(c)
            w += bbox[2] - bbox[0] + letter_spacing

        if text_align == "left":
            pass
        elif text_align == "right":
            x = int(width * (1 - x_ratio) - w)
        elif text_align == "center":
            x = int((width - w) / 2)

        image_draw.text(
            (x, y),
            line,
            fill=text_color,
            font=font,
            stroke_width=stroke_width,
            stroke_fill=outline_color,
        )

        h = font.getbbox(line)[3] - font.getbbox(line)[1] + line_spacing
        y += h

    return image


def watermark(image: PILImage):
    w, h = image.size
    image2 = image.copy()

    text = Image.new(mode="RGBA", size=(w, h), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    size = 2

    draw.polygon([(0, 0), (0, size), (size, 0)], outline="black", fill="black")
    draw.polygon(
        [(0, h), (0, h - size), (size, h)], outline="black", fill="black"
    )
    draw.polygon(
        [(w, 0), (w - size, 0), (w, size)], outline="black", fill="black"
    )
    draw.polygon(
        [(w, h), (w - size, h), (w, h - size)], outline="black", fill="black"
    )

    image2.paste(text, (50, 0), text)
    image2.convert("RGBA")
    image2.putalpha(15)
    image.paste(image2, (0, 0), image2)

    return image


def letterbox(image: PILImage):
    x, y = image.size
    size = max(x, y)
    new_image = Image.new("RGB", (size, size), (0, 0, 0, 255))
    new_image.paste(image, ((size - x) // 2, (size - y) // 2))

    return new_image
