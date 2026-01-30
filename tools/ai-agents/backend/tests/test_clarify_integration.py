"""clarify 阶段集成测试"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage


class TestClarifyIntentIntegration:
    """测试意图解析与 reasoning_node 的集成"""

    @patch('backend.agents.lisa.nodes.reasoning_node.parse_user_intent')
    @patch('backend.agents.lisa.nodes.reasoning_node.extract_blocking_questions')
    @patch('backend.agents.lisa.nodes.reasoning_node.get_stream_writer')
    def test_confirm_proceed_with_blockers_returns_warning(
        self, mock_writer, mock_extract, mock_parse
    ):
        """用户确认继续但有阻塞问题时，应返回警告"""
        from backend.agents.lisa.schemas import UserIntentInClarify
        from backend.agents.lisa.nodes.reasoning_node import reasoning_node
        
        mock_writer.return_value = Mock()
        mock_parse.return_value = UserIntentInClarify(
            intent="confirm_proceed",
            confidence=0.9
        )
        mock_extract.return_value = ["Q1: 登录重试机制?"]
        
        mock_llm = Mock()
        state = {
            "messages": [HumanMessage(content="好的，继续")],
            "current_stage_id": "clarify",
            "current_workflow": "test_design",
            "plan": [{"id": "clarify", "name": "需求澄清"}],
            "artifacts": {},
            "artifact_templates": [],
        }
        
        result = reasoning_node(state, mock_llm)
        
        assert result.goto == "__end__"
        assert "阻塞性问题" in result.update["messages"][0].content

    @patch('backend.agents.lisa.nodes.reasoning_node.parse_user_intent')
    @patch('backend.agents.lisa.nodes.reasoning_node.extract_blocking_questions')
    @patch('backend.agents.lisa.nodes.reasoning_node.get_stream_writer')
    @patch('backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream')
    def test_confirm_proceed_no_blockers_continues_reasoning(
        self, mock_stream, mock_writer, mock_extract, mock_parse
    ):
        """用户确认继续且无阻塞问题时，应继续推理流程"""
        from backend.agents.lisa.schemas import UserIntentInClarify, ReasoningResponse
        from backend.agents.lisa.nodes.reasoning_node import reasoning_node
        
        mock_writer.return_value = Mock()
        mock_parse.return_value = UserIntentInClarify(
            intent="confirm_proceed",
            confidence=0.9
        )
        mock_extract.return_value = []
        mock_stream.return_value = ReasoningResponse(
            thought="好的，让我们继续",
            should_update_artifact=False,
            request_transition_to="strategy"
        )
        
        mock_llm = Mock()
        state = {
            "messages": [HumanMessage(content="好的，继续")],
            "current_stage_id": "clarify",
            "current_workflow": "test_design",
            "plan": [{"id": "clarify", "name": "需求澄清"}],
            "artifacts": {},
            "artifact_templates": [],
        }
        
        result = reasoning_node(state, mock_llm)
        
        assert mock_stream.called

    @patch('backend.agents.lisa.nodes.reasoning_node.get_stream_writer')
    @patch('backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream')
    def test_non_clarify_stage_skips_intent_parsing(
        self, mock_stream, mock_writer
    ):
        """非 clarify 阶段应跳过意图解析"""
        from backend.agents.lisa.schemas import ReasoningResponse
        from backend.agents.lisa.nodes.reasoning_node import reasoning_node
        
        mock_writer.return_value = Mock()
        mock_stream.return_value = ReasoningResponse(
            thought="正在制定测试策略",
            should_update_artifact=True
        )
        
        mock_llm = Mock()
        state = {
            "messages": [HumanMessage(content="好的，继续")],
            "current_stage_id": "strategy",
            "current_workflow": "test_design",
            "plan": [{"id": "strategy", "name": "策略制定"}],
            "artifacts": {},
            "artifact_templates": [],
        }
        
        with patch('backend.agents.lisa.nodes.reasoning_node.parse_user_intent') as mock_parse:
            reasoning_node(state, mock_llm)
            mock_parse.assert_not_called()


class TestExtractBlockingQuestions:
    """测试从产出物中提取阻塞性问题"""
    
    def test_extract_from_markdown_with_blocking_questions(self):
        """测试从包含阻塞性问题的 Markdown 中提取"""
        from backend.agents.lisa.nodes.reasoning_node import extract_blocking_questions
        
        artifacts = {
            "test_design_requirements": """
# 需求分析文档

## 待澄清问题

### 🔴 阻塞性问题 (必须解决)
1. [Q1] 用户登录失败后的重试机制是什么？
2. [Q2] 订单金额的有效范围是多少？

### 🟡 建议澄清
3. [Q3] 是否需要考虑国际化场景？
"""
        }
        
        result = extract_blocking_questions(artifacts)
        
        assert len(result) == 2
        assert "登录" in result[0] or "重试" in result[0]

    def test_extract_from_empty_artifacts(self):
        """测试空产出物返回空列表"""
        from backend.agents.lisa.nodes.reasoning_node import extract_blocking_questions
        
        result = extract_blocking_questions({})
        
        assert result == []
