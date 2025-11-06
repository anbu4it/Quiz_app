# routes/result_routes.py - result display
from flask import Blueprint, render_template, session, redirect, url_for

result_bp = Blueprint("result", __name__)

@result_bp.route("/result")
def result_page():
    """Show result. Redirect to home if no quiz in session."""
    questions = session.get("questions")
    if not questions:
        return redirect(url_for("main.index"))

    username = session.get("username", "User")
    score = session.get("score", 0)
    total = len(questions)
    return render_template("result.html", username=username, score=score, total=total)
