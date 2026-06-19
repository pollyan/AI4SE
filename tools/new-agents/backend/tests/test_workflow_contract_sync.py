import json
from pathlib import Path

from agent_contracts import (
    REQUIRED_ARTIFACT_HEADINGS,
    REQUIRED_ARTIFACT_MERMAID_DIAGRAMS,
    REQUIRED_ARTIFACT_STRUCTURED_VISUALS,
    WORKFLOW_STAGES,
)


NEW_AGENTS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOW_MANIFEST = NEW_AGENTS_ROOT / "workflow_manifest.json"


def _workflow_manifest_stages() -> dict[str, list[str]]:
    manifest = json.loads(WORKFLOW_MANIFEST.read_text(encoding="utf-8"))
    workflows = manifest["workflows"]
    return {
        workflow_id: [
            stage["id"]
            for stage in workflow["stages"]
        ]
        for workflow_id, workflow in workflows.items()
    }


def _workflow_manifest() -> dict:
    return json.loads(WORKFLOW_MANIFEST.read_text(encoding="utf-8"))


def test_shared_workflow_manifest_stage_order_matches_backend_contract():
    assert _workflow_manifest_stages() == WORKFLOW_STAGES


def test_shared_workflow_manifest_stage_keys_match_required_artifact_contracts():
    manifest_stage_keys = {
        (workflow_id, stage_id)
        for workflow_id, stage_ids in _workflow_manifest_stages().items()
        for stage_id in stage_ids
    }

    assert manifest_stage_keys == set(REQUIRED_ARTIFACT_HEADINGS)


def test_shared_workflow_manifest_declares_alex_to_lisa_handoffs():
    handoffs = _workflow_manifest()["handoffs"]

    assert {
        (
            handoff["sourceWorkflowId"],
            handoff["sourceStageId"],
            handoff["targetWorkflowId"],
            handoff["targetStageId"],
        )
        for handoff in handoffs
    } >= {
        ("VALUE_DISCOVERY", "BLUEPRINT", "TEST_DESIGN", "CLARIFY"),
        ("VALUE_DISCOVERY", "BLUEPRINT", "REQ_REVIEW", "REVIEW"),
    }


def test_shared_workflow_manifest_handoffs_reference_known_workflows_and_stages():
    manifest = _workflow_manifest()
    workflow_stages = _workflow_manifest_stages()

    for handoff in manifest["handoffs"]:
        source_workflow = handoff["sourceWorkflowId"]
        target_workflow = handoff["targetWorkflowId"]
        assert source_workflow in workflow_stages
        assert target_workflow in workflow_stages
        assert handoff["sourceStageId"] in workflow_stages[source_workflow]
        assert handoff["targetStageId"] in workflow_stages[target_workflow]
        assert handoff["targetAgentId"] == manifest["workflows"][target_workflow]["agentId"]


def test_backend_container_packages_shared_workflow_manifest():
    dockerfile = (
        NEW_AGENTS_ROOT / "backend" / "docker" / "Dockerfile"
    ).read_text(encoding="utf-8")
    dev_compose = (REPO_ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")
    dev_cn_compose = (REPO_ROOT / "docker-compose.dev-cn.yml").read_text(encoding="utf-8")

    assert "COPY tools/new-agents/workflow_manifest.json /workflow_manifest.json" in dockerfile
    assert "./tools/new-agents/workflow_manifest.json:/workflow_manifest.json:ro" in dev_compose
    assert "./tools/new-agents/workflow_manifest.json:/workflow_manifest.json:ro" in dev_cn_compose


def test_frontend_templates_include_required_structured_visual_contract_examples():
    prompt_files = {
        ("REQ_REVIEW", "REVIEW"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "req_review"
            / "review.ts"
        ),
        ("REQ_REVIEW", "REPORT"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "req_review"
            / "report.ts"
        ),
        ("TEST_DESIGN", "CASES"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "test_design"
            / "cases.ts"
        ),
        ("TEST_DESIGN", "DELIVERY"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "test_design"
            / "delivery.ts"
        ),
        ("TEST_DESIGN", "STRATEGY"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "test_design"
            / "strategy.ts"
        ),
        ("INCIDENT_REVIEW", "IMPROVEMENT"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "incident_review"
            / "improvement.ts"
        ),
        ("INCIDENT_REVIEW", "ROOT_CAUSE"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "incident_review"
            / "root_cause.ts"
        ),
        ("IDEA_BRAINSTORM", "CONCEPT"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "idea_brainstorm"
            / "concept.ts"
        ),
        ("VALUE_DISCOVERY", "ELEVATOR"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "value_discovery"
            / "elevator.ts"
        ),
        ("VALUE_DISCOVERY", "JOURNEY"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "value_discovery"
            / "journey.ts"
        ),
        ("VALUE_DISCOVERY", "BLUEPRINT"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "value_discovery"
            / "blueprint.ts"
        ),
    }

    for stage_key, visual_types in REQUIRED_ARTIFACT_STRUCTURED_VISUALS.items():
        template = prompt_files[stage_key].read_text(encoding="utf-8")
        rendered_template_section = template.split("TEMPLATE = ", maxsplit=1)[1]

        for visual_type in visual_types:
            assert (
                "```ai4se-visual" in template
                or "${FENCE}ai4se-visual" in template
            )
            assert f'"type": "{visual_type}"' in template
            assert '"columns"' in template
            assert '"rows"' in template
            assert "fenced:ai4se-visual" not in rendered_template_section
            assert '"data"' not in rendered_template_section
            assert '"matrix"' not in rendered_template_section


def test_frontend_templates_include_required_mermaid_diagram_examples():
    prompt_files = {
        ("TEST_DESIGN", "CLARIFY"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "test_design"
            / "clarify.ts"
        ),
        ("TEST_DESIGN", "STRATEGY"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "test_design"
            / "strategy.ts"
        ),
        ("REQ_REVIEW", "REPORT"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "req_review"
            / "report.ts"
        ),
        ("INCIDENT_REVIEW", "TIMELINE"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "incident_review"
            / "timeline.ts"
        ),
        ("INCIDENT_REVIEW", "ROOT_CAUSE"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "incident_review"
            / "root_cause.ts"
        ),
        ("INCIDENT_REVIEW", "IMPROVEMENT"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "incident_review"
            / "improvement.ts"
        ),
        ("IDEA_BRAINSTORM", "DEFINE"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "idea_brainstorm"
            / "define.ts"
        ),
        ("IDEA_BRAINSTORM", "CONVERGE"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "idea_brainstorm"
            / "converge.ts"
        ),
        ("VALUE_DISCOVERY", "JOURNEY"): (
            NEW_AGENTS_ROOT
            / "frontend"
            / "src"
            / "core"
            / "prompts"
            / "value_discovery"
            / "journey.ts"
        ),
    }

    assert set(prompt_files) == set(REQUIRED_ARTIFACT_MERMAID_DIAGRAMS)
    for stage_key, diagram_types in REQUIRED_ARTIFACT_MERMAID_DIAGRAMS.items():
        template = prompt_files[stage_key].read_text(encoding="utf-8")

        assert "mermaid" in template
        for diagram_type in diagram_types:
            assert diagram_type in template
