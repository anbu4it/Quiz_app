# routes/quiz_routes.py - handles quiz creation and question navigation
import time

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from services.quiz_service import TriviaService
from services.session_helper import SessionHelper

quiz_bp = Blueprint("quiz", __name__)

# Import limiter if available (will be None if not installed)
try:
    from app import limiter
except ImportError:
    limiter = None


@quiz_bp.route("/quiz", methods=["POST"])
@limiter.limit("10 per minute") if limiter else lambda f: f
def quiz():
    """
    Start a quiz: validate name & topics, fetch 5 questions and store in session,
    then redirect to /question.
    """
    selected_topics = request.form.getlist("topics")

    # Accept a single topic posted as `quiz_type` (used by tests or older forms)
    if not selected_topics:
        quiz_type = request.form.get("quiz_type")
        if quiz_type:
            selected_topics = [quiz_type]

    if not selected_topics:
        flash("Please select at least one topic.")
        return redirect(url_for("main.index"))

    # Use authenticated user's username if available, otherwise use form input
    if current_user.is_authenticated:
        username = current_user.username
    else:
        username = request.form.get("username", "").strip()
        if not username:
            flash("Please enter your name.")
            return redirect(url_for("main.index"))

    if not selected_topics:
        return "<h3>Please select at least one topic. <a href='/'>Go back</a></h3>", 400

    # persist username
    session["username"] = username

    # Get difficulty level (default to medium if not specified)
    difficulty = request.form.get("difficulty", "medium")
    if difficulty not in ["easy", "medium", "hard"]:
        difficulty = "medium"

    # Fetch questions using TriviaService
    # Enable synthetic questions when API is unreachable during app flows/tests
    trivia = TriviaService(allow_synthetic=True)
    try:
        questions = trivia.fetch_questions_for_topics(
            selected_topics, total_needed=5, difficulty=difficulty
        )
    except Exception:
        # On unexpected errors, show generic message
        return "<h3>Unable to load quiz questions. Please try again later.</h3>", 503

    if not questions:
        return "<h3>Unable to load quiz questions. Please try again later.</h3>", 503

    # Save structured questions and category to session
    session["quiz_category"] = selected_topics[0] if len(selected_topics) == 1 else "Mixed Topics"
    SessionHelper.init_quiz_session(session, questions)

    # Initialize quiz timer (default 60 seconds for the whole quiz)
    try:
        session["quiz_started_at"] = int(time.time())
        # Allow override via form (seconds) but clamp to a reasonable range
        limit = request.form.get("time_limit")
        limit_sec = int(limit) if limit and str(limit).isdigit() else 60
        limit_sec = max(30, min(600, limit_sec))
        session["quiz_time_limit_sec"] = limit_sec
    except Exception:
        session["quiz_started_at"] = int(time.time())
        session["quiz_time_limit_sec"] = 60

    return redirect(url_for("quiz.show_question"))


@quiz_bp.route("/question", methods=["GET", "POST"])
def show_question():
    """Display one question at a time and handle answer submission."""
    if "questions" not in session:
        return redirect(url_for("main.index"))

    questions = session["questions"]
    current_index = session.get("current_index", 0)

    # Timer enforcement: if time expired, end quiz immediately
    started = session.get("quiz_started_at")
    limit = session.get("quiz_time_limit_sec", 60)
    now = int(time.time())
    remaining = None
    if started:
        elapsed = now - int(started)
        remaining = max(0, int(limit) - elapsed)
        if remaining <= 0:
            return redirect(url_for("result.result_page"))

    # POST => evaluate answer for current_index
    if request.method == "POST":
        selected = request.form.get("answer")
        # guard for malformed session
        if current_index < 0 or current_index >= len(questions):
            return redirect(url_for("result.result_page"))

        correct_answer = questions[current_index].get("correct")
        is_correct = selected == correct_answer

        if is_correct:
            session["score"] = session.get("score", 0) + 1

        # Check if user wants to see explanation (form includes show_explanation)
        show_explanation = request.form.get("show_explanation")
        if show_explanation:
            # Show the same question with explanation
            question = questions[current_index]
            total_questions = len(questions)
            current_percentage = ((current_index + 1) / total_questions) * 100
            previous_percentage = (
                (current_index / total_questions) * 100 if current_index > 0 else 0
            )

            return render_template(
                "quiz.html",
                question=question,
                index=current_index + 1,
                total=total_questions,
                current_percentage=current_percentage,
                previous_percentage=previous_percentage,
                time_remaining=remaining if remaining is not None else 0,
                show_explanation=True,
                selected_answer=selected,
                is_correct=is_correct,
            )

        # advance index
        session["current_index"] = current_index + 1
        current_index = session["current_index"]

        if current_index >= len(questions):
            # Quiz finished — use PRG pattern: redirect to result page to avoid duplicate submissions
            return redirect(url_for("result.result_page"))

    # show question at current_index
    question = questions[current_index]

    total_questions = len(questions)
    current_percentage = ((current_index + 1) / total_questions) * 100
    previous_percentage = (current_index / total_questions) * 100 if current_index > 0 else 0

    return render_template(
        "quiz.html",
        question=question,
        index=current_index + 1,
        total=total_questions,
        current_percentage=current_percentage,
        previous_percentage=previous_percentage,
        time_remaining=remaining if remaining is not None else 0,
    )


@quiz_bp.route("/daily", methods=["GET"])  # creates a daily challenge quiz
def daily_challenge():
    """Start a deterministic daily challenge quiz (once per day)."""
    # Label for today's challenge
    from datetime import datetime

    today_label = datetime.utcnow().strftime("%Y-%m-%d")
    category_label = f"Daily Challenge {today_label}"

    # If user already played today, just redirect to dashboard with a message
    try:
        if current_user.is_authenticated:
            from models import Score

            existing = (
                Score.query.filter(
                    Score.user_id == current_user.id, Score.quiz_name == category_label
                )
                .order_by(Score.date_taken.desc())
                .first()
            )
            if existing:
                flash(
                    "You've already completed today's Daily Challenge. Come back tomorrow!", "info"
                )
                return redirect(url_for("auth.dashboard"))
    except Exception:
        pass

    # Build deterministic questions using a date-based seed
    trivia = TriviaService(allow_synthetic=True)
    try:
        # Use a fixed set like Mixed Topics, total 5 - daily challenge uses medium difficulty
        questions = trivia.fetch_questions_for_topics(
            ["General Knowledge"], total_needed=5, difficulty="medium"
        )
    except Exception:
        return "<h3>Unable to load daily challenge. Please try again later.</h3>", 503

    if not questions:
        return "<h3>Unable to load daily challenge. Please try again later.</h3>", 503

    session["quiz_category"] = category_label
    SessionHelper.init_quiz_session(session, questions)
    # Daily challenge uses 90 seconds
    session["quiz_started_at"] = int(time.time())
    session["quiz_time_limit_sec"] = 90

    return redirect(url_for("quiz.show_question"))
