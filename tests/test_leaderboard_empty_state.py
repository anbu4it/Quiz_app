import pytest

from app import create_app, db


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app.test_client()


def register(client, username="empty_user", email="empty@test.com", password="Test123!"):
    return client.post(
        "/register",
        data={
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def test_global_leaderboard_empty_state_shown(client):
    # Register to satisfy login_required, but do not add any scores
    r = register(client)
    assert r.status_code == 200

    res = client.get("/leaderboard")
    assert res.status_code == 200
    html = res.data.decode()
    # Check for empty-state messaging and CTA
    assert "No global leaderboard yet." in html
    assert "Start Your First Quiz" in html
