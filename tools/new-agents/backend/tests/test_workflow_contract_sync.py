import json
import re
from pathlib import Path

from agent_contracts import (
    MIN_MEANINGFUL_PARTIAL_CHAT_CHARACTERS,
    NON_MEANINGFUL_AGENT_CHAT_MESSAGES,
    NON_MEANINGFUL_AGENT_CHAT_PREFIXES,
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
FRONTEND_LLM = NEW_AGENTS_ROOT / "frontend" / "src" / "core" / "llm.ts"


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


def test_non_meaningful_agent_chat_messages_match_frontend_stream_parser():
    source = FRONTEND_LLM.read_text(encoding="utf-8")
    match = re.search(
        r"const NON_MEANINGFUL_AGENT_CHAT_MESSAGES = new Set\(\[(.*?)\]\);",
        source,
        re.DOTALL,
    )

    assert match is not None
    frontend_messages = set(re.findall(r"'([^']+)'", match.group(1)))
    assert frontend_messages == set(NON_MEANINGFUL_AGENT_CHAT_MESSAGES)

    prefix_match = re.search(
        r"const NON_MEANINGFUL_AGENT_CHAT_PREFIXES = \[(.*?)\];",
        source,
        re.DOTALL,
    )
    assert prefix_match is not None
    frontend_prefixes = tuple(re.findall(r"'([^']+)'", prefix_match.group(1)))
    assert frontend_prefixes == NON_MEANINGFUL_AGENT_CHAT_PREFIXES

    minimum_match = re.search(
        r"const MIN_MEANINGFUL_PARTIAL_CHAT_CHARACTERS = (\d+);",
        source,
    )
    assert minimum_match is not None
    assert int(minimum_match.group(1)) == MIN_MEANINGFUL_PARTIAL_CHAT_CHARACTERS


def test_shared_workflow_manifest_stage_order_matches_backend_contract():
    assert _workflow_manifest_stages() == WORKFLOW_STAGES


def test_shared_workflow_manifest_visual_contract_matches_backend_required_visual_maps():
    manifest = _workflow_manifest()

    manifest_mermaid = {}
    manifest_structured = {}
    for workflow_id, workflow in manifest["workflows"].items():
        for stage in workflow["stages"]:
            stage_key = (workflow_id, stage["id"])
            visual_contract = stage.get("visualContract") or {}
            mermaid = visual_contract.get("requiredMermaidDiagrams") or []
            structured = visual_contract.get("requiredStructuredVisuals") or []
            if mermaid:
                manifest_mermaid[stage_key] = mermaid
            if structured:
                manifest_structured[stage_key] = structured

    assert manifest_mermaid == REQUIRED_ARTIFACT_MERMAID_DIAGRAMS
    assert manifest_structured == REQUIRED_ARTIFACT_STRUCTURED_VISUALS


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


def test_shared_visual_protocol_declares_layering_policy():
    from workflow_manifest import format_visual_protocol_instruction

    manifest = _workflow_manifest()
    protocol = manifest["visualProtocol"]
    required_mermaid_types = {
        diagram_type
        for diagram_types in REQUIRED_ARTIFACT_MERMAID_DIAGRAMS.values()
        for diagram_type in diagram_types
    }
    required_structured_visual_types = {
        visual_type
        for visual_types in REQUIRED_ARTIFACT_STRUCTURED_VISUALS.values()
        for visual_type in visual_types
    }

    assert protocol["modelOutput"]["mode"] == "artifact_data_only"
    assert protocol["modelOutput"]["forbiddenDslOutputs"] == [
        "Mermaid 代码块",
        "D2 代码块",
        "Graphviz DOT 代码块",
        "PlantUML 代码块",
    ]
    assert protocol["modelOutput"]["forbiddenDirectVisualOutputs"] == [
        "完整 Markdown 文档",
        "Markdown 表格",
        "ai4se-visual JSON 代码块",
    ]
    assert protocol["mermaid"]["source"] == "backend_deterministic_renderer"
    assert (
        set(protocol["mermaid"]["allowedGeneratedDiagramTypes"])
        >= required_mermaid_types
    )
    assert protocol["structuredVisual"]["source"] == "backend_deterministic_renderer"
    assert protocol["structuredVisual"]["primaryForComplexBusinessVisuals"] is True
    assert (
        set(protocol["structuredVisual"]["currentTypes"])
        >= required_structured_visual_types
    )
    assert "timeline-map" in protocol["structuredVisual"]["currentTypes"]
    assert "flow-map" in protocol["structuredVisual"]["currentTypes"]
    assert set(protocol["structuredVisual"]["plannedComplexTypes"]) >= {
        "mindmap",
        "sequence-flow",
        "distribution-chart",
    }
    assert "timeline-map" not in protocol["structuredVisual"]["plannedComplexTypes"]
    assert "flow-map" not in protocol["structuredVisual"]["plannedComplexTypes"]

    instruction = format_visual_protocol_instruction()
    assert "视觉产物协议" in instruction
    assert "模型只输出 artifact_data 结构化业务数据" in instruction
    assert "Mermaid、D2、Graphviz DOT、PlantUML 代码块" in instruction
    assert "完整 Markdown 文档、Markdown 表格、ai4se-visual JSON 代码块" in instruction
    assert "Mermaid 只允许由后端确定性渲染器生成" in instruction
    assert "复杂业务图优先使用 ai4se-visual JSON" in instruction


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


def test_idea_converge_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "IDEA_BRAINSTORM",
        "CONVERGE",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["IDEA_BRAINSTORM"]["stages"]
        if stage["id"] == "CONVERGE"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "ice_evaluations.idea_id 必须唯一" in instruction
    assert "rank 缺省时由后端按 ICE 得分降序派生" in instruction
    assert (
        "ice_score 缺省时由后端按 " "impact * confidence / effort 派生"
    ) in instruction
    assert "decision_matrix.recommended_idea_id" in instruction
    assert "validation_experiments.idea_ids" in instruction
    assert "merge_paths.source_idea_ids" in instruction
    assert "推荐方案必须同时出现在 ICE 结论和决策矩阵中" in instruction
    assert "quadrantChart" in instruction
    assert "右侧收敛聚焦产物" in instruction


def test_derived_artifact_data_fields_are_tracked_and_not_required_in_runtime_examples():
    from agent_runtime import build_structured_output_instruction
    from workflow_manifest import (
        format_artifact_data_contract_instruction,
        get_derived_artifact_data_field_policies,
    )

    policies = get_derived_artifact_data_field_policies()

    assert {
        (policy["workflow_id"], policy["stage_id"], policy["path"])
        for policy in policies
    } == {
        ("TEST_DESIGN", "STRATEGY", "risks[].rpn"),
        ("TEST_DESIGN", "CASES", "case_statistics"),
        ("TEST_DESIGN", "CASES", "case_groups[].cases[].dimension"),
        ("TEST_DESIGN", "DELIVERY", "case_summary_items[].case_count"),
        ("TEST_DESIGN", "DELIVERY", "delivery_metrics.total_cases"),
        ("TEST_DESIGN", "DELIVERY", "delivery_metrics.high_risk_count"),
        ("REQ_REVIEW", "REVIEW", "issue_statistics.p0_count/p1_count/p2_count"),
        ("REQ_REVIEW", "REVIEW", "issue_groups[].issues[].dimension"),
        ("REQ_REVIEW", "REPORT", "issue_statistics.p0_count/p1_count/p2_count"),
        ("VALUE_DISCOVERY", "ELEVATOR", "score_summary.total_score"),
        ("VALUE_DISCOVERY", "ELEVATOR", "score_summary.average_score"),
        ("INCIDENT_REVIEW", "IMPROVEMENT", "report_info.action_count"),
        ("INCIDENT_REVIEW", "IMPROVEMENT", "priority_distribution"),
        ("IDEA_BRAINSTORM", "CONVERGE", "ice_evaluations[].ice_score"),
        ("IDEA_BRAINSTORM", "CONVERGE", "ice_evaluations[].rank"),
        ("STORY_BREAKDOWN", "INPUT_ANALYSIS", "user_stories[].sprint"),
        ("STORY_BREAKDOWN", "EPIC_MAPPING", "user_stories[].sprint"),
        ("STORY_BREAKDOWN", "STORY_BACKLOG", "user_stories[].sprint"),
        ("STORY_BREAKDOWN", "SPRINT_PLAN", "user_stories[].sprint"),
    }

    for policy in policies:
        workflow_id = policy["workflow_id"]
        stage_id = policy["stage_id"]
        contract_instruction = format_artifact_data_contract_instruction(
            workflow_id,
            stage_id,
        )
        runtime_instruction = build_structured_output_instruction(
            workflow_id,
            stage_id,
        )

        for fragment in policy["required_contract_fragments"]:
            assert fragment in contract_instruction, policy["path"]
        for token in policy["forbidden_runtime_example_tokens"]:
            assert token not in runtime_instruction, policy["path"]


def test_strategy_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "TEST_DESIGN",
        "STRATEGY",
    )
    contract = _workflow_manifest()["workflows"]["TEST_DESIGN"]["stages"][1].get(
        "artifactDataContract"
    )

    assert contract is not None
    assert (
        "risks[].rpn 由后端根据 severity * occurrence * detection 计算" in instruction
    )
    assert "quality_goals[].goal_id 必须唯一" in instruction
    assert "risks[].risk_id 必须唯一" in instruction
    assert "test_techniques[].technique_id 必须唯一" in instruction
    assert "test_points[].point_id 必须唯一" in instruction
    assert (
        "test_points.quality_goal、test_points.risk、test_points.technique"
        in instruction
    )
    assert (
        "test_techniques.target、test_techniques.applies_to、test_layers.related"
        in instruction
    )
    assert "risk-board JSON 代码块" in instruction


def test_test_design_clarify_artifact_data_contract_manifest_drives_backend_instruction():
    from agent_runtime import build_structured_output_instruction
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "TEST_DESIGN",
        "CLARIFY",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["TEST_DESIGN"]["stages"]
        if stage["id"] == "CLARIFY"
    )
    contract = stage.get("artifactDataContract")
    runtime_instruction = build_structured_output_instruction(
        "TEST_DESIGN",
        "CLARIFY",
    )

    assert contract is not None
    assert (
        "requirement_facts、system_boundaries、business_rules、flow_links、"
        "clarification_questions、quality_requirements、downstream_inputs 和 "
        "stage_gate 都必须至少包含 1 条"
    ) in instruction
    assert "所有字符串字段必须是非空白内容" in instruction
    assert (
        "clarification_questions[].status 只能是待确认、已确认、已假设或 AI 假设；"
        "已假设仅用于用户明确授权 Lisa 代定的默认场景，可推进；"
        "AI 假设仍表示未经授权的临时推断，P0/P1 阻断问题不能推进；"
        "用户给出具体答案后必须更新为已确认"
    ) in instruction
    assert (
        "clarification_questions[].status 只能是待确认、已确认、已假设或 AI 假设；"
        "已假设仅用于用户明确授权 Lisa 代定的默认场景，可推进；"
        "AI 假设仍表示未经授权的临时推断，P0/P1 阻断问题不能推进；"
        "用户给出具体答案后必须更新为已确认"
    ) in runtime_instruction
    assert "Mermaid 代码块" in instruction
    assert "右侧需求分析文档" in instruction
    assert "Mermaid flowchart" in instruction


def test_test_design_delivery_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "TEST_DESIGN",
        "DELIVERY",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["TEST_DESIGN"]["stages"]
        if stage["id"] == "DELIVERY"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert (
        "case_summary_items[].case_count 缺省时由后端按 "
        "p0_count + p1_count + p2_count 派生"
    ) in instruction
    assert (
        "delivery_metrics.total_cases 缺省时由后端按 "
        "case_summary_items[].case_count 总和派生"
    ) in instruction
    assert (
        "delivery_metrics.high_risk_count 缺省时由后端按 open_risks 中"
        "不可接受风险数量派生"
    ) in instruction
    assert "coverage_map[].case_ids 必须至少包含 1 个用例 ID" in instruction
    assert "coverage-map JSON 代码块" in instruction
    assert "右侧测试设计交付包" in instruction
    assert "ai4se-visual coverage-map" in instruction


def test_cases_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "TEST_DESIGN",
        "CASES",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["TEST_DESIGN"]["stages"]
        if stage["id"] == "CASES"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "case_statistics 由后端根据 case_groups 计算，模型不要输出" in instruction
    assert (
        "case_groups[].cases[].dimension 缺省时由后端按外层 "
        "case_groups[].dimension 派生"
    ) in instruction
    assert "case_groups[].cases[].case_id 必须唯一" in instruction
    assert "automation_candidates.case_id 只能引用已存在的 case_id" in instruction
    assert "coverage_trace.covered_cases 只能引用已存在的 case_id" in instruction
    assert "traceability-matrix JSON 代码块" in instruction
    assert "右侧测试用例集" in instruction
    assert "ai4se-visual traceability-matrix" in instruction


def test_req_review_review_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "REQ_REVIEW",
        "REVIEW",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["REQ_REVIEW"]["stages"]
        if stage["id"] == "REVIEW"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "quality_overview[].severity_score 必须是 1 到 5 的整数" in instruction
    assert "issue_groups[].issues[].issue_id 必须唯一" in instruction
    assert (
        "issue_statistics.p0_count/p1_count/p2_count 缺省时由后端按 "
        "issue_groups[].issues[].priority 中 P0/P1/P2 的数量派生"
    ) in instruction
    assert (
        "issue_groups[].issues[].dimension 缺省时由后端按外层 "
        "issue_groups[].dimension 派生"
    ) in instruction
    assert (
        "revision_suggestions[].related_issues 只能引用 "
        "issue_groups[].issues[].issue_id 中已定义的问题 ID"
    ) in instruction
    assert "score-matrix JSON 代码块" in instruction
    assert "右侧需求评审问题清单" in instruction
    assert "Mermaid flowchart" in instruction
    assert "ai4se-visual score-matrix" in instruction


def test_req_review_report_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "REQ_REVIEW",
        "REPORT",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["REQ_REVIEW"]["stages"]
        if stage["id"] == "REPORT"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "issue_closures[].issue_id 必须唯一" in instruction
    assert (
        "issue_statistics.p0_count/p1_count/p2_count 缺省时由后端按 "
        "issue_closures[].priority 中 P0/P1/P2 的数量派生"
    ) in instruction
    assert (
        "review_conditions[].related_issues 只能引用 "
        "issue_closures[].issue_id 中已定义的问题 ID"
    ) in instruction
    assert (
        "当存在 closure_status != “已关闭” 的 P0/P1 issue_closures 时，"
        "conclusion.review_result 不能为“通过”"
    ) in instruction
    assert "priority-board JSON 代码块" in instruction
    assert "右侧需求评审报告" in instruction
    assert "Mermaid pie" in instruction
    assert "ai4se-visual priority-board" in instruction


def test_incident_root_cause_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "INCIDENT_REVIEW",
        "ROOT_CAUSE",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["INCIDENT_REVIEW"]["stages"]
        if stage["id"] == "ROOT_CAUSE"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "why_chain[].level 必须唯一" in instruction
    assert "cause_evidence.cause_id 必须唯一" in instruction
    assert "cause_evidence.related_level 只能引用 why_chain[].level" in instruction
    assert (
        "fishbone_categories.cause_ids 只能引用 cause_evidence.cause_id" in instruction
    )
    assert (
        "root_cause_conclusions.related_cause_id 只能引用 cause_evidence.cause_id"
        in instruction
    )
    assert "why_chain 至少包含 3 层追问" in instruction
    assert "cause-map JSON 代码块" in instruction
    assert "ai4se-visual cause-map" in instruction
    assert "Mermaid mindmap" in instruction


def test_incident_timeline_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "INCIDENT_REVIEW",
        "TIMELINE",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["INCIDENT_REVIEW"]["stages"]
        if stage["id"] == "TIMELINE"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "所有字符串字段必须是非空白内容" in instruction
    assert (
        "impact_metrics、fact_sources、timeline_events、fact_separation" in instruction
    )
    assert "timeline_events[].fact_ids 必须至少包含 1 个事实 ID" in instruction
    assert "fact_sources[].fact_id 必须唯一" in instruction
    assert (
        "timeline_events[].fact_ids 只能引用 "
        "fact_sources[].fact_id 中已定义的事实 ID"
    ) in instruction
    assert "Mermaid 代码块" in instruction
    assert "右侧故障复盘事件还原" in instruction
    assert "ai4se-visual timeline-map" in instruction
    assert "Mermaid timeline" not in instruction
    assert stage["visualContract"] == {
        "requiredStructuredVisuals": ["timeline-map"],
    }


def test_incident_improvement_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "INCIDENT_REVIEW",
        "IMPROVEMENT",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["INCIDENT_REVIEW"]["stages"]
        if stage["id"] == "IMPROVEMENT"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert (
        "report_info.action_count 缺省时由后端按 " "improvement_actions 数量派生"
    ) in instruction
    assert "improvement_actions[].action_id 必须唯一" in instruction
    assert (
        "priority_distribution 缺省时由后端按 "
        "improvement_actions[].priority 中紧急/重要/常规的数量派生"
    ) in instruction
    assert (
        "root_cause_coverage[].action_ids 只能引用 "
        "improvement_actions[].action_id 中已定义的行动 ID"
    ) in instruction
    assert (
        "improvement_actions[].root_cause_id 只能引用 "
        "root_cause_coverage[].cause_id 中已定义的根因 ID"
    ) in instruction
    assert (
        "root_cause_coverage[].action_ids 必须精确匹配所有 root_cause_id "
        "等于对应 cause_id 的 improvement_actions[].action_id"
    ) in instruction
    assert "action-board JSON 代码块" in instruction
    assert "右侧最终故障复盘报告" in instruction
    assert "ai4se-visual action-board" in instruction


def test_idea_define_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "IDEA_BRAINSTORM",
        "DEFINE",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["IDEA_BRAINSTORM"]["stages"]
        if stage["id"] == "DEFINE"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "evidence_items[].evidence_id 必须唯一" in instruction
    assert "problem_landscape.subproblems[].problem_id 必须唯一" in instruction
    assert (
        "problem_user_fit.evidence_ids 只能引用 evidence_items[].evidence_id"
        in instruction
    )
    assert (
        "problem_landscape.root_problem 必须被至少一个 evidence_items.related_problem 或 problem_user_fit.evidence_or_assumption 条目覆盖"
        in instruction
    )
    assert "stage_gate 至少包含一个 checked=true" in instruction
    assert "Mermaid 代码块" in instruction
    assert "mindmap 代码块" in instruction
    assert "右侧问题域分析" in instruction
    assert "Mermaid mindmap" in instruction


def test_idea_diverge_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "IDEA_BRAINSTORM",
        "DIVERGE",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["IDEA_BRAINSTORM"]["stages"]
        if stage["id"] == "DIVERGE"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "idea_cards[].idea_id 必须唯一" in instruction
    assert "idea_sources[].source_id 必须唯一" in instruction
    assert "parked_or_excluded[].record_id 必须唯一" in instruction
    assert (
        "idea_landscape.groups[].idea_ids 只能引用 idea_cards[].idea_id 中已定义的创意 ID"
        in instruction
    )
    assert (
        "idea_sources[].idea_ids 只能引用 idea_cards[].idea_id 中已定义的创意 ID"
        in instruction
    )
    assert "stage_gate 至少包含一个 checked=true" in instruction
    assert "Mermaid 代码块" in instruction
    assert "mindmap 代码块" in instruction
    assert "右侧创意发散产物" in instruction
    assert "Mermaid mindmap" in instruction


def test_idea_concept_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "IDEA_BRAINSTORM",
        "CONCEPT",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["IDEA_BRAINSTORM"]["stages"]
        if stage["id"] == "CONCEPT"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "core_assumptions[].assumption_id 必须唯一" in instruction
    assert "validation_roadmap[].validation_id 必须唯一" in instruction
    assert "next_actions[].action_id 必须唯一" in instruction
    assert (
        "lean_canvas.cell 必须覆盖问题、用户群体、独特价值主张、解决方案、渠道、收入来源、成本结构、关键指标、竞争壁垒"
        in instruction
    )
    assert (
        "growth_funnel.stage 必须覆盖 Acquisition、Activation、Retention、Revenue、Referral"
        in instruction
    )
    assert (
        "mvp_features[].assumption_ids 只能引用 core_assumptions[].assumption_id 中已定义的假设 ID"
        in instruction
    )
    assert (
        "validation_roadmap[].assumption_ids 只能引用 core_assumptions[].assumption_id 中已定义的假设 ID"
        in instruction
    )
    assert (
        "next_actions[].related_ids 只能引用 core_assumptions[].assumption_id、validation_roadmap[].validation_id 或 premortem_risks[].risk_id 中已定义的 ID"
        in instruction
    )
    assert "stage_gate 至少包含一个 checked=true" in instruction
    assert "mvp-map JSON 代码块" in instruction
    assert "右侧产品概念简报" in instruction
    assert "ai4se-visual mvp-map" in instruction
    assert "Mermaid pie" in instruction
    assert "Mermaid flowchart" in instruction


def test_value_elevator_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "VALUE_DISCOVERY",
        "ELEVATOR",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["VALUE_DISCOVERY"]["stages"]
        if stage["id"] == "ELEVATOR"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "value_flow.nodes[].node_id 必须唯一" in instruction
    assert (
        "value_flow.links[].from_node 和 value_flow.links[].to_node 只能引用 value_flow.nodes[].node_id 中已定义的节点 ID"
        in instruction
    )
    assert "score_matrix[].score 必须是 1 到 5 的整数" in instruction
    assert (
        "score_summary.total_score 由后端根据 score_matrix[].score 求和计算，模型不要输出"
        in instruction
    )
    assert (
        "score_summary.average_score 由后端根据 score_matrix[].score 计算并保留 2 位小数，模型不要输出"
        in instruction
    )
    assert (
        "如果模型显式输出 score_summary.total_score 或 score_summary.average_score，必须与后端计算结果一致"
        in instruction
    )
    assert "Mermaid 代码块" in instruction
    assert "score-matrix JSON 代码块" in instruction
    assert "右侧价值定位分析" in instruction
    assert "Mermaid flowchart" in instruction
    assert "ai4se-visual score-matrix" in instruction


def test_value_persona_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "VALUE_DISCOVERY",
        "PERSONA",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["VALUE_DISCOVERY"]["stages"]
        if stage["id"] == "PERSONA"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "personas[].persona_id 必须唯一" in instruction
    assert (
        "behavior_scenarios[].persona_id、decision_chain[].persona_id、pain_evidence[].persona_id、priority_ranking[].persona_id 只能引用 personas[].persona_id 中已定义的画像 ID"
        in instruction
    )
    assert "priority_ranking[].persona_id 必须唯一" in instruction
    assert "完整 Markdown 文档" in instruction
    assert "Markdown 表格" in instruction
    assert "右侧用户画像分析" in instruction
    assert (
        "画像、行为场景、决策链、痛点证据、反画像和优先级排序 Markdown 表格"
        in instruction
    )


def test_value_journey_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "VALUE_DISCOVERY",
        "JOURNEY",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["VALUE_DISCOVERY"]["stages"]
        if stage["id"] == "JOURNEY"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "journey_stages[].stage_id 必须唯一" in instruction
    assert "journey_stages[].pain_id 必须唯一" in instruction
    assert "journey_stages[].opportunity_id 必须唯一" in instruction
    assert "journey_stages[].emotion_score 必须是 1 到 5 的整数" in instruction
    assert (
        "pain_priorities[].stage_id 只能引用 journey_stages[].stage_id 中已定义的旅程阶段 ID"
        in instruction
    )
    assert (
        "pain_priorities[].pain_id 和 opportunity_scores[].pain_id 只能引用 journey_stages[].pain_id 中已定义的痛点 ID"
        in instruction
    )
    assert (
        "opportunity_scores[].opportunity_id、entry_strategy[].related_opportunity 和 validation_experiments[].opportunity_id 只能引用 journey_stages[].opportunity_id 中已定义的机会 ID"
        in instruction
    )
    assert "Mermaid 代码块" in instruction
    assert "journey-map JSON 代码块" in instruction
    assert "右侧用户旅程分析" in instruction
    assert "Mermaid journey" in instruction
    assert "ai4se-visual journey-map" in instruction


def test_value_blueprint_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    instruction = format_artifact_data_contract_instruction(
        "VALUE_DISCOVERY",
        "BLUEPRINT",
    )
    stage = next(
        stage
        for stage in _workflow_manifest()["workflows"]["VALUE_DISCOVERY"]["stages"]
        if stage["id"] == "BLUEPRINT"
    )
    contract = stage.get("artifactDataContract")

    assert contract is not None
    assert "requirements[].requirement_id 必须唯一" in instruction
    assert "acceptance_criteria[].acceptance_id 必须唯一" in instruction
    assert (
        "feature_modules[].features[].requirement_id 如果非空，只能引用 requirements[].requirement_id 中已定义的需求 ID"
        in instruction
    )
    assert (
        "mvp_plan.included_features[].requirement_id 和 acceptance_criteria[].requirement_id 只能引用 requirements[].requirement_id 中已定义的需求 ID"
        in instruction
    )
    assert (
        "lisa_handoff_inputs[] 中 input_type 为“需求”时 reference_id 只能引用 requirements[].requirement_id 中已定义的需求 ID"
        in instruction
    )
    assert (
        "lisa_handoff_inputs[] 中 input_type 为“验收标准”时 reference_id 只能引用 acceptance_criteria[].acceptance_id 中已定义的验收标准 ID"
        in instruction
    )
    assert "main_flow.nodes[].node_id 必须唯一" in instruction
    assert (
        "main_flow.links[].from_node 和 main_flow.links[].to_node 只能引用 main_flow.nodes[].node_id 中已定义的流程节点 ID"
        in instruction
    )
    assert "Mermaid 代码块" in instruction
    assert "roadmap JSON 代码块" in instruction
    assert "右侧需求蓝图" in instruction
    assert "Mermaid mindmap" in instruction
    assert "Mermaid flowchart" in instruction
    assert "ai4se-visual roadmap" in instruction


def test_story_breakdown_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    workflow = _workflow_manifest()["workflows"]["STORY_BREAKDOWN"]

    for stage in workflow["stages"]:
        instruction = format_artifact_data_contract_instruction(
            "STORY_BREAKDOWN",
            stage["id"],
        )
        contract = stage.get("artifactDataContract")

        assert contract is not None, f"STORY_BREAKDOWN/{stage['id']} missing contract"
        assert (
            "document_info、input_analysis、epics、user_stories、acceptance_criteria、"
            "dependencies、sprint_slices、lisa_handoff_inputs 和 stage_gate 必须齐全；"
            "契约外字段会被拒绝"
        ) in instruction
        assert (
            "input_analysis.target_users、input_analysis.constraints、"
            "input_analysis.open_questions、epics[].dependencies、"
            "dependencies[].related_story_ids 和 sprint_slices[].story_ids "
            "必须至少包含 1 项"
        ) in instruction
        assert "epics[].epic_id 必须唯一" in instruction
        assert "user_stories[].story_id 必须唯一" in instruction
        assert (
            "user_stories[].epic_id 只能引用 epics[].epic_id 中已定义的 Epic ID"
            in instruction
        )
        assert "acceptance_criteria[].criterion_id 必须唯一" in instruction
        assert (
            "acceptance_criteria[].story_id 只能引用 user_stories[].story_id "
            "中已定义的用户故事 ID"
        ) in instruction
        assert "dependencies[].dependency_id 必须唯一" in instruction
        assert (
            "dependencies[].related_story_ids 只能引用 user_stories[].story_id "
            "中已定义的用户故事 ID"
        ) in instruction
        assert "sprint_slices[].sprint_id 必须唯一" in instruction
        assert (
            "sprint_slices[].story_ids 只能引用 user_stories[].story_id "
            "中已定义的用户故事 ID"
        ) in instruction
        assert (
            "user_stories[].sprint 缺省时由后端按 sprint_slices[].story_ids "
            "所属 sprint_slices[].sprint_id 派生"
        ) in instruction
        assert (
            "lisa_handoff_inputs[] 中 input_type 为“用户故事”时 reference_id "
            "只能引用 user_stories[].story_id 中已定义的用户故事 ID"
        ) in instruction
        assert (
            "lisa_handoff_inputs[] 中 input_type 为“验收标准”时 reference_id "
            "只能引用 acceptance_criteria[].criterion_id 中已定义的验收标准 ID"
        ) in instruction
        assert "user_stories[].story_points 必须是大于等于 1 的整数" in instruction
        assert "stage_gate 至少包含一个 checked=true" in instruction
        assert "完整 Markdown 文档" in instruction
        assert "Markdown 表格" in instruction
        assert "Mermaid 代码块" in instruction
        assert "flow-map JSON 代码块" in instruction
        assert "story-map JSON 代码块" in instruction
        assert "右侧用户故事拆解包" in instruction
        assert "ai4se-visual flow-map" in instruction
        assert "ai4se-visual story-map" in instruction


def test_prd_review_artifact_data_contract_manifest_drives_backend_instruction():
    from workflow_manifest import format_artifact_data_contract_instruction

    workflow = _workflow_manifest()["workflows"]["PRD_REVIEW"]
    expected_renderer_outputs = {
        "INVENTORY": ["右侧 PRD 输入盘点", "Mermaid mindmap"],
        "QUALITY_AUDIT": ["右侧 PRD 质量评审", "ai4se-visual score-matrix"],
        "COMPLETION_PLAN": [
            "右侧 PRD 补全建议",
            "ai4se-visual action-board",
            "ai4se-visual roadmap",
        ],
        "REVISION_BLUEPRINT": [
            "右侧 PRD 修订蓝图",
            "ai4se-visual action-board",
            "ai4se-visual roadmap",
        ],
    }

    for stage in workflow["stages"]:
        instruction = format_artifact_data_contract_instruction(
            "PRD_REVIEW",
            stage["id"],
        )
        contract = stage.get("artifactDataContract")

        assert contract is not None, f"PRD_REVIEW/{stage['id']} missing contract"
        assert (
            "document_info、prd_inventory、quality_findings、completion_actions、"
            "revision_sections、acceptance_criteria、handoff_inputs 和 stage_gate "
            "必须齐全；契约外字段会被拒绝"
        ) in instruction
        assert (
            "prd_inventory、quality_findings、completion_actions、revision_sections、"
            "acceptance_criteria、handoff_inputs 和 stage_gate 必须至少包含 1 项"
        ) in instruction
        assert (
            "completion_actions[].finding_ids、acceptance_criteria[].related_section_ids "
            "和 handoff_inputs[].related_section_ids 必须至少包含 1 项"
        ) in instruction
        assert "quality_findings[].finding_id 必须唯一" in instruction
        assert "completion_actions[].action_id 必须唯一" in instruction
        assert "revision_sections[].section_id 必须唯一" in instruction
        assert (
            "completion_actions[].finding_ids 只能引用 quality_findings[].finding_id "
            "中已定义的问题 ID"
        ) in instruction
        assert (
            "acceptance_criteria[].related_section_ids 和 "
            "handoff_inputs[].related_section_ids 只能引用 revision_sections[].section_id "
            "中已定义的修订章节 ID"
        ) in instruction
        assert "stage_gate 至少包含一个 checked=true" in instruction
        assert "完整 Markdown 文档" in instruction
        assert "Markdown 表格" in instruction
        assert "Mermaid 代码块" in instruction
        assert "ai4se-visual JSON 代码块" in instruction
        for renderer_output in expected_renderer_outputs[stage["id"]]:
            assert renderer_output in instruction


def test_workflow_manifest_declares_prompt_template_versions_for_every_stage():
    manifest = _workflow_manifest()

    for workflow_id, workflow in manifest["workflows"].items():
        for stage in workflow["stages"]:
            version = stage.get("promptTemplateVersion")
            assert isinstance(
                version, str
            ), f"{workflow_id}/{stage['id']} missing promptTemplateVersion"
            assert PROMPT_TEMPLATE_VERSION_RE.match(
                version
            ), f"{workflow_id}/{stage['id']} has invalid promptTemplateVersion: {version}"


def test_metadata_footer_stage_prompt_template_versions_match_current_contract():
    from artifact_data_renderers import ARTIFACT_DATA_RENDERERS

    metadata_stage_keys = {
        stage_key
        for stage_key, plan in ARTIFACT_DATA_RENDERERS.items()
        if any(section.role == "metadata" for section in plan.sections)
    }
    manifest = _workflow_manifest()
    versions = {
        (workflow_id, stage["id"]): stage["promptTemplateVersion"]
        for workflow_id, workflow in manifest["workflows"].items()
        for stage in workflow["stages"]
        if (workflow_id, stage["id"]) in metadata_stage_keys
    }

    assert set(versions) == metadata_stage_keys
    assert set(versions.values()) == {"2026.07.16.1"}


def test_workflow_manifest_declares_regression_samples_for_every_stage():
    known_sample_ids = {
        sample["id"] for sample in _prompt_regression_samples()["samples"]
    }
    manifest = _workflow_manifest()

    for workflow_id, workflow in manifest["workflows"].items():
        for stage in workflow["stages"]:
            sample_ids = stage.get("regressionSampleIds")
            assert (
                isinstance(sample_ids, list) and sample_ids
            ), f"{workflow_id}/{stage['id']} missing regressionSampleIds"
            for sample_id in sample_ids:
                assert (
                    sample_id in known_sample_ids
                ), f"{workflow_id}/{stage['id']} references unknown regression sample {sample_id}"


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

    assert (
        "COPY tools/new-agents/workflow_manifest.json /workflow_manifest.json"
        in dockerfile
    )
    assert (
        "COPY tools/new-agents/professional_methods.json /professional_methods.json"
        in dockerfile
    )
    assert (
        "COPY tools/new-agents/prompt_regression_samples.json /prompt_regression_samples.json"
        in dockerfile
    )
    assert (
        "./tools/new-agents/workflow_manifest.json:/workflow_manifest.json:ro"
        in dev_compose
    )
    assert (
        "./tools/new-agents/workflow_manifest.json:/workflow_manifest.json:ro"
        in dev_cn_compose
    )
    assert (
        "./tools/new-agents/professional_methods.json:/professional_methods.json:ro"
        in dev_compose
    )
    assert (
        "./tools/new-agents/professional_methods.json:/professional_methods.json:ro"
        in dev_cn_compose
    )
    assert (
        "./tools/new-agents/prompt_regression_samples.json:/prompt_regression_samples.json:ro"
        in dev_compose
    )
    assert (
        "./tools/new-agents/prompt_regression_samples.json:/prompt_regression_samples.json:ro"
        in dev_cn_compose
    )


def test_frontend_container_packages_shared_workflow_manifest_for_vite_build():
    dockerfile = (NEW_AGENTS_ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")

    assert (
        "COPY tools/new-agents/workflow_manifest.json /workflow_manifest.json"
        in dockerfile
    )
    assert (
        "COPY tools/new-agents/professional_methods.json /professional_methods.json"
        in dockerfile
    )
    assert (
        "COPY tools/new-agents/prompt_regression_samples.json /prompt_regression_samples.json"
        in dockerfile
    )
    assert (
        "COPY tools/new-agents/workflow_manifest.json ./workflow_manifest.json"
        in dockerfile
    )
    assert (
        "COPY tools/new-agents/professional_methods.json ./professional_methods.json"
        in dockerfile
    )
    assert (
        "COPY tools/new-agents/prompt_regression_samples.json ./prompt_regression_samples.json"
        in dockerfile
    )


def test_frontend_templates_include_required_structured_visual_contract_examples():
    for stage_key, visual_types in REQUIRED_ARTIFACT_STRUCTURED_VISUALS.items():
        template = FRONTEND_PROMPT_FILES[stage_key].read_text(encoding="utf-8")
        rendered_template_section = template.split("TEMPLATE = ", maxsplit=1)[1]

        for visual_type in visual_types:
            assert "```ai4se-visual" in template or "${FENCE}ai4se-visual" in template
            assert f'"type": "{visual_type}"' in template
            if visual_type in {"cause-map", "flow-map"}:
                assert '"nodes"' in template
                assert '"edges"' in template
                assert '"columns": ["层级", "问题", "回答"' not in template
            elif visual_type == "timeline-map":
                assert '"events"' in template
                assert '"factIds"' in template
                assert '"columns"' not in template
                assert '"rows"' not in template
            else:
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
