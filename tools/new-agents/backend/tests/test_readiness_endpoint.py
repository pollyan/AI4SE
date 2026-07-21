import os
import tempfile

import pytest
from sqlalchemy.exc import SQLAlchemyError

os.environ["FLASK_TESTING"] = "1"

from app import create_app
from models import db
import routes


@pytest.fixture
def app():
    descriptor, database_path = tempfile.mkstemp()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
    os.close(descriptor)
    os.unlink(database_path)


@pytest.fixture
def client(app):
    return app.test_client()


def test_readiness_requires_database_and_returns_safe_projection(client, monkeypatch):
    response = client.get("/api/readiness")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "service": "new-agents-backend",
        "database": "ok",
    }

    def database_unavailable(_query):
        raise SQLAlchemyError("database-canary-must-not-reach-response")

    monkeypatch.setattr(routes.db.session, "execute", database_unavailable)
    unavailable = client.get("/api/readiness")

    assert unavailable.status_code == 503
    assert unavailable.get_json() == {
        "status": "unavailable",
        "service": "new-agents-backend",
        "database": "unavailable",
    }
    assert "database-canary" not in unavailable.get_data(as_text=True)


def test_readiness_stream_is_unbuffered_typed_sse(client):
    response = client.get("/api/readiness/stream")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/event-stream")
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["X-Accel-Buffering"] == "no"
    assert response.get_data(as_text=True) == (
        'data: {"type": "run_started", "runId": "readiness"}\n\n'
        "data: [DONE]\n\n"
    )
