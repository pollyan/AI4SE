
"""
测试进度状态事件发送

验证进度事件只在流结束时发送（不在开始时发送）
"""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock
from langchain_core.messages import AIMessage
from backend.agents.service import LangchainAssistantService


@pytest.mark.asyncio
async def test_state_event_emitted_at_stream_end_only():
    """
    测试：state 事件在流结束时发送
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    target_node = "workflow_test_design"
    
    plan_json = json.dumps([
        {"id": "clarify", "name": "需求澄清", "status": "pending"},
        {"id": "strategy", "name": "测试策略", "status": "pending"},
        {"id": "cases", "name": "用例设计", "status": "pending"},
        {"id": "delivery", "name": "文档交付", "status": "pending"},
    ], ensure_ascii=False)
    
    response_with_plan = f'<plan>{plan_json}</plan>\n\nHello'
    
    async def mock_astream(*args, **kwargs):
        yield ("messages", (AIMessage(content=response_with_plan), {"langgraph_node": target_node}))
    
    service.agent.astream = mock_astream
    
    collected = []
    async for item in service._stream_graph_message("test_session", "用户输入"):
        collected.append(item)
    
    assert len(collected) >= 1, "应该有输出"
    
    state_events = [e for e in collected if isinstance(e, dict) and e.get("type") == "state"]
    assert len(state_events) >= 1, "应至少包含 1 个 state 事件"
    
    progress = state_events[-1]["progress"]
    assert "stages" in progress, "progress 应包含 stages"
    assert "currentStageIndex" in progress, "progress 应包含 currentStageIndex"
    assert "currentTask" in progress, "progress 应包含 currentTask"


@pytest.mark.asyncio
async def test_state_event_contains_correct_stages():
    """
    测试：state 事件中的阶段信息正确
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()

    target_node = "workflow_test_design"
    
    plan_json = json.dumps([
        {"id": "clarify", "name": "需求澄清", "status": "completed"},
        {"id": "strategy", "name": "测试策略", "status": "active"},
        {"id": "cases", "name": "用例设计", "status": "pending"},
        {"id": "delivery", "name": "文档交付", "status": "pending"},
    ], ensure_ascii=False)
    
    response_with_plan = f'<plan>{plan_json}</plan>\n\nOK'
    
    async def mock_astream(*args, **kwargs):
        yield ("messages", (AIMessage(content=response_with_plan), {"langgraph_node": target_node}))
    
    service.agent.astream = mock_astream
    
    collected = []
    async for item in service._stream_graph_message("test_session", "继续"):
        collected.append(item)
    
    state_events = [e for e in collected if isinstance(e, dict) and e.get("type") == "state"]
    assert len(state_events) >= 1, "应有至少一个 state 事件"
    
    progress = state_events[-1]["progress"]
    stages = progress["stages"]
    
    assert len(stages) == 4, "应有4个阶段"
    assert stages[0]["id"] == "clarify"
    assert stages[0]["status"] == "completed"
    assert stages[1]["id"] == "strategy"
    assert stages[1]["status"] == "active"
    assert stages[2]["status"] == "pending"
    
    assert progress["currentStageIndex"] == 1


@pytest.mark.asyncio
async def test_no_state_event_when_no_plan():
    """
    测试：当没有 plan 时不应发送 state 事件
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()

    target_node = "workflow_test_design"
    
    async def mock_astream(*args, **kwargs):
        yield ("messages", (AIMessage(content="Response"), {"langgraph_node": target_node}))
    
    service.agent.astream = mock_astream
    
    collected = []
    async for item in service._stream_graph_message("test_session", "输入"):
        collected.append(item)
    
    state_events = [e for e in collected if isinstance(e, dict) and e.get("type") == "state"]
    assert len(state_events) == 0, f"无 plan 时不应发送 state 事件，但发现 {len(state_events)} 个"


@pytest.mark.asyncio
async def test_no_state_event_for_alex_without_plan():
    """
    测试：Alex 智能体没有 plan 时不应发送 state 事件
    """
    service = LangchainAssistantService("alex")
    service.agent = MagicMock()
    
    async def mock_astream(*args, **kwargs):
        yield ("messages", (AIMessage(content="Hi"), {"langgraph_node": "model"}))
    
    service.agent.astream = mock_astream
    
    collected = []
    async for item in service._stream_graph_message("test_session", "hello"):
        collected.append(item)
    
    state_events = [e for e in collected if isinstance(e, dict) and e.get("type") == "state"]
    assert len(state_events) == 0, f"无 plan 时不应发送 state 事件，但发现 {len(state_events)} 个"
