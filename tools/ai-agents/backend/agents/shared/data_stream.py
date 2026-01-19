"""
Vercel AI SDK Data Stream Protocol Utility (V2 - w/ text-delta)
https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#v2
"""

import json
from typing import Any, Dict

class DataStreamHeaders:
    """Standard headers for Vercel AI SDK Data Stream Protocol"""
    
    @staticmethod
    def as_dict() -> Dict[str, str]:
        return {
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache, no-transform",
            "X-Content-Type-Options": "nosniff",
            "Connection": "keep-alive",
            "X-Vercel-AI-Data-Stream": "v1",
        }


def format_event(event_data: Dict[str, Any]) -> str:
    """Formats a single SSE event for Data Stream Protocol V2"""
    # V2 format: data: {"type": "...", ...}\n\n
    return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

# ----------------------------------------------------------------------
# Data Stream Protocol Events (Adapted for Client Expectations)
# ----------------------------------------------------------------------

def stream_start(id=None):
    """
    Generate stream start event.
    Expected: { "type": "text-start", "id": "..." }
    """
    return format_event({
        "type": "text-start",
        "id": id or "msg_default"
    })

def stream_text_delta(delta, id=None):
    """
    Generate text delta event.
    Expected: { "type": "text-delta", "id": "...", "delta": "..." }
    """
    return format_event({
        "type": "text-delta",
        "id": id or "msg_default",
        "delta": delta
    })

def stream_text_end(id=None):
    """
    Generate text end event.
    Expected: { "type": "text-end", "id": "..." }
    """
    return format_event({
        "type": "text-end",
        "id": id or "msg_default"
    })

def stream_tool_call(tool_call, id=None):
    """
    Generate tool call event.
    """
    return format_event({
        "type": "tool_call",
        "tool_call": tool_call
    })

def stream_tool_result(tool_call_id, tool_name, result):
    """
    Generate tool result event (V2).
    Expected: { "type": "tool-result", "toolCallId": "...", "toolName": "...", "result": ... }
    """
    return format_event({
        "type": "tool-result",
        "toolCallId": tool_call_id,
        "toolName": tool_name,
        "result": result
    })

def stream_error(error):
    """Generate error event."""
    return format_event({
        "type": "error",
        "error": error
    })

def stream_data(data, data_type="data"):
    """
    Generate custom data event.
    Expected: { "type": "data-<suffix>", "data": ... }
    """
    # Ensure type has data- prefix if not already present (or just append)
    # Standard pattern: data-progress, data-weather, etc.
    # If caller passes just 'progress', we make it 'data-progress'
    
    suffix = data_type
    if not suffix.startswith("data-") and suffix != "data":
        # If suffix is just "progress", make it "data-progress"
        # If suffix is "data", we might need a default suffix like "data-value" 
        # but to keep backward compat or standard, let's allow "data-data" or just "data-custom"
        pass

    # AI SDK V2 requires 'data-' prefix for custom data types
    full_type = f"data-{suffix}" if not suffix.startswith("data-") else suffix
    
    # If generic 'data' is passed, we might want 'data-json' or similar to be safe,
    # but let's stick to the requester's plan of "data-progress" mainly.
    # For generic calls, we default to 'data-data' or similar? 
    # Actually, let's just prepend data- if missing.
    
    return format_event({
        "type": full_type,
        "data": data
    })

def stream_finish(finish_reason, usage=None):
    """Generate finish event."""
    payload = {
        "type": "finish",
        "finishReason": finish_reason
    }
    if usage:
        payload["usage"] = usage
    return format_event(payload)

def stream_done() -> str:
    """End of stream marker"""
    return ""
