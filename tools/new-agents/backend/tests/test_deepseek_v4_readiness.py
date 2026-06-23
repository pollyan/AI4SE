import json
from pathlib import Path

import pytest

from agent_runtime import (
    build_model_settings,
    build_structured_output_instruction,
    get_artifact_data_ready_stages,
    resolve_structured_output_capability,
)
from artifact_data_renderers import render_agent_turn_from_artifact_data


REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOW_MANIFEST = REPO_ROOT / "tools/new-agents/workflow_manifest.json"


def _manifest_stages() -> set[tuple[str, str]]:
    manifest = json.loads(WORKFLOW_MANIFEST.read_text(encoding="utf-8"))
    return {
        (workflow_id, stage["id"])
        for workflow_id, workflow in manifest["workflows"].items()
        for stage in workflow["stages"]
    }


def test_all_manifest_stages_are_deepseek_artifact_data_ready():
    assert get_artifact_data_ready_stages() == _manifest_stages()


def test_artifact_data_ready_stages_do_not_prompt_model_for_markdown_artifacts():
    for workflow_id, stage_id in sorted(get_artifact_data_ready_stages()):
        instruction = build_structured_output_instruction(workflow_id, stage_id)

        assert '"artifact_data"' in instruction
        assert "artifact_update.markdown" not in instruction
        assert "不要输出完整 Markdown" in instruction


def test_deepseek_v4_uses_json_object_only_with_thinking_disabled():
    capability = resolve_structured_output_capability("deepseek-v4-flash")

    assert capability.tier == "json_object_only"
    assert capability.response_format == {"type": "json_object"}
    assert build_model_settings("deepseek-v4-flash") == {
        "extra_body": {"thinking": {"type": "disabled"}}
    }


def test_unknown_artifact_data_stage_is_not_rendered_as_fake_success():
    with pytest.raises(
        ValueError,
        match="artifact_data renderer is not configured for UNKNOWN_WORKFLOW/UNKNOWN_STAGE",
    ):
        render_agent_turn_from_artifact_data(
            {
                "chat": "已生成业务数据。",
                "artifact_data": {"unknown": "stage"},
                "stage_action": None,
                "warnings": [],
            },
            workflow_id="UNKNOWN_WORKFLOW",
            current_stage_id="UNKNOWN_STAGE",
        )
