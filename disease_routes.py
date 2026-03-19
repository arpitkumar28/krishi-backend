import os
import json
from google import genai
from google.genai import types
from flask import Blueprint, request, jsonify
from PIL import Image
from models import db, DiseaseReport

disease_bp = Blueprint('disease', __name__)

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
client = None
if GEMINI_KEY:
    client = genai.Client(api_key=GEMINI_KEY)

def get_stable_model():
    """
    Returns the model ID. 
    If 'gemini-1.5-flash' fails, 'gemini-1.5-pro' is a great alternative.
    'gemini-2.0-flash-exp' is also available and very fast.
    """
    return "gemini-1.5-flash" # Primary model

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
        img.thumbnail((800, 800))
        
        if not client:
            return jsonify({"disease_name": "Error", "confidence": "0%", "treatment": "API Key Missing"}), 200

        # Try with Flash first, then fallback to Pro if there's a 404
        model_to_use = "gemini-1.5-flash"
        
        try:
            return run_inference(model_to_use, img, user_email)
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                print(f"Flash model not found, falling back to Pro...")
                return run_inference("gemini-1.5-pro", img, user_email)
            raise e

    except Exception as e:
        err_msg = str(e)
        print(f"ERROR: {err_msg}")
        if "429" in err_msg:
            return jsonify({
                "disease_name": "AI is Overloaded",
                "confidence": "0%",
                "treatment": "The free limit is reached. Please wait 1 minute."
            }), 200
            
        return jsonify({
            "disease_name": "AI Connection Error",
            "confidence": "0%",
            "treatment": f"Could not analyze image. Error: {err_msg}"
        }), 200

def run_inference(model_id, img, user_email):
    response = client.models.generate_content(
        model=model_id,
        contents=[
            "Analyze this plant leaf. If it has a disease, identify it and give a treatment plan. If healthy, say 'Healthy'. Return the result in JSON format.",
            img
        ],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema={
                'type': 'OBJECT',
                'properties': {
                    'disease_name': {'type': 'STRING'},
                    'confidence': {'type': 'STRING'},
                    'treatment': {'type': 'STRING'}
                },
                'required': ['disease_name', 'confidence', 'treatment']
            }
        )
    )

    res = json.loads(response.text)
    
    # Save to Database
    try:
        new_report = DiseaseReport(
            user_email=user_email,
            disease_name=res.get('disease_name', 'Unknown'),
            confidence=res.get('confidence', '0%'),
            treatment=res.get('treatment', 'No treatment info available.')
        )
        db.session.add(new_report)
        db.session.commit()
    except Exception as db_err:
        print(f"DB Error: {db_err}")
        db.session.rollback()
    
    return jsonify(res)

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
