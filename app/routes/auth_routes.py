from flask import Blueprint, request, jsonify
from app import get_db
from app.utils.auth import create_jwt_token, verify_password, token_required
from app.utils.id_generator import generate_login_log_id
from datetime import datetime
import pytz

auth_bp = Blueprint('auth', __name__)
IST = pytz.timezone('Asia/Kolkata')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing username or password'}), 400
        
    db = get_db()
    user = db.users.find_one({'username': data.get('username')})
    
    if not user or not verify_password(user.get('password'), data.get('password')):
        # Log failed login
        if user:
            failed_log = {
                '_id': generate_login_log_id(),
                'userId': user['_id'],
                'username': user['username'],
                'displayName': user.get('displayName', user['username']),
                'action': 'login_failed',
                'ipAddress': request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown'),
                'userAgent': request.headers.get('User-Agent', 'unknown'),
                'timestamp': datetime.now(IST)
            }
            db.login_logs.insert_one(failed_log)
        return jsonify({'message': 'Invalid username or password'}), 401
        
    token = create_jwt_token(user['_id'])
    
    # Log successful login
    success_log = {
        '_id': generate_login_log_id(),
        'userId': user['_id'],
        'username': user['username'],
        'displayName': user.get('displayName', user['username']),
        'action': 'login_success',
        'ipAddress': request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown'),
        'userAgent': request.headers.get('User-Agent', 'unknown'),
        'timestamp': datetime.now(IST)
    }
    db.login_logs.insert_one(success_log)
    
    return jsonify({
        'token': token,
        'user': {
            'id': user['_id'],
            'username': user['username'],
            'displayName': user.get('displayName', user['username']),
            'email': user.get('email'),
            'avatar': user.get('avatar'),
            'userType': user.get('userType', 'a'),
            'upiId': user.get('upiId')
        }
    }), 200

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user_id):
    db = get_db()
    user = db.users.find_one({'_id': current_user_id})
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
        
    return jsonify({
        'id': user['_id'],
        'username': user['username'],
        'displayName': user.get('displayName', user['username']),
        'email': user.get('email'),
        'avatar': user.get('avatar'),
        'userType': user.get('userType', 'a'),
        'upiId': user.get('upiId')
    }), 200