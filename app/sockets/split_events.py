from flask import request
from flask_socketio import join_room
from app import socketio
from app.utils.auth import verify_jwt_token

@socketio.on('connect')
def handle_connect():
    token = request.args.get('token')
    if not token:
        print('Socket connection rejected: No token')
        return False
        
    payload = verify_jwt_token(token)
    if not payload:
        print('Socket connection rejected: Invalid token')
        return False
        
    user_id = payload['user_id']
    join_room(f'user_{user_id}')
    join_room('splitpay_room')
    print(f'Socket connected successfully! User {user_id} joined splitpay_room')
    
def emit_to_all(event, data):
    socketio.emit(event, data, to='splitpay_room')
