import ast
from pathlib import Path

from workflow_contract_registry import (
    get_required_artifact_headings,
    get_required_artifact_mermaid_diagrams,
    get_required_artifact_structured_visuals,
    get_stage_prompt_template_ids,
    get_workflow_stages,
)


AGENT_CONTRACTS = Path(__file__).resolve().parents[1] / "agent_contracts.py"


def _assigned_call_name(constant_name: str) -> str:
    module = ast.parse(AGENT_CONTRACTS.read_text(encoding="utf-8"))
    assigned_values: list[ast.expr | None] = []

    for statement in module.body:
        if isinstance(statement, ast.Assign):
            targets = statement.targets
            value = statement.value
        elif isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
            value = statement.value
        else:
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == constant_name
            for target in targets
        ):
            continue

        assigned_values.append(value)

    assert len(assigned_values) == 1, (
        f"{constant_name} 只能有一个模块级赋值，避免派生值被手工镜像覆盖"
    )
    value = assigned_values[0]
    assert isinstance(value, ast.Call), (
        f"{constant_name} 必须由 workflow_contract_registry 调用派生"
    )
    assert isinstance(value.func, ast.Name)
    return value.func.id
from agent_contracts import (
    REQUIRED_ARTIFACT_HEADINGS,
    REQUIRED_ARTIFACT_MERMAID_DIAGRAMS,
    REQUIRED_ARTIFACT_STRUCTURED_VISUALS,
)


def test_registry_derives_workflow_stages_from_manifest():
    assert get_workflow_stages() == {
        "TEST_DESIGN": ["CLARIFY", "STRATEGY", "CASES", "DELIVERY"],
        "REQ_REVIEW": ["REVIEW", "REPORT"],
        "INCIDENT_REVIEW": ["TIMELINE", "ROOT_CAUSE", "IMPROVEMENT"],
        "IDEA_BRAINSTORM": ["DEFINE", "DIVERGE", "CONVERGE", "CONCEPT"],
        "VALUE_DISCOVERY": ["ELEVATOR", "PERSONA", "JOURNEY", "BLUEPRINT"],
        "PRD_REVIEW": [
            "INVENTORY",
            "QUALITY_AUDIT",
            "COMPLETION_PLAN",
            "REVISION_BLUEPRINT",
        ],
        "STORY_BREAKDOWN": [
            "INPUT_ANALYSIS",
            "EPIC_MAPPING",
            "STORY_BACKLOG",
            "SPRINT_PLAN",
        ],
    }


def test_registry_requires_prompt_template_id_for_every_stage():
    prompt_template_ids = get_stage_prompt_template_ids()

    assert prompt_template_ids[("TEST_DESIGN", "CLARIFY")] == "test_design.clarify"
    assert prompt_template_ids[("IDEA_BRAINSTORM", "DIVERGE")] == "idea_brainstorm.diverge"
    assert prompt_template_ids[("VALUE_DISCOVERY", "PERSONA")] == "value_discovery.persona"
    assert prompt_template_ids[("PRD_REVIEW", "COMPLETION_PLAN")] == (
        "prd_review.completion_plan"
    )
    assert set(prompt_template_ids) == {
        (workflow_id, stage_id)
        for workflow_id, stage_ids in get_workflow_stages().items()
        for stage_id in stage_ids
    }


def test_registry_artifact_contract_metadata_matches_backend_contracts():
    assert get_required_artifact_headings() == REQUIRED_ARTIFACT_HEADINGS


def test_registry_visual_contract_metadata_matches_backend_contracts():
    assert get_required_artifact_mermaid_diagrams() == REQUIRED_ARTIFACT_MERMAID_DIAGRAMS
    assert get_required_artifact_structured_visuals() == REQUIRED_ARTIFACT_STRUCTURED_VISUALS


def test_agent_contracts_derives_declarative_maps_from_manifest_registry():
    assert {
        "WORKFLOW_STAGES": _assigned_call_name("WORKFLOW_STAGES"),
        "REQUIRED_ARTIFACT_HEADINGS": _assigned_call_name(
            "REQUIRED_ARTIFACT_HEADINGS"
        ),
        "REQUIRED_ARTIFACT_MERMAID_DIAGRAMS": _assigned_call_name(
            "REQUIRED_ARTIFACT_MERMAID_DIAGRAMS"
        ),
        "REQUIRED_ARTIFACT_STRUCTURED_VISUALS": _assigned_call_name(
            "REQUIRED_ARTIFACT_STRUCTURED_VISUALS"
        ),
    } == {
        "WORKFLOW_STAGES": "get_workflow_stages",
        "REQUIRED_ARTIFACT_HEADINGS": "get_required_artifact_headings",
        "REQUIRED_ARTIFACT_MERMAID_DIAGRAMS": "get_required_artifact_mermaid_diagrams",
        "REQUIRED_ARTIFACT_STRUCTURED_VISUALS": "get_required_artifact_structured_visuals",
    }
