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
    # Explicitly configure the API to use v1beta for better model availability
    genai.configure(api_key=GEMINI_KEY)

@disease_bp.route('/predict', methods=['POST'])
def predict():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
            
        file = request.files['file']
        user_email = request.form.get('email', 'anonymous')
        img = Image.open(file)
        
        if not GEMINI_KEY:
            return jsonify({
                "disease_name": "API Key Missing",
                "confidence": "0%",
                "treatment": "Please set GEMINI_API_KEY in Render."
            }), 200

        # Try multiple model name variants for robustness
        success = False
        res = {}
        # List of models to try in order of preference
        models_to_try = ['gemini-1.5-flash', 'gemini-pro-vision']
        
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                prompt = (
                    "Analyze this plant leaf. If it is a leaf, identify the disease and give treatment. "
                    "Return ONLY JSON: {\"disease_name\": \"...\", \"confidence\": \"...%\", \"treatment\": \"...\"}"
                )
                response = model.generate_content([prompt, img])
                
                # Parse response
                text = response.text.strip()
                if '```json' in text:
                    text = text.split('```json')[1].split('```')[0].strip()
                elif '{' in text:
                    text = text[text.find('{'):text.rfind('}')+1]
                
                res = json.loads(text)
                success = True
                break # Exit loop if successful
            except Exception as e:
                print(f"FAILED with {model_name}: {str(e)}")
                continue

        if not success:
            raise Exception("All Gemini models failed. This usually means the API key lacks access or the library is outdated on the server.")

        # Save to Database
        new_report = DiseaseReport(
            user_email=user_email,
            disease_name=res.get('disease_name', 'Unknown'),
            confidence=res.get('confidence', '0%'),
            treatment=res.get('treatment', 'No treatment info.')
        )
        db.session.add(new_report)
        db.session.commit()
        
        return jsonify(res)

    except Exception as e:
        return jsonify({
            "disease_name": "AI Error",
            "confidence": "0%",
            "treatment": f"Final Error: {str(e)}. Tip: Go to Render Dashboard -> Manual Deploy -> Clear Cache & Deploy."
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
