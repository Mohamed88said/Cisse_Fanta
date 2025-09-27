import os
from datetime import datetime, timedelta

class Config:
    """Configuration de base pour l'application Flask"""

    # 🔑 Sécurité
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # 📦 Base de données : Neon.tech PostgreSQL
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    if DATABASE_URL:
        # Pour Neon.tech - conversion automatique si nécessaire
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Fallback SQLite en développement
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(os.getcwd(), 'instance', 'database.db')}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True
    }

    # ☁️ Configuration Cloudinary
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "djbdv90jr")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "455591489376377")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "xfudLM75vr_yKqrpHVAr87NNhDo")

    # 📂 Gestion des fichiers uploadés
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # 🍪 Configuration des sessions
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # 🔒 Date de déverrouillage
    UNLOCK_DATE = datetime(2025, 9, 26, 23, 0, 59)

class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}