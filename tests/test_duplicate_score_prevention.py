import time

from werkzeug.security import generate_password_hash

from app import create_app
from models import User, db


def test_duplicate_score_prevention():
    """Ensure finishing a quiz and refreshing result page does not create a second score entry."""
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
    # Simulate answering all questions quickly; we don't know number so loop until redirect to result
    # We'll break on any non-200 that indicates redirect or when 'Quiz Complete' appears.
    # However current flow redirects to /result after last question.
    for _ in range(25):  # safety upper bound
        r = client.post("/question", data={"answer": "0"}, follow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308):
            # Completion redirect
            break
        # Otherwise continue until completion (may be intermediate question page)
    # Follow redirect to result page
    result_resp = client.get("/result", follow_redirects=True)
    assert result_resp.status_code == 200
    # Refresh result page (simulate user hitting F5)
    refreshed = client.get("/result", follow_redirects=True)
    assert refreshed.status_code == 200
    # Count score rows
    with app.app_context():
        from models import Score

        scores = Score.query.join(User).filter(User.username == "dup_user").all()
        assert len(scores) == 1, f"Expected 1 score, found {len(scores)}"
