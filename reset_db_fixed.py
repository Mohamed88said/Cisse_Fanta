import os
import sys
from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    print("🔄 Réinitialisation de la base de données...")
    
    # Supprimer et recréer toutes les tables
    db.drop_all()
    db.create_all()
    
    # Créer les utilisateurs avec les mots de passe EXACTS
    user1 = User(
        username='maninka mousso',
        password_hash=generate_password_hash('Elle a toujours été belle'),
        favorite_color='#ffdde1'
    )
    
    user2 = User(
        username='panda bg', 
        password_hash=generate_password_hash('La lune est belle ce soir'),
        favorite_color='#e1f5fe'
    )
    
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()
    
    print("✅ Base de données réinitialisée!")
    print("📝 Utilisateurs créés:")
    print("   - maninka mousso")
    print("   - panda bg")
    print("")
    print("🔑 MOTS DE PASSE (copiez-collez exactement):")
    print('   maninka mousso: "Elle a toujours été belle"')
    print('   panda bg: "La lune est belle ce soir"')
    print("")
    print("⚠️  ATTENTION: Respectez les majuscules et espaces!")