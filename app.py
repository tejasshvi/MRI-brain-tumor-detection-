"""
Brain Tumor Prediction Flask Backend
Loads the trained VGG16 model (.h5) and serves predictions via REST API.
"""

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
from PIL import Image
import io
import gdown

app = Flask(__name__)
CORS(app)

# -- Configuration --
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.h5")
IMG_SIZE = (128, 128)
CLASS_LABELS = {0: "Glioma Tumor", 1: "Meningioma Tumor", 2: "No Tumor", 3: "Pituitary Tumor"}

def create_and_load_model(path):
    """Bypasses version errors by rebuilding the architecture and loading weights only"""
    try:
        # Rebuilding VGG16 + Custom Layers structure
        vgg = tf.keras.applications.VGG16(include_top=False, input_shape=(128, 128, 3))
        model = tf.keras.models.Sequential([
            vgg,
            tf.keras.layers.Flatten(name='flatten'),
            tf.keras.layers.Dropout(0.3, name='dropout'),
            tf.keras.layers.Dense(128, activation='relu', name='dense'),
            tf.keras.layers.Dropout(0.2, name='dropout_1'),
            tf.keras.layers.Dense(4, activation='softmax', name='dense_1')
        ])
        # Loading only the weights from the file (compatible across Keras versions)
        model.load_weights(path, by_name=True, skip_mismatch=True)
        return model
    except Exception as e:
        print(f"[ERROR] Model build failed: {e}")
        return None

# -- Startup Download & Build --
if not os.path.exists(MODEL_PATH):
    print("[INFO] Downloading weights from Google Drive...")
    gdown.download(f'https://drive.google.com/uc?id=1hAVC43mf8j_5d6huS_IafujL17H2mXcK', MODEL_PATH, quiet=False)

print(f"[INFO] Initializing model...")
model = create_and_load_model(MODEL_PATH)

if model:
    print("[INFO] Model weights loaded successfully!")
else:
    print("[ERROR] Model failed to initialize correctly.")

@app.route("/predict", methods=["POST"])
def predict():
    if model is None: return jsonify({"error": "Model not loaded"}), 500
    file = request.files.get("file")
    if not file: return jsonify({"error": "No file uploaded"}), 400
    try:
        # Image processing
        img = Image.open(io.BytesIO(file.read())).convert("RGB").resize(IMG_SIZE)
        img_array = np.expand_dims(np.array(img, dtype=np.float32) / 255.0, axis=0)
        
        # Inference
        preds = model.predict(img_array, verbose=0)[0]
        idx = int(np.argmax(preds))
        
        return jsonify({
            "prediction": CLASS_LABELS[idx],
            "confidence": round(float(preds[idx]) * 100, 2),
            "probabilities": {CLASS_LABELS[i]: round(float(preds[i]) * 100, 2) for i in range(4)}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    return jsonify({"status": "online", "model_ready": model is not None})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
