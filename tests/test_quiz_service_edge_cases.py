"""Tests for quiz service caching, error handling, and edge cases."""

import time
from unittest.mock import Mock, patch

import pytest

from services.quiz_service import TriviaService, _QUESTION_CACHE


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    _QUESTION_CACHE.clear()
    yield
    _QUESTION_CACHE.clear()


def test_cache_hit():
    """Test that second request for same topics uses cache."""
    svc = TriviaService(retries=1)

    call_count = {"count": 0}

    def mock_fetch(self, amount=1, category_id=None):
        call_count["count"] += 1
        return [
            {
                "question": "Test?",
                "correct_answer": "A",
                "incorrect_answers": ["B", "C", "D"],
            }
        ]

    with patch.object(TriviaService, "_fetch", mock_fetch):
        # First call - should hit API
        q1 = svc.fetch_questions_for_topics(["General Knowledge"], total_needed=5)
        assert len(q1) > 0
        assert call_count["count"] > 0

        # Second call - should use cache
        initial_count = call_count["count"]
        q2 = svc.fetch_questions_for_topics(["General Knowledge"], total_needed=5)
        assert len(q2) > 0
        assert call_count["count"] == initial_count  # No additional API calls


def test_cache_expiry():
    """Test that cache expires after TTL."""
    import os
    import importlib

    # Set very short cache TTL
    with patch.dict(os.environ, {"QUIZ_CACHE_TTL": "1"}):
        # Reload module to pick up new env var
        from services import quiz_service

        importlib.reload(quiz_service)

        TriviaService = quiz_service.TriviaService
        svc = TriviaService(retries=1)

        call_count = {"count": 0}

        def mock_fetch(self, amount=1, category_id=None):
            call_count["count"] += 1
            return [
                {
                    "question": "Test?",
                    "correct_answer": "A",
                    "incorrect_answers": ["B", "C", "D"],
                }
            ]

        with patch.object(TriviaService, "_fetch", mock_fetch):
            # First call
            svc.fetch_questions_for_topics(["General Knowledge"], total_needed=5)
            first_count = call_count["count"]

            # Wait for cache to expire
            time.sleep(1.5)

            # Second call should hit API again
            svc.fetch_questions_for_topics(["General Knowledge"], total_needed=5)
            assert call_count["count"] > first_count


def test_empty_topics_list():
    """Test that empty topics list returns empty."""
    svc = TriviaService()
    result = svc.fetch_questions_for_topics([], total_needed=5)
    assert result == []


def test_multi_topic_distribution():
    """Test that questions are properly distributed across multiple topics."""
    svc = TriviaService(retries=1)

    def mock_fetch(self, amount=1, category_id=None):
        # Return amount requested
        return [
            {
                "question": f"Q{i}?",
                "correct_answer": "A",
                "incorrect_answers": ["B", "C", "D"],
            }
            for i in range(amount)
        ]

    with patch.object(TriviaService, "_fetch", mock_fetch):
        # Request 5 questions from 2 topics
        questions = svc.fetch_questions_for_topics(
            ["General Knowledge", "Science & Nature"], total_needed=5
        )

        # Should get exactly 5 questions
        assert len(questions) == 5

        # Each question should have proper structure
        for q in questions:
            assert "question" in q
            assert "correct" in q
            assert "options" in q
            assert len(q["options"]) == 4


def test_fallback_to_generic_when_category_fails():
    """Test fallback to generic questions when specific category fails."""
    svc = TriviaService(retries=1)

    def mock_fetch(self, amount=1, category_id=None):
        if category_id is not None:
            # Specific category fails
            return []
        else:
            # Generic fallback succeeds
            return [
                {
                    "question": f"Generic Q{i}?",
                    "correct_answer": "A",
                    "incorrect_answers": ["B", "C", "D"],
                }
                for i in range(amount)
            ]

    with patch.object(TriviaService, "_fetch", mock_fetch):
        questions = svc.fetch_questions_for_topics(["Computers"], total_needed=5)
        # Should get generic questions as fallback
        assert len(questions) == 5


def test_fetch_with_custom_timeout():
    """Test that custom timeout is used."""
    import os

    with patch.dict(os.environ, {"TRIVIA_TIMEOUT_SECONDS": "10"}):
        # Reimport to pick up env var
        import importlib

        from services import quiz_service

        importlib.reload(quiz_service)

        svc = quiz_service.TriviaService()
        assert svc.timeout == 10


def test_fetch_with_custom_retries():
    """Test that custom retry count is used."""
    import os

    with patch.dict(os.environ, {"TRIVIA_MAX_RETRIES": "5"}):
        import importlib

        from services import quiz_service

        importlib.reload(quiz_service)

        svc = quiz_service.TriviaService()
        assert svc.retries == 5


def test_html_unescaping():
    """Test that HTML entities in questions are properly unescaped."""
    svc = TriviaService(retries=1)

    def mock_fetch(self, amount=1, category_id=None):
        return [
            {
                "question": "What&#039;s 2 &amp; 2?",
                "correct_answer": "Four &lt;4&gt;",
                "incorrect_answers": ["One &quot;1&quot;", "Two", "Three"],
            }
        ]

    with patch.object(TriviaService, "_fetch", mock_fetch):
        questions = svc.fetch_questions_for_topics(["Mathematics"], total_needed=1)

        assert questions[0]["question"] == "What's 2 & 2?"
        assert questions[0]["correct"] == "Four <4>"
        # Options should include unescaped text
        assert any('One "1"' in opt for opt in questions[0]["options"])


def test_options_shuffling():
    """Test that correct answer is shuffled into options randomly."""
    svc = TriviaService(retries=1)

    def mock_fetch(self, amount=1, category_id=None):
        return [
            {
                "question": "Test?",
                "correct_answer": "Correct",
                "incorrect_answers": ["Wrong1", "Wrong2", "Wrong3"],
            }
        ]

    with patch.object(TriviaService, "_fetch", mock_fetch):
        questions = svc.fetch_questions_for_topics(["General Knowledge"], total_needed=1)

        options = questions[0]["options"]
        assert "Correct" in options
        assert len(options) == 4
        # Correct answer should be somewhere in options
        assert questions[0]["correct"] in options


def test_insufficient_questions_returned():
    """Test handling when API returns fewer questions than requested."""
    svc = TriviaService(retries=1)

    def mock_fetch(self, amount=1, category_id=None):
        # Return only 2 questions regardless of amount requested
        return [
            {
                "question": f"Q{i}?",
                "correct_answer": "A",
                "incorrect_answers": ["B", "C", "D"],
            }
            for i in range(2)
        ]

    with patch.object(TriviaService, "_fetch", mock_fetch):
        questions = svc.fetch_questions_for_topics(["History"], total_needed=10)
        # API fallback will be called, so we may get 2 from category + 2 from generic = 4
        # The service tries to reach total_needed but uses what's available
        assert len(questions) <= 10
        assert len(questions) >= 2
