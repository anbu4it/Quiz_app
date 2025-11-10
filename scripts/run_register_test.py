from app import create_app
from models import db

app = create_app({'TESTING': True})
with app.app_context():
    db.create_all()
    c = app.test_client()
    res = c.post('/register', data={'username':'regtest','email':'reg@test.com','password':'Test123!','confirm_password':'Test123!'}, follow_redirects=True)
    print('STATUS', res.status_code)
    print(res.get_data(as_text=True)[:2000])
