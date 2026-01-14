
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
async def test_stream_lisa_message_parses_progress_json():
    """
    Test parsing JSON structured output.
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    target_node = "workflow_test_design"
    
    json_block = '''```json
{
  "plan": [
    {"id": "clarify", "name": "需求澄清", "status": "completed"},
    {"id": "strategy", "name": "策略制定", "status": "active"}
  ],
  "current_stage_id": "strategy",
  "artifacts": [],
  "message": "接下来我们进入策略制定阶段。"
}
```'''
    
    mock_events = [
        ("messages", (AIMessage(content=json_block), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    state_events = []
    async for chunk in service._stream_graph_message("test_session", "确认需求"):
        if isinstance(chunk, dict) and chunk.get("type") == "state":
            state_events.append(chunk)
    
    assert len(state_events) >= 1, "应至少有一个 state 事件"
    
    final_state_event = state_events[-1]
    progress = final_state_event.get("progress", {})
    stages = progress.get("stages", [])
    
    assert len(stages) == 2, f"应有 2 个阶段，实际: {len(stages)}"
    assert stages[1]["id"] == "strategy"
    assert stages[1]["status"] == "active"
    assert progress.get("currentStageIndex") == 1


@pytest.mark.asyncio
async def test_stream_lisa_message_cleans_json_from_stored_message():
    """
    Test JSON block removal from stored message.
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    target_node = "workflow_test_design"
    
    response_with_json = '''开始
```json
{"plan": [{"id":"a","status":"active"}], "current_stage_id": "a", "artifacts": [], "message": "内容"}
```
结束'''
    
    mock_events = [
        ("messages", (AIMessage(content=response_with_json), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    collected_text = []
    async for chunk in service._stream_graph_message("test_session", "test"):
        if isinstance(chunk, str):
            collected_text.append(chunk)
    
    final_text = "".join(collected_text)
    
    assert "```json" not in final_text, f"JSON 块应被移除，实际: {final_text}"
    assert "开始" in final_text
    assert "结束" in final_text


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
    
    new_plan = '''```json
{
  "plan": [
    {"id": "clarify", "name": "需求澄清", "status": "completed"},
    {"id": "strategy", "name": "测试策略", "status": "active"}
  ],
  "current_stage_id": "strategy",
  "artifacts": [],
  "message": "完成"
}
```'''
    
    mock_events = [
        ("messages", (AIMessage(content=new_plan), {"langgraph_node": target_node})),
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
