
from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = Path(__file__).resolve().parent / "plant_village_disease_model.keras"

CLASS_NAMES = [
    "Potato Early blight",
    "Potato Late blight",
    "Potato healthy",
]

IMAGE_SIZE = (224, 224)


def load_disease_model():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}\n"
            "Run train_plant_disease.py first."
        )

    model = tf.keras.models.load_model(MODEL_PATH)

    if model.output_shape[-1] != len(CLASS_NAMES):
        raise ValueError(
            f"Model has {model.output_shape[-1]} output classes, "
            f"but {len(CLASS_NAMES)} class names are configured."
        )

    return model



def predict_disease(uploaded_file):
    try:
        model = load_disease_model()

        # Read and preprocess image
        image = Image.open(uploaded_file).convert("RGB")
        image = image.resize(IMAGE_SIZE)

        # Model contains its own Rescaling layer.
        # Pass pixel values in the 0-255 range.
        image_array = np.asarray(
            image,
            dtype=np.float32,
        )

        image_array = np.expand_dims(image_array, axis=0)

        # Predict
        prediction = model.predict(
            image_array,
            verbose=0,
        )[0]

        if len(prediction) != len(CLASS_NAMES):
            return {
                "ok": False,
                "error": (
                    f"Expected {len(CLASS_NAMES)} predictions, "
                    f"received {len(prediction)}."
                ),
            }

        index = int(np.argmax(prediction))

        return {
            "ok": True,
            "label": CLASS_NAMES[index],
            "confidence": float(prediction[index]),
            "probabilities": {
                CLASS_NAMES[i]: float(prediction[i])
                for i in range(len(CLASS_NAMES))
            },
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }
