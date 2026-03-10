import os
import io
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import tensorflow as tf
from datetime import datetime

app = Flask(__name__)
CORS(app) 

# --- CONFIGURATION ---
MODEL_PATH = 'plant_disease_model.h5'
TARGET_SIZE = (128, 128) 

# Optimized model loading for cloud (Inference only)
if os.path.exists(MODEL_PATH):
    model = tf.keras.models.load_model(MODEL_PATH)
else:
    model = None

CLASS_NAMES = [
    'Apple Scab', 'Apple black rot', 'Apple Cedar Rust', 'Apple healthy',
    'Blueberry Healthy', 'Cherry Healthy', 'Cherry powdery Mildew',
    'Corn Gray Leaf Spot', 'Corn Common Rust', 'Corn Healthy', 'Corn Northern Leaf',
    'Grape Black Rot', 'Grape Black Measles', 'Grape Healthy', 'Grape Black Rot',
    'Grape Black Measles', 'Grape Healthy', 'Frape Leaf Blight', 'Orange Haunglongbing',
    'Peach Bacterial Spot', 'Peach Healthy', 'Potato Early Blight', 'Potato Healthy', 
    'Potato Late Blight', 'Raspberry Healthy', 'Soybean Healthy', 'Squash Powdery Mildew',
    'Strawberry Healthy', 'Strawberry Leaf Scorch', 'Tomato Bacterial Spot',
    'Tomato Early Blight', 'Tomato Late Blight', 'Tomato Leaf Mold',
    'Tomato Two Spotted Spider', 'Tomato Mosaic Virus', 'Tomato Yellow Leaf Curl Virus',
    'Tomato Healthy', 'Plant Healthy (Generic)'
]

# --- DETAILED TREATMENT DICTIONARY ---
TREATMENTS = {
    'Apple Scab': 'Apply fungicides like Captan or Mancozeb. Rake and destroy fallen leaves to reduce overwintering spores.',
    'Apple black rot': 'Prune out dead wood and cankers. Apply fungicides like Thiophanate-methyl or Captan during the growing season.',
    'Apple Cedar Rust': 'Remove nearby cedar trees if possible. Use fungicides like Myclobutanil or Triadimefon at the first sign of symptoms.',
    'Cherry powdery Mildew': 'Apply sulfur-based fungicides or Myclobutanil. Ensure good air circulation by pruning.',
    'Corn Gray Leaf Spot': 'Use resistant hybrids. Rotate crops and manage debris. Apply fungicides like Pyraclostrobin if infection is severe.',
    'Corn Common Rust': 'Plant resistant varieties. Fungicides like Azoxystrobin can be used if infection starts early in the season.',
    'Corn Northern Leaf': 'Rotate crops and use resistant hybrids. Fungicides containing Strobilurins or Triazoles are effective.',
    'Grape Black Rot': 'Prune vines to improve airflow. Apply fungicides like Mancozeb or Myclobutanil before and after bloom.',
    'Grape Black Measles': 'Maintain vine health and avoid over-cropping. No specific fungicide treatment is highly effective; focus on cultural practices.',
    'Grape Leaf Blight': 'Apply copper-based fungicides or Mancozeb. Remove and destroy infected leaves.',
    'Frape Leaf Blight': 'Apply copper-based fungicides or Mancozeb. Remove and destroy infected leaves.',
    'Orange Haunglongbing': 'Also known as Citrus Greening. No cure exists. Control the Asian Citrus Psyllid (insect) and remove infected trees.',
    'Peach Bacterial Spot': 'Use resistant varieties. Apply copper-based sprays or Oxytetracycline during the dormant season and early growth.',
    'Potato Early Blight': 'Apply fungicides like Chlorothalonil or Mancozeb. Rotate crops with non-solanaceous plants.',
    'Potato Late Blight': 'Very serious. Use fungicides like Ridomil Gold or Copper sprays. Destroy infected plants immediately to prevent spread.',
    'Squash Powdery Mildew': 'Apply neem oil, potassium bicarbonate, or fungicides like Myclobutanil. Improve spacing for better air circulation.',
    'Strawberry Leaf Scorch': 'Use resistant cultivars. Apply fungicides like Captan or Thiophanate-methyl during wet weather.',
    'Tomato Bacterial Spot': 'Apply copper-based bactericides mixed with Mancozeb. Avoid overhead irrigation and handle plants only when dry.',
    'Tomato Early Blight': 'Remove lower leaves to prevent soil splash. Use fungicides like Chlorothalonil or Mancozeb. Rotate crops yearly.',
    'Tomato Late Blight': 'Apply fungicides like Mancozeb or Ridomil Gold. Ensure proper air circulation and destroy infected plants.',
    'Tomato Leaf Mold': 'Improve greenhouse ventilation. Apply fungicides like Chlorothalonil or Copper-based sprays.',
    'Tomato Two Spotted Spider': 'Use insecticidal soap, neem oil, or miticides like Abamectin. Increase humidity around the plants.',
    'Tomato Mosaic Virus': 'No cure. Use certified virus-free seeds. Remove infected plants and wash hands/tools after handling them.',
    'Tomato Yellow Leaf Curl Virus': 'Control whiteflies using insecticides or neem oil. Use resistant varieties and reflective mulches.',
    'healthy': 'The plant appears healthy! Maintain regular watering, fertilization, and monitoring for any new symptoms.',
    'Healthy': 'The plant appears healthy! Maintain regular watering, fertilization, and monitoring for any new symptoms.',
}

@app.route('/predict', methods=['POST'])
def predict():
    if model is None: return jsonify({'error': 'Model not loaded'}), 500
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    
    try:
        file = request.files['file']
        img = Image.open(io.BytesIO(file.read())).convert('RGB').resize(TARGET_SIZE)
        img_array = np.expand_dims(np.array(img) / 255.0, axis=0)

        predictions = model.predict(img_array)
        result_idx = np.argmax(predictions[0])
        
        if result_idx >= len(CLASS_NAMES):
            disease_name = "Unknown Plant Condition"
        else:
            disease_name = CLASS_NAMES[result_idx]

        confidence = float(np.max(predictions[0]))

        # Dynamic Treatment Lookup
        treatment = "Consult an agricultural expert for detailed diagnosis and treatment."
        for key in TREATMENTS:
            if key in disease_name:
                treatment = TREATMENTS[key]
                break

        return jsonify({
            'class': disease_name,
            'confidence': f"{confidence * 100:.1f}%",
            'treatment': treatment,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
