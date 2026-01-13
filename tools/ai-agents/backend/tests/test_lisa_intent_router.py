"""
Intent Router Node 单元测试

测试 intent_router_node 根据不同意图生成正确的 plan。
"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from backend.agents.lisa.nodes.intent_router import (
    intent_router_node,
    format_messages_for_context,
    summarize_artifacts,
)
from backend.agents.lisa.state import get_initial_state


class TestIntentRouterPlanGeneration:
    """测试意图路由 Plan 动态生成"""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM fixture"""
        llm = MagicMock()
        llm.model = MagicMock()
        return llm
    
    @pytest.fixture
    def base_state(self):
        """基础状态"""
        state = get_initial_state()
        state["messages"] = [HumanMessage(content="测试消息")]
        return state
    
    def test_start_test_design_sets_workflow_type(self, mock_llm, base_state):
        """START_TEST_DESIGN 意图应设置 current_workflow 为 test_design"""
        mock_llm.model.invoke.return_value = MagicMock(
            content='{"intent": "START_TEST_DESIGN", "confidence": 0.9}'
        )
        
        result = intent_router_node(base_state, mock_llm)
        
        # 只验证 workflow type 被设置
        assert result["current_workflow"] == "test_design"
        # plan 不再由 intent_router 生成，由 workflow 节点通过 LLM 动态生成
    
    def test_start_requirement_review_sets_workflow_type(self, mock_llm, base_state):
        """START_REQUIREMENT_REVIEW 意图应设置 current_workflow 为 requirement_review"""
        mock_llm.model.invoke.return_value = MagicMock(
            content='{"intent": "START_REQUIREMENT_REVIEW", "confidence": 0.85}'
        )
        
        result = intent_router_node(base_state, mock_llm)
        
        # 只验证 workflow type 被设置
        assert result["current_workflow"] == "requirement_review"
        # plan 不再由 intent_router 生成，由 workflow 节点通过 LLM 动态生成
    
    def test_continue_preserves_existing_plan(self, mock_llm, base_state):
        """CONTINUE 意图应保持现有 Plan 不变"""
        # 设置初始 plan
        base_state["current_workflow"] = "requirement_review"
        base_state["plan"] = [
            {"id": "clarify", "name": "需求澄清", "status": "completed"},
            {"id": "analysis", "name": "评审分析", "status": "active"},
        ]
        base_state["current_stage_id"] = "analysis"
        
        mock_llm.model.invoke.return_value = MagicMock(
            content='{"intent": "CONTINUE", "confidence": 0.9}'
        )
        
        result = intent_router_node(base_state, mock_llm)
        
        # Plan 应保持不变
        assert result["current_workflow"] == "requirement_review"
        assert result["plan"] == base_state["plan"]
    
    def test_unclear_preserves_state(self, mock_llm, base_state):
        """UNCLEAR 意图应保持状态不变"""
        original_workflow = base_state.get("current_workflow")
        
        mock_llm.model.invoke.return_value = MagicMock(
            content='{"intent": "UNCLEAR", "confidence": 0.3}'
        )
        
        result = intent_router_node(base_state, mock_llm)
        
        # 状态应保持不变
        assert result.get("current_workflow") == original_workflow


class TestFormatMessagesForContext:
    """测试消息格式化"""
    
    def test_format_empty_messages(self):
        """空消息列表应返回占位符"""
        result = format_messages_for_context([])
        assert result == "(无历史消息)"
    
    def test_format_truncates_long_content(self):
        """长消息应被截断"""
        long_content = "a" * 300
        messages = [HumanMessage(content=long_content)]
        
        result = format_messages_for_context(messages)
        
        assert len(result) < len(long_content) + 50
        assert "..." in result


class TestSummarizeArtifacts:
    """测试产出物摘要"""
    
    def test_empty_artifacts(self):
        """空产出物应返回占位符"""
        result = summarize_artifacts({})
        assert result == "(无产出物)"
    
    def test_summarize_with_content(self):
        """有产出物时应返回摘要"""
        artifacts = {"test_key": "some content here"}
        
        result = summarize_artifacts(artifacts)
        
        assert "test_key" in result
