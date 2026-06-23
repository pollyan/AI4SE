from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from agent_contracts import AgentTurnOutput
from agent_runtime import (
    ARTIFACT_DATA_RENDERING_STAGES,
    AgentRuntimeDependencyError,
    AgentRuntimeModelError,
    AgentRuntimeSchemaError,
    build_model_settings,
    build_pydantic_agent_runtime,
    resolve_structured_output_capability,
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVIDENCE_DIR = ROOT / "tmp/new-agents/deepseek-v4-smoke"
REQUIRED_ENV = (
    "NEW_AGENTS_SMOKE_API_KEY",
    "NEW_AGENTS_SMOKE_BASE_URL",
    "NEW_AGENTS_SMOKE_MODEL",
)
SMOKE_WORKFLOW_ID = "TEST_DESIGN"
SMOKE_STAGE_ID = "CLARIFY"


@dataclass(frozen=True)
class DeepSeekV4SmokeConfig:
    api_key: str | None
    base_url: str | None
    model: str | None
    evidence_dir: Path
    missing_env: tuple[str, ...]
    model_mismatch: str | None

    @property
    def ready(self) -> bool:
        return not self.missing_env and self.model_mismatch is None

    @property
    def skip_reason(self) -> str:
        if self.missing_env:
            return "missing smoke environment: " + ", ".join(self.missing_env)
        if self.model_mismatch:
            return (
                "NEW_AGENTS_SMOKE_MODEL must start with deepseek-v4-, "
                f"got {self.model_mismatch}"
            )
        return ""


def load_deepseek_v4_smoke_config(
    env: Mapping[str, str] | None = None,
    *,
    evidence_dir: Path | None = None,
) -> DeepSeekV4SmokeConfig:
    source = os.environ if env is None else env
    configured_evidence_dir = source.get("NEW_AGENTS_SMOKE_EVIDENCE_DIR")
    if evidence_dir is not None:
        output_dir = evidence_dir
    elif configured_evidence_dir:
        output_dir = Path(configured_evidence_dir)
    else:
        output_dir = DEFAULT_EVIDENCE_DIR
    missing = tuple(name for name in REQUIRED_ENV if not source.get(name))
    model = source.get("NEW_AGENTS_SMOKE_MODEL")
    model_mismatch = (
        model
        if model is not None and not missing and not model.startswith("deepseek-v4-")
        else None
    )
    return DeepSeekV4SmokeConfig(
        api_key=source.get("NEW_AGENTS_SMOKE_API_KEY"),
        base_url=source.get("NEW_AGENTS_SMOKE_BASE_URL"),
        model=model,
        evidence_dir=output_dir,
        missing_env=missing,
        model_mismatch=model_mismatch,
    )


def build_deepseek_v4_readiness_evidence(
    config: DeepSeekV4SmokeConfig,
) -> dict[str, Any]:
    model = config.model or "deepseek-v4-flash"
    capability = resolve_structured_output_capability(model)
    status = "ready" if config.ready else "skipped"
    return {
        "kind": "deepseek-v4-smoke-readiness",
        "status": status,
        "skip_reason": config.skip_reason,
        "model": config.model,
        "base_url": config.base_url,
        "capability": {
            "tier": capability.tier,
            "response_format": capability.response_format,
        },
        "model_settings": build_model_settings(model),
        "artifact_data_stages": [
            {"workflow_id": workflow_id, "stage_id": stage_id}
            for workflow_id, stage_id in ARTIFACT_DATA_RENDERING_STAGES
        ],
    }


def write_deepseek_v4_evidence(
    evidence: dict[str, Any],
    evidence_dir: Path,
) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = evidence_dir / f"deepseek-v4-smoke-{timestamp}.json"
    payload = {
        **evidence,
        "created_at": datetime.now(UTC).isoformat(),
        "evidence_path": str(path),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def run_deepseek_v4_structured_smoke(
    config: DeepSeekV4SmokeConfig,
    *,
    runtime_factory: Callable[..., Any] = build_pydantic_agent_runtime,
) -> dict[str, Any]:
    if not config.ready:
        return build_deepseek_v4_readiness_evidence(config)

    runtime = runtime_factory(
        api_key=config.api_key,
        base_url=config.base_url,
        model_name=config.model,
        system_prompt=(
            "你是 Lisa 测试专家。请在 DeepSeek V4 JSON mode 下输出结构化 "
            "artifact_data，由后端负责渲染 Markdown。"
        ),
    )
    final_output: AgentTurnOutput | None = None
    for event in runtime.stream_turn(
        "DeepSeek V4 smoke: 请为登录功能生成需求澄清基线。",
        workflow_id=SMOKE_WORKFLOW_ID,
        current_stage_id=SMOKE_STAGE_ID,
    ):
        if isinstance(event, AgentTurnOutput):
            final_output = event

    if final_output is None:
        raise AgentRuntimeSchemaError("DeepSeek V4 smoke produced no final output")

    markdown = (
        final_output.artifact_update.markdown
        if final_output.artifact_update and final_output.artifact_update.markdown
        else ""
    )
    headings = [
        line.strip()
        for line in markdown.splitlines()
        if line.strip().startswith("#")
    ]
    return {
        "kind": "deepseek-v4-smoke-live",
        "status": "passed",
        "workflow_id": SMOKE_WORKFLOW_ID,
        "stage_id": SMOKE_STAGE_ID,
        "model": config.model,
        "base_url": config.base_url,
        "token_usage": getattr(runtime, "last_token_usage", None),
        "artifact": {
            "has_markdown": bool(markdown),
            "headings": headings[:12],
            "warnings": list(final_output.warnings),
        },
    }


def main() -> int:
    config = load_deepseek_v4_smoke_config()
    try:
        evidence = (
            run_deepseek_v4_structured_smoke(config)
            if config.ready
            else build_deepseek_v4_readiness_evidence(config)
        )
        exit_code = 0
    except (
        AgentRuntimeDependencyError,
        AgentRuntimeModelError,
        AgentRuntimeSchemaError,
        ValueError,
    ) as exc:
        evidence = {
            "kind": "deepseek-v4-smoke-live",
            "status": "failed",
            "model": config.model,
            "base_url": config.base_url,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        exit_code = 1
    path = write_deepseek_v4_evidence(evidence, config.evidence_dir)
    print(path)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
