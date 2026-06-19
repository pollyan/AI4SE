import pytest
import os
import sys
import tempfile
from unittest.mock import patch
from sqlalchemy import text

# Add parent directory to path to easily import our app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set testing environment before importing
os.environ['FLASK_TESTING'] = '1'

from app import create_app, init_db
from models import db, LlmConfig


@pytest.fixture
def app():
    """Create application with test configuration."""
    db_fd, db_path = tempfile.mkstemp()

    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })

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
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })

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

        assert {"anchor_text", "status", "resolved_at_ms", "replies_json"}.issubset(columns)
    finally:
        os.close(db_fd)
        os.unlink(db_path)


def test_health_endpoint(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json == {"status": "ok", "service": "new-agents-backend"}


def test_get_config_no_default(client):
    """Test getting config when DB has no default key."""
    response = client.get('/api/config')
    assert response.status_code == 200
    assert response.json == {"hasDefault": False}


def test_get_config_with_default(client, app):
    """Test getting config when DB has a default key - should NOT expose api_key."""
    with app.app_context():
        config = LlmConfig(
            config_key='default',
            api_key='secret-api-key',
            base_url='https://fake.url/',
            model='test-model',
            description='Test config'
        )
        db.session.add(config)
        db.session.commit()

    response = client.get('/api/config')
    assert response.status_code == 200

    data = response.json
    assert data['hasDefault'] is True
    assert data['baseUrl'] == 'https://fake.url/'
    assert data['model'] == 'test-model'
    assert data['description'] == 'Test config'
    assert "api_key" not in data  # Key security requirement


def test_get_config_uses_environment_selected_config_key(client, app, monkeypatch):
    monkeypatch.setenv('NEW_AGENTS_DEFAULT_LLM_CONFIG_KEY', 'staging')
    with app.app_context():
        db.session.add(LlmConfig(
            config_key='default',
            api_key='default-secret',
            base_url='https://default.test/v1',
            model='default-model',
            description='Default config',
        ))
        db.session.add(LlmConfig(
            config_key='staging',
            api_key='staging-secret',
            base_url='https://staging.test/v1',
            model='staging-model',
            description='Staging config',
        ))
        db.session.commit()

    response = client.get('/api/config')

    assert response.status_code == 200
    assert response.json == {
        'hasDefault': True,
        'baseUrl': 'https://staging.test/v1',
        'model': 'staging-model',
        'description': 'Staging config',
    }


def test_post_config_creates_default_config_without_exposing_api_key(client, app):
    response = client.post('/api/config', json={
        'apiKey': 'new-secret',
        'baseUrl': 'https://api.test.com/v1',
        'model': 'test-model',
        'description': 'UI managed config',
    })

    assert response.status_code == 200
    assert response.json == {
        'hasDefault': True,
        'baseUrl': 'https://api.test.com/v1',
        'model': 'test-model',
        'description': 'UI managed config',
    }
    assert 'apiKey' not in response.json
    assert 'api_key' not in response.json

    with app.app_context():
        config = LlmConfig.query.filter_by(config_key='default').one()
        assert config.api_key == 'new-secret'
        assert config.is_active is True


def test_post_config_updates_default_config_and_preserves_key_when_omitted(client, app):
    with app.app_context():
        db.session.add(LlmConfig(
            config_key='default',
            api_key='existing-secret',
            base_url='https://old.test/v1',
            model='old-model',
            description='Old config',
        ))
        db.session.commit()

    response = client.post('/api/config', json={
        'baseUrl': 'https://new.test/v1',
        'model': 'new-model',
        'description': 'New config',
    })

    assert response.status_code == 200
    assert response.json == {
        'hasDefault': True,
        'baseUrl': 'https://new.test/v1',
        'model': 'new-model',
        'description': 'New config',
    }

    with app.app_context():
        config = LlmConfig.query.filter_by(config_key='default').one()
        assert config.api_key == 'existing-secret'
        assert config.base_url == 'https://new.test/v1'
        assert config.model == 'new-model'


def test_post_config_updates_environment_selected_config_key(client, app, monkeypatch):
    monkeypatch.setenv('NEW_AGENTS_DEFAULT_LLM_CONFIG_KEY', 'staging')
    response = client.post('/api/config', json={
        'apiKey': 'staging-secret',
        'baseUrl': 'https://staging.test/v1',
        'model': 'staging-model',
    })

    assert response.status_code == 200

    with app.app_context():
        assert LlmConfig.query.filter_by(config_key='default').first() is None
        config = LlmConfig.query.filter_by(config_key='staging').one()
        assert config.api_key == 'staging-secret'
        assert config.base_url == 'https://staging.test/v1'
        assert config.model == 'staging-model'


def test_post_config_requires_api_key_when_creating_default_config(client):
    response = client.post('/api/config', json={
        'baseUrl': 'https://api.test.com/v1',
        'model': 'test-model',
    })

    assert response.status_code == 400
    assert response.json == {'error': 'apiKey 不能为空'}


def test_post_config_check_requires_default_config(client):
    response = client.post('/api/config/check')

    assert response.status_code == 503
    assert "系统未配置" in response.json["error"]


def test_post_config_check_returns_model_availability_result(client, app):
    with app.app_context():
        db.session.add(LlmConfig(
            config_key='default',
            api_key='secret-api-key',
            base_url='https://api.test.com/v1',
            model='test-model',
            description='Test config',
        ))
        db.session.commit()

    with patch('routes.check_default_llm_config') as mock_check:
        mock_check.return_value = {
            'ok': True,
            'baseUrl': 'https://api.test.com/v1',
            'model': 'test-model',
            'message': '模型配置可用',
        }
        response = client.post('/api/config/check')

    assert response.status_code == 200
    assert response.json == {
        'ok': True,
        'baseUrl': 'https://api.test.com/v1',
        'model': 'test-model',
        'message': '模型配置可用',
    }
    config = mock_check.call_args.args[0]
    assert config.api_key == 'secret-api-key'


def test_init_db_creates_tables_and_seeds_default_config_from_env(monkeypatch):
    """Application DB initialization should support production config seeding."""
    db_fd, db_path = tempfile.mkstemp()
    monkeypatch.setenv('NEW_AGENTS_DEFAULT_LLM_API_KEY', 'env-secret')
    monkeypatch.setenv('NEW_AGENTS_DEFAULT_LLM_BASE_URL', 'https://llm.test/v1')
    monkeypatch.setenv('NEW_AGENTS_DEFAULT_LLM_MODEL', 'env-model')
    monkeypatch.setenv('NEW_AGENTS_DEFAULT_LLM_DESCRIPTION', 'Env managed')

    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })

    try:
        init_db(app)

        with app.app_context():
            config = LlmConfig.query.filter_by(config_key='default').first()

            assert config is not None
            assert config.api_key == 'env-secret'
            assert config.base_url == 'https://llm.test/v1'
            assert config.model == 'env-model'
            assert config.description == 'Env managed'
            assert config.is_active is True
    finally:
        os.close(db_fd)
        os.unlink(db_path)


def test_init_db_seeds_environment_selected_config_key(monkeypatch):
    db_fd, db_path = tempfile.mkstemp()
    monkeypatch.setenv('NEW_AGENTS_DEFAULT_LLM_CONFIG_KEY', 'prod')
    monkeypatch.setenv('NEW_AGENTS_DEFAULT_LLM_API_KEY', 'prod-secret')
    monkeypatch.setenv('NEW_AGENTS_DEFAULT_LLM_BASE_URL', 'https://prod.test/v1')
    monkeypatch.setenv('NEW_AGENTS_DEFAULT_LLM_MODEL', 'prod-model')

    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })

    try:
        init_db(app)

        with app.app_context():
            config = LlmConfig.query.filter_by(config_key='prod').first()

            assert config is not None
            assert config.api_key == 'prod-secret'
            assert config.base_url == 'https://prod.test/v1'
            assert config.model == 'prod-model'
    finally:
        os.close(db_fd)
        os.unlink(db_path)
