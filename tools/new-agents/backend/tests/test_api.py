import pytest
import os
import sys
import tempfile

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
