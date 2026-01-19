import json
import base64

def test_stream_messages_v2_with_attachments(client, app, db_session):
    """
    Test that the backend correctly handles 'experimental_attachments' in V2 stream.
    Fail condition: Backend ignores attachments and only sees text.
    Pass condition: Backend extracts attachments, saves them to DB, and appends content to prompt.
    """
    # 1. Setup - Create a session
    from backend.models import RequirementsSession, RequirementsMessage
    import uuid
    session_id = str(uuid.uuid4())
    session = RequirementsSession(
        id=session_id,
        project_name="Test Project",
        user_context='{"assistant_type": "lisa"}'
    )
    db_session.add(session)
    db_session.commit()
    
    # 2. Simulate AI SDK request payload with attachments
    # Client sends file content as base64 data URL
    file_content = "This is the content of the attached file."
    base64_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
    data_url = f"data:text/plain;base64,{base64_content}"
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Analyze this file",
                "experimental_attachments": [
                    {
                        "name": "test_doc.txt",
                        "contentType": "text/plain",
                        "url": data_url
                    }
                ]
            }
        ]
    }
    
    # 3. Mock the AI Service dependencies
    from unittest.mock import MagicMock, patch
    
    # Mock get_ai_service to return a dummy service
    with patch('backend.api.requirements.get_ai_service') as mock_get_service:
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Mock the adapter which is called with the final prompt
        with patch('backend.agents.shared.data_stream_adapter.adapt_langgraph_stream') as mock_adapter:
            async def mock_adapt(*args, **kwargs):
                yield "processed"
            mock_adapter.side_effect = mock_adapt
            
            # 4. Execute Request
            response = client.post(
                f'/ai-agents/api/requirements/sessions/{session.id}/messages/v2/stream',
                json=payload
            )
            
            # Consume generator to trigger execution
            list(response.response)
            
            # 5. Verify Prompt Construction (The "Append to text" logic)
            # We expect the file content to be appended to the user message
            call_args = mock_adapter.call_args
            assert call_args is not None
            args, _ = call_args
            # args[2] is 'content' in adapt_langgraph_stream(service, session_id, content, ...)
            actual_content = args[2]
            
            assert "Analyze this file" in actual_content
            assert "test_doc.txt" in actual_content
            assert "This is the content of the attached file" in actual_content
            
            # 6. Verify Database Persistence
            # The User Message should be saved with attached_files metadata
            # We need to query the DB to check
            
            # Note: The view function might commit in a way that our test session sees or doesn't see depending on transaction isolation.
            # In pytest-flask-sqlalchemy, usually it's same transaction if handled right.
            # But let's check what we can.
            
            msg = RequirementsMessage.query.filter_by(session_id=session_id, message_type='user').first()
            assert msg is not None
            assert msg.attached_files is not None
            
            files_meta = json.loads(msg.attached_files)
            assert len(files_meta) == 1
            assert files_meta[0]['filename'] == 'test_doc.txt'
