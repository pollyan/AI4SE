
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
    async for chunk in service._stream_graph_message("test_session", "User input"):
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
    async for chunk in service._stream_graph_message("sess", "input"):
        collected_output.append(chunk)
        
    assert "".join(collected_output) == "ABC"
    assert collected_output == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_stream_lisa_message_parses_progress_xml():
    """
    Test that _stream_graph_message correctly parses XML progress update tags
    and updates current_stage_id in state.
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    # Setup state with default plan
    from backend.agents.lisa.state import get_initial_state
    initial_state = get_initial_state()
    initial_state["current_workflow"] = "test_design"
    service._lisa_session_states = {"test_session": initial_state}
    
    target_node = "workflow_test_design"
    
    # LLM response contains XML progress update tag
    response_with_xml = '好的，需求澄清已完成。<update_status stage="strategy">active</update_status>\n\n接下来我们进入策略制定阶段。'
    
    mock_events = [
        (AIMessage(content=response_with_xml), {"langgraph_node": target_node}),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    collected_output = []
    async for chunk in service._stream_graph_message("test_session", "确认需求"):
        # Skip state events (dicts)
        if isinstance(chunk, str):
            collected_output.append(chunk)
    
    # Verify state was updated
    updated_state = service._lisa_session_states["test_session"]
    assert updated_state["current_stage_id"] == "strategy", \
        f"Expected current_stage_id to be 'strategy', got '{updated_state.get('current_stage_id')}'"


@pytest.mark.asyncio
async def test_stream_lisa_message_cleans_xml_from_stored_message():
    """
    Test that XML tags are removed from the message stored in state.messages
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    from backend.agents.lisa.state import get_initial_state
    initial_state = get_initial_state()
    initial_state["current_workflow"] = "test_design"
    service._lisa_session_states = {"test_session": initial_state}
    
    target_node = "workflow_test_design"
    
    # Response with XML tag in the middle
    response_with_xml = '开始<update_status stage="cases">active</update_status>结束'
    
    mock_events = [
        (AIMessage(content=response_with_xml), {"langgraph_node": target_node}),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    async for _ in service._stream_graph_message("test_session", "test"):
        pass
    
    # Check the stored message content is cleaned
    updated_state = service._lisa_session_states["test_session"]
    last_message = updated_state["messages"][-1]
    
    assert "update_status" not in last_message.content, \
        f"XML tag should be removed from stored message, got: {last_message.content}"
    assert "开始" in last_message.content
    assert "结束" in last_message.content


@pytest.mark.asyncio
async def test_stream_lisa_message_emits_updated_progress_state():
    """
    Test that after parsing XML update, the final state event reflects the new progress.
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()

    from backend.agents.lisa.state import get_initial_state
    initial_state = get_initial_state()
    initial_state["current_workflow"] = "test_design"
    initial_state["current_stage_id"] = "clarify"
    # 添加plan字段，使get_progress_info能够返回进度信息
    initial_state["plan"] = [
        {"id": "clarify", "name": "需求澄清", "status": "pending"},
        {"id": "strategy", "name": "测试策略", "status": "pending"},
        {"id": "cases", "name": "用例设计", "status": "pending"},
        {"id": "delivery", "name": "文档交付", "status": "pending"},
    ]
    service._lisa_session_states = {"test_session": initial_state}
    
    target_node = "workflow_test_design"
    
    response_with_xml = '完成<update_status stage="strategy">active</update_status>'
    
    mock_events = [
        (AIMessage(content=response_with_xml), {"langgraph_node": target_node}),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    # Collect all events including state events
    state_events = []
    async for chunk in service._stream_graph_message("test_session", "test"):
        if isinstance(chunk, dict) and chunk.get("type") == "state":
            state_events.append(chunk)
    
    # Should have at least one state event at the end with updated progress
    assert len(state_events) >= 1, "Should emit at least one state event"
    
    final_state_event = state_events[-1]
    progress = final_state_event.get("progress", {})
    
    # The final progress should show "strategy" as active (index 1)
    assert progress.get("currentStageIndex") == 1, \
        f"Expected currentStageIndex to be 1 (strategy), got {progress.get('currentStageIndex')}"

