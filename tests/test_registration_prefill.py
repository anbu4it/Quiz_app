import re
import pytest
from app import create_app, db


def extract_value(html: str, field: str) -> str | None:
    pattern = rf'id="{field}"[^>]*value="([^"]*)"'
    m = re.search(pattern, html)
    return m.group(1) if m else None


@pytest.fixture
def client():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    with app.app_context():
        db.create_all()
    return app.test_client()


def test_registration_prefills_on_username_length_error(client):
    # First POST with invalid short username
    resp = client.post('/register', data={
        'username': 'ab',  # too short (<3)
        'email': 'user@example.com',
        'password': 'Password1!',
        'confirm_password': 'Password1!'
    })
    assert resp.status_code == 200  # now renders template instead of redirect
    html = resp.get_data(as_text=True)
    # Prefill should retain provided email and username
    assert 'Username must be between 3 and 80 characters' in html
    assert extract_value(html, 'username') == 'ab'
    assert extract_value(html, 'email') == 'user@example.com'

def test_registration_prefills_on_password_policy_error(client):
    resp = client.post('/register', data={
        'username': 'validuser',
        'email': 'valid@example.com',
        'password': 'short',  # invalid (too weak)
        'confirm_password': 'short'
    })
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Weak password message (test mode only length check)
    assert 'Password must be at least 8 characters long' in html
    assert extract_value(html, 'username') == 'validuser'
    assert extract_value(html, 'email') == 'valid@example.com'
