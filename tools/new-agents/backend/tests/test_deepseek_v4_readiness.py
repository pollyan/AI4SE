import json
from pathlib import Path

import pytest

from agent_contracts import validate_agent_turn
from agent_runtime import (
    PydanticAgentRuntime,
    RawStreamingConfig,
    build_model_settings,
    build_structured_output_instruction,
    get_artifact_data_ready_stages,
    resolve_structured_output_capability,
)
from artifact_data_renderers import (
    get_artifact_data_renderer_stage_keys,
    render_agent_turn_from_artifact_data,
)
from sse_schemas import AgentTurnDeltaOutput
from test_artifact_data_renderers import (
    VALID_CASES_ARTIFACT_DATA,
    VALID_CLARIFY_ARTIFACT_DATA,
    VALID_DELIVERY_ARTIFACT_DATA,
    VALID_IDEA_CONCEPT_ARTIFACT_DATA,
    VALID_IDEA_CONVERGE_ARTIFACT_DATA,
    VALID_IDEA_DEFINE_ARTIFACT_DATA,
    VALID_IDEA_DIVERGE_ARTIFACT_DATA,
    VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA,
    VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA,
    VALID_INCIDENT_TIMELINE_ARTIFACT_DATA,
    VALID_PRD_REVIEW_ARTIFACT_DATA,
    VALID_REQ_REVIEW_ARTIFACT_DATA,
    VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
    VALID_STORY_BREAKDOWN_ARTIFACT_DATA,
    VALID_STRATEGY_ARTIFACT_DATA,
    VALID_VALUE_BLUEPRINT_ARTIFACT_DATA,
    VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
    VALID_VALUE_JOURNEY_ARTIFACT_DATA,
    VALID_VALUE_PERSONA_ARTIFACT_DATA,
)

REPO_ROOT = Path(__file__).resolve().parents[4]

ARTIFACT_DATA_FIXTURES = {
    ("TEST_DESIGN", "CLARIFY"): VALID_CLARIFY_ARTIFACT_DATA,
    ("TEST_DESIGN", "STRATEGY"): VALID_STRATEGY_ARTIFACT_DATA,
    ("TEST_DESIGN", "CASES"): VALID_CASES_ARTIFACT_DATA,
    ("TEST_DESIGN", "DELIVERY"): VALID_DELIVERY_ARTIFACT_DATA,
    ("REQ_REVIEW", "REVIEW"): VALID_REQ_REVIEW_ARTIFACT_DATA,
    ("REQ_REVIEW", "REPORT"): VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
    ("INCIDENT_REVIEW", "TIMELINE"): VALID_INCIDENT_TIMELINE_ARTIFACT_DATA,
    ("INCIDENT_REVIEW", "ROOT_CAUSE"): VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA,
    ("INCIDENT_REVIEW", "IMPROVEMENT"): VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA,
    ("IDEA_BRAINSTORM", "DEFINE"): VALID_IDEA_DEFINE_ARTIFACT_DATA,
    ("IDEA_BRAINSTORM", "DIVERGE"): VALID_IDEA_DIVERGE_ARTIFACT_DATA,
    ("IDEA_BRAINSTORM", "CONVERGE"): VALID_IDEA_CONVERGE_ARTIFACT_DATA,
    ("IDEA_BRAINSTORM", "CONCEPT"): VALID_IDEA_CONCEPT_ARTIFACT_DATA,
    ("VALUE_DISCOVERY", "ELEVATOR"): VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
    ("VALUE_DISCOVERY", "PERSONA"): VALID_VALUE_PERSONA_ARTIFACT_DATA,
    ("VALUE_DISCOVERY", "JOURNEY"): VALID_VALUE_JOURNEY_ARTIFACT_DATA,
    ("VALUE_DISCOVERY", "BLUEPRINT"): VALID_VALUE_BLUEPRINT_ARTIFACT_DATA,
    ("PRD_REVIEW", "INVENTORY"): VALID_PRD_REVIEW_ARTIFACT_DATA,
    ("PRD_REVIEW", "QUALITY_AUDIT"): VALID_PRD_REVIEW_ARTIFACT_DATA,
    ("PRD_REVIEW", "COMPLETION_PLAN"): VALID_PRD_REVIEW_ARTIFACT_DATA,
    ("PRD_REVIEW", "REVISION_BLUEPRINT"): VALID_PRD_REVIEW_ARTIFACT_DATA,
    ("STORY_BREAKDOWN", "INPUT_ANALYSIS"): VALID_STORY_BREAKDOWN_ARTIFACT_DATA,
    ("STORY_BREAKDOWN", "EPIC_MAPPING"): VALID_STORY_BREAKDOWN_ARTIFACT_DATA,
    ("STORY_BREAKDOWN", "STORY_BACKLOG"): VALID_STORY_BREAKDOWN_ARTIFACT_DATA,
    ("STORY_BREAKDOWN", "SPRINT_PLAN"): VALID_STORY_BREAKDOWN_ARTIFACT_DATA,
}


class FakeAgent:
    def run_sync(self, prompt, *, deps=None, model_settings=None):
        raise AssertionError("readiness tests use raw streaming, not PydanticAI")


def manifest_stage_keys() -> set[tuple[str, str]]:
    manifest = json.loads(
        (REPO_ROOT / "tools/new-agents/workflow_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    return {
        (workflow_id, stage["id"])
        for workflow_id, workflow in manifest["workflows"].items()
        for stage in workflow["stages"]
    }


def test_deepseek_readiness_covers_every_manifest_stage():
    expected = manifest_stage_keys()

    assert get_artifact_data_ready_stages() == expected
    assert get_artifact_data_renderer_stage_keys() == expected
    assert set(ARTIFACT_DATA_FIXTURES) == expected


def test_deepseek_v4_uses_json_object_only_with_thinking_disabled():
    capability = resolve_structured_output_capability("deepseek-v4-flash")

    assert capability.tier == "json_object_only"
    assert capability.response_format == {"type": "json_object"}
    assert build_model_settings("deepseek-v4-flash") == {
        "extra_body": {"thinking": {"type": "disabled"}}
    }


@pytest.mark.parametrize("workflow_id, stage_id", sorted(ARTIFACT_DATA_FIXTURES))
def test_deepseek_readiness_renderer_output_passes_contract(workflow_id, stage_id):
    output = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成结构化产物数据。",
            "artifact_data": ARTIFACT_DATA_FIXTURES[(workflow_id, stage_id)],
            "stage_action": None,
            "warnings": [],
        },
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )

    assert output.artifact_update.markdown
    assert (
        validate_agent_turn(
            output,
            workflow_id=workflow_id,
            current_stage_id=stage_id,
        )
        == output
    )


@pytest.mark.parametrize("workflow_id, stage_id", sorted(ARTIFACT_DATA_FIXTURES))
def test_deepseek_readiness_instruction_requests_artifact_data(workflow_id, stage_id):
    instruction = build_structured_output_instruction(workflow_id, stage_id)

    assert "artifact_data" in instruction
    assert "artifact_update.markdown" not in instruction
    assert "不要输出完整 Markdown" in instruction


@pytest.mark.parametrize("workflow_id, stage_id", sorted(ARTIFACT_DATA_FIXTURES))
def test_deepseek_readiness_raw_json_streaming_uses_json_object_mode(
    monkeypatch,
    workflow_id,
    stage_id,
):
    final_json = json.dumps(
        {
            "chat": "已生成结构化产物数据。",
            "artifact_data": ARTIFACT_DATA_FIXTURES[(workflow_id, stage_id)],
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield final_json[:12]
        yield final_json[12:]

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )
    runtime = PydanticAgentRuntime(
        FakeAgent(),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="system prompt",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户输入",
            workflow_id=workflow_id,
            current_stage_id=stage_id,
        )
    )

    assert isinstance(outputs[0], AgentTurnDeltaOutput)
    assert outputs[-1].artifact_update.markdown
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
