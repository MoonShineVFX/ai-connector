from PIL import Image, ImageDraw
from PIL.Image import Image as PILImage


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
