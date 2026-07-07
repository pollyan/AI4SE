from workflow_contract_registry import (
    get_required_artifact_headings,
    get_required_artifact_mermaid_diagrams,
    get_required_artifact_structured_visuals,
    get_stage_prompt_template_ids,
    get_workflow_stages,
)
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
        "USER_STORY_BREAKDOWN": ["SCOPE", "STORY_MAP", "STORIES", "HANDOFF"],
    }


def test_registry_requires_prompt_template_id_for_every_stage():
    prompt_template_ids = get_stage_prompt_template_ids()

    assert prompt_template_ids[("TEST_DESIGN", "CLARIFY")] == "test_design.clarify"
    assert prompt_template_ids[("IDEA_BRAINSTORM", "DIVERGE")] == "idea_brainstorm.diverge"
    assert prompt_template_ids[("VALUE_DISCOVERY", "PERSONA")] == "value_discovery.persona"
    assert (
        prompt_template_ids[("USER_STORY_BREAKDOWN", "STORY_MAP")]
        == "user_story_breakdown.story_map"
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
