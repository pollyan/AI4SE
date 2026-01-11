"""
Alex Integration Tests

集成测试：验证Alex智能体的完整工作流。
"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from backend.agents.alex.graph import create_alex_graph
from backend.agents.alex.state import get_initial_state, ArtifactKeys


@pytest.mark.asyncio
class TestAlexFullWorkflow:
    """测试Alex完整工作流"""

    @patch('backend.agents.alex.graph.create_llm_from_config')
    async def test_product_design_workflow_from_start(self, mock_create_llm):
        """
        Integration test for Alex's product design workflow.

        Simulates:
        1. User starts conversation
        2. Alex generates elevator pitch artifact
        3. Workflow progresses through stages
        """

        # 1. Setup Mock LLM
        mock_llm = MagicMock()

        # Define scenario responses
        def side_effect_invoke(messages, **kwargs):
            # Extract system prompt for context
            system_content = ""
            for msg in messages:
                if hasattr(msg, 'content') and isinstance(msg.content, str):
                    system_content += msg.content

            # Check current stage from prompt - check both system and all messages
            if "elevator" in system_content:
                # Generate elevator pitch artifact
                return AIMessage(content='''
好的，让我为您创建电梯演讲。

```markdown
# 电梯演讲

**产品**: AI智能测试平台

**价值主张**: 帮助企业在10分钟内建立完整的测试体系

**目标市场**: 中小型软件企业
```''')
            elif "persona" in system_content:
                return AIMessage(content="生成用户画像中...")
            else:
                return AIMessage(content="继续处理")

        mock_llm.model.invoke.side_effect = side_effect_invoke

        # 2. Patch create_llm
        with patch('backend.agents.alex.graph.create_llm_from_config', return_value=mock_llm):

            # 3. Initialize Graph
            config = {"model_name": "mock-gpt", "base_url": "", "api_key": ""}
            graph = create_alex_graph(config)

            # 4. Start conversation
            state = get_initial_state()
            state["messages"] = [HumanMessage(content="帮我设计一个AI测试平台")]
            state["plan"] = [
                {"id": "elevator", "name": "电梯演讲", "status": "pending"},
                {"id": "persona", "name": "用户画像", "status": "pending"},
            ]
            state["current_stage_id"] = "elevator"

            # Run graph
            result = await graph.ainvoke(state)

            # Assertions
            assert len(result["messages"]) >= 2  # User message + AI response
            last_message = result["messages"][-1]
            assert isinstance(last_message, AIMessage)

            # Should have generated artifact
            assert ArtifactKeys.PRODUCT_ELEVATOR in result["artifacts"]
            elevator_content = result["artifacts"][ArtifactKeys.PRODUCT_ELEVATOR]
            assert "电梯演讲" in elevator_content
            assert "AI智能测试平台" in elevator_content

    @patch('backend.agents.alex.graph.create_llm_from_config')
    async def test_multi_stage_progression(self, mock_create_llm):
        """测试多阶段推进"""
        mock_llm = MagicMock()

        # Mock responses for different stages
        call_count = {"count": 0}

        def side_effect_invoke(messages, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                # First call: elevator stage
                return AIMessage(content='''```markdown
# 电梯演讲
测试平台
```''')
            elif call_count["count"] == 2:
                # Second call: persona stage
                return AIMessage(content='''```markdown
# 用户画像
开发者
```''')
            else:
                return AIMessage(content="完成")

        mock_llm.model.invoke.side_effect = side_effect_invoke

        with patch('backend.agents.alex.graph.create_llm_from_config', return_value=mock_llm):
            config = {"model_name": "mock", "base_url": "", "api_key": ""}
            graph = create_alex_graph(config)

            # First turn: elevator stage
            state = get_initial_state()
            state["messages"] = [HumanMessage(content="开始产品设计")]
            state["plan"] = [
                {"id": "elevator", "name": "电梯演讲", "status": "pending"},
                {"id": "persona", "name": "用户画像", "status": "pending"},
            ]
            state["current_stage_id"] = "elevator"

            result1 = await graph.ainvoke(state)

            # Should have elevator artifact
            assert ArtifactKeys.PRODUCT_ELEVATOR in result1["artifacts"]

            # Second turn: persona stage
            state2 = result1
            state2["messages"].append(HumanMessage(content="继续"))
            state2["current_stage_id"] = "persona"

            result2 = await graph.ainvoke(state2)

            # Should have both artifacts
            assert ArtifactKeys.PRODUCT_ELEVATOR in result2["artifacts"]
            assert ArtifactKeys.PRODUCT_PERSONA in result2["artifacts"]


@pytest.mark.asyncio
class TestAlexErrorHandling:
    """测试Alex错误处理"""

    @patch('backend.agents.alex.graph.create_llm_from_config')
    async def test_handles_llm_failure(self, mock_create_llm):
        """应能处理LLM调用失败"""
        mock_llm = MagicMock()
        mock_llm.model.invoke.side_effect = Exception("LLM服务不可用")

        with patch('backend.agents.alex.graph.create_llm_from_config', return_value=mock_llm):
            config = {"model_name": "mock", "base_url": "", "api_key": ""}
            graph = create_alex_graph(config)

            state = get_initial_state()
            state["messages"] = [HumanMessage(content="测试消息")]

            # Should not raise exception, but return error message
            result = await graph.ainvoke(state)

            assert len(result["messages"]) >= 2
            last_message = result["messages"][-1]
            assert isinstance(last_message, AIMessage)
            assert "抱歉" in last_message.content or "问题" in last_message.content


@pytest.mark.asyncio
class TestAlexStateManagement:
    """测试Alex状态管理"""

    @patch('backend.agents.alex.graph.create_llm_from_config')
    async def test_preserves_across_turns(self, mock_create_llm):
        """状态应在多轮对话中保持"""
        mock_llm = MagicMock()

        mock_response = AIMessage(content='''```markdown
# 内容
产出物
```''')
        mock_llm.model.invoke.return_value = mock_response

        with patch('backend.agents.alex.graph.create_llm_from_config', return_value=mock_llm):
            config = {"model_name": "mock", "base_url": "", "api_key": ""}
            graph = create_alex_graph(config)

            # First turn
            state = get_initial_state()
            state["messages"] = [HumanMessage(content="开始")]
            state["plan"] = [{"id": "elevator", "name": "电梯演讲", "status": "pending"}]
            state["current_stage_id"] = "elevator"

            result1 = await graph.ainvoke(state)

            # Second turn: state should be preserved
            state2 = result1
            state2["messages"].append(HumanMessage(content="继续"))

            result2 = await graph.ainvoke(state2)

            # Artifacts from first turn should still be there
            assert ArtifactKeys.PRODUCT_ELEVATOR in result2["artifacts"]

    @patch('backend.agents.alex.graph.create_llm_from_config')
    async def test_workflow_type_persistence(self, mock_create_llm):
        """工作流类型应保持不变"""
        mock_llm = MagicMock()
        mock_llm.model.invoke.return_value = AIMessage(content="回复")

        with patch('backend.agents.alex.graph.create_llm_from_config', return_value=mock_llm):
            config = {"model_name": "mock", "base_url": "", "api_key": ""}
            graph = create_alex_graph(config)

            state = get_initial_state()
            state["messages"] = [HumanMessage(content="测试")]

            result = await graph.ainvoke(state)

            # Should set and maintain workflow type
            assert result["current_workflow"] == "product_design"
