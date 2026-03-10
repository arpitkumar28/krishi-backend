import os
import io
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import tensorflow as tf
from datetime import datetime

app = Flask(__name__)
CORS(app) 

# --- CONFIGURATION ---
MODEL_PATH = 'plant_disease_model.h5'
TARGET_SIZE = (128, 128) 
_model = None  # Lazy loading

def get_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            print("Loading Model...")
            _model = tf.keras.models.load_model(MODEL_PATH)
        else:
            print("Model file not found!")
    return _model

CLASS_NAMES = [
    'Apple Scab', 'Apple black rot', 'Apple Cedar Rust', 'Apple healthy',
    'Blueberry Healthy', 'Cherry Healthy', 'Cherry powdery Mildew',
    'Corn Gray Leaf Spot', 'Corn Common Rust', 'Corn Healthy', 'Corn Northern Leaf',
    'Grape Black Rot', 'Grape Black Measles', 'Grape Healthy', 'Grape Leaf Blight',
    'Orange Haunglongbing', 'Peach Bacterial Spot', 'Peach Healthy',
    'Potato Early Blight', 'Potato Healthy', 'Potato Late Blight',
    'Raspberry Healthy', 'Soybean Healthy', 'Squash Powdery Mildew',
    'Strawberry Healthy', 'Strawberry Leaf Scorch', 'Tomato Bacterial Spot',
    'Tomato Early Blight', 'Tomato Late Blight', 'Tomato Leaf Mold',
    'Tomato Two Spotted Spider', 'Tomato Mosaic Virus', 'Tomato Yellow Leaf Curl Virus',
    'Tomato Healthy', 'Plant Healthy (Generic)'
]

@app.route('/')
def home():
    return jsonify({
        "status": "Online",
        "message": "Krishi Sahayak AI Backend is Running!",
        "model_loaded": get_model() is not None
    })

@app.route('/predict', methods=['POST'])
def predict():
    model = get_model()
    if model is None: return jsonify({'error': 'Model not loaded'}), 500
    
    try:
        file = request.files['file']
        img = Image.open(io.BytesIO(file.read())).convert('RGB').resize(TARGET_SIZE)
        img_array = np.expand_dims(np.array(img) / 255.0, axis=0)

        predictions = model.predict(img_array)
        result_idx = np.argmax(predictions[0])
        disease_name = CLASS_NAMES[result_idx] if result_idx < len(CLASS_NAMES) else "Unknown"
        confidence = float(np.max(predictions[0]))

        return jsonify({
            'class': disease_name,
            'confidence': f"{confidence * 100:.1f}%",
            'treatment': 'Apply appropriate fungicides and ensure crop rotation.',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
