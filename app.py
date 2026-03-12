import os
import io
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
    image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- ML MODEL CONFIGURATION ---
MODEL_PATH = 'plant_disease_model.h5'
_model = None

CLASS_NAMES = [
    "Apple Scab", "Apple Black Rot", "Cedar Apple Rust", "Apple Healthy",
    "Blueberry Healthy", "Cherry Powdery Mildew", "Cherry Healthy",
    "Corn Gray Leaf Spot", "Corn Common Rust", "Corn Northern Leaf Blight", "Corn Healthy",
    "Grape Black Rot", "Grape Esca", "Grape Leaf Blight", "Grape Healthy",
    "Orange Haunglongbing", "Peach Bacterial Spot", "Peach Healthy",
    "Pepper Bell Bacterial Spot", "Pepper Bell Healthy",
    "Potato Early Blight", "Potato Late Blight", "Potato Healthy",
    "Raspberry Healthy", "Soybean Healthy", "Squash Powdery Mildew",
    "Strawberry Leaf Scorch", "Strawberry Healthy",
    "Tomato Bacterial Spot", "Tomato Early Blight", "Tomato Late Blight",
    "Tomato Leaf Mold", "Tomato Septoria Leaf Spot", "Tomato Spider Mites",
    "Tomato Target Spot", "Tomato Yellow Leaf Curl Virus", "Tomato Mosaic Virus", "Tomato Healthy"
]

TREATMENTS = {
    "Tomato Late Blight": "Use fungicides containing chlorothalonil or copper. Avoid overhead watering.",
    "Potato Early Blight": "Apply mancozeb or chlorothalonil. Rotate crops and remove infected plant debris.",
    "Apple Scab": "Apply sulfur-based fungicides. Prune trees to improve air circulation.",
    "Grape Black Rot": "Prune out infected fruit and vines. Apply captan or myclobutanil fungicides.",
    "Corn Common Rust": "Usually doesn't require treatment, but resistant hybrids are recommended."
}

def get_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            try:
                print(f"Loading model from {MODEL_PATH}...")
                import tensorflow as tf
                # Optimization for limited RAM
                _model = tf.keras.models.load_model(MODEL_PATH, compile=False)
                print("Model loaded successfully!")
            except Exception as e:
                print(f"ERROR loading model: {e}")
        else:
            print(f"WARNING: {MODEL_PATH} not found!")
    return _model

def preprocess_image(image_bytes, target_size=(256, 256)):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert('RGB')
        img = img.resize(target_size)
        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0).astype(np.float32)
        return img_array
    except Exception as e:
        print(f"Preprocessing error: {e}")
        return None

# --- ROUTES ---
@app.route('/')
def home():
    return jsonify({"status": "Online", "message": "Krishi Sahayak API is running!"})

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        name = data.get('name')
        password = data.get('password')
        if not email or not name or not password: return jsonify({"error": "Missing fields"}), 400
        if User.query.filter_by(email=email).first(): return jsonify({"error": "User already exists"}), 400
        new_user = User(name=name, email=email, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "Registration successful"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        password = data.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            return jsonify({
                "message": "Login successful", 
                "user": {
                    "name": user.name, "email": user.email, "title": user.title,
                    "location": user.location, "land_size": user.land_size,
                    "crop_types": user.crop_types, "orders_count": user.orders_count
                }
            }), 200
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/profile/<email>', methods=['GET'])
def get_profile(email):
    user = User.query.filter_by(email=email.lower().strip()).first()
    if not user: return jsonify({"error": "User not found"}), 404
    return jsonify({
        "name": user.name, "email": user.email, "title": user.title,
        "location": user.location, "land_size": user.land_size,
        "crop_types": user.crop_types, "orders_count": user.orders_count
    })

@app.route('/update_profile', methods=['POST'])
def update_profile():
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        user = User.query.filter_by(email=email).first()
        if not user: return jsonify({"error": "User not found"}), 404
        user.name = data.get('name', user.name)
        user.title = data.get('title', user.title)
        user.location = data.get('location', user.location)
        user.land_size = data.get('land_size', user.land_size)
        user.crop_types = data.get('crop_types', user.crop_types)
        db.session.commit()
        return jsonify({"message": "Profile updated", "user": {
            "name": user.name, "email": user.email, "title": user.title,
            "location": user.location, "land_size": user.land_size,
            "crop_types": user.crop_types, "orders_count": user.orders_count
        }}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        user_email = request.form.get('email', 'anonymous')
        
        model = get_model()
        if model is None:
            return jsonify({"error": "Model failed to load on server (RAM limit?)"}), 500

        img_array = preprocess_image(file.read())
        if img_array is None:
            return jsonify({"error": "Invalid image format"}), 400

        predictions = model.predict(img_array)
        class_idx = np.argmax(predictions[0])
        confidence = float(np.max(predictions[0]))
        
        disease_name = CLASS_NAMES[class_idx] if class_idx < len(CLASS_NAMES) else "Unknown"
        treatment = TREATMENTS.get(disease_name, "Consult an expert.")

        new_report = DiseaseReport(
            user_email=user_email, disease_name=disease_name,
            confidence=f"{confidence*100:.1f}%", treatment=treatment
        )
        db.session.add(new_report)
        db.session.commit()

        return jsonify({"disease_name": disease_name, "confidence": f"{confidence*100:.1f}%", "treatment": treatment})
    except Exception as e:
        print(f"Prediction logic error: {e}")
        return jsonify({"error": f"Server processing error: {str(e)}"}), 500

@app.route('/reports/<email>', methods=['GET'])
def get_reports(email):
    reports = DiseaseReport.query.filter_by(user_email=email).order_by(DiseaseReport.created_at.desc()).all()
    return jsonify([{'id': r.id, 'diseaseName': r.disease_name, 'confidence': r.confidence, 
                     'treatment': r.treatment, 'date': r.created_at.isoformat()} for r in reports])

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
