"""
Brain Tumor Prediction Flask Backend
Loads the trained VGG16 model (.h5) and serves predictions via REST API.
"""

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import keras
from PIL import Image
import io

app = Flask(__name__)
CORS(app)

# -- Model Configuration --
import os
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.h5")
IMG_SIZE = (128, 128)  # Model trained with 128x128 input
CLASS_LABELS = {
    0: "Glioma Tumor",
    1: "Meningioma Tumor",
    2: "No Tumor",
    3: "Pituitary Tumor"
}


# -- Load Model Once at Startup --
print(f"[INFO] Loading model from: {MODEL_PATH}")
try:
    model = keras.models.load_model(
        MODEL_PATH,
        compile=False
    )
    print("[INFO] Model loaded successfully!")
    print(f"[INFO] Model input shape: {model.input_shape}")
    print(f"[INFO] Model output shape: {model.output_shape}")
except Exception as e:
    print(f"[ERROR] Failed to load model: {e}")
    import traceback
    traceback.print_exc()
    model = None


def preprocess_image(image_bytes):
    """Preprocess the uploaded image for model inference."""
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")
    img = img.resize(IMG_SIZE)
    img_array = np.array(img, dtype=np.float32)
    img_array = img_array / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array


@app.route("/predict", methods=["POST"])
def predict():
    """Receive an MRI image and return the tumor classification."""
    if model is None:
        return jsonify({"error": "Model not loaded. Check server logs."}), 500

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Send an image with key 'file'."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    try:
        image_bytes = file.read()
        img_array = preprocess_image(image_bytes)

        # Run inference
        predictions = model.predict(img_array, verbose=0)
        predicted_class_idx = int(np.argmax(predictions[0]))
        confidence = float(np.max(predictions[0])) * 100

        # All class probabilities
        all_probs = {
            CLASS_LABELS[i]: round(float(predictions[0][i]) * 100, 2)
            for i in range(len(CLASS_LABELS))
        }

        result = {
            "prediction": CLASS_LABELS[predicted_class_idx],
            "confidence": round(confidence, 2),
            "class_index": predicted_class_idx,
            "probabilities": all_probs
        }

        print(f"[PREDICT] {result['prediction']} ({result['confidence']}%)")
        return jsonify(result)

    except Exception as e:
        print(f"[ERROR] Prediction failed: {e}")
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "online",
        "model_loaded": model is not None,
        "classes": list(CLASS_LABELS.values())
    })


if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("   Brain Tumor Prediction Server")
    print("   Server: http://localhost:5000")
    print("   Health: http://localhost:5000/health")
    print("=" * 55 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
