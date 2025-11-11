# routes/result_routes.py - result display
from flask import Blueprint, render_template, session, redirect, url_for
from flask_login import current_user
from models import db, Score

result_bp = Blueprint("result", __name__)

@result_bp.route("/result")
def result_page():
    """Show result and clean up session data."""
    # Validate quiz session first (before any try block that might clear session)
    questions = session.get("questions")
    if not questions:
        return redirect(url_for("main.index"))

    username = session.get("username", "User")
    score = session.get("score", 0)
    total = len(questions)
    quiz_category = session.get("quiz_category", "General Knowledge")

    # Validate score data
    if not isinstance(score, int) or not isinstance(total, int):
        score = 0  # fallback to 0 instead of failing
    
    if score < 0 or score > total:
        score = min(max(0, score), total)  # clamp to valid range

    # Save score if user is logged in (guard against accidental duplicate by checking latest)
    # Wrap database operations separately so failures don't prevent result display
    if current_user.is_authenticated:
        try:
            from datetime import datetime, timezone, timedelta
            
            last = (Score.query.filter_by(user_id=current_user.id, quiz_name=quiz_category)
                               .order_by(Score.date_taken.desc())
                               .first())
            should_insert = True
            
            # Only skip if identical score was submitted within last 5 seconds (likely a refresh)
            if last and last.score == score and last.max_score == total:
                time_diff = datetime.now(timezone.utc) - last.date_taken
                if time_diff.total_seconds() < 5:
                    should_insert = False
                    try:
                        from flask import current_app
                        current_app.logger.info(f"Skipping duplicate score for user {current_user.id} (submitted {time_diff.total_seconds():.1f}s ago)")
                    except Exception:
                        pass
            
            if should_insert:
                quiz_score = Score(
                    user_id=current_user.id,
                    quiz_name=quiz_category,
                    score=score,
                    max_score=total
                )
                db.session.add(quiz_score)
                db.session.commit()
                try:
                    from flask import current_app
                    current_app.logger.info(f"Score saved: User {current_user.username} - {quiz_category}: {score}/{total}")
                except Exception:
                    pass
        except Exception as e:
            # Log error but don't prevent result display
            db.session.rollback()
            try:
                from flask import current_app
                current_app.logger.error("Failed to save score: %s", str(e))
            except Exception:
                pass

    # Clean up session data AFTER gathering all needed values
    session_keys = ["questions", "score", "current_question", "quiz_category", "answers", "current_index"]
    for key in session_keys:
        session.pop(key, None)

    # Always show result, even if database operations failed
    return render_template("result.html", 
                        username=current_user.username if current_user.is_authenticated else username,
                        score=score, 
                        total=total,
                        category=quiz_category)
