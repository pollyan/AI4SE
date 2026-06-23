import json

from deepseek_v4_smoke_evidence import (
    DEEPSEEK_V4_EXPECTED_ARTIFACT_DATA_STAGES,
    EvidenceStatus,
    collect_deepseek_v4_evidence,
    run_deepseek_v4_provider_evidence,
    run_deepseek_v4_stage_coverage_evidence,
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


def test_provider_evidence_uses_json_object_and_disabled_thinking():
    result = run_deepseek_v4_provider_evidence()

    assert result.status == EvidenceStatus.PASSED
    assert result.details["capability_tier"] == "json_object_only"
    assert result.details["response_format"] == {"type": "json_object"}
    assert result.details["model_settings"] == {
        "extra_body": {"thinking": {"type": "disabled"}}
    }
    assert result.details["agent_retries"] == 3


def test_stage_coverage_evidence_covers_all_deepseek_artifact_data_stages():
    result = run_deepseek_v4_stage_coverage_evidence()

    assert result.status == EvidenceStatus.PASSED
    assert result.details["covered_count"] == 17
    assert set(result.details["covered_stages"]) == {
        f"{workflow_id}/{stage_id}"
        for workflow_id, stage_id in DEEPSEEK_V4_EXPECTED_ARTIFACT_DATA_STAGES
    }


def test_local_evidence_uses_json_object_and_renders_artifact(monkeypatch):
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


def test_local_evidence_reports_contract_failure(monkeypatch):
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


def test_optional_real_smoke_rejects_non_deepseek_v4_model():
    result = run_optional_real_deepseek_v4_smoke(
        env={
            "NEW_AGENTS_DEEPSEEK_V4_SMOKE_API_KEY": "test-key",
            "NEW_AGENTS_DEEPSEEK_V4_SMOKE_BASE_URL": "https://api.deepseek.com",
            "NEW_AGENTS_DEEPSEEK_V4_SMOKE_MODEL": "deepseek-chat",
        },
        agent=FakeAgent({}),
    )

    assert result.status == EvidenceStatus.FAILED
    assert "must start with deepseek-v4-" in result.reason


def test_collect_evidence_includes_provider_coverage_local_and_real_smoke(monkeypatch):
    def fake_stream_chat_completion_content(**_kwargs):
        yield _valid_req_review_report_json()

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )

    results = collect_deepseek_v4_evidence(env={}, agent=FakeAgent({}))
    by_name = {result.name: result for result in results}

    assert by_name["deepseek-v4-provider-capability"].status == EvidenceStatus.PASSED
    assert (
        by_name["deepseek-v4-artifact-data-stage-coverage"].status
        == EvidenceStatus.PASSED
    )
    assert by_name["deepseek-v4-local-deterministic-smoke"].status == EvidenceStatus.PASSED
    assert by_name["deepseek-v4-optional-real-smoke"].status == EvidenceStatus.SKIPPED
