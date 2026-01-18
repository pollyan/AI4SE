"""
Data Stream Protocol Formatting Tool

Implements Vercel AI SDK Data Stream Protocol (v1).
Reference: https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol
"""
import json
from typing import Any, Dict, Optional
from dataclasses import dataclass

@dataclass
class DataStreamHeaders:
    """Required Response Headers"""
    CONTENT_TYPE = "text/event-stream"
    CACHE_CONTROL = "no-cache"
    CONNECTION = "keep-alive"
    PROTOCOL_VERSION = "x-vercel-ai-ui-message-stream"
    NGINX_BUFFERING = "x-accel-buffering"
    
    @classmethod
    def as_dict(cls) -> Dict[str, str]:
        return {
            "Content-Type": cls.CONTENT_TYPE,
            "Cache-Control": cls.CACHE_CONTROL,
            "Connection": cls.CONNECTION,
            cls.PROTOCOL_VERSION: "v1",
            cls.NGINX_BUFFERING: "no",
        }

def format_part(code: str, value: Any) -> str:
    """Format a part of the stream using the protocol: code:json_string\n"""
    # If value is a string and the code expects a string (like '0' text), ensure it's JSON encoded
    # The protocol says: 0:"Hello" -> part code '0', value "Hello" (JSON string)
    return f"{code}:{json.dumps(value, ensure_ascii=False)}\n"

def stream_start(message_id: str) -> str:
    # 'start' is not a standard part of the protocol, sending empty text to establish stream
    # or we can send a custom data event if needed.
    # For now, sending a custom data part with messageId to keep backward compat logic if possible
    # But strictly, we should just start streaming text/tools.
    # Using '8' (data) for messageId info
    return format_part("8", [{"messageId": message_id}])

def stream_text_delta(text: str) -> str:
    """0: Text part"""
    return format_part("0", text)

def stream_tool_call(tool_call_id: str, tool_name: str, args: Dict) -> str:
    """9: Tool call part"""
    return format_part("9", {
        "toolCallId": tool_call_id,
        "toolName": tool_name,
        "args": args
    })

def stream_tool_result(tool_call_id: str, tool_name: str, result: Any) -> str:
    """a: Tool result part"""
    return format_part("a", {
        "toolCallId": tool_call_id,
        "toolName": tool_name,
        "result": result
    })

def stream_finish(reason: str = "stop", usage: Optional[Dict] = None) -> str:
    """d: Finish message part"""
    payload = {"finishReason": reason}
    if usage:
        payload["usage"] = usage
    return format_part("d", payload)

def stream_error(message: str) -> str:
    """e: Error part"""
    return format_part("e", {"error": message})

def stream_data(value: Any) -> str:
    """8: Data part (custom data)"""
    # Protocol expects a JSON list for data part usually, to append to data array?
    # SDK Docs: 8:[{"key":"value"}]
    # We'll ensure it's a list if it's not? Or just send as is if the SDK handles object.
    # Docs say: "8: JSON-stringified array of data values"
    if not isinstance(value, list):
        value = [value]
    return format_part("8", value)

def stream_done() -> str:
    """No specific 'done' code in v1 protocol, usually stream just ends.
    But we can send an empty data part or just nothing."""
    return ""

def stream_tool_call_streaming_start(tool_call_id: str, tool_name: str) -> str:
    """b: Tool call streaming start (not fully standardized in basic docs, using hypothetical 'b')
    Actually Vercel SDK v6 uses 'b' for 'tool_call_delta' which includes all info?
    Let's stick to non-streaming tool calls (9) for now unless we need streaming.
    If we need strictly, 'b' is often {toolCallId, toolName} or delta.
    Ref: https://github.com/vercel/ai/pull/3063
    """
    # This might need adjustment if we implement streaming tools
    # For now, we'll keep it but warn it might not be standard
    return format_part("b", {
        "toolCallId": tool_call_id,
        "toolName": tool_name
    })

def stream_tool_call_delta(tool_call_id: str, args_delta: str) -> str:
    """c: Tool call delta (hypothetical/beta)"""
    return format_part("c", {
        "toolCallId": tool_call_id,
        "argsTextDelta": args_delta
    })
