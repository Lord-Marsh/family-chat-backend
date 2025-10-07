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
    try:
        mongo_uri = app.config['MONGO_URI']
        
        # Parse the database name from URI or use default
        if '/?' in mongo_uri:
            # URI doesn't have database name, extract and add it
            base_uri = mongo_uri.split('/?')[0]
            params = mongo_uri.split('/?')[1]
            mongo_uri = f"{base_uri}/family_chat_db?{params}"
            print(f"Updated MongoDB URI to include database name")
        elif '/' not in mongo_uri.split('@')[-1].split('?')[0]:
            # No database name specified after host
            mongo_uri = mongo_uri.replace('?', '/family_chat_db?')
            print(f"Added database name to MongoDB URI")
        
        mongo_client = MongoClient(mongo_uri)
        
        # Get the database - it will use the one specified in URI
        # or fallback to 'family_chat_db'
        db_name = mongo_uri.split('/')[-1].split('?')[0] or 'family_chat_db'
        db = mongo_client[db_name]
        
        # Test the connection
        mongo_client.server_info()
        print(f"Successfully connected to MongoDB database: {db_name}")
        
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        raise
    
    # Create indexes
    try:
        db.messages.create_index([('sender_id', 1), ('receiver_id', 1), ('timestamp', -1)])
        db.users.create_index('username', unique=True)
        db.users.create_index('email', unique=True)
        print("Database indexes created successfully")
    except Exception as e:
        print(f"Warning: Could not create indexes: {str(e)}")
    
    # Store db in app config for access in routes
    app.db = db
    
    # Initialize SocketIO with threading mode (default)
    # Removed async_mode='eventlet' for Python 3.13 compatibility
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.chat_routes import chat_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    
    # Register socket events
    from app.sockets import chat_events
    
    print("Application initialized successfully")
    
    return app

def get_db():
    """Get database instance"""
    return db
