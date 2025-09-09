import os
from datetime import timedelta

class Config:
    """Configuration de base"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'instance/database.db'
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Configuration de session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True  # HTTPS uniquement en production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # HTTP autorisé en dev

class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    
    # Sécurité renforcée en production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PREFERRED_URL_SCHEME = 'https'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}