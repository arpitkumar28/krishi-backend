import os
import io
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
import tensorflow as tf
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///krishi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class DiseaseReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    disease_name = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.String(10), nullable=False)
    treatment = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- ML MODEL CONFIGURATION ---
MODEL_PATH = 'plant_disease_model.h5'
_model = None

def get_model():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        try:
            _model = tf.keras.models.load_model(MODEL_PATH)
        except Exception as e:
            print(f"Error loading model: {e}")
    return _model

# --- ROUTES ---
@app.route('/')
def home():
    return jsonify({"status": "Online", "message": "Krishi Sahayak AI Backend is Running!"})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').lower().strip()
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists"}), 400
    
    new_user = User(
        name=data.get('name'),
        email=email,
        password_hash=generate_password_hash(data.get('password'))
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').lower().strip()
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, data.get('password')):
        return jsonify({
            "message": "Login successful", 
            "user": {"name": user.name, "email": user.email}
        }), 200
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/predict', methods=['POST'])
def predict():
    # In a real app, you'd process the image here
    # For now, returning dummy data and saving to DB
    user_email = request.form.get('email', 'anonymous@test.com')
    
    # Dummy prediction data
    prediction = {
        'disease_name': 'Tomato Late Blight',
        'confidence': '94%',
        'treatment': 'Apply fungicides containing chlorothalonil or copper. Remove infected leaves.'
    }
    
    new_report = DiseaseReport(
        user_email=user_email,
        disease_name=prediction['disease_name'],
        confidence=prediction['confidence'],
        treatment=prediction['treatment']
    )
    db.session.add(new_report)
    db.session.commit()
    
    return jsonify(prediction)

@app.route('/reports/<email>', methods=['GET'])
def get_reports(email):
    reports = DiseaseReport.query.filter_by(user_email=email).order_by(DiseaseReport.created_at.desc()).all()
    return jsonify([{
        'id': r.id,
        'diseaseName': r.disease_name,
        'confidence': r.confidence,
        'treatment': r.treatment,
        'date': r.created_at.isoformat()
    } for r in reports])

# --- INITIALIZE DATABASE ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
