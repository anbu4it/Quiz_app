"""Tests for profile avatar upload, password validation, and rate limiting."""

import os
import time
from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage
from werkzeug.security import generate_password_hash

from app import create_app
from models import User, db


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in_user(client, app):
    """Create and login a user."""
    # Clear rate limiter state for this session
    from routes.auth_routes import _LOGIN_ATTEMPTS
    _LOGIN_ATTEMPTS.clear()

    with app.app_context():
        user = User(
            username="profiletest",
            email="profile@test.com",
            password_hash=generate_password_hash("Test123!"),
        )
        db.session.add(user)
        db.session.commit()

    client.post(
        "/login", data={"username": "profiletest", "password": "Test123!"}, follow_redirects=True
    )
    return client


def test_profile_upload_avatar(logged_in_user, app):
    """Test uploading an avatar via profile page."""
    file_data = BytesIO(b"fake image content")
    data = {
        "full_name": "Test User",
        "bio": "Test bio",
        "avatar": (file_data, "avatar.png"),
    }

    response = logged_in_user.post(
        "/profile", data=data, content_type="multipart/form-data", follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Profile updated successfully" in response.data

    # Verify user has avatar set
    with app.app_context():
        user = User.query.filter_by(username="profiletest").first()
        assert user.avatar is not None
        assert user.full_name == "Test User"
        assert user.bio == "Test bio"


def test_profile_upload_invalid_extension(logged_in_user):
    """Test uploading file with invalid extension."""
    file_data = BytesIO(b"fake file")
    data = {"avatar": (file_data, "document.pdf")}

    response = logged_in_user.post(
        "/profile", data=data, content_type="multipart/form-data", follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Unsupported file type" in response.data


def test_profile_upload_oversized_file(logged_in_user):
    """Test uploading file exceeding size limit."""
    # Create file > 2MB
    large_data = BytesIO(b"x" * (3 * 1024 * 1024))
    data = {"avatar": (large_data, "large.jpg")}

    response = logged_in_user.post(
        "/profile", data=data, content_type="multipart/form-data", follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Avatar too large" in response.data


def test_profile_remove_avatar(app):
    """Test removing existing avatar."""
    # Clear rate limiter
    from routes.auth_routes import _LOGIN_ATTEMPTS
    _LOGIN_ATTEMPTS.clear()

    client = app.test_client()

    # Create user with avatar already set
    with app.app_context():
        user = User(
            username="avatartest",
            email="avatar@test.com",
            password_hash=generate_password_hash("Test123!"),
            avatar="uploads/test_avatar.png"
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Login
    client.post(
        "/login", data={"username": "avatartest", "password": "Test123!"}, follow_redirects=True
    )

    # Remove avatar
    response = client.post(
        "/profile",
        data={
            "remove_avatar": "1",
            "full_name": "",
            "bio": ""
        },
        content_type="multipart/form-data",
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Profile updated successfully" in response.data

    # Verify avatar was removed
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.avatar is None, f"Expected avatar to be None, but got: {user.avatar}"


def test_registration_password_mismatch(client):
    """Test registration with non-matching passwords."""
    response = client.post(
        "/register",
        data={
            "username": "testuser",
            "email": "test@test.com",
            "password": "Test123!",
            "confirm_password": "Different123!",
        },
    )

    assert response.status_code == 200
    assert b"Passwords do not match" in response.data


def test_registration_duplicate_email(client, app):
    """Test registration with already-used email."""
    with app.app_context():
        user = User(
            username="existing",
            email="existing@test.com",
            password_hash=generate_password_hash("Test123!"),
        )
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/register",
        data={
            "username": "newuser",
            "email": "existing@test.com",
            "password": "Test123!",
            "confirm_password": "Test123!",
        },
    )

    assert response.status_code == 200
    assert b"Email already registered" in response.data


def test_registration_weak_password_production_mode(app):
    """Test password policy enforcement in production mode."""
    # Create non-TESTING app to enable strict password checks
    prod_app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "WTF_CSRF_ENABLED": False})
    client = prod_app.test_client()

    with prod_app.app_context():
        db.create_all()

    # Password missing uppercase
    response = client.post(
        "/register",
        data={
            "username": "weakpass",
            "email": "weak@test.com",
            "password": "password123!",
            "confirm_password": "password123!",
        },
        follow_redirects=False
    )

    assert response.status_code == 200
    assert (
        b"Password must be at least 8 characters and include upper, lower, digit and special character"
        in response.data
    )


def test_login_rate_limiting(client, app):
    """Test login rate limiting after multiple failed attempts."""
    with app.app_context():
        user = User(
            username="ratelimit",
            email="rate@test.com",
            password_hash=generate_password_hash("Correct123!"),
        )
        db.session.add(user)
        db.session.commit()

    # Make 5 failed login attempts (threshold)
    for _ in range(5):
        client.post("/login", data={"username": "ratelimit", "password": "wrong"})

    # 6th attempt should be rate limited
    response = client.post(
        "/login", data={"username": "ratelimit", "password": "wrong"}, follow_redirects=True
    )

    assert b"Too many login attempts" in response.data


def test_login_missing_credentials(app):
    """Test login with missing username or password."""
    # Clear rate limiter state
    from routes.auth_routes import _LOGIN_ATTEMPTS
    _LOGIN_ATTEMPTS.clear()

    # Create fresh client without prior rate limiting
    fresh_app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    client = fresh_app.test_client()

    with fresh_app.app_context():
        db.create_all()

    response = client.post("/login", data={"username": "", "password": ""}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Both username and password are required" in response.data
def test_login_invalid_credentials(app):
    """Test login with wrong password."""
    # Clear rate limiter state
    from routes.auth_routes import _LOGIN_ATTEMPTS
    _LOGIN_ATTEMPTS.clear()

    # Create fresh client to avoid rate limiting interference
    fresh_app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    client = fresh_app.test_client()

    with fresh_app.app_context():
        db.create_all()
        user = User(
            username="validuser",
            email="valid@test.com",
            password_hash=generate_password_hash("Correct123!"),
        )
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/login", data={"username": "validuser", "password": "WrongPassword"}, follow_redirects=True
    )

    assert b"Invalid username or password" in response.data
def test_logout_clears_session(app):
    """Test that logout properly clears session."""
    # Clear rate limiter state
    from routes.auth_routes import _LOGIN_ATTEMPTS
    _LOGIN_ATTEMPTS.clear()

    # Create fresh client to avoid rate limiting
    fresh_app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    client = fresh_app.test_client()

    with fresh_app.app_context():
        db.create_all()
        user = User(
            username="logouttest",
            email="logout@test.com",
            password_hash=generate_password_hash("Test123!"),
        )
        db.session.add(user)
        db.session.commit()

    # Login
    client.post(
        "/login", data={"username": "logouttest", "password": "Test123!"}, follow_redirects=True
    )

    # Verify logged in
    dash_before = client.get("/dashboard")
    assert dash_before.status_code == 200    # Logout
    client.get("/logout", follow_redirects=True)

    # Dashboard should now redirect to login
    dash_after = client.get("/dashboard", follow_redirects=False)
    assert dash_after.status_code == 302
    assert "/login" in dash_after.headers.get("Location", "")
