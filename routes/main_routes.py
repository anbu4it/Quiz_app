# routes/main_routes.py - homepage / topic selection
from flask import Blueprint, render_template

# Categories mapping (same labels as used in services.trivia_service)
TOPICS = [
    "General Knowledge",
    "Science & Nature",
    "Computers",
    "Mathematics",
    "Sports",
    "History",
    "Geography",
    "Art",
    "Celebrities",
]

main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET"])
def index():
    """Home page: name + topic selection"""
    return render_template("index.html", topics=TOPICS)
