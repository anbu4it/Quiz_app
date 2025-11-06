# services/trivia_service.py - encapsulates Open Trivia API logic and retries/fallbacks
import requests
import html
import random
from typing import List, Dict

# mapping label -> OpenTDB category id
CATEGORY_MAP = {
    "General Knowledge": 9,
    "Science & Nature": 17,
    "Computers": 18,
    "Mathematics": 19,
    "Sports": 21,
    "History": 23,
    "Geography": 22,
    "Art": 25,
    "Celebrities": 26
}

class TriviaService:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def _fetch(self, amount: int = 1, category_id: int = None) -> List[Dict]:
        """Call OpenTDB and return list of raw question dicts (may be empty)."""
        params = {"amount": amount, "type": "multiple"}
        if category_id:
            params["category"] = category_id
        resp = requests.get("https://opentdb.com/api.php", params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])

    def fetch_questions_for_topics(self, topics: List[str], total_needed: int = 5) -> List[Dict]:
        """
        Fetch questions distributed across selected topics. Guarantee up to total_needed questions
        when possible, using fallback to general API if needed.
        Returns list of question dicts with keys: question, options, correct
        """
        questions = []

        if not topics:
            return []

        # distribute at least 1 question per topic
        per_topic = max(1, total_needed // len(topics))

        for t in topics:
            cat_id = CATEGORY_MAP.get(t)
            try:
                raw = self._fetch(amount=per_topic, category_id=cat_id)
            except Exception:
                raw = []
            for r in raw:
                q_text = html.unescape(r.get("question", ""))
                correct = html.unescape(r.get("correct_answer", ""))
                options = [html.unescape(x) for x in r.get("incorrect_answers", [])] + [correct]
                random.shuffle(options)
                if q_text and correct:
                    questions.append({"question": q_text, "options": options, "correct": correct})

        # if not enough, fetch generic questions as fallback
        if len(questions) < total_needed:
            try:
                raw = self._fetch(amount=total_needed, category_id=None)
            except Exception:
                raw = []
            for r in raw:
                q_text = html.unescape(r.get("question", ""))
                correct = html.unescape(r.get("correct_answer", ""))
                options = [html.unescape(x) for x in r.get("incorrect_answers", [])] + [correct]
                random.shuffle(options)
                if q_text and correct:
                    questions.append({"question": q_text, "options": options, "correct": correct})

        # make sure we don't ask more than available
        if not questions:
            return []

        if len(questions) <= total_needed:
            return questions
        # random sample for variability
        return random.sample(questions, total_needed)
