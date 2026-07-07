from collections.abc import Iterator
from dataclasses import dataclass
import json
import re
from typing import Any

from pydantic import ValidationError

from agent_contracts import (
    AgentTurnOutput,
    ContractValidationError,
    validate_agent_turn,
)
from artifact_data_renderers import (
    render_agent_turn_from_artifact_data,
    render_partial_agent_turn_from_artifact_data,
)
from llm_client import LlmClientError, stream_chat_completion_content
from sse_schemas import AgentTurnDeltaOutput

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

chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""

RAW_JSON_STREAMING_MAX_ATTEMPTS = 2


ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经做了什么、本轮确认或假定的关键点、右侧产出物会更新哪些部分、接下来需要用户确认或补充什么。不要复制完整产出物正文。",
  "artifact_data": {
    "document_info": {"artifact_name": "...", "workflow": "TEST_DESIGN", "stage": "CLARIFY", "status": "..."},
    "requirement_facts": [{"fact_id": "F-001", "fact": "...", "source": "...", "evidence_level": "...", "status": "..."}],
    "system_boundaries": [{"boundary_type": "...", "content": "...", "testing_meaning": "...", "status": "..."}],
    "business_rules": [{"rule_id": "BR-001", "rule": "...", "trigger": "...", "state_transition": "...", "exception_handling": "...", "acceptance": "...", "status": "..."}],
    "flow_links": [{"from_node": "用户", "to_node": "登录页", "label": "打开入口"}],
    "clarification_questions": [{"question_id": "Q-001", "question": "...", "priority": "P1", "blocking": "阻断/非阻断", "impact": "...", "assumption": "...", "owner": "...", "status": "..."}],
    "quality_requirements": [{"dimension": "...", "requirement_or_assumption": "...", "metric": "...", "risk": "...", "status": "..."}],
    "downstream_inputs": [{"input_type": "...", "input_id": "...", "content": "...", "source": "...", "usage": "..."}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "STRATEGY"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；不要输出完整 Markdown、Mermaid 代码块或表格，后端会负责确定性渲染右侧产出物。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""

STRATEGY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经做了什么、本轮确认或假定的关键点、右侧测试策略蓝图会更新哪些部分、接下来需要用户确认或补充什么。不要复制完整产出物正文。",
  "artifact_data": {
    "document_info": {"artifact_name": "...", "workflow": "TEST_DESIGN", "stage": "STRATEGY", "status": "..."},
    "strategy_summary": {"conclusion": "...", "basis": "F-001 / BR-001 / R-SEED-001", "case_stage_readiness": "可进入/暂缓进入/需补充策略输入"},
    "quality_goals": [{"goal_id": "QG-001", "goal": "...", "metric": "...", "source": "...", "priority": "P0", "status": "..."}],
    "risks": [{"risk_id": "R-001", "name": "...", "failure_mode": "...", "impact": "...", "source": "...", "severity": 5, "occurrence": 3, "detection": 4, "mitigation": "...", "coverage": "...", "status": "待覆盖/已覆盖/风险接受"}],
    "test_techniques": [{"technique_id": "TS-001", "target": "QG-001 / R-001", "category": "...", "technique": "...", "reason": "...", "applies_to": "R-001 / TP-001"}],
    "test_layers": [{"layer": "单元测试/集成测试/E2E 测试", "ratio": "40%", "scope": "...", "related": "R-001 / TP-001", "tools": "...", "entry_condition": "..."}],
    "test_points": [{"point_id": "TP-001", "point": "...", "priority": "P0", "quality_goal": "QG-001", "risk": "R-001", "technique": "TS-001", "layer": "单元/集成/E2E", "estimated_cases": 6, "coverage": "...", "status": "待生成用例"}],
    "tradeoffs": [{"item": "...", "decision": "...", "impact": "...", "owner": "...", "status": "..."}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "CASES"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；severity、occurrence、detection 必须是 1 到 5 的整数；RPN 由后端根据 severity * occurrence * detection 计算，不需要在 risks 中输出 rpn。不要输出完整 Markdown、Mermaid 代码块、risk-board JSON 代码块或表格，后端会负责确定性渲染右侧测试策略蓝图、quadrantChart、block-beta 和 ai4se-visual risk-board。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""

CASES_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经生成哪些用例、覆盖了哪些测试点、哪些环境或数据仍需确认。不要复制完整产出物正文。",
  "artifact_data": {
    "document_info": {"artifact_name": "...", "workflow": "TEST_DESIGN", "stage": "CASES", "status": "..."},
    "case_statistics": {"total": 2, "p0_count": 1, "p1_count": 1, "p2_count": 0},
    "design_bases": [{"basis_id": "BASIS-001", "source_type": "质量目标/风险/测试点/业务规则", "source_id": "TP-001", "basis": "...", "case_direction": "正向/异常/边界/安全/性能"}],
    "case_groups": [{"dimension": "正向功能验证", "cases": [{"case_id": "TC-001", "title": "...", "priority": "P0", "dimension": "正向功能验证", "test_point": "TP-001 登录主链路", "risk": "R-001", "precondition": "...", "steps": "1. ... 2. ...", "test_data": "...", "expected_result": "...", "assertion": "...", "execution_layer": "单元/集成/E2E/探索", "automation_suggestion": "优先自动化/可自动化/暂不自动化", "status": "草稿/待确认/可执行/需补环境"}]}],
    "test_data_environments": [{"data_id": "DATA-001", "type": "测试账号/业务数据/配置/第三方依赖/环境", "content": "...", "preparation": "人工准备/脚本构造/mock/现网只读", "related_cases": "TC-001", "status": "已具备/待准备/需确认"}],
    "automation_candidates": [{"candidate_id": "AUTO-001", "case_id": "TC-001", "recommended_layer": "单元/集成/E2E", "value": "...", "prerequisite": "...", "risk_or_limit": "...", "status": "推荐/暂缓/不建议"}],
    "coverage_trace": [{"test_point": "登录主链路", "priority": "P0", "risk": "R-001", "covered_cases": ["TC-001"], "status": "已覆盖/部分覆盖/未覆盖"}],
    "open_questions": [{"question_id": "CASE-Q-001", "question": "...", "related": "TC-001 / TP-001", "priority": "P1", "blocking": "阻断/非阻断", "owner": "产品/研发/测试/用户确认", "status": "待确认/已确认"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "DELIVERY"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；case_statistics 必须与 case_groups 中的用例总数和 P0/P1/P2 计数一致；coverage_trace.covered_cases 只能引用已存在的 case_id。不要输出完整 Markdown、Mermaid 代码块、traceability-matrix JSON 代码块或表格，后端会负责确定性渲染右侧测试用例集和 ai4se-visual traceability-matrix。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


DELIVERY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经整合哪些需求、策略和用例结论，交付文档是否可评审/可签署，哪些风险仍需确认。不要复制完整产出物正文。",
  "artifact_data": {
    "document_info": {"artifact_name": "...", "workflow": "TEST_DESIGN", "stage": "DELIVERY", "status": "..."},
    "delivery_metrics": {"project_name": "...", "version": "v1.0", "generated_at": "YYYY-MM-DD", "delivery_status": "草稿/待评审/可签署/需补充", "total_cases": 2, "high_risk_count": 1},
    "executive_summary": [{"summary_item": "测试范围/核心风险/用例覆盖/交付判断", "conclusion": "...", "evidence_source": "CLARIFY / STRATEGY / CASES / 阶段门禁", "status": "已确认/待确认/可签署/需补充"}],
    "requirement_summary": [{"content_type": "事实/业务规则/链路/澄清问题", "reference": "F-001 / BR-001 / PATH-001 / Q-001", "conclusion": "...", "open_status": "已确认/待确认/AI 假设/已关闭"}],
    "strategy_summary_items": [{"strategy_item": "质量目标/高风险项/测试分层/资源取舍", "conclusion": "...", "related": "QG-001 / R-001 / TP-001", "coverage_status": "已覆盖/部分覆盖/风险接受/待确认"}],
    "case_summary_items": [{"dimension": "正向功能验证", "case_count": 1, "p0_count": 1, "p1_count": 0, "p2_count": 0, "automation_candidates": 1, "blocked_or_needs_env": 0}],
    "coverage_map": [{"requirement": "REQ-1", "risk": "R-001", "test_point": "TP-001", "case_ids": ["TC-001"], "acceptance_status": "已覆盖/部分覆盖/风险接受/待确认"}],
    "open_risks": [{"risk_id": "OPEN-001", "risk_type": "需求问题/风险接受/环境缺口/数据缺口", "description": "...", "impact": "...", "acceptable": "是/否/需确认", "owner": "产品/研发/测试/用户确认", "next_step": "...", "status": "待处理/已接受/已关闭"}],
    "acceptance_checklist": [{"checked": true, "item": "..."}],
    "signoffs": [{"role": "产品负责人/研发负责人/测试负责人", "owner": "...", "opinion": "通过/有条件通过/不通过", "status": "待签署/已签署"}],
    "change_log": [{"version": "v1.0", "date": "YYYY-MM-DD", "change": "...", "reason": "...", "owner": "..."}]
  },
  "stage_action": null,
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；case_summary_items 中每项 case_count 必须等于 p0_count + p1_count + p2_count；delivery_metrics.total_cases 必须等于所有 case_summary_items.case_count 之和；coverage_map.case_ids 必须至少包含一个用例 ID。coverage_map 必须覆盖需求、风险、测试点、用例和验收状态，后端会同时渲染 ai4se-visual coverage-map 与 traceability-matrix。不要输出完整 Markdown、Mermaid 代码块、coverage-map / traceability-matrix JSON 代码块或表格。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


REQ_REVIEW_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经完成哪些需求质量扫描、发现了哪些 P0/P1/P2 问题、右侧问题清单会更新哪些内容、进入报告阶段前还需要 PM 或研发确认什么。不要复制完整产出物正文。",
  "artifact_data": {
    "review_info": {"artifact_name": "需求质量诊断与评审问题清单", "requirement_name": "...", "review_date": "YYYY-MM-DD", "requirement_summary": "...", "conclusion": "可进入报告/需补充需求/存在阻断问题"},
    "scope_items": [{"scope_type": "评审范围/不评审范围", "content": "...", "review_impact": "...", "status": "已确认/AI 假设/待确认"}],
    "quality_overview": [{"dimension": "可测试性/功能完整性/边界与规则定义/异常场景与闭环/非功能性需求/依赖与环境/需求一致性", "quality_judgement": "清晰/部分缺失/严重缺失", "severity_score": 5, "evidence": "...", "testing_risk": "...", "status": "待 PM 确认/需研发判断/已确认"}],
    "issue_statistics": {"p0_count": 1, "p1_count": 1, "p2_count": 0, "p0_description": "必须在开发前解答，否则无法测试", "p1_description": "建议在开发前明确，否则可能返工", "p2_description": "优化性建议，可排入后续迭代"},
    "issue_groups": [{"dimension": "可测试性", "issues": [{"issue_id": "Q-001", "dimension": "可测试性", "description": "...", "priority": "P0", "blocking": "阻断/非阻断", "requirement_section": "...", "impact": "...", "evidence": "...", "suggestion": "...", "owner": "PM/研发/测试/业务方", "status": "待 PM 确认/需研发判断/已确认/非阻断"}]}],
    "revision_suggestions": [{"suggestion_id": "FIX-001", "related_issues": ["Q-001"], "suggestion": "...", "acceptance": "...", "owner": "PM/研发/测试/业务方", "status": "待处理/已确认/已关闭"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "REPORT"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；quality_overview.severity_score 必须是 1 到 5 的整数；issue_statistics 的 P0/P1/P2 数量必须与 issue_groups 中的问题优先级计数一致；revision_suggestions.related_issues 只能引用已存在的 issue_id。不要输出完整 Markdown、Mermaid 代码块、score-matrix JSON 代码块或表格，后端会负责确定性渲染右侧需求评审问题清单、flowchart 和 ai4se-visual score-matrix。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


REQ_REVIEW_REPORT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经形成什么评审结论、P0/P1/P2 问题关闭状态、复审条件和签署状态。不要复制完整产出物正文。",
  "artifact_data": {
    "conclusion": {"artifact_name": "可签署需求评审报告", "review_result": "通过/有条件通过/不通过", "reason": "...", "development_gate": "允许/有条件允许/暂缓", "needs_recheck": "是/否", "summary": "..."},
    "review_info": {"requirement_name": "...", "review_date": "YYYY-MM-DD", "review_input": "REVIEW 阶段问题清单版本/需求文档版本", "participants": "产品 / 研发 / 测试 / 业务方"},
    "issue_statistics": {"p0_count": 1, "p1_count": 1, "p2_count": 0},
    "issue_closures": [{"issue_id": "Q-001", "priority": "P0", "description": "...", "requirement_section": "...", "impact": "...", "owner": "PM/研发/测试/业务方", "next_step": "...", "closure_status": "待修订/已关闭/风险接受/待排期/不处理", "recheck_condition": "..."}],
    "review_conditions": [{"condition_id": "RC-001", "condition": "...", "related_issues": ["Q-001"], "verification": "...", "owner": "产品/测试/研发", "status": "待满足/已满足"}],
    "signoffs": [{"role": "产品负责人/研发负责人/测试负责人", "owner": "...", "opinion": "通过/有条件通过/不通过", "status": "待签署/已签署"}],
    "change_log": [{"version": "v1.0", "date": "YYYY-MM-DD", "change": "...", "reason": "...", "owner": "..."}]
  },
  "stage_action": null,
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；issue_statistics 的 P0/P1/P2 数量必须与 issue_closures 中的问题优先级计数一致；review_conditions.related_issues 只能引用已存在的 issue_id；存在未关闭 P0/P1 问题时 review_result 不能为“通过”。不要输出完整 Markdown、Mermaid 代码块、priority-board JSON 代码块或表格，后端会负责确定性渲染右侧需求评审报告、pie 和 ai4se-visual priority-board。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


VALUE_ELEVATOR_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经澄清哪些价值定位信息、哪些内容是已确认事实/AI 假设/待验证项、右侧价值定位分析会更新哪些部分。不要复制完整产出物正文。",
  "artifact_data": {
    "document_info": {"artifact_name": "价值定位诊断报告", "workflow": "VALUE_DISCOVERY", "stage": "ELEVATOR", "status": "可进入用户画像/需补充定位信息/暂缓"},
    "positioning_summary": {"one_liner": "...", "core_user": "...", "core_pain": "...", "unique_value": "...", "current_judgement": "可继续画像分析/需补充定位信息/暂缓"},
    "value_flow": {
      "nodes": [{"node_id": "USER", "label": "目标用户", "description": "..."}, {"node_id": "PAIN", "label": "核心痛点", "description": "..."}],
      "links": [{"from_node": "USER", "to_node": "PAIN", "label": "面临"}]
    },
    "target_scenarios": [{"dimension": "主要用户群体/核心使用场景/现有应对方式/现有方案不足", "description": "...", "evidence_level": "事实证据/用户陈述/合理推断/待验证", "status": "已确认/AI 假设/待验证"}],
    "pain_evidence": [{"pain_id": "PAIN-001", "description": "...", "scene": "...", "impact": "...", "evidence_level": "事实证据/用户陈述/合理推断/待验证", "validation_action": "...", "status": "已确认/AI 假设/待验证"}],
    "differentiators": [{"dimension": "核心优势/用户获益/差异化壁垒", "our_value": "...", "existing_solution": "...", "evidence": "...", "status": "已确认/AI 假设/待验证"}],
    "business_feasibility": [{"dimension": "用户付费意愿/商业模式方向/市场规模感知", "judgement": "...", "basis": "...", "validation_action": "...", "status": "已确认/AI 假设/待验证"}],
    "score_matrix": [{"dimension": "痛点强度", "score": 4, "basis": "...", "next_validation": "..."}, {"dimension": "证据强度", "score": 2, "basis": "...", "next_validation": "..."}],
    "score_summary": {"total_score": 6, "average_score": 3.0, "judgement": "..."},
    "assumptions": [{"assumption_id": "H-001", "content": "...", "impact": "...", "validation_action": "...", "owner": "产品/业务/用户研究", "status": "待验证/已验证/否定"}],
    "elevator_pitch": "60 秒内能讲完、让外行听懂、能引起兴趣的完整电梯演讲稿。",
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "PERSONA"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；value_flow.links 只能引用 value_flow.nodes 中已存在的 node_id；score_matrix.score 必须是 1 到 5 的整数；score_summary.total_score 必须等于 score_matrix.score 总和；score_summary.average_score 必须等于平均分。不要输出完整 Markdown、Mermaid 代码块、score-matrix JSON 代码块或表格，后端会负责确定性渲染右侧价值定位分析、flowchart 和 ai4se-visual score-matrix。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


VALUE_PERSONA_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经形成哪些画像、哪些画像证据仍待验证、决策链和反画像有什么关键结论。不要复制完整产出物正文。",
  "artifact_data": {
    "document_info": {"artifact_name": "用户画像与决策链分析", "workflow": "VALUE_DISCOVERY", "stage": "PERSONA", "status": "可进入用户旅程/需补充画像证据/暂缓"},
    "persona_summary": {"artifact_name": "用户画像与决策链分析", "core_user_judgement": "...", "primary_pain": "PAIN-001 ...", "validation_status": "已验证/部分验证/待验证", "journey_readiness": "可进入/需补充画像证据/暂缓"},
    "personas": [{
      "persona_id": "PER-001",
      "name": "...",
      "priority": "核心用户/重要用户/潜在用户",
      "summary": "...",
      "basic_features": [{"dimension": "用户类型/人口或企业属性/技术水平/决策角色", "description": "...", "evidence_level": "事实证据/用户陈述/合理推断/待验证", "validation_status": "已验证/部分验证/待验证"}],
      "behavior_features": [{"dimension": "日常工作模式/信息获取方式/决策模式/工具使用习惯", "description": "...", "trigger": "...", "evidence_level": "事实证据/用户陈述/合理推断/待验证", "validation_status": "已验证/部分验证/待验证"}]
    }],
    "behavior_scenarios": [{"scenario_id": "SC-001", "persona_id": "PER-001", "scenario": "...", "trigger": "...", "user_goal": "...", "current_solution": "...", "status": "已验证/AI 假设/待验证"}],
    "decision_chain": [{"role": "使用者/决策者/付费者", "persona_id": "PER-001", "concern": "...", "influence": "高/中/低", "payment_relation": "...", "evidence_level": "事实证据/用户陈述/合理推断/待验证", "validation_status": "已验证/部分验证/待验证"}],
    "pain_evidence": [{"pain_id": "PAIN-001", "persona_id": "PER-001", "pain": "...", "frequency": "...", "impact": "...", "existing_solution_gap": "...", "evidence_level": "事实证据/用户陈述/合理推断/待验证", "validation_status": "已验证/部分验证/待验证"}],
    "anti_personas": [{"name": "...", "reason": "...", "boundary": "...", "risk": "...", "status": "已确认/AI 假设/待验证"}],
    "priority_ranking": [{"priority": "核心用户", "persona_id": "PER-001", "reason": "...", "related_pain": "PAIN-001", "evidence_level": "事实证据/用户陈述/合理推断/待验证", "validation_status": "已验证/部分验证/待验证"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "JOURNEY"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；personas.persona_id 必须唯一；behavior_scenarios、decision_chain、pain_evidence、priority_ranking 中的 persona_id 只能引用 personas 中已存在的 persona_id；priority_ranking 中同一个 persona_id 只能出现一次。不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或解释文字，后端会负责确定性渲染右侧用户画像分析。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


VALUE_JOURNEY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经形成哪些旅程阶段、情绪低谷、关键痛点、机会假设和验证实验。不要复制完整产出物正文。",
  "artifact_data": {
    "document_info": {"artifact_name": "用户旅程与机会地图", "workflow": "VALUE_DISCOVERY", "stage": "JOURNEY", "status": "可进入需求蓝图/需补充旅程证据/暂缓"},
    "journey_summary": {"core_persona": "...", "core_pain": "...", "entry_strategy": "...", "blueprint_readiness": "可进入需求蓝图/需补充旅程证据/暂缓"},
    "journey_stages": [{
      "stage_id": "JS-001",
      "stage_name": "问题认知",
      "user_task": "...",
      "touchpoint": "...",
      "user_goal": "...",
      "user_behavior": "...",
      "emotion_score": 2,
      "emotion_reason": "...",
      "pain_id": "PAIN-001",
      "key_pain": "...",
      "existing_solution_gap": "...",
      "opportunity_id": "OPP-001",
      "opportunity_hypothesis": "...",
      "success_metric": "...",
      "validation_status": "已验证/部分验证/待验证/AI 假设"
    }],
    "pain_priorities": [{"priority_level": "高优先级痛点/中等优先级痛点/低优先级痛点", "pain_id": "PAIN-001", "pain": "...", "stage_id": "JS-001", "impact": "严重/中等/轻微", "frequency": "高频/中频/低频", "existing_solution_gap": "..."}],
    "opportunity_scores": [{"opportunity_id": "OPP-001", "opportunity": "...", "pain_id": "PAIN-001", "value_potential": "高/中/低", "competition_strength": "强/中/弱", "feasibility": "高/中/低", "success_metric": "...", "validation_status": "已验证/部分验证/待验证/AI 假设"}],
    "entry_strategy": [{"strategy_item": "优先切入阶段/暂缓阶段/验证优先级", "content": "...", "related_opportunity": "OPP-001", "tradeoff_reason": "...", "status": "已确认/AI 假设/待验证"}],
    "validation_experiments": [{"experiment_id": "EXP-001", "hypothesis": "...", "opportunity_id": "OPP-001", "method": "访谈/原型测试/Landing Page/数据分析/对照试点", "success_metric": "...", "owner": "产品/用户研究/业务/研发", "status": "待执行/已执行/已否定/部分验证"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "BLUEPRINT"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；journey_stages.stage_id、pain_id、opportunity_id 必须分别唯一；emotion_score 必须是 1 到 5 的整数；pain_priorities.stage_id 只能引用 journey_stages 中已存在的 stage_id；pain_priorities.pain_id 和 opportunity_scores.pain_id 只能引用 journey_stages 中已存在的 pain_id；opportunity_scores.opportunity_id、entry_strategy.related_opportunity、validation_experiments.opportunity_id 只能引用 journey_stages 中已存在的 opportunity_id。不要输出完整 Markdown 文档、Markdown 表格、Mermaid journey 代码块或 journey-map JSON 代码块，后端会负责确定性渲染右侧用户旅程分析、Mermaid journey 和 ai4se-visual journey-map。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


VALUE_BLUEPRINT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经整合哪些前序价值发现成果、形成哪些 P0/P1/P2 需求、哪些验收标准和 Lisa Handoff 输入仍需确认。不要复制完整产出物正文。",
  "artifact_data": {
    "document_info": {"product_name": "...", "version": "v1.0", "created_at": "YYYY-MM-DD", "product_direction": "...", "artifact_name": "可评审需求蓝图", "blueprint_status": "草稿/待确认/可交接 Lisa"},
    "product_overview": {"vision": "...", "positioning_for": "...", "positioning_who": "...", "positioning_product": "...", "positioning_category": "...", "positioning_value": "...", "positioning_unlike": "...", "positioning_differentiator": "...", "user_value": "...", "business_value": "...", "business_model": "..."},
    "target_users": [{"user_type": "...", "core_pain": "...", "priority": "核心用户/重要用户/潜在用户"}],
    "feature_modules": [{"module_id": "MOD-001", "module_name": "...", "features": [{"feature_id": "FTR-001", "feature_name": "...", "requirement_id": "F-001"}]}],
    "requirements": [{"requirement_id": "F-001", "priority": "P0/P1/P2", "name": "...", "user_story": "作为...我想要...以便...", "related_pain": "PAIN-001 或 OPP-001", "scope": "...", "dependency": "...", "acceptance": "...", "testability_level": "高/中/低", "owner": "产品/研发/测试/业务", "status": "已确认/AI 假设/待确认"}],
    "main_flow": {"nodes": [{"node_id": "START", "label": "..."}], "links": [{"from_node": "START", "to_node": "NEXT", "label": "..."}]},
    "success_metrics": [{"metric_type": "业务指标/用户指标/产品指标", "metric_name": "...", "target": "...", "measurement": "..."}],
    "mvp_plan": {"included_features": [{"requirement_id": "F-001", "feature_name": "...", "included": true, "release": "v1.0 MVP"}], "iterations": [{"version": "v1.0 MVP", "time": "...", "core_features": "...", "goal": "..."}]},
    "non_functional_requirements": [{"type": "性能/安全/兼容性/可观测性", "description": "...", "metric_or_constraint": "...", "verification": "...", "owner": "研发/测试/安全/产品", "status": "已确认/AI 假设/待确认"}],
    "acceptance_criteria": [{"acceptance_id": "AC-001", "requirement_id": "F-001", "criterion": "...", "verification": "人工测试/自动化/数据核对/用户访谈", "testability_level": "高/中/低", "owner": "测试/产品/研发", "status": "已确认/待确认"}],
    "roadmap": [{"version": "v1.0 MVP", "time": "4 周", "core_features": "...", "goal": "...", "success_metric": "..."}],
    "risks": [{"risk_type": "市场风险/产品风险/执行风险", "description": "...", "probability": "高/中/低", "impact": "高/中/低", "mitigation": "...", "owner": "产品/业务/研发/测试", "status": "已确认/AI 假设/待确认"}],
    "lisa_handoff_inputs": [{"input_type": "需求/验收标准/风险/数据/依赖", "reference_id": "F-001 或 AC-001 或 RISK-001", "content": "...", "source": "...", "usage": "需求评审 / 测试设计 / 测试断言 / 测试策略风险种子", "status": "已确认/待确认"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null,
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；requirements.requirement_id 必须唯一；feature_modules.features.requirement_id、mvp_plan.included_features.requirement_id、acceptance_criteria.requirement_id 和 input_type 为“需求”的 lisa_handoff_inputs.reference_id 只能引用 requirements 中已存在的 requirement_id；input_type 为“验收标准”的 lisa_handoff_inputs.reference_id 只能引用 acceptance_criteria 中已存在的 acceptance_id；main_flow.links 只能引用 main_flow.nodes 中已存在的 node_id。不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 roadmap JSON 代码块，后端会负责确定性渲染右侧需求蓝图、功能架构、主流程图和 ai4se-visual roadmap。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


USER_STORY_SCOPE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明本轮已经校准哪些需求范围、哪些需求暂不拆、哪些阻塞问题需要补充。不要复制完整产出物正文。",
  "artifact_data": {
    "document_info": {"artifact_name": "用户故事拆解文档", "workflow": "USER_STORY_BREAKDOWN", "stage": "SCOPE", "status": "..."},
    "in_scope_requirements": [{"requirement_id": "REQ-001", "name": "...", "user_value": "...", "priority": "P0/P1/P2", "split_decision": "进入拆分", "status": "已确认/待确认"}],
    "traceability_index": [{"requirement_id": "REQ-001", "source": "需求蓝图章节或用户输入", "target_user": "...", "scenario": "...", "acceptance_hint": "...", "status": "已确认/待确认"}],
    "out_of_scope_items": [{"requirement_id": "REQ-101", "item": "...", "reason": "...", "reentry_condition": "...", "status": "已记录/待确认"}],
    "blocking_questions": [{"question_id": "Q-001", "requirement_id": "REQ-101", "question": "...", "impact": "...", "owner": "产品/业务/用户", "status": "开放/已确认"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "STORY_MAP"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；in_scope_requirements.requirement_id 必须唯一；traceability_index 只能引用进入拆分的 requirement_id；blocking_questions 只能引用已知 requirement_id。不要输出完整 Markdown、Mermaid 代码块或表格，后端会负责确定性渲染拆分范围和需求追溯图。
chat 字段必须像一次自然的工作对话；不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


USER_STORY_MAP_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明本轮已经形成哪些用户活动、任务、故事地图和 MVP / Release Slice。不要复制完整产出物正文。",
  "artifact_data": {
    "document_info": {"artifact_name": "用户故事拆解文档", "workflow": "USER_STORY_BREAKDOWN", "stage": "STORY_MAP", "status": "..."},
    "requirements": [{"requirement_id": "REQ-001", "name": "...", "priority": "P0/P1/P2", "status": "已确认/待确认"}],
    "activities": [{"activity_id": "ACT-001", "activity": "...", "user_goal": "...", "requirement_ids": ["REQ-001"], "priority": "P0"}],
    "tasks": [{"task_id": "TASK-001", "activity_id": "ACT-001", "task": "...", "success_result": "...", "requirement_ids": ["REQ-001"], "status": "已确认/待确认"}],
    "story_map_items": [{"story_id": "US-001", "activity_id": "ACT-001", "task_id": "TASK-001", "title": "...", "requirement_ids": ["REQ-001"], "slice_id": "MVP-001", "status": "候选/待确认"}],
    "mvp_slices": [{"slice_id": "MVP-001", "story_ids": ["US-001"], "business_outcome": "...", "excluded_items": ["..."], "acceptance": "..."}],
    "release_slices": [{"slice_id": "REL-001", "story_ids": ["US-101"], "release_goal": "...", "dependencies": ["..."], "status": "待排期/待确认"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "STORIES"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；activity_id、task_id、story_id、slice_id 必须唯一；所有 activity/task/story/slice 引用必须存在；故事必须保持垂直业务切片，不能拆成技术任务。不要输出完整 Markdown、Mermaid 代码块或表格，后端会负责确定性渲染用户故事地图。
chat 字段必须像一次自然的工作对话；不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


USER_STORIES_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明本轮已经生成哪些 Ready / Not Ready 用户故事、哪些故事还缺什么信息。不要复制完整产出物正文。",
  "artifact_data": {
    "document_info": {"artifact_name": "用户故事拆解文档", "workflow": "USER_STORY_BREAKDOWN", "stage": "STORIES", "status": "..."},
    "requirements": [{"requirement_id": "REQ-001", "name": "...", "priority": "P0/P1/P2", "status": "已确认/待确认"}],
    "split_principles": [{"principle": "垂直业务切片", "applied": "...", "anti_pattern": "不按工程层拆分"}],
    "story_cards": [{"story_id": "US-001", "title": "...", "user_role": "...", "user_goal": "...", "benefit": "...", "requirement_ids": ["REQ-001"], "activity_id": "ACT-001", "task_id": "TASK-001", "business_rules": ["..."], "acceptance_criteria": ["..."], "non_functional_notes": ["..."], "out_of_scope": ["..."], "dependencies": ["..."], "open_questions": ["..."], "status": "ready"}],
    "ready_story_summaries": [{"story_id": "US-001", "ready_reason": "...", "handoff_summary": "...", "acceptance_criteria_count": 3, "concerns": "..."}],
    "not_ready_stories": [{"story_id": "US-101", "requirement_ids": ["REQ-101"], "blocker_reason": "...", "questions": ["..."], "suggested_next_step": "...", "status": "not_ready"}],
    "open_questions": [{"question_id": "Q-001", "story_id": "US-101", "question": "...", "decision_impact": "...", "owner": "产品/业务/用户", "status": "开放/已确认"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "HANDOFF"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；story_cards.story_id 必须唯一；story_cards.requirement_ids 只能引用 requirements 中已存在的 requirement_id；status 只能是 ready 或 not_ready。ready story 必须包含用户故事正文、acceptance_criteria、business_rules 或明确 N/A、不做范围、依赖和 ready 状态；not_ready story 必须包含 blocker_reason、questions 和 not_ready 状态。不要输出技术任务、文件路径、实现计划、测试命令、完整 Markdown 或表格，后端会负责确定性渲染故事卡片。
chat 字段必须像一次自然的工作对话；不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


USER_STORY_HANDOFF_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明哪些 Ready story 可以形成需求包、哪些 Not Ready story 仍被阻塞。不要复制完整产出物正文。",
  "artifact_data": {
    "document_info": {"artifact_name": "单故事 Handoff 清单", "workflow": "USER_STORY_BREAKDOWN", "stage": "HANDOFF", "status": "..."},
    "requirements": [{"requirement_id": "REQ-001", "name": "...", "priority": "P0/P1/P2", "status": "已确认/待确认"}],
    "ready_story_overview": [{"story_id": "US-001", "title": "...", "requirement_ids": ["REQ-001"], "user_value": "...", "ready_reason": "...", "status": "ready"}],
    "single_story_packets": [{"story_id": "US-001", "requirement_ids": ["REQ-001"], "user_story": "作为...我想要...以便...", "acceptance_criteria": ["..."], "business_rules": ["..."], "non_functional_notes": ["..."], "out_of_scope": ["..."], "dependencies": ["..."], "open_questions": ["..."]}],
    "upstream_traceability": [{"story_id": "US-001", "source_workflow": "VALUE_DISCOVERY", "source_stage": "BLUEPRINT", "source_requirements": ["REQ-001"], "source_slice": "MVP-001", "trace_note": "..."}],
    "not_ready_blockers": [{"story_id": "US-101", "requirement_ids": ["REQ-101"], "blocker_reason": "...", "questions": ["..."], "suggested_next_step": "..."}],
    "ai_coding_input_boundary": {"allowed": ["用户故事正文", "来源需求", "业务规则", "验收标准", "不做范围", "依赖", "开放问题"], "forbidden": ["工程实施内容", "代码层设计", "开发任务拆分", "执行类指令"]},
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null,
  "warnings": []
}

artifact_data 中所有字符串必须非空；single_story_packets 只能引用 ready_story_overview 中的 story_id；所有 requirement_ids 必须存在；handoff 清单只能包含需求信息和上游追溯，不得包含实现计划、文件路径、代码任务或测试命令。不要输出完整 Markdown 或表格，后端会负责确定性渲染单故事 Handoff 清单。
chat 字段必须像一次自然的工作对话；不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


INCIDENT_TIMELINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经梳理哪些事故事实、时间线、影响范围和待确认信息。不要复制完整产出物正文。",
  "artifact_data": {
    "incident_summary": {"incident_name": "...", "severity": "P0/P1/P2/P3", "detected_at": "YYYY-MM-DD HH:MM", "recovered_at": "YYYY-MM-DD HH:MM 或 未恢复", "duration": "...", "impact_scope": "...", "current_status": "已恢复/处理中/待确认"},
    "impact_metrics": [{"dimension": "用户影响/业务影响/系统影响/数据影响", "quantification": "...", "confidence": "高/中/低", "source": "...", "status": "已确认/推测/待确认"}],
    "fact_sources": [{"fact_id": "FACT-001", "fact": "...", "source": "监控告警/日志/用户反馈/人工确认/会议记录", "confidence": "高/中/低", "status": "已确认/待确认"}],
    "timeline_events": [{"section": "故障发生/发现与响应/处理与恢复/恢复确认", "occurred_at": "HH:MM 或 YYYY-MM-DD HH:MM", "event": "...", "fact_ids": ["FACT-001"]}],
    "fact_separation": [{"item_type": "事实/推测/待确认", "content": "...", "handling": "...", "blocking": "阻断/非阻断", "status": "已确认/待确认/需补证据"}],
    "fact_summary": ["..."],
    "participants": [{"role": "发现者/一线响应/研发/运维/产品/客服", "person": "...", "action": "...", "participated_at": "HH:MM 或 YYYY-MM-DD HH:MM", "status": "已确认/待确认"}],
    "missing_information": [{"item": "...", "reason": "...", "supplement_method": "...", "blocking": "阻断/非阻断", "owner": "...", "status": "待补充/已补充/风险接受"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "ROOT_CAUSE"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；fact_sources.fact_id 必须唯一；timeline_events.fact_ids 只能引用已存在的 fact_id。不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或解释文字，后端会负责确定性渲染右侧故障复盘报告和 Mermaid timeline，并会处理时间线标签中的半角冒号。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


INCIDENT_ROOT_CAUSE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经完成哪些 5-Why 推理、识别了哪些直接原因/根本原因/促成因素、哪些原因仍待验证。不要复制完整产出物正文。",
  "artifact_data": {
    "analysis_context": {"incident_name": "...", "scope": "...", "upstream_facts": "...", "current_judgement": "..."},
    "why_chain": [{"level": "现象 或 Why-1/Why-2/Why-3", "question": "...", "answer": "...", "cause_type": "现象/技术/流程/人员/环境/度量/管理", "evidence": "...", "evidence_strength": "高/中/低", "confidence": "高/中/低", "actionability": "可行动/不可行动/待判断/不适用", "verification_status": "已确认/待验证/已排除"}],
    "cause_evidence": [{"cause_id": "CAUSE-001", "cause": "...", "related_level": "Why-1", "evidence": "...", "evidence_strength": "高/中/低", "confidence": "高/中/低", "actionability": "可行动/不可行动/待判断", "verification_status": "已确认/待验证/已排除"}],
    "fishbone_categories": [{"category": "技术/流程/人员/环境/度量/管理", "causes": ["..."], "cause_ids": ["CAUSE-001"]}],
    "root_cause_conclusions": [{"conclusion_type": "直接原因/根本原因/促成因素", "description": "...", "category": "技术/流程/人员/环境/度量/管理", "related_cause_id": "CAUSE-001", "evidence_strength": "高/中/低", "confidence": "高/中/低", "actionability": "可行动/不可行动/待判断", "verification_status": "已确认/待验证"}],
    "excluded_causes": [{"exclusion_id": "EX-001", "suspected_cause": "...", "basis": "...", "evidence_strength": "高/中/低", "still_monitor": "是/否"}],
    "unverified_causes": [{"cause": "...", "reason": "...", "possible_impact": "...", "verification_action": "...", "owner": "...", "status": "待验证/已验证/已排除"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "IMPROVEMENT"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；why_chain 至少包含 3 层 Why；cause_evidence.cause_id 必须唯一；fishbone_categories 至少包含 2 个分类；fishbone_categories.cause_ids 和 root_cause_conclusions.related_cause_id 只能引用已存在的 cause_id；root_cause_conclusions 必须包含“根本原因”。不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块、mindmap 或 cause-map JSON 代码块，后端会负责确定性渲染右侧根因分析、Mermaid mindmap 和 ai4se-visual cause-map。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


INCIDENT_IMPROVEMENT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经形成哪些改进行动、根因覆盖、复查计划、遗留风险和签署确认。不要复制完整产出物正文。",
  "artifact_data": {
    "report_info": {"incident_name": "...", "severity": "P0/P1/P2/P3", "version": "v1.0", "generated_at": "YYYY-MM-DD HH:MM", "action_count": 3, "review_date": "YYYY-MM-DD", "closure_status": "待复查/可关闭/暂缓关闭"},
    "timeline_summary": {"key_events": ["..."], "impact_summary": "...", "recovery_summary": "..."},
    "root_cause_summary": {"direct_cause": "...", "root_cause": "...", "contributing_factors": ["..."], "evidence_summary": "..."},
    "priority_distribution": {"urgent_count": 1, "important_count": 1, "normal_count": 1},
    "improvement_actions": [{"action_id": "A-001", "improvement": "...", "action_type": "纠正措施/预防措施/监控改进/流程改进", "root_cause_id": "CAUSE-001", "root_cause_type": "技术/流程/人员/环境/度量/管理", "owner": "...", "deadline": "YYYY-MM-DD", "verification_method": "...", "acceptance_criteria": "...", "priority": "紧急/重要/常规", "status": "待执行/进行中/待验证/已完成", "tracking_method": "..."}],
    "root_cause_coverage": [{"cause_id": "CAUSE-001", "cause_type": "技术/流程/人员/环境/度量/管理", "description": "...", "action_ids": ["A-001"], "coverage_status": "已覆盖/部分覆盖/风险接受", "uncovered_reason": "不适用 或 ...", "risk_acceptor": "..."}],
    "prevention_checklist": [{"item": "...", "related_cause_id": "CAUSE-001", "owner": "...", "status": "待验证/已纳入/风险接受"}],
    "review_plan": [{"review_item": "...", "review_date": "YYYY-MM-DD", "reviewer": "...", "evidence": "...", "pass_criteria": "...", "status": "待复查/通过/未通过"}],
    "residual_risks": [{"risk_id": "RR-001", "risk": "...", "impact": "...", "acceptance_reason": "...", "risk_acceptor": "...", "review_due_date": "YYYY-MM-DD", "status": "有条件接受/待处理/已关闭"}],
    "lessons_learned": [{"lesson_id": "L-001", "lesson": "...", "scope": "...", "sharing_suggestion": "..."}],
    "organizational_learning": [{"learning_item": "...", "audience": "...", "channel": "...", "owner": "...", "due_date": "YYYY-MM-DD", "status": "待宣导/已宣导/待纳入制度"}],
    "signoffs": [{"role": "事故复盘主持人/业务负责人/研发负责人/测试负责人", "owner": "...", "confirmation": "...", "status": "待签署/已签署"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null,
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；report_info.action_count 必须等于 improvement_actions 数量；improvement_actions.action_id 必须唯一；priority_distribution 必须与 improvement_actions.priority 计数一致；root_cause_coverage.action_ids 只能引用已存在的 action_id；improvement_actions.root_cause_id 必须能在 root_cause_coverage.cause_id 中找到。不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块、pie 或 action-board JSON 代码块，后端会负责确定性渲染右侧最终故障复盘报告、Mermaid pie 和 ai4se-visual action-board。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


IDEA_DEFINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经形成哪些问题假设、目标用户、证据状态、验证动作、约束边界和风险思考。不要复制完整产出物正文。",
  "artifact_data": {
    "problem_statement": {"target_user": "...", "scenario": "...", "core_pain": "...", "existing_alternative": "...", "alternative_gap": "...", "consequence": "...", "validation_status": "待验证/部分验证/已验证"},
    "target_users": [{"dimension": "角色定义/核心痛点/痛点频率/现有应对/期望状态/付费意愿", "description": "...", "evidence_level": "事实证据/用户陈述/合理推断/待验证", "validation_status": "已验证/部分验证/待验证"}],
    "problem_landscape": {"root_problem": "...", "subproblems": [{"problem_id": "P-001", "problem": "...", "symptoms": ["..."]}]},
    "evidence_items": [{"evidence_id": "EV-001", "related_problem": "...", "source": "用户访谈/数据/社区讨论/类比案例/AI 假设", "evidence_level": "事实证据/用户陈述/合理推断/待验证", "validation_action": "...", "owner": "产品/用户研究/业务/用户确认", "validation_status": "已验证/部分验证/待验证"}],
    "problem_user_fit": [{"dimension": "问题是否真实存在？/受影响用户群规模/用户是否在主动寻求解决方案？/现有替代方案的满意度", "current_judgement": "...", "evidence_or_assumption": "...", "evidence_ids": ["EV-001"], "validation_action": "...", "validation_status": "已验证/部分验证/待验证"}],
    "constraints_boundaries": [{"boundary_type": "约束/不可做边界", "content": "...", "impact": "...", "status": "已确认/待确认"}],
    "reverse_validation": [{"failure_hypothesis": "...", "trigger_signal": "...", "validation_action": "...", "validation_status": "待验证/部分验证/已验证"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "DIVERGE"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；evidence_items.evidence_id 必须唯一；problem_landscape.subproblems.problem_id 必须唯一；problem_user_fit.evidence_ids 只能引用已存在的 evidence_id；problem_landscape.root_problem 必须被至少一个 evidence_items 或 problem_user_fit 条目覆盖；为稳定通过校验，至少一个 evidence_items.related_problem 必须原样包含 problem_landscape.root_problem，且至少一个 problem_user_fit.evidence_or_assumption 必须原样包含 problem_landscape.root_problem；stage_gate 至少包含一个 checked=true。不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 mindmap，后端会负责确定性渲染右侧问题域分析和 Mermaid mindmap。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


IDEA_DIVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮如何从问题域发散创意、覆盖了哪些发散维度、形成了哪些候选创意、哪些方向被搁置，以及进入收敛前需要用户确认什么。不要复制完整产出物正文。",
  "artifact_data": {
    "divergence_method": {"method_name": "HMW + 类比创新 + 约束反转", "goal": "...", "input_basis": "...", "coverage_dimensions": ["效率提升", "证据收集", "决策辅助"], "constraints": "..."},
    "idea_landscape": {"root_theme": "...", "groups": [{"group_id": "G-001", "theme": "...", "idea_ids": ["ID-001"]}]},
    "idea_cards": [{"idea_id": "ID-001", "title": "...", "one_liner": "...", "target_user": "...", "scenario": "...", "value_proposition": "...", "key_hypotheses": ["..."], "novelty_source": "...", "evidence_level": "事实证据/用户陈述/合理推断/待验证", "validation_action": "...", "status": "候选/待验证/搁置/排除", "status_reason": "..."}],
    "idea_sources": [{"source_id": "SRC-001", "source_type": "问题域证据/HMW/类比案例/约束反转/AI 假设", "source": "...", "idea_ids": ["ID-001"], "key_assumption": "...", "status_reason": "..."}],
    "parked_or_excluded": [{"record_id": "PK-001", "idea_or_direction": "...", "reason": "...", "revisit_condition": "...", "status_reason": "..."}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "CONVERGE"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；idea_cards.idea_id 必须唯一；idea_sources.source_id 必须唯一；parked_or_excluded.record_id 必须唯一；idea_landscape.groups.idea_ids 和 idea_sources.idea_ids 只能引用已存在的 idea_id；stage_gate 至少包含一个 checked=true。不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 mindmap，后端会负责确定性渲染右侧创意发散产物和 Mermaid mindmap。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


IDEA_CONVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮如何对候选创意做收敛评估、推荐了哪个方案、淘汰或暂缓了哪些方向、有哪些资源约束和下一步验证。不要复制完整产出物正文。",
  "artifact_data": {
    "decision_matrix": {"scoring_rubric": "...", "recommended_idea_id": "ID-001", "recommendation": "...", "user_confirmation_status": "待确认/已确认", "decision_items": [{"idea_id": "ID-001", "idea_name": "...", "decision": "推荐方案/备选/暂缓/淘汰", "reason": "...", "evidence_source": "..."}]},
    "ice_evaluations": [{"idea_id": "ID-001", "idea_name": "...", "impact": 5, "confidence": 4, "effort": 2, "ice_score": 10.0, "rank": 1, "conclusion": "推荐方案/备选/暂缓/淘汰", "elimination_reason": "...", "evidence_source": "...", "next_validation": "..."}],
    "resource_constraints": [{"constraint_type": "时间/数据/技术/渠道/预算", "content": "...", "impact": "...", "handling": "...", "status": "已确认/待确认"}],
    "sensitivity_analysis": [{"variable": "...", "change": "...", "impact": "...", "signal": "...", "next_validation": "..."}],
    "validation_experiments": [{"experiment_id": "EXP-001", "idea_ids": ["ID-001"], "goal": "...", "method": "...", "success_metric": "...", "owner": "产品/用户研究/业务/用户确认", "next_validation": "...", "status": "待执行/待排期/进行中/已完成"}],
    "merge_paths": [{"path_id": "MERGE-001", "source_idea_ids": ["ID-001", "ID-002"], "merge_logic": "...", "integrated_concept": "...", "applicable_condition": "...", "risk": "...", "user_confirmation_status": "待确认/已确认"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "CONCEPT"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；ice_evaluations.idea_id 必须唯一；rank 必须唯一；impact、confidence、effort 必须是 1 到 5 的整数；ice_score 必须等于 impact * confidence / effort；decision_matrix.recommended_idea_id、validation_experiments.idea_ids 和 merge_paths.source_idea_ids 只能引用已存在的 idea_id；推荐方案必须同时出现在 ICE 结论和决策矩阵中；stage_gate 至少包含一个 checked=true。不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 quadrantChart，后端会负责确定性渲染右侧收敛聚焦产物和 Mermaid quadrantChart。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


IDEA_CONCEPT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持后端确定性渲染，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_data"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮如何把问题域、创意发散和收敛结论整合成产品概念简报，重点说明定位、MVP、验证路线、不可做范围和下一步行动。不要复制完整产出物正文。",
  "artifact_data": {
    "positioning_statement": {"target_user": "...", "user_need": "...", "product_name": "...", "category": "...", "value_proposition": "...", "alternative": "...", "differentiation": "..."},
    "core_assumptions": [{"assumption_id": "H-001", "assumption": "...", "source": "DEFINE/DIVERGE/CONVERGE", "importance": "高/中/低", "validation_action": "...", "owner": "产品/用户研究/业务/用户确认", "status": "待验证/部分验证/已验证"}],
    "lean_canvas": [{"cell": "问题", "content": "..."}, {"cell": "用户群体", "content": "..."}, {"cell": "独特价值主张", "content": "..."}, {"cell": "解决方案", "content": "..."}, {"cell": "渠道", "content": "..."}, {"cell": "收入来源", "content": "..."}, {"cell": "成本结构", "content": "..."}, {"cell": "关键指标", "content": "..."}, {"cell": "竞争壁垒", "content": "..."}],
    "mvp_features": [{"module": "...", "mvp_level": "P0/P1/P2", "user_value": "...", "validation_metric": "...", "tradeoff_reason": "...", "assumption_ids": ["H-001"], "status": "待验证/待排期/暂缓"}],
    "growth_funnel": [{"stage": "Acquisition", "user_behavior": "...", "metric": "...", "mvp_implementation": "..."}, {"stage": "Activation", "user_behavior": "...", "metric": "...", "mvp_implementation": "..."}, {"stage": "Retention", "user_behavior": "...", "metric": "...", "mvp_implementation": "..."}, {"stage": "Revenue", "user_behavior": "...", "metric": "...", "mvp_implementation": "..."}, {"stage": "Referral", "user_behavior": "...", "metric": "...", "mvp_implementation": "..."}],
    "premortem_risks": [{"risk_id": "R-001", "dimension": "市场风险/产品风险/执行风险", "failure_reason": "...", "likelihood": "高/中/低", "mitigation": "..."}],
    "validation_roadmap": [{"validation_id": "V0", "stage": "问题验证/价值验证/MVP验证", "goal": "...", "experiment": "...", "success_metric": "...", "time_window": "...", "owner": "产品/用户研究/业务/用户确认", "status": "待执行/进行中/已完成", "assumption_ids": ["H-001"]}],
    "out_of_scope": [{"item": "...", "reason": "...", "reconsider_condition": "...", "status": "已确认/待确认"}],
    "decision_records": [{"decision": "推荐概念", "conclusion": "...", "basis": "...", "decider": "角色或用户", "date": "YYYY-MM-DD", "status": "已确认/待确认"}],
    "next_actions": [{"action_id": "ACT-001", "action": "...", "related_ids": ["H-001", "V0", "R-001"], "owner": "产品/用户研究/业务/用户确认", "due_date": "YYYY-MM-DD", "acceptance": "...", "status": "待开始/进行中/已完成"}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null,
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；core_assumptions.assumption_id、validation_roadmap.validation_id 和 next_actions.action_id 必须唯一；lean_canvas 必须覆盖问题、用户群体、独特价值主张、解决方案、渠道、收入来源、成本结构、关键指标和竞争壁垒；growth_funnel 必须覆盖 Acquisition、Activation、Retention、Revenue 和 Referral；mvp_features.assumption_ids 和 validation_roadmap.assumption_ids 只能引用已存在的 assumption_id；next_actions.related_ids 只能引用已存在的 assumption_id、validation_id 或 risk_id；stage_gate 至少包含一个 checked=true。不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块、pie、flowchart 或 ai4se-visual mvp-map，后端会负责确定性渲染右侧产品概念简报、Mermaid 图和 mvp-map。
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


def supports_artifact_data_rendering(workflow_id: str, current_stage_id: str) -> bool:
    return (workflow_id, current_stage_id) in {
        ("IDEA_BRAINSTORM", "DEFINE"),
        ("IDEA_BRAINSTORM", "DIVERGE"),
        ("IDEA_BRAINSTORM", "CONVERGE"),
        ("IDEA_BRAINSTORM", "CONCEPT"),
        ("TEST_DESIGN", "CLARIFY"),
        ("TEST_DESIGN", "STRATEGY"),
        ("TEST_DESIGN", "CASES"),
        ("TEST_DESIGN", "DELIVERY"),
        ("REQ_REVIEW", "REVIEW"),
        ("REQ_REVIEW", "REPORT"),
        ("VALUE_DISCOVERY", "ELEVATOR"),
        ("VALUE_DISCOVERY", "PERSONA"),
        ("VALUE_DISCOVERY", "JOURNEY"),
        ("VALUE_DISCOVERY", "BLUEPRINT"),
        ("USER_STORY_BREAKDOWN", "SCOPE"),
        ("USER_STORY_BREAKDOWN", "STORY_MAP"),
        ("USER_STORY_BREAKDOWN", "STORIES"),
        ("USER_STORY_BREAKDOWN", "HANDOFF"),
        ("INCIDENT_REVIEW", "TIMELINE"),
        ("INCIDENT_REVIEW", "ROOT_CAUSE"),
        ("INCIDENT_REVIEW", "IMPROVEMENT"),
    }


def prioritize_artifact_data_for_visible_streaming(instruction: str) -> str:
    """Move artifact_data before chat so right-pane output can stream first."""
    instruction = instruction.replace(
        '1. "chat"\n2. "artifact_data"',
        '1. "artifact_data"\n2. "chat"',
        1,
    )
    match = re.search(
        r'(JSON 对象结构：\n\{\n)  "chat": ([^\n]+),\n  "artifact_data":',
        instruction,
    )
    if not match:
        return instruction
    chat_value = match.group(2)
    instruction = (
        instruction[: match.start()]
        + match.group(1)
        + '  "artifact_data":'
        + instruction[match.end() :]
    )
    return instruction.replace(
        '\n  },\n  "stage_action"',
        f'\n  }},\n  "chat": {chat_value},\n  "stage_action"',
        1,
    )


def build_structured_output_instruction(
    workflow_id: str,
    current_stage_id: str,
) -> str:
    artifact_data_instruction = None
    if (workflow_id, current_stage_id) == ("IDEA_BRAINSTORM", "DEFINE"):
        artifact_data_instruction = IDEA_DEFINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("IDEA_BRAINSTORM", "DIVERGE"):
        artifact_data_instruction = IDEA_DIVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("IDEA_BRAINSTORM", "CONVERGE"):
        artifact_data_instruction = IDEA_CONVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("IDEA_BRAINSTORM", "CONCEPT"):
        artifact_data_instruction = IDEA_CONCEPT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "CLARIFY"):
        artifact_data_instruction = ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "STRATEGY"):
        artifact_data_instruction = STRATEGY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "CASES"):
        artifact_data_instruction = CASES_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "DELIVERY"):
        artifact_data_instruction = DELIVERY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("REQ_REVIEW", "REVIEW"):
        artifact_data_instruction = REQ_REVIEW_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("REQ_REVIEW", "REPORT"):
        artifact_data_instruction = REQ_REVIEW_REPORT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "ELEVATOR"):
        artifact_data_instruction = VALUE_ELEVATOR_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "PERSONA"):
        artifact_data_instruction = VALUE_PERSONA_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "JOURNEY"):
        artifact_data_instruction = VALUE_JOURNEY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "BLUEPRINT"):
        artifact_data_instruction = VALUE_BLUEPRINT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("USER_STORY_BREAKDOWN", "SCOPE"):
        artifact_data_instruction = USER_STORY_SCOPE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("USER_STORY_BREAKDOWN", "STORY_MAP"):
        artifact_data_instruction = USER_STORY_MAP_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("USER_STORY_BREAKDOWN", "STORIES"):
        artifact_data_instruction = USER_STORIES_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("USER_STORY_BREAKDOWN", "HANDOFF"):
        artifact_data_instruction = USER_STORY_HANDOFF_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("INCIDENT_REVIEW", "TIMELINE"):
        artifact_data_instruction = INCIDENT_TIMELINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("INCIDENT_REVIEW", "ROOT_CAUSE"):
        artifact_data_instruction = INCIDENT_ROOT_CAUSE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    elif (workflow_id, current_stage_id) == ("INCIDENT_REVIEW", "IMPROVEMENT"):
        artifact_data_instruction = INCIDENT_IMPROVEMENT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    if artifact_data_instruction is not None:
        return prioritize_artifact_data_for_visible_streaming(artifact_data_instruction)
    return TEXT_STRUCTURED_OUTPUT_INSTRUCTION


def build_raw_json_retry_prompt(
    prompt: str,
    error: Exception,
    *,
    workflow_id: str | None = None,
    current_stage_id: str | None = None,
) -> str:
    if (
        workflow_id is not None
        and current_stage_id is not None
        and supports_artifact_data_rendering(workflow_id, current_stage_id)
    ):
        return (
            f"{prompt}\n\n"
            "【上一轮结构化输出未通过校验】\n"
            f"{error}\n\n"
            "请立刻重新输出一个完整合法的 JSON 对象，不要输出 JSON 之外的解释。"
            "必须修正上述 artifact_data 数据问题；所有必填字段必须存在，"
            "所有字符串必须非空，数组必须至少包含一项。不要输出 Markdown 文档、"
            "Mermaid 代码块或表格，后端会根据 artifact_data 渲染右侧产出物。"
        )
    return (
        f"{prompt}\n\n"
        "【上一轮结构化输出未通过校验】\n"
        f"{error}\n\n"
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
                f"结构化输出不符合业务契约，请重新生成完整合法输出：{exc}"
            ) from exc


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
    ) -> Iterator[AgentTurnDeltaOutput | AgentTurnOutput]:
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
    ) -> Iterator[AgentTurnDeltaOutput | AgentTurnOutput]:
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
            accumulated = ""
            latest_chat = ""
            latest_markdown = ""
            emitted_any_delta = False

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
                on_usage=lambda total_tokens: setattr(
                    self,
                    "last_token_usage",
                    total_tokens,
                ),
            ):
                accumulated += text_chunk
                delta = build_partial_agent_delta(
                    accumulated,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
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

            try:
                final_output = parse_agent_turn_output_text(
                    accumulated,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
            except json.JSONDecodeError:
                raise
            except ValidationError as exc:
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


def extract_json_object_prefix(text: str, key: str) -> dict[str, Any] | None:
    key_match = re.search(rf'"{re.escape(key)}"\s*:', text)
    if not key_match:
        return None
    index = key_match.end()
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] != "{":
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(text[index:])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def extract_completed_json_object_members(text: str, key: str) -> dict[str, Any]:
    key_match = re.search(rf'"{re.escape(key)}"\s*:', text)
    if not key_match:
        return {}
    index = key_match.end()
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] != "{":
        return {}

    index += 1
    members: dict[str, Any] = {}
    decoder = json.JSONDecoder()
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            return members
        if text[index] == "}":
            return members
        if text[index] == ",":
            index += 1
            continue
        if text[index] != '"':
            return members

        try:
            member_key, key_end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            return members
        if not isinstance(member_key, str):
            return members
        index += key_end

        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text) or text[index] != ":":
            return members
        index += 1

        while index < len(text) and text[index].isspace():
            index += 1
        try:
            value, value_end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            return members
        members[member_key] = value
        index += value_end

        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            return members
        if text[index] == ",":
            index += 1
            continue
        if text[index] == "}":
            return members
        return members

    return members


def build_partial_agent_delta(
    text: str,
    *,
    workflow_id: str | None = None,
    current_stage_id: str | None = None,
) -> AgentTurnDeltaOutput | None:
    chat = extract_json_string_prefix(text, "chat")
    markdown = extract_json_string_prefix(text, "markdown")
    artifact_patch = None
    if (
        not markdown
        and workflow_id is not None
        and current_stage_id is not None
        and supports_artifact_data_rendering(workflow_id, current_stage_id)
    ):
        artifact_data = extract_json_object_prefix(text, "artifact_data")
        if artifact_data is not None:
            try:
                rendered = render_agent_turn_from_artifact_data(
                    {
                        "chat": chat or "正在生成右侧产出物。",
                        "artifact_data": artifact_data,
                        "stage_action": None,
                        "warnings": [],
                    },
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
            except (ValueError, ValidationError):
                rendered = None
            if rendered is not None:
                markdown = rendered.artifact_update.markdown
                artifact_patch = rendered.artifact_patch
        else:
            partial_artifact_data = extract_completed_json_object_members(
                text,
                "artifact_data",
            )
            if partial_artifact_data:
                try:
                    rendered = render_partial_agent_turn_from_artifact_data(
                        {
                            "chat": chat or "正在生成右侧产出物。",
                            "artifact_data": partial_artifact_data,
                            "stage_action": None,
                            "warnings": [],
                        },
                        workflow_id=workflow_id,
                        current_stage_id=current_stage_id,
                    )
                except (ValueError, ValidationError):
                    rendered = None
                if rendered is not None:
                    markdown = rendered.artifact_update.markdown
                    artifact_patch = rendered.artifact_patch
    if not chat and not markdown:
        return None
    return AgentTurnDeltaOutput(
        chat=chat,
        artifact_update=(
            {"type": "replace", "markdown": markdown} if markdown else None
        ),
        artifact_patch=artifact_patch,
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
