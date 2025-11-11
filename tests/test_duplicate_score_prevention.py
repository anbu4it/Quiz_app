import time

from werkzeug.security import generate_password_hash

from app import create_app
from models import User, db


def test_duplicate_score_prevention():
    """Ensure finishing a quiz and refreshing result page does not create a second score entry."""
    # Clear rate limiter state
    from routes.auth_routes import _LOGIN_ATTEMPTS
    _LOGIN_ATTEMPTS.clear()

    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    client = app.test_client()
    with app.app_context():
        db.create_all()
        user = User(
            username="dup_user",
            email="dup@example.com",
            password_hash=generate_password_hash("password123"),
        )
        db.session.add(user)
        db.session.commit()
    # Login
    client.post(
        "/login", data={"username": "dup_user", "password": "password123"}, follow_redirects=True
    )
    # Start quiz
    client.post("/quiz", data={"quiz_type": "Python Basics"}, follow_redirects=True)
    
    # Answer all questions with correct answers
    with client.session_transaction() as sess:
        total = len(sess.get("questions", []))
    
    for _ in range(total):
        with client.session_transaction() as sess:
            idx = sess.get("current_index", 0)
            questions = sess.get("questions", [])
            if idx < len(questions):
                correct = questions[idx]["correct"]
                client.post("/question", data={"answer": correct})
    
    # Visit result page
    result_resp = client.get("/result", follow_redirects=True)
    assert result_resp.status_code == 200
    
    # Count score rows after first visit
    with app.app_context():
        from models import Score

        scores = Score.query.join(User).filter(User.username == "dup_user").all()
        initial_count = len(scores)
        assert initial_count >= 1, "Should have at least one score"
    
    # Refresh result page (should redirect to index since session cleared)
    refreshed = client.get("/result", follow_redirects=True)
    assert refreshed.status_code == 200
    
    # Count score rows after refresh - should not increase
    with app.app_context():
        scores = Score.query.join(User).filter(User.username == "dup_user").all()
        assert len(scores) == initial_count, f"Score count changed after refresh: {initial_count} -> {len(scores)}"
