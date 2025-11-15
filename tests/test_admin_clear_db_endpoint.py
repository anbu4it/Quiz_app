import os
from flask import Flask
import importlib
import types


def test_admin_clear_db_token_flow(monkeypatch):
    admin_mod = importlib.import_module("admin_clear_db")

    app = Flask(__name__)
    app.config.update(SECRET_KEY="test")
    app.register_blueprint(admin_mod.admin_bp)

    client = app.test_client()

    # 403 when ADMIN_CLEAR_TOKEN is not set
    if "ADMIN_CLEAR_TOKEN" in os.environ:
        monkeypatch.delenv("ADMIN_CLEAR_TOKEN", raising=False)
    r = client.get("/admin/clear-database")
    assert r.status_code == 403

    # 401 when wrong token
    monkeypatch.setenv("ADMIN_CLEAR_TOKEN", "good")
    r = client.get("/admin/clear-database?token=bad")
    assert r.status_code == 401

    # 200 on success with mocked DB operations
    class _FakeQuery:
        def delete(self):
            return 1

    class _FakeSession:
        def commit(self):
            pass
        def rollback(self):
            pass

    monkeypatch.setattr(admin_mod, "Score", types.SimpleNamespace(query=_FakeQuery()), raising=True)
    monkeypatch.setattr(admin_mod, "User", types.SimpleNamespace(query=_FakeQuery()), raising=True)
    monkeypatch.setattr(admin_mod, "db", types.SimpleNamespace(session=_FakeSession()), raising=True)

    r = client.get("/admin/clear-database?token=good")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data["deleted"]["scores"] == 1
    assert data["deleted"]["users"] == 1
