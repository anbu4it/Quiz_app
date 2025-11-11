import json
import unittest
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from models import Score, User, db


class QuizAppTestCase(unittest.TestCase):
    def setUp(self):
        # Create app with test config so DB is initialized correctly for tests
        test_cfg = {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}
        self.app = create_app(test_cfg)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self._create_test_data()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_test_data(self):
        # Create test users
        users = [
            User(
                username="test_user",
                email="test@test.com",
                password_hash=generate_password_hash("password123"),
            ),
            User(
                username="another_user",
                email="another@test.com",
                password_hash=generate_password_hash("password123"),
            ),
        ]
        for user in users:
            db.session.add(user)
        db.session.commit()

        # Create test scores
        base_date = datetime.now()
        scores = [
            Score(
                user_id=1,
                quiz_name="Python Basics",
                score=8,
                max_score=10,
                date_taken=base_date - timedelta(days=1),
            ),
            Score(
                user_id=1,
                quiz_name="JavaScript Basics",
                score=7,
                max_score=10,
                date_taken=base_date - timedelta(days=2),
            ),
            Score(
                user_id=2,
                quiz_name="Python Basics",
                score=9,
                max_score=10,
                date_taken=base_date - timedelta(days=1),
            ),
        ]
        for score in scores:
            db.session.add(score)
        db.session.commit()

    def test_homepage(self):
        """Test the homepage loads correctly"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_registration(self):
        """Test user registration process"""
        # Test successful registration
        response = self.client.post(
            "/register",
            data={"username": "new_user", "email": "new@test.com", "password": "password123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        # Test duplicate username
        response = self.client.post(
            "/register",
            data={
                "username": "test_user",
                "email": "different@test.com",
                "password": "password123",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Username already exists", response.data)

    def test_login_logout(self):
        """Test login and logout functionality"""
        # Test successful login
        response = self.client.post(
            "/login",
            data={"username": "test_user", "password": "password123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        # Test invalid login
        response = self.client.post(
            "/login",
            data={"username": "test_user", "password": "wrongpassword"},
            follow_redirects=True,
        )
        self.assertIn(b"Invalid username or password", response.data)

        # Test logout
        response = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_protected_routes(self):
        """Test access to protected routes"""
        # Try accessing protected route without login
        response = self.client.get("/dashboard", follow_redirects=True)
        self.assertIn(b"Please log in", response.data)

        # Login and try again
        self.client.post("/login", data={"username": "test_user", "password": "password123"})
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)

    def test_quiz_flow(self):
        """Test the quiz taking process"""
        # Login first
        self.client.post("/login", data={"username": "test_user", "password": "password123"})

        # Start quiz
        response = self.client.post(
            "/quiz", data={"quiz_type": "Python Basics"}, follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)

        # Answer questions
        response = self.client.post(
            "/question", data={"answer": "0"}  # Assuming multiple choice with index 0
        )
        self.assertEqual(response.status_code, 200)

    def test_leaderboard(self):
        """Test leaderboard functionality"""
        # Login first
        self.client.post("/login", data={"username": "test_user", "password": "password123"})

        # Access leaderboard
        response = self.client.get("/leaderboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"test_user", response.data)  # Should show our test user

    def test_dashboard(self):
        """Test dashboard functionality"""
        # Login first
        self.client.post("/login", data={"username": "test_user", "password": "password123"})

        # Access dashboard
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Python Basics", response.data)  # Should show quiz name
        self.assertIn(b"JavaScript Basics", response.data)

    def test_score_calculation(self):
        """Test score calculation and statistics"""
        user = User.query.filter_by(username="test_user").first()
        scores = Score.query.filter_by(user_id=user.id).all()

        # Calculate expected statistics
        total_score = sum(score.score for score in scores)
        total_possible = sum(score.max_score for score in scores)
        expected_average = (total_score / total_possible) * 100

        # Login and check dashboard
        self.client.post("/login", data={"username": "test_user", "password": "password123"})
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)

        # Basic checks for score display
        self.assertTrue(str(total_score).encode() in response.data)
        self.assertTrue(str(len(scores)).encode() in response.data)


if __name__ == "__main__":
    unittest.main()
