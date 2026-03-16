from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__)

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        user = User.query.filter_by(email=data.get('email', '').lower().strip()).first()
        if user and check_password_hash(user.password_hash, data.get('password')):
            return jsonify({"message": "Login successful", "user": {"name": user.name, "email": user.email, "title": user.title, "location": user.location, "land_size": user.land_size, "crop_types": user.crop_types, "orders_count": user.orders_count}}), 200
        return jsonify({"error": "Invalid email or password"}), 401
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        if User.query.filter_by(email=email).first(): return jsonify({"error": "User exists"}), 400
        new_user = User(name=data.get('name'), email=email, password_hash=generate_password_hash(data.get('password')))
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "Registration successful"}), 201
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/profile/<email>', methods=['GET'])
def get_user_profile(email):
    try:
        user = User.query.filter_by(email=email.lower().strip()).first()
        if not user: return jsonify({"error": "User not found"}), 404
        return jsonify({
            "name": user.name,
            "email": user.email,
            "title": user.title,
            "location": user.location,
            "land_size": user.land_size,
            "crop_types": user.crop_types,
            "orders_count": user.orders_count
        }), 200
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/update_profile', methods=['POST'])
def update_profile():
    try:
        data = request.get_json()
        user = User.query.filter_by(email=data.get('email', '').lower().strip()).first()
        if not user: return jsonify({"error": "User not found"}), 404
        user.name = data.get('name', user.name)
        user.title = data.get('title', user.title)
        user.location = data.get('location', user.location)
        user.land_size = data.get('land_size', user.land_size)
        user.crop_types = data.get('crop_types', user.crop_types)
        db.session.commit()
        return jsonify({"message": "Profile updated", "user": {"name": user.name, "email": user.email, "title": user.title, "location": user.location, "land_size": user.land_size, "crop_types": user.crop_types, "orders_count": user.orders_count}}), 200
    except Exception as e: return jsonify({"error": str(e)}), 500
