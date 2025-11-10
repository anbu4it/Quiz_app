import pytest
from app import create_app, db
from models import User, Score
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone


@pytest.fixture
def client():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    with app.app_context():
        db.create_all()
        yield app.test_client()


def register(client, username='avatar_user', email='avatar@test.com', password='Test123!'):
    return client.post('/register', data={
        'username': username,
        'email': email,
        'password': password,
        'confirm_password': password
    }, follow_redirects=True)


def test_full_auth_pages_flow(client):
    """Register -> dashboard -> profile -> leaderboard -> logout -> protected access check."""
    # Register (auto-login)
    r = register(client)
    assert r.status_code == 200
    assert 'Registration successful' in r.data.decode()

    # Dashboard
    dash = client.get('/dashboard')
    assert dash.status_code == 200
    # Profile
    profile = client.get('/profile')
    assert profile.status_code == 200

    # Inject scores so leaderboard has content
    with client.application.app_context():
        user = User.query.filter_by(username='avatar_user').first()
        s1 = Score(user_id=user.id, quiz_name='General Knowledge', score=5, max_score=5)
        s2 = Score(user_id=user.id, quiz_name='Science & Nature', score=4, max_score=5)
        db.session.add_all([s1, s2])
        db.session.commit()

    leaderboard = client.get('/leaderboard')
    assert leaderboard.status_code == 200
    html = leaderboard.data.decode()
    assert 'avatar_user' in html
    assert 'General Knowledge' in html
    # Jinja HTML-escapes '&' so category may appear as &amp;
    assert ('Science & Nature' in html) or ('Science &amp; Nature' in html)
    # Default avatar fallback
    assert 'default-avatar.svg' in html

    # Logout
    logout = client.get('/logout', follow_redirects=True)
    assert logout.status_code == 200

    # Protected page should redirect or deny
    protected = client.get('/dashboard', follow_redirects=False)
    assert protected.status_code in (302, 401)
    if protected.status_code == 302:
        assert '/login' in protected.headers.get('Location', '')


def test_leaderboard_shows_custom_avatar(client):
    """Original avatar test adapted to pytest: user has custom avatar path displayed."""
    with client.application.app_context():
        user = User(username='avatar_user', email='avatar@test.com', password_hash=generate_password_hash('Test123!'), avatar='uploads/test-avatar.png')
        db.session.add(user)
        db.session.commit()
        score = Score(user_id=user.id, quiz_name='Python Quiz', score=9, max_score=10, date_taken=datetime.now(timezone.utc))
        db.session.add(score)
        db.session.commit()

    # Login via form (not register to keep avatar pre-set)
    login_resp = client.post('/login', data={'username': 'avatar_user', 'password': 'Test123!'}, follow_redirects=True)
    assert login_resp.status_code == 200

    res = client.get('/leaderboard')
    assert res.status_code == 200
    html = res.data.decode()
    assert '/static/uploads/test-avatar.png' in html
