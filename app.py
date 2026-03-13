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
# Set your Gemini API Key in Render Environment Variables as GEMINI_API_KEY
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
        
        # Load image for Gemini
        img = Image.open(file)
        
        # Call Gemini AI
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """
        Analyze this plant leaf image. Provide the result in JSON format:
        {
          "disease_name": "Name of disease or 'Healthy'",
          "confidence": "Estimated confidence percentage",
          "treatment": "Short recommended treatment"
        }
        Only return the JSON.
        """
        
        response = model.generate_content([prompt, img])
        # Clean the response to ensure it's valid JSON
        json_str = response.text.replace('```json', '').replace('```', '').strip()
        res = json.loads(json_str)
        
        # Save to DB with "Proper Date" (datetime.utcnow)
        new_report = DiseaseReport(
            user_email=user_email, 
            disease_name=res['disease_name'], 
            confidence=res['confidence'], 
            treatment=res['treatment']
        )
        db.session.add(new_report)
        db.session.commit()
        
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"Gemini Error: {str(e)}"}), 500

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

@app.route('/reports/<email>', methods=['GET'])
def get_reports(email):
    reports = DiseaseReport.query.filter_by(user_email=email).order_by(DiseaseReport.created_at.desc()).all()
    return jsonify([{
        'id': r.id, 
        'diseaseName': r.disease_name, 
        'confidence': r.confidence, 
        'treatment': r.treatment, 
        'date': r.created_at.isoformat() # This provides the 'proper date' to your Flutter app
    } for r in reports])

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
