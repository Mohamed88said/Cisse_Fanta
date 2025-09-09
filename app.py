from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import random
import json
from datetime import datetime, date
from datetime import timedelta
import secrets

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = secrets.token_hex(32)  # Clé secrète sécurisée
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
db = SQLAlchemy(app)

# --- Authentification ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Modèle User ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# --- Modèle Phrase ---
class Phrase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    texte = db.Column(db.String(300), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    couleur = db.Column(db.String(20), default='#ffffff')
    est_favori = db.Column(db.Boolean, default=False)
    auteur = db.Column(db.String(50), default='Anonyme')
    likes = db.Column(db.Integer, default=0)
    tags = db.Column(db.String(200))  # Tags séparés par des virgules

# --- Modèle Photo ---
class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    legende = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    auteur = db.Column(db.String(50), default='Anonyme')
    likes = db.Column(db.Integer, default=0)
    file_size = db.Column(db.Integer)  # Taille du fichier en bytes

# --- Modèle MoodJournal ---
class MoodJournal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    mood = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, default=date.today)
    verse_shown = db.Column(db.String(10), nullable=False)

# --- Nouveau modèle pour les statistiques ---
class Statistics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'message_added', 'photo_uploaded', etc.
    date = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.String(200))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def upgrade_database():
    """Met à jour la structure de la base de données avec gestion d'erreurs améliorée"""
    try:
        with app.app_context():
            db.create_all()
            
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            
            # Vérification et ajout des colonnes manquantes pour la table phrase
            if inspector.has_table('phrase'):
                columns = [col['name'] for col in inspector.get_columns('phrase')]
                
                if 'couleur' not in columns:
                    db.session.execute(text('ALTER TABLE phrase ADD COLUMN couleur VARCHAR(20) DEFAULT "#ffffff"'))
                if 'est_favori' not in columns:
                    db.session.execute(text('ALTER TABLE phrase ADD COLUMN est_favori BOOLEAN DEFAULT FALSE'))
                if 'auteur' not in columns:
                    db.session.execute(text('ALTER TABLE phrase ADD COLUMN auteur VARCHAR(50) DEFAULT "Anonyme"'))
                if 'likes' not in columns:
                    db.session.execute(text('ALTER TABLE phrase ADD COLUMN likes INTEGER DEFAULT 0'))
                if 'tags' not in columns:
                    db.session.execute(text('ALTER TABLE phrase ADD COLUMN tags VARCHAR(200)'))
            
            # Vérification et ajout des colonnes manquantes pour la table photo
            if inspector.has_table('photo'):
                photo_columns = [col['name'] for col in inspector.get_columns('photo')]
                if 'likes' not in photo_columns:
                    db.session.execute(text('ALTER TABLE photo ADD COLUMN likes INTEGER DEFAULT 0'))
                if 'file_size' not in photo_columns:
                    db.session.execute(text('ALTER TABLE photo ADD COLUMN file_size INTEGER'))
            
            # Vérification et ajout des colonnes manquantes pour la table user
            if inspector.has_table('user'):
                user_columns = [col['name'] for col in inspector.get_columns('user')]
                if 'password_hash' not in user_columns:
                    db.session.execute(text('ALTER TABLE user ADD COLUMN password_hash VARCHAR(128)'))
                if 'created_at' not in user_columns:
                    db.session.execute(text('ALTER TABLE user ADD COLUMN created_at DATETIME'))
                if 'last_login' not in user_columns:
                    db.session.execute(text('ALTER TABLE user ADD COLUMN last_login DATETIME'))
            
            db.session.commit()
            print("Base de données mise à jour avec succès!")
            
    except Exception as e:
        print(f"Erreur lors de la mise à jour de la base: {e}")
        db.session.rollback()
        try:
            db.create_all()
            print("Tables créées avec succès!")
        except Exception as e2:
            print(f"Erreur critique: {e2}")

def log_activity(user, action, details=None):
    """Enregistre l'activité de l'utilisateur"""
    try:
        stat = Statistics(user=user, action=action, details=details)
        db.session.add(stat)
        db.session.commit()
    except Exception as e:
        print(f"Erreur lors de l'enregistrement de l'activité: {e}")
        db.session.rollback()

# Fonctions utilitaires pour le mood
def load_mood_data():
    try:
        with open('mood_verses.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Fichier mood_verses.json non trouvé!")
        return {}

def get_recent_verses(username, days=30):
    recent_date = date.today() - timedelta(days=days)
    recent_entries = MoodJournal.query.filter(
        MoodJournal.username == username,
        MoodJournal.date >= recent_date
    ).all()
    return [entry.verse_shown for entry in recent_entries]

# --- Nouvelle fonction pour gérer les indices de connexion ---
def get_login_hint(attempts):
    hints = {
        0: "",
        1: "💡 Indice : Pense à une déclaration d'amour japonaise...",
        2: "💡 Indice : C'est une réponse à un compliment sur la beauté...",
        3: "💡 Indice : Ça commence par 'Oui c'est vrai...'",
        4: "💡 Indice : La réponse complète est 'Oui c'est vrai, elle est magnifique'"
    }
    return hints.get(min(attempts, 4), hints[4])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Réinitialiser le compteur si c'est un nouvel utilisateur
        if 'login_attempts' not in session or session.get('last_username') != username:
            session['login_attempts'] = 0
            session['last_username'] = username
        
        # Vérification des mots de passe spéciaux
        if username == "said" and password == "La lune est belle ce soir":
            user = User.query.filter_by(username=username).first()
            if user:
                user.last_login = datetime.utcnow()
                db.session.commit()
                login_user(user)
                session.pop('login_attempts', None)
                session.pop('last_username', None)
                log_activity(username, 'login', 'Connexion réussie')
                return redirect(url_for('index'))
        
        elif username == "fanta":
            if password == "Oui c'est vrai, elle est magnifique":
                user = User.query.filter_by(username=username).first()
                if user:
                    user.last_login = datetime.utcnow()
                    db.session.commit()
                    login_user(user)
                    session.pop('login_attempts', None)
                    session.pop('last_username', None)
                    log_activity(username, 'login', 'Connexion réussie')
                    return redirect(url_for('index'))
            else:
                # Incrémenter le compteur d'essais pour Fanta
                session['login_attempts'] = session.get('login_attempts', 0) + 1
                log_activity(username, 'failed_login', f'Tentative {session["login_attempts"]}')
                flash(f"Mot de passe incorrect. {get_login_hint(session['login_attempts'])}", 'error')
                return render_template('login.html', 
                                    hint=get_login_hint(session['login_attempts']),
                                    attempts=session['login_attempts'])
        
        else:
            # Pour les autres utilisateurs ou mots de passe incorrects
            flash("Nom d'utilisateur ou mot de passe incorrect", 'error')
    
    # Afficher le hint actuel si disponible
    hint = session.get('login_attempts', 0) > 0 and session.get('last_username') == 'fanta'
    return render_template('login.html', 
                         hint=get_login_hint(session.get('login_attempts', 0)) if hint else "",
                         attempts=session.get('login_attempts', 0))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    log_activity(current_user.username if current_user.is_authenticated else 'unknown', 'logout')
    session.pop('login_attempts', None)
    session.pop('last_username', None)
    flash('Déconnexion réussie. À bientôt! 👋', 'info')
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        texte = request.form['texte']
        if len(texte.strip()) == 0:
            flash('Le message ne peut pas être vide! 📝', 'error')
            return redirect(url_for('index'))
        
        if len(texte) > 500:
            flash('Le message est trop long (maximum 500 caractères)! ✂️', 'error')
            return redirect(url_for('index'))
            
        couleur = request.form.get('couleur', '#ffffff')
        tags = request.form.get('tags', '')
        
        nouvelle_phrase = Phrase(
            texte=texte, 
            couleur=couleur, 
            auteur=current_user.username,
            tags=tags
        )
        db.session.add(nouvelle_phrase)
        db.session.commit()
        log_activity(current_user.username, 'message_added', f'Message: {texte[:50]}...')
        flash('Votre message a été ajouté avec succès! 💖', 'success')
        return redirect(url_for('index'))
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    phrases = Phrase.query.order_by(Phrase.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Statistiques
    total_messages = Phrase.query.count()
    total_photos = Photo.query.count()
    favoris_count = Phrase.query.filter_by(est_favori=True).count()
    
    return render_template('index.html', 
                         phrases=phrases.items, 
                         pagination=phrases,
                         user=current_user.username,
                         stats={
                             'total_messages': total_messages,
                             'total_photos': total_photos,
                             'favoris_count': favoris_count
                         })

@app.route('/like_phrase/<int:phrase_id>')
@login_required
def like_phrase(phrase_id):
    phrase = Phrase.query.get_or_404(phrase_id)
    phrase.likes += 1
    db.session.commit()
    log_activity(current_user.username, 'phrase_liked', f'Phrase ID: {phrase_id}')
    return jsonify({'likes': phrase.likes})

@app.route('/favori/<int:phrase_id>')
@login_required
def toggle_favori(phrase_id):
    phrase = Phrase.query.get_or_404(phrase_id)
    phrase.est_favori = not phrase.est_favori
    db.session.commit()
    action = 'added_to_favorites' if phrase.est_favori else 'removed_from_favorites'
    log_activity(current_user.username, action, f'Phrase ID: {phrase_id}')
    return redirect(url_for('index'))

@app.route('/supprimer/<int:phrase_id>')
@login_required
def supprimer_phrase(phrase_id):
    phrase = Phrase.query.get_or_404(phrase_id)
    # Vérifier que l'utilisateur peut supprimer ce message
    if phrase.auteur != current_user.username:
        flash('Vous ne pouvez supprimer que vos propres messages! 🚫', 'error')
        return redirect(url_for('index'))
    
    log_activity(current_user.username, 'message_deleted', f'Message: {phrase.texte[:50]}...')
    db.session.delete(phrase)
    db.session.commit()
    flash('Message supprimé avec succès', 'info')
    return redirect(url_for('index'))

@app.route('/galerie')
@login_required
def galerie():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    photos = Photo.query.order_by(Photo.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('galerie.html', 
                         photos=photos.items, 
                         pagination=photos,
                         user=current_user.username)

@app.route('/like_photo/<int:photo_id>')
@login_required
def like_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    photo.likes += 1
    db.session.commit()
    log_activity(current_user.username, 'photo_liked', f'Photo ID: {photo_id}')
    return jsonify({'likes': photo.likes})

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('galerie'))
    
    file = request.files['file']
    legende = request.form.get('legende', '')
    
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('galerie'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Ajouter un timestamp pour éviter les conflits de noms
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Vérifier la taille du fichier
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > app.config['MAX_CONTENT_LENGTH']:
            flash('Le fichier est trop volumineux (maximum 16MB)! 📏', 'error')
            return redirect(url_for('galerie'))
        
        file.save(filepath)
        
        nouvelle_photo = Photo(
            filename=filename, 
            legende=legende, 
            auteur=current_user.username,
            file_size=file_size
        )
        db.session.add(nouvelle_photo)
        db.session.commit()
        
        log_activity(current_user.username, 'photo_uploaded', f'Photo: {filename}')
        flash('Photo ajoutée avec succès! 📸', 'success')
        return redirect(url_for('galerie'))
    
    flash('Type de fichier non autorisé', 'error')
    return redirect(url_for('galerie'))

@app.route('/supprimer_photo/<int:photo_id>')
@login_required
def supprimer_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    
    # Vérifier que l'utilisateur peut supprimer cette photo
    if photo.auteur != current_user.username:
        flash('Vous ne pouvez supprimer que vos propres photos! 🚫', 'error')
        return redirect(url_for('galerie'))
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], photo.filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except OSError as e:
            print(f"Erreur lors de la suppression du fichier: {e}")
    
    log_activity(current_user.username, 'photo_deleted', f'Photo: {photo.filename}')
    db.session.delete(photo)
    db.session.commit()
    flash('Photo supprimée avec succès', 'info')
    return redirect(url_for('galerie'))

@app.route('/mood', methods=['GET', 'POST'])
@login_required
def mood():
    if request.method == 'POST':
        selected_mood = request.form['mood']
        
        # Sélectionner un verset approprié
        mood_data = load_mood_data()
        if not mood_data:
            flash('Erreur: Impossible de charger les versets.', 'error')
            return redirect(url_for('mood'))
        
        verses = mood_data.get(selected_mood, [])
        
        if not verses:
            flash('Aucun verset disponible pour cette humeur.', 'error')
            return redirect(url_for('mood'))
        
        # Choisir un verset aléatoire non montré récemment (sur 30 jours)
        recent_verses = get_recent_verses(current_user.username)
        available_verses = []
        for v in verses:
            # Pour les versets normaux qui ont un verse_id
            if 'verse_id' in v:
                if v['verse_id'] not in recent_verses:
                    available_verses.append(v)
            # Pour les hadiths/duas qui n'ont pas de verse_id, on génère un ID unique
            else:
                unique_id = f"{v.get('type', 'unknown')}-{v.get('source', 'unknown')}-{v.get('reference', 'unknown')}"
                if unique_id not in recent_verses:
                    available_verses.append(v)
        
        # Si tous les versets ont été vus récemment, on réinitialise la liste
        if not available_verses:
            available_verses = verses
        
        selected_verse = random.choice(available_verses)
        
        # Sauvegarder le choix (on garde l'historique, mais sans restriction)
        new_entry = MoodJournal(
            username=current_user.username,
            mood=selected_mood,
            date=date.today(),
            verse_shown=selected_verse.get('verse_id', f"{selected_verse.get('type', 'unknown')}-{selected_verse.get('source', 'unknown')}")
        )
        db.session.add(new_entry)
        db.session.commit()
        
        log_activity(current_user.username, 'mood_checked', f'Mood: {selected_mood}')
        
        return render_template('mood_result.html', 
                             mood=selected_mood, 
                             verse=selected_verse,
                             user=current_user.username)
    
    return render_template('mood.html', user=current_user.username)

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    if query:
        phrases = Phrase.query.filter(
            Phrase.texte.contains(query) | 
            Phrase.tags.contains(query)
        ).order_by(Phrase.date.desc()).all()
        log_activity(current_user.username, 'search', f'Query: {query}')
    else:
        phrases = []
    
    return render_template('search_results.html', 
                         phrases=phrases, 
                         query=query,
                         user=current_user.username)

@app.route('/stats')
@login_required
def stats():
    # Statistiques générales
    total_messages = Phrase.query.count()
    total_photos = Photo.query.count()
    favoris_count = Phrase.query.filter_by(est_favori=True).count()
    
    # Messages par utilisateur
    messages_by_user = db.session.query(
        Phrase.auteur, 
        db.func.count(Phrase.id).label('count')
    ).group_by(Phrase.auteur).all()
    
    # Photos par utilisateur
    photos_by_user = db.session.query(
        Photo.auteur, 
        db.func.count(Photo.id).label('count')
    ).group_by(Photo.auteur).all()
    
    # Activité récente
    recent_activity = Statistics.query.order_by(
        Statistics.date.desc()
    ).limit(20).all()
    
    return render_template('stats.html',
                         total_messages=total_messages,
                         total_photos=total_photos,
                         favoris_count=favoris_count,
                         messages_by_user=messages_by_user,
                         photos_by_user=photos_by_user,
                         recent_activity=recent_activity,
                         user=current_user.username)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(413)
def too_large(error):
    flash('Le fichier est trop volumineux! 📏', 'error')
    return redirect(url_for('galerie'))

if __name__ == '__main__':
    with app.app_context():
        upgrade_database()
        
        # Créer les utilisateurs avec les nouveaux champs
        if not User.query.first():
            user1 = User(username="said")
            user1.set_password("La lune est belle ce soir")
            user2 = User(username="fanta")
            user2.set_password("Oui c'est vrai, elle est magnifique")
            db.session.add(user1)
            db.session.add(user2)
            db.session.commit()
            print("Utilisateurs créés!")
        else:
            # Migrer les anciens utilisateurs si nécessaire
            users = User.query.all()
            for user in users:
                if not hasattr(user, 'password_hash') or user.password_hash is None:
                    if user.username == "said":
                        user.set_password("La lune est belle ce soir")
                    elif user.username == "fanta":
                        user.set_password("Oui c'est vrai, elle est magnifique")
            db.session.commit()
    
    app.run(host="0.0.0.0", port=5000)