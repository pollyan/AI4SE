"""
Intent Router Node 单元测试

测试 intent_router_node 使用 with_structured_output 进行意图识别。
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
from backend.agents.lisa.schemas import IntentResult


class TestIntentRouterWithStructuredOutput:
    """测试意图路由使用 with_structured_output"""
    
    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.model = MagicMock()
        return llm
    
    @pytest.fixture
    def base_state(self):
        state = get_initial_state()
        state["messages"] = [HumanMessage(content="测试消息")]
        return state
    
    def test_uses_with_structured_output(self, mock_llm, base_state):
        """应使用 with_structured_output 而非手动 JSON 解析"""
        structured_llm = MagicMock()
        structured_llm.invoke.return_value = IntentResult(
            intent="START_TEST_DESIGN",
            confidence=0.95,
            entities=["登录页面"],
            reason="明确要求设计测试用例"
        )
        mock_llm.model.with_structured_output.return_value = structured_llm
        
        intent_router_node(base_state, mock_llm)
        
        mock_llm.model.with_structured_output.assert_called_once()
        call_args = mock_llm.model.with_structured_output.call_args
        assert call_args[0][0] == IntentResult
        assert call_args[1].get("method") == "function_calling"
    
    def test_start_test_design_sets_workflow_type(self, mock_llm, base_state):
        """START_TEST_DESIGN 意图应设置 current_workflow 为 test_design"""
        structured_llm = MagicMock()
        structured_llm.invoke.return_value = IntentResult(
            intent="START_TEST_DESIGN",
            confidence=0.95,
            entities=["登录页面"],
            reason="明确要求设计测试用例"
        )
        mock_llm.model.with_structured_output.return_value = structured_llm
        
        result = intent_router_node(base_state, mock_llm)
        
        assert result["current_workflow"] == "test_design"
    
    def test_start_requirement_review_sets_workflow_type(self, mock_llm, base_state):
        """START_REQUIREMENT_REVIEW 意图应设置 current_workflow 为 requirement_review"""
        structured_llm = MagicMock()
        structured_llm.invoke.return_value = IntentResult(
            intent="START_REQUIREMENT_REVIEW",
            confidence=0.85,
            entities=["需求文档"],
            reason="要求评审需求"
        )
        mock_llm.model.with_structured_output.return_value = structured_llm
        
        result = intent_router_node(base_state, mock_llm)
        
        assert result["current_workflow"] == "requirement_review"
    
    def test_null_intent_preserves_workflow_and_sets_clarification(self, mock_llm, base_state):
        """intent 为 null 时保持当前工作流，并设置 clarification"""
        base_state["current_workflow"] = "test_design"
        clarification_text = "您是希望我帮您评审需求文档，还是直接设计测试用例？"
        
        structured_llm = MagicMock()
        structured_llm.invoke.return_value = IntentResult(
            intent=None,
            confidence=0.3,
            entities=[],
            reason="意图不明确",
            clarification=clarification_text
        )
        mock_llm.model.with_structured_output.return_value = structured_llm
        
        result = intent_router_node(base_state, mock_llm)
        
        assert result["current_workflow"] == "test_design"
        assert result.get("clarification") == clarification_text
    
    def test_continue_workflow_preserves_existing_plan(self, mock_llm, base_state):
        """继续当前工作流时保持现有 plan 不变"""
        base_state["current_workflow"] = "requirement_review"
        base_state["plan"] = [
            {"id": "clarify", "name": "需求澄清", "status": "completed"},
            {"id": "analysis", "name": "评审分析", "status": "active"},
        ]
        base_state["current_stage_id"] = "analysis"
        
        structured_llm = MagicMock()
        structured_llm.invoke.return_value = IntentResult(
            intent=None,
            confidence=0.95,
            entities=["密码规则"],
            reason="用户在补充当前任务细节，无需切换工作流"
        )
        mock_llm.model.with_structured_output.return_value = structured_llm
        
        result = intent_router_node(base_state, mock_llm)
        
        assert result["current_workflow"] == "requirement_review"
        assert result["plan"] == base_state["plan"]
    
    def test_handles_empty_messages(self, mock_llm, base_state):
        """无消息时应直接返回原状态"""
        base_state["messages"] = []
        
        result = intent_router_node(base_state, mock_llm)
        
        assert result == base_state
        mock_llm.model.with_structured_output.assert_not_called()


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
