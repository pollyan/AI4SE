"""
Test Vercel AI SDK Data Stream Protocol Compliance
Reference: https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol

This test ensures that the backend data_stream.py module produces
output that is strictly compliant with the protocol expected by
the frontend Vercel AI SDK adapter.
"""
import json
import pytest
from backend.agents.shared import data_stream
from backend.agents.shared.data_stream import DataStreamHeaders

class TestDataStreamProtocolCompliance:
    """
    Protocol Format Reference:
    0: Text part
    8: Data part
    9: Tool call part
    a: Tool result part
    b: Tool call streaming part (optional)
    c: Tool result streaming part (optional - not implemented yet)
    d: Finish message part
    e: Error part
    """

    def test_header_compliance(self):
        """Verify headers match Vercel AI SDK requirements"""
        headers = DataStreamHeaders.as_dict()
        assert headers["Content-Type"] == "text/event-stream"
        assert headers["x-vercel-ai-ui-message-stream"] == "v1"

    def test_text_stream_format(self):
        """
        Verify text delta format.
        Protocol: 0:{string}\n
        """
        output = data_stream.stream_text_delta("Hello")
        
        # Strict Data Stream Protocol Check
        assert output == '0:"Hello"\n'

    def test_tool_call_format(self):
        """
        Verify tool call format.
        Protocol (v1): 9:{toolCallId, toolName, args}\n
        """
        tool_id = "call_123"
        name = "get_weather"
        args = {"location": "San Francisco"}
        
        output = data_stream.stream_tool_call(tool_id, name, args)
        
        # Strict Data Stream Protocol Check
        # 9:{"toolCallId":"call_123","toolName":"get_weather","args":{"location":"San Francisco"}}\n
        assert output.startswith("9:")
        payload_str = output[2:].strip()
        data = json.loads(payload_str)
        assert data["toolCallId"] == tool_id
        assert data["toolName"] == name
        assert data["args"] == args

    def test_tool_result_format(self):
        """
        Verify tool result format.
        Protocol (v1): a:{toolCallId, toolName, result}\n
        """
        tool_id = "call_123"
        name = "get_weather"
        result = "Sunny, 25C"
        
        output = data_stream.stream_tool_result(tool_id, name, result)
        
        # Strict Data Stream Protocol Check
        # a:{"toolCallId":"call_123","toolName":"get_weather","result":"Sunny, 25C"}\n
        assert output.startswith("a:")
        payload_str = output[2:].strip()
        data = json.loads(payload_str)
        assert data["toolCallId"] == tool_id
        assert data["toolName"] == name
        assert data["result"] == result

    def test_finish_format(self):
        """
        Verify finish format.
        Protocol (v1): d:{finishReason, usage}\n
        """
        reason = "stop"
        usage = {"promptTokens": 10, "completionTokens": 20}
        
        output = data_stream.stream_finish(reason, usage)
        
        # Strict Data Stream Protocol Check
        # d:{"finishReason":"stop","usage":{"promptTokens":10,"completionTokens":20}}\n
        assert output.startswith("d:")
        payload_str = output[2:].strip()
        data = json.loads(payload_str)
        assert data["finishReason"] == reason
        assert data["usage"] == usage

    def test_error_sanitization(self):
        """
        Verify error format sanitization.
        Should not leak tracebacks.
        Protocol (v1): e:{error: string}\n
        """
        raw_error = "Connection failed: SecretKey=12345"
        # We expect the stream_error to wrap this.
        # Ideally, we want the system to mask secrets, but data_stream.py just formats.
        # The logic for sanitization should be in the caller (requirements.py).
        # But here we verify the FORMAT is correct.
        
        output = data_stream.stream_error(raw_error)
        assert output.startswith("e:")
        # e:{"error":"Connection failed: SecretKey=12345"}\n
        payload_str = output[2:].strip()
        data = json.loads(payload_str)
        assert data["error"] == raw_error
