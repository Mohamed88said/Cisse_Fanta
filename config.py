import os
from datetime import timedelta

class Config:
    """Configuration de base pour l'application Flask"""

    # 🔑 Sécurité
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # 📦 Base de données : SQLite en dev, PostgreSQL en prod
    if os.environ.get("RENDER"):  # Sur Render
        database_url = os.environ.get("DATABASE_URL", "")
        if database_url:
            SQLALCHEMY_DATABASE_URI = database_url.replace("postgresql://", "postgresql+psycopg://")
        else:
            raise ValueError("DATABASE_URL manquant sur Render")
    else:  # En local
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(os.getcwd(), 'instance', 'database.db')}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # ☁️ Configuration Cloudinary
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

    # 📂 Gestion des fichiers uploadés
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # 🍪 Configuration des sessions
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'

# Configuration automatique
if os.environ.get("FLASK_ENV") == "production" or os.environ.get("RENDER"):
    config = ProductionConfig
else:
    config = DevelopmentConfig