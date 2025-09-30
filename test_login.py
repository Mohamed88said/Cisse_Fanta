from app import app, User
from werkzeug.security import check_password_hash

with app.app_context():
    # Test direct
    user = User.query.filter_by(username='maninka mousso').first()
    if user:
        print("Utilisateur trouvé:", user.username)
        test = check_password_hash(user.password_hash, 'Elle a toujours été belle')
        print("Mot de passe correct:", test)
    else:
        print("❌ Utilisateur non trouvé!")