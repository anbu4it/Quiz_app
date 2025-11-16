def test_wsgi_imports_app():
    import importlib

    wsgi = importlib.import_module("wsgi")
    assert hasattr(wsgi, "app") and wsgi.app is not None
