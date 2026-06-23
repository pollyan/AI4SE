from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from agent_contracts import AgentTurnOutput
from agent_runtime import (
    AgentRuntimeDependencyError,
    AgentRuntimeModelError,
    AgentRuntimeSchemaError,
    PydanticAgentRuntime,
    RawStreamingConfig,
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


class _NoopAgent:
    pass


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
    try:
        return _run_runtime_evidence(
            api_key="local-evidence-key",
            base_url=DEEPSEEK_V4_BASE_URL,
            model_name=DEEPSEEK_V4_MODEL,
            agent=agent,
            name="deepseek-v4-local-structured-output-evidence",
        )
    except (
        AgentRuntimeDependencyError,
        AgentRuntimeModelError,
        AgentRuntimeSchemaError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        return EvidenceResult(
            name="deepseek-v4-local-structured-output-evidence",
            status=EvidenceStatus.FAILED,
            reason=f"artifact_data validation failed: {type(exc).__name__}: {exc}",
        )


def run_optional_real_deepseek_v4_smoke(
    *,
    env: Mapping[str, str] | None = None,
    agent: Any | None = None,
) -> EvidenceResult:
    source = os.environ if env is None else env
    missing = tuple(name for name in REAL_SMOKE_REQUIRED_ENV if not source.get(name))
    if missing:
        return EvidenceResult(
            name="deepseek-v4-real-smoke",
            status=EvidenceStatus.SKIPPED,
            reason="missing smoke environment: " + ", ".join(missing),
        )

    model_name = source["NEW_AGENTS_DEEPSEEK_V4_SMOKE_MODEL"]
    if not model_name.startswith("deepseek-v4-"):
        return EvidenceResult(
            name="deepseek-v4-real-smoke",
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
            name="deepseek-v4-real-smoke",
        )
    except (
        AgentRuntimeDependencyError,
        AgentRuntimeModelError,
        AgentRuntimeSchemaError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        return EvidenceResult(
            name="deepseek-v4-real-smoke",
            status=EvidenceStatus.FAILED,
            reason=f"DeepSeek V4 real smoke failed: {type(exc).__name__}: {exc}",
        )


def _result_to_json(result: EvidenceResult) -> str:
    return json.dumps(
        {
            "name": result.name,
            "status": result.status.value,
            "reason": result.reason,
            "details": result.details,
        },
        ensure_ascii=False,
        indent=2,
    )


def main() -> int:
    result = run_optional_real_deepseek_v4_smoke()
    print(_result_to_json(result))
    return 1 if result.status == EvidenceStatus.FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
