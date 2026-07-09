import json
from functools import lru_cache
from pathlib import Path
from typing import Any


NEW_AGENTS_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_MANIFEST = NEW_AGENTS_ROOT / "workflow_manifest.json"

DERIVED_ARTIFACT_DATA_FIELD_POLICIES: tuple[dict[str, Any], ...] = (
    {
        "workflow_id": "TEST_DESIGN",
        "stage_id": "STRATEGY",
        "path": "risks[].rpn",
        "required_contract_fragments": (
            "risks[].rpn 由后端根据 severity * occurrence * detection 计算",
        ),
        "forbidden_runtime_example_tokens": ('"rpn":',),
    },
    {
        "workflow_id": "TEST_DESIGN",
        "stage_id": "CASES",
        "path": "case_statistics",
        "required_contract_fragments": (
            "case_statistics 由后端根据 case_groups 计算，模型不要输出",
        ),
        "forbidden_runtime_example_tokens": ('"case_statistics":',),
    },
    {
        "workflow_id": "TEST_DESIGN",
        "stage_id": "CASES",
        "path": "case_groups[].cases[].dimension",
        "required_contract_fragments": (
            "case_groups[].cases[].dimension 缺省时由后端按外层 "
            "case_groups[].dimension 派生",
        ),
        "forbidden_runtime_example_tokens": (
            '"case_id": "TC-001", "title": "...", "priority": "P0", "dimension":',
        ),
    },
    {
        "workflow_id": "TEST_DESIGN",
        "stage_id": "DELIVERY",
        "path": "case_summary_items[].case_count",
        "required_contract_fragments": (
            "case_summary_items[].case_count 缺省时由后端按 "
            "p0_count + p1_count + p2_count 派生",
        ),
        "forbidden_runtime_example_tokens": ('"case_count":',),
    },
    {
        "workflow_id": "TEST_DESIGN",
        "stage_id": "DELIVERY",
        "path": "delivery_metrics.total_cases",
        "required_contract_fragments": (
            "delivery_metrics.total_cases 缺省时由后端按 "
            "case_summary_items[].case_count 总和派生",
        ),
        "forbidden_runtime_example_tokens": ('"total_cases":',),
    },
    {
        "workflow_id": "TEST_DESIGN",
        "stage_id": "DELIVERY",
        "path": "delivery_metrics.high_risk_count",
        "required_contract_fragments": (
            "delivery_metrics.high_risk_count 缺省时由后端按 "
            "open_risks 中不可接受风险数量派生",
        ),
        "forbidden_runtime_example_tokens": ('"high_risk_count":',),
    },
    {
        "workflow_id": "REQ_REVIEW",
        "stage_id": "REVIEW",
        "path": "issue_statistics.p0_count/p1_count/p2_count",
        "required_contract_fragments": (
            "issue_statistics.p0_count/p1_count/p2_count 缺省时由后端按 "
            "issue_groups[].issues[].priority 中 P0/P1/P2 的数量派生",
        ),
        "forbidden_runtime_example_tokens": (
            '"p0_count":',
            '"p1_count":',
            '"p2_count":',
        ),
    },
    {
        "workflow_id": "REQ_REVIEW",
        "stage_id": "REVIEW",
        "path": "issue_groups[].issues[].dimension",
        "required_contract_fragments": (
            "issue_groups[].issues[].dimension 缺省时由后端按外层 "
            "issue_groups[].dimension 派生",
        ),
        "forbidden_runtime_example_tokens": (
            '"issue_id": "Q-001", "dimension":',
        ),
    },
    {
        "workflow_id": "REQ_REVIEW",
        "stage_id": "REPORT",
        "path": "issue_statistics.p0_count/p1_count/p2_count",
        "required_contract_fragments": (
            "issue_statistics.p0_count/p1_count/p2_count 缺省时由后端按 "
            "issue_closures[].priority 中 P0/P1/P2 的数量派生",
        ),
        "forbidden_runtime_example_tokens": (
            '"p0_count":',
            '"p1_count":',
            '"p2_count":',
        ),
    },
    {
        "workflow_id": "VALUE_DISCOVERY",
        "stage_id": "ELEVATOR",
        "path": "score_summary.total_score",
        "required_contract_fragments": (
            "score_summary.total_score 由后端根据 score_matrix[].score 求和计算，"
            "模型不要输出",
        ),
        "forbidden_runtime_example_tokens": ('"total_score":',),
    },
    {
        "workflow_id": "VALUE_DISCOVERY",
        "stage_id": "ELEVATOR",
        "path": "score_summary.average_score",
        "required_contract_fragments": (
            "score_summary.average_score 由后端根据 score_matrix[].score "
            "计算并保留 2 位小数，模型不要输出",
        ),
        "forbidden_runtime_example_tokens": ('"average_score":',),
    },
    {
        "workflow_id": "INCIDENT_REVIEW",
        "stage_id": "IMPROVEMENT",
        "path": "report_info.action_count",
        "required_contract_fragments": (
            "report_info.action_count 缺省时由后端按 improvement_actions 数量派生",
        ),
        "forbidden_runtime_example_tokens": ('"action_count":',),
    },
    {
        "workflow_id": "INCIDENT_REVIEW",
        "stage_id": "IMPROVEMENT",
        "path": "priority_distribution",
        "required_contract_fragments": (
            "priority_distribution 缺省时由后端按 "
            "improvement_actions[].priority 中紧急/重要/常规的数量派生",
        ),
        "forbidden_runtime_example_tokens": ('"priority_distribution":',),
    },
    {
        "workflow_id": "IDEA_BRAINSTORM",
        "stage_id": "CONVERGE",
        "path": "ice_evaluations[].ice_score",
        "required_contract_fragments": (
            "ice_score 缺省时由后端按 impact * confidence / effort 派生",
        ),
        "forbidden_runtime_example_tokens": ('"ice_score":',),
    },
    {
        "workflow_id": "IDEA_BRAINSTORM",
        "stage_id": "CONVERGE",
        "path": "ice_evaluations[].rank",
        "required_contract_fragments": (
            "rank 缺省时由后端按 ICE 得分降序派生",
        ),
        "forbidden_runtime_example_tokens": ('"rank":',),
    },
    {
        "workflow_id": "STORY_BREAKDOWN",
        "stage_id": "INPUT_ANALYSIS",
        "path": "user_stories[].sprint",
        "required_contract_fragments": (
            "user_stories[].sprint 缺省时由后端按 sprint_slices[].story_ids "
            "所属 sprint_slices[].sprint_id 派生",
        ),
        "forbidden_runtime_example_tokens": (
            '"story_id": "US-001", "epic_id": "EPIC-001", "title": "...", '
            '"user_story": "作为...我想...以便...", "priority": "P0/P1/P2", "sprint":',
        ),
    },
    {
        "workflow_id": "STORY_BREAKDOWN",
        "stage_id": "EPIC_MAPPING",
        "path": "user_stories[].sprint",
        "required_contract_fragments": (
            "user_stories[].sprint 缺省时由后端按 sprint_slices[].story_ids "
            "所属 sprint_slices[].sprint_id 派生",
        ),
        "forbidden_runtime_example_tokens": (
            '"story_id": "US-001", "epic_id": "EPIC-001", "title": "...", '
            '"user_story": "作为...我想...以便...", "priority": "P0/P1/P2", "sprint":',
        ),
    },
    {
        "workflow_id": "STORY_BREAKDOWN",
        "stage_id": "STORY_BACKLOG",
        "path": "user_stories[].sprint",
        "required_contract_fragments": (
            "user_stories[].sprint 缺省时由后端按 sprint_slices[].story_ids "
            "所属 sprint_slices[].sprint_id 派生",
        ),
        "forbidden_runtime_example_tokens": (
            '"story_id": "US-001", "epic_id": "EPIC-001", "title": "...", '
            '"user_story": "作为...我想...以便...", "priority": "P0/P1/P2", "sprint":',
        ),
    },
    {
        "workflow_id": "STORY_BREAKDOWN",
        "stage_id": "SPRINT_PLAN",
        "path": "user_stories[].sprint",
        "required_contract_fragments": (
            "user_stories[].sprint 缺省时由后端按 sprint_slices[].story_ids "
            "所属 sprint_slices[].sprint_id 派生",
        ),
        "forbidden_runtime_example_tokens": (
            '"story_id": "US-001", "epic_id": "EPIC-001", "title": "...", '
            '"user_story": "作为...我想...以便...", "priority": "P0/P1/P2", "sprint":',
        ),
    },
)


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


def get_derived_artifact_data_field_policies() -> tuple[dict[str, Any], ...]:
    return DERIVED_ARTIFACT_DATA_FIELD_POLICIES


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
