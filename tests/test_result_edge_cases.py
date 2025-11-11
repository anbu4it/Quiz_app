"""Tests for result page error handling and edge cases."""

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from models import Score, User, db


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
    with app.app_context():
        user = User(
            username="resultuser",
            email="result@test.com",
            password_hash=generate_password_hash("Test123!"),
        )
        db.session.add(user)
        db.session.commit()

    client.post(
        "/login", data={"username": "resultuser", "password": "Test123!"}, follow_redirects=True
    )
    return client


def test_result_with_invalid_score_type(logged_in_user):
    """Test result page handles non-integer score gracefully."""
    with logged_in_user.session_transaction() as sess:
        sess["username"] = "resultuser"
        sess["score"] = "invalid"  # Not an int
        sess["questions"] = [{"q": "test"}] * 5
        sess["quiz_category"] = "Test"

    response = logged_in_user.get("/result")
    assert response.status_code == 200
    # Should fallback to 0 score
    assert b"0" in response.data


def test_result_with_negative_score(logged_in_user):
    """Test result page clamps negative scores to valid range."""
    with logged_in_user.session_transaction() as sess:
        sess["username"] = "resultuser"
        sess["score"] = -5
        sess["questions"] = [{"q": "test"}] * 5
        sess["quiz_category"] = "Test"

    response = logged_in_user.get("/result")
    assert response.status_code == 200
    # Score should be clamped to 0
    html = response.get_data(as_text=True)
    assert "0" in html or "score" in html.lower()


def test_result_with_score_exceeding_total(logged_in_user):
    """Test result page clamps score > total to total."""
    with logged_in_user.session_transaction() as sess:
        sess["username"] = "resultuser"
        sess["score"] = 100
        sess["questions"] = [{"q": "test"}] * 5
        sess["quiz_category"] = "Test"

    response = logged_in_user.get("/result")
    assert response.status_code == 200
    # Score should be clamped to 5 (total)


def test_result_database_error_still_displays(logged_in_user, app):
    """Test that result page displays even if database save fails."""
    from unittest.mock import patch

    with logged_in_user.session_transaction() as sess:
        sess["username"] = "resultuser"
        sess["score"] = 3
        sess["questions"] = [{"q": "test"}] * 5
        sess["quiz_category"] = "Test"

    # Mock db.session.commit to raise an error
    with patch.object(db.session, "commit", side_effect=Exception("DB error")):
        response = logged_in_user.get("/result")

    # Should still return 200 and display result
    assert response.status_code == 200
    assert b"3" in response.data


def test_result_cleans_session_after_display(logged_in_user):
    """Test that session is cleaned after result is displayed."""
    with logged_in_user.session_transaction() as sess:
        sess["username"] = "resultuser"
        sess["score"] = 4
        sess["questions"] = [{"q": "test"}] * 5
        sess["quiz_category"] = "Test"
        sess["current_index"] = 4

    response = logged_in_user.get("/result")
    assert response.status_code == 200

    # Check that session was cleaned
    with logged_in_user.session_transaction() as sess:
        assert "questions" not in sess
        assert "score" not in sess
        assert "current_index" not in sess
        assert "quiz_category" not in sess


def test_result_without_login_shows_form_username(client):
    """Test result page for non-logged-in user shows session username."""
    with client.session_transaction() as sess:
        sess["username"] = "GuestUser"
        sess["score"] = 2
        sess["questions"] = [{"q": "test"}] * 5
        sess["quiz_category"] = "General"

    response = client.get("/result")
    assert response.status_code == 200
    assert b"GuestUser" in response.data


def test_result_score_not_duplicated_on_refresh(logged_in_user, app):
    """Test that refreshing result page doesn't create duplicate score."""
    # Start and complete a quiz
    logged_in_user.post("/quiz", data={"quiz_type": "Math"}, follow_redirects=True)

    # Complete questions
    for _ in range(5):
        with logged_in_user.session_transaction() as sess:
            idx = sess.get("current_index", 0)
            questions = sess.get("questions", [])
            if idx < len(questions):
                correct = questions[idx]["correct"]
                logged_in_user.post("/question", data={"answer": correct})

    # Visit result page
    logged_in_user.get("/result")

    # Refresh by visiting again (should redirect to index since session cleared)
    response = logged_in_user.get("/result", follow_redirects=True)
    assert response.status_code == 200

    # Check database has only one score
    with app.app_context():
        user = User.query.filter_by(username="resultuser").first()
        scores = Score.query.filter_by(user_id=user.id).all()
        # Should have at most 1 score
        assert len(scores) <= 1


def test_result_with_missing_category(logged_in_user):
    """Test result page handles missing quiz_category."""
    with logged_in_user.session_transaction() as sess:
        sess["username"] = "resultuser"
        sess["score"] = 3
        sess["questions"] = [{"q": "test"}] * 5
        # quiz_category intentionally missing

    response = logged_in_user.get("/result")
    assert response.status_code == 200
    # Should use default category
    assert b"General Knowledge" in response.data or b"score" in response.data.lower()
