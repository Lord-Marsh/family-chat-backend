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
            'userType': user.get('userType', 'a')
        })
        
    return jsonify(formatted_users), 200
