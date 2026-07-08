import json
from functools import lru_cache
from pathlib import Path
from typing import Any


NEW_AGENTS_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_MANIFEST = NEW_AGENTS_ROOT / "workflow_manifest.json"


@lru_cache(maxsize=1)
def load_workflow_manifest() -> dict[str, Any]:
    return json.loads(WORKFLOW_MANIFEST.read_text(encoding="utf-8"))


def get_workflow_agent_id(workflow_id: str) -> str:
    workflow = load_workflow_manifest()["workflows"].get(workflow_id)
    if workflow is None:
        raise ValueError(f"未知 workflowId: {workflow_id}")
    agent_id = workflow.get("agentId")
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError(f"workflow manifest 缺少 agentId: {workflow_id}")
    return agent_id.strip()


def get_workflow_stage(workflow_id: str, stage_id: str) -> dict[str, Any]:
    workflow = load_workflow_manifest()["workflows"].get(workflow_id)
    if workflow is None:
        raise ValueError(f"未知 workflowId: {workflow_id}")
    for stage in workflow.get("stages", []):
        if stage.get("id") == stage_id:
            return stage
    raise ValueError(f"未知 workflow stage: {workflow_id}/{stage_id}")


def get_stage_artifact_data_contract(
    workflow_id: str,
    stage_id: str,
) -> dict[str, Any] | None:
    stage = get_workflow_stage(workflow_id, stage_id)
    contract = stage.get("artifactDataContract")
    if contract is None:
        return None
    if not isinstance(contract, dict):
        raise ValueError(
            f"artifactDataContract 必须是对象: {workflow_id}/{stage_id}"
        )
    return contract


def _string_list(
    value: Any,
    field_name: str,
    workflow_id: str,
    stage_id: str,
) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(
            f"artifactDataContract.{field_name} 必须是非空字符串数组: "
            f"{workflow_id}/{stage_id}"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"artifactDataContract.{field_name} 包含空值: "
                f"{workflow_id}/{stage_id}"
            )
        result.append(item.strip())
    return result


def _join_with_final_separator(items: list[str], final_separator: str) -> str:
    if len(items) == 1:
        return items[0]
    return "、".join(items[:-1]) + final_separator + items[-1]


def format_artifact_data_contract_instruction(
    workflow_id: str,
    stage_id: str,
) -> str:
    contract = get_stage_artifact_data_contract(workflow_id, stage_id)
    if contract is None:
        return "artifact_data 中所有字符串必须非空；数组必须至少包含一项。"

    model_output_rules = _string_list(
        contract.get("modelOutputRules"),
        "modelOutputRules",
        workflow_id,
        stage_id,
    )
    forbidden_outputs = _string_list(
        contract.get("forbiddenOutputs"),
        "forbiddenOutputs",
        workflow_id,
        stage_id,
    )
    renderer_outputs = _string_list(
        contract.get("rendererOutputs"),
        "rendererOutputs",
        workflow_id,
        stage_id,
    )
    return (
        "artifact_data 中所有字符串必须非空；数组必须至少包含一项；"
        + "；".join(model_output_rules)
        + "。不要输出"
        + _join_with_final_separator(forbidden_outputs, "或 ")
        + "，后端会负责确定性渲染"
        + _join_with_final_separator(renderer_outputs, "和 ")
        + "。"
    )


def get_workflow_handoffs() -> list[dict[str, Any]]:
    handoffs = load_workflow_manifest().get("handoffs", [])
    if not isinstance(handoffs, list):
        raise ValueError("workflow manifest handoffs 必须是数组")
    return handoffs
