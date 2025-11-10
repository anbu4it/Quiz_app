# config.py - configuration constants
import os
from pathlib import Path

# Create instance folder if it doesn't exist
INSTANCE_PATH = Path(__file__).parent / 'instance'
INSTANCE_PATH.mkdir(exist_ok=True)

# Database file will be stored in the instance folder
DB_PATH = INSTANCE_PATH / 'quiz.db'

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
    # Use DATABASE_URL for production, fallback to SQLite for local development
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH.absolute()}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    INSTANCE_PATH = str(INSTANCE_PATH)
    
    # Cookie/session security (tunable via env for local vs prod)
    # Default to safe values; override with env vars as needed
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    # Don't force Secure cookies locally unless explicitly enabled
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    REMEMBER_COOKIE_SECURE = os.getenv("REMEMBER_COOKIE_SECURE", "0") == "1"
    
    # Preferred scheme for URL generation in prod behind HTTPS
    PREFERRED_URL_SCHEME = os.getenv("PREFERRED_URL_SCHEME", "https")
