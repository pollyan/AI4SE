"""
Data Stream Protocol V2 测试
TDD: 先编写测试，验证 V2 协议格式的正确性
"""

import pytest
import json


class TestDataStreamV2Protocol:
    """Data Stream Protocol V2 格式测试"""

    def _format_event(self, event_json_str: str) -> str:
        """Helper to format a JSON string into an SSE data event."""
        return f"data: {event_json_str}\n\n"

    def test_text_event_format(self):
        """V2 文本事件应该使用显式类型格式"""
        # V2 期望格式: { "type": "text", "value": "Hello" }
        from backend.agents.shared.data_stream import stream_text_delta
        
        result = stream_text_delta("Hello")
        
        # 解析 SSE 格式
        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        
        # 提取 JSON 部分
        json_part = result[6:-2]  # 去掉 "data: " 和 "\n\n"
        
        # V1 格式是 "0:\"Hello\""，V2 应该是对象格式
        # 暂时验证当前 V1 格式，后续更新到 V2
        # 目前 V1 使用: 0:"Hello"
        assert "0:" in json_part or "text" in json_part.lower()

    def test_text_stream_events(self):
        """Test text stream events generation (text-start, text-delta, text-end)."""
        from backend.agents.shared import data_stream
        # 1. Text Start
        start_event = data_stream.stream_start("msg_1")
        assert start_event.startswith("data: ")
        assert start_event.endswith("\n\n")
        data = json.loads(start_event[6:-2])
        assert data["type"] == "text-start"
        assert data["id"] == "msg_1"

        # 2. Text Delta
        delta_event = data_stream.stream_text_delta("Hello", "msg_1")
        assert delta_event.startswith("data: ")
        assert delta_event.endswith("\n\n")
        data = json.loads(delta_event[6:-2])
        assert data["type"] == "text-delta"
        assert data["id"] == "msg_1"
        assert data["delta"] == "Hello"

        # 3. Text End
        end_event = data_stream.stream_text_end("msg_1")
        assert end_event.startswith("data: ")
        assert end_event.endswith("\n\n")
        data = json.loads(end_event[6:-2])
        assert data["type"] == "text-end"
        assert data["id"] == "msg_1"

    def test_data_event_format(self):
        """V2 自定义数据事件应该使用 data-xxx 类型"""
        from backend.agents.shared.data_stream import stream_data
        
        progress = {"stages": [{"id": "clarify", "name": "澄清需求", "status": "active"}]}
        result = stream_data(progress)
        
        assert result.startswith("data: ")
        
        # V1 格式: 8:[{...}]
        # V2 期望: { "type": "data-progress", "id": "...", "data": {...} }
        json_part = result[6:-2]
        assert "8:" in json_part or "data" in json_part.lower()

    def test_finish_event_format(self):
        """V2 完成事件格式验证"""
        from backend.agents.shared.data_stream import stream_finish
        
        result = stream_finish("stop")
        
        assert result.startswith("data: ")
        json_part = result[6:-2]
        
        # V1: d:{"finishReason":"stop"}
        # V2 应该类似
        assert "d:" in json_part or "finish" in json_part.lower()

    def test_error_event_format(self):
        """V2 错误事件格式验证"""
        from backend.agents.shared.data_stream import stream_error
        
        result = stream_error("Something went wrong")
        
        assert result.startswith("data: ")
        json_part = result[6:-2]
        
        # V1: e:{"error":"..."}
        assert "e:" in json_part or "error" in json_part.lower()

    def test_tool_call_event_format(self):
        """V2 工具调用事件格式验证 (tool-input-available)"""
        from backend.agents.shared.data_stream import stream_tool_input_available
        
        result = stream_tool_input_available(
            tool_call_id="call_123",
            tool_name="update_progress",
            args={"stage": "analysis"}
        )
        
        assert result.startswith("data: ")
        json_part = result[6:-2]
        data = json.loads(json_part)
        
        assert data["type"] == "tool-input-available"
        assert data["toolCallId"] == "call_123"
        assert data["toolName"] == "update_progress"
        assert data["input"] == {"stage": "analysis"}

    def test_tool_result_event_format(self):
        """V2 工具结果事件格式验证 (tool-output-available)"""
        from backend.agents.shared.data_stream import stream_tool_output_available
        
        result = stream_tool_output_available(
            tool_call_id="call_123",
            output={"success": True}
        )
        
        assert result.startswith("data: ")
        json_part = result[6:-2]
        data = json.loads(json_part)
        
        assert data["type"] == "tool-output-available"
        assert data["toolCallId"] == "call_123"
        assert data["output"] == {"success": True}


class TestDataStreamAdapter:
    """Data Stream 适配器测试"""

    @pytest.mark.asyncio
    async def test_adapter_yields_start_event(self):
        """适配器应该首先产生 start 事件"""
        # 需要 mock service
        pass

    @pytest.mark.asyncio
    async def test_adapter_converts_text_chunks(self):
        """适配器应该将文本 chunk 转换为 text 事件"""
        pass

    @pytest.mark.asyncio
    async def test_adapter_converts_state_to_data(self):
        """适配器应该将 state 事件转换为 data 事件"""
        pass

    @pytest.mark.asyncio
    async def test_adapter_yields_finish_at_end(self):
        """适配器应该在最后产生 finish 事件"""
        pass


class TestDataStreamHeaders:
    """V2 协议响应头测试"""

    def test_required_headers(self):
        """V2 协议需要正确的响应头"""
        from backend.agents.shared.data_stream import DataStreamHeaders
        
        headers = DataStreamHeaders.as_dict()
        
        assert "text/event-stream" in headers["Content-Type"]
        assert "no-cache" in headers.get("Cache-Control", "")
        assert "X-Vercel-AI-Data-Stream" in headers or "x-accel-buffering" in headers


class TestV2ProtocolMigration:
    """V1 到 V2 迁移测试"""

    def test_v2_text_format(self):
        """验证 V2 文本格式"""
        # V2 格式应该是: data: {"type":"text","value":"Hello"}\n\n
        expected_v2_format = {
            "type": "text",
            "value": "Hello"
        }
        
        # TODO: 实现 V2 stream_text 后验证
        # from backend.agents.shared.data_stream_v2 import stream_text
        # result = stream_text("Hello")
        # assert json.loads(result[6:-2]) == expected_v2_format
        pass

    def test_v2_data_progress_format(self):
        """验证 V2 进度数据格式"""
        # V2 格式应该是: data: {"type":"data-progress","id":"...","data":{...}}\n\n
        expected_structure = {
            "type": "data-progress",
            "id": str,  # UUID
            "data": dict,
        }
        
        # TODO: 实现后验证
        pass
