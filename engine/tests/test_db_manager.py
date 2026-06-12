import pytest


class TestDBManager:
    def test_health_check_all_ok(self, init_test_db):
        db = init_test_db
        health = db.health_check()
        for name, result in health.items():
            assert result["ok"], f"{name}.db not ok: {result.get('error')}"
            assert result["tables"] > 0

    def test_query_and_execute(self, init_test_db):
        db = init_test_db
        db.execute(
            "self",
            "INSERT INTO profile (id, name, timezone) VALUES (?, ?, ?)",
            ("test_001", "Test User", "UTC"),
        )
        rows = db.query("self", "SELECT * FROM profile WHERE id=?", ("test_001",))
        assert len(rows) == 1
        assert rows[0]["name"] == "Test User"

    def test_query_empty_result(self, init_test_db):
        db = init_test_db
        rows = db.query("self", "SELECT * FROM profile WHERE id='nonexistent'")
        assert rows == []

    def test_execute_returns_rowcount(self, init_test_db):
        db = init_test_db
        count = db.execute(
            "self",
            "INSERT INTO profile (id, name) VALUES (?, ?)",
            ("rowcount_test", "Rowcount"),
        )
        assert count == 1

    def test_unknown_db_raises(self):
        import db_manager as db
        with pytest.raises(ValueError, match="Unknown database"):
            db.query("nonexistent", "SELECT 1")

    def test_bad_sql_raises(self, init_test_db):
        db = init_test_db
        with pytest.raises(Exception):
            db.query("self", "SELECT * FROM nonexistent_table")
