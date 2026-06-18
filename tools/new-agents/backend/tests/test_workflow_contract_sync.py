import re
from pathlib import Path

from agent_contracts import REQUIRED_ARTIFACT_HEADINGS, WORKFLOW_STAGES


NEW_AGENTS_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_WORKFLOWS = (
    NEW_AGENTS_ROOT
    / "frontend"
    / "src"
    / "core"
    / "workflows.ts"
)


def _frontend_workflow_stages() -> dict[str, list[str]]:
    workflows: dict[str, list[str]] = {}
    current_workflow: str | None = None
    in_stages = False

    for line in FRONTEND_WORKFLOWS.read_text(encoding="utf-8").splitlines():
        workflow_match = re.match(r"^    ([A-Z_]+): \{$", line)
        if workflow_match:
            current_workflow = workflow_match.group(1)
            workflows[current_workflow] = []
            in_stages = False
            continue

        if current_workflow is None:
            continue

        if line.strip() == "stages: [":
            in_stages = True
            continue

        if in_stages and line.strip() == "],":
            in_stages = False
            continue

        if in_stages:
            stage_match = re.match(r"^\s+id: '([A-Z_]+)',$", line)
            if stage_match:
                workflows[current_workflow].append(stage_match.group(1))

    return workflows


def test_backend_workflow_stage_contract_matches_frontend_workflow_config():
    frontend_stages = _frontend_workflow_stages()

    assert frontend_stages == WORKFLOW_STAGES


def test_required_artifact_contracts_match_frontend_workflow_stages():
    frontend_stage_keys = {
        (workflow_id, stage_id)
        for workflow_id, stage_ids in _frontend_workflow_stages().items()
        for stage_id in stage_ids
    }

    assert set(REQUIRED_ARTIFACT_HEADINGS) == frontend_stage_keys
