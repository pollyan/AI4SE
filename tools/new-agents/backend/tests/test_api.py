import pytest
import os
import sys

# Add parent directory to path to easily import our app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We expect an ImportError initially since `app` does not exist
try:
    from app import app, init_db, get_session
    from models import LlmConfig
except ImportError:
    app = None

@pytest.fixture
def client():
    if app is None:
        pytest.fail("Cannot import app from app.py, implementation missing.")
        
    import tempfile
    
    # Use a temporary file path so the database state persists across connections in the same test
    db_fd, db_path = tempfile.mkstemp()
    app.config['DATABASE_URL'] = f'sqlite:///{db_path}'
    
    with app.app_context():
        # Ensure we bind our session and metadata to a single fixed engine
        from models import Base, get_engine
        engine = get_engine()
        Base.metadata.create_all(engine)
        
    with app.test_client() as client:
        yield client
        
    # Teardown
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

def test_get_config_with_default(client):
    """Test getting config when DB has a default key - should NOT expose api_key."""
    from app import get_session
    from models import LlmConfig
    
    with app.app_context():
        session = get_session()
        config = LlmConfig(
            config_key='default',
            api_key='secret-api-key',
            base_url='https://fake.url/',
            model='test-model',
            description='Test config'
        )
        session.add(config)
        session.commit()

    response = client.get('/api/config')
    assert response.status_code == 200
    
    data = response.json
    assert data['hasDefault'] is True
    assert data['baseUrl'] == 'https://fake.url/'
    assert data['model'] == 'test-model'
    assert data['description'] == 'Test config'
    assert "api_key" not in data  # Key security requirement

def test_chat_stream_empty_body(client):
    """Test standard validation for chat streaming proxy."""
    response = client.post('/api/chat/stream', json={})
    assert response.status_code == 400
    assert response.json == {"error": "请求体为空"}
    
    response2 = client.post('/api/chat/stream', json={"model": "gpt-4"})
    assert response2.status_code == 400
    assert response2.json == {"error": "messages 不能为空"}
