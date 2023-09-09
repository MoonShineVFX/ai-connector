import numpy as np
from PIL import Image
from nsfw_detector import predict
from tensorflow import keras
from pathlib import Path

model = predict.load_model(str(Path(__file__).parent / "nsfw_model.h5"))


def nsfw_check(image: Image):
    if image.mode != "RGB":
        image = image.convert("RGB")
    image = image.resize((224, 224), Image.NEAREST)
    image = keras.preprocessing.image.img_to_array(image)
    image /= 255
    return predict.classify_nd(model, np.asarray([image]))[0]
