import os
import tempfile

import pytest

from app import create_app
from config_service import (
    build_default_llm_config_payload,
    get_active_default_llm_config,
    get_default_llm_config_payload,
    upsert_default_llm_config_from_env,
)
from models import LlmConfig, db


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with app.app_context():
        db.create_all()
        yield app

    os.close(db_fd)
    os.unlink(db_path)


def test_get_active_default_llm_config_returns_none_when_missing(app) -> None:
    with app.app_context():
        assert get_active_default_llm_config() is None
        assert build_default_llm_config_payload(None) == {"hasDefault": False}


def test_get_active_default_llm_config_ignores_inactive_default(app) -> None:
    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="secret-api-key",
                base_url="https://api.test.com/v1",
                model="test-model",
                is_active=False,
            )
        )
        db.session.commit()

        assert get_active_default_llm_config() is None


def test_build_default_llm_config_payload_excludes_api_key(app) -> None:
    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="secret-api-key",
                base_url="https://api.test.com/v1",
                model="test-model",
                description="Test config",
            )
        )
        db.session.commit()

        config = get_active_default_llm_config()
        payload = build_default_llm_config_payload(config)

    assert payload == {
        "hasDefault": True,
        "baseUrl": "https://api.test.com/v1",
        "model": "test-model",
        "description": "Test config",
    }
    assert "api_key" not in payload


def test_get_default_llm_config_payload_queries_and_excludes_api_key(app) -> None:
    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="secret-api-key",
                base_url="https://api.test.com/v1",
                model="test-model",
                description="Test config",
            )
        )
        db.session.commit()

        payload = get_default_llm_config_payload()

    assert payload == {
        "hasDefault": True,
        "baseUrl": "https://api.test.com/v1",
        "model": "test-model",
        "description": "Test config",
    }
    assert "api_key" not in payload


def test_upsert_default_llm_config_from_env_creates_active_default(
    app,
    monkeypatch,
) -> None:
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_API_KEY", "env-secret")
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_BASE_URL", "https://llm.test/v1")
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_MODEL", "env-model")
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_DESCRIPTION", "Env managed")

    with app.app_context():
        config = upsert_default_llm_config_from_env()

        assert config is not None
        assert config.config_key == "default"
        assert config.api_key == "env-secret"
        assert config.base_url == "https://llm.test/v1"
        assert config.model == "env-model"
        assert config.description == "Env managed"
        assert config.is_active is True

        payload = get_default_llm_config_payload()

    assert payload == {
        "hasDefault": True,
        "baseUrl": "https://llm.test/v1",
        "model": "env-model",
        "description": "Env managed",
    }
    assert "api_key" not in payload


def test_upsert_default_llm_config_from_env_updates_and_reactivates_existing(
    app,
    monkeypatch,
) -> None:
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_API_KEY", "new-secret")
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_MODEL", "new-model")
    monkeypatch.delenv("NEW_AGENTS_DEFAULT_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("NEW_AGENTS_DEFAULT_LLM_DESCRIPTION", raising=False)

    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="old-secret",
                base_url="https://old.test/v1",
                model="old-model",
                description="Old config",
                is_active=False,
            )
        )
        db.session.commit()

        config = upsert_default_llm_config_from_env()

        assert config is not None
        assert config.api_key == "new-secret"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.model == "new-model"
        assert config.description == "Environment default LLM config"
        assert config.is_active is True
        assert LlmConfig.query.filter_by(config_key="default").count() == 1


@pytest.mark.parametrize(
    ("api_key", "model"),
    [
        ("", "env-model"),
        ("env-secret", ""),
    ],
)
def test_upsert_default_llm_config_from_env_skips_incomplete_config(
    app,
    monkeypatch,
    api_key,
    model,
) -> None:
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_API_KEY", api_key)
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_MODEL", model)
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_BASE_URL", "https://llm.test/v1")

    with app.app_context():
        config = upsert_default_llm_config_from_env()

        assert config is None
        assert LlmConfig.query.filter_by(config_key="default").first() is None
