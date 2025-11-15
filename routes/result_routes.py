# routes/result_routes.py - result display
from flask import Blueprint, redirect, render_template, session, url_for
from flask_login import current_user

from models import Score, db
from datetime import date, timedelta

result_bp = Blueprint("result", __name__)


def _update_user_streak(user):
    """Update user's quiz streak based on current date."""
    today = date.today()
    last_quiz_date = user.last_quiz_date
    
    if last_quiz_date is None:
        # First quiz ever
        user.current_streak = 1
        user.longest_streak = 1
        user.last_quiz_date = today
    elif last_quiz_date == today:
        # Already completed a quiz today, no change
        pass
    elif last_quiz_date == today - timedelta(days=1):
        # Completed quiz yesterday, continue streak
        user.current_streak += 1
        if user.current_streak > user.longest_streak:
            user.longest_streak = user.current_streak
        user.last_quiz_date = today
    else:
        # Streak broken, start over
        user.current_streak = 1
        user.last_quiz_date = today


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
    # Time tracking
    started = session.get("quiz_started_at")
    limit = session.get("quiz_time_limit_sec", 0)
    import time as _t

    time_spent = None
    if started:
        try:
            time_spent = max(0, int(_t.time()) - int(started))
        except Exception:
            time_spent = None

    # Validate score data
    if not isinstance(score, int) or not isinstance(total, int):
        score = 0  # fallback to 0 instead of failing

    if score < 0 or score > total:
        score = min(max(0, score), total)  # clamp to valid range

    # Save score if user is logged in (guard against accidental duplicate by checking latest)
    # Wrap database operations separately so failures don't prevent result display
    achievements = []
    if current_user.is_authenticated:
        try:
            from datetime import datetime, timezone

            last = (
                Score.query.filter_by(user_id=current_user.id, quiz_name=quiz_category)
                .order_by(Score.date_taken.desc())
                .first()
            )
            should_insert = True

            # Only skip if identical score was submitted within last 5 seconds (likely a refresh)
            if last and last.score == score and last.max_score == total:
                time_diff = datetime.now(timezone.utc) - last.date_taken
                if time_diff.total_seconds() < 5:
                    should_insert = False
                    try:
                        from flask import current_app

                        current_app.logger.info(
                            f"Skipping duplicate score for user {current_user.id} (submitted {time_diff.total_seconds():.1f}s ago)"
                        )
                    except Exception:
                        pass

            if should_insert:
                quiz_score = Score(
                    user_id=current_user.id, quiz_name=quiz_category, score=score, max_score=total
                )
                db.session.add(quiz_score)
                
                # Update user streak
                _update_user_streak(current_user)
                
                db.session.commit()
                try:
                    from flask import current_app

                    current_app.logger.info(
                        f"Score saved: User {current_user.username} - {quiz_category}: {score}/{total}"
                    )
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

            # Compute achievements (best-effort, non-persistent)
            try:
                total_attempts = Score.query.filter_by(user_id=current_user.id).count()
                if total_attempts == 1:
                    achievements.append(
                        {"title": "First Quiz!", "desc": "You completed your first quiz."}
                    )
                # Perfect score
                if total and score == total:
                    achievements.append(
                        {"title": "Perfect Score", "desc": "All answers correct. Outstanding!"}
                    )
                # Fast finisher: completed under 50% of time limit (if known)
                if time_spent is not None and limit:
                    if time_spent <= int(limit) // 2:
                        achievements.append(
                            {"title": "Speed Runner", "desc": "Finished in half the allotted time."}
                        )
                # Personal best for this category
                best = (
                    db.session.query(Score)
                    .filter(Score.user_id == current_user.id, Score.quiz_name == quiz_category)
                    .order_by(Score.score.desc())
                    .first()
                )
                if best and best.score == score:
                    achievements.append(
                        {"title": "Personal Best", "desc": f"Best score in {quiz_category}."}
                    )
                
                # Streak achievements
                if hasattr(current_user, 'current_streak'):
                    if current_user.current_streak >= 30:
                        achievements.append(
                            {"title": "🔥 30-Day Streak!", "desc": "30 consecutive days of learning."}
                        )
                    elif current_user.current_streak >= 7:
                        achievements.append(
                            {"title": "🔥 7-Day Streak!", "desc": "A week of consistent practice."}
                        )
                    elif current_user.current_streak >= 3:
                        achievements.append(
                            {"title": "🔥 On Fire!", "desc": f"{current_user.current_streak} day streak."}
                        )
            except Exception:
                pass

    # Clean up session data AFTER gathering all needed values
    session_keys = [
        "questions",
        "score",
        "current_question",
        "quiz_category",
        "answers",
        "current_index",
        "quiz_started_at",
        "quiz_time_limit_sec",
    ]
    for key in session_keys:
        session.pop(key, None)

    # Always show result, even if database operations failed
    return render_template(
        "result.html",
        username=current_user.username if current_user.is_authenticated else username,
        score=score,
        total=total,
        category=quiz_category,
        achievements=achievements,
        time_limit=limit,
        time_spent=time_spent,
    )
