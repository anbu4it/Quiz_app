"""Deterministic quiz completion test.
Ensures a user can register, start a quiz, answer all questions correctly
and that the final score saved equals max_score.
"""

import uuid

from app import create_app
from models import Score, db


def test_quiz_full_flow():
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    with app.app_context():
        db.drop_all()
        db.create_all()

    with app.test_client() as c:
        # Register user
        uname = "u" + uuid.uuid4().hex[:6]
        r = c.post(
            "/register",
            data={
                "username": uname,
                "email": uname + "@x.com",
                "password": "Test123!",
                "confirm_password": "Test123!",
            },
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert "Logout" in r.get_data(as_text=True)

        # Start quiz
        s = c.post(
            "/quiz",
            data={"quiz_type": "General Knowledge", "username": uname},
            follow_redirects=True,
        )
        assert s.status_code == 200

        # Fetch total questions from session
        with c.session_transaction() as sess:
            total = len(sess.get("questions", []))
        assert total > 0

        # Answer each question with its correct answer
        for _ in range(total):
            with c.session_transaction() as sess:
                idx = sess.get("current_index", 0)
                questions = sess.get("questions", [])
                correct = questions[idx]["correct"] if 0 <= idx < len(questions) else None
            resp = c.post("/question", data={"answer": correct}, follow_redirects=True)
            assert resp.status_code == 200

        # On completion, check score saved
        with app.app_context():
            saved = Score.query.order_by(Score.date_taken.desc()).first()
            assert saved is not None, "Score row should be saved"
            assert saved.max_score == total
            assert saved.score == total, "All answers were correct so score should equal max_score"
