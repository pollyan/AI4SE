from functools import lru_cache
from typing import Any

from workflow_manifest import load_workflow_manifest


def _require_non_blank_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"workflow manifest 缺少 {field_name}")
    return value.strip()


@lru_cache(maxsize=1)
def get_workflow_contract_registry() -> dict[str, Any]:
    manifest = load_workflow_manifest()
    workflows = manifest.get("workflows")
    if not isinstance(workflows, dict):
        raise ValueError("workflow manifest workflows 必须是对象")
    return manifest


def get_workflow_stages() -> dict[str, list[str]]:
    workflows = get_workflow_contract_registry()["workflows"]
    workflow_stages: dict[str, list[str]] = {}

    for workflow_id, workflow in workflows.items():
        stages = workflow.get("stages")
        if not isinstance(stages, list):
            raise ValueError(f"workflow manifest stages 必须是数组: {workflow_id}")
        workflow_stages[workflow_id] = [
            _require_non_blank_string(stage.get("id"), f"{workflow_id}.stages[].id")
            for stage in stages
        ]

    return workflow_stages


def get_stage_prompt_template_ids() -> dict[tuple[str, str], str]:
    workflows = get_workflow_contract_registry()["workflows"]
    prompt_template_ids: dict[tuple[str, str], str] = {}

    for workflow_id, workflow in workflows.items():
        stages = workflow.get("stages")
        if not isinstance(stages, list):
            raise ValueError(f"workflow manifest stages 必须是数组: {workflow_id}")
        for stage in stages:
            stage_id = _require_non_blank_string(
                stage.get("id"),
                f"{workflow_id}.stages[].id",
            )
            prompt_template_ids[(workflow_id, stage_id)] = _require_non_blank_string(
                stage.get("promptTemplateId"),
                f"{workflow_id}/{stage_id}.promptTemplateId",
            )

    return prompt_template_ids


def get_handoff_prompt_template_ids() -> dict[str, str]:
    handoffs = get_workflow_contract_registry().get("handoffs", [])
    if not isinstance(handoffs, list):
        raise ValueError("workflow manifest handoffs 必须是数组")

    return {
        _require_non_blank_string(handoff.get("id"), "handoffs[].id"):
        _require_non_blank_string(
            handoff.get("promptTemplateId"),
            f"{handoff.get('id')}.promptTemplateId",
        )
        for handoff in handoffs
    }
