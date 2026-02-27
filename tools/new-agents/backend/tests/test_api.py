import pytest
import os
import sys

# Add parent directory to path to easily import our app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We expect an ImportError initially since `app` does not exist
os.environ['FLASK_TESTING'] = '1'
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

from unittest.mock import patch, MagicMock

def test_chat_stream_missing_config(client):
    """Test streaming when no default configuration exists."""
    response = client.post('/api/chat/stream', json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 503
    assert "系统未配置" in response.json["error"]

@patch('app.OpenAI')
def test_chat_stream_success(mock_openai, client):
    """Test successful SSE stream."""
    from app import get_session
    from models import LlmConfig
    
    with app.app_context():
        session = get_session()
        config = session.query(LlmConfig).filter_by(config_key='default').first()
        if not config:
            config = LlmConfig(config_key='default', api_key='sk-123', base_url='http://t', model='gpt-4')
            session.add(config)
            session.commit()

    # Mock the return values for stream
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    class MockDelta:
        def __init__(self, content): self.content = content
    class MockChoice:
        def __init__(self, delta): self.delta = delta
    class MockChunk:
        def __init__(self, content): self.choices = [MockChoice(MockDelta(content))] if content else []

    mock_client.chat.completions.create.return_value = [
        MockChunk("Hello"),
        MockChunk(" World")
    ]

    response = client.post('/api/chat/stream', json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 200
    assert response.mimetype == 'text/event-stream'
    
    # Process the stream generator
    data = response.get_data(as_text=True)
    assert 'data: {"content": "Hello"}' in data
    assert 'data: {"content": " World"}' in data
    assert 'data: [DONE]' in data

@patch('app.OpenAI')
def test_chat_stream_openai_error(mock_openai, client):
    """Test handling of OpenAI exception during stream creation."""
    from app import get_session
    from models import LlmConfig
    
    with app.app_context():
        session = get_session()
        if not session.query(LlmConfig).filter_by(config_key='default').first():
            session.add(LlmConfig(config_key='default', api_key='sk', base_url='x', model='y'))
            session.commit()

    mock_openai.side_effect = Exception("OpenAI API unreachable")
    
    response = client.post('/api/chat/stream', json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 200 # It returns 200 and streams the error
    
    data = response.get_data(as_text=True)
    assert 'data: {"error": "OpenAI API unreachable"}' in data
