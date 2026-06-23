from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

import agent_runtime as agent_runtime_module
from openai import OpenAIError

from agent_contracts import AgentTurnOutput
from agent_runtime import (
    AgentRuntimeDependencyError,
    AgentRuntimeModelError,
    AgentRuntimeSchemaError,
    PydanticAgentRuntime,
    RawStreamingConfig,
    build_agent_retries,
    build_model_settings,
    build_structured_output_instruction,
    resolve_structured_output_capability,
    supports_artifact_data_rendering,
)


class EvidenceStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class EvidenceResult:
    name: str
    status: EvidenceStatus
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


DEEPSEEK_V4_MODEL = "deepseek-v4-flash"
DEEPSEEK_V4_BASE_URL = "https://api.deepseek.com"
SMOKE_WORKFLOW_ID = "REQ_REVIEW"
SMOKE_STAGE_ID = "REPORT"
REAL_SMOKE_REQUIRED_ENV = (
    "NEW_AGENTS_DEEPSEEK_V4_SMOKE_API_KEY",
    "NEW_AGENTS_DEEPSEEK_V4_SMOKE_BASE_URL",
    "NEW_AGENTS_DEEPSEEK_V4_SMOKE_MODEL",
)
DEEPSEEK_V4_EXPECTED_ARTIFACT_DATA_STAGES = (
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
    ("INCIDENT_REVIEW", "TIMELINE"),
    ("INCIDENT_REVIEW", "ROOT_CAUSE"),
    ("INCIDENT_REVIEW", "IMPROVEMENT"),
)


class _NoopAgent:
    pass


REQ_REVIEW_REPORT_SMOKE_ARTIFACT_DATA = {
    "conclusion": {
        "artifact_name": "可签署需求评审报告",
        "review_result": "不通过",
        "reason": "存在 1 个 P0 阻塞性问题，必须修订需求后重新评审。",
        "development_gate": "暂缓",
        "needs_recheck": "是",
        "summary": "会员权益需求当前缺少核心展示验收标准，暂不建议进入开发和测试设计。",
    },
    "review_info": {
        "requirement_name": "会员权益需求",
        "review_date": "2026-06-23",
        "review_input": "REQ_REVIEW/REVIEW 问题清单 v1.0",
        "participants": "产品 / 研发 / 测试",
    },
    "issue_statistics": {
        "p0_count": 1,
        "p1_count": 1,
        "p2_count": 1,
    },
    "issue_closures": [
        {
            "issue_id": "Q-001",
            "priority": "P0",
            "description": "权益状态缺少可验收的展示断言。",
            "requirement_section": "权益中心展示",
            "impact": "影响权益展示主链路测试设计",
            "owner": "PM",
            "next_step": "补充每种权益状态的展示字段、排序和空态验收标准。",
            "closure_status": "待修订",
            "recheck_condition": "修订 PRD 后覆盖已领取、已过期、不可用状态断言。",
        },
        {
            "issue_id": "Q-002",
            "priority": "P1",
            "description": "领取次数和过期时间缺少边界规则。",
            "requirement_section": "权益领取规则",
            "impact": "影响边界值和异常路径覆盖",
            "owner": "PM / 研发",
            "next_step": "明确领取次数、过期时间和重复领取提示。",
            "closure_status": "待修订",
            "recheck_condition": "补充每日、每周期和总次数限制。",
        },
        {
            "issue_id": "Q-003",
            "priority": "P2",
            "description": "建议补充权益运营配置示例。",
            "requirement_section": "配置说明",
            "impact": "提升测试数据准备效率",
            "owner": "PM",
            "next_step": "补充典型权益配置样例。",
            "closure_status": "待排期",
            "recheck_condition": "后续迭代补充即可。",
        },
    ],
    "review_conditions": [
        {
            "condition_id": "RC-001",
            "condition": "P0 问题 Q-001 关闭后重新评审。",
            "related_issues": ["Q-001"],
            "verification": "检查修订 PRD 中权益状态展示验收标准。",
            "owner": "产品 / 测试",
            "status": "待满足",
        },
        {
            "condition_id": "RC-002",
            "condition": "P1 问题 Q-002 给出明确边界规则。",
            "related_issues": ["Q-002"],
            "verification": "检查领取次数和过期计算口径。",
            "owner": "产品 / 研发",
            "status": "待满足",
        },
    ],
    "signoffs": [
        {
            "role": "产品负责人",
            "owner": "PM",
            "opinion": "不通过",
            "status": "待签署",
        },
        {
            "role": "测试负责人",
            "owner": "测试",
            "opinion": "不通过",
            "status": "待签署",
        },
    ],
    "change_log": [
        {
            "version": "v1.0",
            "date": "2026-06-23",
            "change": "首次生成需求评审报告",
            "reason": "完成 REVIEW 阶段问题清单汇总",
            "owner": "Lisa",
        }
    ],
}


def _deterministic_smoke_stream(**_kwargs: Any):
    yield json.dumps(
        {
            "chat": "我已整理正式需求评审报告，请确认右侧内容。",
            "artifact_data": REQ_REVIEW_REPORT_SMOKE_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )


def _uses_default_network_stream() -> bool:
    return (
        getattr(
            agent_runtime_module.stream_chat_completion_content,
            "__module__",
            "",
        )
        == "llm_client"
    )


def run_deepseek_v4_provider_evidence(
    model_name: str = DEEPSEEK_V4_MODEL,
) -> EvidenceResult:
    capability = resolve_structured_output_capability(model_name)
    model_settings = build_model_settings(model_name)
    agent_retries = build_agent_retries(model_name)
    details = {
        "model": model_name,
        "capability_tier": capability.tier,
        "response_format": capability.response_format,
        "model_settings": model_settings,
        "agent_retries": agent_retries,
    }
    expected_settings = {"extra_body": {"thinking": {"type": "disabled"}}}
    if (
        capability.tier == "json_object_only"
        and capability.response_format == {"type": "json_object"}
        and model_settings == expected_settings
        and agent_retries == 3
    ):
        return EvidenceResult(
            name="deepseek-v4-provider-capability",
            status=EvidenceStatus.PASSED,
            details=details,
        )
    return EvidenceResult(
        name="deepseek-v4-provider-capability",
        status=EvidenceStatus.FAILED,
        reason="DeepSeek V4 provider capability is not json_object_only with thinking disabled",
        details=details,
    )


def run_deepseek_v4_stage_coverage_evidence() -> EvidenceResult:
    covered = []
    missing = []
    for workflow_id, stage_id in DEEPSEEK_V4_EXPECTED_ARTIFACT_DATA_STAGES:
        stage_key = f"{workflow_id}/{stage_id}"
        if not supports_artifact_data_rendering(workflow_id, stage_id):
            missing.append(stage_key)
            continue
        instruction = build_structured_output_instruction(workflow_id, stage_id)
        if "artifact_data" not in instruction:
            missing.append(f"{stage_key}: missing artifact_data instruction")
            continue
        covered.append(stage_key)

    details = {
        "expected_count": len(DEEPSEEK_V4_EXPECTED_ARTIFACT_DATA_STAGES),
        "covered_count": len(covered),
        "covered_stages": covered,
        "missing_stages": missing,
    }
    if missing:
        return EvidenceResult(
            name="deepseek-v4-artifact-data-stage-coverage",
            status=EvidenceStatus.FAILED,
            reason="DeepSeek V4 artifact_data stage coverage is incomplete",
            details=details,
        )
    return EvidenceResult(
        name="deepseek-v4-artifact-data-stage-coverage",
        status=EvidenceStatus.PASSED,
        details=details,
    )


def _build_runtime(
    *,
    api_key: str,
    base_url: str,
    model_name: str,
    agent: Any,
) -> PydanticAgentRuntime:
    return PydanticAgentRuntime(
        agent,
        raw_streaming_config=RawStreamingConfig(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            system_prompt=(
                "你是 Lisa 需求评审专家。请在 DeepSeek V4 JSON mode 下输出 "
                "artifact_data，由后端负责确定性渲染 Markdown、Mermaid 和 "
                "ai4se-visual。"
            ),
        ),
    )


def _run_runtime_evidence(
    *,
    api_key: str,
    base_url: str,
    model_name: str,
    agent: Any,
    name: str,
) -> EvidenceResult:
    runtime = _build_runtime(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        agent=agent,
    )
    final_output: AgentTurnOutput | None = None
    for event in runtime.stream_turn(
        "DeepSeek V4 evidence: 请生成需求评审报告。",
        workflow_id=SMOKE_WORKFLOW_ID,
        current_stage_id=SMOKE_STAGE_ID,
    ):
        if isinstance(event, AgentTurnOutput):
            final_output = event

    if final_output is None:
        return EvidenceResult(
            name=name,
            status=EvidenceStatus.FAILED,
            reason="DeepSeek V4 evidence produced no output",
        )

    markdown = (
        final_output.artifact_update.markdown
        if final_output.artifact_update and final_output.artifact_update.markdown
        else ""
    )
    artifact_title = markdown.splitlines()[0].strip() if markdown else ""
    if not markdown or artifact_title != "# 需求评审报告":
        return EvidenceResult(
            name=name,
            status=EvidenceStatus.FAILED,
            reason="DeepSeek V4 evidence did not render the expected artifact",
            details={"artifact_title": artifact_title},
        )

    return EvidenceResult(
        name=name,
        status=EvidenceStatus.PASSED,
        details={
            "workflow_id": SMOKE_WORKFLOW_ID,
            "stage_id": SMOKE_STAGE_ID,
            "model": model_name,
            "base_url": base_url,
            "artifact_title": artifact_title,
            "warnings": list(final_output.warnings),
            "token_usage": getattr(runtime, "last_token_usage", None),
        },
    )


def run_local_deepseek_v4_evidence(*, agent: Any) -> EvidenceResult:
    original_stream = agent_runtime_module.stream_chat_completion_content
    patch_default_stream = _uses_default_network_stream()
    if patch_default_stream:
        agent_runtime_module.stream_chat_completion_content = _deterministic_smoke_stream
    try:
        return _run_runtime_evidence(
            api_key="local-evidence-key",
            base_url=DEEPSEEK_V4_BASE_URL,
            model_name=DEEPSEEK_V4_MODEL,
            agent=agent,
            name="deepseek-v4-local-deterministic-smoke",
        )
    except (
        AgentRuntimeDependencyError,
        AgentRuntimeModelError,
        AgentRuntimeSchemaError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        OpenAIError,
    ) as exc:
        return EvidenceResult(
            name="deepseek-v4-local-deterministic-smoke",
            status=EvidenceStatus.FAILED,
            reason=f"artifact_data validation failed: {type(exc).__name__}: {exc}",
        )
    finally:
        if patch_default_stream:
            agent_runtime_module.stream_chat_completion_content = original_stream


def run_optional_real_deepseek_v4_smoke(
    *,
    env: Mapping[str, str] | None = None,
    agent: Any | None = None,
) -> EvidenceResult:
    source = os.environ if env is None else env
    missing = tuple(name for name in REAL_SMOKE_REQUIRED_ENV if not source.get(name))
    if missing:
        return EvidenceResult(
            name="deepseek-v4-optional-real-smoke",
            status=EvidenceStatus.SKIPPED,
            reason="missing smoke environment: " + ", ".join(missing),
        )

    model_name = source["NEW_AGENTS_DEEPSEEK_V4_SMOKE_MODEL"]
    if not model_name.startswith("deepseek-v4-"):
        return EvidenceResult(
            name="deepseek-v4-optional-real-smoke",
            status=EvidenceStatus.FAILED,
            reason=(
                "NEW_AGENTS_DEEPSEEK_V4_SMOKE_MODEL must start with "
                f"deepseek-v4-, got {model_name}"
            ),
        )

    try:
        return _run_runtime_evidence(
            api_key=source["NEW_AGENTS_DEEPSEEK_V4_SMOKE_API_KEY"],
            base_url=source["NEW_AGENTS_DEEPSEEK_V4_SMOKE_BASE_URL"],
            model_name=model_name,
            agent=agent or _NoopAgent(),
            name="deepseek-v4-optional-real-smoke",
        )
    except (
        AgentRuntimeDependencyError,
        AgentRuntimeModelError,
        AgentRuntimeSchemaError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        OpenAIError,
    ) as exc:
        return EvidenceResult(
            name="deepseek-v4-optional-real-smoke",
            status=EvidenceStatus.FAILED,
            reason=f"DeepSeek V4 real smoke failed: {type(exc).__name__}: {exc}",
        )


def collect_deepseek_v4_evidence(
    *,
    env: Mapping[str, str] | None = None,
    agent: Any | None = None,
) -> list[EvidenceResult]:
    local_agent = agent or _NoopAgent()
    return [
        run_deepseek_v4_provider_evidence(),
        run_deepseek_v4_stage_coverage_evidence(),
        run_local_deepseek_v4_evidence(agent=local_agent),
        run_optional_real_deepseek_v4_smoke(env=env, agent=agent),
    ]


def _result_to_dict(result: EvidenceResult) -> dict[str, Any]:
    return {
        "name": result.name,
        "status": result.status.value,
        "reason": result.reason,
        "details": result.details,
    }


def results_to_json(results: list[EvidenceResult]) -> str:
    return json.dumps(
        [_result_to_dict(result) for result in results],
        ensure_ascii=False,
        indent=2,
    )


def main() -> int:
    results = collect_deepseek_v4_evidence()
    print(results_to_json(results))
    return 1 if any(result.status == EvidenceStatus.FAILED for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
