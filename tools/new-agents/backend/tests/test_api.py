import pytest
import os
import sys
import tempfile
from unittest.mock import patch
from sqlalchemy import text

# Add parent directory to path to easily import our app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set testing environment before importing
os.environ["FLASK_TESTING"] = "1"

from app import create_app, init_db
from models import db, LlmConfig


@pytest.fixture
def app():
    """Create application with test configuration."""
    db_fd, db_path = tempfile.mkstemp()

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_init_db_upgrades_existing_artifact_comment_table():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    try:
        with app.app_context():
            db.session.execute(text("""
                CREATE TABLE agent_artifact_comments (
                    id INTEGER PRIMARY KEY,
                    run_id VARCHAR(36) NOT NULL,
                    client_id VARCHAR(128) NOT NULL,
                    stage_id VARCHAR(64) NOT NULL,
                    content TEXT NOT NULL,
                    artifact_excerpt TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL
                )
            """))
            db.session.commit()

            init_db(app)

            columns = {
                row[1]
                for row in db.session.execute(
                    text("PRAGMA table_info(agent_artifact_comments)")
                )
            }

        assert {"anchor_text", "status", "resolved_at_ms", "replies_json"}.issubset(
            columns
        )
    finally:
        os.close(db_fd)
        os.unlink(db_path)


def test_init_db_upgrades_existing_artifact_section_lock_table():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    try:
        with app.app_context():
            db.session.execute(text("""
                CREATE TABLE agent_artifact_section_locks (
                    id INTEGER PRIMARY KEY,
                    run_id VARCHAR(36) NOT NULL,
                    client_id VARCHAR(128) NOT NULL,
                    stage_id VARCHAR(64) NOT NULL,
                    heading TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL
                )
            """))
            db.session.commit()

            init_db(app)

            columns = {
                row[1]
                for row in db.session.execute(
                    text("PRAGMA table_info(agent_artifact_section_locks)")
                )
            }

        assert "section_anchor" in columns
    finally:
        os.close(db_fd)
        os.unlink(db_path)


def test_init_db_upgrades_existing_artifact_version_table_with_artifact_data_json():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    try:
        with app.app_context():
            db.session.execute(text("""
                CREATE TABLE agent_artifact_versions (
                    id INTEGER PRIMARY KEY,
                    artifact_id INTEGER NOT NULL,
                    version_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME
                )
            """))
            db.session.commit()

            init_db(app)

            columns = {
                row[1]
                for row in db.session.execute(
                    text("PRAGMA table_info(agent_artifact_versions)")
                )
            }

        assert "artifact_data_json" in columns
    finally:
        os.close(db_fd)
        os.unlink(db_path)


def test_init_db_upgrades_existing_turn_metric_table_with_diagnostic_json():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    try:
        with app.app_context():
            db.session.execute(text("""
                CREATE TABLE agent_run_turn_metrics (
                    id INTEGER PRIMARY KEY,
                    run_id VARCHAR(36) NOT NULL,
                    workflow_id VARCHAR(64) NOT NULL,
                    stage_id VARCHAR(64) NOT NULL,
                    model VARCHAR(128) NOT NULL,
                    provider VARCHAR(128) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    error_code VARCHAR(64),
                    duration_ms INTEGER NOT NULL,
                    input_chars INTEGER NOT NULL DEFAULT 0,
                    output_chars INTEGER NOT NULL DEFAULT 0,
                    estimated_tokens INTEGER NOT NULL DEFAULT 0,
                    contract_retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME
                )
            """))
            db.session.commit()

            init_db(app)

            columns = {
                row[1]
                for row in db.session.execute(
                    text("PRAGMA table_info(agent_run_turn_metrics)")
                )
            }

        assert "diagnostic_json" in columns
    finally:
        os.close(db_fd)
        os.unlink(db_path)


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok", "service": "new-agents-backend"}


def test_get_config_no_default(client):
    """Test getting config when DB has no default key."""
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json == {
        "hasDefault": False,
        "browserConfigAdminAvailable": True,
    }


def test_get_config_reports_browser_admin_unavailable_in_production(
    client,
    monkeypatch,
):
    monkeypatch.setenv("AI4SE_ENV", "production")
    monkeypatch.setenv("NEW_AGENTS_CONFIG_ADMIN_ALLOW_UNAUTHENTICATED", "true")

    response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json == {
        "hasDefault": False,
        "browserConfigAdminAvailable": False,
    }


def test_get_config_with_default(client, app):
    """Test getting config when DB has a default key - should NOT expose api_key."""
    with app.app_context():
        config = LlmConfig(
            config_key="default",
            api_key="secret-api-key",
            base_url="https://fake.url/",
            model="test-model",
            description="Test config",
        )
        db.session.add(config)
        db.session.commit()

    response = client.get("/api/config")
    assert response.status_code == 200

    data = response.json
    assert data["hasDefault"] is True
    assert data["baseUrl"] == "https://fake.url/"
    assert data["model"] == "test-model"
    assert data["description"] == "Test config"
    assert "api_key" not in data  # Key security requirement


def test_get_config_uses_environment_selected_config_key(client, app, monkeypatch):
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_CONFIG_KEY", "staging")
    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="default-secret",
                base_url="https://default.test/v1",
                model="default-model",
                description="Default config",
            )
        )
        db.session.add(
            LlmConfig(
                config_key="staging",
                api_key="staging-secret",
                base_url="https://staging.test/v1",
                model="staging-model",
                description="Staging config",
            )
        )
        db.session.commit()

    response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json == {
        "hasDefault": True,
        "baseUrl": "https://staging.test/v1",
        "model": "staging-model",
        "description": "Staging config",
        "browserConfigAdminAvailable": True,
    }


def test_post_config_creates_default_config_without_exposing_api_key(client, app):
    response = client.post(
        "/api/config",
        json={
            "apiKey": "new-secret",
            "baseUrl": "https://api.test.com/v1",
            "model": "test-model",
            "description": "UI managed config",
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "hasDefault": True,
        "baseUrl": "https://api.test.com/v1",
        "model": "test-model",
        "description": "UI managed config",
    }
    assert "apiKey" not in response.json
    assert "api_key" not in response.json

    with app.app_context():
        config = LlmConfig.query.filter_by(config_key="default").one()
        assert config.api_key == "new-secret"
        assert config.is_active is True


def test_post_config_updates_default_config_and_preserves_key_when_omitted(client, app):
    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="existing-secret",
                base_url="https://old.test/v1",
                model="old-model",
                description="Old config",
            )
        )
        db.session.commit()

    response = client.post(
        "/api/config",
        json={
            "baseUrl": "https://new.test/v1",
            "model": "new-model",
            "description": "New config",
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "hasDefault": True,
        "baseUrl": "https://new.test/v1",
        "model": "new-model",
        "description": "New config",
    }

    with app.app_context():
        config = LlmConfig.query.filter_by(config_key="default").one()
        assert config.api_key == "existing-secret"
        assert config.base_url == "https://new.test/v1"
        assert config.model == "new-model"


def test_post_config_updates_environment_selected_config_key(client, app, monkeypatch):
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_CONFIG_KEY", "staging")
    response = client.post(
        "/api/config",
        json={
            "apiKey": "staging-secret",
            "baseUrl": "https://staging.test/v1",
            "model": "staging-model",
        },
    )

    assert response.status_code == 200

    with app.app_context():
        assert LlmConfig.query.filter_by(config_key="default").first() is None
        config = LlmConfig.query.filter_by(config_key="staging").one()
        assert config.api_key == "staging-secret"
        assert config.base_url == "https://staging.test/v1"
        assert config.model == "staging-model"


def test_post_config_requires_api_key_when_creating_default_config(client):
    response = client.post(
        "/api/config",
        json={
            "baseUrl": "https://api.test.com/v1",
            "model": "test-model",
        },
    )

    assert response.status_code == 400
    assert response.json == {"error": "apiKey 不能为空"}


def test_post_config_check_requires_default_config(client):
    response = client.post("/api/config/check")

    assert response.status_code == 503
    assert "系统未配置" in response.json["error"]


def test_post_config_check_returns_model_availability_result(client, app):
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

    with patch("routes.check_default_llm_config") as mock_check:
        mock_check.return_value = {
            "ok": True,
            "baseUrl": "https://api.test.com/v1",
            "model": "test-model",
            "message": "模型配置可用",
        }
        response = client.post("/api/config/check")

    assert response.status_code == 200
    assert response.json == {
        "ok": True,
        "baseUrl": "https://api.test.com/v1",
        "model": "test-model",
        "message": "模型配置可用",
    }
    config = mock_check.call_args.args[0]
    assert config.api_key == "secret-api-key"


def test_runtime_default_config_check_uses_only_saved_provider_target(client, app):
    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="secret-api-key",
                base_url="https://saved.test/v1",
                model="saved-model",
                description="Saved config",
            )
        )
        db.session.commit()

    with patch("routes.check_default_llm_config") as mock_check:
        mock_check.return_value = {
            "ok": True,
            "baseUrl": "https://saved.test/v1",
            "model": "saved-model",
            "message": "模型配置可用",
        }
        response = client.post("/api/config/default/check")

    assert response.status_code == 200
    config = mock_check.call_args.args[0]
    assert config.api_key == "secret-api-key"
    assert config.base_url == "https://saved.test/v1"
    assert config.model == "saved-model"


def test_runtime_default_config_check_rejects_target_override(client, app):
    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="secret-api-key",
                base_url="https://saved.test/v1",
                model="saved-model",
            )
        )
        db.session.commit()

    with patch("routes.check_default_llm_config") as mock_check:
        response = client.post(
            "/api/config/default/check",
            json={
                "baseUrl": "https://attacker.example/v1",
                "model": "capture-authorization",
            },
        )

    assert response.status_code == 400
    mock_check.assert_not_called()


def test_runtime_default_config_check_rejects_saved_provider_proxy_collision(
    client,
    app,
    monkeypatch,
):
    monkeypatch.setenv("PROXY_API_KEY", "saved-provider-key")
    monkeypatch.setenv("NEW_AGENTS_CONFIG_ADMIN_API_KEY", "admin-key")
    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="saved-provider-key",
                base_url="https://saved.test/v1",
                model="saved-model",
            )
        )
        db.session.commit()

    with patch("routes.check_default_llm_config") as mock_check:
        response = client.post(
            "/api/config/default/check",
            headers={"X-API-Key": "saved-provider-key"},
        )

    assert response.status_code == 503
    assert response.json == {"error": "服务认证未正确配置"}
    mock_check.assert_not_called()


def test_config_update_rejects_provider_key_matching_runtime_credential(
    client,
    monkeypatch,
):
    monkeypatch.setenv("PROXY_API_KEY", "runtime-key")
    monkeypatch.setenv("NEW_AGENTS_CONFIG_ADMIN_API_KEY", "admin-key")
    monkeypatch.delenv("NEW_AGENTS_DEFAULT_LLM_API_KEY", raising=False)

    response = client.post(
        "/api/config",
        json={
            "apiKey": "runtime-key",
            "baseUrl": "https://api.test.com/v1",
            "model": "test-model",
        },
        headers={"X-API-Key": "admin-key"},
    )

    assert response.status_code == 400
    assert response.json == {
        "error": "模型密钥不得与配置管理或运行时代理密钥复用",
    }


def test_temporary_config_check_rejects_provider_key_matching_admin_credential(
    client,
    monkeypatch,
):
    monkeypatch.setenv("PROXY_API_KEY", "runtime-key")
    monkeypatch.setenv("NEW_AGENTS_CONFIG_ADMIN_API_KEY", "admin-key")
    monkeypatch.delenv("NEW_AGENTS_DEFAULT_LLM_API_KEY", raising=False)

    response = client.post(
        "/api/config/check",
        json={
            "apiKey": "admin-key",
            "baseUrl": "https://api.test.com/v1",
            "model": "test-model",
        },
        headers={"X-API-Key": "admin-key"},
    )

    assert response.status_code == 400
    assert response.json == {
        "error": "模型密钥不得与配置管理或运行时代理密钥复用",
    }


def test_post_config_check_uses_temporary_form_config_without_persisting(client, app):
    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="saved-secret",
                base_url="https://saved.test/v1",
                model="saved-model",
                description="Saved config",
            )
        )
        db.session.commit()

    with patch("routes.check_default_llm_config") as mock_check:
        mock_check.return_value = {
            "ok": True,
            "baseUrl": "https://current.test/v1",
            "model": "current-model",
            "message": "模型配置可用",
        }
        response = client.post(
            "/api/config/check",
            json={
                "apiKey": "current-secret",
                "baseUrl": "https://current.test/v1",
                "model": "current-model",
                "description": "Current config",
            },
        )

    assert response.status_code == 200
    assert response.json == {
        "ok": True,
        "baseUrl": "https://current.test/v1",
        "model": "current-model",
        "message": "模型配置可用",
    }
    config = mock_check.call_args.args[0]
    assert config.api_key == "current-secret"
    assert config.base_url == "https://current.test/v1"
    assert config.model == "current-model"

    with app.app_context():
        saved = LlmConfig.query.filter_by(config_key="default").one()
        assert saved.api_key == "saved-secret"
        assert saved.base_url == "https://saved.test/v1"
        assert saved.model == "saved-model"


def test_post_config_check_reuses_saved_key_for_temporary_form_config(client, app):
    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="saved-secret",
                base_url="https://saved.test/v1",
                model="saved-model",
                description="Saved config",
            )
        )
        db.session.commit()

    with patch("routes.check_default_llm_config") as mock_check:
        mock_check.return_value = {
            "ok": True,
            "baseUrl": "https://current.test/v1",
            "model": "current-model",
            "message": "模型配置可用",
        }
        response = client.post(
            "/api/config/check",
            json={
                "baseUrl": "https://current.test/v1",
                "model": "current-model",
                "description": "Current config",
            },
        )

    assert response.status_code == 200
    config = mock_check.call_args.args[0]
    assert config.api_key == "saved-secret"
    assert config.base_url == "https://current.test/v1"
    assert config.model == "current-model"


def test_init_db_creates_tables_and_seeds_default_config_from_env(monkeypatch):
    """Application DB initialization should support production config seeding."""
    db_fd, db_path = tempfile.mkstemp()
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_API_KEY", "env-secret")
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_BASE_URL", "https://llm.test/v1")
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_MODEL", "env-model")
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_DESCRIPTION", "Env managed")

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    try:
        init_db(app)

        with app.app_context():
            config = LlmConfig.query.filter_by(config_key="default").first()

            assert config is not None
            assert config.api_key == "env-secret"
            assert config.base_url == "https://llm.test/v1"
            assert config.model == "env-model"
            assert config.description == "Env managed"
            assert config.is_active is True
    finally:
        os.close(db_fd)
        os.unlink(db_path)


def test_init_db_seeds_environment_selected_config_key(monkeypatch):
    db_fd, db_path = tempfile.mkstemp()
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_CONFIG_KEY", "prod")
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_API_KEY", "prod-secret")
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_BASE_URL", "https://prod.test/v1")
    monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_MODEL", "prod-model")

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    try:
        init_db(app)

        with app.app_context():
            config = LlmConfig.query.filter_by(config_key="prod").first()

            assert config is not None
            assert config.api_key == "prod-secret"
            assert config.base_url == "https://prod.test/v1"
            assert config.model == "prod-model"
    finally:
        os.close(db_fd)
        os.unlink(db_path)
