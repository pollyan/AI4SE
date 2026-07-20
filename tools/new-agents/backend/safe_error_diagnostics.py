"""Shared safe field projections for structured-output diagnostics."""

from types import MappingProxyType

SAFE_STREAM_TERMINATION_VALIDATORS = MappingProxyType(
    {
        "content_filter": "content_filtered",
        "insufficient_system_resource": "provider_resource_exhausted",
        "length": "output_truncated",
        "tool_calls": "unexpected_tool_call",
        "unknown": "stream_termination",
    }
)
SAFE_RESPONSE_SCHEMA_VALIDATORS = frozenset(
    {"json_decode", *SAFE_STREAM_TERMINATION_VALIDATORS.values()}
)

SAFE_SCHEMA_FIELD_PATHS = MappingProxyType(
    {
        "clarify_question_status_literal": (
            "artifact_data.clarification_questions[].status"
        ),
        "delivery_case_count_mismatch": "artifact_data.case_summary_items[].case_count",
        "delivery_high_risk_count_mismatch": (
            "artifact_data.delivery_metrics.high_risk_count"
        ),
        "delivery_total_cases_mismatch": "artifact_data.delivery_metrics.total_cases",
        "idea_define_duplicate_root_problem_id": (
            "artifact_data.problem_landscape.root_problem_id"
        ),
        "idea_define_missing_fit_root_evidence_reference": (
            "artifact_data.problem_user_fit[].evidence_ids"
        ),
        "idea_define_missing_root_problem_evidence": (
            "artifact_data.evidence_items[].related_problem_ids"
        ),
        "idea_define_unknown_problem_reference": (
            "artifact_data.evidence_items[].related_problem_ids"
        ),
        "idea_concept_empty_mvp_feature_assumption_ids": (
            "artifact_data.mvp_features[].assumption_ids"
        ),
        "idea_concept_empty_next_action_related_ids": (
            "artifact_data.next_actions[].related_ids"
        ),
        "idea_concept_empty_validation_assumption_ids": (
            "artifact_data.validation_roadmap[].assumption_ids"
        ),
        "incident_improvement_action_count_mismatch": (
            "artifact_data.report_info.action_count"
        ),
        "incident_improvement_action_group_mismatch": (
            "artifact_data.root_cause_coverage[].action_ids"
        ),
        "incident_improvement_covered_without_actions": (
            "artifact_data.root_cause_coverage[].action_ids"
        ),
        "incident_improvement_duplicate_action_id": (
            "artifact_data.improvement_actions[].action_id"
        ),
        "incident_improvement_duplicate_cause_id": (
            "artifact_data.root_cause_coverage[].cause_id"
        ),
        "incident_improvement_priority_distribution_mismatch": (
            "artifact_data.priority_distribution"
        ),
        "incident_improvement_unknown_action_reference": (
            "artifact_data.root_cause_coverage[].action_ids"
        ),
        "incident_improvement_unknown_cause_reference": (
            "artifact_data.improvement_actions[].root_cause_id"
        ),
    }
)


def project_safe_schema_field_path(validator: str) -> str:
    if validator == "extra_forbidden":
        return "artifact_data.extra_field"
    if validator in SAFE_RESPONSE_SCHEMA_VALIDATORS:
        return "response_json"
    return SAFE_SCHEMA_FIELD_PATHS.get(validator, "artifact_data")
