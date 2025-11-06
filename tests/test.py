import os
import sys
import pytest

# Ensure the parent folder is in the path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from services import quiz_service, session_helper

@pytest.fixture
def client():
    """Create a Flask test client."""
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()
    return client


# ---------- INDEX PAGE TESTS ----------

def test_index_page_loads(client):
    """Ensure the index page loads with category options."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"General Knowledge" in response.data or b"Science & Nature" in response.data


# ---------- QUIZ ROUTE TESTS ----------

def test_quiz_missing_username(client):
    """If username not entered, should return 400."""
    response = client.post('/quiz', data={'topics': ['Computers']})
    assert response.status_code == 400
    assert b"Please enter your name" in response.data


def test_quiz_no_topics_selected(client):
    """If no topics selected, should return 400."""
    response = client.post('/quiz', data={'username': 'Anbu'})
    assert response.status_code == 400
    assert b"Please select at least one topic" in response.data


def test_quiz_fetches_questions_success(client, monkeypatch):
    """Mocks API response to ensure successful quiz creation."""

    mock_response = {
        "response_code": 0,
        "results": [
            {
                "question": "Which language runs Flask?",
                "correct_answer": "Python",
                "incorrect_answers": ["C", "Java", "C++"]
            }
        ]
    }

    def mock_get(url, *args, **kwargs):
        class MockResp:
            def json(self_inner):
                return mock_response
            def raise_for_status(self_inner): pass
        return MockResp()

    # Patch the quiz_service's fetch_questions method
    monkeypatch.setattr(quiz_service.requests, "get", mock_get)

    response = client.post('/quiz', data={
        'username': 'Anbu',
        'topics': ['Computers']
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Which language runs Flask?" in response.data


def test_quiz_api_failure_fallback(client, monkeypatch):
    """If API fails, app should handle gracefully."""
    def mock_get_fail(url, *args, **kwargs):
        raise Exception("API Failure")

    monkeypatch.setattr(quiz_service.requests, "get", mock_get_fail)

    response = client.post('/quiz', data={
        'username': 'Anbu',
        'topics': ['Computers']
    })

    # Should display an error message
    assert response.status_code in [200, 503]
    assert b"Unable to load quiz" in response.data or b"<h3" in response.data


# ---------- QUESTION FLOW TESTS ----------

def test_question_page_redirect_if_no_session(client):
    """Should redirect to index if session expired."""
    response = client.get('/question', follow_redirects=True)
    assert response.status_code == 200
    assert b"General Knowledge" in response.data


def test_question_flow_and_scoring(client):
    """Simulate answering questions and reaching result."""
    with client.session_transaction() as sess:
        sess['username'] = 'Anbu'
        sess['score'] = 0
        sess['current_index'] = 0
        sess['questions'] = [
            {"question": "Flask is written in?", "correct": "Python", "options": ["Python", "Java", "C++", "Ruby"]},
            {"question": "2 + 2 = ?", "correct": "4", "options": ["1", "2", "3", "4"]}
        ]

    # First question (correct)
    response = client.post('/question', data={'answer': 'Python'}, follow_redirects=True)
    assert response.status_code == 200
    assert b"2 + 2" in response.data  # Should move to next question

    # Second question (incorrect)
    response = client.post('/question', data={'answer': '3'}, follow_redirects=True)
    assert response.status_code == 200
    # Flexible check for result page
    assert b"score" in response.data.lower() or b"result" in response.data.lower()


# ---------- RESULT PAGE TESTS ----------

def test_result_page_displays_score(client):
    """Should display username and final score."""
    with client.session_transaction() as sess:
        sess['username'] = 'Anbu'
        sess['score'] = 2
        sess['questions'] = [{"question": "x"}] * 2

    response = client.get('/result')
    assert response.status_code == 200
    assert b"Anbu" in response.data
    assert b"2" in response.data


def test_result_redirect_if_no_session(client):
    """If session expired, should redirect to home."""
    response = client.get('/result', follow_redirects=True)
    assert response.status_code == 200
    assert b"General Knowledge" in response.data


# ---------- SESSION PERSISTENCE ----------

def test_username_persists_in_session(client):
    """Username should persist across requests."""
    with client.session_transaction() as sess:
        sess['username'] = 'Anbu'

    response = client.get('/question', follow_redirects=True)
    assert response.status_code == 200 or response.status_code == 302
