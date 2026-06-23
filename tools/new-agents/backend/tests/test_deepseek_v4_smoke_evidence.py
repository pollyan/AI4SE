from __future__ import annotations

import json
from pathlib import Path

from deepseek_v4_smoke_evidence import (
    build_deepseek_v4_readiness_evidence,
    load_deepseek_v4_smoke_config,
    run_deepseek_v4_structured_smoke,
    write_deepseek_v4_evidence,
)


def test_config_reports_missing_smoke_environment(tmp_path: Path) -> None:
    config = load_deepseek_v4_smoke_config({}, evidence_dir=tmp_path)

    assert config.ready is False
    assert config.missing_env == (
        "NEW_AGENTS_SMOKE_API_KEY",
        "NEW_AGENTS_SMOKE_BASE_URL",
        "NEW_AGENTS_SMOKE_MODEL",
    )
    assert "NEW_AGENTS_SMOKE_API_KEY" in config.skip_reason
    assert config.evidence_dir == tmp_path


def test_config_rejects_non_deepseek_v4_model(tmp_path: Path) -> None:
    config = load_deepseek_v4_smoke_config(
        {
            "NEW_AGENTS_SMOKE_API_KEY": "test-key",
            "NEW_AGENTS_SMOKE_BASE_URL": "https://api.example.test",
            "NEW_AGENTS_SMOKE_MODEL": "gpt-4.1-mini",
        },
        evidence_dir=tmp_path,
    )

    assert config.ready is False
    assert config.model_mismatch == "gpt-4.1-mini"
    assert "deepseek-v4-" in config.skip_reason


def test_readiness_evidence_summarizes_deepseek_v4_artifact_data_path(
    tmp_path: Path,
) -> None:
    env = {
        "NEW_AGENTS_SMOKE_API_KEY": "test-key",
        "NEW_AGENTS_SMOKE_BASE_URL": "https://api.deepseek.com",
        "NEW_AGENTS_SMOKE_MODEL": "deepseek-v4-flash",
    }
    config = load_deepseek_v4_smoke_config(env, evidence_dir=tmp_path)

    evidence = build_deepseek_v4_readiness_evidence(config)

    assert evidence["status"] == "ready"
    assert evidence["model"] == "deepseek-v4-flash"
    assert evidence["capability"]["tier"] == "json_object_only"
    assert evidence["capability"]["response_format"] == {"type": "json_object"}
    assert evidence["model_settings"]["extra_body"] == {
        "thinking": {"type": "disabled"}
    }
    assert len(evidence["artifact_data_stages"]) == 17
    assert {"workflow_id": "TEST_DESIGN", "stage_id": "CLARIFY"} in evidence[
        "artifact_data_stages"
    ]
    assert {"workflow_id": "IDEA_BRAINSTORM", "stage_id": "CONCEPT"} in evidence[
        "artifact_data_stages"
    ]


def test_write_evidence_records_skip_reason(tmp_path: Path) -> None:
    config = load_deepseek_v4_smoke_config({}, evidence_dir=tmp_path)
    evidence = build_deepseek_v4_readiness_evidence(config)

    path = write_deepseek_v4_evidence(evidence, tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "skipped"
    assert "NEW_AGENTS_SMOKE_MODEL" in payload["skip_reason"]
    assert Path(payload["evidence_path"]) == path
    assert path.name.startswith("deepseek-v4-smoke-")


class FakeRuntime:
    last_token_usage = 321

    def stream_turn(self, prompt: str, *, workflow_id: str, current_stage_id: str):
        from agent_runtime import parse_agent_turn_output_text
        from test_artifact_data_renderers import VALID_CLARIFY_ARTIFACT_DATA

        assert "DeepSeek V4" in prompt
        yield parse_agent_turn_output_text(
            json.dumps(
                {
                    "chat": "我已整理需求澄清基线。",
                    "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
                    "stage_action": None,
                    "warnings": [],
                },
                ensure_ascii=False,
            ),
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )


def test_live_smoke_evidence_uses_runtime_and_records_artifact_summary(
    tmp_path: Path,
) -> None:
    env = {
        "NEW_AGENTS_SMOKE_API_KEY": "test-key",
        "NEW_AGENTS_SMOKE_BASE_URL": "https://api.deepseek.com",
        "NEW_AGENTS_SMOKE_MODEL": "deepseek-v4-flash",
    }
    config = load_deepseek_v4_smoke_config(env, evidence_dir=tmp_path)

    evidence = run_deepseek_v4_structured_smoke(
        config,
        runtime_factory=lambda *_args, **_kwargs: FakeRuntime(),
    )

    assert evidence["status"] == "passed"
    assert evidence["workflow_id"] == "TEST_DESIGN"
    assert evidence["stage_id"] == "CLARIFY"
    assert evidence["token_usage"] == 321
    assert evidence["artifact"]["has_markdown"] is True
    assert "# 需求分析文档" in evidence["artifact"]["headings"]
