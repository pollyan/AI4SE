import json
from pathlib import Path

import pytest

from sse_encoder import encode_sse_done, encode_sse_event
from sse_schemas import (
    AgentRetryEvent,
    AgentTurnDeltaEvent,
    AgentTurnEvent,
    ErrorEvent,
    RunStartedEvent,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "contract-fixtures"
    / "agent-runtime-events.json"
)
SSE_EVENT_MODELS = {
    "run_started": RunStartedEvent,
    "agent_retry": AgentRetryEvent,
    "agent_delta": AgentTurnDeltaEvent,
    "agent_turn": AgentTurnEvent,
    "error": ErrorEvent,
}


def test_encode_error_event_uses_typed_message_contract():
    encoded = encode_sse_event(
        ErrorEvent(code="LLM_ERROR", message="OpenAI API unreachable")
    )

    payload = json.loads(encoded.removeprefix("data: ").strip())
    assert payload == {
        "type": "error",
        "code": "LLM_ERROR",
        "message": "OpenAI API unreachable",
    }
    assert "response" not in payload
    assert "error" not in payload


def test_encode_error_event_includes_optional_diagnostic_contract():
    encoded = encode_sse_event(
        ErrorEvent.model_validate(
            {
                "code": "SCHEMA_VALIDATION_FAILED",
                "message": "artifact_data.requirement_facts.0.fact must be non-empty",
                "diagnostic": {
                    "phase": "structured_output",
                    "workflowId": "TEST_DESIGN",
                    "stageId": "CLARIFY",
                    "fieldPath": "artifact_data.requirement_facts.0.fact",
                    "validator": "string_too_short",
                    "retryable": True,
                    "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。",
                },
            }
        )
    )

    payload = json.loads(encoded.removeprefix("data: ").strip())

    assert payload["diagnostic"] == {
        "phase": "structured_output",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
        "fieldPath": "artifact_data.requirement_facts.0.fact",
        "validator": "string_too_short",
        "retryable": True,
        "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。",
    }


def test_encode_sse_done_keeps_done_sentinel():
    assert encode_sse_done() == "data: [DONE]\n\n"


def test_encode_run_started_event_uses_run_id_alias():
    encoded = encode_sse_event(RunStartedEvent(run_id="run-123"))

    payload = json.loads(encoded.removeprefix("data: ").strip())
    assert payload == {
        "type": "run_started",
        "runId": "run-123",
    }


def test_encode_agent_retry_event_uses_attempt_index_alias():
    encoded = encode_sse_event(AgentRetryEvent(attempt_index=2))

    payload = json.loads(encoded.removeprefix("data: ").strip())
    assert payload == {"type": "agent_retry", "attemptIndex": 2}


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"code": "   ", "message": "failed"}, "error code cannot be blank"),
        ({"code": "LLM_ERROR", "message": "   "}, "error message cannot be blank"),
    ],
)
def test_error_event_rejects_blank_code_or_message(payload, message):
    with pytest.raises(ValueError, match=message):
        ErrorEvent.model_validate(payload)


def test_error_event_rejects_invalid_diagnostic_contract():
    with pytest.raises(ValueError, match="diagnostic phase cannot be blank"):
        ErrorEvent.model_validate(
            {
                "code": "SCHEMA_VALIDATION_FAILED",
                "message": "failed",
                "diagnostic": {
                    "phase": " ",
                    "workflowId": "TEST_DESIGN",
                    "stageId": "CLARIFY",
                    "fieldPath": "artifact_data",
                    "validator": "structured_output",
                    "retryable": True,
                    "publicReason": "结构化输出未通过校验。",
                },
            }
        )


def test_error_event_rejects_unknown_fields():
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        ErrorEvent.model_validate(
            {
                "code": "LLM_ERROR",
                "message": "OpenAI API unreachable",
                "error": "legacy field",
            }
        )


def test_agent_turn_event_rejects_unknown_top_level_fields():
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        AgentTurnEvent.model_validate(
            {
                "output": {
                    "chat": "已更新右侧文档。",
                    "artifact_update": {"type": "none"},
                    "stage_action": None,
                    "warnings": [],
                },
                "legacy": True,
            }
        )


def test_agent_turn_event_serializes_artifact_patch_with_camel_case_fields():
    event = AgentTurnEvent.model_validate(
        {
            "output": {
                "chat": "已追加系统边界。",
                "artifact_update": {
                    "type": "replace",
                    "markdown": "# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n新风险",
                },
                "artifact_patch": {
                    "operation": "add_after",
                    "sectionAnchor": "h2:风险:1",
                    "afterSectionAnchor": "h2:范围:1",
                    "replacementMarkdown": "## 风险\n\n新风险",
                    "baseContent": "# 文档\n\n## 范围\n\n旧范围",
                },
                "stage_action": None,
                "warnings": [],
            },
        }
    )

    payload = json.loads(encode_sse_event(event).removeprefix("data: ").strip())

    assert payload["output"]["artifact_patch"] == {
        "operation": "add_after",
        "sectionAnchor": "h2:风险:1",
        "afterSectionAnchor": "h2:范围:1",
        "replacementMarkdown": "## 风险\n\n新风险",
        "baseContent": "# 文档\n\n## 范围\n\n旧范围",
    }


def test_agent_delta_event_rejects_patch_without_replace_artifact_update():
    with pytest.raises(ValueError, match="artifact_patch requires replace"):
        AgentTurnDeltaEvent.model_validate(
            {
                "output": {
                    "chat": "正在追加章节。",
                    "artifact_patch": {
                        "operation": "add_after",
                        "sectionAnchor": "h2:风险:1",
                        "afterSectionAnchor": "h2:范围:1",
                        "replacementMarkdown": "## 风险\n\n新风险",
                    },
                },
            }
        )


def test_agent_runtime_event_fixture_matches_backend_sse_schema():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    for payload in fixture["events"]:
        model = SSE_EVENT_MODELS[payload["type"]]
        event = model.model_validate(payload)
        encoded = encode_sse_event(event)
        encoded_payload = json.loads(encoded.removeprefix("data: ").strip())

        assert encoded_payload == payload
