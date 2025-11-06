# services/session_helper.py - small helpers to init/reset the session quiz state
# services/session_helper.py
class SessionHelper:
    @staticmethod
    def init_quiz_session(session, questions):
        session['questions'] = questions
        session['score'] = 0
        session['current_index'] = 0


