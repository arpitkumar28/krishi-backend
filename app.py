import os
import io
import json
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import tensorflow as tf
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app) 

# --- CONFIGURATION ---
MODEL_PATH = 'plant_disease_model.h5'
USER_DB = '/tmp/users.json' 
TARGET_SIZE = (128, 128) 
_model = None

def get_model():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        _model = tf.keras.models.load_model(MODEL_PATH)
    return _model

def load_users():
    if not os.path.exists(USER_DB): return {}
    try:
        with open(USER_DB, 'r') as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USER_DB, 'w') as f: json.dump(users, f)

CLASS_NAMES = [
    'Apple Scab', 'Apple black rot', 'Apple Cedar Rust', 'Apple healthy',
    'Blueberry Healthy', 'Cherry Healthy', 'Cherry powdery Mildew',
    'Corn Gray Leaf Spot', 'Corn Common Rust', 'Corn Healthy', 'Corn Northern Leaf',
    'Grape Black Rot', 'Grape Black Measles', 'Grape Healthy', 'Grape Black Rot',
    'Grape Black Measles', 'Grape Healthy', 'Frape Leaf Blight', 'Orange Haunglongbing',
    'Peach Bacterial Spot', 'Peach Healthy', 'Potato Early Blight', 'Potato Healthy', 
    'Potato Late Blight', 'Raspberry Healthy', 'Soybean Healthy', 'Squash Powdery Mildew',
    'Strawberry Healthy', 'Strawberry Leaf Scorch', 'Tomato Bacterial Spot',
    'Tomato Early Blight', 'Tomato Late Blight', 'Tomato Leaf Mold',
    'Tomato Two Spotted Spider', 'Tomato Mosaic Virus', 'Tomato Yellow Leaf Curl Virus',
    'Tomato Healthy', 'Plant Healthy (Generic)'
]

TREATMENTS = {
    'Apple Scab': 'Apply fungicides like Captan or Mancozeb. Rake and destroy fallen leaves.',
    'Potato Late Blight': 'Use fungicides like Ridomil Gold or Copper sprays. Destroy infected plants immediately.',
    'Tomato Late Blight': 'Apply fungicides like Mancozeb. Ensure proper air circulation and remove infected leaves.',
    'Bacterial Spot': 'Apply copper-based sprays. Avoid overhead irrigation.',
    'Powdery Mildew': 'Apply neem oil or sulfur-based fungicides. Improve spacing for airflow.',
    'healthy': 'The plant looks healthy! Keep up the good work with regular watering and nutrients.',
    'default': 'Identify early, remove infected parts, and use appropriate organic or chemical fungicides.'
}

# --- ROUTES ---

@app.route('/')
def home():
    return jsonify({
        "status": "Online",
        "message": "Krishi Sahayak AI Backend is Running!",
        "model_loaded": get_model() is not None
    })

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').lower().strip()
    if not email: return jsonify({"error": "Email required"}), 400
    
    users = load_users()
    if email in users: return jsonify({"error": "User already exists"}), 400
    
    users[email] = {
        "name": data.get('name'),
        "password": generate_password_hash(data.get('password'))
    }
    save_users(users)
    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').lower().strip()
    user = load_users().get(email)
    
    if user and check_password_hash(user['password'], data.get('password')):
        return jsonify({"message": "Login successful", "user": {"name": user['name'], "email": email}}), 200
    return jsonify({"error": "Invalid email or password"}), 401

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
        
        treatment = TREATMENTS['default']
        for key in TREATMENTS:
            if key.lower() in disease_name.lower():
                treatment = TREATMENTS[key]
                break

        return jsonify({
            'class': disease_name,
            'confidence': f"{float(np.max(predictions[0])) * 100:.1f}%",
            'treatment': treatment
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
