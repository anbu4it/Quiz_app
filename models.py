from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    full_name = db.Column(db.String(120), nullable=True)
    bio = db.Column(db.String(500), nullable=True)
    avatar = db.Column(db.String(256), nullable=True)  # filename stored in static/uploads
    current_streak = db.Column(db.Integer, default=0, nullable=False)  # Current consecutive days
    longest_streak = db.Column(db.Integer, default=0, nullable=False)  # All-time best streak
    last_quiz_date = db.Column(db.Date, nullable=True)  # Last day user completed a quiz
    # Total XP accumulated across all quizzes
    total_xp = db.Column(db.Integer, default=0, nullable=False)
    scores = db.relationship("Score", backref="user", lazy=True)


class Score(db.Model):
    __tablename__ = "score"
    __table_args__ = (
        # Index for user's quiz history (dashboard queries)
        db.Index("idx_user_date", "user_id", "date_taken"),
        # Index for leaderboard per-category queries
        db.Index("idx_quiz_name", "quiz_name"),
        # Composite index for leaderboard ranking (quiz + score DESC)
        db.Index("idx_quiz_score", "quiz_name", "score"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    quiz_name = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    # Difficulty level used when taking the quiz (easy/medium/hard)
    difficulty = db.Column(db.String(16), nullable=True)
    # XP earned for this attempt (difficulty-weighted)
    xp_earned = db.Column(db.Integer, default=0, nullable=False)
    # Use timezone-aware UTC timestamps to avoid deprecation warnings and ambiguity
    date_taken = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
