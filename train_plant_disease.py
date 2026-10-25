
import argparse
import json
from pathlib import Path

import tensorflow as tf

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 8
SEED = 42

CLASS_DIRS = [
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
]

DISPLAY_NAMES = [
    "Potato Early blight",
    "Potato Late blight",
    "Potato healthy",
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data_dir",
        default=r"C:\Users\dell\Downloads\KrishiMitra_AI_MVP (1)\KrishiMitra_AI\PlantVillage",
    )

    parser.add_argument("--output_dir", default=".")
    parser.add_argument("--epochs", type=int, default=20)

    args = parser.parse_args()

    if args.epochs < 1:
        parser.error("--epochs must be at least 1")

    data_dir = Path(args.data_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not data_dir.is_dir():
        raise FileNotFoundError(
            f"Dataset directory not found: {data_dir}"
        )

    for class_name in CLASS_DIRS:
        class_path = data_dir / class_name

        if not class_path.is_dir():
            raise FileNotFoundError(
                f"Missing class folder: {class_path}"
            )

        image_count = sum(
            1
            for path in class_path.rglob("*")
            if path.is_file()
            and path.suffix.lower() in IMAGE_EXTENSIONS
        )

        print(f"{class_name}: {image_count} images")

        if image_count < 2:
            raise ValueError(
                f"At least 2 images are required in {class_path}"
            )

    print("TensorFlow version:", tf.__version__)

    train_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        class_names=CLASS_DIRS,
        validation_split=0.2,
        subset="training",
        seed=SEED,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        label_mode="categorical",
    )

    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        class_names=CLASS_DIRS,
        validation_split=0.2,
        subset="validation",
        seed=SEED,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        label_mode="categorical",
    )

    autotune = tf.data.AUTOTUNE

    train_ds = train_ds.prefetch(autotune)
    val_ds = val_ds.prefetch(autotune)

    augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.08),
        tf.keras.layers.RandomZoom(0.10),
        tf.keras.layers.RandomContrast(0.10),
    ])

    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights="imagenet",
    )

    base_model.trainable = False

    inputs = tf.keras.Input(shape=(224, 224, 3))

    x = augmentation(inputs)
    x = tf.keras.layers.Rescaling(
        1.0 / 127.5,
        offset=-1,
    )(x)

    x = base_model(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.25)(x)

    outputs = tf.keras.layers.Dense(
        len(CLASS_DIRS),
        activation="softmax",
    )(x)

    model = tf.keras.Model(inputs, outputs)

    best_path = output_dir / "best_plant_village_model.keras"

    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            str(best_path),
            monitor="val_loss",
            save_best_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=5,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.2,
            patience=2,
            min_lr=1e-6,
        ),
    ]

    # Phase 1: Train classification layers
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        callbacks=callbacks,
    )

    # Phase 2: Fine-tune the last MobileNetV2 layers
    base_model.trainable = True

    for layer in base_model.layers[:-30]:
        layer.trainable = False

    for layer in base_model.layers:
        if isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=max(1, min(10, args.epochs // 2)),
        callbacks=callbacks,
    )

    # Save trained model in Keras format
    keras_path = output_dir / "plant_village_disease_model.keras"
    model.save(str(keras_path))

    # Save class labels in the same order as model outputs
    with open(
        output_dir / "plant_village_class_names.json",
        "w",
        encoding="utf-8",
    ) as file:
            json.dump(
            {
                "class_dirs": CLASS_DIRS,
                "display_names": DISPLAY_NAMES,
            },
            file,
            indent=4,
        )

    print("\nTraining completed successfully.")
    print("Model output shape:", model.output_shape)
    print("Saved model:", keras_path)
    print(
        "Saved labels:",
        output_dir / "plant_village_class_names.json",
    )


if __name__ == "__main__":
    main()
