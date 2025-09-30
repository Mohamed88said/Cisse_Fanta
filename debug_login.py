import os
from app import app, db, User
from werkzeug.security import check_password_hash

with app.app_context():
    print("🔍 DEBUG - Vérification des utilisateurs:")
    
    users = User.query.all()
    for user in users:
        print(f"Utilisateur: {user.username}")
        print(f"Password hash: {user.password_hash}")
        
        # Test des mots de passe
        test_passwords = [
            'Elle a toujours été belle',
            'La lune est belle ce soir',
            'elle a toujours été belle',  # minuscules
            'la lune est belle ce soir'   # minuscules
        ]
        
        for pwd in test_passwords:
            is_correct = check_password_hash(user.password_hash, pwd)
            print(f"  '{pwd}' -> {is_correct}")
        
        print("---")
