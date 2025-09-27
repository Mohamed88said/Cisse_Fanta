from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    favorite_color = db.Column(db.String(20), default='#ffdde1')
    visit_count = db.Column(db.Integer, default=0)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Phrase(db.Model):
    __tablename__ = 'phrases'
    
    id = db.Column(db.Integer, primary_key=True)
    texte = db.Column(db.Text, nullable=False)
    auteur = db.Column(db.String(80), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    couleur = db.Column(db.String(20), default='#ffdde1')
    tags = db.Column(db.Text)
    est_favori = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)
    is_special = db.Column(db.Boolean, default=False)

class Photo(db.Model):
    __tablename__ = 'photos'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    cloudinary_url = db.Column(db.Text)  # Nouveau champ pour Cloudinary
    legende = db.Column(db.Text)
    auteur = db.Column(db.String(80), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)
    likes = db.Column(db.Integer, default=0)

class Letter(db.Model):
    __tablename__ = 'letters'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sender = db.Column(db.String(80), nullable=False)
    recipient = db.Column(db.String(80), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Memory(db.Model):
    __tablename__ = 'memories'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_memory = db.Column(db.Date, nullable=False)
    author = db.Column(db.String(80), nullable=False)
    is_anniversary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Activity(db.Model):
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)

def init_default_data():
    """Initialise les données par défaut"""
    # Créer les utilisateurs par défaut
    users_data = [
        {
            'username': 'maninka mousso',
            'password': 'Elle a toujours été belle',
            'favorite_color': '#ffdde1'
        },
        {
            'username': 'panda bg', 
            'password': 'La lune est belle ce soir',
            'favorite_color': '#e1f5fe'
        }
    ]
    
    for user_data in users_data:
        user = User.query.filter_by(username=user_data['username']).first()
        if not user:
            user = User(username=user_data['username'])
            user.set_password(user_data['password'])
            user.favorite_color = user_data['favorite_color']
            db.session.add(user)
    
    db.session.commit()