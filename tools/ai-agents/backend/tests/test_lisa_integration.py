
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from backend.agents.lisa.graph import create_lisa_graph
from backend.agents.lisa.state import get_initial_state, ArtifactKeys

class MockLLMResponse:
    """Helper to simulate LLM responses based on input patterns"""
    
    def __init__(self):
        self.responses = []
        
    def add_response(self, trigger_content: str, response_content: str):
        self.responses.append((trigger_content, response_content))
        
    def invoke(self, messages):
        """Mock invoke method"""
        last_msg = messages[-1]
        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        
        # Check input against triggers
        for trigger, response in self.responses:
            if trigger in content:
                # Return AIMessage
                return AIMessage(content=response)
        
        # Default response if no match
        return AIMessage(content='{"intent": "UNCLEAR", "confidence": 0.5}')

@pytest.mark.asyncio
async def test_lisa_full_workflow_integration():
    """
    Integration test for Lisa's multi-turn workflow.
    Simulates:
    1. User asks vague question -> Router -> Clarify
    2. User answers -> Router -> Test Design (Clarify Stage) -> Artifact Generated
    """
    
    # 1. Setup Mock LLM
    mock_llm = MagicMock()
    
    # Define Scenario Responses
    def side_effect_invoke(messages, **kwargs):
        # Extract last user message content for simple routing
        # Note: messages might include SystemMessage, so we look for HumanMessage or last message
        user_content = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_content = m.content
                break
        
        # Determine intent routing responses (Router Node)
        if "请分析上述对话中用户的意图" in str(messages[-1].content): # Router prompt signature
            if "登录功能" in user_content and "新功能" not in user_content:
                # Turn 1: Vague request
                return AIMessage(content='{"intent": "UNCLEAR"}')
            elif "新功能" in user_content:
                # Turn 2: Specific request
                return AIMessage(content='{"intent": "START_TEST_DESIGN"}')
                
        # Determine Test Design Logic (Design Node)
        if "测试设计工作流" in str(messages[0].content): # Design prompt signature
             return AIMessage(content="""
好的，我已更新需求文档。
```markdown
# 需求分析文档
## 功能概述
用户登录功能...
```
""")
             
        # Default fallback
        return AIMessage(content="I don't understand.")

    mock_llm.model.invoke.side_effect = side_effect_invoke

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
        
        # Run graph
        result = await graph.ainvoke(state)
        
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
        
        # Run graph again
        result_2 = await graph.ainvoke(state)
        
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

