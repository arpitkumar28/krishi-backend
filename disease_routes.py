import os
import json
import time
from google import genai
from flask import Blueprint, request, jsonify
from PIL import Image
from models import db, DiseaseReport

disease_bp = Blueprint('disease', __name__)

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
client = None
if GEMINI_KEY:
    # Explicitly use the stable API version
    client = genai.Client(api_key=GEMINI_KEY, http_options={'api_version': 'v1'})

@disease_bp.route('/predict', methods=['POST'])
def predict():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
            
        file = request.files['file']
        user_email = request.form.get('email', 'anonymous')
        
        img = Image.open(file)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail((500, 500))
        
        if not client:
            return jsonify({"disease_name": "Error", "confidence": "0%", "treatment": "API Key Missing"}), 200

        # Try models with their full resource names to avoid 404
        models_to_try = ["gemini-1.5-flash", "gemini-2.0-flash"]
        
        prompt = (
            "Analyze this plant leaf. Identify the disease and give treatment. "
            "Return ONLY JSON: {\"disease_name\": \"...\", \"confidence\": \"...%\", \"treatment\": \"...\"}"
        )
        
        response = None
        last_error = ""
        
        for model_id in models_to_try:
            try:
                # Add a tiny delay to help with rate limits
                time.sleep(1)
                response = client.models.generate_content(
                    model=model_id,
                    contents=[prompt, img]
                )
                if response:
                    break
            except Exception as e:
                last_error = str(e)
                if "429" in last_error:
                    # If quota hit, wait a bit longer and try the next one
                    time.sleep(2)
                continue

        if not response:
            if "429" in last_error:
                return jsonify({
                    "disease_name": "AI is Busy",
                    "confidence": "0%",
                    "treatment": "You've reached the free limit. Please wait 1 minute and try again."
                }), 200
            return jsonify({
                "disease_name": "AI Connection Error",
                "confidence": "0%",
                "treatment": f"Could not connect. Error: {last_error}"
            }), 200

        # Parse JSON
        try:
            text = response.text.strip()
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '{' in text:
                text = text[text.find('{'):text.rfind('}')+1]
            res = json.loads(text)
        except:
            res = {"disease_name": "Healthy / Unknown", "confidence": "70%", "treatment": response.text[:200]}

        # Save to DB
        try:
            new_report = DiseaseReport(
                user_email=user_email,
                disease_name=res.get('disease_name', 'Unknown'),
                confidence=res.get('confidence', '0%'),
                treatment=res.get('treatment', 'No treatment info.')
            )
            db.session.add(new_report)
            db.session.commit()
        except:
            db.session.rollback()
        
        return jsonify(res)

    except Exception as e:
        return jsonify({"disease_name": "Error", "confidence": "0%", "treatment": str(e)}), 200

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
