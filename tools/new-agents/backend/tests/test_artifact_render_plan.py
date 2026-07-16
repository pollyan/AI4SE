import copy
from itertools import pairwise

import pytest
from pydantic import Field, ValidationError

from agent_contracts import validate_artifact_visual_blocks
from artifact_data_renderer_base import StrictArtifactDataModel, render_compact_metadata
from artifact_data_renderers import (
    ARTIFACT_DATA_RENDERERS,
    get_artifact_render_plan_business_section_ids,
    get_artifact_render_plan_stage_keys,
    render_available_artifact_data,
    render_complete_artifact_data,
)
from artifact_render_plan import ArtifactRenderPlan, ArtifactSectionSpec
from agent_contracts import REQUIRED_ARTIFACT_HEADINGS, WORKFLOW_STAGES
from test_artifact_data_renderers import (
    ARTIFACT_DATA_STAGE_FIXTURES,
    VALID_CASES_ARTIFACT_DATA,
    VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA,
    VALID_REQ_REVIEW_ARTIFACT_DATA,
    VALID_STRATEGY_ARTIFACT_DATA,
)


def test_req_review_render_plan_reveals_business_context_before_later_sections():
    fixture = copy.deepcopy(VALID_REQ_REVIEW_ARTIFACT_DATA)

    review_info = render_available_artifact_data(
        {"review_info": fixture["review_info"]},
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )
    scope = render_available_artifact_data(
        {
            "review_info": fixture["review_info"],
            "scope_items": fixture["scope_items"],
        },
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )
    overview = render_available_artifact_data(
        {
            "review_info": fixture["review_info"],
            "scope_items": fixture["scope_items"],
            "quality_overview": fixture["quality_overview"],
        },
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )

    assert review_info is not None
    assert scope is not None
    assert overview is not None
    assert "## 评审上下文" in review_info.markdown
    assert "## 评审范围与不评审范围" not in review_info.markdown
    assert "## 评审范围与不评审范围" in scope.markdown
    assert "## 需求质量总览" not in scope.markdown
    assert "## 需求质量总览" in overview.markdown
    assert set(review_info.completed_section_ids) < set(scope.completed_section_ids)
    assert set(scope.completed_section_ids) < set(overview.completed_section_ids)
    validate_artifact_visual_blocks(review_info.markdown)
    validate_artifact_visual_blocks(scope.markdown)
    validate_artifact_visual_blocks(overview.markdown)


def test_partial_field_validation_preserves_top_level_field_constraints():
    rendered = render_available_artifact_data(
        {"requirement_facts": []},
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert rendered is None


def test_partial_field_validation_reuses_parent_blank_string_rule():
    rendered = render_available_artifact_data(
        {"elevator_pitch": "   "},
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert rendered is None


def test_metadata_only_partial_does_not_emit_an_artifact():
    fixture = ARTIFACT_DATA_STAGE_FIXTURES[("TEST_DESIGN", "CLARIFY")]

    rendered = render_available_artifact_data(
        {"document_info": copy.deepcopy(fixture["document_info"])},
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert rendered is None


def test_req_review_render_plan_converges_exactly_to_complete_renderer():
    available = render_available_artifact_data(
        copy.deepcopy(VALID_REQ_REVIEW_ARTIFACT_DATA),
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )
    complete = render_complete_artifact_data(
        copy.deepcopy(VALID_REQ_REVIEW_ARTIFACT_DATA),
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )

    assert available is not None
    assert available.markdown == complete.markdown
    assert available.completed_section_ids == complete.completed_section_ids
    assert complete.normalized_artifact_data == VALID_REQ_REVIEW_ARTIFACT_DATA


def test_req_review_invalid_consistency_group_is_withheld_but_full_render_fails():
    fixture = copy.deepcopy(VALID_REQ_REVIEW_ARTIFACT_DATA)
    fixture["issue_statistics"]["p0_count"] = 99

    available = render_available_artifact_data(
        fixture,
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )

    assert available is not None
    assert "## 评审范围与不评审范围" in available.markdown
    assert "## 需求质量总览" in available.markdown
    assert "## 问题统计" not in available.markdown
    assert "## 按维度问题清单" in available.markdown
    assert "## 修订建议" in available.markdown
    assert "## 阶段门禁" in available.markdown

    with pytest.raises(ValidationError, match="issue_statistics"):
        render_complete_artifact_data(
            fixture,
            workflow_id="REQ_REVIEW",
            current_stage_id="REVIEW",
        )


def test_artifact_render_plans_cover_every_online_stage():
    online_stage_keys = {
        (workflow_id, stage_id)
        for workflow_id, stages in WORKFLOW_STAGES.items()
        for stage_id in stages
    }

    assert set(get_artifact_render_plan_stage_keys()) == online_stage_keys
    assert set(ARTIFACT_DATA_STAGE_FIXTURES) == online_stage_keys


def test_cases_full_contract_requires_a_checked_stage_gate_item():
    fixture = copy.deepcopy(VALID_CASES_ARTIFACT_DATA)
    for item in fixture["stage_gate"]:
        item["checked"] = False

    with pytest.raises(ValidationError, match="stage_gate"):
        render_complete_artifact_data(
            fixture,
            workflow_id="TEST_DESIGN",
            current_stage_id="CASES",
        )


def test_invalid_cases_gate_withholds_only_gate_section_from_available_artifact():
    fixture = copy.deepcopy(VALID_CASES_ARTIFACT_DATA)
    for item in fixture["stage_gate"]:
        item["checked"] = False

    available = render_available_artifact_data(
        fixture,
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert available is not None
    assert "case-statistics" in available.completed_section_ids
    assert "case-groups" in available.completed_section_ids
    assert "automation-candidates" in available.completed_section_ids
    assert "stage-gate" not in available.completed_section_ids


def test_strategy_unknown_reference_withholds_only_dependent_section():
    fixture = copy.deepcopy(VALID_STRATEGY_ARTIFACT_DATA)
    fixture["test_points"][0]["quality_goal"] = "QG-404"

    available = render_available_artifact_data(
        fixture,
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert available is not None
    assert "## 1. 策略摘要" in available.markdown
    assert "## 2. 质量目标" in available.markdown
    assert "## 3. 风险" in available.markdown
    assert "## 4. 测试技术" in available.markdown
    assert "test-points" not in available.completed_section_ids
    assert "tradeoffs" in available.completed_section_ids
    assert "stage-gate" in available.completed_section_ids

    with pytest.raises(ValidationError, match="test_points references unknown"):
        render_complete_artifact_data(
            fixture,
            workflow_id="TEST_DESIGN",
            current_stage_id="STRATEGY",
        )


@pytest.mark.parametrize(
    ("workflow_id", "stage_id", "fixture_key", "mutate", "section_id"),
    [
        (
            "INCIDENT_REVIEW",
            "ROOT_CAUSE",
            ("INCIDENT_REVIEW", "ROOT_CAUSE"),
            lambda fixture: fixture["cause_evidence"][0].__setitem__(
                "related_level", "Why-404"
            ),
            "cause-evidence",
        ),
        (
            "STORY_BREAKDOWN",
            "STORY_BACKLOG",
            ("STORY_BREAKDOWN", "STORY_BACKLOG"),
            lambda fixture: fixture["user_stories"][0].__setitem__(
                "epic_id", "EPIC-404"
            ),
            "story-backlog",
        ),
        (
            "VALUE_DISCOVERY",
            "ELEVATOR",
            ("VALUE_DISCOVERY", "ELEVATOR"),
            lambda fixture: fixture["value_flow"]["links"][0].__setitem__(
                "to_node", "MISSING"
            ),
            "value-flow",
        ),
        (
            "IDEA_BRAINSTORM",
            "DEFINE",
            ("IDEA_BRAINSTORM", "DEFINE"),
            lambda fixture: fixture["problem_user_fit"][0]["evidence_ids"].append(
                "EV-404"
            ),
            "problem-user-fit",
        ),
        (
            "IDEA_BRAINSTORM",
            "DIVERGE",
            ("IDEA_BRAINSTORM", "DIVERGE"),
            lambda fixture: fixture["idea_landscape"]["groups"][0]["idea_ids"].append(
                "ID-404"
            ),
            "idea-landscape",
        ),
        (
            "IDEA_BRAINSTORM",
            "DIVERGE",
            ("IDEA_BRAINSTORM", "DIVERGE"),
            lambda fixture: fixture["idea_sources"][0]["idea_ids"].append("ID-404"),
            "idea-sources",
        ),
        (
            "IDEA_BRAINSTORM",
            "CONVERGE",
            ("IDEA_BRAINSTORM", "CONVERGE"),
            lambda fixture: fixture["decision_matrix"].__setitem__(
                "recommended_idea_id", "ID-404"
            ),
            "decision-matrix",
        ),
        (
            "IDEA_BRAINSTORM",
            "CONVERGE",
            ("IDEA_BRAINSTORM", "CONVERGE"),
            lambda fixture: fixture["validation_experiments"][0]["idea_ids"].append(
                "ID-404"
            ),
            "validation-experiments",
        ),
        (
            "IDEA_BRAINSTORM",
            "CONCEPT",
            ("IDEA_BRAINSTORM", "CONCEPT"),
            lambda fixture: fixture["mvp_features"][0]["assumption_ids"].append(
                "H-404"
            ),
            "mvp-features",
        ),
        (
            "IDEA_BRAINSTORM",
            "CONCEPT",
            ("IDEA_BRAINSTORM", "CONCEPT"),
            lambda fixture: fixture["next_actions"][0]["related_ids"].append("MISSING"),
            "next-actions",
        ),
        (
            "INCIDENT_REVIEW",
            "TIMELINE",
            ("INCIDENT_REVIEW", "TIMELINE"),
            lambda fixture: fixture["timeline_events"][0]["fact_ids"].append(
                "FACT-404"
            ),
            "timeline",
        ),
        (
            "INCIDENT_REVIEW",
            "ROOT_CAUSE",
            ("INCIDENT_REVIEW", "ROOT_CAUSE"),
            lambda fixture: fixture["fishbone_categories"][0]["cause_ids"].append(
                "CAUSE-404"
            ),
            "fishbone",
        ),
        (
            "INCIDENT_REVIEW",
            "IMPROVEMENT",
            ("INCIDENT_REVIEW", "IMPROVEMENT"),
            lambda fixture: fixture["root_cause_coverage"][0]["action_ids"].append(
                "A-404"
            ),
            "root-cause-coverage",
        ),
        (
            "REQ_REVIEW",
            "REPORT",
            ("REQ_REVIEW", "REPORT"),
            lambda fixture: fixture["review_conditions"][0]["related_issues"].append(
                "Q-404"
            ),
            "review-conditions",
        ),
        (
            "PRD_REVIEW",
            "COMPLETION_PLAN",
            ("PRD_REVIEW", "COMPLETION_PLAN"),
            lambda fixture: fixture["completion_actions"][0]["finding_ids"].append(
                "FIND-404"
            ),
            "completion-actions",
        ),
        (
            "PRD_REVIEW",
            "REVISION_BLUEPRINT",
            ("PRD_REVIEW", "REVISION_BLUEPRINT"),
            lambda fixture: fixture["acceptance_criteria"][0][
                "related_section_ids"
            ].append("SEC-404"),
            "acceptance-criteria",
        ),
        (
            "VALUE_DISCOVERY",
            "PERSONA",
            ("VALUE_DISCOVERY", "PERSONA"),
            lambda fixture: fixture["behavior_scenarios"][0].__setitem__(
                "persona_id", "PER-404"
            ),
            "behavior-scenarios",
        ),
        (
            "VALUE_DISCOVERY",
            "JOURNEY",
            ("VALUE_DISCOVERY", "JOURNEY"),
            lambda fixture: fixture["pain_priorities"][0].__setitem__(
                "stage_id", "JS-404"
            ),
            "pain-priorities",
        ),
        (
            "VALUE_DISCOVERY",
            "BLUEPRINT",
            ("VALUE_DISCOVERY", "BLUEPRINT"),
            lambda fixture: fixture["mvp_plan"]["included_features"][0].__setitem__(
                "requirement_id", "F-404"
            ),
            "mvp-plan",
        ),
        (
            "STORY_BREAKDOWN",
            "STORY_BACKLOG",
            ("STORY_BREAKDOWN", "STORY_BACKLOG"),
            lambda fixture: fixture["acceptance_criteria"][0].__setitem__(
                "story_id", "US-404"
            ),
            "acceptance-criteria",
        ),
        (
            "STORY_BREAKDOWN",
            "STORY_BACKLOG",
            ("STORY_BREAKDOWN", "STORY_BACKLOG"),
            lambda fixture: fixture["dependencies"][0]["related_story_ids"].append(
                "US-404"
            ),
            "dependencies",
        ),
        (
            "STORY_BREAKDOWN",
            "STORY_BACKLOG",
            ("STORY_BREAKDOWN", "STORY_BACKLOG"),
            lambda fixture: fixture["sprint_slices"][0]["story_ids"].append("US-404"),
            "sprint-slices",
        ),
        (
            "STORY_BREAKDOWN",
            "STORY_BACKLOG",
            ("STORY_BREAKDOWN", "STORY_BACKLOG"),
            lambda fixture: fixture["lisa_handoff_inputs"][0].__setitem__(
                "reference_id", "US-404"
            ),
            "lisa-handoff-inputs",
        ),
    ],
)
def test_invalid_cross_reference_withholds_dependent_partial_section(
    workflow_id: str,
    stage_id: str,
    fixture_key: tuple[str, str],
    mutate,
    section_id: str,
):
    fixture = copy.deepcopy(ARTIFACT_DATA_STAGE_FIXTURES[fixture_key])
    mutate(fixture)

    available = render_available_artifact_data(
        fixture,
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )

    assert available is not None
    assert section_id not in available.completed_section_ids

    with pytest.raises(ValidationError):
        render_complete_artifact_data(
            fixture,
            workflow_id=workflow_id,
            current_stage_id=stage_id,
        )


class _VisualIsolationArtifactData(StrictArtifactDataModel):
    before: str = Field(min_length=1)
    invalid_visual: str = Field(min_length=1)
    after: str = Field(min_length=1)


class _MetadataOrderingArtifactData(StrictArtifactDataModel):
    metadata: str = Field(min_length=1)
    business: str = Field(min_length=1)


def _metadata_ordering_section(
    section_id: str,
    field_name: str,
    *,
    role: str = "business",
) -> ArtifactSectionSpec:
    return ArtifactSectionSpec(
        section_id=section_id,
        dependencies=(field_name,),
        render=lambda data: f"## {section_id}\n\n{getattr(data, field_name)}",
        role=role,
    )


@pytest.mark.parametrize(
    "sections",
    [
        (
            _metadata_ordering_section("business", "business"),
            _metadata_ordering_section("unknown", "metadata", role="unknown"),
        ),
        (
            _metadata_ordering_section("duplicate", "business"),
            _metadata_ordering_section("duplicate", "metadata", role="metadata"),
        ),
        (_metadata_ordering_section("metadata", "metadata", role="metadata"),),
    ],
)
def test_render_plan_rejects_invalid_section_role_configuration(sections):
    with pytest.raises(ValueError, match="role|duplicate|business"):
        ArtifactRenderPlan(
            model=_MetadataOrderingArtifactData,
            title=lambda _data: "# Metadata ordering probe",
            title_dependencies=(),
            sections=sections,
        )


def test_render_plan_uses_business_then_metadata_as_one_canonical_order():
    plan = ArtifactRenderPlan(
        model=_MetadataOrderingArtifactData,
        title=lambda _data: "# Metadata ordering probe",
        title_dependencies=(),
        sections=(
            _metadata_ordering_section("metadata", "metadata", role="metadata"),
            _metadata_ordering_section("business", "business"),
        ),
    )

    partial = plan.render_available({"metadata": "meta", "business": "value"})
    complete = plan.render_complete({"metadata": "meta", "business": "value"})

    assert partial is not None
    assert partial.completed_section_ids == ("business", "metadata")
    assert partial.markdown.index("## business") < partial.markdown.index("## metadata")
    assert partial.markdown == complete.markdown
    assert partial.completed_section_ids == complete.completed_section_ids


def test_compact_metadata_rejects_invalid_heading_and_escapes_inline_markup():
    with pytest.raises(ValueError, match="H1-H3"):
        render_compact_metadata("文档信息", (("字段", "值"),))

    rendered = render_compact_metadata(
        "## 文档信息",
        (("Artifact 名称", "<script>*unsafe*</script> | _draft_ ~~old~~ &copy;"),),
    )

    assert rendered.startswith("## 文档信息\n文档元信息：")
    assert (
        "&lt;script&gt;&#42;unsafe&#42;&lt;/script&gt; &#124; "
        "&#95;draft&#95; &#126;&#126;old&#126;&#126; &amp;copy;"
    ) in rendered
    assert "\n|" not in rendered


@pytest.mark.parametrize(
    ("stage_key", "wrong_workflow", "wrong_stage"),
    [
        (("STORY_BREAKDOWN", "INPUT_ANALYSIS"), "STORY_BREAKDOWN", "SPRINT_PLAN"),
        (("PRD_REVIEW", "INVENTORY"), "PRD_REVIEW", "REVISION_BLUEPRINT"),
        (("TEST_DESIGN", "CLARIFY"), "REQ_REVIEW", "CLARIFY"),
    ],
)
def test_document_info_identity_must_match_runtime_stage(
    stage_key: tuple[str, str],
    wrong_workflow: str,
    wrong_stage: str,
):
    workflow_id, stage_id = stage_key
    fixture = copy.deepcopy(ARTIFACT_DATA_STAGE_FIXTURES[stage_key])
    fixture["document_info"]["workflow"] = wrong_workflow
    fixture["document_info"]["stage"] = wrong_stage

    with pytest.raises(ValueError, match="document_info identity"):
        render_complete_artifact_data(
            fixture,
            workflow_id=workflow_id,
            current_stage_id=stage_id,
        )

    with pytest.raises(ValueError, match="document_info identity"):
        render_available_artifact_data(
            fixture,
            workflow_id=workflow_id,
            current_stage_id=stage_id,
        )


def test_clarify_renders_business_first_and_compact_document_metadata_last():
    fixture = copy.deepcopy(ARTIFACT_DATA_STAGE_FIXTURES[("TEST_DESIGN", "CLARIFY")])

    rendered = render_complete_artifact_data(
        fixture,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert rendered.markdown.index("## 1. 需求事实清单") < rendered.markdown.index(
        "文档元信息："
    )
    assert rendered.markdown.rstrip().splitlines()[-1].startswith("文档元信息：")
    assert "| 字段 | 内容 |" not in rendered.markdown
    assert (
        rendered.normalized_artifact_data["document_info"] == fixture["document_info"]
    )


def test_delivery_splits_business_overview_from_compact_document_metadata():
    fixture = copy.deepcopy(ARTIFACT_DATA_STAGE_FIXTURES[("TEST_DESIGN", "DELIVERY")])

    rendered = render_complete_artifact_data(
        fixture,
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    )

    overview = rendered.markdown.index("## 1. 交付概览")
    summary = rendered.markdown.index("## 2. 执行摘要")
    metadata = rendered.markdown.index("文档元信息：")
    assert overview < summary < metadata
    business_markdown = rendered.markdown[overview:metadata]
    metadata_markdown = rendered.markdown[metadata:]
    for value in ("登录功能", "可签署", "2", "1"):
        assert value in business_markdown
    for value in ("TEST&#95;DESIGN", "DELIVERY", "v1.0", "2026-06-23"):
        assert value in metadata_markdown
    assert "| 字段 | 内容 |" not in metadata_markdown
    assert (
        rendered.normalized_artifact_data["delivery_metrics"]
        == fixture["delivery_metrics"]
    )


@pytest.mark.parametrize(
    (
        "workflow_id",
        "stage_id",
        "business_heading",
        "business_values",
        "metadata_values",
    ),
    [
        (
            "REQ_REVIEW",
            "REVIEW",
            "## 评审上下文",
            ("会员权益需求", "会员可在权益中心查看", "存在阻断问题"),
            ("需求质量诊断与评审问题清单", "2026-06-23"),
        ),
        (
            "REQ_REVIEW",
            "REPORT",
            "## 评审上下文",
            ("会员权益需求", "REQ_REVIEW/REVIEW", "产品 / 研发 / 测试"),
            ("2026-06-23",),
        ),
        (
            "INCIDENT_REVIEW",
            "IMPROVEMENT",
            "## 报告概览",
            ("支付回调失败", "P1", "改进行动总数 | 3", "2026-07-07", "待复查"),
            ("v1.0", "2026-06-23 16:30"),
        ),
        (
            "VALUE_DISCOVERY",
            "BLUEPRINT",
            "## 需求蓝图概览",
            ("面向中小研发团队的 AI 测试设计工作台",),
            ("v1.0", "2026-06-23", "可评审需求蓝图", "可交接 Lisa"),
        ),
    ],
)
def test_mixed_information_sections_keep_business_context_out_of_metadata_footer(
    workflow_id: str,
    stage_id: str,
    business_heading: str,
    business_values: tuple[str, ...],
    metadata_values: tuple[str, ...],
):
    fixture = copy.deepcopy(ARTIFACT_DATA_STAGE_FIXTURES[(workflow_id, stage_id)])

    rendered = render_complete_artifact_data(
        fixture,
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )

    business_start = rendered.markdown.index(business_heading)
    metadata_start = rendered.markdown.index("文档元信息：")
    assert business_start < metadata_start
    business_markdown = rendered.markdown[business_start:metadata_start]
    metadata_markdown = rendered.markdown[metadata_start:]
    for value in business_values:
        assert value in business_markdown
        assert value not in metadata_markdown
    for value in metadata_values:
        assert value in metadata_markdown
    assert "\n|" not in metadata_markdown


VISIBLE_METADATA_STAGE_KEYS = {
    ("TEST_DESIGN", "CLARIFY"),
    ("TEST_DESIGN", "STRATEGY"),
    ("TEST_DESIGN", "CASES"),
    ("TEST_DESIGN", "DELIVERY"),
    ("REQ_REVIEW", "REVIEW"),
    ("REQ_REVIEW", "REPORT"),
    ("INCIDENT_REVIEW", "IMPROVEMENT"),
    ("VALUE_DISCOVERY", "ELEVATOR"),
    ("VALUE_DISCOVERY", "PERSONA"),
    ("VALUE_DISCOVERY", "JOURNEY"),
    ("VALUE_DISCOVERY", "BLUEPRINT"),
    ("STORY_BREAKDOWN", "INPUT_ANALYSIS"),
    ("STORY_BREAKDOWN", "EPIC_MAPPING"),
    ("STORY_BREAKDOWN", "STORY_BACKLOG"),
    ("STORY_BREAKDOWN", "SPRINT_PLAN"),
    ("PRD_REVIEW", "INVENTORY"),
    ("PRD_REVIEW", "QUALITY_AUDIT"),
    ("PRD_REVIEW", "COMPLETION_PLAN"),
    ("PRD_REVIEW", "REVISION_BLUEPRINT"),
}

NO_PURE_METADATA_STAGE_KEYS = {
    ("INCIDENT_REVIEW", "TIMELINE"),
    ("INCIDENT_REVIEW", "ROOT_CAUSE"),
    ("IDEA_BRAINSTORM", "DEFINE"),
    ("IDEA_BRAINSTORM", "DIVERGE"),
    ("IDEA_BRAINSTORM", "CONVERGE"),
    ("IDEA_BRAINSTORM", "CONCEPT"),
}


def test_all_25_stages_have_one_exhaustive_metadata_display_classification():
    classified = VISIBLE_METADATA_STAGE_KEYS | NO_PURE_METADATA_STAGE_KEYS

    assert len(VISIBLE_METADATA_STAGE_KEYS) == 19
    assert len(NO_PURE_METADATA_STAGE_KEYS) == 6
    assert sum(
        len(group)
        for group in (
            VISIBLE_METADATA_STAGE_KEYS,
            NO_PURE_METADATA_STAGE_KEYS,
        )
    ) == len(classified)
    assert classified == set(ARTIFACT_DATA_RENDERERS)


@pytest.mark.parametrize(
    ("stage_key", "fixture"),
    sorted(ARTIFACT_DATA_STAGE_FIXTURES.items()),
)
def test_every_stage_keeps_business_before_lightweight_or_structured_metadata(
    stage_key: tuple[str, str],
    fixture: dict,
):
    workflow_id, stage_id = stage_key
    plan = ARTIFACT_DATA_RENDERERS[stage_key]
    rendered = render_complete_artifact_data(
        copy.deepcopy(fixture),
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )
    role_by_section_id = {section.section_id: section.role for section in plan.sections}
    completed_roles = tuple(
        role_by_section_id[section_id] for section_id in rendered.completed_section_ids
    )

    assert completed_roles[0] == "business"
    assert completed_roles == tuple(
        sorted(completed_roles, key={"business": 0, "metadata": 1}.get)
    )
    if stage_key in VISIBLE_METADATA_STAGE_KEYS:
        assert completed_roles[-1] == "metadata"
        assert rendered.markdown.count("文档元信息：") == 1
        assert rendered.markdown.rstrip().splitlines()[-1].startswith("文档元信息：")
        assert (
            "\n| 字段 | 内容 |"
            not in rendered.markdown[rendered.markdown.index("文档元信息：") :]
        )
    else:
        assert "metadata" not in completed_roles
        assert "文档元信息：" not in rendered.markdown

    if "document_info" in plan.model.model_fields:
        assert (
            rendered.normalized_artifact_data["document_info"]
            == fixture["document_info"]
        )
        document_info = rendered.normalized_artifact_data["document_info"]
        if "workflow" in document_info:
            assert document_info["workflow"] == workflow_id
            assert document_info["stage"] == stage_id


@pytest.mark.parametrize(
    ("stage_key", "fixture"),
    sorted(ARTIFACT_DATA_STAGE_FIXTURES.items()),
)
def test_manifest_required_markdown_headings_follow_renderer_order(
    stage_key: tuple[str, str],
    fixture: dict,
):
    rendered = render_complete_artifact_data(
        copy.deepcopy(fixture),
        workflow_id=stage_key[0],
        current_stage_id=stage_key[1],
    )
    rendered_headings: list[str] = []
    inside_fence = False
    for line in rendered.markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            inside_fence = not inside_fence
            continue
        prefix = stripped.split(" ", 1)[0]
        if (
            not inside_fence
            and 1 <= len(prefix) <= 6
            and set(prefix) == {"#"}
            and len(stripped) > len(prefix)
        ):
            rendered_headings.append(stripped)

    required_contract = REQUIRED_ARTIFACT_HEADINGS[stage_key]
    required_headings = [
        heading for heading in required_contract if heading.startswith("#")
    ]
    positions = [rendered_headings.index(heading) for heading in required_headings]

    assert positions == sorted(positions)

    dynamic_headings: set[str] = set()
    if stage_key == ("TEST_DESIGN", "CASES"):
        dynamic_headings.update(
            f"### 3.{index} {group['dimension']}"
            for index, group in enumerate(fixture["case_groups"], start=1)
        )
    elif stage_key == ("REQ_REVIEW", "REVIEW"):
        dynamic_headings.update(
            f"### {index}. {group['dimension']}"
            for index, group in enumerate(fixture["issue_groups"], start=1)
        )
    elif stage_key == ("VALUE_DISCOVERY", "JOURNEY"):
        dynamic_headings.update(
            f"### 阶段 {index}：{stage['stage_name']}"
            for index, stage in enumerate(fixture["journey_stages"], start=1)
        )
    for rendered_heading in rendered_headings:
        if rendered_heading in dynamic_headings:
            continue
        assert any(
            (
                rendered_heading == required_heading
                if required_heading.startswith("#")
                else rendered_heading.startswith("# ")
                and required_heading in rendered_heading
            )
            for required_heading in required_contract
        ), f"renderer heading is missing from manifest contract: {rendered_heading}"


@pytest.mark.parametrize(
    ("stage_id", "business_heading", "artifact_name"),
    [
        ("ELEVATOR", "## 定位摘要", "价值定位诊断报告"),
        ("PERSONA", "## 画像摘要", "用户画像与决策链分析"),
    ],
)
def test_value_summary_keeps_artifact_name_only_in_metadata_footer(
    stage_id: str,
    business_heading: str,
    artifact_name: str,
):
    rendered = render_complete_artifact_data(
        copy.deepcopy(ARTIFACT_DATA_STAGE_FIXTURES[("VALUE_DISCOVERY", stage_id)]),
        workflow_id="VALUE_DISCOVERY",
        current_stage_id=stage_id,
    )
    business_start = rendered.markdown.index(business_heading)
    metadata_start = rendered.markdown.index("## 文档信息")

    assert artifact_name not in rendered.markdown[business_start:metadata_start]
    assert artifact_name in rendered.markdown[metadata_start:]


def test_invalid_visual_section_is_withheld_without_blocking_later_section():
    plan = ArtifactRenderPlan(
        model=_VisualIsolationArtifactData,
        title=lambda _data: "# Visual isolation probe",
        title_dependencies=(),
        sections=(
            ArtifactSectionSpec(
                section_id="before",
                dependencies=("before",),
                render=lambda data: f"## Before\n\n{data.before}",
            ),
            ArtifactSectionSpec(
                section_id="invalid-visual",
                dependencies=("invalid_visual",),
                render=lambda data: (
                    "## Invalid visual\n\n```ai4se-visual\n"
                    f"{data.invalid_visual}\n```"
                ),
            ),
            ArtifactSectionSpec(
                section_id="after",
                dependencies=("after",),
                render=lambda data: f"## After\n\n{data.after}",
            ),
        ),
    )

    rendered = plan.render_available(
        {"before": "stable", "invalid_visual": "{not-json}", "after": "kept"}
    )

    assert rendered is not None
    assert rendered.completed_section_ids == ("before", "after")
    assert "## Before" in rendered.markdown
    assert "## Invalid visual" not in rendered.markdown
    assert "## After" in rendered.markdown


def test_available_projection_reuses_derived_case_statistics_for_rendering():
    fixture = copy.deepcopy(VALID_CASES_ARTIFACT_DATA)
    fixture.pop("case_statistics")

    available = render_available_artifact_data(
        fixture,
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert available is not None
    assert "## 1. 用例统计" in available.markdown
    assert "**统计摘要**：共 2 条用例" in available.markdown


@pytest.mark.parametrize(
    ("workflow_id", "stage_id", "derived_field"),
    [
        ("TEST_DESIGN", "CASES", "case_statistics"),
        ("REQ_REVIEW", "REPORT", "issue_statistics"),
        ("INCIDENT_REVIEW", "IMPROVEMENT", "priority_distribution"),
    ],
)
def test_omitted_optional_derived_field_converges_in_partial_and_complete_render(
    workflow_id: str,
    stage_id: str,
    derived_field: str,
):
    fixture = copy.deepcopy(ARTIFACT_DATA_STAGE_FIXTURES[(workflow_id, stage_id)])
    fixture.pop(derived_field)

    available = render_available_artifact_data(
        fixture,
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )
    complete = render_complete_artifact_data(
        fixture,
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )

    assert available is not None
    assert available.markdown == complete.markdown
    assert available.completed_section_ids == complete.completed_section_ids


@pytest.mark.parametrize(
    ("workflow_id", "stage_id", "omit_derived_value"),
    [
        (
            "IDEA_BRAINSTORM",
            "CONVERGE",
            lambda fixture: (
                fixture["ice_evaluations"][0].pop("ice_score"),
                fixture["ice_evaluations"][0].pop("rank"),
            ),
        ),
        (
            "INCIDENT_REVIEW",
            "IMPROVEMENT",
            lambda fixture: fixture["report_info"].pop("action_count"),
        ),
        (
            "TEST_DESIGN",
            "STRATEGY",
            lambda fixture: fixture["risks"][0].pop("rpn"),
        ),
        (
            "TEST_DESIGN",
            "CASES",
            lambda fixture: fixture["case_groups"][0]["cases"][0].pop("dimension"),
        ),
        (
            "TEST_DESIGN",
            "DELIVERY",
            lambda fixture: (
                fixture["case_summary_items"][0].pop("case_count"),
                fixture["delivery_metrics"].pop("total_cases"),
                fixture["delivery_metrics"].pop("high_risk_count"),
            ),
        ),
        (
            "REQ_REVIEW",
            "REVIEW",
            lambda fixture: (
                fixture["issue_groups"][0]["issues"][0].pop("dimension"),
                fixture["issue_statistics"].pop("p0_count"),
            ),
        ),
        (
            "REQ_REVIEW",
            "REPORT",
            lambda fixture: fixture["issue_statistics"].pop("p0_count"),
        ),
        (
            "VALUE_DISCOVERY",
            "ELEVATOR",
            lambda fixture: (
                fixture["score_summary"].pop("total_score"),
                fixture["score_summary"].pop("average_score"),
            ),
        ),
        (
            "STORY_BREAKDOWN",
            "STORY_BACKLOG",
            lambda fixture: fixture["user_stories"][0].pop("sprint"),
        ),
    ],
)
def test_nested_derived_defaults_converge_in_partial_and_complete_render(
    workflow_id: str,
    stage_id: str,
    omit_derived_value,
):
    fixture = copy.deepcopy(ARTIFACT_DATA_STAGE_FIXTURES[(workflow_id, stage_id)])
    omit_derived_value(fixture)

    available = render_available_artifact_data(
        fixture,
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )
    complete = render_complete_artifact_data(
        fixture,
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )

    assert available is not None
    assert available.markdown == complete.markdown
    assert available.completed_section_ids == complete.completed_section_ids


@pytest.mark.parametrize("invalid_kind", ["duplicate_why_level", "unchecked_gate"])
def test_root_cause_full_contract_rejects_manifest_invariant_drift(
    invalid_kind: str,
):
    fixture = copy.deepcopy(VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA)
    if invalid_kind == "duplicate_why_level":
        fixture["why_chain"][1]["level"] = fixture["why_chain"][0]["level"]
    else:
        for item in fixture["stage_gate"]:
            item["checked"] = False

    with pytest.raises(ValidationError, match="why_chain|stage_gate"):
        render_complete_artifact_data(
            fixture,
            workflow_id="INCIDENT_REVIEW",
            current_stage_id="ROOT_CAUSE",
        )


@pytest.mark.parametrize(
    ("workflow_id", "stage_id", "fixture"),
    [
        (workflow_id, stage_id, fixture)
        for (workflow_id, stage_id), fixture in sorted(
            ARTIFACT_DATA_STAGE_FIXTURES.items()
        )
    ],
)
def test_every_stage_reveals_multiple_business_section_snapshots_and_converges(
    workflow_id: str,
    stage_id: str,
    fixture: dict,
):
    partial: dict = {}
    business_ids = set(
        get_artifact_render_plan_business_section_ids(workflow_id, stage_id)
    )
    business_snapshots: list[tuple[str, ...]] = []
    rendered_markdowns: list[str] = []

    for field_name, value in fixture.items():
        partial[field_name] = copy.deepcopy(value)
        rendered = render_available_artifact_data(
            partial,
            workflow_id=workflow_id,
            current_stage_id=stage_id,
        )
        if rendered is None:
            continue
        validate_artifact_visual_blocks(rendered.markdown)
        completed_business_ids = tuple(
            section_id
            for section_id in rendered.completed_section_ids
            if section_id in business_ids
        )
        if completed_business_ids and (
            not business_snapshots or completed_business_ids != business_snapshots[-1]
        ):
            business_snapshots.append(completed_business_ids)
            rendered_markdowns.append(rendered.markdown)

    complete = render_complete_artifact_data(
        copy.deepcopy(fixture),
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )
    available = render_available_artifact_data(
        copy.deepcopy(fixture),
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )

    assert len(business_snapshots) >= 3, (workflow_id, stage_id, business_snapshots)
    assert all(
        set(previous) < set(current)
        for previous, current in pairwise(business_snapshots)
    )
    assert len(set(rendered_markdowns)) == len(rendered_markdowns)
    assert available is not None
    assert available.markdown == complete.markdown
    assert available.completed_section_ids == complete.completed_section_ids
