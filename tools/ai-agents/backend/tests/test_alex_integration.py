"""
Alex ADK Agent Integration Tests

集成测试：验证 Alex ADK 智能体的完整工作流，包括 Tool Calling 和状态管理。
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from backend.agents.alex.agent import create_alex_agent, AlexAdkRunner, create_alex_graph
from backend.agents.alex.prompts import LISA_V5_2_INSTRUCTION, TOOL_USAGE_PROMPT
from backend.agents.alex.tools import ALEX_TOOLS, set_plan, update_stage, save_artifact
from backend.agents.alex.state_manager import AlexStateManager, AlexSessionState


class TestAlexTools:

    def test_tools_list_contains_three_tools(self):
        assert len(ALEX_TOOLS) == 3
        assert set_plan in ALEX_TOOLS
        assert update_stage in ALEX_TOOLS
        assert save_artifact in ALEX_TOOLS

    def test_set_plan_returns_confirmation(self):
        stages = [
            {"id": "clarify", "name": "需求澄清"},
            {"id": "strategy", "name": "策略制定"}
        ]
        result = set_plan(stages)
        assert "2 个阶段" in result

    def test_update_stage_returns_confirmation(self):
        result = update_stage("clarify", "completed")
        assert "clarify" in result
        assert "completed" in result

    def test_save_artifact_returns_confirmation(self):
        result = save_artifact("req_doc", "# Document Content")
        assert "req_doc" in result
        assert "字符" in result


class TestAlexStateManager:

    def test_get_state_creates_new_state(self):
        manager = AlexStateManager()
        state = manager.get_state("session-1")
        
        assert isinstance(state, AlexSessionState)
        assert state.plan == []
        assert state.current_stage_id == ""
        assert state.artifacts == {}

    def test_handle_set_plan_creates_plan(self):
        manager = AlexStateManager()
        stages = [
            {"id": "clarify", "name": "需求澄清", "artifact_key": "req_doc", "artifact_name": "需求分析文档"},
            {"id": "strategy", "name": "策略制定"}
        ]
        
        manager.handle_set_plan("session-1", stages)
        state = manager.get_state("session-1")
        
        assert len(state.plan) == 2
        assert state.plan[0]["status"] == "active"
        assert state.plan[1]["status"] == "pending"
        assert state.current_stage_id == "clarify"
        assert len(state.artifact_templates) == 1

    def test_handle_update_stage_completes_and_activates_next(self):
        manager = AlexStateManager()
        stages = [
            {"id": "clarify", "name": "需求澄清"},
            {"id": "strategy", "name": "策略制定"}
        ]
        manager.handle_set_plan("session-1", stages)
        
        manager.handle_update_stage("session-1", "clarify", "completed")
        state = manager.get_state("session-1")
        
        assert state.plan[0]["status"] == "completed"
        assert state.plan[1]["status"] == "active"
        assert state.current_stage_id == "strategy"

    def test_handle_save_artifact_stores_content(self):
        manager = AlexStateManager()
        manager.handle_set_plan("session-1", [{"id": "clarify", "name": "需求澄清", "artifact_key": "req_doc", "artifact_name": "文档"}])
        
        manager.handle_save_artifact("session-1", "req_doc", "# 完整内容")
        state = manager.get_state("session-1")
        
        assert "req_doc" in state.artifacts
        assert state.artifacts["req_doc"] == "# 完整内容"

    def test_get_progress_info_returns_correct_format(self):
        manager = AlexStateManager()
        stages = [
            {"id": "clarify", "name": "需求澄清", "artifact_key": "req_doc", "artifact_name": "需求分析文档"},
            {"id": "strategy", "name": "策略制定", "artifact_key": "strategy_doc", "artifact_name": "测试策略蓝图"}
        ]
        manager.handle_set_plan("session-1", stages)
        manager.handle_save_artifact("session-1", "req_doc", "# 内容")
        
        progress = manager.get_progress_info("session-1")
        
        assert progress is not None
        assert len(progress["stages"]) == 2
        assert progress["currentStageIndex"] == 0
        assert "正在需求澄清..." in progress["currentTask"]
        assert "req_doc" in progress["artifactProgress"]["completed"]
        assert progress["artifacts"]["req_doc"] == "# 内容"

    def test_get_progress_info_returns_none_without_plan(self):
        manager = AlexStateManager()
        progress = manager.get_progress_info("session-1")
        
        assert progress is None


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
            assert TOOL_USAGE_PROMPT in call_kwargs["instruction"]

    def test_create_alex_agent_uses_config_values(self):
        config = {
            "model_name": "custom-model",
            "base_url": "https://custom.api.com/v1",
            "api_key": "custom-key"
        }
        
        with patch('backend.agents.alex.agent.LiteLlm') as mock_litellm, \
             patch('backend.agents.alex.agent.LlmAgent'):
            
            create_alex_agent(config)
            
            mock_litellm.assert_called_once()
            call_kwargs = mock_litellm.call_args[1]
            assert call_kwargs["model"] == "openai/custom-model"
            assert call_kwargs["api_base"] == "https://custom.api.com/v1"
            assert call_kwargs["api_key"] == "custom-key"


class TestAlexAdkRunner:

    def test_create_alex_graph_returns_runner(self):
        config = {
            "model_name": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "test-key"
        }
        
        with patch('backend.agents.alex.agent.LlmAgent'), \
             patch('backend.agents.alex.agent.Runner'), \
             patch('backend.agents.alex.agent.InMemorySessionService'):
            
            result = create_alex_graph(config)
            
            assert isinstance(result, AlexAdkRunner)
            assert isinstance(result.state_manager, AlexStateManager)

    @pytest.mark.asyncio
    async def test_runner_creates_session_on_first_message(self):
        config = {
            "model_name": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "test-key"
        }
        
        with patch('backend.agents.alex.agent.LlmAgent'), \
             patch('backend.agents.alex.agent.Runner') as mock_runner_class, \
             patch('backend.agents.alex.agent.InMemorySessionService') as mock_session_class:
            
            mock_session_service = MagicMock()
            mock_session_service.get_session = AsyncMock(return_value=None)
            mock_session_service.create_session = AsyncMock()
            mock_session_class.return_value = mock_session_service
            
            async def mock_run_async(*args, **kwargs):
                return
                yield
            
            mock_runner = MagicMock()
            mock_runner.run_async = mock_run_async
            mock_runner_class.return_value = mock_runner
            
            runner = AlexAdkRunner(config)
            
            chunks = []
            async for chunk in runner.stream_message("session-1", "Hello"):
                chunks.append(chunk)
            
            mock_session_service.create_session.assert_called_once()


@pytest.mark.asyncio
class TestAlexStreamMessage:

    async def test_stream_message_yields_text_parts(self):
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
            
            mock_event = MagicMock()
            mock_part = MagicMock()
            mock_part.text = "Hello, I'm Alex"
            mock_part.function_call = None
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
            
            assert len(chunks) == 1
            assert chunks[0] == "Hello, I'm Alex"

    async def test_stream_message_handles_tool_calls(self):
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
            mock_function_call.name = "set_plan"
            mock_function_call.args = {
                "stages": [
                    {"id": "clarify", "name": "需求澄清", "artifact_key": "req_doc", "artifact_name": "需求分析文档"}
                ]
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
            
            state_events = [c for c in chunks if isinstance(c, dict) and c.get("type") == "state"]
            assert len(state_events) == 1
            assert "progress" in state_events[0]
            assert state_events[0]["progress"]["stages"][0]["id"] == "clarify"

    async def test_invoke_returns_full_response(self):
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
            
            mock_event1 = MagicMock()
            mock_part1 = MagicMock()
            mock_part1.text = "Hello, "
            mock_part1.function_call = None
            mock_event1.content = MagicMock()
            mock_event1.content.parts = [mock_part1]
            
            mock_event2 = MagicMock()
            mock_part2 = MagicMock()
            mock_part2.text = "I'm Alex"
            mock_part2.function_call = None
            mock_event2.content = MagicMock()
            mock_event2.content.parts = [mock_part2]
            
            async def mock_run_async(*args, **kwargs):
                yield mock_event1
                yield mock_event2
            
            mock_runner = MagicMock()
            mock_runner.run_async = mock_run_async
            mock_runner_class.return_value = mock_runner
            
            runner = AlexAdkRunner(config)
            runner._initialized_sessions.add("session-1")
            
            result = await runner.invoke("session-1", "Hello")
            
            assert result == "Hello, I'm Alex"


class TestPromptsModule:

    def test_instruction_is_non_empty_string(self):
        assert isinstance(LISA_V5_2_INSTRUCTION, str)
        assert len(LISA_V5_2_INSTRUCTION) > 1000

    def test_tool_usage_prompt_exists(self):
        assert isinstance(TOOL_USAGE_PROMPT, str)
        assert "set_plan" in TOOL_USAGE_PROMPT
        assert "update_stage" in TOOL_USAGE_PROMPT
        assert "save_artifact" in TOOL_USAGE_PROMPT
