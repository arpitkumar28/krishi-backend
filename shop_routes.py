from flask import Blueprint, request, jsonify
from models import db, CartItem

shop_bp = Blueprint('shop', __name__)

PRODUCTS = [
    {"id": 1, "name": "Mancozeb Fungicide", "category": "Fungicide", "price": "₹450", "image": "https://placehold.co/100"},
    {"id": 2, "name": "Neem Oil (Organic)", "category": "Pesticide", "price": "₹280", "image": "https://placehold.co/100"},
    {"id": 3, "name": "NPK Fertilizer", "category": "Fertilizer", "price": "₹1,200", "image": "https://placehold.co/100"},
    {"id": 4, "name": "Urea (Bag)", "category": "Fertilizer", "price": "₹266", "image": "https://placehold.co/100"},
    {"id": 5, "name": "Copper Fungicide", "category": "Fungicide", "price": "₹380", "image": "https://placehold.co/100"},
    {"id": 6, "name": "Hybrid Maize Seeds", "category": "Seed", "price": "₹550", "image": "https://placehold.co/100"}
]

@shop_bp.route('/agri-store', methods=['GET'])
def get_store_items():
    category = request.args.get('category', 'All')
    if category != 'All' and category != 'All Products':
        filtered = [p for p in PRODUCTS if p['category'].lower() == category.lower()]
        return jsonify(filtered)
    return jsonify(PRODUCTS)

@shop_bp.route('/cart/add', methods=['POST'])
def add_to_cart():
    try:
        data = request.get_json()
        user_email = data.get('email')
        product_id = data.get('product_id')
        
        if not user_email or not product_id:
            return jsonify({"error": "Missing email or product_id"}), 400
            
        product = next((p for p in PRODUCTS if p['id'] == product_id), None)
        if not product:
            return jsonify({"error": "Product not found"}), 404
            
        # Check if item already exists in cart for this user
        existing_item = CartItem.query.filter_by(user_email=user_email, product_id=product_id).first()
        if existing_item:
            existing_item.quantity += 1
        else:
            new_item = CartItem(
                user_email=user_email,
                product_id=product['id'],
                product_name=product['name'],
                price=product['price'],
                category=product['category'],
                image=product['image'],
                quantity=1
            )
            db.session.add(new_item)
            
        db.session.commit()
        return jsonify({"message": "Added to cart successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@shop_bp.route('/cart/<email>', methods=['GET'])
def get_cart(email):
    try:
        items = CartItem.query.filter_by(user_email=email).all()
        return jsonify([{
            "id": i.id,
            "product_id": i.product_id,
            "name": i.product_name,
            "price": i.price,
            "quantity": i.quantity,
            "category": i.category,
            "image": i.image
        } for i in items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@shop_bp.route('/cart/remove', methods=['POST'])
def remove_from_cart():
    try:
        data = request.get_json()
        item_id = data.get('cart_item_id')
        item = CartItem.query.get(item_id)
        if item:
            db.session.delete(item)
            db.session.commit()
            return jsonify({"message": "Item removed"}), 200
        return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
