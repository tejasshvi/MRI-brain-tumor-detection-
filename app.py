"""
Brain Tumor Prediction Flask Backend
Loads the trained VGG16 model (.h5) and serves predictions via REST API.
"""

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import json
import h5py
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import tensorflow as tf
from tensorflow import keras
from PIL import Image
import io
import gdown

app = Flask(__name__)
CORS(app)

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.h5")
IMG_SIZE = (128, 128)
CLASS_LABELS = {0: "Glioma Tumor", 1: "Meningioma Tumor", 2: "No Tumor", 3: "Pituitary Tumor"}

def fix_model_config(h5_path):
    """Bypasses Keras version mismatches by cleaning the internal JSON config."""
    try:
        with h5py.File(h5_path, 'r+') as f:
            if 'model_config' in f.attrs:
                config = json.loads(f.attrs['model_config'])
                def clean(obj):
                    if isinstance(obj, dict):
                        for k in ['module', 'registered_name', 'quantization_config']:
                            obj.pop(k, None)
                        for v in obj.values(): clean(v)
                    elif isinstance(obj, list):
                        for i in obj: clean(i)
                clean(config)
                f.attrs['model_config'] = json.dumps(config).encode('utf-8')
                print("[INFO] Model config cleaned for compatibility.")
    except Exception as e:
        print(f"[WARNING] Fix failed: {e}")

# -- Startup Logic --
if not os.path.exists(MODEL_PATH):
    print("[INFO] Downloading model...")
    gdown.download(f'https://drive.google.com/uc?id=1hAVC43mf8j_5d6huS_IafujL17H2mXcK', MODEL_PATH, quiet=False)

fix_model_config(MODEL_PATH)

print(f"[INFO] Loading model...")
try:
    model = keras.models.load_model(MODEL_PATH, compile=False)
    print("[INFO] Model loaded successfully!")
except Exception as e:
    print(f"[ERROR] Failed to load model: {e}")
    model = None

@app.route("/predict", methods=["POST"])
def predict():
    if model is None: return jsonify({"error": "Model not loaded"}), 500
    file = request.files.get("file")
    if not file: return jsonify({"error": "No file"}), 400
    try:
        img = Image.open(io.BytesIO(file.read())).convert("RGB").resize(IMG_SIZE)
        img_array = np.expand_dims(np.array(img, dtype=np.float32) / 255.0, axis=0)
        preds = model.predict(img_array, verbose=0)[0]
        idx = int(np.argmax(preds))
        return jsonify({
            "prediction": CLASS_LABELS[idx],
            "confidence": round(float(preds[idx]) * 100, 2),
            "probabilities": {CLASS_LABELS[i]: round(float(preds[i]) * 100, 2) for i in range(4)}
        })
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/health")
def health(): return jsonify({"status": "online", "model_ready": model is not None})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
