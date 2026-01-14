
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from backend.agents.lisa.graph import create_lisa_graph
from backend.agents.lisa.state import get_initial_state, ArtifactKeys
from backend.agents.lisa.schemas import IntentResult


@pytest.mark.asyncio
async def test_lisa_full_workflow_integration():
    mock_llm = MagicMock()
    
    call_count = {"intent_router": 0}
    
    def side_effect_with_structured_output(schema, method=None):
        structured_mock = MagicMock()
        
        def structured_invoke(messages, **kwargs):
            call_count["intent_router"] += 1
            
            user_content = ""
            for m in reversed(messages):
                if isinstance(m, HumanMessage):
                    user_content = m.content
                    break
            
            if call_count["intent_router"] == 1:
                return IntentResult(
                    intent=None,
                    confidence=0.5,
                    entities=["登录功能"],
                    reason="意图不明确",
                    clarification="请问您是想进行新功能测试还是回归测试？"
                )
            else:
                return IntentResult(
                    intent="START_TEST_DESIGN",
                    confidence=0.95,
                    entities=["登录功能"],
                    reason="明确要求进行新功能测试"
                )
        
        structured_mock.invoke = structured_invoke
        return structured_mock
    
    def side_effect_invoke(messages, **kwargs):
        user_content = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_content = m.content
                break
        
        if "测试设计工作流" in str(messages[0].content):
             return AIMessage(content="""
好的，我已更新需求文档。
```markdown
# 需求分析文档
## 功能概述
用户登录功能...
```
""")
             
        return AIMessage(content="I don't understand.")

    mock_llm.model.invoke.side_effect = side_effect_invoke
    mock_llm.model.with_structured_output.side_effect = side_effect_with_structured_output

    # 2. Patch create_llm to return our mock
    with patch('backend.agents.lisa.graph.create_llm_from_config', return_value=mock_llm):
        
        # 3. Initialize Graph
        config = {"model_name": "mock-gpt", "base_url": "", "api_key": ""}
        graph = create_lisa_graph(config)
        
        # 4. Turn 1: Vague Request
        # ---------------------------------------------------------
        # User: "我想测试一个登录功能"
        # Expectation: Router -> Clarify (Ask Method)
        
        state = get_initial_state()
        state["messages"] = [HumanMessage(content="我想测试一个登录功能")]
        
        invoke_config = {"configurable": {"thread_id": "test-lisa-001"}}
        result = await graph.ainvoke(state, config=invoke_config)
        
        # Assertions Turn 1
        assert "Lisa Song" in result["messages"][-1].content # Clarify message
        assert result.get("current_workflow") is None # Not started yet
        
        # 5. Turn 2: Answer Clarification
        # ---------------------------------------------------------
        # User: "是新功能测试"
        # Expectation: Router -> Test Design -> Artifact Created (Strategy Stage)
        
        # Simulate continuing conversation (append previous AI response + new User input)
        state = result # Carry over state
        state["messages"].append(HumanMessage(content="是新功能测试"))
        
        result_2 = await graph.ainvoke(state, config=invoke_config)
        
        # Assertions Turn 2
        last_msg = result_2["messages"][-1]
        
        # Should have routed to test design
        assert result_2["current_workflow"] == "test_design"
        
        # Should have generated artifact
        assert ArtifactKeys.TEST_DESIGN_REQUIREMENTS in result_2["artifacts"]
        assert "需求分析文档" in result_2["artifacts"][ArtifactKeys.TEST_DESIGN_REQUIREMENTS]
        
        # State should be updated (determined by artifacts)
        # Note: The 'workflow_stage' field in the returned state reflects the stage *during* execution (clarify).
        # The next turn would pick up 'strategy' based on the presence of the artifact.
        # So we assert the artifact presence and that determine_stage would now return 'strategy'.

        from backend.agents.lisa.nodes.workflow_test_design import determine_stage
        assert determine_stage(result_2, "test_design") == "strategy"

