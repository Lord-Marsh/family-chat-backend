from flask import Blueprint, jsonify
from app import get_db
from app.utils.auth import token_required

user_bp = Blueprint('users', __name__)

@user_bp.route('', methods=['GET'])
@token_required
def get_users(current_user_id):
    db = get_db()
    users = list(db.users.find({}, {'password': 0}))
    
    # Format the response
    formatted_users = []
    for user in users:
        formatted_users.append({
            'id': user['_id'],
            'username': user.get('username'),
            'displayName': user.get('displayName'),
            'email': user.get('email'),
            'avatar': user.get('avatar'),
            'userType': user.get('userType', 'a'),
            'upiId': user.get('upiId')
        })
        
    return jsonify(formatted_users), 200

@user_bp.route('/me', methods=['PUT'])
@token_required
def update_profile(current_user_id):
    db = get_db()
    data = request.get_json()
    
    updates = {}
    if 'displayName' in data:
        updates['displayName'] = data['displayName']
    if 'upiId' in data:
        updates['upiId'] = data['upiId']
        
    if updates:
        db.users.update_one({'_id': current_user_id}, {'$set': updates})
        
    user = db.users.find_one({'_id': current_user_id})
    return jsonify({
        'id': user['_id'],
        'username': user['username'],
        'displayName': user.get('displayName', user['username']),
        'email': user.get('email'),
        'avatar': user.get('avatar'),
        'userType': user.get('userType', 'a'),
        'upiId': user.get('upiId')
    }), 200
