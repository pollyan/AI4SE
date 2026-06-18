import json

from sse_schemas import SseEvent


def encode_sse_event(event: SseEvent) -> str:
    payload = event.model_dump(mode="json", exclude_none=True)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def encode_sse_done() -> str:
    return "data: [DONE]\n\n"
