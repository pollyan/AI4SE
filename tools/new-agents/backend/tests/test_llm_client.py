from unittest.mock import MagicMock, patch

import pytest
from openai import OpenAIError

from llm_client import (
    LlmClientError,
    extract_delta_content,
    stream_chat_completion_content,
)


class MockDelta:
    def __init__(self, content: str | None) -> None:
        self.content = content


class MockChoice:
    def __init__(self, content: str | None) -> None:
        self.delta = MockDelta(content)


class MockChunk:
    def __init__(self, content: str | None) -> None:
        self.choices = [MockChoice(content)] if content is not None else []


@patch("llm_client.OpenAI")
def test_stream_chat_completion_content_calls_openai_and_yields_content(
    mock_openai: MagicMock,
) -> None:
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value = [
        MockChunk("Hello"),
        MockChunk(""),
        MockChunk(None),
        MockChunk(" World"),
    ]

    messages = [{"role": "user", "content": "Hi"}]

    chunks = list(stream_chat_completion_content(
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model="test-model",
        messages=messages,
        temperature=0.2,
    ))

    assert chunks == ["Hello", " World"]
    mock_openai.assert_called_once_with(
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
    )
    mock_client.chat.completions.create.assert_called_once_with(
        model="test-model",
        messages=messages,
        temperature=0.2,
        stream=True,
    )


@patch("llm_client.OpenAI")
def test_stream_chat_completion_content_wraps_base_openai_errors(
    mock_openai: MagicMock,
) -> None:
    mock_openai.side_effect = OpenAIError("OpenAI unavailable")

    with pytest.raises(LlmClientError) as exc_info:
        list(stream_chat_completion_content(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model="test-model",
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.7,
        ))

    assert str(exc_info.value) == "OpenAI unavailable"
    assert isinstance(exc_info.value.__cause__, OpenAIError)


def test_extract_delta_content_rejects_malformed_stream_chunk() -> None:
    with pytest.raises(LlmClientError) as exc_info:
        extract_delta_content("not a stream chunk")

    assert str(exc_info.value) == "LLM stream chunk missing choices"
