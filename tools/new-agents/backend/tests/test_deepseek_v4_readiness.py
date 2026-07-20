import json
from pathlib import Path

import pytest

from agent_contracts import validate_agent_turn
from agent_runtime import (
    PydanticAgentRuntime,
    RawStreamingConfig,
    build_structured_output_instruction,
)
from artifact_data_renderers import (
    get_artifact_data_renderer_stage_keys,
    render_agent_turn_from_artifact_data,
)
from sse_schemas import AgentTurnDeltaOutput
from test_artifact_data_renderers import ARTIFACT_DATA_STAGE_FIXTURES

ARTIFACT_DATA_FIXTURES = ARTIFACT_DATA_STAGE_FIXTURES

REPO_ROOT = Path(__file__).resolve().parents[4]


class FakeAgent:
    def run_sync(self, prompt, *, deps=None, model_settings=None):
        raise AssertionError("readiness tests use raw streaming, not PydanticAI")


def manifest_stage_keys():
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

    assert set(get_artifact_data_renderer_stage_keys()) == expected
    assert set(ARTIFACT_DATA_FIXTURES) == expected


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

    assert output is not None
    validate_agent_turn(output, workflow_id=workflow_id, current_stage_id=stage_id)


@pytest.mark.parametrize("workflow_id, stage_id", sorted(ARTIFACT_DATA_FIXTURES))
def test_deepseek_readiness_instruction_requests_artifact_data(workflow_id, stage_id):
    instruction = build_structured_output_instruction(workflow_id, stage_id)

    assert "artifact_data" in instruction
    assert "artifact_update.markdown" not in instruction


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
        kwargs["on_finish_reason"]("stop")

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
