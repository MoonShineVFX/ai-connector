import blurhash
from PIL.Image import Image as PILImage

RES = 64
COMPONENTS = 4


def encode_blurhash(image: PILImage):
    width, height = image.size
    image = image.resize((RES, RES)).convert("RGB")
    return {
        "hash": blurhash.encode(image, COMPONENTS, COMPONENTS),
        "width": width,
        "height": height,
    }
