import unittest
from app import create_app
from models import db, User, Score
from werkzeug.security import generate_password_hash
from datetime import datetime

class LeaderboardAvatarTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            # create user with avatar path pointing to static/uploads/test-avatar.png
            user = User(username='avatar_user', email='avatar@test.com', password_hash=generate_password_hash('Test123!'), avatar='uploads/test-avatar.png')
            db.session.add(user)
            db.session.commit()
            # add a score so the user shows up in leaderboard
            score = Score(user_id=user.id, quiz_name='Python Quiz', score=9, max_score=10, date_taken=datetime.utcnow())
            db.session.add(score)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_leaderboard_shows_avatar_url(self):
        with self.app.test_client() as c:
            # login the user
            res = c.post('/login', data={'username': 'avatar_user', 'password': 'Test123!'}, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            # access leaderboard (route is registered at /leaderboard)
            res = c.get('/leaderboard')
            self.assertEqual(res.status_code, 200)
            html = res.get_data(as_text=True)
            # Expect the avatar static URL to appear in the page
            self.assertIn('/static/uploads/test-avatar.png', html)

if __name__ == '__main__':
    unittest.main()
