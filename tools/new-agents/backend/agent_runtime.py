from collections.abc import Iterator
from dataclasses import dataclass
import json
import re
from typing import Any

from pydantic import ValidationError

from agent_contracts import (
    AgentTurnOutput,
    ContractValidationError,
    build_stage_action_contract_prompt,
    validate_agent_turn,
)
from artifact_data_renderers import (
    get_artifact_data_renderer_stage_keys,
    render_agent_turn_from_artifact_data,
    render_complete_artifact_data,
    render_partial_artifact_data_markdown,
)
from artifact_data_instruction_registry import (
    ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS,
    DOCUMENT_INFO_RUNTIME_IDENTITY_INSTRUCTION,
)
from llm_client import LlmClientError, stream_chat_completion_content
from safe_error_diagnostics import (
    SAFE_STREAM_TERMINATION_VALIDATORS,
    project_safe_schema_field_path,
)
from sse_schemas import AgentRetrySignal, AgentTurnDeltaOutput
from workflow_manifest import format_visual_protocol_instruction

try:
    from pydantic_ai.exceptions import (
        ModelAPIError,
        ModelHTTPError,
        UnexpectedModelBehavior,
    )
except ImportError:
    ModelAPIError = None
    ModelHTTPError = None
    UnexpectedModelBehavior = None

PYDANTIC_AI_SCHEMA_ERRORS = tuple(
    error_type for error_type in (UnexpectedModelBehavior,) if error_type is not None
)
PYDANTIC_AI_MODEL_ERRORS = tuple(
    error_type
    for error_type in (ModelHTTPError, ModelAPIError)
    if error_type is not None
)


class AgentRuntimeDependencyError(RuntimeError):
    """Raised when the configured agent runtime dependency is unavailable."""


class AgentRuntimeSchemaError(RuntimeError):
    """Raised when PydanticAI cannot produce valid structured output."""


class AgentRuntimeModelError(RuntimeError):
    """Raised when the underlying model provider reports an error."""


@dataclass(frozen=True)
class AgentTurnValidationDeps:
    workflow_id: str
    current_stage_id: str


@dataclass(frozen=True)
class RawStreamingConfig:
    api_key: str
    base_url: str | None
    model_name: str
    system_prompt: str


@dataclass(frozen=True)
class StructuredOutputCapability:
    tier: str
    response_format: dict[str, Any] | None
    max_output_tokens: int | None = None


class RawJsonStreamTerminationError(ValueError):
    SAFE_REASONS = frozenset(SAFE_STREAM_TERMINATION_VALIDATORS)

    def __init__(self, reason: str):
        self.reason = reason if reason in self.SAFE_REASONS else "unknown"
        super().__init__(f"raw JSON stream terminated: {self.reason}")


TEXT_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持前端实时显示，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_update"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经做了什么、本轮确认或假定的关键点、右侧产出物更新了哪些部分、接下来需要用户确认或补充什么。不要复制完整产出物正文。",
  "artifact_update": {
    "type": "replace 或 none",
    "markdown": "当 type 为 replace 时，这里必须是完整 Markdown 产出物"
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "下一阶段内部 ID"},
  "warnings": []
}

chat 字段必须像一次自然的工作对话，不要只用一两句模板化提示；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时可以适度使用短列表；不要每轮套用固定 bullet 数量、固定标签或固定栏目，让左侧对话有独立阅读价值。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""

RAW_JSON_STREAMING_MAX_ATTEMPTS = 3

_SAFE_RETRY_FIELD_PATHS = {
    "artifact_data": "artifact_data",
    "artifact_update": "artifact_update",
    "chat": "chat",
    "stage_action": "stage_action",
    "warnings": "warnings",
}
_SAFE_RETRY_VALIDATORS = frozenset(
    {
        "bool_type",
        "dict_type",
        "enum",
        "extra_forbidden",
        "float_type",
        "int_type",
        "list_type",
        "literal_error",
        "missing",
        "string_too_short",
        "string_type",
        "too_short",
        "union_tag_invalid",
        "union_tag_not_found",
        "value_error",
    }
)
_SAFE_RETRY_PATH_SEGMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_MAX_SAFE_RETRY_PATH_SEGMENTS = 12
_MAX_SAFE_RETRY_FIELD_PATH_LENGTH = 240
_SAFE_RETRY_CORRECTIONS = {
    "blank_string": (
        "所有字符串字段必须使用有意义的非空文本；条件不适用的字段填写“无”、"
        "“不适用”或明确原因，不要输出空字符串。"
    ),
    "clarify_question_status_literal": (
        "clarification_questions[].status 只能从“待确认”“已确认”“已假设”"
        "“AI 假设”中选择一个；用户已明确回答时用“已确认”，用户明确授权代定"
        "场景时用“已假设”，未经授权的临时推断用“AI 假设”，其余用“待确认”。"
    ),
    "delivery_case_count_mismatch": (
        "模型不要输出 case_summary_items[].case_count；"
        "该字段由后端派生，计算规则为 p0_count + p1_count + p2_count。"
    ),
    "delivery_high_risk_count_mismatch": (
        "模型不要输出 delivery_metrics.high_risk_count；"
        "该字段由后端派生，计算规则为 open_risks 中 risk_type 包含“风险”且 "
        "acceptable 不为“是”的条目数量。"
    ),
    "delivery_total_cases_mismatch": (
        "模型不要输出 delivery_metrics.total_cases；"
        "该字段由后端派生，计算规则为 case_summary_items[].case_count 总和。"
    ),
    "too_short": (
        "所有数组（包括嵌套的引用 ID 数组）必须至少包含一项；"
        "引用 ID 必须来自同一 JSON 中对应已定义 ID。"
    ),
    "idea_converge_blank_elimination_reason": (
        "ice_evaluations[].elimination_reason 必须是非空文本；"
        "对于推荐或保留方案填写“不淘汰”并说明保留依据。"
    ),
    "idea_define_empty_evidence_ids": (
        "problem_user_fit[].evidence_ids 必须至少引用一个"
        "已在 evidence_items[].evidence_id 中定义的 ID。"
    ),
    "idea_define_duplicate_evidence_id": (
        "evidence_items[].evidence_id 必须唯一；重复证据应合并内容或分配新的 ID。"
    ),
    "idea_define_duplicate_problem_id": (
        "problem_landscape.subproblems[].problem_id 必须唯一。"
    ),
    "idea_define_duplicate_root_problem_id": (
        "problem_landscape.root_problem_id 不能与任何 "
        "problem_landscape.subproblems[].problem_id 重复。"
    ),
    "idea_define_unknown_problem_reference": (
        "evidence_items[].related_problem_ids 只能引用 "
        "problem_landscape.root_problem_id 或已定义的 "
        "problem_landscape.subproblems[].problem_id。"
    ),
    "idea_define_missing_root_problem_evidence": (
        "至少一个 evidence_items[].related_problem_ids 必须包含 "
        "problem_landscape.root_problem_id。"
    ),
    "idea_define_missing_fit_root_evidence_reference": (
        "至少一个 problem_user_fit[].evidence_ids 必须引用一条 "
        "related_problem_ids 包含 root_problem_id 的 evidence_items[].evidence_id。"
    ),
    "idea_define_unknown_evidence_reference": (
        "problem_user_fit[].evidence_ids 只能引用 evidence_items[].evidence_id"
        " 中已定义的 ID。"
    ),
    "idea_concept_empty_mvp_feature_assumption_ids": (
        "每个 mvp_features[].assumption_ids 必须至少引用一个 "
        "core_assumptions[].assumption_id 中已定义的假设 ID。"
    ),
    "idea_concept_empty_validation_assumption_ids": (
        "每个 validation_roadmap[].assumption_ids 必须至少引用一个 "
        "core_assumptions[].assumption_id 中已定义的假设 ID。"
    ),
    "idea_concept_empty_next_action_related_ids": (
        "每个 next_actions[].related_ids 必须至少引用一个已定义的 "
        "assumption_id、validation_id 或 risk_id。"
    ),
    "incident_improvement_blank_risk_acceptor": (
        "root_cause_coverage[].risk_acceptor 必须是非空文本；"
        "无需风险接受时填写“不适用”并说明覆盖状态。"
    ),
    "incident_improvement_duplicate_action_id": (
        "improvement_actions[].action_id 必须唯一；重复行动应合并或分配新的 ID。"
    ),
    "incident_improvement_action_count_mismatch": (
        "模型不要输出 report_info.action_count；该字段由后端根据 "
        "improvement_actions 的数量派生。"
    ),
    "incident_improvement_priority_distribution_mismatch": (
        "模型不要输出 priority_distribution；该字段由后端根据 "
        "improvement_actions[].priority 派生。"
    ),
    "incident_improvement_duplicate_cause_id": (
        "root_cause_coverage[].cause_id 必须唯一。"
    ),
    "incident_improvement_unknown_action_reference": (
        "root_cause_coverage[].action_ids 只能引用 "
        "improvement_actions[].action_id 中已定义的 ID。"
    ),
    "incident_improvement_unknown_cause_reference": (
        "improvement_actions[].root_cause_id 只能引用 "
        "root_cause_coverage[].cause_id 中已定义的 ID。"
    ),
    "incident_improvement_covered_without_actions": (
        "root_cause_coverage[].coverage_status 为“已覆盖”时，action_ids "
        "必须至少包含一个已定义的行动 ID。"
    ),
    "incident_improvement_action_group_mismatch": (
        "每个 root_cause_coverage[].action_ids 必须精确等于所有 "
        "root_cause_id 为该 cause_id 的 improvement_actions[].action_id。"
    ),
    "stage_gate_unchecked": ("stage_gate 至少包含一个 checked=true 的已满足门禁项。"),
    "journey_duplicate_stage_id": (
        "journey_stages 每一项的 stage_id 必须唯一，并让引用字段使用对应 ID。"
    ),
    "journey_duplicate_pain_id": (
        "journey_stages 每一项的 pain_id 必须唯一；同一痛点跨阶段出现时也要分配不同 ID。"
    ),
    "journey_duplicate_opportunity_id": (
        "journey_stages 每一项的 opportunity_id 必须唯一；同一机会跨阶段出现时也要分配不同 ID。"
    ),
    "journey_unknown_stage_reference": (
        "pain_priorities[].stage_id 必须逐字引用 journey_stages[].stage_id 中已定义的 ID。"
    ),
    "journey_unknown_pain_reference": (
        "pain_priorities 和 opportunity_scores 的 pain_id 必须逐字引用 journey_stages 中已定义的 pain_id。"
    ),
    "journey_unknown_opportunity_reference": (
        "opportunity_scores、entry_strategy 和 validation_experiments 的机会 ID 必须逐字引用 journey_stages 中已定义的 opportunity_id。"
    ),
}


def project_safe_value_error_validator(error_detail: dict[str, Any]) -> str | None:
    location = tuple(error_detail.get("loc") or ())
    if (
        error_detail.get("type") == "literal_error"
        and len(location) == 3
        and location[0] == "clarification_questions"
        and isinstance(location[1], int)
        and location[2] == "status"
    ):
        return "clarify_question_status_literal"
    if error_detail.get("type") == "too_short" and (
        len(location) == 3 and isinstance(location[1], int)
    ):
        return {
            ("mvp_features", "assumption_ids"): (
                "idea_concept_empty_mvp_feature_assumption_ids"
            ),
            ("next_actions", "related_ids"): (
                "idea_concept_empty_next_action_related_ids"
            ),
            ("problem_user_fit", "evidence_ids"): ("idea_define_empty_evidence_ids"),
            ("validation_roadmap", "assumption_ids"): (
                "idea_concept_empty_validation_assumption_ids"
            ),
        }.get((location[0], location[2]))
    if error_detail.get("type") != "value_error":
        return None
    context = error_detail.get("ctx")
    if not isinstance(context, dict):
        return None
    message = str(context.get("error") or "")
    if message == "case_count must equal p0_count + p1_count + p2_count":
        return "delivery_case_count_mismatch"
    if message == (
        "delivery_metrics.total_cases must match case_summary_items total_cases"
    ):
        return "delivery_total_cases_mismatch"
    if message == (
        "delivery_metrics.high_risk_count must match unacceptable open risks"
    ):
        return "delivery_high_risk_count_mismatch"
    if message == "string fields cannot be blank":
        if (
            len(location) == 3
            and location[0] == "ice_evaluations"
            and isinstance(location[1], int)
            and location[2] == "elimination_reason"
        ):
            return "idea_converge_blank_elimination_reason"
        if (
            len(location) == 3
            and location[0] == "root_cause_coverage"
            and isinstance(location[1], int)
            and location[2] == "risk_acceptor"
        ):
            return "incident_improvement_blank_risk_acceptor"
        return "blank_string"
    duplicate_match = re.fullmatch(
        r"journey_stages contains duplicate (stage_id|pain_id|opportunity_id)",
        message,
    )
    if duplicate_match:
        return f"journey_duplicate_{duplicate_match.group(1)}"
    if message.startswith("pain_priorities references unknown stage ids:"):
        return "journey_unknown_stage_reference"
    if message.startswith("journey references unknown pain ids:"):
        return "journey_unknown_pain_reference"
    if message.startswith("journey references unknown opportunity ids:"):
        return "journey_unknown_opportunity_reference"
    if message == "evidence_items contains duplicate evidence_id":
        return "idea_define_duplicate_evidence_id"
    if message == "problem_landscape contains duplicate problem_id":
        return "idea_define_duplicate_problem_id"
    if message == (
        "problem_landscape.root_problem_id duplicates subproblem problem_id"
    ):
        return "idea_define_duplicate_root_problem_id"
    if message.startswith("evidence_items references unknown problem ids:"):
        return "idea_define_unknown_problem_reference"
    if message == (
        "problem_landscape.root_problem_id must be covered by evidence_items"
    ):
        return "idea_define_missing_root_problem_evidence"
    if message == (
        "problem_user_fit must reference evidence covering "
        "problem_landscape.root_problem_id"
    ):
        return "idea_define_missing_fit_root_evidence_reference"
    if message.startswith("problem_user_fit references unknown evidence ids:"):
        return "idea_define_unknown_evidence_reference"
    if message == "improvement_actions contains duplicate action_id":
        return "incident_improvement_duplicate_action_id"
    if message == ("report_info.action_count must match improvement_actions length"):
        return "incident_improvement_action_count_mismatch"
    if message == "priority_distribution must match improvement_actions priorities":
        return "incident_improvement_priority_distribution_mismatch"
    if message == "root_cause_coverage contains duplicate cause_id":
        return "incident_improvement_duplicate_cause_id"
    if message.startswith("root_cause_coverage references unknown action ids:"):
        return "incident_improvement_unknown_action_reference"
    if message.startswith(
        "improvement_actions.root_cause_id references unknown coverage cause ids:"
    ):
        return "incident_improvement_unknown_cause_reference"
    if message.startswith(
        "root_cause_coverage.coverage_status 已覆盖 requires action_ids:"
    ):
        return "incident_improvement_covered_without_actions"
    if message.startswith(
        "root_cause_coverage.action_ids must match improvement_actions grouped "
        "by root_cause_id:"
    ):
        return "incident_improvement_action_group_mismatch"
    if message == "stage_gate must include at least one checked item":
        return "stage_gate_unchecked"
    return None


def project_safe_value_error_field_path(validator: str) -> str:
    return project_safe_schema_field_path(validator)


def project_safe_missing_field_path(error_detail: dict[str, Any]) -> str | None:
    if error_detail.get("type") != "missing":
        return None
    location = tuple(error_detail.get("loc") or ())
    if location in {
        ("stage_action", "type"),
        ("stage_action", "target_stage_id"),
    }:
        return ".".join(location)
    if (
        not location
        or len(location) > _MAX_SAFE_RETRY_PATH_SEGMENTS
        or not any(isinstance(segment, int) for segment in location)
    ):
        return None

    projected_segments: list[str] = []
    for segment in location:
        if isinstance(segment, bool):
            return None
        if isinstance(segment, int):
            if not projected_segments:
                return None
            projected_segments[-1] += "[]"
            continue
        if (
            not isinstance(segment, str)
            or _SAFE_RETRY_PATH_SEGMENT.fullmatch(segment) is None
        ):
            return None
        projected_segments.append(segment)

    if not projected_segments:
        return None
    if projected_segments[0] != "artifact_data":
        projected_segments.insert(0, "artifact_data")
    field_path = ".".join(projected_segments)
    if len(field_path) > _MAX_SAFE_RETRY_FIELD_PATH_LENGTH:
        return None
    return field_path


def get_artifact_data_ready_stages() -> set[tuple[str, str]]:
    return set(ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS)


def supports_artifact_data_rendering(workflow_id: str, current_stage_id: str) -> bool:
    stage_key = (workflow_id, current_stage_id)
    return (
        stage_key in ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS
        and stage_key in get_artifact_data_renderer_stage_keys()
    )


def build_structured_output_instruction(
    workflow_id: str,
    current_stage_id: str,
) -> str:
    stage_key = (workflow_id, current_stage_id)
    instruction = ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS.get(stage_key)
    if instruction is None:
        return TEXT_STRUCTURED_OUTPUT_INSTRUCTION
    document_info_instruction = (
        "\n\n" + DOCUMENT_INFO_RUNTIME_IDENTITY_INSTRUCTION
        if '"document_info"' in instruction
        else ""
    )
    return (
        instruction.rstrip()
        + document_info_instruction
        + "\n\n"
        + format_visual_protocol_instruction()
        + "\n"
    )


def _safe_raw_json_retry_diagnostic(error: Exception) -> tuple[str, str, str]:
    if isinstance(error, RawJsonStreamTerminationError):
        validator = SAFE_STREAM_TERMINATION_VALIDATORS[error.reason]
        return "stream_termination", "response_json", validator
    if isinstance(error, json.JSONDecodeError):
        return "json_syntax", "response_json", "json_decode"
    if isinstance(error, ValidationError):
        errors = error.errors()
        if not errors:
            return (
                "schema_validation",
                "structured_output",
                "pydantic_validation",
            )
        first_error = errors[0]
        projected_validator = project_safe_value_error_validator(first_error)
        if projected_validator is not None:
            return (
                "schema_validation",
                project_safe_value_error_field_path(projected_validator),
                projected_validator,
            )
        projected_missing_path = project_safe_missing_field_path(first_error)
        if projected_missing_path is not None:
            return "schema_validation", projected_missing_path, "missing"
        location = first_error.get("loc") or ()
        top_level = str(location[0]) if location else ""
        field_path = _SAFE_RETRY_FIELD_PATHS.get(
            top_level,
            "structured_output",
        )
        validator_candidate = str(first_error.get("type") or "pydantic_validation")
        validator = (
            validator_candidate
            if validator_candidate in _SAFE_RETRY_VALIDATORS
            else "pydantic_validation"
        )
        return "schema_validation", field_path, validator
    if isinstance(error, ContractValidationError):
        message = str(error)
        if message == "last stage cannot request next stage":
            return (
                "contract_validation",
                "stage_action",
                "terminal_stage_action",
            )
        if message.startswith("invalid target stage:") or message.startswith(
            "target stage must be next stage:"
        ):
            return (
                "contract_validation",
                "stage_action.target_stage_id",
                "stage_transition",
            )
        return "contract_validation", "artifact_contract", "workflow_contract"
    if isinstance(error, ValueError):
        return "artifact_validation", "artifact_data", "artifact_value"
    return "structured_output", "structured_output", "output_validation"


def _format_safe_raw_json_retry_diagnostic(error: Exception) -> str:
    category, field_path, validator = _safe_raw_json_retry_diagnostic(error)
    return (
        f"failureCategory={category}; "
        f"fieldPath={field_path}; "
        f"validator={validator}"
    )


def build_raw_json_retry_prompt(
    prompt: str,
    error: Exception,
    *,
    workflow_id: str | None = None,
    current_stage_id: str | None = None,
) -> str:
    category, field_path, validator = _safe_raw_json_retry_diagnostic(error)
    safe_diagnostic = (
        f"failureCategory={category}; "
        f"fieldPath={field_path}; "
        f"validator={validator}"
    )
    correction = _SAFE_RETRY_CORRECTIONS.get(validator)
    if (
        (field_path == "stage_action" or field_path.startswith("stage_action."))
        and workflow_id is not None
        and current_stage_id is not None
    ):
        correction = build_stage_action_contract_prompt(
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        ).strip()
    if correction is None and validator == "missing" and "." in field_path:
        correction = (
            f"{field_path} 是必填字段；该路径对应的每个对象都必须包含这个字段，"
            "且字符串值必须非空。"
        )
    correction_line = f"\n{correction}" if correction else ""
    if (
        workflow_id is not None
        and current_stage_id is not None
        and supports_artifact_data_rendering(workflow_id, current_stage_id)
    ):
        repair_target = (
            "上述 artifact_data 数据问题"
            if field_path == "artifact_data" or field_path.startswith("artifact_data.")
            else "上述结构化输出问题"
        )
        return (
            f"{prompt}\n\n"
            "【上一轮结构化输出未通过校验】\n"
            f"{safe_diagnostic}{correction_line}\n\n"
            "请立刻重新输出一个完整合法的 JSON 对象，不要输出 JSON 之外的解释。"
            f"必须修正{repair_target}；所有必填字段必须存在，"
            "所有字符串必须非空，数组必须至少包含一项。不要输出 Markdown 文档、"
            "Mermaid、D2、Graphviz DOT、PlantUML 代码块或表格，"
            "后端会根据 artifact_data 渲染右侧产出物。"
        )
    return (
        f"{prompt}\n\n"
        "【上一轮结构化输出未通过校验】\n"
        f"{safe_diagnostic}{correction_line}\n\n"
        "请立刻重新输出一个完整合法的 JSON 对象，不要输出 JSON 之外的解释。"
        "必须修正上述问题；如果当前阶段要求右侧产出物，"
        "artifact_update.type 必须为 replace，markdown 必须包含当前阶段完整 Markdown 文档、"
        "所有必填标题、必需 Mermaid/ai4se-visual 可视化和阶段门禁。"
    )


def register_contract_output_validator(agent: Any) -> None:
    from pydantic_ai.exceptions import ModelRetry

    @agent.output_validator
    def validate_contract(ctx: Any, output: AgentTurnOutput) -> AgentTurnOutput:
        try:
            return validate_agent_turn(
                output,
                workflow_id=ctx.deps.workflow_id,
                current_stage_id=ctx.deps.current_stage_id,
            )
        except ContractValidationError as exc:
            raise ModelRetry(
                "结构化输出不符合业务契约，请重新生成完整合法输出。"
                f"{_format_safe_raw_json_retry_diagnostic(exc)}"
            ) from None


class PydanticAgentRuntime:
    def __init__(
        self,
        agent: Any,
        raw_streaming_config: RawStreamingConfig | None = None,
    ):
        self.agent = agent
        self.raw_streaming_config = raw_streaming_config
        self.last_token_usage: int | None = None

    @staticmethod
    def _coerce_output(output: Any) -> AgentTurnOutput:
        if isinstance(output, AgentTurnOutput):
            return output
        return AgentTurnOutput.model_validate(output)

    @staticmethod
    def _coerce_delta_output(output: Any) -> AgentTurnDeltaOutput:
        if isinstance(output, AgentTurnDeltaOutput):
            return output
        if isinstance(output, AgentTurnOutput):
            return AgentTurnDeltaOutput.model_validate(output.model_dump(mode="json"))
        return AgentTurnDeltaOutput.model_validate(output)

    def run_turn(
        self,
        prompt: str,
        *,
        workflow_id: str,
        current_stage_id: str,
    ) -> AgentTurnOutput:
        try:
            result = self.agent.run_sync(
                prompt,
                deps=AgentTurnValidationDeps(
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                ),
            )
        except PYDANTIC_AI_SCHEMA_ERRORS as exc:
            raise AgentRuntimeSchemaError(str(exc)) from exc
        except PYDANTIC_AI_MODEL_ERRORS as exc:
            raise AgentRuntimeModelError(str(exc)) from exc

        output = result.output
        output = self._coerce_output(output)
        return validate_agent_turn(
            output,
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )

    def stream_turn(
        self,
        prompt: str,
        *,
        workflow_id: str,
        current_stage_id: str,
    ) -> Iterator[AgentRetrySignal | AgentTurnDeltaOutput | AgentTurnOutput]:
        if self.raw_streaming_config is not None:
            try:
                yield from self._stream_raw_json_turn(
                    prompt,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
                return
            except LlmClientError as exc:
                raise AgentRuntimeModelError(str(exc)) from exc
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                raise AgentRuntimeSchemaError(str(exc)) from exc

        if not hasattr(self.agent, "run_stream_sync"):
            yield self.run_turn(
                prompt,
                workflow_id=workflow_id,
                current_stage_id=current_stage_id,
            )
            return

        deps = AgentTurnValidationDeps(
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )
        final_output: AgentTurnOutput | None = None
        try:
            result = self.agent.run_stream_sync(prompt, deps=deps)
            for raw_output in result.stream_output(debounce_by=None):
                try:
                    delta_output = self._coerce_delta_output(raw_output)
                except (ValidationError, ValueError):
                    continue
                if (
                    delta_output.chat is None
                    and delta_output.artifact_update is None
                    and delta_output.stage_action is None
                    and not delta_output.warnings
                ):
                    continue
                try:
                    final_output = self._coerce_output(raw_output)
                    yield final_output
                except (ValidationError, ValueError):
                    yield delta_output
            if final_output is None and hasattr(result, "get_output"):
                final_output = self._coerce_output(result.get_output())
                yield final_output
        except PYDANTIC_AI_SCHEMA_ERRORS as exc:
            raise AgentRuntimeSchemaError(str(exc)) from exc
        except PYDANTIC_AI_MODEL_ERRORS as exc:
            raise AgentRuntimeModelError(str(exc)) from exc

        if final_output is None:
            raise AgentRuntimeSchemaError("PydanticAI stream produced no output")
        validate_agent_turn(
            final_output,
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )

    def _stream_raw_json_turn(
        self,
        prompt: str,
        *,
        workflow_id: str,
        current_stage_id: str,
    ) -> Iterator[AgentRetrySignal | AgentTurnDeltaOutput | AgentTurnOutput]:
        assert self.raw_streaming_config is not None
        config = self.raw_streaming_config
        self.last_token_usage = None
        extra_body = None
        model_settings = build_model_settings(config.model_name)
        if model_settings:
            extra_body = model_settings.get("extra_body")
        structured_output_capability = resolve_structured_output_capability(
            config.model_name
        )

        attempt_prompt = prompt
        for attempt_index in range(RAW_JSON_STREAMING_MAX_ATTEMPTS):
            if attempt_index > 0:
                yield AgentRetrySignal(attemptIndex=attempt_index + 1)
            accumulated = ""
            latest_chat = ""
            latest_markdown = ""
            emitted_any_delta = False
            attempt_token_usage = 0
            finish_reason: str | None = None

            def record_attempt_usage(total_tokens: int) -> None:
                nonlocal attempt_token_usage
                attempt_token_usage = total_tokens

            def record_finish_reason(reason: str) -> None:
                nonlocal finish_reason
                finish_reason = reason

            for text_chunk in stream_chat_completion_content(
                api_key=config.api_key,
                base_url=config.base_url,
                model=config.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            config.system_prompt
                            + build_structured_output_instruction(
                                workflow_id,
                                current_stage_id,
                            )
                        ),
                    },
                    {"role": "user", "content": attempt_prompt},
                ],
                temperature=0,
                response_format=structured_output_capability.response_format,
                extra_body=extra_body,
                max_tokens=structured_output_capability.max_output_tokens,
                on_usage=record_attempt_usage,
                on_finish_reason=record_finish_reason,
            ):
                accumulated += text_chunk
                try:
                    delta = build_partial_agent_delta(
                        accumulated,
                        workflow_id=workflow_id,
                        current_stage_id=current_stage_id,
                    )
                except ValueError:
                    # Partial projections are best effort. The complete payload is
                    # validated below, where renderer failures trigger a safe retry.
                    delta = None
                if delta is None:
                    continue
                next_chat = delta.chat or latest_chat
                next_markdown = (
                    delta.artifact_update.markdown
                    if delta.artifact_update and delta.artifact_update.markdown
                    else latest_markdown
                )
                if not should_emit_partial_delta(
                    latest_chat=latest_chat,
                    next_chat=next_chat,
                    latest_markdown=latest_markdown,
                    next_markdown=next_markdown,
                ):
                    continue
                latest_chat = next_chat
                latest_markdown = next_markdown
                emitted_any_delta = True
                yield delta

            if attempt_token_usage:
                self.last_token_usage = (
                    self.last_token_usage or 0
                ) + attempt_token_usage

            if finish_reason != "stop":
                termination_error = RawJsonStreamTerminationError(
                    finish_reason or "unknown"
                )
                if (
                    finish_reason == "length"
                    and attempt_index < RAW_JSON_STREAMING_MAX_ATTEMPTS - 1
                ):
                    attempt_prompt = build_raw_json_retry_prompt(
                        prompt,
                        termination_error,
                        workflow_id=workflow_id,
                        current_stage_id=current_stage_id,
                    )
                    continue
                raise termination_error

            try:
                final_output = parse_agent_turn_output_text(
                    accumulated,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                if attempt_index >= RAW_JSON_STREAMING_MAX_ATTEMPTS - 1:
                    raise
                attempt_prompt = build_raw_json_retry_prompt(
                    prompt,
                    exc,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
                continue

            try:
                final_output = validate_agent_turn(
                    final_output,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
            except (ContractValidationError, ValidationError) as exc:
                if attempt_index >= RAW_JSON_STREAMING_MAX_ATTEMPTS - 1:
                    raise
                attempt_prompt = build_raw_json_retry_prompt(
                    prompt,
                    exc,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
                continue

            if not emitted_any_delta:
                yield AgentTurnDeltaOutput.model_validate(
                    final_output.model_dump(mode="json")
                )
            yield final_output
            return

        raise AgentRuntimeSchemaError(
            "Raw JSON streaming did not produce valid structured output"
        )


def build_model_settings(model_name: str) -> dict[str, Any] | None:
    if model_name.startswith("deepseek-v4-"):
        return {
            "extra_body": {
                "thinking": {
                    "type": "disabled",
                }
            }
        }
    return None


def build_agent_retries(model_name: str) -> int | None:
    if model_name.startswith("deepseek-v4-"):
        return 3
    return None


def resolve_structured_output_capability(
    model_name: str,
) -> StructuredOutputCapability:
    if model_name.startswith("deepseek-v4-"):
        return StructuredOutputCapability(
            tier="json_object_only",
            response_format={"type": "json_object"},
            max_output_tokens=32768,
        )
    return StructuredOutputCapability(
        tier="json_object_only",
        response_format={"type": "json_object"},
    )


def strip_json_fence(text: str) -> str:
    stripped = text.strip()
    fence_match = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fence_match:
        return fence_match.group(1).strip()
    return stripped


def parse_agent_turn_output_text(
    text: str,
    *,
    workflow_id: str | None = None,
    current_stage_id: str | None = None,
) -> AgentTurnOutput:
    parsed = json.loads(strip_json_fence(text))
    if "artifact_data" in parsed:
        if workflow_id is None or current_stage_id is None:
            raise ValueError(
                "workflow_id and current_stage_id are required for artifact_data"
            )
        rendered = render_agent_turn_from_artifact_data(
            parsed,
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )
        if rendered is None:
            raise ValueError(
                f"artifact_data renderer is not configured for {workflow_id}/{current_stage_id}"
            )
        return rendered
    return AgentTurnOutput.model_validate(parsed)


def extract_json_string_prefix(text: str, key: str) -> str | None:
    key_match = re.search(rf'"{re.escape(key)}"\s*:', text)
    if not key_match:
        return None
    index = key_match.end()
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] != '"':
        return None
    index += 1
    chars: list[str] = []
    while index < len(text):
        char = text[index]
        if char == '"':
            return "".join(chars)
        if char != "\\":
            chars.append(char)
            index += 1
            continue

        index += 1
        if index >= len(text):
            break
        escape = text[index]
        if escape == "n":
            chars.append("\n")
        elif escape == "r":
            chars.append("\r")
        elif escape == "t":
            chars.append("\t")
        elif escape == "b":
            chars.append("\b")
        elif escape == "f":
            chars.append("\f")
        elif escape in {'"', "\\", "/"}:
            chars.append(escape)
        elif escape == "u":
            hex_value = text[index + 1 : index + 5]
            if len(hex_value) < 4 or not re.fullmatch(r"[0-9a-fA-F]{4}", hex_value):
                break
            chars.append(chr(int(hex_value, 16)))
            index += 4
        else:
            chars.append(escape)
        index += 1
    return "".join(chars) if chars else None


def build_partial_agent_delta(
    text: str,
    *,
    workflow_id: str | None = None,
    current_stage_id: str | None = None,
) -> AgentTurnDeltaOutput | None:
    chat = extract_json_string_prefix(text, "chat")
    markdown = extract_json_string_prefix(text, "markdown")
    if not markdown and re.search(r'"artifact_data"\s*:', text):
        markdown = build_artifact_data_progress_markdown(
            text,
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )
    if not chat and not markdown:
        return None
    return AgentTurnDeltaOutput(
        chat=chat,
        artifact_update=(
            {"type": "replace", "markdown": markdown} if markdown else None
        ),
    )


def build_artifact_data_progress_markdown(
    text: str,
    *,
    workflow_id: str | None = None,
    current_stage_id: str | None = None,
) -> str | None:
    complete_markdown = render_complete_streamed_artifact_data_markdown(
        text,
        workflow_id=workflow_id,
        current_stage_id=current_stage_id,
    )
    if complete_markdown:
        return complete_markdown
    return render_partial_streamed_artifact_data_markdown(
        text,
        workflow_id=workflow_id,
        current_stage_id=current_stage_id,
    )


def extract_complete_json_value_after_key(text: str, key: str) -> Any | None:
    key_match = re.search(rf'"{re.escape(key)}"\s*:', text)
    if key_match is None:
        return None
    index = key_match.end()
    while index < len(text) and text[index].isspace():
        index += 1
    try:
        value, _ = json.JSONDecoder().raw_decode(text[index:])
    except json.JSONDecodeError:
        return None
    return value


def extract_partial_json_object_after_key(text: str, key: str) -> dict[str, Any] | None:
    key_match = re.search(rf'"{re.escape(key)}"\s*:', text)
    if key_match is None:
        return None
    index = key_match.end()
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] != "{":
        return None

    decoder = json.JSONDecoder()
    index += 1
    partial: dict[str, Any] = {}
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index < len(text) and text[index] == ",":
            index += 1
            continue
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text) or text[index] == "}":
            break

        try:
            field_name, next_index = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            break
        if not isinstance(field_name, str):
            break
        index += next_index

        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text) or text[index] != ":":
            break
        index += 1
        while index < len(text) and text[index].isspace():
            index += 1

        try:
            field_value, next_index = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            break
        partial[field_name] = field_value
        index += next_index

    return partial or None


def render_complete_streamed_artifact_data_markdown(
    text: str,
    *,
    workflow_id: str | None,
    current_stage_id: str | None,
) -> str | None:
    if workflow_id is None or current_stage_id is None:
        return None
    artifact_data = extract_complete_json_value_after_key(text, "artifact_data")
    if artifact_data is None:
        return None
    try:
        rendered = render_complete_artifact_data(
            artifact_data,
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )
    except (ValidationError, ValueError):
        return None
    return rendered.markdown


def render_partial_streamed_artifact_data_markdown(
    text: str,
    *,
    workflow_id: str | None,
    current_stage_id: str | None,
) -> str | None:
    if workflow_id is None or current_stage_id is None:
        return None
    artifact_data = extract_partial_json_object_after_key(text, "artifact_data")
    if artifact_data is None:
        return None
    return render_partial_artifact_data_markdown(
        artifact_data,
        workflow_id=workflow_id,
        current_stage_id=current_stage_id,
    )


def should_emit_partial_delta(
    *,
    latest_chat: str,
    next_chat: str,
    latest_markdown: str,
    next_markdown: str,
) -> bool:
    if next_chat == latest_chat and next_markdown == latest_markdown:
        return False
    if not latest_chat and next_chat:
        return True
    if not latest_markdown and next_markdown:
        return True
    if len(next_chat) - len(latest_chat) >= 4:
        return True
    if next_chat != latest_chat and next_chat.endswith(("。", "！", "？", "\n")):
        return True
    if len(next_markdown) - len(latest_markdown) >= 32:
        return True
    if next_markdown.count("\n") > latest_markdown.count("\n"):
        return True
    return False


def build_pydantic_agent_runtime(
    *,
    api_key: str,
    base_url: str,
    model_name: str,
    system_prompt: str,
) -> PydanticAgentRuntime:
    try:
        from pydantic_ai import Agent
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
    except ImportError as exc:
        raise AgentRuntimeDependencyError(
            "pydantic-ai-slim[openai] is required for PydanticAgentRuntime; "
            "install tools/new-agents/backend/requirements.txt"
        ) from exc

    model = OpenAIChatModel(
        model_name,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        settings=build_model_settings(model_name),
    )
    agent = Agent(
        model,
        deps_type=AgentTurnValidationDeps,
        output_type=AgentTurnOutput,
        system_prompt=system_prompt,
        retries=build_agent_retries(model_name),
    )
    register_contract_output_validator(agent)
    return PydanticAgentRuntime(
        agent,
        raw_streaming_config=RawStreamingConfig(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            system_prompt=system_prompt,
        ),
    )
