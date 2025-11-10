from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import desc, func
from models import db, User, Score
from werkzeug.utils import secure_filename
import os
from datetime import datetime

# Upload settings
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif'}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB


def _allowed_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


def _remove_avatar_file(avatar_path: str):
    """Remove avatar file under static folder if it exists."""
    if not avatar_path:
        return
    try:
        full = os.path.join(current_app.static_folder, avatar_path)
        if os.path.exists(full):
            os.remove(full)
    except Exception:
        # fail silently; removal is best-effort
        pass

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Input validation
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return redirect(url_for('auth.register'))
            
        if len(username) < 3 or len(username) > 80:
            flash('Username must be between 3 and 80 characters', 'error')
            return redirect(url_for('auth.register'))
            
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return redirect(url_for('auth.register'))
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))
        
        try:
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            # Auto-login the newly registered user and redirect to main page
            login_user(user)
            flash('Registration successful! You are now logged in.', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            return redirect(url_for('auth.register'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False) == 'true'
        
        if not username or not password:
            flash('Both username and password are required', 'error')
            return redirect(url_for('auth.login'))
        
        try:
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('main.index'))
            
            flash('Invalid username or password', 'error')
        except Exception as e:
            flash('Login failed. Please try again.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/dashboard')
@login_required
def dashboard():
    # Get user's scores
    user_scores = current_user.scores
    return render_template('auth/dashboard.html', scores=user_scores)


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """View and edit user profile, including uploading an avatar."""
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        bio = request.form.get('bio')

        # Update textual fields
        current_user.full_name = full_name
        current_user.bio = bio

        # Handle avatar upload / removal
        remove_avatar = request.form.get('remove_avatar')
        if remove_avatar:
            _remove_avatar_file(current_user.avatar)
            current_user.avatar = None

        file = request.files.get('avatar')
        if file and file.filename:
            filename = secure_filename(file.filename)
            # Validate extension
            if not _allowed_file(filename):
                flash('Unsupported file type for avatar. Allowed: png, jpg, jpeg, gif', 'warning')
                return redirect(url_for('auth.profile'))

            # Validate file size (seek-based)
            file.stream.seek(0, os.SEEK_END)
            size = file.stream.tell()
            file.stream.seek(0)
            if size > MAX_AVATAR_SIZE:
                flash('Avatar too large (max 2MB).', 'warning')
                return redirect(url_for('auth.profile'))

            # remove old avatar file if exists
            _remove_avatar_file(current_user.avatar)

            _, ext = os.path.splitext(filename)
            # build unique filename: userID_timestamp.ext
            safe_name = f"user_{current_user.id}_{int(datetime.utcnow().timestamp())}{ext}"
            upload_dir = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, safe_name)
            file.save(save_path)
            # store relative path (uploads/...) to serve via url_for('static', ...)
            current_user.avatar = f"uploads/{safe_name}"

        try:
            db.session.commit()
            flash('Profile updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Failed to update profile: ' + str(e), 'danger')

        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html')

@auth_bp.route('/leaderboard')
@login_required
def leaderboard():
    try:
        # First, get all unique quiz categories
        categories = db.session.query(Score.quiz_name).distinct().all()
        categories = [cat[0] for cat in categories]

        # Initialize leaderboards dictionary with empty lists for all categories
        leaderboards = {category: [] for category in categories}

        # Get top scores by topic
        for category in categories:
            # include avatar for display in leaderboard
            topic_scores = db.session.query(
                User.username,
                User.avatar,
                func.count(Score.id).label('attempts'),
                func.avg(Score.score * 100.0 / Score.max_score).label('avg_percentage'),
                func.max(Score.score * 100.0 / Score.max_score).label('best_percentage'),
                func.max(Score.date_taken).label('last_attempt')
            ).join(User).filter(
                Score.quiz_name == category
            ).group_by(
                User.username,
                User.avatar
            ).order_by(
                desc('best_percentage'),
                desc('avg_percentage'),
                desc('last_attempt')
            ).all()

            # Add scores for this category, normalizing avatar path and falling back
            for score in topic_scores:
                avatar_path = getattr(score, 'avatar', None)
                if avatar_path:
                    full = os.path.join(current_app.static_folder, avatar_path)
                    if not os.path.exists(full):
                        avatar_path = 'images/default-avatar.svg'
                else:
                    avatar_path = 'images/default-avatar.svg'

                leaderboards[category].append({
                    'username': score.username,
                    'avatar': avatar_path,
                    'attempts': score.attempts,
                    'avg_score': round(score.avg_percentage, 2),
                    'best_score': round(score.best_percentage, 2)
                })

        # Get global top performers
        # include avatar in global top performers
        top_performers = db.session.query(
            User.username,
            User.avatar,
            func.count(Score.id).label('total_quizzes'),
            func.avg(Score.score * 100.0 / Score.max_score).label('avg_percentage')
        ).join(Score).group_by(User.username, User.avatar).order_by(
            desc('avg_percentage')
        ).limit(5).all()

        # Normalize avatars for global performers
        normalized_top = []
        for p in top_performers:
            avatar_path = getattr(p, 'avatar', None)
            if avatar_path:
                full = os.path.join(current_app.static_folder, avatar_path)
                if not os.path.exists(full):
                    avatar_path = 'images/default-avatar.svg'
            else:
                avatar_path = 'images/default-avatar.svg'
            normalized_top.append({
                'username': p.username,
                'avatar': avatar_path,
                'total_quizzes': p.total_quizzes,
                'avg_percentage': round(p.avg_percentage, 2)
            })

        # Sort categories alphabetically for consistent tab order
        sorted_leaderboards = dict(sorted(leaderboards.items()))

        return render_template('auth/leaderboard.html', 
                             leaderboards=sorted_leaderboards,
                             top_performers=normalized_top)
    except Exception as e:
        flash('Error loading leaderboard data: ' + str(e), 'error')
        return render_template('auth/leaderboard.html', 
                             leaderboards={},
                             top_performers=[])