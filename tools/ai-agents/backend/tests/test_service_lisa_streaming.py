
import pytest
import json
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from backend.agents.service import LangchainAssistantService

@pytest.mark.asyncio
async def test_stream_lisa_message_deduplication():
    """
    Test that _stream_lisa_message correctly handles duplicate content.
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    service._lisa_session_states = {
        "test_session": {
            "messages": [],
            "current_workflow": "test_design",
            "workflow_stage": "clarify"
        }
    }
    
    target_node = "workflow_test_design"
    
    mock_events = [
        ("messages", (AIMessage(content="H"), {"langgraph_node": target_node})),
        ("messages", (AIMessage(content="He"), {"langgraph_node": target_node})),
        ("messages", (AIMessage(content="Hel"), {"langgraph_node": target_node})),
        ("messages", (AIMessage(content="Hell"), {"langgraph_node": target_node})),
        ("messages", (AIMessage(content="Hello"), {"langgraph_node": target_node})),
        ("messages", (AIMessage(content="Hello"), {"langgraph_node": target_node})),
        ("messages", (AIMessage(content="Hello W"), {"langgraph_node": target_node})),
        ("messages", (AIMessage(content="Hello Wo"), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
            
    service.agent.astream = mock_astream
    
    collected_output = []
    async for chunk in service._stream_graph_message("test_session", "User input"):
        if isinstance(chunk, str):
            collected_output.append(chunk)
        
    full_text = "".join(collected_output)
    
    assert full_text == "Hello Wo", f"Expected 'Hello Wo', got '{full_text}'"
    assert collected_output == ["H", "e", "l", "l", "o", " W", "o"]

@pytest.mark.asyncio
async def test_stream_lisa_message_duplicate_chunks():
    """Test protecting against rapid duplicate chunks"""
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    service._lisa_session_states = {"sess": {"messages": [], "current_workflow": None}}
    
    target_node = "workflow_test_design"
    
    mock_events = [
        ("messages", (AIMessage(content="A"), {"langgraph_node": target_node})),
        ("messages", (AIMessage(content="AB"), {"langgraph_node": target_node})),
        ("messages", (AIMessage(content="AB"), {"langgraph_node": target_node})),
        ("messages", (AIMessage(content="ABC"), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    collected_output = []
    async for chunk in service._stream_graph_message("sess", "input"):
        if isinstance(chunk, str):
            collected_output.append(chunk)
        
    assert "".join(collected_output) == "ABC"
    assert collected_output == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_stream_lisa_message_parses_progress_xml():
    """
    Test parsing XML plan tag (Full Snapshot Mode).
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    from backend.agents.lisa.state import get_initial_state
    initial_state = get_initial_state()
    initial_state["current_workflow"] = "test_design"
    service._lisa_session_states = {"test_session": initial_state}
    
    target_node = "workflow_test_design"
    
    plan_json = json.dumps([
        {"id": "clarify", "name": "需求澄清", "status": "completed"},
        {"id": "strategy", "name": "策略制定", "status": "active"}
    ], ensure_ascii=False)
    
    response_with_xml = f'<plan>{plan_json}</plan>\n\n接下来我们进入策略制定阶段。'
    
    mock_events = [
        ("messages", (AIMessage(content=response_with_xml), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    collected_output = []
    async for chunk in service._stream_graph_message("test_session", "确认需求"):
        if isinstance(chunk, str):
            collected_output.append(chunk)
    
    updated_state = service._lisa_session_states["test_session"]
    
    assert updated_state["plan"] is not None
    assert len(updated_state["plan"]) == 2
    assert updated_state["plan"][1]["id"] == "strategy"
    assert updated_state["plan"][1]["status"] == "active"
    
    assert updated_state["current_stage_id"] == "strategy"


@pytest.mark.asyncio
async def test_stream_lisa_message_cleans_xml_from_stored_message():
    """
    Test XML tags removal from stored message.
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    from backend.agents.lisa.state import get_initial_state
    initial_state = get_initial_state()
    initial_state["current_workflow"] = "test_design"
    service._lisa_session_states = {"test_session": initial_state}
    
    target_node = "workflow_test_design"
    
    response_with_xml = '开始<plan>[{"id":"a","status":"active"}]</plan>结束'
    
    mock_events = [
        ("messages", (AIMessage(content=response_with_xml), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    async for _ in service._stream_graph_message("test_session", "test"):
        pass
    
    updated_state = service._lisa_session_states["test_session"]
    last_message = updated_state["messages"][-1]
    
    assert "plan" not in last_message.content
    assert "开始" in last_message.content
    assert "结束" in last_message.content


@pytest.mark.asyncio
async def test_stream_lisa_message_emits_updated_progress_state():
    """
    Test that state event reflects new progress.
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()

    from backend.agents.lisa.state import get_initial_state
    initial_state = get_initial_state()
    initial_state["current_workflow"] = "test_design"
    
    initial_state["plan"] = [
        {"id": "clarify", "name": "需求澄清", "status": "active"},
        {"id": "strategy", "name": "测试策略", "status": "pending"},
    ]
    initial_state["current_stage_id"] = "clarify"
    
    service._lisa_session_states = {"test_session": initial_state}
    
    target_node = "workflow_test_design"
    
    new_plan = json.dumps([
        {"id": "clarify", "name": "需求澄清", "status": "completed"},
        {"id": "strategy", "name": "测试策略", "status": "active"},
    ], ensure_ascii=False)
    
    response_with_xml = f'<plan>{new_plan}</plan>完成'
    
    mock_events = [
        ("messages", (AIMessage(content=response_with_xml), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    state_events = []
    async for chunk in service._stream_graph_message("test_session", "test"):
        if isinstance(chunk, dict) and chunk.get("type") == "state":
            state_events.append(chunk)
    
    assert len(state_events) >= 1
    
    final_state_event = state_events[-1]
    progress = final_state_event.get("progress", {})
    
    assert progress.get("currentStageIndex") == 1
