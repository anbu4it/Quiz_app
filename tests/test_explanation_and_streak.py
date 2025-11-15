"""Additional tests to cover quiz explanation branch and streak updates."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from models import User, db


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "WTF_CSRF_ENABLED": False})
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def _start_basic_quiz(client, username="guest1"):
    # Kick off a quiz to populate session with questions
    resp = client.post(
        "/quiz",
        data={"quiz_type": "General Knowledge", "username": username, "difficulty": "medium"},
        follow_redirects=True,
    )
    assert resp.status_code == 200


def test_explanation_branch_renders_and_holds_index(client):
    """Posting with show_explanation should render explanation and not advance the index."""
    _start_basic_quiz(client)

    # Get current index and an answer option
    with client.session_transaction() as sess:
        idx = sess.get("current_index", 0)
        questions = sess.get("questions", [])
        assert questions, "Quiz session should contain questions"
        # pick the first option (could be correct or not)
        selected = questions[idx]["options"][0]

    # Post answer with show_explanation flag
    r = client.post("/question", data={"answer": selected, "show_explanation": "true"}, follow_redirects=True)
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    # Expect explanation UI elements
    assert "explanation-box" in html
    assert "Continue" in html and "Submit Answer" not in html

    # Ensure index did not advance
    with client.session_transaction() as sess:
        assert sess.get("current_index", 0) == idx


@pytest.fixture
def logged_in_client(app):
    with app.app_context():
        u = User(username="streaker", email="streak@test.com", password_hash=generate_password_hash("Test123!"))
        db.session.add(u)
        db.session.commit()
    c = app.test_client()
    c.post("/login", data={"username": "streaker", "password": "Test123!"}, follow_redirects=True)
    return c


def _set_result_session(c, category_label):
    # Minimal fields the result page relies on
    with c.session_transaction() as sess:
        sess["username"] = "streaker"
        sess["score"] = 1
        sess["questions"] = [{"q": "x"}] * 5
        sess["quiz_category"] = category_label


def test_streak_updates_across_days(logged_in_client, app):
    """Verify streak increments for consecutive days, holds for same-day, and resets after a gap."""
    with app.app_context():
        user = User.query.filter_by(username="streaker").first()
        # Start with no last_quiz_date
        user.last_quiz_date = None
        user.current_streak = 0
        user.longest_streak = 0
        db.session.commit()

    # First result: should set streak to 1
    _set_result_session(logged_in_client, "General D1")
    resp1 = logged_in_client.get("/result")
    assert resp1.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username="streaker").first()
        assert user.current_streak == 1
        assert user.longest_streak >= 1
        assert user.last_quiz_date == date.today()

    # Same-day repeat: should keep streak unchanged
    _set_result_session(logged_in_client, "General SameDay")
    resp_same = logged_in_client.get("/result")
    assert resp_same.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username="streaker").first()
        assert user.current_streak == 1

    # Pretend it's tomorrow so yesterday is considered consecutive
    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date.today() + timedelta(days=1)

    _set_result_session(logged_in_client, "General D2")
    with patch("routes.result_routes.date", _FakeDate):
        resp2 = logged_in_client.get("/result")
    assert resp2.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username="streaker").first()
        assert user.current_streak >= 2
        assert user.longest_streak >= 2

    # Gap of several days: move 'today' forward 5 days to reset streak
    _set_result_session(logged_in_client, "General Gap")
    class _FakeDate2(date):
        @classmethod
        def today(cls):
            return date.today() + timedelta(days=5)

    with patch("routes.result_routes.date", _FakeDate2):
        resp3 = logged_in_client.get("/result")
    assert resp3.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username="streaker").first()
        assert user.current_streak == 1
