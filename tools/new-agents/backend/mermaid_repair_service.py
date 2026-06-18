import re

from llm_client import LlmClientError, stream_chat_completion_content
from openai import APIError, AuthenticationError, RateLimitError
from prompts.mermaid_repair import (
    MERMAID_REPAIR_SYSTEM_PROMPT,
    build_mermaid_repair_user_prompt,
)
from request_schemas import MermaidRepairRequest


class MermaidRepairError(RuntimeError):
    pass


def clean_mermaid_repair_output(output: str) -> str:
    cleaned = output.strip()
    match = re.search(r"```(?:mermaid)?\n?([\s\S]*?)```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    else:
        cleaned = re.sub(r"^```mermaid\n?", "", cleaned)
        cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

    if not cleaned:
        raise MermaidRepairError("Mermaid repair returned empty code")

    return cleaned


def truncate_broken_code(broken_code: str) -> str:
    if len(broken_code) <= 5000:
        return broken_code
    return f"{broken_code[:5000]}\n...[TRUNCATED]"


def get_first_non_blank_line(text: str) -> str:
    return next((line for line in text.splitlines() if line.strip()), "unknown type")


def repair_mermaid_code(
    repair_request: MermaidRepairRequest,
    *,
    api_key: str,
    base_url: str | None,
    model_name: str,
) -> str:
    messages = [
        {
            "role": "system",
            "content": MERMAID_REPAIR_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": build_mermaid_repair_user_prompt(
                first_line=get_first_non_blank_line(repair_request.broken_code),
                error_message=repair_request.error_message,
                broken_code=truncate_broken_code(repair_request.broken_code),
                block_index=repair_request.block_index,
            ),
        },
    ]
    try:
        raw_response = "".join(
            stream_chat_completion_content(
                api_key=api_key,
                base_url=base_url,
                model=model_name,
                messages=messages,
                temperature=0.2,
            )
        )
    except (LlmClientError, AuthenticationError, RateLimitError, APIError) as e:
        raise MermaidRepairError(str(e)) from e
    return clean_mermaid_repair_output(raw_response)
