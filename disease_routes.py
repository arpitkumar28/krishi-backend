import os
import json
import google.generativeai as genai
from flask import Blueprint, request, jsonify
from PIL import Image
from models import db, DiseaseReport

disease_bp = Blueprint('disease', __name__)

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

@disease_bp.route('/predict', methods=['POST'])
def predict():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
            
        file = request.files['file']
        user_email = request.form.get('email', 'anonymous')
        img = Image.open(file)
        
        if not GEMINI_KEY or GEMINI_KEY == 'YOUR_API_KEY_HERE':
            return jsonify({
                "disease_name": "Configuration Error",
                "confidence": "0%",
                "treatment": "GEMINI_API_KEY is missing in backend environment variables."
            }), 200

        # AI Analysis
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            "Analyze this plant leaf image. "
            "1. Identify the disease name (or 'Healthy' if no disease). "
            "2. Provide a confidence percentage. "
            "3. Provide a brief treatment recommendation. "
            "Return ONLY a JSON object: "
            "{\"disease_name\": \"...\", \"confidence\": \"...%\", \"treatment\": \"...\"}"
        )
        
        response = model.generate_content([prompt, img])
        
        # Parse JSON strictly
        text_response = response.text.strip()
        if '```json' in text_response:
            text_response = text_response.split('```json')[1].split('```')[0].strip()
        elif '{' in text_response:
            text_response = text_response[text_response.find('{'):text_response.rfind('}')+1]
            
        res = json.loads(text_response)
        
        # Save to Database
        new_report = DiseaseReport(
            user_email=user_email,
            disease_name=res.get('disease_name', 'Unknown'),
            confidence=res.get('confidence', '0%'),
            treatment=res.get('treatment', 'No treatment info available.')
        )
        db.session.add(new_report)
        db.session.commit()
        
        return jsonify(res)

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({
            "disease_name": "AI Error",
            "confidence": "0%",
            "treatment": f"Error: {str(e)}"
        }), 200

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
