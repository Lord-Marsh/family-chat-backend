from flask import Flask, g
from flask_cors import CORS
from flask_socketio import SocketIO
from pymongo import MongoClient
import pymongo
from config import config

# Initialize SocketIO
socketio = SocketIO(cors_allowed_origins="*")

# Database client placeholder
mongo_client = None

def get_db():
    if 'db' not in g:
        g.db = mongo_client.get_database('sp')
    return g.db

def create_app(config_name='default'):
    app = Flask(__name__)
    config_obj = config[config_name]()
    app.config.from_object(config_obj)
    
    # Get MONGO_URI from the config instance (it's a @property)
    mongo_uri = config_obj.MONGO_URI
    app.config['MONGO_URI'] = mongo_uri

    # Initialize CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', '*'))

    # Setup MongoDB connection
    global mongo_client
    mongo_client = MongoClient(mongo_uri)
    db = mongo_client.get_database('sp')

    # Run reverse DB migration
    from app.utils.migration import run_migration
    run_migration(db)

    # Setup indexes
    db.users.create_index([("username", pymongo.ASCENDING)], unique=True)
    db.users.create_index([("email", pymongo.ASCENDING)], unique=True)
    db.splits.create_index([("status", pymongo.ASCENDING)])
    db.splits.create_index([("createdAt", pymongo.DESCENDING)])
    db.splits.create_index([("status", pymongo.ASCENDING), ("createdAt", pymongo.DESCENDING)])
    db.login_logs.create_index([("timestamp", pymongo.DESCENDING)])
    db.email_logs.create_index([("timestamp", pymongo.DESCENDING)])
    db.activity_logs.create_index([("timestamp", pymongo.DESCENDING)])

    # Register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.split_routes import split_bp
    from app.routes.balance_routes import balance_bp
    from app.routes.user_routes import user_bp
    from app.routes.log_routes import log_bp
    from app.routes.category_routes import category_bp
    from app.routes.analytics_routes import analytics_bp
    from app.routes.webauthn_routes import webauthn_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(split_bp, url_prefix='/api/splits')
    app.register_blueprint(balance_bp, url_prefix='/api/balances')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(log_bp, url_prefix='/api/logs')
    app.register_blueprint(category_bp, url_prefix='/api/categories')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(webauthn_bp, url_prefix='/api/webauthn')

    # Import socket events
    from app.sockets import split_events

    # Initialize scheduler
    from app.utils.scheduler import init_scheduler
    init_scheduler(app)

    # Initialize extensions
    socketio.init_app(app)

    return app
