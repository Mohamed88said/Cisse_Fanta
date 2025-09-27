import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import current_app
import os
from werkzeug.utils import secure_filename
from datetime import datetime

def init_cloudinary():
    """Initialise la configuration Cloudinary"""
    cloudinary.config(
        cloud_name=current_app.config['CLOUDINARY_CLOUD_NAME'],
        api_key=current_app.config['CLOUDINARY_API_KEY'],
        api_secret=current_app.config['CLOUDINARY_API_SECRET']
    )

def upload_to_cloudinary(file, folder="love_app"):
    """
    Upload un fichier vers Cloudinary
    Retourne l'URL et les métadonnées
    """
    try:
        init_cloudinary()
        
        # Créer un nom de fichier unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + secure_filename(file.filename)
        
        # Upload vers Cloudinary
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            public_id=filename,
            resource_type="auto"
        )
        
        return {
            'success': True,
            'url': result['secure_url'],
            'public_id': result['public_id'],
            'filename': filename,
            'file_size': result.get('bytes', 0)
        }
        
    except Exception as e:
        current_app.logger.error(f"Erreur Cloudinary: {str(e)}")
        return {'success': False, 'error': str(e)}

def delete_from_cloudinary(public_id):
    """Supprime un fichier de Cloudinary"""
    try:
        init_cloudinary()
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        current_app.logger.error(f"Erreur suppression Cloudinary: {str(e)}")
        return False

def allowed_file(filename):
    """Vérifie si le fichier est autorisé"""
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_file_locally(file):
    """
    Sauvegarde locale de fallback si Cloudinary échoue
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # Créer le dossier si nécessaire
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        return {
            'success': True,
            'filename': filename,
            'file_path': file_path,
            'file_size': file_size
        }
        
    except Exception as e:
        current_app.logger.error(f"Erreur sauvegarde locale: {str(e)}")
        return {'success': False, 'error': str(e)}