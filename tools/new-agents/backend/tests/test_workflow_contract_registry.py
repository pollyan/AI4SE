from workflow_contract_registry import (
    get_stage_prompt_template_ids,
    get_workflow_stages,
)


def test_registry_derives_workflow_stages_from_manifest():
    assert get_workflow_stages() == {
        "TEST_DESIGN": ["CLARIFY", "STRATEGY", "CASES", "DELIVERY"],
        "REQ_REVIEW": ["REVIEW", "REPORT"],
        "INCIDENT_REVIEW": ["TIMELINE", "ROOT_CAUSE", "IMPROVEMENT"],
        "IDEA_BRAINSTORM": ["DEFINE", "DIVERGE", "CONVERGE", "CONCEPT"],
        "VALUE_DISCOVERY": ["ELEVATOR", "PERSONA", "JOURNEY", "BLUEPRINT"],
    }


def test_registry_requires_prompt_template_id_for_every_stage():
    prompt_template_ids = get_stage_prompt_template_ids()

    assert prompt_template_ids[("TEST_DESIGN", "CLARIFY")] == "test_design.clarify"
    assert prompt_template_ids[("IDEA_BRAINSTORM", "DIVERGE")] == "idea_brainstorm.diverge"
    assert prompt_template_ids[("VALUE_DISCOVERY", "PERSONA")] == "value_discovery.persona"
    assert set(prompt_template_ids) == {
        (workflow_id, stage_id)
        for workflow_id, stage_ids in get_workflow_stages().items()
        for stage_id in stage_ids
    }
