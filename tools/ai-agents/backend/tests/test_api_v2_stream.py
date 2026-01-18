
def test_stream_messages_v2_with_ai_sdk_parts_format(client, app, db_session):
    """
    Test that the backend correctly handles the Vercel AI SDK 'messages' format 
    when it uses 'parts' instead of 'content' (multimodal/v2 format).
    """
    # 1. Setup - Create a session
    from backend.models import RequirementsSession
    import uuid
    session = RequirementsSession(
        id=str(uuid.uuid4()),
        project_name="Test Project",
        user_context='{"assistant_type": "lisa"}'
    )
    db_session.add(session)
    db_session.commit()
    
    # 2. Simulate AI SDK request payload with 'parts'
    # { "messages": [ { "role": "user", "parts": [{ "type": "text", "text": "Hello Parts" }] } ] }
    payload = {
        "messages": [
            {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": "Hello Parts"
                    }
                ]
            }
        ]
    }
    
    # 3. Mock the AI Service
    from unittest.mock import MagicMock, patch
    with patch('backend.api.requirements.get_ai_service') as mock_get_service:
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        async def mock_stream(*args, **kwargs):
            yield "data: {\"type\": \"text-delta\", \"text\": \"Response\"}\n\n"
        mock_service.stream_message = mock_stream
        
        with patch('backend.agents.shared.data_stream_adapter.adapt_langgraph_stream') as mock_adapter:
            async def mock_adapt(*args, **kwargs):
                yield "parsed_response"
            mock_adapter.side_effect = mock_adapt
            
            # 4. Execute Request
            response = client.post(
                f'/ai-agents/api/requirements/sessions/{session.id}/messages/v2/stream',
                json=payload
            )
            
            list(response.response)
            
            # 5. Verify
            call_args = mock_adapter.call_args
            assert call_args is not None
            args, _ = call_args
            actual_content = args[2]
            
            assert actual_content == "Hello Parts", f"Expected 'Hello Parts', got '{actual_content}'"
