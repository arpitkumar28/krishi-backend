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
secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SECRET_KEY'] = secret_key

uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

db_uri = uri or 'sqlite:///krishi.db'
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Print startup info for Render logs
print("----------------------------------------")
print(f"Server starting at {datetime.now()}")
print(f"Database type: {'PostgreSQL' if uri else 'SQLite (Local Dev)'}")
if not uri:
    print("WARNING: DATABASE_URL not found. Using local SQLite.")
print("----------------------------------------")

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
    if _model is None:
        if os.path.exists(MODEL_PATH):
            try:
                print(f"Loading model from {MODEL_PATH}...")
                _model = tf.keras.models.load_model(MODEL_PATH)
                print("Model loaded successfully!")
            except Exception as e:
                print(f"ERROR: Could not load model: {e}")
        else:
            print(f"WARNING: Model file {MODEL_PATH} not found!")
    return _model

# --- ROUTES ---
@app.route('/')
def home():
    return jsonify({"status": "Online", "message": "Krishi Sahayak AI Backend is Running!"})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').lower().strip()
    print(f"Register attempt for: {email}")
    
    if User.query.filter_by(email=email).first():
        print(f"Register failed: User {email} already exists")
        return jsonify({"error": "User already exists"}), 400
    
    new_user = User(
        name=data.get('name'),
        email=email,
        password_hash=generate_password_hash(data.get('password'))
    )
    db.session.add(new_user)
    db.session.commit()
    print(f"User {email} registered successfully.")
    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').lower().strip()
    print(f"Login attempt: {email}")
    
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, data.get('password')):
        print(f"Login successful: {email}")
        return jsonify({
            "message": "Login successful", 
            "user": {"name": user.name, "email": user.email}
        }), 200
    
    print(f"Login failed: {email}")
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/predict', methods=['POST'])
def predict():
    user_email = request.form.get('email', 'anonymous@test.com')
    print(f"Prediction requested by: {user_email}")
    
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
    print(f"Prediction saved for {user_email}: {prediction['disease_name']}")
    
    return jsonify(prediction)

@app.route('/reports/<email>', methods=['GET'])
def get_reports(email):
    print(f"Fetching reports for: {email}")
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
    print("Ensuring database tables exist...")
    db.create_all()
    print("Database initialization complete.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
