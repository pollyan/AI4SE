from collections.abc import Callable, Iterator, Sequence
from typing import Any, Protocol, TypeGuard

from openai import APIError, AuthenticationError, OpenAI, OpenAIError, RateLimitError


class ChatDelta(Protocol):
    content: str | None


class ChatChoice(Protocol):
    delta: ChatDelta
    finish_reason: str | None


class ChatStreamChunk(Protocol):
    choices: Sequence[ChatChoice]


class ChatUsage(Protocol):
    total_tokens: int


ChatMessage = dict[str, str]


class LlmClientError(RuntimeError):
    """Raised when the OpenAI client fails with a non-specific SDK error."""


SAFE_FINISH_REASONS = frozenset(
    {
        "content_filter",
        "insufficient_system_resource",
        "length",
        "stop",
        "tool_calls",
    }
)


def is_chat_stream_chunk(value: object) -> TypeGuard[ChatStreamChunk]:
    return hasattr(value, "choices")


def extract_delta_content(chunk: object) -> str | None:
    if not is_chat_stream_chunk(chunk):
        raise LlmClientError("LLM stream chunk missing choices")

    if not chunk.choices:
        return None

    delta = chunk.choices[0].delta
    if not delta:
        return None

    content = delta.content

    if content is None or content == "":
        return None

    if not isinstance(content, str):
        raise LlmClientError("LLM stream delta content must be a string")

    return content


def extract_total_tokens(chunk: object) -> int | None:
    usage = getattr(chunk, "usage", None)
    if usage is None:
        return None
    total_tokens = getattr(usage, "total_tokens", None)
    if not isinstance(total_tokens, int):
        return None
    return total_tokens


def extract_finish_reason(chunk: object) -> str | None:
    if not is_chat_stream_chunk(chunk) or not chunk.choices:
        return None
    finish_reason = getattr(chunk.choices[0], "finish_reason", None)
    if finish_reason is None:
        return None
    if not isinstance(finish_reason, str):
        return "unknown"
    return finish_reason if finish_reason in SAFE_FINISH_REASONS else "unknown"


def stream_chat_completion_content(
    *,
    api_key: str,
    base_url: str | None,
    model: str,
    messages: list[ChatMessage],
    temperature: float,
    response_format: dict[str, Any] | None = None,
    extra_body: dict[str, Any] | None = None,
    max_tokens: int | None = None,
    on_usage: Callable[[int], None] | None = None,
    on_finish_reason: Callable[[str], None] | None = None,
) -> Iterator[str]:
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if response_format is not None:
            request_kwargs["response_format"] = response_format
        if extra_body is not None:
            request_kwargs["extra_body"] = extra_body
        if max_tokens is not None:
            request_kwargs["max_tokens"] = max_tokens
        if on_usage is not None:
            request_kwargs["stream_options"] = {"include_usage": True}
        stream = client.chat.completions.create(**request_kwargs)

        for chunk in stream:
            finish_reason = extract_finish_reason(chunk)
            if finish_reason is not None and on_finish_reason is not None:
                on_finish_reason(finish_reason)
            total_tokens = extract_total_tokens(chunk)
            if total_tokens is not None and on_usage is not None:
                on_usage(total_tokens)
            content = extract_delta_content(chunk)
            if content:
                yield content
    except (AuthenticationError, RateLimitError, APIError):
        raise
    except OpenAIError as e:
        raise LlmClientError(str(e)) from e
