import json

import pytest

from sse_encoder import encode_sse_done, encode_sse_event
from sse_schemas import AgentTurnEvent, ErrorEvent


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


def test_encode_sse_done_keeps_done_sentinel():
    assert encode_sse_done() == "data: [DONE]\n\n"


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


def test_error_event_rejects_unknown_fields():
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        ErrorEvent.model_validate({
            "code": "LLM_ERROR",
            "message": "OpenAI API unreachable",
            "error": "legacy field",
        })


def test_agent_turn_event_rejects_unknown_top_level_fields():
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        AgentTurnEvent.model_validate({
            "output": {
                "chat": "已更新右侧文档。",
                "artifact_update": {"type": "none"},
                "stage_action": None,
                "warnings": [],
            },
            "legacy": True,
        })
