import os
import json
import cloudinary
import cloudinary.uploader
import cloudinary.api
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text, extract
import secrets
import random
from calendar import monthcalendar
import calendar
import requests
import threading
import time

app = Flask(__name__)

# Configuration de l'application
app.config.from_object('config.ProductionConfig')

# Configuration Cloudinary
cloudinary.config(
    cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
    api_key=app.config['CLOUDINARY_API_KEY'],
    api_secret=app.config['CLOUDINARY_API_SECRET']
)

# Vérification de la configuration de la base de données
if not app.config.get('SQLALCHEMY_DATABASE_URI'):
    raise ValueError("DATABASE_URL n'est pas configuré dans les variables d'environnement")

# Initialisation de la base de données
db = SQLAlchemy(app)

# Date de déverrouillage (27 septembre 2025)
UNLOCK_DATE = datetime(2025, 9, 26, 23, 00, 59)

# Extensions de fichiers autorisées
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Modèles de base de données
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    favorite_color = db.Column(db.String(7), default='#ffdde1')
    visit_count = db.Column(db.Integer, default=0)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Phrase(db.Model):
    __tablename__ = 'phrases'
    id = db.Column(db.Integer, primary_key=True)
    texte = db.Column(db.Text, nullable=False)
    auteur = db.Column(db.String(80), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    couleur = db.Column(db.String(7), default='#ffdde1')
    tags = db.Column(db.String(200))
    est_favori = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)
    is_special = db.Column(db.Boolean, default=False)

class Photo(db.Model):
    __tablename__ = 'photos'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    cloudinary_url = db.Column(db.Text)
    cloudinary_public_id = db.Column(db.String(200))
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

class CalendarEvent(db.Model):
    __tablename__ = 'calendar_events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    event_type = db.Column(db.String(50), default='special')
    description = db.Column(db.Text)
    created_by = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Challenge(db.Model):
    __tablename__ = 'challenges'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    challenge_type = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    completed_by = db.Column(db.String(80))
    completed_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Activity(db.Model):
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)

def init_db():
    """Initialise la base de données avec toutes les tables nécessaires"""
    with app.app_context():
        # Créer toutes les tables
        db.create_all()
        
        # Vérifier si les utilisateurs existent déjà
        existing_users = User.query.all()
        existing_usernames = [user.username for user in existing_users]
        
        # Créer les utilisateurs s'ils n'existent pas
        if 'maninka mousso' not in existing_usernames:
            user1 = User(
                username='maninka mousso',
                password_hash=generate_password_hash('Elle a toujours été belle'),
                favorite_color='#ffdde1'
            )
            db.session.add(user1)
        
        if 'panda bg' not in existing_usernames:
            user2 = User(
                username='panda bg',
                password_hash=generate_password_hash('La lune est belle ce soir'),
                favorite_color='#e1f5fe'
            )
            db.session.add(user2)
        
        # Ajouter des défis par défaut s'ils n'existent pas
        existing_challenges = Challenge.query.count()
        if existing_challenges == 0:
            default_challenges = [
                ("Écris un message d'amour", "Partage un message tendre avec ton amour", "message", 15),
                ("Partage une photo souvenir", "Upload une photo qui vous rappelle un beau moment", "photo", 20),
                ("Vérifie ton humeur", "Utilise la fonction humeur du jour", "mood", 10),
                ("Ajoute un souvenir précieux", "Immortalise un moment spécial dans vos souvenirs", "memory", 25),
                ("Envoie une lettre d'amour", "Écris une belle lettre à ton partenaire", "letter", 30)
            ]
            
            for title, desc, c_type, points in default_challenges:
                challenge = Challenge(
                    title=title,
                    description=desc,
                    challenge_type=c_type,
                    points=points
                )
                db.session.add(challenge)
        
        db.session.commit()

def log_activity(user, action, details=None):
    """Enregistre une activité utilisateur"""
    activity = Activity(
        user=user,
        action=action,
        details=details
    )
    db.session.add(activity)
    db.session.commit()

def load_mood_verses():
    """Charge les versets depuis le fichier JSON"""
    try:
        with open('mood_verses.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Retourner des versets par défaut si le fichier n'existe pas
        return {
            "heureux": [{
                "arabic": "وَبَشِّرِ الصَّابِرِينَ",
                "french": "Et annonce la bonne nouvelle aux patients",
                "explanation": "Ce verset nous rappelle que la patience est récompensée par Allah.",
                "conclusion": "Continue à être patient(e) et joyeux/joyeuse, Allah te récompensera."
            }],
            "triste": [{
                "arabic": "وَلَا تَحْزَنْ إِنَّ اللَّهَ مَعَنَا",
                "french": "Ne t'attriste pas, Allah est avec nous",
                "explanation": "Allah est toujours avec nous dans les moments difficiles.",
                "conclusion": "N'aie pas de tristesse, Allah veille sur toi."
            }]
        }

def get_love_quotes():
    """Retourne une liste de citations d'amour"""
    quotes = [
        "N'oublie pas que je pense à toi ",
        "Prend soin de toi et de ton bonheur avant les autres",
        "Appelle-moi quand tu veux, je suis là pour toi même si on se dispute ou on ne se voit pas",
        "La lune est belle ce soir.",
        "Tu es l'une des meilleurs choses qui me soit arrivée.",
        "Mange bien et fait des activités que tu aimes avec des gens que tu aimes ou seule si tu préfères",
        "Tu es belle à l'intérieur comme à l'extérieur",
    ]
    return random.choice(quotes)

def is_site_unlocked():
    """Vérifie si le site est déverrouillé (après le 27 septembre 2025)"""
    return datetime.now() >= UNLOCK_DATE

# Créer le dossier uploads s'il n'existe pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialiser la base de données
init_db()

@app.before_request
def check_access():
    """Vérifie l'accès au site selon la date de déverrouillage"""
    # Pages autorisées même quand le site est verrouillé
    allowed_paths = ['/login', '/static', '/locked', '/logout', '/unlock_special', '/special_access']
    
    # Vérifier si le site est toujours verrouillé
    if not is_site_unlocked():
        # Si l'utilisateur a déjà accès spécial, le laisser passer
        if session.get('special_access'):
            return
        
        # Vérifier si l'utilisateur essaie d'accéder à une page non autorisée
        if not any(request.path.startswith(path) for path in allowed_paths):
            return redirect(url_for('locked_page'))
        
@app.before_request
def require_login():
    """Vérifie que l'utilisateur est connecté pour toutes les routes sauf login et locked"""
    if (request.endpoint and 
        request.endpoint not in ['login', 'locked_page', 'static', 'unlock_special'] and 
        'user' not in session):
        return redirect(url_for('login'))

@app.route('/locked')
def locked_page():
    """Page de verrouillage avec compte à rebours"""
    # Calculer le temps restant jusqu'au déverrouillage
    now = datetime.now()
    time_remaining = UNLOCK_DATE - now
    
    # Formater le temps restant
    days = time_remaining.days
    hours, remainder = divmod(time_remaining.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return render_template('locked.html', 
                         unlock_date=UNLOCK_DATE,
                         days=days,
                         hours=hours,
                         minutes=minutes,
                         seconds=seconds)

@app.route('/unlock_special', methods=['POST'])
def unlock_special():
    """API pour déverrouiller l'accès spécial (utilisée par la porte mystérieuse)"""
    if is_site_unlocked():
        return jsonify({'success': True, 'message': 'Le site est déjà déverrouillé'})
    
    data = request.get_json()
    name = data.get('name', '').strip().lower()
    password = data.get('password', '').strip()
    
    if name == 'saïd':
        session['special_access'] = True
        return jsonify({
            'success': True,
            'message': 'Accès spécial accordé ! Bienvenue Saïd.'
        })
    elif password == '2708':
        return jsonify({
            'success': False,
            'message': 'Ohhhh bien tenté Fanta ! Je t\'ai reconnu, tu as cru que ça serait si facile que ça ? Tu vas patienter.'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Accès refusé. Merci de patienter.'
        })

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Récupérer le nombre de tentatives depuis la session
    if 'login_attempts' not in session:
        session['login_attempts'] = {}
    
    if request.method == 'POST':
        username = request.form['username'].lower().strip()
        password = request.form['password']
        
        # Initialiser les tentatives pour cet utilisateur si nécessaire
        if username not in session['login_attempts']:
            session['login_attempts'][username] = 0
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            # Réinitialiser les tentatives en cas de succès
            session['login_attempts'][username] = 0
            session['user'] = username
            
            # Mettre à jour les statistiques de connexion
            user.visit_count += 1
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            
            log_activity(username, 'login')
            flash('Connexion réussie ! Bienvenue dans ton jardin secret 💖', 'success')
            
            # Rediriger vers la page appropriée selon l'état de déverrouillage
            if is_site_unlocked() or session.get('special_access'):
                return redirect(url_for('index'))
            else:
                return redirect(url_for('locked_page'))
        else:
            # Incrémenter les tentatives
            session['login_attempts'][username] += 1
            attempts = session['login_attempts'][username]
            
            if attempts == 1:
                if username == 'maninka mousso':
                    flash('Hmm... Pense à ce que je te dit toujours sur ta beauté 💫', 'error')
                elif username == 'panda bg':
                    flash('Rappelle-toi cette phrase romantique qui est une déclaration à nous 🌙', 'error')
                else:
                    flash('Nom d\'utilisateur ou mot de passe incorrect', 'error')
            elif attempts == 2:
                if username == 'maninka mousso':
                    flash('Indice : "Elle a toujours été..." - tu sais la suite ! ✨', 'error')
                elif username == 'panda bg':
                    flash('Indice : "La lune est..." - continue la phrase romantique 🌙', 'error')
                else:
                    flash('Nom d\'utilisateur ou mot de passe incorrect', 'error')
            elif attempts >= 3:
                if username == 'maninka mousso':
                    flash('Ton mot de passe est : "Elle a toujours été belle" 💖', 'info')
                elif username == 'panda bg':
                    flash('Ton mot de passe est : "La lune est belle ce soir" 🌙', 'info')
                else:
                    flash('Trop de tentatives. Contacte l\'administrateur.', 'error')
            else:
                flash('Nom d\'utilisateur ou mot de passe incorrect', 'error')
    
    # Récupérer les tentatives actuelles pour l'affichage
    current_attempts = {}
    if 'login_attempts' in session:
        current_attempts = session['login_attempts']
    
    return render_template('login.html', attempts=current_attempts)

@app.route('/special_access', methods=['GET', 'POST'])
def special_access():
    """Page d'accès spécial avec l'œil qui observe"""
    if is_site_unlocked():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form['name'].strip().lower()
        password = request.form['password'].strip()
        
        if name == 'saïd':
            session['special_access'] = True
            flash('Accès spécial accordé ! Bienvenue Saïd.', 'success')
            return redirect(url_for('index'))
        elif password == '2708':
            flash('Ohhhh bien tenté Fanta ! Je t\'ai reconnu, tu as cru que ça serait si facile que ça ? Tu vas patienter.', 'error')
        else:
            flash('Accès refusé. Merci de patienter.', 'error')
    
    return render_template('special_access.html')

@app.route('/logout')
def logout():
    user = session.get('user')
    if user:
        log_activity(user, 'logout')
    session.pop('user', None)
    session.pop('special_access', None)
    flash('Déconnexion réussie. À bientôt ! 👋', 'info')
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def index():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    if request.method == 'POST':
        texte = request.form['texte'].strip()
        couleur = request.form.get('couleur', '#ffdde1')
        tags = request.form.get('tags', '').strip()
        
        if texte:
            phrase = Phrase(
                texte=texte,
                auteur=user,
                couleur=couleur,
                tags=tags
            )
            db.session.add(phrase)
            db.session.commit()
            
            log_activity(user, 'message_added', f'Message: {texte[:50]}...')
            flash('Message ajouté avec succès ! 💖', 'success')
        
        return redirect(url_for('index'))
    
    # Récupérer les messages avec pagination
    phrases = Phrase.query.order_by(Phrase.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Statistiques
    stats = {
        'total_messages': Phrase.query.count(),
        'total_photos': Photo.query.count(),
        'favoris_count': Phrase.query.filter_by(est_favori=True).count()
    }
    
    # Lettres non lues
    unread_letters = Letter.query.filter_by(recipient=user, is_read=False).count()
    
    # Informations utilisateur
    user_info = User.query.filter_by(username=user).first()
    
    # Salutation personnalisée
    greetings = {
        'maninka mousso': "Salut ma maninka mousso préférée( seule d'ailleurs 😂 )",
        'panda bg': "Salut mon panda préféré"
    }
    
    return render_template('index.html',
                         phrases=phrases.items,
                         user=user,
                         pagination=phrases,
                         stats=stats,
                         unread_letters=unread_letters,
                         visit_count=user_info.visit_count if user_info else 0,
                         current_user={'favorite_color': user_info.favorite_color if user_info else '#ffdde1'},
                         personal_greeting=greetings.get(user, f"Salut {user.title()}"),
                         love_quote=get_love_quotes(),
                         now=datetime.now())

@app.route('/toggle_favori/<int:phrase_id>')
def toggle_favori(phrase_id):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    phrase = Phrase.query.get_or_404(phrase_id)
    phrase.est_favori = not phrase.est_favori
    db.session.commit()
    
    action = 'favori_added' if phrase.est_favori else 'favori_removed'
    log_activity(session['user'], action, f'Phrase ID: {phrase_id}')
    
    return redirect(url_for('index'))

@app.route('/like_phrase/<int:phrase_id>')
def like_phrase(phrase_id):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return jsonify({'error': 'Site verrouillé'}), 403
    
    phrase = Phrase.query.get_or_404(phrase_id)
    phrase.likes += 1
    db.session.commit()
    
    log_activity(session['user'], 'phrase_liked', f'Phrase ID: {phrase_id}')
    
    return jsonify({'likes': phrase.likes})

@app.route('/supprimer_phrase/<int:phrase_id>')
def supprimer_phrase(phrase_id):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    phrase = Phrase.query.get_or_404(phrase_id)
    
    # Vérifier que l'utilisateur est l'auteur
    if phrase.auteur == user:
        db.session.delete(phrase)
        db.session.commit()
        log_activity(user, 'phrase_deleted', f'Phrase ID: {phrase_id}')
        flash('Message supprimé avec succès', 'success')
    else:
        flash('Vous ne pouvez supprimer que vos propres messages', 'error')
    
    return redirect(url_for('index'))

@app.route('/galerie')
def galerie():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    photos = Photo.query.order_by(Photo.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('galerie.html', photos=photos.items, user=session['user'], pagination=photos)

@app.route('/upload', methods=['POST'])
def upload_file():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('galerie'))
    
    file = request.files['file']
    legende = request.form.get('legende', '').strip()
    
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('galerie'))
    
    if file and allowed_file(file.filename):
        try:
            # Upload vers Cloudinary
            upload_result = cloudinary.uploader.upload(
                file,
                folder="love_site",
                resource_type="image"
            )
            
            # Enregistrer en base
            photo = Photo(
                filename=file.filename,
                cloudinary_url=upload_result['secure_url'],
                cloudinary_public_id=upload_result['public_id'],
                legende=legende,
                auteur=session['user'],
                file_size=upload_result.get('bytes', 0)
            )
            db.session.add(photo)
            db.session.commit()
            
            log_activity(session['user'], 'photo_uploaded', f'Photo: {file.filename}')
            flash('Photo uploadée avec succès ! 📸', 'success')
            
        except Exception as e:
            flash(f'Erreur lors de l\'upload: {str(e)}', 'error')
    else:
        flash('Type de fichier non autorisé', 'error')
    
    return redirect(url_for('galerie'))

@app.route('/like_photo/<int:photo_id>')
def like_photo(photo_id):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return jsonify({'error': 'Site verrouillé'}), 403
    
    photo = Photo.query.get_or_404(photo_id)
    photo.likes += 1
    db.session.commit()
    
    log_activity(session['user'], 'photo_liked', f'Photo ID: {photo_id}')
    
    return jsonify({'likes': photo.likes})

@app.route('/supprimer_photo/<int:photo_id>')
def supprimer_photo(photo_id):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    photo = Photo.query.get_or_404(photo_id)
    
    # Vérifier que l'utilisateur est l'auteur
    if photo.auteur == user:
        # Supprimer de Cloudinary
        if photo.cloudinary_public_id:
            try:
                cloudinary.uploader.destroy(photo.cloudinary_public_id)
            except Exception as e:
                print(f"Erreur lors de la suppression Cloudinary: {e}")
        
        # Supprimer de la base
        db.session.delete(photo)
        db.session.commit()
        
        log_activity(user, 'photo_deleted', f'Photo ID: {photo_id}')
        flash('Photo supprimée avec succès', 'success')
    else:
        flash('Vous ne pouvez supprimer que vos propres photos', 'error')
    
    return redirect(url_for('galerie'))

@app.route('/mood', methods=['GET', 'POST'])
def mood():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    if request.method == 'POST':
        selected_mood = request.form['mood']
        log_activity(session['user'], 'mood_checked', f'Mood: {selected_mood}')
        return redirect(url_for('mood_result', mood=selected_mood))
    
    return render_template('mood.html', user=session['user'])

@app.route('/mood_result/<mood>')
def mood_result(mood):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    verses = load_mood_verses()
    
    # Sélectionner un verset aléatoire pour l'humeur
    if mood in verses and verses[mood]:
        verse = random.choice(verses[mood])
    else:
        # Verset par défaut
        verse = {
            "arabic": "وَاللَّهُ يُحِبُّ الْمُحْسِنِينَ",
            "french": "Et Allah aime les bienfaisants",
            "explanation": "Allah aime ceux qui fait le bien.",
            "conclusion": "Continue à faire le bien, Allah t'aime."
        }
    
    return render_template('mood_result.html', mood=mood, verse=verse, user=session['user'])

@app.route('/search')
def search():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    query = request.args.get('q', '').strip()
    phrases = []
    
    if query:
        phrases = Phrase.query.filter(
            (Phrase.texte.ilike(f'%{query}%')) | 
            (Phrase.tags.ilike(f'%{query}%'))
        ).order_by(Phrase.date.desc()).all()
        
        log_activity(session['user'], 'search', f'Query: {query}')
    
    return render_template('search_results.html', phrases=phrases, query=query, user=session['user'])

@app.route('/letters')
def letters():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    
    # Lettres reçues
    received_letters = Letter.query.filter_by(recipient=user).order_by(Letter.created_at.desc()).all()
    
    # Lettres envoyées
    sent_letters = Letter.query.filter_by(sender=user).order_by(Letter.created_at.desc()).all()
    
    return render_template('letters.html', 
                         received_letters=received_letters,
                         sent_letters=sent_letters,
                         user=user)

@app.route('/write_letter', methods=['GET', 'POST'])
def write_letter():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    recipient = 'maninka mousso' if user == 'panda bg' else 'panda bg'
    
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        
        if title and content:
            letter = Letter(
                title=title,
                content=content,
                sender=user,
                recipient=recipient
            )
            db.session.add(letter)
            db.session.commit()
            
            log_activity(user, 'letter_sent', f'To: {recipient}, Title: {title}')
            flash('Lettre envoyée avec amour ! 💌', 'success')
            return redirect(url_for('letters'))
    
    return render_template('write_letter.html', user=user, recipient=recipient)

@app.route('/read_letter/<int:letter_id>')
def read_letter(letter_id):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    letter = Letter.query.get_or_404(letter_id)
    
    # Vérifier que l'utilisateur peut lire cette lettre
    if letter.sender != user and letter.recipient != user:
        flash('Vous n\'avez pas accès à cette lettre', 'error')
        return redirect(url_for('letters'))
    
    # Marquer comme lue si c'est le destinataire
    if letter.recipient == user and not letter.is_read:
        letter.is_read = True
        db.session.commit()
        log_activity(user, 'letter_read', f'Letter ID: {letter_id}')
    
    return render_template('read_letter.html', letter=letter, user=user)

@app.route('/memories')
def memories():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    # Souvenirs anniversaires
    anniversaries = Memory.query.filter_by(is_anniversary=True).order_by(Memory.date_memory.desc()).all()
    
    # Souvenirs réguliers
    regular_memories = Memory.query.filter_by(is_anniversary=False).order_by(Memory.date_memory.desc()).all()
    
    return render_template('memories.html', 
                         anniversaries=anniversaries,
                         regular_memories=regular_memories,
                         user=session['user'])

@app.route('/add_memory', methods=['GET', 'POST'])
def add_memory():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form['description'].strip()
        date_memory = request.form['date_memory']
        is_anniversary = 'is_anniversary' in request.form
        
        if title and description and date_memory:
            memory = Memory(
                title=title,
                description=description,
                date_memory=datetime.strptime(date_memory, '%Y-%m-%d').date(),
                author=session['user'],
                is_anniversary=is_anniversary
            )
            db.session.add(memory)
            db.session.commit()
            
            log_activity(session['user'], 'memory_added', f'Memory: {title}')
            flash('Souvenir ajouté avec succès ! ✨', 'success')
            return redirect(url_for('memories'))
    
    return render_template('add_memory.html', user=session['user'])

@app.route('/love_calendar')
def love_calendar():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # Générer le calendrier
    cal = monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Récupérer les événements
    events = CalendarEvent.query.filter(
        extract('year', CalendarEvent.event_date) == year,
        extract('month', CalendarEvent.event_date) == month
    ).all()
    
    # Organiser les événements par jour
    events_by_day = {}
    for event in events:
        day = event.event_date.day
        if day not in events_by_day:
            events_by_day[day] = []
        events_by_day[day].append(event)
    
    # Dates spéciales (anniversaires, etc.)
    special_dates = {}
    if month == 9:  # Septembre
        special_dates[27] = {'title': 'Anniversaire de Maninka Mousso', 'type': 'anniversary'}
    
    return render_template('love_calendar.html',
                         calendar_data=cal,
                         current_month=month,
                         current_year=year,
                         month_name=month_name,
                         events_by_day=events_by_day,
                         special_dates=special_dates,
                         today=datetime.now().date())

@app.route('/add_calendar_event', methods=['POST'])
def add_calendar_event():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    title = request.form['title'].strip()
    event_date = request.form['event_date']
    event_type = request.form['event_type']
    description = request.form.get('description', '').strip()
    
    if title and event_date:
        event = CalendarEvent(
            title=title,
            event_date=datetime.strptime(event_date, '%Y-%m-%d').date(),
            event_type=event_type,
            description=description,
            created_by=session['user']
        )
        db.session.add(event)
        db.session.commit()
        
        flash('Événement ajouté au calendrier ! 📅', 'success')
    
    return redirect(url_for('love_calendar'))

@app.route('/love_challenges')
def love_challenges():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    # Défis actifs
    active_challenges = Challenge.query.filter_by(is_active=True, completed_by=None).order_by(Challenge.points.desc()).all()
    
    # Défis terminés
    completed_challenges = Challenge.query.filter(Challenge.completed_by.isnot(None)).order_by(Challenge.completed_date.desc()).all()
    
    # Points totaux de l'utilisateur
    total_points = db.session.query(db.func.sum(Challenge.points)).filter(Challenge.completed_by == session['user']).scalar() or 0
    
    return render_template('love_challenges.html',
                         active_challenges=active_challenges,
                         completed_challenges=completed_challenges,
                         total_points=total_points,
                         user=session['user'])

@app.route('/complete_challenge/<int:challenge_id>')
def complete_challenge(challenge_id):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    challenge = Challenge.query.get_or_404(challenge_id)
    
    # Marquer le défi comme terminé
    if not challenge.completed_by:
        challenge.completed_by = session['user']
        challenge.completed_date = datetime.utcnow()
        db.session.commit()
        
        flash('Défi terminé ! Bravo ! 🎉', 'success')
    
    return redirect(url_for('love_challenges'))

@app.route('/personalize', methods=['GET', 'POST'])
def personalize():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    user_info = User.query.filter_by(username=user).first()
    
    if request.method == 'POST':
        favorite_color = request.form['favorite_color']
        
        user_info.favorite_color = favorite_color
        db.session.commit()
        
        flash('Préférences sauvegardées ! 🎨', 'success')
        return redirect(url_for('personalize'))
    
    return render_template('personalize.html', 
                         user=user,
                         current_user=user_info,
                         current_color=user_info.favorite_color if user_info else '#ffdde1')

@app.route('/stats')
def stats():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    # Statistiques générales
    total_messages = Phrase.query.count()
    total_photos = Photo.query.count()
    favoris_count = Phrase.query.filter_by(est_favori=True).count()
    total_letters = Letter.query.count()
    total_memories = Memory.query.count()
    
    # Messages par utilisateur
    messages_by_user = db.session.query(
        Phrase.auteur, 
        db.func.count(Phrase.id).label('count')
    ).group_by(Phrase.auteur).order_by(db.func.count(Phrase.id).desc()).all()
    
    # Photos par utilisateur
    photos_by_user = db.session.query(
        Photo.auteur, 
        db.func.count(Photo.id).label('count')
    ).group_by(Photo.auteur).order_by(db.func.count(Photo.id).desc()).all()
    
    # Activité récente
    recent_activity = Activity.query.order_by(Activity.date.desc()).limit(20).all()
    
    return render_template('stats.html',
                         total_messages=total_messages,
                         total_photos=total_photos,
                         favoris_count=favoris_count,
                         total_letters=total_letters,
                         total_memories=total_memories,
                         messages_by_user=messages_by_user,
                         photos_by_user=photos_by_user,
                         recent_activity=recent_activity,
                         user=session['user'])

@app.route('/birthday_surprise')
def birthday_surprise():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    # Vérifier que c'est Maninka Mousso et que c'est son anniversaire
    if session['user'] != 'maninka mousso':
        flash('Cette page est réservée à Maninka Mousso ! 😊', 'info')
        return redirect(url_for('index'))
    
    today = datetime.now().date()
    if today.month != 9 or today.day < 27:
        flash('La surprise n\'est pas encore prête ! 🎁', 'info')
        return redirect(url_for('countdown'))
    
    # Lettre de surprise d'anniversaire
    surprise = {
        'title': 'Joyeux Anniversaire ma Maninka Mousso ! 🎂',
        'content': '''Ma très chère Maninka Mousso,

Aujourd'hui est un jour très spécial car c'est TON jour ! 🎉

J'ai créé ce site entier comme une déclaration d'amour pour toi. Chaque ligne de code, chaque couleur, chaque fonctionnalité a été pensée avec amour pour te faire sourire.

Tu es ma maninka mousso, la plus gentille, la plus belle, celle qui sait me faire rire. Ton sourire, ta voix, ton amour tout est un trésor.

Pour ton anniversaire, j'ai voulu t'offrir quelque chose d'unique : notre propre jardin secret numérique où nous pouvons cultiver notre amour, partager nos souvenirs et écrire notre histoire.

Que cette nouvelle année de ta vie soit remplie de bonheur, de réussites, de rires et surtout... de nous ! 💕

Je t'aime plus que les mots ne peuvent l'exprimer, plus que les étoiles dans le ciel, plus que tu ne le sais toi-même.

Joyeux anniversaire la plus belle et gentille ! 👑

Ton panda qui trouve la lune si  belle chaque soir 🌙,
Ton plus grand fan 💖

P.S. : Explore toutes les nouvelles fonctionnalités que j'ai ajoutées spécialement pour ton anniversaire ! 🎁'''
    }
    
    return render_template('birthday_surprise.html', surprise=surprise, user=session['user'])

@app.route('/countdown')
def countdown():
    # Calculer les jours jusqu'au 27 septembre
    today = datetime.now().date()
    target_date = datetime(today.year, 9, 27).date()
    
    # Si on est déjà passé le 27 septembre cette année, viser l'année prochaine
    if today > target_date:
        target_date = datetime(today.year + 1, 9, 27).date()
    
    days_left = (target_date - today).days
    
    return render_template('countdown.html', 
                         days_left=days_left,
                         target_date=target_date,
                         user=session['user'])

# Gestion des erreurs
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

@app.errorhandler(413)
def too_large(error):
    flash('Fichier trop volumineux (max 16MB)', 'error')
    return redirect(url_for('galerie'))

if __name__ == '__main__':
    # Configuration pour la production
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)



# Route de santé pour les services de monitoring
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

# Route pour s'auto-pinger (optionnel)
@app.route('/self-ping')
def self_ping():
    try:
        # Remplace par l'URL de ton site Render
        response = requests.get('https://ton-site.onrender.com/health')
        return {'self_ping': 'success', 'status_code': response.status_code}
    except Exception as e:
        return {'self_ping': 'failed', 'error': str(e)}

# Fonction pour auto-pinger périodiquement
def start_auto_ping():
    def ping_loop():
        while True:
            try:
                # Ping toutes les 8 minutes (Render s'endort après 15 min d'inactivité)
                requests.get('https://ton-site.onrender.com/self-ping', timeout=10)
                print(f"Auto-ping à {datetime.now()}")
            except Exception as e:
                print(f"Erreur auto-ping: {e}")
            time.sleep(480)  # 8 minutes
    
    # Démarrer le thread d'auto-ping
    thread = threading.Thread(target=ping_loop)
    thread.daemon = True
    thread.start()

# Démarrer l'auto-ping au lancement de l'app
if __name__ == '__main__':
    start_auto_ping()
    app.run(debug=False)