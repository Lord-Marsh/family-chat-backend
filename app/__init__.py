from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from pymongo import MongoClient
from config import config
import os

# Initialize extensions
socketio = SocketIO(cors_allowed_origins="*")
mongo_client = None
db = None

def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Initialize MongoDB
    global mongo_client, db
    mongo_client = MongoClient(app.config['MONGO_URI'])
    db = mongo_client.get_database()
    
    # Create indexes
    db.messages.create_index([('sender_id', 1), ('receiver_id', 1), ('timestamp', -1)])
    db.users.create_index('username', unique=True)
    db.users.create_index('email', unique=True)
    
    # Store db in app config for access in routes
    app.db = db
    
    # Initialize SocketIO
    socketio.init_app(app, cors_allowed_origins="*", async_mode='eventlet')
    
    # Register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.chat_routes import chat_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    
    # Register socket events
    from app.sockets import chat_events
    
    return app

def get_db():
    """Get database instance"""
    return db