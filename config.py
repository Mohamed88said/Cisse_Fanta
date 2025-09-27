import os
from datetime import datetime, timedelta

class Config:
    """Configuration de base pour l'application Flask"""

    # 🔑 Sécurité
    SECRET_KEY = os.environ.get("SECRET_KEY", "68e60b4d247647f18db672d7b14d85dfdd7a1a69cdeb35144cc7b5563f369e23")

    # 📦 Base de données : Neon.tech PostgreSQL UNIQUEMENT
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")
    
    # 🔥 FORCER PostgreSQL - pas de fallback SQLite
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True
    }

    # ☁️ Configuration Cloudinary
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "djbdv90jr")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "455591489376377")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "xfudLM75vr_yKqrpHVAr87NNhDo")

    # 📂 Gestion des fichiers uploadés (Cloudinary uniquement)
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
    'default': ProductionConfig  # 🔥 Production par défaut
}