from unittest.mock import MagicMock, patch

import pytest
from openai import OpenAIError

from llm_client import (
    LlmClientError,
    extract_delta_content,
    extract_finish_reason,
    stream_chat_completion_content,
)


class MockDelta:
    def __init__(self, content: str | None) -> None:
        self.content = content


class MockChoice:
    def __init__(
        self,
        content: str | None,
        finish_reason: str | None = None,
    ) -> None:
        self.delta = MockDelta(content)
        self.finish_reason = finish_reason


class MockChunk:
    def __init__(
        self,
        content: str | None,
        finish_reason: str | None = None,
    ) -> None:
        self.choices = (
            [MockChoice(content, finish_reason)]
            if content is not None or finish_reason is not None
            else []
        )


class MockUsage:
    def __init__(self, total_tokens: int) -> None:
        self.total_tokens = total_tokens


class MockUsageChunk:
    def __init__(self, total_tokens: int) -> None:
        self.choices = []
        self.usage = MockUsage(total_tokens)


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

    chunks = list(
        stream_chat_completion_content(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model="test-model",
            messages=messages,
            temperature=0.2,
        )
    )

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
def test_stream_chat_completion_content_reports_usage_when_callback_is_supplied(
    mock_openai: MagicMock,
) -> None:
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value = [
        MockChunk("Hello"),
        MockUsageChunk(42),
    ]
    usage_values: list[int] = []
    messages = [{"role": "user", "content": "Hi"}]

    chunks = list(
        stream_chat_completion_content(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model="test-model",
            messages=messages,
            temperature=0.2,
            on_usage=usage_values.append,
        )
    )

    assert chunks == ["Hello"]
    assert usage_values == [42]
    mock_client.chat.completions.create.assert_called_once_with(
        model="test-model",
        messages=messages,
        temperature=0.2,
        stream=True,
        stream_options={"include_usage": True},
    )


@patch("llm_client.OpenAI")
def test_stream_chat_completion_content_reports_safe_finish_reason_and_token_limit(
    mock_openai: MagicMock,
) -> None:
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value = [
        MockChunk('{"chat":'),
        MockChunk(None, "length"),
    ]
    finish_reasons: list[str] = []
    messages = [{"role": "user", "content": "Hi"}]

    chunks = list(
        stream_chat_completion_content(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model="test-model",
            messages=messages,
            temperature=0,
            max_tokens=32768,
            on_finish_reason=finish_reasons.append,
        )
    )

    assert chunks == ['{"chat":']
    assert finish_reasons == ["length"]
    mock_client.chat.completions.create.assert_called_once_with(
        model="test-model",
        messages=messages,
        temperature=0,
        stream=True,
        max_tokens=32768,
    )


def test_extract_finish_reason_projects_unknown_provider_value() -> None:
    assert extract_finish_reason(MockChunk(None, "provider-secret-reason")) == "unknown"


@patch("llm_client.OpenAI")
def test_stream_chat_completion_content_wraps_base_openai_errors(
    mock_openai: MagicMock,
) -> None:
    mock_openai.side_effect = OpenAIError("OpenAI unavailable")

    with pytest.raises(LlmClientError) as exc_info:
        list(
            stream_chat_completion_content(
                api_key="test-api-key",
                base_url="https://api.test.com/v1",
                model="test-model",
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
            )
        )

    assert str(exc_info.value) == "OpenAI unavailable"
    assert isinstance(exc_info.value.__cause__, OpenAIError)


def test_extract_delta_content_rejects_malformed_stream_chunk() -> None:
    with pytest.raises(LlmClientError) as exc_info:
        extract_delta_content("not a stream chunk")

    assert str(exc_info.value) == "LLM stream chunk missing choices"
