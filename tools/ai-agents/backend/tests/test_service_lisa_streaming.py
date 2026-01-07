
import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from backend.agents.service import LangchainAssistantService

@pytest.mark.asyncio
async def test_stream_lisa_message_deduplication():
    """
    Test that _stream_lisa_message correctly handles duplicate content 
    that might be emitted by LangGraph (e.g. incremental chunks mixed with full messages).
    """
    # 1. Setup Service and Mock Agent
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    # Mock _lisa_session_states
    service._lisa_session_states = {
        "test_session": {
            "messages": [],
            "current_workflow": "test_design",
            "workflow_stage": "clarify"
        }
    }
    
    # 2. Define Test Cases
    
    # Scenario:
    # 1. Incremental chunks: "H", "He", "Hel" ... "Hello"
    # 2. Duplicate full message event (simulating LangGraph behavior): "Hello"
    # 3. New content continues: "Hello W", "Hello Wo"
    
    target_node = "workflow_test_design"
    
    # Events format: (message, metadata)
    mock_events = [
        # 1. Incremental accumulation (normal streaming)
        (AIMessage(content="H"), {"langgraph_node": target_node}),
        (AIMessage(content="He"), {"langgraph_node": target_node}),
        (AIMessage(content="Hel"), {"langgraph_node": target_node}),
        (AIMessage(content="Hell"), {"langgraph_node": target_node}),
        (AIMessage(content="Hello"), {"langgraph_node": target_node}),
        
        # 2. THE BUG SCENARIO: Full message event arriving after streaming
        # This is exactly "Hello" again, which should be ignored
        (AIMessage(content="Hello"), {"langgraph_node": target_node}),
        
        # 3. New content starts (incremental relative to "Hello")
        (AIMessage(content="Hello W"), {"langgraph_node": target_node}),
        (AIMessage(content="Hello Wo"), {"langgraph_node": target_node}),
    ]
    
    # Setup mock astream to yield these events
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
            
    service.agent.astream = mock_astream
    
    # 3. Run and Collect Output
    collected_output = []
    async for chunk in service._stream_lisa_message("test_session", "User input"):
        collected_output.append(chunk)
        
    full_text = "".join(collected_output)
    
    # 4. Assertions
    
    # Expectation: "Hello Wo"
    # "H"
    # "He" -> yields "e"
    # "Hel" -> yields "l"
    # "Hell" -> yields "l"
    # "Hello" -> yields "o"
    # "Hello" (duplicate) -> yields nothing (deduplicated)
    # "Hello W" -> yields " W"
    # "Hello Wo" -> yields "o"
    
    assert full_text == "Hello Wo", f"Expected 'Hello Wo', got '{full_text}'"
    assert collected_output == ["H", "e", "l", "l", "o", " W", "o"]

@pytest.mark.asyncio
async def test_stream_lisa_message_duplicate_chunks():
    """Test protecting against rapid duplicate chunks if any"""
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    service._lisa_session_states = {"sess": {"messages": [], "current_workflow": None}}
    
    target_node = "workflow_test_design"
    
    # Scenario: Duplicate events with same content
    mock_events = [
        (AIMessage(content="A"), {"langgraph_node": target_node}),
        (AIMessage(content="AB"), {"langgraph_node": target_node}),
        (AIMessage(content="AB"), {"langgraph_node": target_node}), # Duplicate event
        (AIMessage(content="ABC"), {"langgraph_node": target_node}),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    collected_output = []
    async for chunk in service._stream_lisa_message("sess", "input"):
        collected_output.append(chunk)
        
    assert "".join(collected_output) == "ABC"
    assert collected_output == ["A", "B", "C"]
