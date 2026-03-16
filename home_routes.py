from flask import Blueprint, jsonify

home_bp = Blueprint('home_page', __name__)

@home_bp.route('/weather/<location>', methods=['GET'])
def get_weather(location):
    return jsonify({
        "location": location or "Patna, Bihar",
        "temperature": 29.0,
        "condition": "Partly Cloudy",
        "advice": "Ideal weather for field work!"
    })

@home_bp.route('/market-prices', methods=['GET'])
def get_market_prices():
    return jsonify([
        {"name": "Wheat", "category": "Grains", "price": "₹2,100", "unit": "quintal"},
        {"name": "Tomato", "category": "Vegetables", "price": "₹1,800", "unit": "quintal"},
        {"name": "Potato", "category": "Vegetables", "price": "₹1,200", "unit": "quintal"},
        {"name": "Mustard", "category": "Oilseeds", "price": "₹5,400", "unit": "quintal"},
        {"name": "Rice", "category": "Grains", "price": "₹3,200", "unit": "quintal"}
    ])

@home_bp.route('/community/posts', methods=['GET'])
def get_community_posts():
    return jsonify([
        {"id": 1, "author": "Rajesh Kumar", "content": "My tomato crops are doing great this season thanks to the new irrigation tech!", "likes": 24},
        {"id": 2, "author": "Amit Singh", "content": "Anyone else seeing yellowing of leaves in wheat?", "likes": 12}
    ])

@home_bp.route('/weather/alerts', methods=['GET'])
def get_weather_alerts():
    return jsonify([
        {"id": 1, "type": "Warning", "message": "Heavy rain expected in 48 hours. Secure your harvests."},
        {"id": 2, "type": "Info", "message": "Temperature set to rise next week. Increase irrigation frequency."}
    ])
