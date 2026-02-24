import pytest
from typing import cast, Dict, Any
from unittest.mock import MagicMock, patch
from langgraph.types import Command
from backend.agents.lisa.nodes.reasoning_node import reasoning_node
from backend.agents.lisa.schemas import ReasoningResponse
from backend.agents.lisa.state import LisaState


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    # Mock fallback string response for extract_json_from_markdown
    llm.model.invoke.return_value.content = '{"thought": "mocked", "should_update_artifact": false}'
    # Provide backward compatibility for older tests
    structured_llm = MagicMock()
    llm.model.with_structured_output.return_value = structured_llm
    return llm


@pytest.fixture
def mock_state() -> Dict[str, Any]:
    return {
        "messages": [],
        "artifacts": {"test_design_requirements": "existing content"},
        "current_stage_id": "clarify",
        "current_workflow": "test_design",
        "plan": [{"id": "clarify", "name": "Clarify"}],
    }


@patch("backend.agents.lisa.nodes.reasoning_node.get_robust_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_test_design_prompt")
def test_reasoning_node_always_routes_to_artifact(
    mock_prompt, mock_process, mock_writer, mock_llm, mock_state
):
    """Test that ReasoningNode ALWAYS routes to artifact_node, regardless of should_update flag"""

    # Case 1: LLM says update needed
    mock_process.return_value = ReasoningResponse(
        thought="Update needed.",
        progress_step="Updating...",
        should_update_artifact=True,
    )

    command = reasoning_node(cast(LisaState, mock_state), None, mock_llm)
    assert command.goto == "artifact_node"

    # Case 2: LLM says NO update needed (should still route to artifact_node per new logic)
    mock_process.return_value = ReasoningResponse(
        thought="No update needed.", should_update_artifact=False
    )

    command = reasoning_node(cast(LisaState, mock_state), None, mock_llm)
    assert command.goto == "artifact_node"


@patch("backend.agents.lisa.nodes.reasoning_node.get_robust_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_test_design_prompt")
def test_reasoning_node_initializaton_force_routing(
    mock_prompt, mock_process, mock_writer, mock_llm
):
    """Test that ReasoningNode forces routing to ArtifactNode when initializing empty artifact"""

    # Empty state triggering initialization
    state = {
        "messages": [],
        "artifacts": {},  # Empty artifacts
        # plan and templates missing, ensuring ensure_workflow_initialized runs
    }

    # Mock LLM saying NO update needed (we expect the logic to override this)
    mock_process.return_value = ReasoningResponse(
        thought="Welcome.", should_update_artifact=False
    )

    command = reasoning_node(cast(LisaState, state), None, mock_llm)

    assert isinstance(command, Command)
    assert command.goto == "artifact_node"
    # State should have been updated with initialization data
    assert command.update is not None
    assert "plan" in command.update
    assert "artifact_templates" in command.update


@patch("backend.agents.lisa.nodes.reasoning_node.get_robust_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_test_design_prompt")
def test_reasoning_node_stream_exception(
    mock_prompt, mock_process, mock_writer, mock_llm, mock_state
):
    mock_process.side_effect = Exception("Stream error")

    command = reasoning_node(cast(LisaState, mock_state), None, mock_llm)

    assert isinstance(command, Command)
    assert command.goto == "__end__"
    assert command.update is not None
    assert len(command.update["messages"]) > 0
    assert "异常" in command.update["messages"][-1].content


@patch("backend.agents.lisa.nodes.reasoning_node.get_robust_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_test_design_prompt")
def test_reasoning_node_stage_transition(
    mock_prompt, mock_process, mock_writer, mock_llm, mock_state
):
    mock_process.return_value = ReasoningResponse(
        thought="Moving to next stage",
        request_transition_to="strategy",
        should_update_artifact=False,
    )

    command = reasoning_node(cast(LisaState, mock_state), None, mock_llm)

    assert command.update is not None
    assert command.update["current_stage_id"] == "strategy"
    assert command.update.get("current_workflow") == "test_design"


@patch("backend.agents.lisa.nodes.reasoning_node.get_robust_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_requirement_review_prompt")
def test_reasoning_node_req_review_workflow(
    mock_req_prompt, mock_process, mock_writer, mock_llm
):
    state = {
        "messages": [],
        "artifacts": {"req_review_record": "content"},
        "current_stage_id": "clarify",
        "current_workflow": "requirement_review",
        "plan": [{"id": "clarify", "name": "Clarify"}],
    }

    mock_process.return_value = ReasoningResponse(
        thought="Reviewing...", should_update_artifact=False
    )

    reasoning_node(cast(LisaState, state), None, mock_llm)

    mock_req_prompt.assert_called_once()


@patch("backend.agents.lisa.nodes.reasoning_node.get_robust_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_test_design_prompt")
def test_stage_transition_triggers_artifact_for_missing_output(
    mock_prompt, mock_process, mock_writer, mock_llm
):
    """
    测试：当用户请求流转到新阶段时，如果新阶段缺少产出物，
    应该强制路由到 artifact_node 来生成初始产出物。

    这是修复 GitHub Issue 的关键测试：
    用户说"进入strategy"时，应该自动生成 strategy 阶段的产出物。
    """
    state = {
        "messages": [],
        "artifacts": {
            "test_design_requirements": "existing content"
        },  # clarify 阶段的产出物已存在
        "current_stage_id": "clarify",
        "current_workflow": "test_design",
        "plan": [
            {"id": "clarify", "name": "Clarify"},
            {"id": "strategy", "name": "Strategy"},
        ],
        "artifact_templates": [
            {
                "stage": "clarify",
                "key": "test_design_requirements",
                "outline": "Requirements outline",
            },
            {
                "stage": "strategy",
                "key": "test_strategy",
                "outline": "Strategy outline",
            },
        ],
    }

    # 模拟 LLM 响应：请求流转到 strategy 阶段，但不需要更新产出物
    mock_process.return_value = ReasoningResponse(
        thought="Moving to strategy stage",
        request_transition_to="strategy",
        should_update_artifact=False,  # LLM 认为不需要更新
    )

    command = reasoning_node(cast(LisaState, state), None, mock_llm)

    # 验证：
    # 1. 阶段应该被更新为 strategy
    assert command.update["current_stage_id"] == "strategy"
    # 2. 应该强制路由到 artifact_node（因为 strategy 阶段的产出物 test_strategy 不存在）
    assert command.goto == "artifact_node", (
        f"Expected routing to artifact_node for missing 'test_strategy' artifact, but got {command.goto}"
    )
