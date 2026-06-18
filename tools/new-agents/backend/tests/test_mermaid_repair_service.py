from unittest.mock import patch

import pytest

from llm_client import LlmClientError
from mermaid_repair_service import (
    MermaidRepairError,
    clean_mermaid_repair_output,
    repair_mermaid_code,
)
from request_schemas import MermaidRepairRequest


def test_clean_mermaid_repair_output_strips_markdown_fences() -> None:
    assert clean_mermaid_repair_output(
        "```mermaid\ngraph TD\n  A-->B\n```"
    ) == "graph TD\n  A-->B"


def test_clean_mermaid_repair_output_rejects_empty_output() -> None:
    with pytest.raises(MermaidRepairError) as exc_info:
        clean_mermaid_repair_output("```mermaid\n```")

    assert str(exc_info.value) == "Mermaid repair returned empty code"


@patch("mermaid_repair_service.stream_chat_completion_content")
def test_repair_mermaid_code_builds_prompt_and_returns_cleaned_code(
    mock_stream,
) -> None:
    mock_stream.return_value = [
        "```mermaid\n",
        "graph TD\n  A-->B\n",
        "```",
    ]
    request = MermaidRepairRequest.model_validate({
        "brokenCode": "graph TD\n  A-->",
        "errorMessage": "Syntax Error",
        "blockIndex": 0,
    })

    repaired = repair_mermaid_code(
        request,
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
    )

    assert repaired == "graph TD\n  A-->B"
    call = mock_stream.call_args.kwargs
    assert call["api_key"] == "test-api-key"
    assert call["base_url"] == "https://api.test.com/v1"
    assert call["model"] == "test-model"
    assert call["temperature"] == 0.2
    assert call["messages"][0]["role"] == "system"
    assert "Mermaid" in call["messages"][0]["content"]
    assert "Syntax Error" in call["messages"][1]["content"]
    assert "graph TD\n  A-->" in call["messages"][1]["content"]


@patch("mermaid_repair_service.stream_chat_completion_content")
def test_repair_mermaid_code_maps_llm_client_error_to_repair_error(
    mock_stream,
) -> None:
    mock_stream.side_effect = LlmClientError("OpenAI unavailable")
    request = MermaidRepairRequest.model_validate({
        "brokenCode": "graph TD\n  A-->",
        "errorMessage": "Syntax Error",
    })

    with pytest.raises(MermaidRepairError) as exc_info:
        repair_mermaid_code(
            request,
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )

    assert str(exc_info.value) == "OpenAI unavailable"
    assert isinstance(exc_info.value.__cause__, LlmClientError)
