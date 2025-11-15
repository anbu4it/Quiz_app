from functional_check import run_checks

def test_functional_check_runs_and_has_core_keys():
    results = run_checks()
    assert isinstance(results, dict)
    # Check a few representative keys exist and carry expected tuple shapes
    for key in ["home", "register", "quiz_finish", "db_saved", "404"]:
        assert key in results
        status, ok = results[key]
        assert isinstance(status, int)
        assert isinstance(ok, (bool, int))
