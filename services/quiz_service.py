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

import os
from datetime import datetime, timezone
_QUESTION_CACHE: dict = {}
# Allow TTL override via env var QUIZ_CACHE_TTL (seconds)
try:
    _CACHE_TTL_SECONDS = int(os.getenv('QUIZ_CACHE_TTL', '120'))
except ValueError:
    _CACHE_TTL_SECONDS = 120

class TriviaService:
    def __init__(self, timeout: int = None, retries: int = None):
        # Allow overrides from env; fallback to provided argument or defaults
        if timeout is None:
            try:
                timeout = int(os.getenv('TRIVIA_TIMEOUT_SECONDS', '5'))
            except ValueError:
                timeout = 5
        if retries is None:
            try:
                retries = int(os.getenv('TRIVIA_MAX_RETRIES', '3'))
            except ValueError:
                retries = 3
        self.timeout = timeout
        self.retries = max(1, retries)

    def _fetch(self, amount: int = 1, category_id: int = None) -> List[Dict]:
        """Call OpenTDB with simple retry/backoff; return list of raw question dicts (may be empty)."""
        params = {"amount": amount, "type": "multiple"}
        if category_id:
            params["category"] = category_id
        # dynamic linear backoff sequence based on configured retries
        backoffs = [i * 0.4 for i in range(self.retries)]  # 0.0, 0.4, 0.8, ...
        last_err = None
        for delay in backoffs:
            if delay:
                import time as _t
                _t.sleep(delay)
            try:
                resp = requests.get("https://opentdb.com/api.php", params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                return data.get("results", [])
            except Exception as e:
                last_err = e
                continue
        # On repeated failure, return empty (caller performs fallback logic)
        return []

    def fetch_questions_for_topics(self, topics: List[str], total_needed: int = 5) -> List[Dict]:
        """
        Fetch questions distributed across selected topics. Guarantee up to total_needed questions
        when possible, using fallback to general API if needed.
        Returns list of question dicts with keys: question, options, correct
        """
        import time
        questions = []

        # Basic cache key using sorted topics and requested total
        key = (tuple(sorted(topics)), total_needed)
        now = time.time()
        cached = _QUESTION_CACHE.get(key)
        if cached and (now - cached['ts'] < _CACHE_TTL_SECONDS):
            return cached['data'][:]

        if not topics:
            return []

        # Calculate questions per topic with proper distribution
        # Ensure we fetch enough to reach total_needed even with rounding
        base_per_topic = total_needed // len(topics)
        remainder = total_needed % len(topics)
        
        # Fetch questions from each topic
        for idx, t in enumerate(topics):
            # First 'remainder' topics get an extra question to reach total_needed
            questions_to_fetch = base_per_topic + (1 if idx < remainder else 0)
            
            cat_id = CATEGORY_MAP.get(t)
            try:
                raw = self._fetch(amount=questions_to_fetch, category_id=cat_id)
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
            final = questions
        else:
            final = random.sample(questions, total_needed)

        # Store in cache
        _QUESTION_CACHE[key] = {'data': final[:], 'ts': now}
        return final
