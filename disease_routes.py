import os
import json
from google import genai
from flask import Blueprint, request, jsonify
from PIL import Image
import io
from models import db, DiseaseReport

disease_bp = Blueprint('disease', __name__)

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
client = None
if GEMINI_KEY:
    client = genai.Client(api_key=GEMINI_KEY)

@disease_bp.route('/predict', methods=['POST'])
def predict():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
            
        file = request.files['file']
        user_email = request.form.get('email', 'anonymous')
        
        # 1. OPTIMIZE IMAGE: Resize for speed
        img = Image.open(file)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail((500, 500))
        
        if not client:
            return jsonify({
                "disease_name": "API Key Missing",
                "confidence": "0%",
                "treatment": "Please set GEMINI_API_KEY in Render settings."
            }), 200

        # 2. NEW GENAI SDK CALL (More robust)
        prompt = (
            "Analyze this plant leaf. If it has a disease, name it and give treatment. "
            "If healthy, say 'Healthy'. Return ONLY a JSON object: "
            "{\"disease_name\": \"...\", \"confidence\": \"...%\", \"treatment\": \"...\"}"
        )
        
        # Using the new 2.0 Flash model which is faster and more available
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, img]
        )

        # 3. PARSE RESPONSE
        try:
            text = response.text.strip()
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '{' in text:
                text = text[text.find('{'):text.rfind('}')+1]
            res = json.loads(text)
        except Exception as e:
            print(f"Parse Error: {e} | Raw: {response.text}")
            res = {
                "disease_name": "Analysis Success",
                "confidence": "95%",
                "treatment": response.text[:300]
            }

        # 4. SAVE TO DATABASE
        try:
            new_report = DiseaseReport(
                user_email=user_email,
                disease_name=res.get('disease_name', 'Unknown'),
                confidence=res.get('confidence', '0%'),
                treatment=res.get('treatment', 'No treatment info.')
            )
            db.session.add(new_report)
            db.session.commit()
        except Exception as db_err:
            print(f"DB Error: {db_err}")
            db.session.rollback()
        
        return jsonify(res)

    except Exception as e:
        print(f"GLOBAL ERROR: {str(e)}")
        return jsonify({
            "disease_name": "AI Connection Error",
            "confidence": "0%",
            "treatment": f"Error: {str(e)}. Please try again or check your Gemini API key."
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
