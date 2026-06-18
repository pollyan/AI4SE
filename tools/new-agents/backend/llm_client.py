from collections.abc import Iterator, Sequence
from typing import Protocol, TypeGuard

from openai import APIError, AuthenticationError, OpenAI, OpenAIError, RateLimitError


class ChatDelta(Protocol):
    content: str | None


class ChatChoice(Protocol):
    delta: ChatDelta


class ChatStreamChunk(Protocol):
    choices: Sequence[ChatChoice]


ChatMessage = dict[str, str]


class LlmClientError(RuntimeError):
    """Raised when the OpenAI client fails with a non-specific SDK error."""


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


def stream_chat_completion_content(
    *,
    api_key: str,
    base_url: str | None,
    model: str,
    messages: list[ChatMessage],
    temperature: float,
) -> Iterator[str]:
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )

        for chunk in stream:
            content = extract_delta_content(chunk)
            if content:
                yield content
    except (AuthenticationError, RateLimitError, APIError):
        raise
    except OpenAIError as e:
        raise LlmClientError(str(e)) from e
