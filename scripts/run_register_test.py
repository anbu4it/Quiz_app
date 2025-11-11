
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from models import db
from flask import session

app = create_app({'TESTING': True})
with app.app_context():
    # ensure fresh database for the test
    db.drop_all()
    db.create_all()
    c = app.test_client()
    with c:
        res = c.post('/register', data={'username':'tryagainuser','email':'tryagain@test.com','password':'Test123!','confirm_password':'Test123!'}, follow_redirects=True)
        print('STATUS', res.status_code)
        print(res.get_data(as_text=True)[:2000])
        # Check session for user_id (Flask-Login stores _user_id)
        assert '_user_id' in session, 'User should be logged in after registration.'
        print('Session login state after registration: PASSED')
