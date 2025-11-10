from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    full_name = db.Column(db.String(120), nullable=True)
    bio = db.Column(db.String(500), nullable=True)
    avatar = db.Column(db.String(256), nullable=True)  # filename stored in static/uploads
    scores = db.relationship('Score', backref='user', lazy=True)

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_name = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    # Use timezone-aware UTC timestamps to avoid deprecation warnings and ambiguity
    date_taken = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))