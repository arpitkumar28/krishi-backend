import os
import io
import json
import google.generativeai as genai
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
GEMINI_KEY = os.environ.get('GEMINI_API_KEY', 'YOUR_API_KEY_HERE')
genai.configure(api_key=GEMINI_KEY)

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

# --- ROUTES ---
@app.route('/')
def home():
    return jsonify({"status": "Online", "message": "Krishi Sahayak AI Backend Running"})

@app.route('/predict', methods=['POST'])
def predict():
    try:
        if 'file' not in request.files: return jsonify({"error": "No file"}), 400
        file = request.files['file']
        user_email = request.form.get('email', 'anonymous')
        img = Image.open(file)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = "Analyze this plant leaf. Return JSON: {\"disease_name\": \"...\", \"confidence\": \"...%\", \"treatment\": \"...\"}"
        response = model.generate_content([prompt, img])
        json_str = response.text.replace('```json', '').replace('```', '').strip()
        res = json.loads(json_str)
        new_report = DiseaseReport(user_email=user_email, disease_name=res['disease_name'], confidence=res['confidence'], treatment=res['treatment'])
        db.session.add(new_report)
        db.session.commit()
        return jsonify(res)
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        user = User.query.filter_by(email=data.get('email', '').lower().strip()).first()
        if user and check_password_hash(user.password_hash, data.get('password')):
            return jsonify({"message": "Login successful", "user": {"name": user.name, "email": user.email, "title": user.title, "location": user.location, "land_size": user.land_size, "crop_types": user.crop_types, "orders_count": user.orders_count}}), 200
        return jsonify({"error": "Invalid email or password"}), 401
    except Exception as e: return jsonify({"error": str(e)}), 500

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

# --- HOME PAGE SECTIONS ---

@app.route('/weather/<location>', methods=['GET'])
def get_weather(location):
    # In a real app, this would call a Weather API
    return jsonify({
        "location": location or "Patna, Bihar",
        "temperature": 29.0,
        "condition": "Partly Cloudy",
        "advice": "Ideal weather for field work!"
    })

@app.route('/market-prices', methods=['GET'])
def get_market_prices():
    return jsonify([
        {"name": "Wheat", "category": "Grains", "price": "₹2,100", "unit": "quintal"},
        {"name": "Tomato", "category": "Vegetables", "price": "₹1,800", "unit": "quintal"},
        {"name": "Potato", "category": "Vegetables", "price": "₹1,200", "unit": "quintal"},
        {"name": "Mustard", "category": "Oilseeds", "price": "₹5,400", "unit": "quintal"},
        {"name": "Rice", "category": "Grains", "price": "₹3,200", "unit": "quintal"}
    ])

@app.route('/agri-store', methods=['GET'])
def get_store_items():
    category = request.args.get('category', 'All')
    products = [
        {"id": 1, "name": "Mancozeb Fungicide", "category": "Fungicide", "price": "₹450", "image": "https://placehold.co/100"},
        {"id": 2, "name": "Neem Oil (Organic)", "category": "Pesticide", "price": "₹280", "image": "https://placehold.co/100"},
        {"id": 3, "name": "NPK Fertilizer", "category": "Fertilizer", "price": "₹1,200", "image": "https://placehold.co/100"},
        {"id": 4, "name": "Urea (Bag)", "category": "Fertilizer", "price": "₹266", "image": "https://placehold.co/100"},
        {"id": 5, "name": "Copper Fungicide", "category": "Fungicide", "price": "₹380", "image": "https://placehold.co/100"},
        {"id": 6, "name": "Hybrid Maize Seeds", "category": "Seed", "price": "₹550", "image": "https://placehold.co/100"}
    ]
    
    if category != 'All' and category != 'All Products':
        products = [p for p in products if p['category'].lower() == category.lower()]
        
    return jsonify(products)

@app.route('/community/posts', methods=['GET'])
def get_community_posts():
    return jsonify([
        {"id": 1, "author": "Rajesh Kumar", "content": "My tomato crops are doing great this season thanks to the new irrigation tech!", "likes": 24},
        {"id": 2, "author": "Amit Singh", "content": "Anyone else seeing yellowing of leaves in wheat?", "likes": 12}
    ])

@app.route('/weather/alerts', methods=['GET'])
def get_weather_alerts():
    return jsonify([
        {"id": 1, "type": "Warning", "message": "Heavy rain expected in 48 hours. Secure your harvests."},
        {"id": 2, "type": "Info", "message": "Temperature set to rise next week. Increase irrigation frequency."}
    ])

# --- PROFILE DATA ---

@app.route('/crops/<email>', methods=['GET'])
def get_crops(email):
    return jsonify([
        {"name": "Tomato", "area": "2.5 Acres", "status": "Healthy"},
        {"name": "Potato", "area": "1.5 Acres", "status": "Needs Care"}
    ])

@app.route('/transactions/<email>', methods=['GET'])
def get_transactions(email):
    return jsonify([
        {"id": 1, "item": "Organic NPK", "amount": "₹1,250", "date": "Mar 12, 2024"},
        {"id": 2, "item": "Hybrid Seeds", "amount": "₹450", "date": "Mar 05, 2024"}
    ])

@app.route('/reports/<email>', methods=['GET'])
def get_reports(email):
    reports = DiseaseReport.query.filter_by(user_email=email).order_by(DiseaseReport.created_at.desc()).all()
    return jsonify([{'id': r.id, 'diseaseName': r.disease_name, 'confidence': r.confidence, 'treatment': r.treatment, 'date': r.created_at.isoformat()} for r in reports])

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
