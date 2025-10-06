from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
from app.utils.auth import create_jwt_token, token_required, hash_password, verify_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login endpoint"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password are required'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    # Find user in database
    db = current_app.db
    user = db.users.find_one({'username': username})
    
    if not user:
        return jsonify({'message': 'Invalid username or password'}), 401
    
    # Verify password
    if not verify_password(user['password'], password):
        return jsonify({'message': 'Invalid username or password'}), 401
    
    # Create JWT token
    token = create_jwt_token(user['_id'])
    
    # Return user info without password
    user_info = {
        'id': str(user['_id']),
        'username': user['username'],
        'email': user['email'],
        'displayName': user.get('displayName', user['username']),
        'avatar': user.get('avatar', '')
    }
    
    return jsonify({
        'token': token,
        'user': user_info
    }), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        return jsonify({'message': 'Username, email, and password are required'}), 400
    
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    display_name = data.get('displayName', username)
    avatar = data.get('avatar', '')
    
    db = current_app.db
    
    # Check if user already exists
    if db.users.find_one({'username': username}):
        return jsonify({'message': 'Username already exists'}), 400
    
    if db.users.find_one({'email': email}):
        return jsonify({'message': 'Email already exists'}), 400
    
    # Hash password
    hashed_password = hash_password(password)
    
    # Create user document
    user_doc = {
        'username': username,
        'password': hashed_password,
        'email': email,
        'displayName': display_name,
        'avatar': avatar
    }
    
    # Insert user
    result = db.users.insert_one(user_doc)
    user_id = result.inserted_id
    
    # Create JWT token
    token = create_jwt_token(user_id)
    
    # Return user info
    user_info = {
        'id': str(user_id),
        'username': username,
        'email': email,
        'displayName': display_name,
        'avatar': avatar
    }
    
    return jsonify({
        'token': token,
        'user': user_info
    }), 201

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user_id):
    """Get current user information"""
    db = current_app.db
    
    try:
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
    except:
        return jsonify({'message': 'Invalid user ID'}), 400
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    user_info = {
        'id': str(user['_id']),
        'username': user['username'],
        'email': user['email'],
        'displayName': user.get('displayName', user['username']),
        'avatar': user.get('avatar', '')
    }
    
    return jsonify(user_info), 200