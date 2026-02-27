"""clarify 阶段集成测试"""
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage


class TestClarifyIntentIntegration:
    """测试意图解析与 reasoning_node 的集成"""

    @patch('backend.agents.lisa.nodes.reasoning_node.parse_user_intent')
    @patch('backend.agents.lisa.nodes.reasoning_node.extract_blocking_questions')
    @patch('backend.agents.lisa.nodes.reasoning_node.get_robust_stream_writer')
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
        mock_llm.model.invoke.return_value.content = '{"thought":"MOCK","should_update_artifact":false,"request_transition_to":null}'
        state = {
            "messages": [HumanMessage(content="好的，继续")],
            "current_stage_id": "clarify",
            "current_workflow": "test_design",
            "plan": [{"id": "clarify", "name": "需求澄清"}],
            "artifacts": {},
            "artifact_templates": [],
        }
        
        result = reasoning_node(state, None, mock_llm)
        
        assert result.goto == "__end__"
        assert "阻塞性问题" in result.update["messages"][0].content

    @patch('backend.agents.lisa.nodes.reasoning_node.parse_user_intent')
    @patch('backend.agents.lisa.nodes.reasoning_node.extract_blocking_questions')
    @patch('backend.agents.lisa.nodes.reasoning_node.get_robust_stream_writer')
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
        mock_llm.model.invoke.return_value.content = '{"thought":"MOCK","should_update_artifact":false,"request_transition_to":null}'
        state = {
            "messages": [HumanMessage(content="好的，继续")],
            "current_stage_id": "clarify",
            "current_workflow": "test_design",
            "plan": [{"id": "clarify", "name": "需求澄清"}],
            "artifacts": {},
            "artifact_templates": [],
        }
        
        result = reasoning_node(state, None, mock_llm)
        
        assert mock_stream.called

    @patch('backend.agents.lisa.nodes.reasoning_node.get_robust_stream_writer')
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
        mock_llm.model.invoke.return_value.content = '{"thought":"MOCK","should_update_artifact":false,"request_transition_to":null}'
        state = {
            "messages": [HumanMessage(content="好的，继续")],
            "current_stage_id": "strategy",
            "current_workflow": "test_design",
            "plan": [{"id": "strategy", "name": "策略制定"}],
            "artifacts": {},
            "artifact_templates": [],
        }
        
        with patch('backend.agents.lisa.nodes.reasoning_node.parse_user_intent') as mock_parse:
            reasoning_node(state, None, mock_llm)
            mock_parse.assert_not_called()

    @patch('backend.agents.lisa.nodes.reasoning_node.parse_user_intent')
    @patch('backend.agents.lisa.nodes.reasoning_node.extract_blocking_questions')
    @patch('backend.agents.lisa.nodes.reasoning_node.get_robust_stream_writer')
    @patch('backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream')
    def test_llm_transition_blocked_by_p0(
        self, mock_stream, mock_writer, mock_extract, mock_parse
    ):
        """如果 LLM 自行决定进入下一阶段，但系统检测到存在 P0 问题，必须强行拦截不让跳出 clarify"""
        from backend.agents.lisa.schemas import UserIntentInClarify, ReasoningResponse
        from backend.agents.lisa.nodes.reasoning_node import reasoning_node
        
        mock_writer.return_value = Mock()
        # 假设用户只提供材料，未明确提出结束或 proceed
        mock_parse.return_value = UserIntentInClarify(
            intent="provide_material",
            confidence=0.8
        )
        
        # 尽管只提供了材料，但系统侦测到依然存在残留 P0！
        mock_extract.return_value = ["残留未解决的致命问题"]
        
        # 但是 LLM "走神了"，自己试图跳出
        mock_stream.return_value = ReasoningResponse(
            thought="材料收到了，我要开始策略制定了！",
            should_update_artifact=True,
            request_transition_to="strategy"  # 危险操作
        )
        
        mock_llm = Mock()
        mock_llm.model.invoke.return_value.content = '{"thought":"MOCK","should_update_artifact":false,"request_transition_to":null}'
        state = {
            "messages": [HumanMessage(content="这是给你的材料")],
            "current_stage_id": "clarify",
            "current_workflow": "test_design",
            "plan": [{"id": "clarify", "name": "需求澄清"}],
            "artifacts": {},
            "artifact_templates": [],
        }
        
        result = reasoning_node(state, None, mock_llm)
        
        # 验证结果被绝对防线强压下来
        assert result.goto == "artifact_node"
        
        # 拦截状态后当前阶段没有发生跃迁，所以不在 update_state 里，或者只检查 warning
        # 必须带上告警
        assert "warning" in result.update
        assert "拦截" in result.update["warning"]


class TestExtractBlockingQuestions:
    """测试从产出物中提取阻塞性问题"""
    
    def test_extract_from_structured_artifacts_with_blocking_questions(self):
        """测试从结构化产出物中提取阻塞性问题"""
        from backend.agents.lisa.nodes.reasoning_node import extract_blocking_questions
        
        # 遵循“确定性优先”原则，使用结构化数据
        structured_artifacts = {
            "test_design_requirements": {
                "assumptions": [
                    {
                        "priority": "P0",
                        "status": "pending",
                        "question": "用户登录失败后的重试机制是什么？",
                    },
                    {
                        "priority": "P0",
                        "status": "待确认",
                        "question": "订单金额的有效范围是多少？",
                    },
                    {
                        "priority": "P1",
                        "status": "pending",
                        "question": "是否需要考虑国际化场景？",
                    }
                ]
            }
        }
        
        result = extract_blocking_questions({}, structured_artifacts)
        
        assert len(result) == 2
        assert result[0] == "用户登录失败后的重试机制是什么？"
        assert result[1] == "订单金额的有效范围是多少？"

    def test_extract_from_empty_artifacts(self):
        """测试空产出物返回空列表"""
        from backend.agents.lisa.nodes.reasoning_node import extract_blocking_questions
        
        result = extract_blocking_questions({}, {})
        
        assert result == []
