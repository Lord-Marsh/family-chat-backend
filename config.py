import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET = os.getenv('JWT_SECRET', 'jwt-secret-key-change-in-production')
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
    
    # SMTP Configuration
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_EMAIL = os.getenv('SMTP_EMAIL', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')

    # Production toggle: set PRODUCTION=true in .env to use Atlas, false for local MongoDB
    PRODUCTION = os.getenv('PRODUCTION', 'false').lower() == 'true'

    @property
    def MONGO_URI(self):
        if self.PRODUCTION:
            return os.getenv('MONGO_URI_PRODUCTION', 'mongodb+srv://localhost/sp')
        else:
            return os.getenv('MONGO_URI_LOCAL', 'mongodb://localhost:27017/sp')

class LocalConfig(Config):
    """Local development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    @property
    def CORS_ORIGINS(self):
        # Default to allow all in production if not explicitly set, to prevent instant blocking on Render
        return os.getenv('CORS_ORIGINS', '*').split(',')

# Configuration dictionary
config = {
    'local': LocalConfig,
    'production': ProductionConfig,
    'default': LocalConfig
}
