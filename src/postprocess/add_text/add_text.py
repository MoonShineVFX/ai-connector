import textwrap

from PIL import ImageDraw, ImageFont
from PIL.Image import Image as PILImage
from pathlib import Path

FONT_PATH = str(Path(__file__).parent / "ff.ttc")


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
    font = ImageFont.truetype(FONT_PATH, font_size)
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
