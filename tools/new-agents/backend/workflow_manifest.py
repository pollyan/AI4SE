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


def get_workflow_handoffs() -> list[dict[str, Any]]:
    handoffs = load_workflow_manifest().get("handoffs", [])
    if not isinstance(handoffs, list):
        raise ValueError("workflow manifest handoffs 必须是数组")
    return handoffs
