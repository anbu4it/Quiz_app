# routes/result_routes.py - result display
from flask import Blueprint, render_template, session, redirect, url_for
from flask_login import current_user
from models import db, Score

result_bp = Blueprint("result", __name__)

@result_bp.route("/result")
def result_page():
    """Show result and clean up session data."""
    try:
        # Validate quiz session
        questions = session.get("questions")
        if not questions:
            return redirect(url_for("main.index"))

        username = session.get("username", "User")
        score = session.get("score", 0)
        total = len(questions)
        quiz_category = session.get("quiz_category", "General Knowledge")

        # Validate score data
        if not isinstance(score, int) or not isinstance(total, int):
            raise ValueError("Invalid score data")
        
        if score < 0 or score > total:
            raise ValueError("Score out of valid range")

        # Save score if user is logged in (guard against accidental duplicate by checking latest)
        if current_user.is_authenticated:
            try:
                last = (Score.query.filter_by(user_id=current_user.id, quiz_name=quiz_category)
                                   .order_by(Score.date_taken.desc())
                                   .first())
            except Exception:
                last = None
            should_insert = True
            if last and last.score == score and last.max_score == total:
                # Heuristic: identical consecutive score for same quiz name within short time
                # might be a refresh; skip insert
                should_insert = False
            if should_insert:
                quiz_score = Score(
                    user_id=current_user.id,
                    quiz_name=quiz_category,
                    score=score,
                    max_score=total
                )
                db.session.add(quiz_score)
                db.session.commit()

        # Clean up session data
        session_keys = ["questions", "score", "current_question", "quiz_category", "answers", "current_index"]
        for key in session_keys:
            session.pop(key, None)

        return render_template("result.html", 
                            username=current_user.username if current_user.is_authenticated else username,
                            score=score, 
                            total=total,
                            category=quiz_category)
    except Exception as e:
        db.session.rollback()
        session.clear()  # Clear all session data on error
        return redirect(url_for("main.index"))
