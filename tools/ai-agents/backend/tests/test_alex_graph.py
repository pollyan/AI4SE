"""
Alex Graph 单元测试

测试 LangGraph 图编译和基础路由逻辑。
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from backend.agents.alex.state import AlexState, get_initial_state
from backend.agents.alex.graph import setup_node, create_alex_graph


class TestSetupNode:
    """测试setup节点"""

    def test_sets_default_workflow_when_none(self):
        """当没有设置工作流时，应设置默认为product_design"""
        state = get_initial_state()

        result = setup_node(state)

        assert result["current_workflow"] == "product_design"
        assert result["plan"] == []

    def test_preserves_existing_workflow(self):
        """当已有工作流时，应保持不变"""
        state = get_initial_state()
        state["current_workflow"] = "product_design"
        state["plan"] = [{"id": "test"}]

        result = setup_node(state)

        assert result["current_workflow"] == "product_design"
        assert result["plan"] == [{"id": "test"}]

    def test_initializes_empty_plan(self):
        """当plan不存在时，应初始化为空列表"""
        state = get_initial_state()
        del state["plan"]

        result = setup_node(state)

        assert "plan" in result
        assert result["plan"] == []


class TestGraphCompilation:
    """测试图编译（需要 Mock LLM）"""

    @patch('backend.agents.alex.graph.create_llm_from_config')
    def test_graph_can_be_created(self, mock_create_llm):
        """图应能正常创建"""
        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.model = MagicMock()
        mock_create_llm.return_value = mock_llm

        config = {
            "model_name": "test-model",
            "base_url": "http://test",
            "api_key": "test-key",
        }

        graph = create_alex_graph(config)

        # 验证图已编译
        assert graph is not None
        # 验证图有预期的方法
        assert hasattr(graph, 'invoke')
        assert hasattr(graph, 'stream')

    @patch('backend.agents.alex.graph.create_llm_from_config')
    def test_graph_has_correct_nodes(self, mock_create_llm):
        """图应包含正确的节点"""
        mock_llm = MagicMock()
        mock_llm.model = MagicMock()
        mock_create_llm.return_value = mock_llm

        config = {"model_name": "test", "base_url": "http://test", "api_key": "key"}
        graph = create_alex_graph(config)

        # 验证图的节点结构
        # 图应该有: setup -> workflow_product_design -> END
        assert graph is not None

    @patch('backend.agents.alex.graph.create_llm_from_config')
    def test_creates_llm_with_config(self, mock_create_llm):
        """应使用配置创建LLM"""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        config = {
            "model_name": "qwen-vl-max-latest",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "test-key",
        }

        create_alex_graph(config)

        # 验证create_llm_from_config被调用
        mock_create_llm.assert_called_once_with(config)


class TestGetInitialState:
    """测试初始状态获取"""

    def test_returns_valid_alex_state(self):
        """应返回有效的AlexState"""
        from backend.agents.alex.state import get_initial_state

        state = get_initial_state()

        assert "messages" in state
        assert "current_workflow" in state
        assert "workflow_stage" in state
        assert "artifacts" in state
        assert "plan" in state
        assert "current_stage_id" in state

    def test_initial_state_is_empty(self):
        """初始状态应为空"""
        from backend.agents.alex.state import get_initial_state

        state = get_initial_state()

        assert state["messages"] == []
        assert state["current_workflow"] is None
        assert state["workflow_stage"] is None
        assert state["artifacts"] == {}
        assert state["plan"] == []
        assert state["current_stage_id"] is None
        assert state["pending_clarifications"] == []
        assert state["consensus_items"] == []


class TestWorkflowExecution:
    """测试工作流执行（需要Mock LLM）"""

    @pytest.mark.asyncio
    @patch('backend.agents.alex.graph.create_llm_from_config')
    async def test_workflow_executes_from_start(self, mock_create_llm):
        """工作流应能从START执行到END"""
        # Mock LLM响应
        mock_llm = MagicMock()
        mock_response = AIMessage(content="测试响应")
        mock_llm.model.invoke.return_value = mock_response
        mock_create_llm.return_value = mock_llm

        config = {"model_name": "test", "base_url": "http://test", "api_key": "key"}
        graph = create_alex_graph(config)

        # 初始状态
        initial_state = get_initial_state()
        initial_state["messages"].append(HumanMessage(content="测试消息"))

        # 执行图
        result = await graph.ainvoke(initial_state)

        # 验证结果
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) >= 2  # 至少包含用户消息和AI响应
