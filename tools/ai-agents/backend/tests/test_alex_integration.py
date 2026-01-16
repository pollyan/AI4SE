"""
Alex ADK Agent Integration Tests

集成测试：验证 Alex ADK 智能体的完整工作流，包括 Tool Calling 和状态管理。
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from backend.agents.alex.agent import create_alex_agent, AlexAdkRunner, create_alex_graph
from backend.agents.alex.prompts import LISA_V5_2_INSTRUCTION
from backend.agents.alex.tools import ALEX_TOOLS, update_progress, update_artifact
from backend.agents.alex.state_manager import AlexStateManager, AlexSessionState


class TestAlexTools:

    def test_tools_list_contains_correct_tools(self):
        assert len(ALEX_TOOLS) == 2
        assert update_progress in ALEX_TOOLS
        assert update_artifact in ALEX_TOOLS


class TestAlexStateManager:

    def test_get_state_creates_new_state(self):
        manager = AlexStateManager()
        state = manager.get_state("session-1")
        
        assert isinstance(state, AlexSessionState)
        assert state.plan == []
        assert state.current_stage_id == ""
        assert state.artifacts == {}

    def test_handle_update_progress_updates_state(self):
        manager = AlexStateManager()
        stages = [
            {"id": "clarify", "name": "需求澄清", "status": "active", "artifact_key": "test_design_requirements"},
            {"id": "strategy", "name": "策略制定", "status": "pending"}
        ]
        
        manager.handle_update_progress("session-1", stages, "clarify", "Testing task")
        state = manager.get_state("session-1")
        
        assert len(state.plan) == 2
        assert state.current_stage_id == "clarify"
        assert state.current_task == "Testing task"
        # 验证自动模板初始化
        assert "test_design_requirements" in state.artifacts
        assert "1. 背景与目标" in state.artifacts["test_design_requirements"]

    def test_handle_update_artifact_updates_content(self):
        manager = AlexStateManager()
        # 先初始化状态
        manager.handle_update_progress("session-1", [], "clarify", "")
        
        # 模拟模板及其内容
        manager.get_state("session-1").artifacts["doc1"] = "## Section 1\n> Placeholder\n\n## Section 2"
        
        # 更新章节（这里需要 mock templates.py 的行为或确保 artifact key 在 templates 中存在）
        # 为了测试方便，我们假设 update_artifact 能处理不存在于 templates.py 的 key (fallback 到全量覆盖或 append)
        # 但新的 update_artifact 逻辑强依赖 templates.py。
        # 所以我们使用真实存在的 key "test_design_requirements"
        
        manager.handle_update_progress("session-1", [
            {"id": "clarify", "name": "Clarify", "artifact_key": "test_design_requirements"}
        ], "clarify", "")
        
        state = manager.get_state("session-1")
        original_content = state.artifacts["test_design_requirements"]
        
        manager.handle_update_artifact("session-1", "test_design_requirements", "background", "> New Background Content")
        
        updated_content = state.artifacts["test_design_requirements"]
        assert "> New Background Content" in updated_content
        assert "1. 背景与目标" in updated_content


class TestAlexAgentCreation:

    def test_create_alex_agent_includes_tools(self):
        config = {
            "model_name": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "test-key"
        }
        
        with patch('backend.agents.alex.agent.LlmAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent
            
            create_alex_agent(config)
            
            call_kwargs = mock_agent_class.call_args[1]
            assert call_kwargs["name"] == "alex"
            assert call_kwargs["tools"] == ALEX_TOOLS
            assert LISA_V5_2_INSTRUCTION in call_kwargs["instruction"]


class TestAlexAdkRunner:

    @pytest.mark.asyncio
    async def test_stream_message_handles_update_progress(self):
        config = {
            "model_name": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "test-key"
        }
        
        with patch('backend.agents.alex.agent.LlmAgent'), \
             patch('backend.agents.alex.agent.Runner') as mock_runner_class, \
             patch('backend.agents.alex.agent.InMemorySessionService') as mock_session_class:
            
            mock_session_service = MagicMock()
            mock_session_service.get_session = AsyncMock(return_value=MagicMock())
            mock_session_class.return_value = mock_session_service
            
            mock_function_call = MagicMock()
            mock_function_call.name = "update_progress"
            mock_function_call.args = {
                "stages": [{"id": "clarify", "name": "Clarify"}],
                "current_stage_id": "clarify",
                "current_task": "Task"
            }
            
            mock_event = MagicMock()
            mock_part = MagicMock()
            mock_part.text = None
            mock_part.function_call = mock_function_call
            mock_event.content = MagicMock()
            mock_event.content.parts = [mock_part]
            
            async def mock_run_async(*args, **kwargs):
                yield mock_event
            
            mock_runner = MagicMock()
            mock_runner.run_async = mock_run_async
            mock_runner_class.return_value = mock_runner
            
            runner = AlexAdkRunner(config)
            runner._initialized_sessions.add("session-1")
            
            chunks = []
            async for chunk in runner.stream_message("session-1", "Hello"):
                chunks.append(chunk)
            
            # 验证 tools 被调用导致状态更新
            state = runner.state_manager.get_state("session-1")
            assert state.current_stage_id == "clarify"
