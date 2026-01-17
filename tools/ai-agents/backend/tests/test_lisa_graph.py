"""
Lisa Graph 单元测试

测试 LangGraph 图编译和基础路由逻辑。
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from backend.agents.lisa.state import LisaState, get_initial_state
from backend.agents.lisa.graph import get_graph_initial_state


class TestGetGraphInitialState:
    """测试图初始状态获取"""
    
    def test_returns_valid_lisa_state(self):
        """应返回有效的 LisaState"""
        state = get_graph_initial_state()
        
        assert "messages" in state
        assert "current_workflow" in state
        assert "workflow_stage" in state
        assert "artifacts" in state
    
    def test_initial_state_is_empty(self):
        """初始状态应为空"""
        state = get_graph_initial_state()
        
        assert state["messages"] == []
        assert state["current_workflow"] is None
        assert state["artifacts"] == {}


class TestIntentRouterNode:
    """测试意图路由节点"""
    
    def test_format_messages_for_context(self):
        """测试消息格式化函数"""
        from backend.agents.lisa.nodes.intent_router import format_messages_for_context
        
        messages = [
            HumanMessage(content="测试消息1"),
            AIMessage(content="回复消息1"),
        ]
        
        result = format_messages_for_context(messages)
        
        assert "用户" in result
        assert "Lisa" in result
        assert "测试消息1" in result
    
    def test_format_messages_truncates_long_content(self):
        """测试长消息截断"""
        from backend.agents.lisa.nodes.intent_router import format_messages_for_context
        
        long_content = "a" * 300
        messages = [HumanMessage(content=long_content)]
        
        result = format_messages_for_context(messages)
        
        assert "..." in result
        assert len(result) < 300
    
    def test_summarize_artifacts_empty(self):
        """测试空产出物摘要"""
        from backend.agents.lisa.nodes.intent_router import summarize_artifacts
        
        result = summarize_artifacts({})
        
        assert result == "(无产出物)"
    
    def test_summarize_artifacts_with_content(self):
        """测试有内容的产出物摘要"""
        from backend.agents.lisa.nodes.intent_router import summarize_artifacts
        
        artifacts = {
            "test_design_requirements": "内容内容内容",
        }
        
        result = summarize_artifacts(artifacts)
        
        assert "test_design_requirements" in result
        assert "字符" in result


class TestClarifyIntentNode:
    """测试意图澄清节点"""
    
    def test_adds_clarify_message(self):
        """应添加澄清消息"""
        from backend.agents.lisa.nodes.clarify_intent import clarify_intent_node
        
        state = get_initial_state()
        mock_llm = Mock()
        
        result = clarify_intent_node(state, mock_llm)
        
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert "Lisa Song" in result["messages"][0].content
    
    def test_preserves_existing_messages(self):
        """应保留现有消息"""
        from backend.agents.lisa.nodes.clarify_intent import clarify_intent_node
        
        state = get_initial_state()
        state["messages"] = [HumanMessage(content="原有消息")]
        mock_llm = Mock()
        
        result = clarify_intent_node(state, mock_llm)
        
        assert len(result["messages"]) == 2
        assert result["messages"][0].content == "原有消息"


class TestWorkflowTestDesignNode:
    """测试测试设计工作流节点"""
    
    def test_determine_stage_empty(self):
        """无产出物时应从 clarify 开始"""
        from backend.agents.lisa.nodes.workflow_test_design import determine_stage

        state = get_initial_state()

        result = determine_stage(state, "test_design")

        assert result == "clarify"
    
    def test_determine_stage_with_requirements(self):
        """有需求文档时应进入 strategy"""
        from backend.agents.lisa.nodes.workflow_test_design import determine_stage
        from backend.agents.lisa.state import ArtifactKeys

        state = get_initial_state()
        state["artifacts"][ArtifactKeys.TEST_DESIGN_REQUIREMENTS] = "需求内容"

        result = determine_stage(state, "test_design")

        assert result == "strategy"
    
    def test_determine_stage_with_strategy(self):
        """有策略文档时应进入 cases"""
        from backend.agents.lisa.nodes.workflow_test_design import determine_stage
        from backend.agents.lisa.state import ArtifactKeys

        state = get_initial_state()
        state["artifacts"][ArtifactKeys.TEST_DESIGN_STRATEGY] = "策略内容"

        result = determine_stage(state, "test_design")

        # 有 strategy 时进入 cases 阶段
        assert result == "cases"
    
    def test_get_artifacts_summary_empty(self):
        """空产出物摘要"""
        from backend.agents.shared.artifact_summary import get_artifacts_summary
        
        result = get_artifacts_summary({})
        
        assert result == "(无)"


class TestGraphCompilation:
    """测试图编译（需要 Mock LLM）"""
    
    @patch('backend.agents.lisa.graph.create_llm_from_config')
    def test_graph_can_be_created(self, mock_create_llm):
        """图应能正常创建"""
        from backend.agents.lisa.graph import create_lisa_graph
        
        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.model = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        config = {
            "model_name": "test-model",
            "base_url": "http://test",
            "api_key": "test-key",
        }
        
        graph = create_lisa_graph(config)
        
        # 验证图已编译
        assert graph is not None
        # 验证图有预期的方法
        assert hasattr(graph, 'invoke')
        assert hasattr(graph, 'stream')
