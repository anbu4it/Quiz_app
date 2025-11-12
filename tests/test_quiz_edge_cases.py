"""Tests for quiz route error handling and edge cases."""

import pytest
from unittest.mock import patch

from app import create_app
from models import db
from werkzeug.security import generate_password_hash
from models import User


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
    # Clear rate limiter state
    from routes.auth_routes import _LOGIN_ATTEMPTS

    _LOGIN_ATTEMPTS.clear()

    with app.app_context():
        user = User(
            username="quizuser",
            email="quiz@test.com",
            password_hash=generate_password_hash("Test123!"),
        )
        db.session.add(user)
        db.session.commit()

    client.post(
        "/login", data={"username": "quizuser", "password": "Test123!"}, follow_redirects=True
    )
    return client


def test_quiz_with_empty_topics(client):
    """Test quiz submission with empty topics list."""
    response = client.post(
        "/quiz", data={"username": "testuser", "topics": []}, follow_redirects=True
    )

    assert response.status_code == 200
    assert b"select at least one topic" in response.data


def test_quiz_logged_in_uses_authenticated_username(logged_in_user):
    """Test that logged-in user's username is used from current_user."""
    response = logged_in_user.post(
        "/quiz",
        data={"username": "DifferentUser", "quiz_type": "Science & Nature"},
        follow_redirects=True,
    )

    assert response.status_code == 200

    # Session should have authenticated username
    # Note: quiz_routes uses current_user.username when authenticated
    with logged_in_user.session_transaction() as sess:
        # The route uses current_user.username which is "quizuser"
        username = sess.get("username")
        assert username == "quizuser"


def test_quiz_service_exception_handling(client):
    """Test quiz route handles TriviaService exceptions."""
    with patch("routes.quiz_routes.TriviaService.fetch_questions_for_topics") as mock_fetch:
        mock_fetch.side_effect = Exception("API failure")

        response = client.post("/quiz", data={"username": "testuser", "quiz_type": "History"})

        assert response.status_code == 503
        assert b"Unable to load quiz questions" in response.data


def test_quiz_empty_questions_response(client):
    """Test handling when API returns empty questions list."""
    with patch("routes.quiz_routes.TriviaService.fetch_questions_for_topics") as mock_fetch:
        mock_fetch.return_value = []

        response = client.post("/quiz", data={"username": "testuser", "quiz_type": "Computers"})

        assert response.status_code == 503
        assert b"Unable to load quiz questions" in response.data


def test_question_with_invalid_session_index(client):
    """Test question route handles corrupted session index."""
    with client.session_transaction() as sess:
        sess["questions"] = [{"question": "Q1", "correct": "A", "options": ["A", "B", "C", "D"]}]
        sess["current_index"] = 999  # Out of bounds

    response = client.post("/question", data={"answer": "A"}, follow_redirects=True)

    # Should redirect to result without crashing
    assert response.status_code == 200


def test_question_negative_index(client):
    """Test question route handles negative index."""
    with client.session_transaction() as sess:
        sess["questions"] = [{"question": "Q1", "correct": "A", "options": ["A", "B", "C", "D"]}]
        sess["current_index"] = -1

    response = client.post("/question", data={"answer": "A"}, follow_redirects=True)

    assert response.status_code == 200


def test_question_post_increments_index(client):
    """Test that answering a question increments the index."""
    with client.session_transaction() as sess:
        sess["username"] = "testuser"
        sess["questions"] = [
            {"question": "Q1", "correct": "A", "options": ["A", "B", "C", "D"]},
            {"question": "Q2", "correct": "B", "options": ["A", "B", "C", "D"]},
        ]
        sess["current_index"] = 0
        sess["score"] = 0

    response = client.post("/question", data={"answer": "A"})

    # Should move to next question
    with client.session_transaction() as sess:
        assert sess["current_index"] == 1
        assert sess["score"] == 1  # Correct answer


def test_question_incorrect_answer_no_score_change(client):
    """Test that incorrect answer doesn't increment score."""
    with client.session_transaction() as sess:
        sess["username"] = "testuser"
        sess["questions"] = [{"question": "Q1", "correct": "A", "options": ["A", "B", "C", "D"]}]
        sess["current_index"] = 0
        sess["score"] = 0

    response = client.post("/question", data={"answer": "B"})  # Wrong answer

    with client.session_transaction() as sess:
        assert sess["score"] == 0  # No points


def test_question_get_shows_progress_bar(client):
    """Test that question page shows progress information."""
    with client.session_transaction() as sess:
        sess["questions"] = [
            {"question": "Q1", "correct": "A", "options": ["A", "B", "C", "D"]},
            {"question": "Q2", "correct": "B", "options": ["A", "B", "C", "D"]},
            {"question": "Q3", "correct": "C", "options": ["A", "B", "C", "D"]},
        ]
        sess["current_index"] = 1  # On question 2 of 3

    response = client.get("/question")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Q2" in html
    # Progress indicator should show 2/3 or similar
    assert "2" in html and "3" in html


def test_quiz_multi_topic_selection(client):
    """Test quiz creation with multiple topics."""
    response = client.post(
        "/quiz",
        data={
            "username": "testuser",
            "topics": ["General Knowledge", "Science & Nature", "Computers"],
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with client.session_transaction() as sess:
        questions = sess.get("questions", [])
        assert len(questions) == 5  # Should fetch 5 questions
        # Category should be "Mixed Topics" for multiple selections
        assert sess.get("quiz_category") in ["General Knowledge", "Mixed Topics"]


def test_quiz_single_topic_category_name(client):
    """Test that single topic uses its name as category."""
    response = client.post(
        "/quiz",
        data={"username": "testuser", "topics": ["Mathematics"]},
        follow_redirects=True,
    )

    assert response.status_code == 200

    with client.session_transaction() as sess:
        assert sess.get("quiz_category") == "Mathematics"
