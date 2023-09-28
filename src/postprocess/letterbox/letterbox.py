from PIL import Image
from PIL.Image import Image as PILImage


def letterbox(image: PILImage):
    x, y = image.size
    size = max(x, y)
    new_image = Image.new("RGB", (size, size), (0, 0, 0, 255))
    new_image.paste(image, ((size - x) // 2, (size - y) // 2))

    return new_image
