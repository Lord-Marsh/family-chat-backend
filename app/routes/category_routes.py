from flask import Blueprint, request, jsonify
from app import get_db
from app.utils.auth import token_required

category_bp = Blueprint('categories', __name__)

@category_bp.route('', methods=['GET'])
@token_required
def get_categories(current_user_id):
    db = get_db()
    categories = list(db.categories.find({}))
    
    if not categories:
        # Default presets
        presets = [
            {'_id': 'CAT-001', 'name': 'Food', 'icon': '🍔'},
            {'_id': 'CAT-002', 'name': 'Snacks', 'icon': '🍿'},
            {'_id': 'CAT-003', 'name': 'Groceries', 'icon': '🛒'},
            {'_id': 'CAT-004', 'name': 'Transport', 'icon': '🚗'},
            {'_id': 'CAT-005', 'name': 'Bills', 'icon': '📄'},
            {'_id': 'CAT-006', 'name': 'Recharge', 'icon': '📱'},
            {'_id': 'CAT-007', 'name': 'Other', 'icon': '📦'}
        ]
        db.categories.insert_many(presets)
        categories = presets
        
    return jsonify(categories), 200

@category_bp.route('', methods=['POST'])
@token_required
def create_category(current_user_id):
    db = get_db()
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'message': 'Name is required'}), 400
        
    count = db.categories.count_documents({})
    cat_id = f'CAT-{count + 1:03d}'
    
    new_cat = {
        '_id': cat_id,
        'name': data['name'],
        'icon': data.get('icon', '📌')
    }
    
    db.categories.insert_one(new_cat)
    return jsonify(new_cat), 201
