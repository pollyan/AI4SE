"""
SSE 事件流解析工具

将 Flask test_client 的 SSE 响应解析为结构化事件列表，
支持轨迹提取和文本拼接，让 Smoke Test 断言简洁清晰。
"""

import json
from dataclasses import dataclass
from typing import List


@dataclass
class SSEEvent:
    """一个 SSE 事件"""
    event_type: str       # "text-start", "text-delta", "tool-input-available" 等
    data: dict            # 解析后的 JSON 数据
    raw: str              # 原始 data: 行


@dataclass
class ToolCall:
    """工具调用轨迹项"""
    tool_name: str        # "update_artifact" 或 "UpdateStructuredArtifact"
    artifact_key: str     # "test_design_requirements" 等


def parse_sse_response(response) -> List[SSEEvent]:
    """
    从 Flask test_client 的 Response 中解析所有 SSE 事件。

    SSE 格式: data: {"type": "...", ...}\\n\\n
    """
    events = []
    raw_data = response.get_data(as_text=True)

    for line in raw_data.split("\n"):
        line = line.strip()
        if not line or not line.startswith("data: "):
            continue

        json_str = line[6:]  # 去掉 "data: " 前缀
        if not json_str:
            continue

        try:
            data = json.loads(json_str)
            event_type = data.get("type", "unknown")
            events.append(SSEEvent(event_type=event_type, data=data, raw=line))
        except json.JSONDecodeError:
            # 忽略非 JSON 行（如空行或 done 标记）
            continue

    return events


def send_and_collect(client, session_id: str, message: str) -> List[SSEEvent]:
    """
    发送一条消息并收集所有 SSE 事件。

    封装了 HTTP 请求 + SSE 解析，让多轮测试代码简洁。
    """
    response = client.post(
        f"/ai-agents/api/requirements/sessions/{session_id}/messages/v2/stream",
        json={"messages": [{"role": "user", "content": message}]},
        content_type="application/json"
    )
    assert response.status_code == 200, (
        f"请求失败: HTTP {response.status_code}\n"
        f"响应: {response.get_data(as_text=True)[:500]}"
    )
    return parse_sse_response(response)


def extract_full_text(events: List[SSEEvent]) -> str:
    """从事件流中拼接完整文本回复"""
    return "".join(
        e.data.get("delta", "")
        for e in events
        if e.event_type == "text-delta"
    )


def extract_tool_trajectory(events: List[SSEEvent]) -> List[ToolCall]:
    """
    从事件流中提取有序的工具调用轨迹。

    注意: SSE 中 tool-input-available 的 input 格式是 {"key": "test_design_requirements"}，
    不包含 artifact_type。artifact_key 直接从 input.key 获取。
    """
    return [
        ToolCall(
            tool_name=e.data.get("toolName", "unknown"),
            artifact_key=e.data.get("input", {}).get("key", "unknown")
        )
        for e in events
        if e.event_type == "tool-input-available"
    ]


def get_tool_events(events: List[SSEEvent]) -> List[SSEEvent]:
    """提取所有工具调用事件（tool-input-available）"""
    return [e for e in events if e.event_type == "tool-input-available"]


def assert_stream_integrity(events: List[SSEEvent]) -> None:
    """
    断言 SSE 流的基本完整性：
    - 有 text-start 事件
    - 有 text-delta 事件
    - 有 text-end 事件
    - 有 finish 事件
    """
    types = [e.event_type for e in events]
    assert "text-start" in types, f"缺少 text-start 事件。实际事件类型: {types}"
    assert "text-delta" in types, f"缺少 text-delta 事件。实际事件类型: {types}"
    assert "text-end" in types, f"缺少 text-end 事件。实际事件类型: {types}"
    assert "finish" in types, f"缺少 finish 事件。实际事件类型: {types}"
