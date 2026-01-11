"""
测试进度状态事件发送

验证进度事件只在流结束时发送（不在开始时发送）
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from langchain_core.messages import AIMessage
from backend.agents.service import LangchainAssistantService


@pytest.mark.asyncio
async def test_state_event_emitted_at_stream_end_only():
    """
    测试：state 事件只在流结束后发送（不在开始时发送）
    
    这是新的行为：进度事件只在 LLM 响应完成后发送，
    避免在用户还没看到响应时就显示可能过时的进度。
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    # 初始化 Lisa 状态
    service._lisa_session_states = {
        "test_session": {
            "messages": [],
            "current_workflow": "test_design",
            "current_stage_id": "clarify",
            "workflow_stage": "clarify",
            "plan": [
                {"id": "clarify", "name": "需求澄清", "status": "pending"},
                {"id": "strategy", "name": "测试策略", "status": "pending"},
                {"id": "cases", "name": "用例设计", "status": "pending"},
                {"id": "delivery", "name": "文档交付", "status": "pending"},
            ],
            "artifacts": {},
            "pending_clarifications": [],
            "consensus_items": [],
        }
    }
    
    # Mock astream 返回一个简单的 AI 消息
    async def mock_astream(*args, **kwargs):
        yield (AIMessage(content="Hello"), {"langgraph_node": "workflow_test_design"})
    
    service.agent.astream = mock_astream
    
    # 收集所有输出
    collected = []
    async for item in service._stream_graph_message("test_session", "用户输入"):
        collected.append(item)
    
    # 断言：第一个输出应该是文本（不是 state 事件）
    assert len(collected) >= 1, "应该有输出"
    
    first_item = collected[0]
    assert isinstance(first_item, str), f"第一个输出应是文本，实际是 {type(first_item)}"
    
    # state 事件应该在最后
    state_events = [e for e in collected if isinstance(e, dict) and e.get("type") == "state"]
    assert len(state_events) == 1, f"应有恰好1个 state 事件（结束时），实际有 {len(state_events)}"
    
    # 验证 state 事件结构
    progress = state_events[0]["progress"]
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

    service._lisa_session_states = {
        "test_session": {
            "messages": [],
            "current_workflow": "test_design",
            "current_stage_id": "strategy",  # 当前在第二阶段
            "workflow_stage": "strategy",
            "plan": [
                {"id": "clarify", "name": "需求澄清", "status": "pending"},
                {"id": "strategy", "name": "测试策略", "status": "pending"},
                {"id": "cases", "name": "用例设计", "status": "pending"},
                {"id": "delivery", "name": "文档交付", "status": "pending"},
            ],
            "artifacts": {"test_design_requirements": "some content"},
            "pending_clarifications": [],
            "consensus_items": [],
        }
    }
    
    async def mock_astream(*args, **kwargs):
        yield (AIMessage(content="OK"), {"langgraph_node": "workflow_test_design"})
    
    service.agent.astream = mock_astream
    
    collected = []
    async for item in service._stream_graph_message("test_session", "继续"):
        collected.append(item)
    
    # 找到 state 事件
    state_events = [e for e in collected if isinstance(e, dict) and e.get("type") == "state"]
    assert len(state_events) >= 1, "应有至少一个 state 事件"
    
    progress = state_events[0]["progress"]
    stages = progress["stages"]
    
    # 验证阶段结构
    assert len(stages) == 4, "应有4个阶段"
    assert stages[0]["id"] == "clarify"
    assert stages[0]["status"] == "completed"  # 第一阶段已完成
    assert stages[1]["id"] == "strategy"
    assert stages[1]["status"] == "active"  # 当前阶段
    assert stages[2]["status"] == "pending"
    
    # 验证当前阶段索引
    assert progress["currentStageIndex"] == 1  # strategy 是第二个（索引1）


@pytest.mark.asyncio
async def test_no_state_event_when_no_plan():
    """
    测试：当没有 plan 时不应发送 state 事件
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()

    service._lisa_session_states = {
        "test_session": {
            "messages": [],
            "current_workflow": "test_design",
            "current_stage_id": "clarify",
            "workflow_stage": "clarify",
            "plan": [],  # 空 plan
            "artifacts": {},
            "pending_clarifications": [],
            "consensus_items": [],
        }
    }
    
    async def mock_astream(*args, **kwargs):
        yield (AIMessage(content="Response"), {"langgraph_node": "workflow_test_design"})
    
    service.agent.astream = mock_astream
    
    collected = []
    async for item in service._stream_graph_message("test_session", "输入"):
        collected.append(item)
    
    # 没有 plan 时不应有 state 事件
    state_events = [e for e in collected if isinstance(e, dict) and e.get("type") == "state"]
    assert len(state_events) == 0, f"无 plan 时不应发送 state 事件，但发现 {len(state_events)} 个"


@pytest.mark.asyncio
async def test_no_state_event_for_alex_without_plan():
    """
    测试：Alex 智能体没有 plan 时不应发送 state 事件
    """
    service = LangchainAssistantService("alex")
    service.agent = MagicMock()
    
    # Alex 使用不同的初始状态（无 plan）
    service._lisa_session_states = {
        "test_session": {
            "messages": [],
            "plan": [],  # 空 plan
        }
    }
    
    async def mock_astream(*args, **kwargs):
        yield (AIMessage(content="Hi"), {"langgraph_node": "model"})
    
    service.agent.astream = mock_astream
    
    collected = []
    async for item in service._stream_graph_message("test_session", "hello"):
        collected.append(item)
    
    # 没有 plan 时不应有 state 事件
    state_events = [e for e in collected if isinstance(e, dict) and e.get("type") == "state"]
    assert len(state_events) == 0, f"无 plan 时不应发送 state 事件，但发现 {len(state_events)} 个"

