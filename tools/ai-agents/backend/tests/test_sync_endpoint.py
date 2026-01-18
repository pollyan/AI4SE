import pytest
import json
from unittest.mock import MagicMock, patch
from backend.api.requirements import sync_session_messages
from backend.models import RequirementsMessage, RequirementsSession

# We need to mock the flask app context and db
@pytest.fixture
def app_context():
    from flask import Flask
    app = Flask(__name__)
    with app.app_context():
        yield

@pytest.fixture
def mock_db():
    with patch('backend.api.requirements.db') as mock:
        yield mock

@patch('backend.api.requirements.RequirementsSession')
@patch('backend.api.requirements.RequirementsMessage')
def test_sync_creates_tool_messages(MockMessage, MockSession, mock_db):
    from flask import Flask
    app = Flask(__name__)
    
    # Setup
    session_id = "sess_1"
    ai_msg_id = 100
    
    # Mock Session
    mock_session = MagicMock()
    MockSession.query.get.return_value = mock_session
    
    # Mock Existing AI Message
    mock_ai_msg = MagicMock()
    mock_ai_msg.id = ai_msg_id
    mock_ai_msg.session_id = session_id
    mock_ai_msg.message_metadata = "{}"
    MockMessage.query.get.return_value = mock_ai_msg
    
    # Request Data
    tool_result_msg = {
        "id": str(ai_msg_id),
        "role": "assistant",
        "content": "Checked weather.",
        "toolInvocations": [
            {
                "toolCallId": "call_123",
                "toolName": "get_weather",
                "args": {"city": "Paris"},
                "state": "result",
                "result": "Sunny"
            }
        ]
    }
    
    with app.test_request_context(
        json={"messages": [tool_result_msg]},
        content_type='application/json'
    ):
        # Execute
        sync_session_messages(session_id)
        
        # Verify AI Message Updated
        assert mock_ai_msg.content == "Checked weather."
        
        # Verify Tool Message Created
        tool_msg_calls = [
            call for call in MockMessage.call_args_list 
            if call.kwargs.get('message_type') == 'tool'
        ]
        
        # This assertion should FAIL because implementation doesn't create tool messages yet
        assert len(tool_msg_calls) == 1
        assert tool_msg_calls[0].kwargs['content'] == "Sunny"
        metadata = json.loads(tool_msg_calls[0].kwargs['message_metadata'])
        assert metadata['tool_call_id'] == "call_123"
