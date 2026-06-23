import json
import re
from pathlib import Path

from agent_contracts import (
    REQUIRED_ARTIFACT_HEADINGS,
    REQUIRED_ARTIFACT_MERMAID_DIAGRAMS,
    REQUIRED_ARTIFACT_STRUCTURED_VISUALS,
    WORKFLOW_STAGES,
)
from scripts.validation.new_agents_workflow_dry_run import (
    load_workflow_dry_run_inputs,
)
from workflow_handoffs import HANDOFF_PROMPT_TEMPLATES

NEW_AGENTS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOW_MANIFEST = NEW_AGENTS_ROOT / "workflow_manifest.json"
PROFESSIONAL_METHODS = NEW_AGENTS_ROOT / "professional_methods.json"
PROMPT_REGRESSION_SAMPLES = NEW_AGENTS_ROOT / "prompt_regression_samples.json"
PROMPT_TEMPLATE_VERSION_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}\.\d+$")
DRY_RUN_INPUTS = load_workflow_dry_run_inputs(REPO_ROOT)
FRONTEND_PROMPT_FILES = DRY_RUN_INPUTS.prompt_files_by_stage


def _workflow_manifest_stages() -> dict[str, list[str]]:
    manifest = json.loads(WORKFLOW_MANIFEST.read_text(encoding="utf-8"))
    workflows = manifest["workflows"]
    return {
        workflow_id: [stage["id"] for stage in workflow["stages"]]
        for workflow_id, workflow in workflows.items()
    }


def _workflow_manifest() -> dict:
    return json.loads(WORKFLOW_MANIFEST.read_text(encoding="utf-8"))


def _professional_methods() -> dict:
    return json.loads(PROFESSIONAL_METHODS.read_text(encoding="utf-8"))


def _prompt_regression_samples() -> dict:
    return json.loads(PROMPT_REGRESSION_SAMPLES.read_text(encoding="utf-8"))


def test_shared_workflow_manifest_stage_order_matches_backend_contract():
    assert _workflow_manifest_stages() == WORKFLOW_STAGES


def test_story_breakdown_is_declared_as_shared_runtime_workflow():
    manifest = _workflow_manifest()
    workflow = manifest["workflows"]["STORY_BREAKDOWN"]

    assert workflow["agentId"] == "alex"
    assert workflow["slug"] == "story-breakdown"
    assert [stage["id"] for stage in workflow["stages"]] == [
        "INPUT_ANALYSIS",
        "EPIC_MAPPING",
        "STORY_BACKLOG",
        "SPRINT_PLAN",
    ]


def test_prd_review_manifest_and_backend_contract_are_synchronized():
    manifest = _workflow_manifest()
    workflow = manifest["workflows"]["PRD_REVIEW"]

    assert workflow["agentId"] == "alex"
    assert workflow["slug"] == "prd-review"
    assert WORKFLOW_STAGES["PRD_REVIEW"] == [
        "INVENTORY",
        "QUALITY_AUDIT",
        "COMPLETION_PLAN",
        "REVISION_BLUEPRINT",
    ]
    assert [stage["id"] for stage in workflow["stages"]] == [
        "INVENTORY",
        "QUALITY_AUDIT",
        "COMPLETION_PLAN",
        "REVISION_BLUEPRINT",
    ]


def test_shared_workflow_manifest_stage_keys_match_required_artifact_contracts():
    manifest_stage_keys = {
        (workflow_id, stage_id)
        for workflow_id, stage_ids in _workflow_manifest_stages().items()
        for stage_id in stage_ids
    }

    assert manifest_stage_keys == set(REQUIRED_ARTIFACT_HEADINGS)


def test_shared_workflow_manifest_stage_keys_match_frontend_prompt_templates():
    manifest_stage_keys = {
        (workflow_id, stage_id)
        for workflow_id, stage_ids in _workflow_manifest_stages().items()
        for stage_id in stage_ids
    }

    assert manifest_stage_keys == set(FRONTEND_PROMPT_FILES)


def test_professional_method_registry_has_required_fields():
    methods = _professional_methods()["methods"]

    assert {method["id"] for method in methods} >= {
        "fmea",
        "test_pyramid",
        "jtbd",
        "rice",
        "kano",
        "capa",
        "ice",
    }
    for method in methods:
        assert method["id"].strip()
        assert method["name"].strip()
        assert method["description"].strip()
        assert method["guidance"].strip()


def test_workflow_manifest_professional_method_ids_are_known():
    known_method_ids = {method["id"] for method in _professional_methods()["methods"]}
    manifest = _workflow_manifest()

    for workflow_id, workflow in manifest["workflows"].items():
        for stage in workflow["stages"]:
            for method_id in stage.get("methodIds", []):
                assert (
                    method_id in known_method_ids
                ), f"{workflow_id}/{stage['id']} references unknown method {method_id}"


def test_representative_stages_declare_professional_methods():
    manifest = _workflow_manifest()

    expected = {
        ("TEST_DESIGN", "STRATEGY"): {"fmea", "test_pyramid"},
        ("INCIDENT_REVIEW", "IMPROVEMENT"): {"capa"},
        ("VALUE_DISCOVERY", "JOURNEY"): {"jtbd", "rice", "kano"},
        ("IDEA_BRAINSTORM", "CONVERGE"): {"ice"},
    }

    for (workflow_id, stage_id), method_ids in expected.items():
        stage = next(
            stage
            for stage in manifest["workflows"][workflow_id]["stages"]
            if stage["id"] == stage_id
        )
        assert set(stage.get("methodIds", [])) >= method_ids


def test_workflow_manifest_declares_prompt_template_versions_for_every_stage():
    manifest = _workflow_manifest()

    for workflow_id, workflow in manifest["workflows"].items():
        for stage in workflow["stages"]:
            version = stage.get("promptTemplateVersion")
            assert isinstance(version, str), (
                f"{workflow_id}/{stage['id']} missing promptTemplateVersion"
            )
            assert PROMPT_TEMPLATE_VERSION_RE.match(version), (
                f"{workflow_id}/{stage['id']} has invalid promptTemplateVersion: {version}"
            )


def test_workflow_manifest_declares_regression_samples_for_every_stage():
    known_sample_ids = {
        sample["id"]
        for sample in _prompt_regression_samples()["samples"]
    }
    manifest = _workflow_manifest()

    for workflow_id, workflow in manifest["workflows"].items():
        for stage in workflow["stages"]:
            sample_ids = stage.get("regressionSampleIds")
            assert isinstance(sample_ids, list) and sample_ids, (
                f"{workflow_id}/{stage['id']} missing regressionSampleIds"
            )
            for sample_id in sample_ids:
                assert sample_id in known_sample_ids, (
                    f"{workflow_id}/{stage['id']} references unknown regression sample {sample_id}"
                )


def test_prompt_regression_samples_reference_known_workflow_stages():
    workflow_stages = _workflow_manifest_stages()
    samples = _prompt_regression_samples()["samples"]

    for sample in samples:
        workflow_id = sample["workflowId"]
        stage_id = sample["stageId"]
        assert workflow_id in workflow_stages
        assert stage_id in workflow_stages[workflow_id]
        assert sample["input"].strip()
        assert sample["expectedFocus"]
        assert sample["acceptanceChecks"]


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
        ("STORY_BREAKDOWN", "SPRINT_PLAN", "TEST_DESIGN", "CLARIFY"),
        ("STORY_BREAKDOWN", "SPRINT_PLAN", "REQ_REVIEW", "REVIEW"),
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
        assert (
            handoff["targetAgentId"]
            == manifest["workflows"][target_workflow]["agentId"]
        )


def test_shared_workflow_manifest_handoffs_declare_prompt_templates():
    manifest = _workflow_manifest()

    for handoff in manifest["handoffs"]:
        assert handoff.get("promptTemplateId") in HANDOFF_PROMPT_TEMPLATES


def test_backend_container_packages_shared_workflow_manifest():
    dockerfile = (NEW_AGENTS_ROOT / "backend" / "docker" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    dev_compose = (REPO_ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")
    dev_cn_compose = (REPO_ROOT / "docker-compose.dev-cn.yml").read_text(
        encoding="utf-8"
    )

    assert "COPY tools/new-agents/workflow_manifest.json /workflow_manifest.json" in dockerfile
    assert "COPY tools/new-agents/professional_methods.json /professional_methods.json" in dockerfile
    assert "COPY tools/new-agents/prompt_regression_samples.json /prompt_regression_samples.json" in dockerfile
    assert "./tools/new-agents/workflow_manifest.json:/workflow_manifest.json:ro" in dev_compose
    assert "./tools/new-agents/workflow_manifest.json:/workflow_manifest.json:ro" in dev_cn_compose
    assert "./tools/new-agents/professional_methods.json:/professional_methods.json:ro" in dev_compose
    assert "./tools/new-agents/professional_methods.json:/professional_methods.json:ro" in dev_cn_compose
    assert "./tools/new-agents/prompt_regression_samples.json:/prompt_regression_samples.json:ro" in dev_compose
    assert "./tools/new-agents/prompt_regression_samples.json:/prompt_regression_samples.json:ro" in dev_cn_compose


def test_frontend_container_packages_shared_workflow_manifest_for_vite_build():
    dockerfile = (NEW_AGENTS_ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY tools/new-agents/workflow_manifest.json /workflow_manifest.json" in dockerfile
    assert "COPY tools/new-agents/professional_methods.json /professional_methods.json" in dockerfile
    assert "COPY tools/new-agents/prompt_regression_samples.json /prompt_regression_samples.json" in dockerfile
    assert "COPY tools/new-agents/workflow_manifest.json ./workflow_manifest.json" in dockerfile
    assert "COPY tools/new-agents/professional_methods.json ./professional_methods.json" in dockerfile
    assert "COPY tools/new-agents/prompt_regression_samples.json ./prompt_regression_samples.json" in dockerfile


def test_frontend_templates_include_required_structured_visual_contract_examples():
    for stage_key, visual_types in REQUIRED_ARTIFACT_STRUCTURED_VISUALS.items():
        template = FRONTEND_PROMPT_FILES[stage_key].read_text(encoding="utf-8")
        rendered_template_section = template.split("TEMPLATE = ", maxsplit=1)[1]

        for visual_type in visual_types:
            assert "```ai4se-visual" in template or "${FENCE}ai4se-visual" in template
            assert f'"type": "{visual_type}"' in template
            assert '"columns"' in template
            assert '"rows"' in template
            assert "fenced:ai4se-visual" not in rendered_template_section
            assert '"data"' not in rendered_template_section
            assert '"matrix"' not in rendered_template_section


def test_frontend_templates_include_required_mermaid_diagram_examples():
    for stage_key, diagram_types in REQUIRED_ARTIFACT_MERMAID_DIAGRAMS.items():
        template = FRONTEND_PROMPT_FILES[stage_key].read_text(encoding="utf-8")

        assert "mermaid" in template
        for diagram_type in diagram_types:
            assert diagram_type in template
