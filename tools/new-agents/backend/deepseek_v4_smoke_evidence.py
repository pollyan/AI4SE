from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
from typing import Any, Callable

from agent_runtime import (
    ARTIFACT_DATA_RENDERING_STAGES,
    AgentRuntimeModelError,
    AgentRuntimeSchemaError,
    build_model_settings,
    build_pydantic_agent_runtime,
    resolve_structured_output_capability,
)

REQUIRED_ENV_VARS = (
    "NEW_AGENTS_SMOKE_API_KEY",
    "NEW_AGENTS_SMOKE_BASE_URL",
    "NEW_AGENTS_SMOKE_MODEL",
)
DEFAULT_EVIDENCE_DIR = Path("tmp/new-agents/deepseek-v4-smoke")
SMOKE_WORKFLOW_ID = "TEST_DESIGN"
SMOKE_STAGE_ID = "CLARIFY"
SMOKE_SYSTEM_PROMPT = """
你是 Lisa 测试专家。请严格遵守系统追加的 artifact_data JSON 输出要求。
本次只验证 TEST_DESIGN/CLARIFY 阶段，不要请求进入下一阶段。
chat 只返回给用户看的简短说明，禁止包含 Markdown 标题、表格、代码块或完整文档正文。
""".strip()
SMOKE_USER_PROMPT = """
请为一个登录功能生成需求澄清阶段的需求分析文档。
功能包括账号密码登录、短信验证码登录、第三方登录、失败重试、账号锁定和安全审计。
""".strip()


@dataclass(frozen=True)
class DeepSeekV4SmokeConfig:
    api_key: str | None
    base_url: str | None
    model: str | None
    missing_env: tuple[str, ...]
    evidence_dir: Path

    @property
    def model_mismatch(self) -> str | None:
        if self.model and not self.model.startswith("deepseek-v4-"):
            return self.model
        return None

    @property
    def ready(self) -> bool:
        return not self.missing_env and self.model_mismatch is None

    @property
    def skip_reason(self) -> str:
        if self.missing_env:
            return "missing DeepSeek V4 smoke environment: " + ", ".join(
                self.missing_env
            )
        if self.model_mismatch:
            return (
                "NEW_AGENTS_SMOKE_MODEL must start with deepseek-v4- for this "
                f"evidence gate, got {self.model_mismatch}"
            )
        return ""


def load_deepseek_v4_smoke_config(
    env: Mapping[str, str] | None = None,
    *,
    evidence_dir: Path | None = None,
) -> DeepSeekV4SmokeConfig:
    source = os.environ if env is None else env
    missing = tuple(name for name in REQUIRED_ENV_VARS if not source.get(name))
    configured_evidence_dir = (
        evidence_dir
        or Path(source.get("NEW_AGENTS_SMOKE_EVIDENCE_DIR", ""))
        if source.get("NEW_AGENTS_SMOKE_EVIDENCE_DIR")
        else evidence_dir
    )
    return DeepSeekV4SmokeConfig(
        api_key=source.get("NEW_AGENTS_SMOKE_API_KEY"),
        base_url=source.get("NEW_AGENTS_SMOKE_BASE_URL"),
        model=source.get("NEW_AGENTS_SMOKE_MODEL"),
        missing_env=missing,
        evidence_dir=configured_evidence_dir or DEFAULT_EVIDENCE_DIR,
    )


def _generated_at() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _artifact_data_stages() -> list[dict[str, str]]:
    return [
        {"workflow_id": workflow_id, "stage_id": stage_id}
        for workflow_id, stage_id in ARTIFACT_DATA_RENDERING_STAGES
    ]


def build_deepseek_v4_readiness_evidence(
    config: DeepSeekV4SmokeConfig,
) -> dict[str, Any]:
    model = config.model or ""
    capability = resolve_structured_output_capability(model)
    return {
        "schema_version": 1,
        "kind": "deepseek-v4-structured-artifact-smoke",
        "status": "ready" if config.ready else "skipped",
        "generated_at": _generated_at(),
        "model": config.model,
        "base_url": config.base_url,
        "missing_env": list(config.missing_env),
        "skip_reason": config.skip_reason,
        "capability": {
            "tier": capability.tier,
            "response_format": capability.response_format,
        },
        "model_settings": build_model_settings(model),
        "artifact_data_stages": _artifact_data_stages(),
    }


def _evidence_filename(status: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_status = re.sub(r"[^a-z0-9_-]+", "-", status.lower()).strip("-")
    return f"deepseek-v4-smoke-{timestamp}-{safe_status or 'evidence'}.json"


def write_deepseek_v4_evidence(
    evidence: Mapping[str, Any],
    evidence_dir: Path,
) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = evidence_dir / _evidence_filename(str(evidence.get("status", "evidence")))
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _artifact_summary(markdown: str | None) -> dict[str, Any]:
    headings = (
        re.findall(r"^#{1,6}\s+.+$", markdown, flags=re.MULTILINE)
        if markdown
        else []
    )
    return {
        "has_markdown": bool(markdown),
        "heading_count": len(headings),
        "headings": headings[:20],
        "contains_mermaid": "```mermaid" in markdown if markdown else False,
        "length": len(markdown or ""),
    }


def run_deepseek_v4_structured_smoke(
    config: DeepSeekV4SmokeConfig,
    *,
    runtime_factory: Callable[..., Any] = build_pydantic_agent_runtime,
) -> dict[str, Any]:
    evidence = build_deepseek_v4_readiness_evidence(config)
    if not config.ready:
        return evidence

    try:
        runtime = runtime_factory(
            api_key=config.api_key,
            base_url=config.base_url,
            model_name=config.model,
            system_prompt=SMOKE_SYSTEM_PROMPT,
        )
        outputs = list(
            runtime.stream_turn(
                SMOKE_USER_PROMPT,
                workflow_id=SMOKE_WORKFLOW_ID,
                current_stage_id=SMOKE_STAGE_ID,
            )
        )
        final_output = outputs[-1]
        markdown = (
            final_output.artifact_update.markdown
            if final_output.artifact_update is not None
            else None
        )
        evidence.update(
            {
                "status": "passed",
                "workflow_id": SMOKE_WORKFLOW_ID,
                "stage_id": SMOKE_STAGE_ID,
                "token_usage": getattr(runtime, "last_token_usage", None),
                "artifact": _artifact_summary(markdown),
                "warnings": list(final_output.warnings or []),
            }
        )
    except (AgentRuntimeModelError, AgentRuntimeSchemaError, TypeError, ValueError) as exc:
        evidence.update(
            {
                "status": "failed",
                "workflow_id": SMOKE_WORKFLOW_ID,
                "stage_id": SMOKE_STAGE_ID,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }
        )
    return evidence


def main() -> int:
    config = load_deepseek_v4_smoke_config()
    evidence = run_deepseek_v4_structured_smoke(config)
    path = write_deepseek_v4_evidence(evidence, config.evidence_dir)
    print(f"DeepSeek V4 smoke evidence: {path}")
    if evidence["status"] == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
