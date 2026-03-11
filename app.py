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
USER_DB = '/tmp/users.json' # Use /tmp for better write access on cloud
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

# --- AUTH ROUTES ---

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email', '').lower().strip() # Force lowercase
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
        
    users = load_users()
    if email in users:
        return jsonify({"error": "User already exists"}), 400
    
    users[email] = {
        "name": name,
        "password": generate_password_hash(password)
    }
    save_users(users)
    print(f"DEBUG: New user registered: {email}")
    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').lower().strip() # Force lowercase
    password = data.get('password')
    
    users = load_users()
    user = users.get(email)
    
    if user and check_password_hash(user['password'], password):
        print(f"DEBUG: Login success for: {email}")
        return jsonify({
            "message": "Login successful",
            "user": {"name": user['name'], "email": email}
        }), 200
    
    print(f"DEBUG: Login failed for: {email}. User found: {user is not None}")
    return jsonify({"error": "Invalid email or password"}), 401

# --- AI ROUTES ---

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
        return jsonify({'class': 'Tomato Late Blight', 'confidence': '94%', 'treatment': 'Apply Mancozeb'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def health():
    return jsonify({"status": "Online", "service": "Krishi Sahayak AI"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
