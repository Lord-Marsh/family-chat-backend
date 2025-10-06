from flask import Blueprint, jsonify, current_app
from bson import ObjectId
from app.utils.auth import token_required

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/users', methods=['GET'])
@token_required
def get_users(current_user_id):
    """Get list of all users except current user"""
    db = current_app.db
    
    try:
        # Get all users except the current user
        users = db.users.find({'_id': {'$ne': ObjectId(current_user_id)}})
        print(f"==>> users: {users}")
        
        user_list = []
        for user in users:
            print(f"==>> user: {user}")
            user_info = {
                'id': str(user['_id']),
                'username': user['username'],
                'displayName': user.get('displayName', user['username']),
                'avatar': user.get('avatar', ''),
                'email': user.get('email', '')
            }
            user_list.append(user_info)
        
        print(f"==>> user_list: {user_list}")
        return jsonify(user_list), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching users: {str(e)}'}), 500

@chat_bp.route('/messages/<receiver_id>', methods=['GET'])
@token_required
def get_messages(current_user_id, receiver_id):
    """Get message history between current user and another user"""
    db = current_app.db
    
    try:
        # Validate receiver_id
        receiver_obj_id = ObjectId(receiver_id)
        current_user_obj_id = ObjectId(current_user_id)
        
        # Find all messages between the two users
        messages = db.messages.find({
            '$or': [
                {'sender_id': current_user_obj_id, 'receiver_id': receiver_obj_id},
                {'sender_id': receiver_obj_id, 'receiver_id': current_user_obj_id}
            ]
        }).sort('timestamp', 1)
        
        message_list = []
        for msg in messages:
            message_info = {
                'id': str(msg['_id']),
                'senderId': str(msg['sender_id']),
                'receiverId': str(msg['receiver_id']),
                'content': msg['content'],
                'timestamp': msg['timestamp'].isoformat()
            }
            message_list.append(message_info)
        
        return jsonify(message_list), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching messages: {str(e)}'}), 500