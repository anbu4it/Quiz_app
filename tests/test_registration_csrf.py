import re
import pytest
from app import create_app, db


def _extract_csrf(html: str) -> str | None:
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else None


def test_registration_with_csrf_enabled():
    # Create app with CSRF enabled (no TESTING override)
    app = create_app()
    client = app.test_client()

    with app.app_context():
        db.create_all()

    # GET register to obtain CSRF token
    get_resp = client.get('/register')
    assert get_resp.status_code == 200
    token = _extract_csrf(get_resp.get_data(as_text=True))
    assert token, "csrf_token not found in register form"

    # POST valid registration payload
    payload = {
        'csrf_token': token,
        'username': 'reg_user_csrf',
        'email': 'reg_user_csrf@example.com',
        'password': 'Password1!',
        'confirm_password': 'Password1!'
    }
    post_resp = client.post('/register', data=payload, follow_redirects=True)
    assert post_resp.status_code == 200
    # After successful registration, dashboard should be accessible
    dash = client.get('/dashboard', follow_redirects=False)
    assert dash.status_code == 200, "Dashboard not accessible after registration; session/cookies may not be set"
