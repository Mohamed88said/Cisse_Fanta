import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import random
import cloudinary
import cloudinary.uploader
import cloudinary.api
import psycopg2
from urllib.parse import urlparse

app = Flask(__name__)

# Configuration sécurisée pour la production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configuration Cloudinary
app.config['CLOUDINARY_CLOUD_NAME'] = os.environ.get('CLOUDINARY_CLOUD_NAME', 'djbdv90jr')
app.config['CLOUDINARY_API_KEY'] = os.environ.get('CLOUDINARY_API_KEY', '455591489376377')
app.config['CLOUDINARY_API_SECRET'] = os.environ.get('CLOUDINARY_API_SECRET', 'xfudLM75vr_yKqrpHVAr87NNhDo')

# Configuration de la base de données (Neon.tech ou SQLite)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Neon.tech PostgreSQL
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")
    
    parsed_url = urlparse(DATABASE_URL)
    app.config['DATABASE_CONFIG'] = {
        'dbname': parsed_url.path[1:],  # Enlever le slash initial
        'user': parsed_url.username,
        'password': parsed_url.password,
        'host': parsed_url.hostname,
        'port': parsed_url.port,
        'sslmode': 'require'
    }
    DB_TYPE = 'postgresql'
else:
    # SQLite en local
    app.config['DATABASE_PATH'] = os.environ.get('DATABASE_PATH', 'instance/database.db')
    DB_TYPE = 'sqlite'

# Date de déverrouillage (27 septembre 2025)
UNLOCK_DATE = datetime(2025, 9, 26, 23, 0, 59)

# Extensions de fichiers autorisées
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Initialiser Cloudinary
cloudinary.config(
    cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
    api_key=app.config['CLOUDINARY_API_KEY'],
    api_secret=app.config['CLOUDINARY_API_SECRET']
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    if DB_TYPE == 'postgresql':
        conn = psycopg2.connect(**app.config['DATABASE_CONFIG'])
        conn.autocommit = True
    else:
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialise la base de données avec toutes les tables nécessaires"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        # Tables PostgreSQL pour Neon.tech
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                favorite_color TEXT DEFAULT '#ffdde1',
                visit_count INTEGER DEFAULT 0,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phrases (
                id SERIAL PRIMARY KEY,
                texte TEXT NOT NULL,
                auteur TEXT NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                couleur TEXT DEFAULT '#ffdde1',
                tags TEXT,
                est_favori BOOLEAN DEFAULT FALSE,
                likes INTEGER DEFAULT 0,
                is_special BOOLEAN DEFAULT FALSE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photos (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                cloudinary_url TEXT,
                legende TEXT,
                auteur TEXT NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER,
                likes INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS letters (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                date_memory DATE NOT NULL,
                author TEXT NOT NULL,
                is_anniversary BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar_events (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                event_date DATE NOT NULL,
                event_type TEXT DEFAULT 'special',
                description TEXT,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS challenges (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                challenge_type TEXT NOT NULL,
                points INTEGER DEFAULT 10,
                is_active BOOLEAN DEFAULT TRUE,
                completed_by TEXT,
                completed_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # SQLite (version originale)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                favorite_color TEXT DEFAULT '#ffdde1',
                visit_count INTEGER DEFAULT 0,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phrases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                texte TEXT NOT NULL,
                auteur TEXT NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                couleur TEXT DEFAULT '#ffdde1',
                tags TEXT,
                est_favori BOOLEAN DEFAULT 0,
                likes INTEGER DEFAULT 0,
                is_special BOOLEAN DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                cloudinary_url TEXT,
                legende TEXT,
                auteur TEXT NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER,
                likes INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS letters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                date_memory DATE NOT NULL,
                author TEXT NOT NULL,
                is_anniversary BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                event_date DATE NOT NULL,
                event_type TEXT DEFAULT 'special',
                description TEXT,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                challenge_type TEXT NOT NULL,
                points INTEGER DEFAULT 10,
                is_active BOOLEAN DEFAULT 1,
                completed_by TEXT,
                completed_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    # Créer les utilisateurs par défaut
    if DB_TYPE == 'postgresql':
        cursor.execute("SELECT username FROM users")
        existing_users = [row[0] for row in cursor.fetchall()]
    else:
        existing_users_result = cursor.execute('SELECT username FROM users').fetchall()
        existing_users = [user[0] for user in existing_users_result]
    
    # Mettre à jour les utilisateurs avec les nouveaux noms et mots de passe
    if 'maninka mousso' not in existing_users:
        if DB_TYPE == 'postgresql':
            cursor.execute('''
                INSERT INTO users (username, password_hash, favorite_color)
                VALUES (%s, %s, %s)
            ''', ('maninka mousso', generate_password_hash('Elle a toujours été belle'), '#ffdde1'))
        else:
            cursor.execute('''
                INSERT INTO users (username, password_hash, favorite_color)
                VALUES (?, ?, ?)
            ''', ('maninka mousso', generate_password_hash('Elle a toujours été belle'), '#ffdde1'))
    
    if 'panda bg' not in existing_users:
        if DB_TYPE == 'postgresql':
            cursor.execute('''
                INSERT INTO users (username, password_hash, favorite_color)
                VALUES (%s, %s, %s)
            ''', ('panda bg', generate_password_hash('La lune est belle ce soir'), '#e1f5fe'))
        else:
            cursor.execute('''
                INSERT INTO users (username, password_hash, favorite_color)
                VALUES (?, ?, ?)
            ''', ('panda bg', generate_password_hash('La lune est belle ce soir'), '#e1f5fe'))
    
    # Ajouter quelques défis par défaut
    if DB_TYPE == 'postgresql':
        cursor.execute("SELECT COUNT(*) FROM challenges")
        existing_challenges_count = cursor.fetchone()[0]
    else:
        existing_challenges = cursor.execute('SELECT COUNT(*) as count FROM challenges').fetchone()
        existing_challenges_count = existing_challenges['count']
    
    if existing_challenges_count == 0:
        default_challenges = [
            ("Écris un message d'amour", "Partage un message tendre avec ton amour", "message", 15),
            ("Partage une photo souvenir", "Upload une photo qui vous rappelle un beau moment", "photo", 20),
            ("Vérifie ton humeur", "Utilise la fonction humeur du jour", "mood", 10),
            ("Ajoute un souvenir précieux", "Immortalise un moment spécial dans vos souvenirs", "memory", 25),
            ("Envoie une lettre d'amour", "Écris une belle lettre à ton partenaire", "letter", 30)
        ]
        
        for title, desc, c_type, points in default_challenges:
            if DB_TYPE == 'postgresql':
                cursor.execute('''
                    INSERT INTO challenges (title, description, challenge_type, points)
                    VALUES (%s, %s, %s, %s)
                ''', (title, desc, c_type, points))
            else:
                cursor.execute('''
                    INSERT INTO challenges (title, description, challenge_type, points)
                    VALUES (?, ?, ?, ?)
                ''', (title, desc, c_type, points))
    
    conn.commit()
    cursor.close()
    conn.close()

def upload_to_cloudinary(file):
    """Upload un fichier vers Cloudinary"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + secure_filename(file.filename)
        
        result = cloudinary.uploader.upload(
            file,
            folder="love_app",
            public_id=filename,
            resource_type="image"
        )
        
        return {
            'success': True,
            'url': result['secure_url'],
            'public_id': result['public_id'],
            'filename': filename,
            'file_size': result.get('bytes', 0)
        }
    except Exception as e:
        print(f"Erreur Cloudinary: {e}")
        return {'success': False, 'error': str(e)}

def log_activity(user, action, details=None):
    """Enregistre une activité utilisateur"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            INSERT INTO activities (username, action, details)
            VALUES (%s, %s, %s)
        ''', (user, action, details))
    else:
        cursor.execute('''
            INSERT INTO activities (user, action, details)
            VALUES (?, ?, ?)
        ''', (user, action, details))
    
    conn.commit()
    cursor.close()
    conn.close()

def load_mood_verses():
    """Charge les versets depuis le fichier JSON"""
    try:
        with open('mood_verses.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
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
os.makedirs('instance', exist_ok=True)

# Initialiser la base de données
init_db()

@app.before_request
def check_access():
    """Vérifie l'accès au site selon la date de déverrouillage"""
    allowed_paths = ['/login', '/static', '/locked', '/logout', '/unlock_special', '/special_access']
    
    if not is_site_unlocked():
        if session.get('special_access'):
            return
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
    now = datetime.now()
    time_remaining = UNLOCK_DATE - now
    
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
    """API pour déverrouiller l'accès spécial"""
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
    if 'login_attempts' not in session:
        session['login_attempts'] = {}
    
    if request.method == 'POST':
        username = request.form['username'].lower().strip()
        password = request.form['password']
        
        if username not in session['login_attempts']:
            session['login_attempts'][username] = 0
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DB_TYPE == 'postgresql':
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        else:
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Convertir en dict pour un accès cohérent
        user = None
        if user_data:
            if DB_TYPE == 'postgresql':
                user = {
                    'id': user_data[0],
                    'username': user_data[1],
                    'password_hash': user_data[2],
                    'favorite_color': user_data[3],
                    'visit_count': user_data[4],
                    'last_login': user_data[5],
                    'created_at': user_data[6]
                }
            else:
                user = dict(user_data)
        
        if user and check_password_hash(user['password_hash'], password):
            session['login_attempts'][username] = 0
            session['user'] = username
            
            # Mettre à jour les statistiques de connexion
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if DB_TYPE == 'postgresql':
                cursor.execute('''
                    UPDATE users 
                    SET visit_count = visit_count + 1, last_login = CURRENT_TIMESTAMP
                    WHERE username = %s
                ''', (username,))
            else:
                cursor.execute('''
                    UPDATE users 
                    SET visit_count = visit_count + 1, last_login = CURRENT_TIMESTAMP
                    WHERE username = ?
                ''', (username,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            log_activity(username, 'login')
            flash('Connexion réussie ! Bienvenue dans ton jardin secret 💖', 'success')
            
            if is_site_unlocked() or session.get('special_access'):
                return redirect(url_for('index'))
            else:
                return redirect(url_for('locked_page'))
        else:
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
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if DB_TYPE == 'postgresql':
                cursor.execute('''
                    INSERT INTO phrases (texte, auteur, couleur, tags)
                    VALUES (%s, %s, %s, %s)
                ''', (texte, user, couleur, tags))
            else:
                cursor.execute('''
                    INSERT INTO phrases (texte, auteur, couleur, tags)
                    VALUES (?, ?, ?, ?)
                ''', (texte, user, couleur, tags))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            log_activity(user, 'message_added', f'Message: {texte[:50]}...')
            flash('Message ajouté avec succès ! 💖', 'success')
        
        return redirect(url_for('index'))
    
    # Récupérer les messages avec pagination
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Compter le total des messages
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT COUNT(*) FROM phrases')
    else:
        cursor.execute('SELECT COUNT(*) FROM phrases')
    
    total = cursor.fetchone()[0]
    
    # Récupérer les messages pour la page actuelle
    offset = (page - 1) * per_page
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            SELECT * FROM phrases 
            ORDER BY date DESC 
            LIMIT %s OFFSET %s
        ''', (per_page, offset))
        phrases_data = cursor.fetchall()
        phrases = []
        for row in phrases_data:
            phrases.append({
                'id': row[0],
                'texte': row[1],
                'auteur': row[2],
                'date': row[3],
                'couleur': row[4],
                'tags': row[5],
                'est_favori': row[6],
                'likes': row[7],
                'is_special': row[8]
            })
    else:
        cursor.execute('''
            SELECT * FROM phrases 
            ORDER BY date DESC 
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        phrases_data = cursor.fetchall()
        phrases = [dict(row) for row in phrases_data]
    
    # Statistiques
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT COUNT(*) FROM phrases')
        total_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM photos')
        total_photos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM phrases WHERE est_favori = TRUE')
        favoris_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM letters WHERE recipient = %s AND is_read = FALSE', (user,))
        unread_letters = cursor.fetchone()[0]
        
        cursor.execute('SELECT visit_count, favorite_color FROM users WHERE username = %s', (user,))
        user_info_data = cursor.fetchone()
    else:
        cursor.execute('SELECT COUNT(*) FROM phrases')
        total_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM photos')
        total_photos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM phrases WHERE est_favori = 1')
        favoris_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM letters WHERE recipient = ? AND is_read = 0', (user,))
        unread_letters = cursor.fetchone()[0]
        
        cursor.execute('SELECT visit_count, favorite_color FROM users WHERE username = ?', (user,))
        user_info_data = cursor.fetchone()
    
    stats = {
        'total_messages': total_messages,
        'total_photos': total_photos,
        'favoris_count': favoris_count
    }
    
    # Convertir user_info en dict
    user_info = {}
    if user_info_data:
        if DB_TYPE == 'postgresql':
            user_info = {
                'visit_count': user_info_data[0],
                'favorite_color': user_info_data[1]
            }
        else:
            user_info = dict(user_info_data)
    
    cursor.close()
    conn.close()
    
    # Pagination
    has_prev = page > 1
    has_next = offset + per_page < total
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_num': page - 1 if has_prev else None,
        'next_num': page + 1 if has_next else None,
        'iter_pages': lambda: range(max(1, page - 2), min((total + per_page - 1) // per_page + 1, page + 3))
    }
    
    # Salutation personnalisée
    greetings = {
        'maninka mousso': "Salut ma maninka mousso préférée( seule d'ailleurs 😂 )",
        'panda bg': "Salut mon panda préféré"
    }
    
    return render_template('index.html',
                         phrases=phrases,
                         user=user,
                         pagination=pagination,
                         stats=stats,
                         unread_letters=unread_letters,
                         visit_count=user_info.get('visit_count', 0),
                         current_user={'favorite_color': user_info.get('favorite_color', '#ffdde1')},
                         personal_greeting=greetings.get(user, f"Salut {user.title()}"),
                         love_quote=get_love_quotes(),
                         now=datetime.now())

@app.route('/toggle_favori/<int:phrase_id>')
def toggle_favori(phrase_id):
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT est_favori FROM phrases WHERE id = %s', (phrase_id,))
        phrase_data = cursor.fetchone()
        if phrase_data:
            new_status = not phrase_data[0]
            cursor.execute('UPDATE phrases SET est_favori = %s WHERE id = %s', (new_status, phrase_id))
    else:
        cursor.execute('SELECT est_favori FROM phrases WHERE id = ?', (phrase_id,))
        phrase = cursor.fetchone()
        if phrase:
            new_status = not phrase['est_favori']
            cursor.execute('UPDATE phrases SET est_favori = ? WHERE id = ?', (new_status, phrase_id))
    
    conn.commit()
    
    action = 'favori_added' if new_status else 'favori_removed'
    log_activity(session['user'], action, f'Phrase ID: {phrase_id}')
    
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/like_phrase/<int:phrase_id>')
def like_phrase(phrase_id):
    if not is_site_unlocked() and not session.get('special_access'):
        return jsonify({'error': 'Site verrouillé'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('UPDATE phrases SET likes = likes + 1 WHERE id = %s', (phrase_id,))
        cursor.execute('SELECT likes FROM phrases WHERE id = %s', (phrase_id,))
        likes_data = cursor.fetchone()
        likes = likes_data[0] if likes_data else 0
    else:
        cursor.execute('UPDATE phrases SET likes = likes + 1 WHERE id = ?', (phrase_id,))
        cursor.execute('SELECT likes FROM phrases WHERE id = ?', (phrase_id,))
        likes_row = cursor.fetchone()
        likes = likes_row['likes'] if likes_row else 0
    
    conn.commit()
    cursor.close()
    conn.close()
    
    log_activity(session['user'], 'phrase_liked', f'Phrase ID: {phrase_id}')
    return jsonify({'likes': likes})

@app.route('/supprimer_phrase/<int:phrase_id>')
def supprimer_phrase(phrase_id):
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que l'utilisateur est l'auteur
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT auteur FROM phrases WHERE id = %s', (phrase_id,))
        phrase_data = cursor.fetchone()
        if phrase_data and phrase_data[0] == user:
            cursor.execute('DELETE FROM phrases WHERE id = %s', (phrase_id,))
            log_activity(user, 'phrase_deleted', f'Phrase ID: {phrase_id}')
            flash('Message supprimé avec succès', 'success')
        else:
            flash('Vous ne pouvez supprimer que vos propres messages', 'error')
    else:
        cursor.execute('SELECT auteur FROM phrases WHERE id = ?', (phrase_id,))
        phrase = cursor.fetchone()
        if phrase and phrase['auteur'] == user:
            cursor.execute('DELETE FROM phrases WHERE id = ?', (phrase_id,))
            log_activity(user, 'phrase_deleted', f'Phrase ID: {phrase_id}')
            flash('Message supprimé avec succès', 'success')
        else:
            flash('Vous ne pouvez supprimer que vos propres messages', 'error')
    
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/galerie')
def galerie():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Compter le total des photos
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT COUNT(*) FROM photos')
    else:
        cursor.execute('SELECT COUNT(*) FROM photos')
    
    total = cursor.fetchone()[0]
    
    # Récupérer les photos pour la page actuelle
    offset = (page - 1) * per_page
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            SELECT * FROM photos 
            ORDER BY date DESC 
            LIMIT %s OFFSET %s
        ''', (per_page, offset))
        photos_data = cursor.fetchall()
        photos = []
        for row in photos_data:
            photos.append({
                'id': row[0],
                'filename': row[1],
                'cloudinary_url': row[2],
                'legende': row[3],
                'auteur': row[4],
                'date': row[5],
                'file_size': row[6],
                'likes': row[7]
            })
    else:
        cursor.execute('''
            SELECT * FROM photos 
            ORDER BY date DESC 
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        photos_data = cursor.fetchall()
        photos = [dict(row) for row in photos_data]
    
    cursor.close()
    conn.close()
    
    # Pagination
    has_prev = page > 1
    has_next = offset + per_page < total
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_num': page - 1 if has_prev else None,
        'next_num': page + 1 if has_next else None,
        'iter_pages': lambda: range(max(1, page - 2), min((total + per_page - 1) // per_page + 1, page + 3))
    }
    
    return render_template('galerie.html', photos=photos, pagination=pagination)

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    
    if 'photo' not in request.files:
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('galerie'))
    
    file = request.files['photo']
    legende = request.form.get('legende', '').strip()
    
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('galerie'))
    
    if file and allowed_file(file.filename):
        # Upload vers Cloudinary
        result = upload_to_cloudinary(file)
        
        if result['success']:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if DB_TYPE == 'postgresql':
                cursor.execute('''
                    INSERT INTO photos (filename, cloudinary_url, legende, auteur, file_size)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (result['filename'], result['url'], legende, user, result['file_size']))
            else:
                cursor.execute('''
                    INSERT INTO photos (filename, cloudinary_url, legende, auteur, file_size)
                    VALUES (?, ?, ?, ?, ?)
                ''', (result['filename'], result['url'], legende, user, result['file_size']))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            log_activity(user, 'photo_uploaded', f'Photo: {result["filename"]}')
            flash('Photo uploadée avec succès ! 📸', 'success')
        else:
            flash(f'Erreur lors de l\'upload: {result["error"]}', 'error')
    else:
        flash('Type de fichier non autorisé. Utilisez PNG, JPG, JPEG, GIF ou WEBP.', 'error')
    
    return redirect(url_for('galerie'))

@app.route('/like_photo/<int:photo_id>')
def like_photo(photo_id):
    if not is_site_unlocked() and not session.get('special_access'):
        return jsonify({'error': 'Site verrouillé'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('UPDATE photos SET likes = likes + 1 WHERE id = %s', (photo_id,))
        cursor.execute('SELECT likes FROM photos WHERE id = %s', (photo_id,))
        likes_data = cursor.fetchone()
        likes = likes_data[0] if likes_data else 0
    else:
        cursor.execute('UPDATE photos SET likes = likes + 1 WHERE id = ?', (photo_id,))
        cursor.execute('SELECT likes FROM photos WHERE id = ?', (photo_id,))
        likes_row = cursor.fetchone()
        likes = likes_row['likes'] if likes_row else 0
    
    conn.commit()
    cursor.close()
    conn.close()
    
    log_activity(session['user'], 'photo_liked', f'Photo ID: {photo_id}')
    return jsonify({'likes': likes})

@app.route('/supprimer_photo/<int:photo_id>')
def supprimer_photo(photo_id):
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que l'utilisateur est l'auteur
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT auteur, cloudinary_url FROM photos WHERE id = %s', (photo_id,))
        photo_data = cursor.fetchone()
        if photo_data and photo_data[0] == user:
            # Supprimer de Cloudinary
            if photo_data[1]:
                try:
                    public_id = photo_data[1].split('/')[-1].split('.')[0]
                    cloudinary.uploader.destroy(f"love_app/{public_id}")
                except Exception as e:
                    print(f"Erreur suppression Cloudinary: {e}")
            
            cursor.execute('DELETE FROM photos WHERE id = %s', (photo_id,))
            log_activity(user, 'photo_deleted', f'Photo ID: {photo_id}')
            flash('Photo supprimée avec succès', 'success')
        else:
            flash('Vous ne pouvez supprimer que vos propres photos', 'error')
    else:
        cursor.execute('SELECT auteur, cloudinary_url FROM photos WHERE id = ?', (photo_id,))
        photo = cursor.fetchone()
        if photo and photo['auteur'] == user:
            # Supprimer de Cloudinary
            if photo['cloudinary_url']:
                try:
                    public_id = photo['cloudinary_url'].split('/')[-1].split('.')[0]
                    cloudinary.uploader.destroy(f"love_app/{public_id}")
                except Exception as e:
                    print(f"Erreur suppression Cloudinary: {e}")
            
            cursor.execute('DELETE FROM photos WHERE id = ?', (photo_id,))
            log_activity(user, 'photo_deleted', f'Photo ID: {photo_id}')
            flash('Photo supprimée avec succès', 'success')
        else:
            flash('Vous ne pouvez supprimer que vos propres photos', 'error')
    
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('galerie'))

@app.route('/lettres')
def lettres():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            SELECT * FROM letters 
            WHERE recipient = %s 
            ORDER BY created_at DESC
        ''', (user,))
        letters_data = cursor.fetchall()
        received_letters = []
        for row in letters_data:
            received_letters.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'sender': row[3],
                'recipient': row[4],
                'is_read': row[5],
                'created_at': row[6]
            })
        
        cursor.execute('''
            SELECT * FROM letters 
            WHERE sender = %s 
            ORDER BY created_at DESC
        ''', (user,))
        sent_letters_data = cursor.fetchall()
        sent_letters = []
        for row in sent_letters_data:
            sent_letters.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'sender': row[3],
                'recipient': row[4],
                'is_read': row[5],
                'created_at': row[6]
            })
    else:
        cursor.execute('''
            SELECT * FROM letters 
            WHERE recipient = ? 
            ORDER BY created_at DESC
        ''', (user,))
        received_letters = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT * FROM letters 
            WHERE sender = ? 
            ORDER BY created_at DESC
        ''', (user,))
        sent_letters = [dict(row) for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return render_template('lettres.html', 
                         received_letters=received_letters,
                         sent_letters=sent_letters)

@app.route('/ecrire_lettre', methods=['GET', 'POST'])
def ecrire_lettre():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        recipient = request.form['recipient'].strip()
        
        if title and content and recipient:
            sender = session['user']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if DB_TYPE == 'postgresql':
                cursor.execute('''
                    INSERT INTO letters (title, content, sender, recipient)
                    VALUES (%s, %s, %s, %s)
                ''', (title, content, sender, recipient))
            else:
                cursor.execute('''
                    INSERT INTO letters (title, content, sender, recipient)
                    VALUES (?, ?, ?, ?)
                ''', (title, content, sender, recipient))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            log_activity(sender, 'letter_sent', f'À: {recipient}, Titre: {title}')
            flash('Lettre envoyée avec succès ! 💌', 'success')
            return redirect(url_for('lettres'))
        else:
            flash('Veuillez remplir tous les champs', 'error')
    
    return render_template('ecrire_lettre.html')

@app.route('/lire_lettre/<int:letter_id>')
def lire_lettre(letter_id):
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT * FROM letters WHERE id = %s', (letter_id,))
        letter_data = cursor.fetchone()
        if letter_data:
            letter = {
                'id': letter_data[0],
                'title': letter_data[1],
                'content': letter_data[2],
                'sender': letter_data[3],
                'recipient': letter_data[4],
                'is_read': letter_data[5],
                'created_at': letter_data[6]
            }
            
            # Marquer comme lu si c'est le destinataire
            if letter['recipient'] == user and not letter['is_read']:
                cursor.execute('UPDATE letters SET is_read = TRUE WHERE id = %s', (letter_id,))
                conn.commit()
        else:
            letter = None
    else:
        cursor.execute('SELECT * FROM letters WHERE id = ?', (letter_id,))
        letter_row = cursor.fetchone()
        if letter_row:
            letter = dict(letter_row)
            
            # Marquer comme lu si c'est le destinataire
            if letter['recipient'] == user and not letter['is_read']:
                cursor.execute('UPDATE letters SET is_read = 1 WHERE id = ?', (letter_id,))
                conn.commit()
        else:
            letter = None
    
    cursor.close()
    conn.close()
    
    if not letter:
        flash('Lettre non trouvée', 'error')
        return redirect(url_for('lettres'))
    
    if letter['recipient'] != user and letter['sender'] != user:
        flash('Vous n\'avez pas accès à cette lettre', 'error')
        return redirect(url_for('lettres'))
    
    return render_template('lire_lettre.html', letter=letter)

@app.route('/memories')
def memories():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            SELECT * FROM memories 
            ORDER BY date_memory DESC
        ''')
        memories_data = cursor.fetchall()
        memories_list = []
        for row in memories_data:
            memories_list.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'date_memory': row[3],
                'author': row[4],
                'is_anniversary': row[5],
                'created_at': row[6]
            })
    else:
        cursor.execute('''
            SELECT * FROM memories 
            ORDER BY date_memory DESC
        ''')
        memories_list = [dict(row) for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return render_template('memories.html', memories=memories_list)

@app.route('/add_memory', methods=['GET', 'POST'])
def add_memory():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form['description'].strip()
        date_memory = request.form['date_memory']
        is_anniversary = 'is_anniversary' in request.form
        
        if title and description and date_memory:
            author = session['user']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if DB_TYPE == 'postgresql':
                cursor.execute('''
                    INSERT INTO memories (title, description, date_memory, author, is_anniversary)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (title, description, date_memory, author, is_anniversary))
            else:
                cursor.execute('''
                    INSERT INTO memories (title, description, date_memory, author, is_anniversary)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, description, date_memory, author, is_anniversary))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            log_activity(author, 'memory_added', f'Titre: {title}')
            flash('Souvenir ajouté avec succès ! 📝', 'success')
            return redirect(url_for('memories'))
        else:
            flash('Veuillez remplir tous les champs obligatoires', 'error')
    
    return render_template('add_memory.html')

@app.route('/delete_memory/<int:memory_id>')
def delete_memory(memory_id):
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que l'utilisateur est l'auteur
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT author FROM memories WHERE id = %s', (memory_id,))
        memory_data = cursor.fetchone()
        if memory_data and memory_data[0] == user:
            cursor.execute('DELETE FROM memories WHERE id = %s', (memory_id,))
            log_activity(user, 'memory_deleted', f'Memory ID: {memory_id}')
            flash('Souvenir supprimé avec succès', 'success')
        else:
            flash('Vous ne pouvez supprimer que vos propres souvenirs', 'error')
    else:
        cursor.execute('SELECT author FROM memories WHERE id = ?', (memory_id,))
        memory = cursor.fetchone()
        if memory and memory['author'] == user:
            cursor.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
            log_activity(user, 'memory_deleted', f'Memory ID: {memory_id}')
            flash('Souvenir supprimé avec succès', 'success')
        else:
            flash('Vous ne pouvez supprimer que vos propres souvenirs', 'error')
    
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('memories'))

@app.route('/calendar')
def calendar():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            SELECT * FROM calendar_events 
            ORDER BY event_date
        ''')
        events_data = cursor.fetchall()
        events = []
        for row in events_data:
            events.append({
                'id': row[0],
                'title': row[1],
                'event_date': row[2],
                'event_type': row[3],
                'description': row[4],
                'created_by': row[5],
                'created_at': row[6]
            })
    else:
        cursor.execute('''
            SELECT * FROM calendar_events 
            ORDER BY event_date
        ''')
        events = [dict(row) for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return render_template('calendar.html', events=events)

@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    if request.method == 'POST':
        title = request.form['title'].strip()
        event_date = request.form['event_date']
        event_type = request.form['event_type']
        description = request.form.get('description', '').strip()
        
        if title and event_date:
            created_by = session['user']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if DB_TYPE == 'postgresql':
                cursor.execute('''
                    INSERT INTO calendar_events (title, event_date, event_type, description, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (title, event_date, event_type, description, created_by))
            else:
                cursor.execute('''
                    INSERT INTO calendar_events (title, event_date, event_type, description, created_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, event_date, event_type, description, created_by))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            log_activity(created_by, 'event_added', f'Titre: {title}')
            flash('Événement ajouté avec succès ! 📅', 'success')
            return redirect(url_for('calendar'))
        else:
            flash('Veuillez remplir tous les champs obligatoires', 'error')
    
    return render_template('add_event.html')

@app.route('/delete_event/<int:event_id>')
def delete_event(event_id):
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que l'utilisateur est le créateur
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT created_by FROM calendar_events WHERE id = %s', (event_id,))
        event_data = cursor.fetchone()
        if event_data and event_data[0] == user:
            cursor.execute('DELETE FROM calendar_events WHERE id = %s', (event_id,))
            log_activity(user, 'event_deleted', f'Event ID: {event_id}')
            flash('Événement supprimé avec succès', 'success')
        else:
            flash('Vous ne pouvez supprimer que vos propres événements', 'error')
    else:
        cursor.execute('SELECT created_by FROM calendar_events WHERE id = ?', (event_id,))
        event = cursor.fetchone()
        if event and event['created_by'] == user:
            cursor.execute('DELETE FROM calendar_events WHERE id = ?', (event_id,))
            log_activity(user, 'event_deleted', f'Event ID: {event_id}')
            flash('Événement supprimé avec succès', 'success')
        else:
            flash('Vous ne pouvez supprimer que vos propres événements', 'error')
    
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('calendar'))

@app.route('/challenges')
def challenges():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            SELECT * FROM challenges 
            WHERE is_active = TRUE
            ORDER BY points DESC
        ''')
        challenges_data = cursor.fetchall()
        challenges_list = []
        for row in challenges_data:
            challenges_list.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'challenge_type': row[3],
                'points': row[4],
                'is_active': row[5],
                'completed_by': row[6],
                'completed_date': row[7],
                'created_at': row[8]
            })
    else:
        cursor.execute('''
            SELECT * FROM challenges 
            WHERE is_active = 1
            ORDER BY points DESC
        ''')
        challenges_list = [dict(row) for row in cursor.fetchall()]
    
    # Vérifier les défis complétés par l'utilisateur
    completed_challenges = []
    for challenge in challenges_list:
        if challenge['completed_by'] and user in challenge['completed_by']:
            completed_challenges.append(challenge['id'])
    
    cursor.close()
    conn.close()
    
    return render_template('challenges.html', 
                         challenges=challenges_list,
                         completed_challenges=completed_challenges)

@app.route('/complete_challenge/<int:challenge_id>')
def complete_challenge(challenge_id):
    if not is_site_unlocked() and not session.get('special_access'):
        return jsonify({'error': 'Site verrouillé'}), 403
    
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT completed_by FROM challenges WHERE id = %s', (challenge_id,))
        challenge_data = cursor.fetchone()
        if challenge_data:
            completed_by = challenge_data[0] or ''
            if user not in completed_by:
                new_completed_by = completed_by + f',{user}' if completed_by else user
                cursor.execute('''
                    UPDATE challenges 
                    SET completed_by = %s, completed_date = CURRENT_TIMESTAMP 
                    WHERE id = %s
                ''', (new_completed_by, challenge_id))
                conn.commit()
                
                log_activity(user, 'challenge_completed', f'Challenge ID: {challenge_id}')
                flash('Défi complété ! Points gagnés ! 🎉', 'success')
            else:
                flash('Vous avez déjà complété ce défi', 'info')
    else:
        cursor.execute('SELECT completed_by FROM challenges WHERE id = ?', (challenge_id,))
        challenge = cursor.fetchone()
        if challenge:
            completed_by = challenge['completed_by'] or ''
            if user not in completed_by:
                new_completed_by = completed_by + f',{user}' if completed_by else user
                cursor.execute('''
                    UPDATE challenges 
                    SET completed_by = ?, completed_date = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (new_completed_by, challenge_id))
                conn.commit()
                
                log_activity(user, 'challenge_completed', f'Challenge ID: {challenge_id}')
                flash('Défi complété ! Points gagnés ! 🎉', 'success')
            else:
                flash('Vous avez déjà complété ce défi', 'info')
    
    cursor.close()
    conn.close()
    return redirect(url_for('challenges'))

@app.route('/mood')
def mood():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    return render_template('mood.html')

@app.route('/get_mood_verse/<mood_type>')
def get_mood_verse(mood_type):
    if not is_site_unlocked() and not session.get('special_access'):
        return jsonify({'error': 'Site verrouillé'}), 403
    
    verses = load_mood_verses()
    mood_verses = verses.get(mood_type, [])
    
    if mood_verses:
        verse = random.choice(mood_verses)
        log_activity(session['user'], 'mood_check', f'Mood: {mood_type}')
        return jsonify(verse)
    else:
        return jsonify({
            'arabic': 'لَا تَقْنَطُوا مِن رَّحْمَةِ اللَّهِ',
            'french': 'Ne désespérez pas de la miséricorde d\'Allah',
            'explanation': 'Allah est toujours miséricordieux envers Ses serviteurs.',
            'conclusion': 'Ayez confiance en la miséricorde divine.'
        })

@app.route('/profile')
def profile():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            SELECT username, favorite_color, visit_count, last_login, created_at 
            FROM users WHERE username = %s
        ''', (user,))
        user_data = cursor.fetchone()
        if user_data:
            profile_data = {
                'username': user_data[0],
                'favorite_color': user_data[1],
                'visit_count': user_data[2],
                'last_login': user_data[3],
                'created_at': user_data[4]
            }
        else:
            profile_data = None
        
        # Statistiques de l'utilisateur
        cursor.execute('SELECT COUNT(*) FROM phrases WHERE auteur = %s', (user,))
        user_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM photos WHERE auteur = %s', (user,))
        user_photos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM letters WHERE sender = %s', (user,))
        user_letters_sent = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM letters WHERE recipient = %s', (user,))
        user_letters_received = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM memories WHERE author = %s', (user,))
        user_memories = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM calendar_events WHERE created_by = %s', (user,))
        user_events = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM challenges WHERE completed_by LIKE %s', (f'%{user}%',))
        user_challenges = cursor.fetchone()[0]
        
        # Activités récentes
        cursor.execute('''
            SELECT action, details, date 
            FROM activities 
            WHERE username = %s 
            ORDER BY date DESC 
            LIMIT 10
        ''', (user,))
        activities_data = cursor.fetchall()
        activities = []
        for row in activities_data:
            activities.append({
                'action': row[0],
                'details': row[1],
                'date': row[2]
            })
    else:
        cursor.execute('''
            SELECT username, favorite_color, visit_count, last_login, created_at 
            FROM users WHERE username = ?
        ''', (user,))
        user_row = cursor.fetchone()
        if user_row:
            profile_data = dict(user_row)
        else:
            profile_data = None
        
        # Statistiques de l'utilisateur
        cursor.execute('SELECT COUNT(*) FROM phrases WHERE auteur = ?', (user,))
        user_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM photos WHERE auteur = ?', (user,))
        user_photos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM letters WHERE sender = ?', (user,))
        user_letters_sent = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM letters WHERE recipient = ?', (user,))
        user_letters_received = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM memories WHERE author = ?', (user,))
        user_memories = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM calendar_events WHERE created_by = ?', (user,))
        user_events = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM challenges WHERE completed_by LIKE ?', (f'%{user}%',))
        user_challenges = cursor.fetchone()[0]
        
        # Activités récentes
        cursor.execute('''
            SELECT action, details, date 
            FROM activities 
            WHERE user = ? 
            ORDER BY date DESC 
            LIMIT 10
        ''', (user,))
        activities_rows = cursor.fetchall()
        activities = [dict(row) for row in activities_rows]
    
    cursor.close()
    conn.close()
    
    stats = {
        'messages': user_messages,
        'photos': user_photos,
        'letters_sent': user_letters_sent,
        'letters_received': user_letters_received,
        'memories': user_memories,
        'events': user_events,
        'challenges': user_challenges
    }
    
    return render_template('profile.html', 
                         profile=profile_data,
                         stats=stats,
                         activities=activities)

@app.route('/update_profile_color', methods=['POST'])
def update_profile_color():
    if not is_site_unlocked() and not session.get('special_access'):
        return jsonify({'error': 'Site verrouillé'}), 403
    
    user = session['user']
    color = request.json.get('color', '#ffdde1')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('UPDATE users SET favorite_color = %s WHERE username = %s', (color, user))
    else:
        cursor.execute('UPDATE users SET favorite_color = ? WHERE username = ?', (color, user))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    log_activity(user, 'color_updated', f'Color: {color}')
    return jsonify({'success': True, 'color': color})

@app.route('/search')
def search():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    
    if not query:
        return render_template('search.html', results=[], query='', search_type=search_type)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    results = []
    
    if search_type in ['all', 'messages']:
        if DB_TYPE == 'postgresql':
            cursor.execute('''
                SELECT * FROM phrases 
                WHERE texte ILIKE %s OR tags ILIKE %s
                ORDER BY date DESC
            ''', (f'%{query}%', f'%{query}%'))
            messages_data = cursor.fetchall()
            for row in messages_data:
                results.append({
                    'type': 'message',
                    'id': row[0],
                    'texte': row[1],
                    'auteur': row[2],
                    'date': row[3],
                    'couleur': row[4],
                    'tags': row[5]
                })
        else:
            cursor.execute('''
                SELECT * FROM phrases 
                WHERE texte LIKE ? OR tags LIKE ?
                ORDER BY date DESC
            ''', (f'%{query}%', f'%{query}%'))
            messages_rows = cursor.fetchall()
            for row in messages_rows:
                results.append({
                    'type': 'message',
                    'id': row['id'],
                    'texte': row['texte'],
                    'auteur': row['auteur'],
                    'date': row['date'],
                    'couleur': row['couleur'],
                    'tags': row['tags']
                })
    
    if search_type in ['all', 'photos']:
        if DB_TYPE == 'postgresql':
            cursor.execute('''
                SELECT * FROM photos 
                WHERE legende ILIKE %s
                ORDER BY date DESC
            ''', (f'%{query}%',))
            photos_data = cursor.fetchall()
            for row in photos_data:
                results.append({
                    'type': 'photo',
                    'id': row[0],
                    'filename': row[1],
                    'cloudinary_url': row[2],
                    'legende': row[3],
                    'auteur': row[4],
                    'date': row[5]
                })
        else:
            cursor.execute('''
                SELECT * FROM photos 
                WHERE legende LIKE ?
                ORDER BY date DESC
            ''', (f'%{query}%',))
            photos_rows = cursor.fetchall()
            for row in photos_rows:
                results.append({
                    'type': 'photo',
                    'id': row['id'],
                    'filename': row['filename'],
                    'cloudinary_url': row['cloudinary_url'],
                    'legende': row['legende'],
                    'auteur': row['auteur'],
                    'date': row['date']
                })
    
    if search_type in ['all', 'memories']:
        if DB_TYPE == 'postgresql':
            cursor.execute('''
                SELECT * FROM memories 
                WHERE title ILIKE %s OR description ILIKE %s
                ORDER BY date_memory DESC
            ''', (f'%{query}%', f'%{query}%'))
            memories_data = cursor.fetchall()
            for row in memories_data:
                results.append({
                    'type': 'memory',
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'date_memory': row[3],
                    'author': row[4]
                })
        else:
            cursor.execute('''
                SELECT * FROM memories 
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY date_memory DESC
            ''', (f'%{query}%', f'%{query}%'))
            memories_rows = cursor.fetchall()
            for row in memories_rows:
                results.append({
                    'type': 'memory',
                    'id': row['id'],
                    'title': row['title'],
                    'description': row['description'],
                    'date_memory': row['date_memory'],
                    'author': row['author']
                })
    
    cursor.close()
    conn.close()
    
    log_activity(session['user'], 'search', f'Query: {query}, Type: {search_type}')
    return render_template('search.html', results=results, query=query, search_type=search_type)

@app.route('/api/stats')
def api_stats():
    if not is_site_unlocked() and not session.get('special_access'):
        return jsonify({'error': 'Site verrouillé'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT COUNT(*) FROM phrases')
        total_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM photos')
        total_photos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM letters')
        total_letters = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM memories')
        total_memories = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM calendar_events')
        total_events = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM challenges WHERE completed_by IS NOT NULL')
        completed_challenges = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
    else:
        cursor.execute('SELECT COUNT(*) FROM phrases')
        total_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM photos')
        total_photos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM letters')
        total_letters = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM memories')
        total_memories = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM calendar_events')
        total_events = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM challenges WHERE completed_by IS NOT NULL')
        completed_challenges = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    stats = {
        'total_messages': total_messages,
        'total_photos': total_photos,
        'total_letters': total_letters,
        'total_memories': total_memories,
        'total_events': total_events,
        'completed_challenges': completed_challenges,
        'total_users': total_users
    }
    
    return jsonify(stats)

@app.route('/api/user_activity')
def api_user_activity():
    if not is_site_unlocked() and not session.get('special_access'):
        return jsonify({'error': 'Site verrouillé'}), 403
    
    user = session['user']
    limit = request.args.get('limit', 10, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            SELECT action, details, date 
            FROM activities 
            WHERE username = %s 
            ORDER BY date DESC 
            LIMIT %s
        ''', (user, limit))
        activities_data = cursor.fetchall()
        activities = []
        for row in activities_data:
            activities.append({
                'action': row[0],
                'details': row[1],
                'date': row[2].isoformat() if row[2] else None
            })
    else:
        cursor.execute('''
            SELECT action, details, date 
            FROM activities 
            WHERE user = ? 
            ORDER BY date DESC 
            LIMIT ?
        ''', (user, limit))
        activities_rows = cursor.fetchall()
        activities = []
        for row in activities_rows:
            activities.append({
                'action': row['action'],
                'details': row['details'],
                'date': row['date']
            })
    
    cursor.close()
    conn.close()
    
    return jsonify(activities)

# Créer des templates d'erreur basiques
@app.errorhandler(404)
def page_not_found(e):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page non trouvée</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: linear-gradient(135deg, #ffdde1, #ee9ca7); }
            h1 { color: #d63384; }
            a { color: #d63384; text-decoration: none; }
        </style>
    </head>
    <body>
        <h1>404 - Page non trouvée</h1>
        <p>Désolé, la page que vous cherchez n'existe pas.</p>
        <p><a href="/">Retour à l'accueil</a></p>
    </body>
    </html>
    """, 404

@app.errorhandler(500)
def internal_server_error(e):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Erreur serveur</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: linear-gradient(135deg, #ffdde1, #ee9ca7); }
            h1 { color: #d63384; }
            a { color: #d63384; text-decoration: none; }
        </style>
    </head>
    <body>
        <h1>500 - Erreur interne du serveur</h1>
        <p>Une erreur s'est produite. Veuillez réessayer plus tard.</p>
        <p><a href="/">Retour à l'accueil</a></p>
    </body>
    </html>
    """, 500

@app.route('/test_db')
def test_db():
    """Route de test pour vérifier la connexion à la base de données"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DB_TYPE == 'postgresql':
            cursor.execute('SELECT version()')
            version = cursor.fetchone()[0]
        else:
            cursor.execute('SELECT sqlite_version()')
            version = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'database_type': DB_TYPE,
            'version': version,
            'unlock_date': UNLOCK_DATE.isoformat(),
            'current_time': datetime.now().isoformat(),
            'is_unlocked': is_site_unlocked()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'database_type': DB_TYPE
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)