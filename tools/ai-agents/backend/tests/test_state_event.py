"""
测试进度状态事件发送

TDD: 红阶段 - 这些测试应该失败，因为功能尚未实现
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from langchain_core.messages import AIMessage
from backend.agents.service import LangchainAssistantService


@pytest.mark.asyncio
async def test_state_event_emitted_at_stream_start():
    """
    测试：流开始时应发送初始 state 事件
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    # 初始化 Lisa 状态
    service._lisa_session_states = {
        "test_session": {
            "messages": [],
            "current_workflow": "test_design",
            "workflow_stage": "clarify",
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
    
    # 断言：第一个输出应该是 state 事件（字典类型）
    assert len(collected) >= 1, "应该有输出"
    
    first_item = collected[0]
    assert isinstance(first_item, dict), f"第一个输出应是字典（state事件），实际是 {type(first_item)}"
    assert first_item.get("type") == "state", f"第一个事件类型应为 'state'，实际是 {first_item}"
    assert "progress" in first_item, "state 事件应包含 progress 字段"
    
    progress = first_item["progress"]
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
            "workflow_stage": "strategy",  # 第二阶段
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
async def test_state_event_emitted_at_stream_end():
    """
    测试：流结束后应发送最终 state 事件
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    service._lisa_session_states = {
        "test_session": {
            "messages": [],
            "current_workflow": "test_design",
            "workflow_stage": "clarify",
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
    
    # 找到所有 state 事件
    state_events = [e for e in collected if isinstance(e, dict) and e.get("type") == "state"]
    
    # 应该有开始和结束两个 state 事件
    assert len(state_events) >= 2, f"应有至少2个 state 事件（开始和结束），实际有 {len(state_events)}"


@pytest.mark.asyncio
async def test_no_state_event_for_alex():
    """
    测试：Alex 智能体不应发送 state 事件
    """
    service = LangchainAssistantService("alex")
    service.agent = MagicMock()
    
    # Alex 使用不同的初始状态
    service._lisa_session_states = {
        "test_session": {
            "messages": [],
        }
    }
    
    async def mock_astream(*args, **kwargs):
        yield (AIMessage(content="Hi"), {"langgraph_node": "model"})
    
    service.agent.astream = mock_astream
    
    collected = []
    async for item in service._stream_graph_message("test_session", "hello"):
        collected.append(item)
    
    # Alex 不应有 state 事件
    state_events = [e for e in collected if isinstance(e, dict) and e.get("type") == "state"]
    assert len(state_events) == 0, f"Alex 不应发送 state 事件，但发现 {len(state_events)} 个"
