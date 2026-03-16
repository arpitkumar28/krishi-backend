import os
from flask import Flask, jsonify
from flask_cors import CORS
from models import db
from auth_routes import auth_bp
from shop_routes import shop_bp
from disease_routes import disease_bp
from home_routes import home_bp

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
app.register_blueprint(disease_bp)
app.register_blueprint(home_bp)

@app.route('/')
def home():
    return jsonify({"status": "Online", "message": "Krishi Sahayak API Backend Running"})

# Initialize DB Tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
