import sqlite3

import pytest

from backend.app import create_app
from backend.models import db


MEMORY_TEST_CONFIG = {
    "TESTING": True,
    "AI4SE_ENV": "test",
    "INTENT_ACCESS_MODE": "local-dev",
    "INTENT_EXECUTION_ENABLED": False,
    "INTENT_PUBLIC_ORIGIN": "http://127.0.0.1:5001",
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
}


def test_test_factory_binds_the_requested_memory_database_before_initialization():
    app = create_app(test_config=MEMORY_TEST_CONFIG)

    with app.app_context():
        assert app.config["TESTING"] is True
        assert app.config["INTENT_PROXY_TOPOLOGY"] is None
        assert str(db.engine.url) == "sqlite:///:memory:"


def test_test_factory_rejects_file_database_before_opening_it(tmp_path):
    sentinel_path = tmp_path / "must-not-be-opened.sqlite"
    connection = sqlite3.connect(sentinel_path)
    connection.execute("CREATE TABLE sentinel (value TEXT NOT NULL)")
    connection.execute("INSERT INTO sentinel(value) VALUES ('keep')")
    connection.commit()
    connection.close()

    file_uri = f"sqlite:///{sentinel_path}"
    with pytest.raises(ValueError, match="isolated in-memory SQLite"):
        create_app(
            test_config=MEMORY_TEST_CONFIG
            | {"SQLALCHEMY_DATABASE_URI": file_uri}
        )

    connection = sqlite3.connect(sentinel_path)
    assert connection.execute("SELECT value FROM sentinel").fetchall() == [("keep",)]
    connection.close()
