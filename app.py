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
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '68e60b4d247647f18db672d7b14d85dfdd7a1a69cdeb35144cc7b5563f369e23')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configuration Cloudinary
app.config['CLOUDINARY_CLOUD_NAME'] = os.environ.get('CLOUDINARY_CLOUD_NAME', 'djbdv90jr')
app.config['CLOUDINARY_API_KEY'] = os.environ.get('CLOUDINARY_API_KEY', '455591489376377')
app.config['CLOUDINARY_API_SECRET'] = os.environ.get('CLOUDINARY_API_SECRET', 'xfudLM75vr_yKqrpHVAr87NNhDo')

# 🔥 CONFIGURATION UNIQUE - PostgreSQL Neon.tech uniquement
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_oC3pqDdPf5Ru@ep-lingering-mountain-afolq7j6-pooler.c-2.us-west-2.aws.neon.tech/neondb?sslmode=require')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
DB_TYPE = 'postgresql'  # Toujours PostgreSQL sur Render

# Configuration de connexion PostgreSQL
parsed_url = urlparse(DATABASE_URL)
app.config['DATABASE_CONFIG'] = {
    'dbname': parsed_url.path.split('/')[-1],  # Récupérer 'neondb'
    'user': parsed_url.username,
    'password': parsed_url.password,
    'host': parsed_url.hostname,
    'port': parsed_url.port,
    'sslmode': 'require'
}

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
    """Connexion à PostgreSQL Neon.tech"""
    conn = psycopg2.connect(**app.config['DATABASE_CONFIG'])
    conn.autocommit = True
    return conn

def init_db():
    """Initialise la base de données avec toutes les tables nécessaires"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
            user TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Créer les utilisateurs par défaut
    cursor.execute("SELECT username FROM users")
    existing_users = [row[0] for row in cursor.fetchall()]
    
    # Mettre à jour les utilisateurs avec les nouveaux noms et mots de passe
    if 'maninka mousso' not in existing_users:
        cursor.execute('''
            INSERT INTO users (username, password_hash, favorite_color)
            VALUES (%s, %s, %s)
        ''', ('maninka mousso', generate_password_hash('Elle a toujours été belle'), '#ffdde1'))
    
    if 'panda bg' not in existing_users:
        cursor.execute('''
            INSERT INTO users (username, password_hash, favorite_color)
            VALUES (%s, %s, %s)
        ''', ('panda bg', generate_password_hash('La lune est belle ce soir'), '#e1f5fe'))
    
    # Ajouter quelques défis par défaut
    cursor.execute("SELECT COUNT(*) FROM challenges")
    existing_challenges_count = cursor.fetchone()[0]
    
    if existing_challenges_count == 0:
        default_challenges = [
            ("Écris un message d'amour", "Partage un message tendre avec ton amour", "message", 15),
            ("Partage une photo souvenir", "Upload une photo qui vous rappelle un beau moment", "photo", 20),
            ("Vérifie ton humeur", "Utilise la fonction humeur du jour", "mood", 10),
            ("Ajoute un souvenir précieux", "Immortalise un moment spécial dans vos souvenirs", "memory", 25),
            ("Envoie une lettre d'amour", "Écris une belle lettre à ton partenaire", "letter", 30)
        ]
        
        for title, desc, c_type, points in default_challenges:
            cursor.execute('''
                INSERT INTO challenges (title, description, challenge_type, points)
                VALUES (%s, %s, %s, %s)
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
    
    cursor.execute('''
        INSERT INTO activities (user, action, details)
        VALUES (%s, %s, %s)
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
        
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Convertir en dict pour un accès cohérent
        user = None
        if user_data:
            user = {
                'id': user_data[0],
                'username': user_data[1],
                'password_hash': user_data[2],
                'favorite_color': user_data[3],
                'visit_count': user_data[4],
                'last_login': user_data[5],
                'created_at': user_data[6]
            }
        
        if user and check_password_hash(user['password_hash'], password):
            session['login_attempts'][username] = 0
            session['user'] = username
            
            # Mettre à jour les statistiques de connexion
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users 
                SET visit_count = visit_count + 1, last_login = CURRENT_TIMESTAMP
                WHERE username = %s
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
            
            cursor.execute('''
                INSERT INTO phrases (texte, auteur, couleur, tags)
                VALUES (%s, %s, %s, %s)
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
    cursor.execute('SELECT COUNT(*) FROM phrases')
    total = cursor.fetchone()[0]
    
    # Récupérer les messages pour la page actuelle
    offset = (page - 1) * per_page
    
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
    
    # Statistiques
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
    
    stats = {
        'total_messages': total_messages,
        'total_photos': total_photos,
        'favoris_count': favoris_count
    }
    
    # Convertir user_info en dict
    user_info = {}
    if user_info_data:
        user_info = {
            'visit_count': user_info_data[0],
            'favorite_color': user_info_data[1]
        }
    
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
    
    cursor.execute('SELECT est_favori FROM phrases WHERE id = %s', (phrase_id,))
    phrase_data = cursor.fetchone()
    if phrase_data:
        new_status = not phrase_data[0]
        cursor.execute('UPDATE phrases SET est_favori = %s WHERE id = %s', (new_status, phrase_id))
    
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
    
    cursor.execute('UPDATE phrases SET likes = likes + 1 WHERE id = %s', (phrase_id,))
    cursor.execute('SELECT likes FROM phrases WHERE id = %s', (phrase_id,))
    likes_data = cursor.fetchone()
    likes = likes_data[0] if likes_data else 0
    
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
    cursor.execute('SELECT auteur FROM phrases WHERE id = %s', (phrase_id,))
    phrase_data = cursor.fetchone()
    if phrase_data and phrase_data[0] == user:
        cursor.execute('DELETE FROM phrases WHERE id = %s', (phrase_id,))
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
    cursor.execute('SELECT COUNT(*) FROM photos')
    total = cursor.fetchone()[0]
    
    # Récupérer les photos pour la page actuelle
    offset = (page - 1) * per_page
    
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
    
    return render_template('galerie.html', photos=photos, user=session['user'], pagination=pagination)

@app.route('/upload', methods=['POST'])
def upload_file():
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
        # 🔥 UTILISER CLOUDINARY UNIQUEMENT
        cloudinary_result = upload_to_cloudinary(file)
        
        if cloudinary_result['success']:
            # Sauvegarde Cloudinary réussie
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO photos (filename, cloudinary_url, legende, auteur, file_size)
                VALUES (%s, %s, %s, %s, %s)
            ''', (cloudinary_result['filename'], cloudinary_result['url'], legende, session['user'], cloudinary_result['file_size']))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            log_activity(session['user'], 'photo_uploaded', f'Photo: {cloudinary_result["filename"]}')
            flash('Photo uploadée avec succès vers Cloudinary ! 📸', 'success')
        else:
            flash('Erreur Cloudinary: ' + cloudinary_result.get('error', 'Unknown error'), 'error')
    else:
        flash('Type de fichier non autorisé', 'error')
    
    return redirect(url_for('galerie'))

@app.route('/like_photo/<int:photo_id>')
def like_photo(photo_id):
    if not is_site_unlocked() and not session.get('special_access'):
        return jsonify({'error': 'Site verrouillé'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE photos SET likes = likes + 1 WHERE id = %s', (photo_id,))
    cursor.execute('SELECT likes FROM photos WHERE id = %s', (photo_id,))
    likes_data = cursor.fetchone()
    likes = likes_data[0] if likes_data else 0
    
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
    cursor.execute('SELECT auteur, filename, cloudinary_url FROM photos WHERE id = %s', (photo_id,))
    photo_data = cursor.fetchone()
    if photo_data and photo_data[0] == user:
        # Supprimer de Cloudinary si applicable
        if photo_data[2]:  # cloudinary_url existe
            try:
                public_id = photo_data[2].split('/')[-1].split('.')[0]
                cloudinary.uploader.destroy(public_id)
            except Exception as e:
                print(f"Erreur suppression Cloudinary: {e}")
        
        cursor.execute('DELETE FROM photos WHERE id = %s', (photo_id,))
        log_activity(user, 'photo_deleted', f'Photo ID: {photo_id}')
        flash('Photo supprimée avec succès', 'success')
    else:
        flash('Vous ne pouvez supprimer que vos propres photos', 'error')
    
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('galerie'))

@app.route('/mood', methods=['GET', 'POST'])
def mood():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    if request.method == 'POST':
        selected_mood = request.form['mood']
        log_activity(session['user'], 'mood_checked', f'Mood: {selected_mood}')
        return redirect(url_for('mood_result', mood=selected_mood))
    
    return render_template('mood.html', user=session['user'])

@app.route('/mood_result/<mood>')
def mood_result(mood):
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    verses = load_mood_verses()
    
    if mood in verses and verses[mood]:
        verse = random.choice(verses[mood])
    else:
        verse = {
            "arabic": "وَاللَّهُ يُحِبُّ الْمُحْسِنِينَ",
            "french": "Et Allah aime les bienfaisants",
            "explanation": "Allah aime ceux qui fait le bien.",
            "conclusion": "Continue à faire le bien, Allah t'aime."
        }
    
    return render_template('mood_result.html', mood=mood, verse=verse, user=session['user'])

@app.route('/search')
def search():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    query = request.args.get('q', '').strip()
    phrases = []
    
    if query:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM phrases 
            WHERE texte LIKE %s OR tags LIKE %s
            ORDER BY date DESC
        ''', (f'%{query}%', f'%{query}%'))
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
        
        cursor.close()
        conn.close()
        
        log_activity(session['user'], 'search', f'Query: {query}')
    
    return render_template('search_results.html', phrases=phrases, query=query, user=session['user'])

@app.route('/stats')
def stats():
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Statistiques générales
    cursor.execute('SELECT COUNT(*) FROM phrases')
    total_messages = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM photos')
    total_photos = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM phrases WHERE est_favori = TRUE')
    favoris_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM letters')
    total_letters = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM memories')
    total_memories = cursor.fetchone()[0]
    
    # Messages par utilisateur
    cursor.execute('''
        SELECT auteur, COUNT(*) as count 
        FROM phrases 
        GROUP BY auteur 
        ORDER BY count DESC
    ''')
    messages_by_user_data = cursor.fetchall()
    messages_by_user = []
    for row in messages_by_user_data:
        messages_by_user.append({'auteur': row[0], 'count': row[1]})
    
    # Photos par utilisateur
    cursor.execute('''
        SELECT auteur, COUNT(*) as count 
        FROM photos 
        GROUP BY auteur 
        ORDER BY count DESC
    ''')
    photos_by_user_data = cursor.fetchall()
    photos_by_user = []
    for row in photos_by_user_data:
        photos_by_user.append({'auteur': row[0], 'count': row[1]})
    
    # Activité récente
    cursor.execute('''
        SELECT * FROM activities 
        ORDER BY date DESC 
        LIMIT 20
    ''')
    activities_data = cursor.fetchall()
    recent_activity = []
    for row in activities_data:
        recent_activity.append({
            'id': row[0],
            'user': row[1],
            'action': row[2],
            'details': row[3],
            'date': row[4]
        })
    
    cursor.close()
    conn.close()
    
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
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)