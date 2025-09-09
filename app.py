from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import random
import json
from datetime import datetime, date
from datetime import timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'supersecretkey'  # Clé secrète pour la session
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
db = SQLAlchemy(app)

# --- Authentification ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Modèle User ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

# --- Modèle Phrase ---
class Phrase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    texte = db.Column(db.String(300), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    couleur = db.Column(db.String(20), default='#ffffff')
    est_favori = db.Column(db.Boolean, default=False)
    auteur = db.Column(db.String(50), default='Anonyme')

# --- Modèle Photo ---
class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    legende = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    auteur = db.Column(db.String(50), default='Anonyme')

# --- Modèle MoodJournal ---
class MoodJournal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    mood = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, default=date.today)
    verse_shown = db.Column(db.String(10), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def upgrade_database():
    """Met à jour la structure de la base de données si nécessaire"""
    try:
        # Vérifie si la table phrase a la colonne couleur
        with app.app_context():
            # Crée toutes les tables si elles n'existent pas
            db.create_all()
            
            # Vérifie et ajoute les colonnes manquantes à la table phrase
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('phrase')]
            
            if 'couleur' not in columns:
                print("Ajout de la colonne couleur...")
                db.session.execute(text('ALTER TABLE phrase ADD COLUMN couleur VARCHAR(20) DEFAULT "#ffffff"'))
            
            if 'est_favori' not in columns:
                print("Ajout de la colonne est_favori...")
                db.session.execute(text('ALTER TABLE phrase ADD COLUMN est_favori BOOLEAN DEFAULT FALSE'))
            
            if 'auteur' not in columns:
                print("Ajout de la colonne auteur...")
                db.session.execute(text('ALTER TABLE phrase ADD COLUMN auteur VARCHAR(50) DEFAULT "Anonyme"'))
            
            db.session.commit()
            print("Base de données mise à jour avec succès!")
            
    except Exception as e:
        print(f"Erreur lors de la mise à jour de la base: {e}")
        # En cas d'erreur, on recrée tout
        db.drop_all()
        db.create_all()
        print("Base de données recréée!")

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
                login_user(user)
                session.pop('login_attempts', None)
                session.pop('last_username', None)
                return redirect(url_for('index'))
        
        elif username == "fanta":
            if password == "Oui c'est vrai, elle est magnifique":
                user = User.query.filter_by(username=username).first()
                if user:
                    login_user(user)
                    session.pop('login_attempts', None)
                    session.pop('last_username', None)
                    return redirect(url_for('index'))
            else:
                # Incrémenter le compteur d'essais pour Fanta
                session['login_attempts'] = session.get('login_attempts', 0) + 1
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
    session.pop('login_attempts', None)
    session.pop('last_username', None)
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        texte = request.form['texte']
        couleur = request.form.get('couleur', '#ffffff')
        nouvelle_phrase = Phrase(texte=texte, couleur=couleur, auteur=current_user.username)
        db.session.add(nouvelle_phrase)
        db.session.commit()
        flash('Votre message a été ajouté avec succès! 💖', 'success')
        return redirect(url_for('index'))
    
    phrases = Phrase.query.order_by(Phrase.date.desc()).all()
    return render_template('index.html', phrases=phrases, user=current_user.username)

@app.route('/favori/<int:phrase_id>')
@login_required
def toggle_favori(phrase_id):
    phrase = Phrase.query.get_or_404(phrase_id)
    phrase.est_favori = not phrase.est_favori
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/supprimer/<int:phrase_id>')
@login_required
def supprimer_phrase(phrase_id):
    phrase = Phrase.query.get_or_404(phrase_id)
    db.session.delete(phrase)
    db.session.commit()
    flash('Message supprimé avec succès', 'info')
    return redirect(url_for('index'))

@app.route('/galerie')
@login_required
def galerie():
    photos = Photo.query.order_by(Photo.date.desc()).all()
    return render_template('galerie.html', photos=photos, user=current_user.username)

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
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        
        nouvelle_photo = Photo(filename=filename, legende=legende, auteur=current_user.username)
        db.session.add(nouvelle_photo)
        db.session.commit()
        
        flash('Photo ajoutée avec succès! 📸', 'success')
        return redirect(url_for('galerie'))
    
    flash('Type de fichier non autorisé', 'error')
    return redirect(url_for('galerie'))

@app.route('/supprimer_photo/<int:photo_id>')
@login_required
def supprimer_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], photo.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
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
            date=date.today(), # On s'assure d'enregistrer la date du jour
            verse_shown=selected_verse['verse_id']
        )
        db.session.add(new_entry)
        db.session.commit()
        
        return render_template('mood_result.html', 
                             mood=selected_mood, 
                             verse=selected_verse,
                             user=current_user.username)
    
    # On rend simplement le template mood.html sans lui passer la variable 'already_answered'
    return render_template('mood.html', user=current_user.username)

if __name__ == '__main__':
    with app.app_context():
        # Met à jour la base de données avant de démarrer
        upgrade_database()
        
        # ✅ Crée les utilisateurs si la base est vide
        if not User.query.first():
            user1 = User(username="said", password="La lune est belle ce soir")
            user2 = User(username="fanta", password="Oui c'est vrai, elle est magnifique")
            db.session.add(user1)
            db.session.add(user2)
            db.session.commit()
            print("Utilisateurs créés!")
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)