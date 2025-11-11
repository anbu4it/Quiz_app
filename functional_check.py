"""Functional page-by-page verification script.
Run inside the virtual environment:
  python functional_check.py
Outputs tuple of (status_code, heuristic_content_ok) per route.
"""

import uuid

from app import create_app


def run_checks():
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    results = {}
    with app.test_client() as c:
        # Home
        r = c.get("/")
        results["home"] = (r.status_code, "topics" in r.get_data(as_text=True))

        # Register
        uname = "u" + uuid.uuid4().hex[:6]
        reg = c.post(
            "/register",
            data={
                "username": uname,
                "email": uname + "@x.com",
                "password": "Test123!",
                "confirm_password": "Test123!",
            },
            follow_redirects=True,
        )
        results["register"] = (reg.status_code, "Logout" in reg.get_data(as_text=True))

        # Quiz start
        start = c.post(
            "/quiz",
            data={"quiz_type": "General Knowledge", "username": uname},
            follow_redirects=True,
        )
        results["start_quiz"] = (
            start.status_code,
            "/question" in start.request.path or "quiz.html" in start.get_data(as_text=True),
        )

        # Question GET initial
        q1 = c.get("/question")
        results["question_get"] = (q1.status_code, "quiz.html" in q1.get_data(as_text=True))

        # Finish the quiz by submitting the correct answer for each question from session
        # This makes the flow deterministic and should yield a perfect score
        from models import Score, db  # local import to avoid test-time circulars

        # Determine total questions from session and submit correct answers
        with c.session_transaction() as sess:
            total = len(sess.get("questions", []))
        last_resp = None
        for _ in range(max(0, total)):
            with c.session_transaction() as sess:
                idx = sess.get("current_index", 0)
                questions = sess.get("questions", [])
                correct = None
                if 0 <= idx < len(questions):
                    correct = questions[idx].get("correct")
            last_resp = c.post("/question", data={"answer": correct}, follow_redirects=True)
        # After final submission, we should be on the result page
        results["quiz_finish"] = (
            getattr(last_resp, "status_code", 0),
            last_resp is not None
            and (
                "score" in last_resp.get_data(as_text=True).lower()
                or "result" in last_resp.get_data(as_text=True).lower()
            ),
        )

        # Validate DB saved score equals total for logged-in user
        saved_ok = False
        user_id = None
        with c.session_transaction() as sess:
            uid = sess.get("_user_id")
            if uid:
                try:
                    user_id = int(uid)
                except Exception:
                    user_id = None
        if user_id:
            with app.app_context():
                try:
                    last_score = (
                        db.session.query(Score)
                        .filter_by(user_id=user_id)
                        .order_by(Score.date_taken.desc())
                        .first()
                    )
                    if last_score and last_score.max_score == total and last_score.score == total:
                        saved_ok = True
                except Exception:
                    saved_ok = False
        results["db_saved"] = (200, saved_ok)

        # Dashboard
        dash = c.get("/dashboard")
        results["dashboard"] = (dash.status_code, dash.status_code == 200)

        # Profile
        prof = c.get("/profile")
        results["profile_get"] = (
            prof.status_code,
            "Profile" in prof.get_data(as_text=True)
            or "avatar" in prof.get_data(as_text=True).lower(),
        )

        # Leaderboard
        lead = c.get("/leaderboard")
        results["leaderboard"] = (
            lead.status_code,
            "Leaderboard" in lead.get_data(as_text=True)
            or "top" in lead.get_data(as_text=True).lower(),
        )

        # Logout
        lo = c.get("/logout", follow_redirects=True)
        results["logout"] = (lo.status_code, "Login" in lo.get_data(as_text=True))

        # 404
        notf = c.get("/no_such_page_xyz")
        results["404"] = (notf.status_code, notf.status_code == 404)

        # Security headers
        home2 = c.get("/")
        results["security_headers"] = (
            200,
            bool(home2.headers.get("Content-Security-Policy"))
            and home2.headers.get("X-Frame-Options") == "DENY",
        )

    return results


if __name__ == "__main__":
    for k, v in run_checks().items():
        print(f"{k}: {v}")
