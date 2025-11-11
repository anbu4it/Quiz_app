from unittest.mock import Mock

import pytest

from services.quiz_service import TriviaService


class DummyResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._json


def test_fetch_retry_success(monkeypatch):
    """Ensure _fetch retries after initial failures and succeeds on later attempt."""
    attempts = {"count": 0}

    def fake_get(url, params=None, timeout=None):
        attempts["count"] += 1
        # Fail first two attempts, succeed on third
        if attempts["count"] < 3:
            raise Exception("network error")
        return DummyResponse(
            {
                "results": [
                    {
                        "question": "Test Q?",
                        "correct_answer": "A",
                        "incorrect_answers": ["B", "C", "D"],
                    }
                ]
            }
        )

    monkeypatch.setattr("services.quiz_service.requests.get", fake_get)

    svc = TriviaService(timeout=1, retries=3)
    results = svc._fetch(amount=1)
    assert len(results) == 1, "Expected a single question after retries"
    assert attempts["count"] == 3, f"Expected 3 attempts, got {attempts['count']}"


def test_fetch_all_fail(monkeypatch):
    """When all attempts fail, _fetch returns empty list."""

    def fake_get(url, params=None, timeout=None):
        raise Exception("persistent failure")

    monkeypatch.setattr("services.quiz_service.requests.get", fake_get)

    svc = TriviaService(timeout=1, retries=2)
    results = svc._fetch(amount=1)
    assert results == [], "Expected empty list on persistent failures"
