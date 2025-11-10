from app import create_app
from models import db
import uuid

app = create_app({'TESTING': True})
with app.app_context():
    db.drop_all()
    db.create_all()
    c = app.test_client()
    uname = 'user_' + uuid.uuid4().hex[:6]
    data = {'username': uname, 'email': uname + '@test.com', 'password': 'Test123!', 'confirm_password': 'Test123!'}
    res = c.post('/register', data=data, follow_redirects=True)
    print('USERNAME:', uname)
    print('STATUS', res.status_code)
    txt = res.get_data(as_text=True)
    print(txt[:1400])
    print('\nLOGGED_IN?', ('Logout' in txt) or ('Welcome' in txt) or ('/dashboard' in txt))
