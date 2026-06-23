import json

from agent_contracts import AgentTurnOutput
from deepseek_v4_smoke_evidence import (
    EvidenceStatus,
    run_local_deepseek_v4_evidence,
    run_optional_real_deepseek_v4_smoke,
)
from test_agent_runtime import FakeAgent
from test_artifact_data_renderers import VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA


def _valid_req_review_report_json() -> str:
    return json.dumps(
        {
            "chat": "我已整理正式需求评审报告，请确认右侧内容。",
            "artifact_data": VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )


def test_local_deepseek_v4_evidence_uses_json_object_and_renders_artifact(monkeypatch):
    calls = []

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield _valid_req_review_report_json()

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )

    result = run_local_deepseek_v4_evidence(agent=FakeAgent({}))

    assert result.status == EvidenceStatus.PASSED
    assert result.details["workflow_id"] == "REQ_REVIEW"
    assert result.details["stage_id"] == "REPORT"
    assert result.details["artifact_title"] == "# 需求评审报告"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in calls[0]["messages"][0]["content"]


def test_local_deepseek_v4_evidence_reports_contract_failure(monkeypatch):
    def fake_stream_chat_completion_content(**_kwargs):
        yield json.dumps(
            {
                "chat": "缺少右侧产物数据。",
                "artifact_data": {"document_info": {}},
                "stage_action": None,
                "warnings": [],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )

    result = run_local_deepseek_v4_evidence(agent=FakeAgent({}))

    assert result.status == EvidenceStatus.FAILED
    assert result.reason
    assert "artifact_data" in result.reason or "validation" in result.reason.lower()


def test_optional_real_smoke_skips_without_credentials():
    result = run_optional_real_deepseek_v4_smoke(env={})

    assert result.status == EvidenceStatus.SKIPPED
    assert "NEW_AGENTS_DEEPSEEK_V4_SMOKE_API_KEY" in result.reason


def test_optional_real_smoke_never_reports_passed_without_runtime_output(monkeypatch):
    def fake_stream_chat_completion_content(**_kwargs):
        return
        yield

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )

    result = run_optional_real_deepseek_v4_smoke(
        env={
            "NEW_AGENTS_DEEPSEEK_V4_SMOKE_API_KEY": "test-key",
            "NEW_AGENTS_DEEPSEEK_V4_SMOKE_BASE_URL": "https://api.deepseek.com",
            "NEW_AGENTS_DEEPSEEK_V4_SMOKE_MODEL": "deepseek-v4-flash",
        },
        agent=FakeAgent({}),
    )

    assert result.status == EvidenceStatus.FAILED
    assert result.reason
    assert not isinstance(result.details.get("output"), AgentTurnOutput)
