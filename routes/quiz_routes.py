# routes/quiz_routes.py - handles quiz creation and question navigation
from flask import Blueprint, request, redirect, url_for, render_template, session, flash
from flask_login import login_required, current_user
from services.quiz_service import TriviaService
from services.session_helper import SessionHelper

quiz_bp = Blueprint("quiz", __name__)

@quiz_bp.route("/quiz", methods=["POST"])
def quiz():
    """
    Start a quiz: validate name & topics, fetch 5 questions and store in session,
    then redirect to /question.
    """
    selected_topics = request.form.getlist("topics")
    
    # Accept a single topic posted as `quiz_type` (used by tests or older forms)
    if not selected_topics:
        quiz_type = request.form.get('quiz_type')
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

    # Fetch questions using TriviaService
    trivia = TriviaService()
    try:
        questions = trivia.fetch_questions_for_topics(selected_topics, total_needed=5)
    except Exception:
        # On unexpected errors, show generic message
        return "<h3>Unable to load quiz questions. Please try again later.</h3>", 503

    if not questions:
        return "<h3>Unable to load quiz questions. Please try again later.</h3>", 503

    # Save structured questions and category to session
    session['quiz_category'] = selected_topics[0] if len(selected_topics) == 1 else 'Mixed Topics'
    SessionHelper.init_quiz_session(session, questions)

    return redirect(url_for("quiz.show_question"))


@quiz_bp.route("/question", methods=["GET", "POST"])
def show_question():
    """Display one question at a time and handle answer submission."""
    if "questions" not in session:
        return redirect(url_for("main.index"))

    questions = session["questions"]
    current_index = session.get("current_index", 0)

    # POST => evaluate answer for current_index
    if request.method == "POST":
        selected = request.form.get("answer")
        # guard for malformed session
        if current_index < 0 or current_index >= len(questions):
            return redirect(url_for("result.result_page"))

        correct_answer = questions[current_index].get("correct")
        if selected == correct_answer:
            session["score"] = session.get("score", 0) + 1

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
        previous_percentage=previous_percentage
    )
