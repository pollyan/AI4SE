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
from artifact_data_renderers import render_agent_turn_from_artifact_data
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

chat 字段必须像一次自然的工作对话，不要只用一两句模板化提示；建议保留 2 到 4 个短段落或短列表，让左侧对话有独立阅读价值。
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
chat 字段必须像一次自然的工作对话，不要只用一两句模板化提示；建议保留 2 到 4 个短段落或短列表，让左侧对话有独立阅读价值。
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
    "risks": [{"risk_id": "R-001", "name": "...", "failure_mode": "...", "impact": "...", "source": "...", "severity": 5, "occurrence": 3, "detection": 4, "rpn": 60, "mitigation": "...", "coverage": "...", "status": "待覆盖/已覆盖/风险接受"}],
    "test_techniques": [{"technique_id": "TS-001", "target": "QG-001 / R-001", "category": "...", "technique": "...", "reason": "...", "applies_to": "R-001 / TP-001"}],
    "test_layers": [{"layer": "单元测试/集成测试/E2E 测试", "ratio": "40%", "scope": "...", "related": "R-001 / TP-001", "tools": "...", "entry_condition": "..."}],
    "test_points": [{"point_id": "TP-001", "point": "...", "priority": "P0", "quality_goal": "QG-001", "risk": "R-001", "technique": "TS-001", "layer": "单元/集成/E2E", "estimated_cases": 6, "coverage": "...", "status": "待生成用例"}],
    "tradeoffs": [{"item": "...", "decision": "...", "impact": "...", "owner": "...", "status": "..."}],
    "stage_gate": [{"checked": true, "item": "..."}]
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "CASES"},
  "warnings": []
}

artifact_data 中所有字符串必须非空；数组必须至少包含一项；severity、occurrence、detection 必须是 1 到 5 的整数；rpn 必须等于 severity * occurrence * detection。不要输出完整 Markdown、Mermaid 代码块、risk-board JSON 代码块或表格，后端会负责确定性渲染右侧测试策略蓝图、quadrantChart、block-beta 和 ai4se-visual risk-board。
chat 字段必须像一次自然的工作对话，不要只用一两句模板化提示；建议保留 2 到 4 个短段落或短列表，让左侧对话有独立阅读价值。
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
chat 字段必须像一次自然的工作对话，不要只用一两句模板化提示；建议保留 2 到 4 个短段落或短列表，让左侧对话有独立阅读价值。
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

artifact_data 中所有字符串必须非空；数组必须至少包含一项；case_summary_items 中每项 case_count 必须等于 p0_count + p1_count + p2_count；delivery_metrics.total_cases 必须等于所有 case_summary_items.case_count 之和；coverage_map.case_ids 必须至少包含一个用例 ID。不要输出完整 Markdown、Mermaid 代码块、coverage-map JSON 代码块或表格，后端会负责确定性渲染右侧测试设计交付文档和 ai4se-visual coverage-map。
chat 字段必须像一次自然的工作对话，不要只用一两句模板化提示；建议保留 2 到 4 个短段落或短列表，让左侧对话有独立阅读价值。
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
chat 字段必须像一次自然的工作对话，不要只用一两句模板化提示；建议保留 2 到 4 个短段落或短列表，让左侧对话有独立阅读价值。
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
chat 字段必须像一次自然的工作对话，不要只用一两句模板化提示；建议保留 2 到 4 个短段落或短列表，让左侧对话有独立阅读价值。
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
chat 字段必须像一次自然的工作对话，不要只用一两句模板化提示；建议保留 2 到 4 个短段落或短列表，让左侧对话有独立阅读价值。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""


def supports_artifact_data_rendering(workflow_id: str, current_stage_id: str) -> bool:
    return (workflow_id, current_stage_id) in {
        ("TEST_DESIGN", "CLARIFY"),
        ("TEST_DESIGN", "STRATEGY"),
        ("TEST_DESIGN", "CASES"),
        ("TEST_DESIGN", "DELIVERY"),
        ("REQ_REVIEW", "REVIEW"),
        ("REQ_REVIEW", "REPORT"),
        ("VALUE_DISCOVERY", "ELEVATOR"),
    }


def build_structured_output_instruction(
    workflow_id: str,
    current_stage_id: str,
) -> str:
    if (workflow_id, current_stage_id) == ("TEST_DESIGN", "CLARIFY"):
        return ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    if (workflow_id, current_stage_id) == ("TEST_DESIGN", "STRATEGY"):
        return STRATEGY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    if (workflow_id, current_stage_id) == ("TEST_DESIGN", "CASES"):
        return CASES_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    if (workflow_id, current_stage_id) == ("TEST_DESIGN", "DELIVERY"):
        return DELIVERY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    if (workflow_id, current_stage_id) == ("REQ_REVIEW", "REVIEW"):
        return REQ_REVIEW_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    if (workflow_id, current_stage_id) == ("REQ_REVIEW", "REPORT"):
        return REQ_REVIEW_REPORT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
    if (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "ELEVATOR"):
        return VALUE_ELEVATOR_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
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
                delta = build_partial_agent_delta(accumulated)
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
                if emitted_any_delta and (latest_chat or latest_markdown):
                    yield AgentTurnOutput.model_validate(
                        {
                            "chat": latest_chat
                            or "本轮响应已中断，右侧产出物可能不完整。",
                            "artifact_update": (
                                {"type": "replace", "markdown": latest_markdown}
                                if latest_markdown
                                else {"type": "none"}
                            ),
                            "stage_action": None,
                            "warnings": ["artifact_truncated"],
                        }
                    )
                    return
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


def build_partial_agent_delta(text: str) -> AgentTurnDeltaOutput | None:
    chat = extract_json_string_prefix(text, "chat")
    markdown = extract_json_string_prefix(text, "markdown")
    if not chat and not markdown:
        return None
    return AgentTurnDeltaOutput(
        chat=chat,
        artifact_update=(
            {"type": "replace", "markdown": markdown} if markdown else None
        ),
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
