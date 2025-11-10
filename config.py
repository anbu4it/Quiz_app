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
    # Ensure we're using absolute path for SQLite database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH.absolute()}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Make sure instance path exists
    INSTANCE_PATH = str(INSTANCE_PATH)
