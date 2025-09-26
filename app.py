import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import random

app = Flask(__name__)

# Configuration sécurisée pour la production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configuration de la base de données
DATABASE = os.environ.get('DATABASE_PATH', 'instance/database.db')

# Date de déverrouillage (27 septembre 2025)
UNLOCK_DATE = datetime(2025, 9, 25, 23, 00, 59)

# Extensions de fichiers autorisées
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialise la base de données avec toutes les tables nécessaires"""
    conn = get_db_connection()
    
    # Table des utilisateurs
    conn.execute('''
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
    
    # Table des phrases
    conn.execute('''
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
    
    # Table des photos
    conn.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            legende TEXT,
            auteur TEXT NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_size INTEGER,
            likes INTEGER DEFAULT 0
        )
    ''')
    
    # Table des lettres
    conn.execute('''
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
    
    # Table des souvenirs
    conn.execute('''
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
    
    # Table des événements du calendrier
    conn.execute('''
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
    
    # Table des défis
    conn.execute('''
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
    
    # Table des activités
    conn.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Créer les utilisateurs par défaut si ils n'existent pas
    existing_users = conn.execute('SELECT username FROM users').fetchall()
    existing_usernames = [user['username'] for user in existing_users]
    
    # Mettre à jour les utilisateurs avec les nouveaux noms et mots de passe
    if 'maninka mousso' not in existing_usernames:
        # Supprimer l'ancien utilisateur fanta s'il existe
        conn.execute('DELETE FROM users WHERE username = ?', ('fanta',))
        # Créer le nouvel utilisateur
        conn.execute('''
            INSERT INTO users (username, password_hash, favorite_color)
            VALUES (?, ?, ?)
        ''', ('maninka mousso', generate_password_hash('Elle a toujours été belle'), '#ffdde1'))
    
    if 'panda bg' not in existing_usernames:
        # Supprimer l'ancien utilisateur saïd s'il existe
        conn.execute('DELETE FROM users WHERE username = ?', ('saïd',))
        # Créer le nouvel utilisateur
        conn.execute('''
            INSERT INTO users (username, password_hash, favorite_color)
            VALUES (?, ?, ?)
        ''', ('panda bg', generate_password_hash('La lune est belle ce soir'), '#e1f5fe'))
    
    # Ajouter quelques défis par défaut
    existing_challenges = conn.execute('SELECT COUNT(*) as count FROM challenges').fetchone()
    if existing_challenges['count'] == 0:
        default_challenges = [
            ("Écris un message d'amour", "Partage un message tendre avec ton amour", "message", 15),
            ("Partage une photo souvenir", "Upload une photo qui vous rappelle un beau moment", "photo", 20),
            ("Vérifie ton humeur", "Utilise la fonction humeur du jour", "mood", 10),
            ("Ajoute un souvenir précieux", "Immortalise un moment spécial dans vos souvenirs", "memory", 25),
            ("Envoie une lettre d'amour", "Écris une belle lettre à ton partenaire", "letter", 30)
        ]
        
        for title, desc, c_type, points in default_challenges:
            conn.execute('''
                INSERT INTO challenges (title, description, challenge_type, points)
                VALUES (?, ?, ?, ?)
            ''', (title, desc, c_type, points))
    
    conn.commit()
    conn.close()

def log_activity(user, action, details=None):
    """Enregistre une activité utilisateur"""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO activities (user, action, details)
        VALUES (?, ?, ?)
    ''', (user, action, details))
    conn.commit()
    conn.close()

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
os.makedirs('instance', exist_ok=True)

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
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            # Réinitialiser les tentatives en cas de succès
            session['login_attempts'][username] = 0
            session['user'] = username
            
            # Mettre à jour les statistiques de connexion
            conn = get_db_connection()
            conn.execute('''
                UPDATE users 
                SET visit_count = visit_count + 1, last_login = CURRENT_TIMESTAMP
                WHERE username = ?
            ''', (username,))
            conn.commit()
            conn.close()
            
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
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO phrases (texte, auteur, couleur, tags)
                VALUES (?, ?, ?, ?)
            ''', (texte, user, couleur, tags))
            conn.commit()
            conn.close()
            
            log_activity(user, 'message_added', f'Message: {texte[:50]}...')
            flash('Message ajouté avec succès ! 💖', 'success')
        
        return redirect(url_for('index'))
    
    # Récupérer les messages avec pagination
    conn = get_db_connection()
    
    # Compter le total des messages
    total = conn.execute('SELECT COUNT(*) FROM phrases').fetchone()[0]
    
    # Récupérer les messages pour la page actuelle
    offset = (page - 1) * per_page
    phrases = conn.execute('''
        SELECT * FROM phrases 
        ORDER BY date DESC 
        LIMIT ? OFFSET ?
    ''', (per_page, offset)).fetchall()
    
    # Statistiques
    stats = {
        'total_messages': conn.execute('SELECT COUNT(*) FROM phrases').fetchone()[0],
        'total_photos': conn.execute('SELECT COUNT(*) FROM photos').fetchone()[0],
        'favoris_count': conn.execute('SELECT COUNT(*) FROM phrases WHERE est_favori = 1').fetchone()[0]
    }
    
    # Lettres non lues
    unread_letters = conn.execute('''
        SELECT COUNT(*) FROM letters 
        WHERE recipient = ? AND is_read = 0
    ''', (user,)).fetchone()[0]
    
    # Informations utilisateur
    user_info = conn.execute('''
        SELECT visit_count, favorite_color FROM users WHERE username = ?
    ''', (user,)).fetchone()
    
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
                         visit_count=user_info['visit_count'] if user_info else 0,
                         current_user={'favorite_color': user_info['favorite_color'] if user_info else '#ffdde1'},
                         personal_greeting=greetings.get(user, f"Salut {user.title()}"),
                         love_quote=get_love_quotes(),
                         now=datetime.now())

@app.route('/toggle_favori/<int:phrase_id>')
def toggle_favori(phrase_id):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    conn = get_db_connection()
    phrase = conn.execute('SELECT est_favori FROM phrases WHERE id = ?', (phrase_id,)).fetchone()
    
    if phrase:
        new_status = not phrase['est_favori']
        conn.execute('UPDATE phrases SET est_favori = ? WHERE id = ?', (new_status, phrase_id))
        conn.commit()
        
        action = 'favori_added' if new_status else 'favori_removed'
        log_activity(session['user'], action, f'Phrase ID: {phrase_id}')
    
    conn.close()
    return redirect(url_for('index'))

@app.route('/like_phrase/<int:phrase_id>')
def like_phrase(phrase_id):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return jsonify({'error': 'Site verrouillé'}), 403
    
    conn = get_db_connection()
    conn.execute('UPDATE phrases SET likes = likes + 1 WHERE id = ?', (phrase_id,))
    conn.commit()
    
    # Récupérer le nouveau nombre de likes
    likes = conn.execute('SELECT likes FROM phrases WHERE id = ?', (phrase_id,)).fetchone()
    conn.close()
    
    log_activity(session['user'], 'phrase_liked', f'Phrase ID: {phrase_id}')
    
    return jsonify({'likes': likes['likes'] if likes else 0})

@app.route('/supprimer_phrase/<int:phrase_id>')
def supprimer_phrase(phrase_id):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    conn = get_db_connection()
    
    # Vérifier que l'utilisateur est l'auteur
    phrase = conn.execute('SELECT auteur FROM phrases WHERE id = ?', (phrase_id,)).fetchone()
    
    if phrase and phrase['auteur'] == user:
        conn.execute('DELETE FROM phrases WHERE id = ?', (phrase_id,))
        conn.commit()
        log_activity(user, 'phrase_deleted', f'Phrase ID: {phrase_id}')
        flash('Message supprimé avec succès', 'success')
    else:
        flash('Vous ne pouvez supprimer que vos propres messages', 'error')
    
    conn.close()
    return redirect(url_for('index'))

@app.route('/galerie')
def galerie():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    conn = get_db_connection()
    
    # Compter le total des photos
    total = conn.execute('SELECT COUNT(*) FROM photos').fetchone()[0]
    
    # Récupérer les photos pour la page actuelle
    offset = (page - 1) * per_page
    photos = conn.execute('''
        SELECT * FROM photos 
        ORDER BY date DESC 
        LIMIT ? OFFSET ?
    ''', (per_page, offset)).fetchall()
    
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
        # Créer un nom de fichier sécurisé avec timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            
            # Enregistrer en base
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO photos (filename, legende, auteur, file_size)
                VALUES (?, ?, ?, ?)
            ''', (filename, legende, session['user'], file_size))
            conn.commit()
            conn.close()
            
            log_activity(session['user'], 'photo_uploaded', f'Photo: {filename}')
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
    
    conn = get_db_connection()
    conn.execute('UPDATE photos SET likes = likes + 1 WHERE id = ?', (photo_id,))
    conn.commit()
    
    # Récupérer le nouveau nombre de likes
    likes = conn.execute('SELECT likes FROM photos WHERE id = ?', (photo_id,)).fetchone()
    conn.close()
    
    log_activity(session['user'], 'photo_liked', f'Photo ID: {photo_id}')
    
    return jsonify({'likes': likes['likes'] if likes else 0})

@app.route('/supprimer_photo/<int:photo_id>')
def supprimer_photo(photo_id):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    conn = get_db_connection()
    
    # Vérifier que l'utilisateur est l'auteur
    photo = conn.execute('SELECT auteur, filename FROM photos WHERE id = ?', (photo_id,)).fetchone()
    
    if photo and photo['auteur'] == user:
        # Supprimer le fichier
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Erreur lors de la suppression du fichier: {e}")
        
        # Supprimer de la base
        conn.execute('DELETE FROM photos WHERE id = ?', (photo_id,))
        conn.commit()
        log_activity(user, 'photo_deleted', f'Photo ID: {photo_id}')
        flash('Photo supprimée avec succès', 'success')
    else:
        flash('Vous ne pouvez supprimer que vos propres photos', 'error')
    
    conn.close()
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
        conn = get_db_connection()
        phrases = conn.execute('''
            SELECT * FROM phrases 
            WHERE texte LIKE ? OR tags LIKE ?
            ORDER BY date DESC
        ''', (f'%{query}%', f'%{query}%')).fetchall()
        conn.close()
        
        log_activity(session['user'], 'search', f'Query: {query}')
    
    return render_template('search_results.html', phrases=phrases, query=query, user=session['user'])

@app.route('/letters')
def letters():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    conn = get_db_connection()
    
    # Lettres reçues
    received_letters = conn.execute('''
        SELECT * FROM letters 
        WHERE recipient = ? 
        ORDER BY created_at DESC
    ''', (user,)).fetchall()
    
    # Lettres envoyées
    sent_letters = conn.execute('''
        SELECT * FROM letters 
        WHERE sender = ? 
        ORDER BY created_at DESC
    ''', (user,)).fetchall()
    
    conn.close()
    
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
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO letters (title, content, sender, recipient)
                VALUES (?, ?, ?, ?)
            ''', (title, content, user, recipient))
            conn.commit()
            conn.close()
            
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
    conn = get_db_connection()
    
    letter = conn.execute('SELECT * FROM letters WHERE id = ?', (letter_id,)).fetchone()
    
    if not letter:
        flash('Lettre introuvable', 'error')
        return redirect(url_for('letters'))
    
    # Vérifier que l'utilisateur peut lire cette lettre
    if letter['sender'] != user and letter['recipient'] != user:
        flash('Vous n\'avez pas accès à cette lettre', 'error')
        return redirect(url_for('letters'))
    
    # Marquer comme lue si c'est le destinataire
    if letter['recipient'] == user and not letter['is_read']:
        conn.execute('UPDATE letters SET is_read = 1 WHERE id = ?', (letter_id,))
        conn.commit()
        log_activity(user, 'letter_read', f'Letter ID: {letter_id}')
    
    conn.close()
    
    return render_template('read_letter.html', letter=letter, user=user)

@app.route('/memories')
def memories():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    conn = get_db_connection()
    
    # Souvenirs anniversaires
    anniversaries = conn.execute('''
        SELECT * FROM memories 
        WHERE is_anniversary = 1 
        ORDER BY date_memory DESC
    ''').fetchall()
    
    # Souvenirs réguliers
    regular_memories = conn.execute('''
        SELECT * FROM memories 
        WHERE is_anniversary = 0 
        ORDER BY date_memory DESC
    ''').fetchall()
    
    conn.close()
    
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
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO memories (title, description, date_memory, author, is_anniversary)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, description, date_memory, session['user'], is_anniversary))
            conn.commit()
            conn.close()
            
            log_activity(session['user'], 'memory_added', f'Memory: {title}')
            flash('Souvenir ajouté avec succès ! ✨', 'success')
            return redirect(url_for('memories'))
    
    return render_template('add_memory.html', user=session['user'])

@app.route('/love_calendar')
def love_calendar():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    # Implémentation basique du calendrier
    from calendar import monthcalendar
    import calendar
    
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # Générer le calendrier
    cal = monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Récupérer les événements
    conn = get_db_connection()
    events = conn.execute('''
        SELECT * FROM calendar_events 
        WHERE strftime('%Y', event_date) = ? AND strftime('%m', event_date) = ?
    ''', (str(year), f'{month:02d}')).fetchall()
    conn.close()
    
    # Organiser les événements par jour
    events_by_day = {}
    for event in events:
        day = int(event['event_date'].split('-')[2])
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
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO calendar_events (title, event_date, event_type, description, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, event_date, event_type, description, session['user']))
        conn.commit()
        conn.close()
        
        flash('Événement ajouté au calendrier ! 📅', 'success')
    
    return redirect(url_for('love_calendar'))

@app.route('/love_challenges')
def love_challenges():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    conn = get_db_connection()
    
    # Défis actifs
    active_challenges = conn.execute('''
        SELECT * FROM challenges 
        WHERE is_active = 1 AND completed_by IS NULL
        ORDER BY points DESC
    ''').fetchall()
    
    # Défis terminés
    completed_challenges = conn.execute('''
        SELECT * FROM challenges 
        WHERE completed_by IS NOT NULL
        ORDER BY completed_date DESC
    ''').fetchall()
    
    # Points totaux de l'utilisateur
    total_points = conn.execute('''
        SELECT SUM(points) as total FROM challenges 
        WHERE completed_by = ?
    ''', (session['user'],)).fetchone()
    
    conn.close()
    
    return render_template('love_challenges.html',
                         active_challenges=active_challenges,
                         completed_challenges=completed_challenges,
                         total_points=total_points['total'] or 0,
                         user=session['user'])

@app.route('/complete_challenge/<int:challenge_id>')
def complete_challenge(challenge_id):
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    conn = get_db_connection()
    
    # Marquer le défi comme terminé
    conn.execute('''
        UPDATE challenges 
        SET completed_by = ?, completed_date = CURRENT_TIMESTAMP
        WHERE id = ? AND completed_by IS NULL
    ''', (session['user'], challenge_id))
    
    conn.commit()
    conn.close()
    
    flash('Défi terminé ! Bravo ! 🎉', 'success')
    return redirect(url_for('love_challenges'))

@app.route('/personalize', methods=['GET', 'POST'])
def personalize():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    user = session['user']
    
    if request.method == 'POST':
        favorite_color = request.form['favorite_color']
        
        conn = get_db_connection()
        conn.execute('''
            UPDATE users SET favorite_color = ? WHERE username = ?
        ''', (favorite_color, user))
        conn.commit()
        conn.close()
        
        flash('Préférences sauvegardées ! 🎨', 'success')
        return redirect(url_for('personalize'))
    
    # Récupérer les informations utilisateur
    conn = get_db_connection()
    user_info = conn.execute('''
        SELECT * FROM users WHERE username = ?
    ''', (user,)).fetchone()
    conn.close()
    
    return render_template('personalize.html', 
                         user=user,
                         current_user=user_info,
                         current_color=user_info['favorite_color'] if user_info else '#ffdde1')

@app.route('/stats')
def stats():
    # Vérifier si le site est déverrouillé
    if not is_site_unlocked() and not session.get('special_access'):
        return redirect(url_for('locked_page'))
    
    conn = get_db_connection()
    
    # Statistiques générales
    total_messages = conn.execute('SELECT COUNT(*) FROM phrases').fetchone()[0]
    total_photos = conn.execute('SELECT COUNT(*) FROM photos').fetchone()[0]
    favoris_count = conn.execute('SELECT COUNT(*) FROM phrases WHERE est_favori = 1').fetchone()[0]
    total_letters = conn.execute('SELECT COUNT(*) FROM letters').fetchone()[0]
    total_memories = conn.execute('SELECT COUNT(*) FROM memories').fetchone()[0]
    
    # Messages par utilisateur
    messages_by_user = conn.execute('''
        SELECT auteur, COUNT(*) as count 
        FROM phrases 
        GROUP BY auteur 
        ORDER BY count DESC
    ''').fetchall()
    
    # Photos par utilisateur
    photos_by_user = conn.execute('''
        SELECT auteur, COUNT(*) as count 
        FROM photos 
        GROUP BY auteur 
        ORDER BY count DESC
    ''').fetchall()
    
    # Activité récente
    recent_activity = conn.execute('''
        SELECT * FROM activities 
        ORDER BY date DESC 
        LIMIT 20
    ''').fetchall()
    
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





