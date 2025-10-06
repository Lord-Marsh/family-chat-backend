from flask_socketio import emit, join_room
from flask import request
from app import socketio, get_db
from app.utils.auth import verify_jwt_token
from bson import ObjectId
from datetime import datetime

# Store connected users
connected_users = {}

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    # Get token from query parameters
    token = request.args.get('token')
    
    if not token:
        return False  # Reject connection
    
    # Verify token
    payload = verify_jwt_token(token)
    if not payload:
        return False  # Reject connection
    
    user_id = payload['user_id']
    
    # Store user's session ID
    connected_users[request.sid] = user_id
    
    # Join user's personal room
    join_room(f'user_{user_id}')
    
    print(f'User {user_id} connected with session {request.sid}')
    emit('connected', {'userId': user_id})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    if request.sid in connected_users:
        user_id = connected_users[request.sid]
        del connected_users[request.sid]
        print(f'User {user_id} disconnected')

@socketio.on('send_message')
def handle_send_message(data):
    """Handle sending a message"""
    if request.sid not in connected_users:
        emit('error', {'message': 'Unauthorized'})
        return
    
    sender_id = connected_users[request.sid]
    receiver_id = data.get('receiverId')
    content = data.get('content')
    
    if not receiver_id or not content:
        emit('error', {'message': 'Receiver ID and content are required'})
        return
    
    try:
        db = get_db()
        
        # Create message document
        message_doc = {
            'sender_id': ObjectId(sender_id),
            'receiver_id': ObjectId(receiver_id),
            'content': content,
            'timestamp': datetime.utcnow()
        }
        
        # Insert message into database
        result = db.messages.insert_one(message_doc)
        message_id = result.inserted_id
        
        # Prepare message response
        message_response = {
            'id': str(message_id),
            'senderId': sender_id,
            'receiverId': receiver_id,
            'content': content,
            'timestamp': message_doc['timestamp'].isoformat()
        }
        
        # Emit to sender
        emit('new_message', message_response, room=f'user_{sender_id}')
        
        # Emit to receiver
        emit('new_message', message_response, room=f'user_{receiver_id}')
        
        print(f'Message sent from {sender_id} to {receiver_id}')
        
    except Exception as e:
        print(f'Error sending message: {str(e)}')
        emit('error', {'message': f'Error sending message: {str(e)}'})

@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicator"""
    if request.sid not in connected_users:
        return
    
    sender_id = connected_users[request.sid]
    receiver_id = data.get('receiverId')
    is_typing = data.get('isTyping', False)
    
    if receiver_id:
        emit('user_typing', {
            'userId': sender_id,
            'isTyping': is_typing
        }, room=f'user_{receiver_id}')