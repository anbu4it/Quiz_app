# config.py - configuration constants
import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
    # Add more config (DB_URI, API keys) here later
