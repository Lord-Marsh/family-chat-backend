import os
from app import create_app, socketio

# Get environment configuration
config_name = os.getenv('FLASK_ENV', 'local')
app = create_app(config_name)

if __name__ == '__main__':
    # Run with SocketIO
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )