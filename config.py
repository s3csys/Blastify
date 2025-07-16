"""Application configuration."""

import os
import logging
from dotenv import load_dotenv, find_dotenv, set_key

# Load environment variables from .env file
load_dotenv(override=True)

class Config:
    """Base configuration class."""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    FLASK_HOST = os.environ.get('FLASK_HOST') or '0.0.0.0'
    FLASK_PORT = int(os.environ.get('FLASK_PORT') or 6000)
    
    # Upload folder configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    
    # Database configuration
    DATABASE_ENCRYPTION_KEY = os.environ.get('DATABASE_ENCRYPTION_KEY') or 'default-encryption-key-change-in-production'
    # Use a simpler SQLite connection without encryption for development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Celery configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'
    
    # Administrator account configuration
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'your_secure_password'
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@example.com'
    
    # Logging configuration
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_DIR = os.environ.get('LOG_DIR') or 'logs'
    ACCESS_LOG = os.environ.get('ACCESS_LOG') or 'access.log'
    ERROR_LOG = os.environ.get('ERROR_LOG') or 'error.log'
    APP_LOG = os.environ.get('APP_LOG') or 'app.log'
    LOG_FORMAT = os.environ.get('LOG_FORMAT') or '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_DATE_FORMAT = os.environ.get('LOG_DATE_FORMAT') or '%Y-%m-%d %H:%M:%S'
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES') or 10485760)  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT') or 5)
    
    # Development settings
    DEBUG_MODE = os.environ.get('DEBUG_MODE', 'True').lower() in ('true', 'yes', '1', 't')
    
    # API rate limiting
    RATELIMIT_DEFAULT = '100/hour'
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'

class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True

class TestingConfig(Config):
    """Testing configuration."""
    
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'

class ProductionConfig(Config):
    """Production configuration."""
    
    # Production-specific settings
    # Google OAuth configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')