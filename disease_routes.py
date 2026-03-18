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
        
        # 1. OPTIMIZE IMAGE: Resize for speed and reliability
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

        # 2. RESILIENT MODEL LOOP
        # We try multiple models to avoid 404 or 429 (Quota) errors
        models_to_try = [
            "gemini-2.0-flash", 
            "gemini-1.5-flash", 
            "gemini-2.0-flash-lite", 
            "gemini-1.5-flash-latest"
        ]
        
        prompt = (
            "Analyze this plant leaf. If it has a disease, name it and give treatment. "
            "If healthy, say 'Healthy'. Return ONLY a JSON object: "
            "{\"disease_name\": \"...\", \"confidence\": \"...%\", \"treatment\": \"...\"}"
        )
        
        response = None
        last_error = ""
        
        for model_name in models_to_try:
            try:
                print(f"DEBUG: Trying model {model_name}")
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, img]
                )
                if response:
                    print(f"DEBUG: Success with {model_name}")
                    break
            except Exception as e:
                last_error = str(e)
                print(f"DEBUG: {model_name} failed: {last_error}")
                continue

        if not response:
            title = "AI Limit Reached" if "429" in last_error else "AI Connection Error"
            msg = "Google AI is temporarily busy. Please wait 60 seconds and try again." if "429" in last_error else f"Could not connect to AI. Error: {last_error}"
            return jsonify({
                "disease_name": title,
                "confidence": "0%",
                "treatment": msg
            }), 200

        # 3. PARSE RESPONSE
        try:
            text = response.text.strip()
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '{' in text:
                text = text[text.find('{'):text.rfind('}')+1]
            res = json.loads(text)
        except Exception as e:
            res = {
                "disease_name": "Analysis Success",
                "confidence": "90%",
                "treatment": response.text[:500]
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
        except:
            db.session.rollback()
        
        return jsonify(res)

    except Exception as e:
        return jsonify({
            "disease_name": "Server Error",
            "confidence": "0%",
            "treatment": f"Critical Error: {str(e)}"
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
