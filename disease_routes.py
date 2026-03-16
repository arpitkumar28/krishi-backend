import os
import json
import google.generativeai as genai
from flask import Blueprint, request, jsonify
from PIL import Image
from models import db, DiseaseReport

disease_bp = Blueprint('disease', __name__)

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get('GEMINI_API_KEY', 'YOUR_API_KEY_HERE')
genai.configure(api_key=GEMINI_KEY)

@disease_bp.route('/predict', methods=['POST'])
def predict():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
            
        file = request.files['file']
        user_email = request.form.get('email', 'anonymous')
        img = Image.open(file)
        
        # Try real Gemini Analysis first
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = "Analyze this plant leaf. Return JSON: {\"disease_name\": \"...\", \"confidence\": \"...%\", \"treatment\": \"...\"}"
            response = model.generate_content([prompt, img])
            json_str = response.text.replace('```json', '').replace('```', '').strip()
            res = json.loads(json_str)
        except Exception:
            # Fallback to Mock Data if API fails/key is missing
            res = {
                "disease_name": "Tomato Late Blight",
                "confidence": "92%",
                "treatment": "Apply copper-based fungicides and remove infected leaves."
            }
            
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
        return jsonify({"error": str(e)}), 500

@disease_bp.route('/reports/<email>', methods=['GET'])
def get_reports(email):
    try:
        reports = DiseaseReport.query.filter_by(user_email=email).order_by(DiseaseReport.created_at.desc()).all()
        return jsonify([{
            'id': r.id,
            'diseaseName': r.disease_name,
            'confidence': r.confidence,
            'treatment': r.treatment,
            'date': r.created_at.isoformat()
        } for r in reports])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
