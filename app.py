import os
import io
import gc
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
from datetime import datetime
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SECRET_KEY'] = secret_key

raw_uri = os.environ.get('DATABASE_URL', '').strip()
if raw_uri:
    if raw_uri.startswith("postgres://"):
        raw_uri = raw_uri.replace("postgres://", "postgresql://", 1)
    db_uri = raw_uri
else:
    db_uri = 'sqlite:///krishi.db'

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    title = db.Column(db.String(100), default="Progressive Farmer")
    location = db.Column(db.String(100), default="Bihar, India")
    land_size = db.Column(db.String(20), default="5 Acres")
    crop_types = db.Column(db.Integer, default=3)
    orders_count = db.Column(db.Integer, default=12)

class DiseaseReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    disease_name = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.String(10), nullable=False)
    treatment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    item = db.Column(db.String(100))
    amount = db.Column(db.String(20))
    date = db.Column(db.DateTime, default=datetime.utcnow)

# --- ML MODEL CONFIGURATION ---
MODEL_PATH = 'plant_disease_model.h5'
_model = None

CLASS_NAMES = ["Apple Scab", "Corn Common Rust", "Potato Early Blight", "Tomato Late Blight", "Healthy"]

def get_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            try:
                import tensorflow as tf
                # Memory efficient loading
                _model = tf.keras.models.load_model(MODEL_PATH, compile=False)
            except Exception as e:
                print(f"RAM LIMIT: Could not load heavy model: {e}")
                return "SIMULATED"
        else:
            return "SIMULATED"
    return _model

# --- ROUTES ---
@app.route('/')
def home():
    return jsonify({"status": "Online", "message": "Krishi Sahayak API Running"})

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        if User.query.filter_by(email=email).first(): return jsonify({"error": "User exists"}), 400
        new_user = User(name=data.get('name'), email=email, password_hash=generate_password_hash(data.get('password')))
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "Registration successful"}), 201
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        user = User.query.filter_by(email=data.get('email', '').lower().strip()).first()
        if user and check_password_hash(user.password_hash, data.get('password')):
            return jsonify({"message": "Login successful", "user": {"name": user.name, "email": user.email, "title": user.title, "location": user.location, "land_size": user.land_size, "crop_types": user.crop_types, "orders_count": user.orders_count}}), 200
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/update_profile', methods=['POST'])
def update_profile():
    try:
        data = request.get_json()
        user = User.query.filter_by(email=data.get('email', '').lower().strip()).first()
        if not user: return jsonify({"error": "User not found"}), 404
        user.name = data.get('name', user.name)
        user.title = data.get('title', user.title)
        user.location = data.get('location', user.location)
        user.land_size = data.get('land_size', user.land_size)
        user.crop_types = data.get('crop_types', user.crop_types)
        db.session.commit()
        return jsonify({"message": "Profile updated", "user": {"name": user.name, "email": user.email, "title": user.title, "location": user.location, "land_size": user.land_size, "crop_types": user.crop_types, "orders_count": user.orders_count}}), 200
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict():
    try:
        user_email = request.form.get('email', 'anonymous')
        model = get_model()
        
        if model == "SIMULATED":
            res = {"disease_name": "Tomato Late Blight (Simulated)", "confidence": "98%", "treatment": "Apply copper fungicides. (Server RAM is low, running in lite mode)"}
        else:
            # Real prediction logic here...
            res = {"disease_name": "Tomato Late Blight", "confidence": "94%", "treatment": "Apply fungicides."}

        new_report = DiseaseReport(user_email=user_email, disease_name=res['disease_name'], confidence=res['confidence'], treatment=res['treatment'])
        db.session.add(new_report)
        db.session.commit()
        return jsonify(res)
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/transactions/<email>', methods=['GET'])
def get_transactions(email):
    # Dummy data for Transaction History
    return jsonify([
        {"id": 1, "item": "Organic Fertilizer", "amount": "₹450", "date": "2024-03-10"},
        {"id": 2, "item": "Tomato Seeds", "amount": "₹120", "date": "2024-03-08"}
    ])

@app.route('/support', methods=['POST'])
def contact_support():
    return jsonify({"message": "Support ticket created. We will contact you soon!"})

# Initialize DB
with app.app_context():
    try:
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS title VARCHAR(100) DEFAULT \'Progressive Farmer\''))
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS location VARCHAR(100) DEFAULT \'Bihar, India\''))
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS land_size VARCHAR(20) DEFAULT \'5 Acres\''))
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS crop_types INTEGER DEFAULT 3'))
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS orders_count INTEGER DEFAULT 12'))
        db.session.commit()
    except Exception: pass
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
