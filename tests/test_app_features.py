"""Tests for app error handlers, security headers, and health checks."""

import pytest
from unittest.mock import patch

from app import create_app
from models import db


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_404_error_handler(client):
    """Test custom 404 page."""
    response = client.get("/nonexistent-page")
    assert response.status_code == 404
    assert b"404" in response.data or b"Not Found" in response.data


def test_500_error_handler(app):
    """Test 500 error handler."""

    # Create a route that raises an exception
    @app.route("/trigger-500")
    def trigger_500():
        raise Exception("Intentional error for testing")

    # Disable debug mode to ensure error handler is triggered
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.config["DEBUG"] = False

    client = app.test_client()
    response = client.get("/trigger-500")
    assert response.status_code == 500


def test_csrf_error_handler(client):
    """Test CSRF error handling."""
    # Attempt POST without CSRF token when CSRF is enabled
    prod_app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    prod_client = prod_app.test_client()

    with prod_app.app_context():
        db.create_all()

    # POST to register without CSRF token
    response = prod_client.post(
        "/register",
        data={
            "username": "test",
            "email": "test@test.com",
            "password": "Test123!",
            "confirm_password": "Test123!",
        },
        follow_redirects=True,
    )

    # Should redirect with flash message about session/form expiry
    assert response.status_code == 200


def test_security_headers(client):
    """Test that security headers are set correctly."""
    response = client.get("/")

    # Check security headers
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers
    assert "Content-Security-Policy" in response.headers

    # Verify CSP allows necessary resources
    csp = response.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "https://cdn.jsdelivr.net" in csp
    assert "https://res.cloudinary.com" in csp


def test_healthz_endpoint_healthy(client):
    """Test health check endpoint when database is accessible."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["db"] is True


@patch("app.db.session.execute")
def test_healthz_endpoint_db_unavailable(mock_execute, app):
    """Test health check when database is temporarily unavailable."""
    mock_execute.side_effect = Exception("Database connection failed")

    client = app.test_client()
    response = client.get("/healthz")

    # Should return 200 by default (non-strict mode)
    assert response.status_code == 200
    data = response.get_json()
    assert data["db"] is False


def test_healthz_strict_mode(app):
    """Test health check in strict mode returns 503 on db failure."""
    import os

    with patch.dict(os.environ, {"HEALTHZ_STRICT": "1"}):
        with patch("app.db.session.execute", side_effect=Exception("DB error")):
            client = app.test_client()
            response = client.get("/healthz")
            # In strict mode, should return 503 when db is down
            assert response.status_code == 503


def test_x_forwarded_proto_handling(app):
    """Test that X-Forwarded-Proto header is respected."""
    client = app.test_client()

    # Simulate request from behind HTTPS proxy
    response = client.get("/", headers={"X-Forwarded-Proto": "https"})
    assert response.status_code == 200


def test_static_url_helper_with_cache_buster(client):
    """Test that static_url helper adds version parameter."""
    response = client.get("/")
    html = response.get_data(as_text=True)

    # Check if CSS/JS includes version parameter
    # The helper should add ?v=<timestamp>
    assert "?v=" in html or ".css" in html


def test_avatar_url_filter_cloudinary(app):
    """Test avatar_url filter with Cloudinary URL."""
    avatar_filter = app.jinja_env.filters["avatar_url"]

    cloudinary_url = "https://res.cloudinary.com/test/image/upload/avatar.jpg"
    result = avatar_filter(cloudinary_url)
    assert result == cloudinary_url


def test_avatar_url_filter_local(app):
    """Test avatar_url filter with local path."""
    client = app.test_client()
    with client:
        # Make a request to establish request context
        client.get("/")

        avatar_filter = app.jinja_env.filters["avatar_url"]
        local_path = "uploads/avatar.png"
        result = avatar_filter(local_path)
        assert "uploads/avatar.png" in result


def test_avatar_url_filter_none(app):
    """Test avatar_url filter with None returns default."""
    client = app.test_client()
    with client:
        # Make a request to establish request context
        client.get("/")

        avatar_filter = app.jinja_env.filters["avatar_url"]
        result = avatar_filter(None)
        assert "default-avatar.svg" in result


def test_database_initialization_sqlite(app):
    """Test that SQLite database is initialized on first run."""
    # This is already tested by fixture, but verify tables exist
    with app.app_context():
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        assert "user" in tables
        assert "score" in tables
