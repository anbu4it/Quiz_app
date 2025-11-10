"""Functional page-by-page verification script.
Run inside the virtual environment:
  python functional_check.py
Outputs tuple of (status_code, heuristic_content_ok) per route.
"""
from app import create_app
import uuid
from bs4 import BeautifulSoup

def run_checks():
    app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False})
    results = {}
    with app.test_client() as c:
        # Home
        r = c.get('/')
        results['home'] = (r.status_code, 'topics' in r.get_data(as_text=True))

        # Register
        uname = 'u'+uuid.uuid4().hex[:6]
        reg = c.post('/register', data={'username': uname, 'email': uname+'@x.com', 'password':'Test123!', 'confirm_password':'Test123!'}, follow_redirects=True)
        results['register'] = (reg.status_code, 'Logout' in reg.get_data(as_text=True))

        # Quiz start
        start = c.post('/quiz', data={'quiz_type':'General Knowledge','username':uname}, follow_redirects=True)
        results['start_quiz'] = (start.status_code, '/question' in start.request.path or 'quiz.html' in start.get_data(as_text=True))

        # Question GET
        q1 = c.get('/question')
        results['question_get'] = (q1.status_code, 'quiz.html' in q1.get_data(as_text=True))

        # Answer submission
        soup = BeautifulSoup(q1.get_data(as_text=True), 'html.parser')
        first = soup.find('input', {'name':'answer'})
        ans = first['value'] if first and first.has_attr('value') else None
        sub = c.post('/question', data={'answer': ans}, follow_redirects=True)
        results['question_post'] = (sub.status_code, ('quiz.html' in sub.get_data(as_text=True)) or ('result.html' in sub.get_data(as_text=True)))

        # Result page (may require finishing all questions; tolerant check)
        res = c.get('/result')
        results['result_page'] = (res.status_code, 'score' in res.get_data(as_text=True).lower() or 'result' in res.get_data(as_text=True).lower())

        # Dashboard
        dash = c.get('/dashboard')
        results['dashboard'] = (dash.status_code, dash.status_code == 200)

        # Profile
        prof = c.get('/profile')
        results['profile_get'] = (prof.status_code, 'Profile' in prof.get_data(as_text=True) or 'avatar' in prof.get_data(as_text=True).lower())

        # Leaderboard
        lead = c.get('/leaderboard')
        results['leaderboard'] = (lead.status_code, 'Leaderboard' in lead.get_data(as_text=True) or 'top' in lead.get_data(as_text=True).lower())

        # Logout
        lo = c.get('/logout', follow_redirects=True)
        results['logout'] = (lo.status_code, 'Login' in lo.get_data(as_text=True))

        # 404
        notf = c.get('/no_such_page_xyz')
        results['404'] = (notf.status_code, notf.status_code == 404)

        # Security headers
        home2 = c.get('/')
        results['security_headers'] = (
            200,
            bool(home2.headers.get('Content-Security-Policy')) and home2.headers.get('X-Frame-Options') == 'DENY'
        )

    return results

if __name__ == '__main__':
    for k, v in run_checks().items():
        print(f'{k}: {v}')
