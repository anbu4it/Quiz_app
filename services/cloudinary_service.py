"""Cloudinary service for avatar uploads with fallback to local storage."""
import os
import cloudinary
import cloudinary.uploader
from flask import current_app


def init_cloudinary():
    """Initialize Cloudinary with environment variables."""
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
    
    if cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        return True
    return False


def upload_avatar(file, user_id: int) -> str:
    """
    Upload avatar to Cloudinary (production) or local storage (development).
    
    Args:
        file: FileStorage object from Flask request
        user_id: User ID for unique naming
        
    Returns:
        URL or path to the uploaded avatar
    """
    # Check if Cloudinary is configured
    cloudinary_enabled = init_cloudinary()
    
    if cloudinary_enabled:
        try:
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file,
                folder="quiz_app_avatars",
                public_id=f"user_{user_id}",
                overwrite=True,
                resource_type="image",
                transformation=[
                    {'width': 200, 'height': 200, 'crop': 'fill', 'gravity': 'face'},
                    {'quality': 'auto:good'}
                ]
            )
            current_app.logger.info(f"Cloudinary upload successful for user {user_id}")
            return result['secure_url']
        except Exception as e:
            current_app.logger.error(f"Cloudinary upload failed: {str(e)}")
            # Fall through to local storage
    
    # Fallback to local storage (development/testing)
    from werkzeug.utils import secure_filename
    from datetime import datetime
    
    filename = secure_filename(file.filename)
    _, ext = os.path.splitext(filename)
    safe_name = f"user_{user_id}_{int(datetime.utcnow().timestamp())}{ext}"
    
    upload_dir = os.path.join(current_app.static_folder, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, safe_name)
    
    file.save(save_path)
    current_app.logger.info(f"Local storage upload for user {user_id}")
    
    # Return relative path for local storage
    return f"uploads/{safe_name}"


def delete_avatar(avatar_url_or_path: str) -> bool:
    """
    Delete avatar from Cloudinary or local storage.
    
    Args:
        avatar_url_or_path: Full URL (Cloudinary) or relative path (local)
        
    Returns:
        True if deleted successfully
    """
    if not avatar_url_or_path:
        return False
    
    # Check if it's a Cloudinary URL
    if avatar_url_or_path.startswith('https://res.cloudinary.com/'):
        cloudinary_enabled = init_cloudinary()
        if cloudinary_enabled:
            try:
                # Extract public_id from URL
                # URL format: https://res.cloudinary.com/{cloud_name}/image/upload/v{version}/{folder}/{public_id}.{ext}
                parts = avatar_url_or_path.split('/')
                if 'quiz_app_avatars' in parts:
                    idx = parts.index('quiz_app_avatars')
                    public_id_with_ext = parts[idx + 1]
                    public_id = os.path.splitext(public_id_with_ext)[0]
                    full_public_id = f"quiz_app_avatars/{public_id}"
                    
                    cloudinary.uploader.destroy(full_public_id)
                    current_app.logger.info(f"Cloudinary avatar deleted: {full_public_id}")
                    return True
            except Exception as e:
                current_app.logger.error(f"Cloudinary delete failed: {str(e)}")
                return False
    else:
        # Local file deletion
        try:
            full_path = os.path.join(current_app.static_folder, avatar_url_or_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                current_app.logger.info(f"Local avatar deleted: {avatar_url_or_path}")
                return True
        except Exception as e:
            current_app.logger.error(f"Local delete failed: {str(e)}")
            return False
    
    return False


def is_cloudinary_url(avatar: str) -> bool:
    """Check if avatar is a Cloudinary URL."""
    return avatar and avatar.startswith('https://res.cloudinary.com/')
