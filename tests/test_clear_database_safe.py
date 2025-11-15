import builtins
import importlib
import sys
import types


def test_clear_database_safe(monkeypatch):
    # Provide a fake 'app' module exposing a Flask app object to satisfy import
    from flask import Flask

    fake_app_mod = types.ModuleType("app")
    fake_app_mod.app = Flask(__name__)

    # Temporarily inject fake 'app' for importing clear_database
    original_app_mod = sys.modules.get("app")
    sys.modules["app"] = fake_app_mod
    try:
        mod = importlib.import_module("clear_database")
    finally:
        # Restore original app module mapping to avoid polluting other tests
        if original_app_mod is not None:
            sys.modules["app"] = original_app_mod
        else:
            del sys.modules["app"]

    # Build fake objects to avoid touching real DB
    class _FakeQuery:
        def delete(self):
            return 42

    class _FakeSession:
        def commit(self):
            pass

        def rollback(self):
            pass

    # Patch Score, User, db within the module
    fake_db = types.SimpleNamespace(session=_FakeSession())
    monkeypatch.setattr(mod, "db", fake_db, raising=True)
    monkeypatch.setattr(mod, "Score", types.SimpleNamespace(query=_FakeQuery()), raising=True)
    monkeypatch.setattr(mod, "User", types.SimpleNamespace(query=_FakeQuery()), raising=True)

    # Silence prints for cleaner test output
    monkeypatch.setattr(builtins, "print", lambda *a, **k: None)

    # Execute function; should not raise
    mod.clear_all_data()
