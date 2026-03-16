import os
from flask import Flask, jsonify
from flask_cors import CORS
from models import db
from auth_routes import auth_bp
from shop_routes import shop_bp

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
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

# Initialize Database
db.init_app(app)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(shop_bp)

@app.route('/')
def home():
    return jsonify({"status": "Online", "message": "Krishi Sahayak API Backend Running"})

# --- HOME PAGE SECTIONS ---
@app.route('/weather/<location>', methods=['GET'])
def get_weather(location):
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

# Initialize DB Tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
