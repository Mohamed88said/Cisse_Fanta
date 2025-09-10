import os
from datetime import timedelta

class Config:
    """Configuration de base"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Base de données (SQLite en dev, PostgreSQL/MySQL en prod via DATABASE_URL)
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'instance/database.db'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Configuration de session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # HTTP autorisé en dev

class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True   # HTTPS obligatoire en prod
    PREFERRED_URL_SCHEME = 'https'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
