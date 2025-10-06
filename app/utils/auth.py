import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash

def create_jwt_token(user_id):
    """Create a JWT token for a user"""
    expiration = datetime.datetime.utcnow() + datetime.timedelta(
        hours=current_app.config['JWT_EXPIRATION_HOURS']
    )
    
    payload = {
        'user_id': str(user_id),
        'exp': expiration,
        'iat': datetime.datetime.utcnow()
    }
    
    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET'],
        algorithm='HS256'
    )
    
    return token

def verify_jwt_token(token):
    """Verify a JWT token and return the payload"""
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET'],
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    """Decorator to protect routes with JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'message': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({'message': 'Token is invalid or expired'}), 401
        
        # Add user_id to kwargs
        kwargs['current_user_id'] = payload['user_id']
        return f(*args, **kwargs)
    
    return decorated

def hash_password(password):
    """Hash a password for storing"""
    return generate_password_hash(password)

def verify_password(hashed_password, password):
    """Verify a stored password against a provided password"""
    return check_password_hash(hashed_password, password)