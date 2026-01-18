
import pytest
import json
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage, AIMessageChunk
from backend.agents.service import LangchainAssistantService

@pytest.mark.asyncio
async def test_stream_lisa_message_deduplication():
    """
    Test that _stream_lisa_message correctly handles duplicate content.
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    service._lisa_session_states = {
        "test_session": {
            "messages": [],
            "current_workflow": "test_design",
            "workflow_stage": "clarify"
        }
    }
    
    target_node = "workflow_test_design"
    
    # 修正：LangGraph stream_mode="messages" 发送的是增量(incremental) chunks
    # 之前的测试用了累积(cumulative) chunks，导致去重逻辑变得必要但有害
    mock_events = [
        ("messages", (AIMessageChunk(content="H"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="e"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="l"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="l"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="o"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content=" "), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="W"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="o"), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
            
    service.agent.astream = mock_astream
    
    collected_output = []
    async for chunk in service._stream_graph_message("test_session", "User input"):
        if isinstance(chunk, str):
            collected_output.append(chunk)
        
    full_text = "".join(collected_output)
    
    assert full_text == "Hello Wo", f"Expected 'Hello Wo', got '{full_text}'"
    # 验证是否收到了所有 chunks
    # 注意：由于 clean_response_streaming 包含 rstrip()，末尾的空格会被暂存
    # 直到下一个非空字符到来时才一起输出。所以 ' ' 和 'W' 可能会合并为 ' W'
    assert full_text == "Hello Wo", f"Expected 'Hello Wo', got '{full_text}'"
    # 只要内容正确即可，不需要严格对应 chunks 边界
    assert "Hello Wo" in "".join(collected_output)

@pytest.mark.asyncio
async def test_stream_lisa_message_duplicate_chunks():
    """Test duplicate incremental chunks are preserved (not swallowed)"""
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    service._lisa_session_states = {"sess": {"messages": [], "current_workflow": None}}
    
    target_node = "workflow_test_design"
    
    # 模拟增量 chunks，其中包含重复内容 (例如 LLM 输出 "AA")
    mock_events = [
        ("messages", (AIMessageChunk(content="A"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="B"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="B"), {"langgraph_node": target_node})), # 重复 B
        ("messages", (AIMessageChunk(content="C"), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    collected_output = []
    async for chunk in service._stream_graph_message("sess", "input"):
        if isinstance(chunk, str):
            collected_output.append(chunk)
        
    # 修正期望：如果是增量，BB 应该保留，而不是被去重
    assert "".join(collected_output) == "ABBC"
    assert collected_output == ["A", "B", "B", "C"]


@pytest.mark.asyncio
async def test_stream_lisa_message_parses_progress_json():
    """
    Test parsing JSON structured output.
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    target_node = "workflow_test_design"
    
    json_block = '''```json
{
  "plan": [
    {"id": "clarify", "name": "需求澄清", "status": "completed"},
    {"id": "strategy", "name": "策略制定", "status": "active"}
  ],
  "current_stage_id": "strategy",
  "artifacts": [],
  "message": "接下来我们进入策略制定阶段。"
}
```'''
    
    mock_events = [
        ("messages", (AIMessageChunk(content=json_block), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    state_events = []
    async for chunk in service._stream_graph_message("test_session", "确认需求"):
        if isinstance(chunk, dict) and chunk.get("type") == "state":
            state_events.append(chunk)
    
    assert len(state_events) >= 1, "应至少有一个 state 事件"
    
    final_state_event = state_events[-1]
    progress = final_state_event.get("progress", {})
    stages = progress.get("stages", [])
    
    assert len(stages) == 2, f"应有 2 个阶段，实际: {len(stages)}"
    assert stages[1]["id"] == "strategy"
    assert stages[1]["status"] == "active"
    assert progress.get("currentStageIndex") == 1


@pytest.mark.asyncio
async def test_stream_lisa_message_cleans_json_from_stored_message():
    """
    Test JSON block removal from stored message.
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    
    target_node = "workflow_test_design"
    
    response_with_json = '''开始
```json
{"plan": [{"id":"a","status":"active"}], "current_stage_id": "a", "artifacts": [], "message": "内容"}
```
结束'''
    
    mock_events = [
        ("messages", (AIMessageChunk(content=response_with_json), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    collected_text = []
    async for chunk in service._stream_graph_message("test_session", "test"):
        if isinstance(chunk, str):
            collected_text.append(chunk)
    
    final_text = "".join(collected_text)
    
    assert "```json" not in final_text, f"JSON 块应被移除，实际: {final_text}"
    assert "开始" in final_text
    assert "结束" in final_text


@pytest.mark.asyncio
async def test_stream_lisa_message_emits_updated_progress_state():
    """
    Test that state event reflects new progress.
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()

    from backend.agents.lisa.state import get_initial_state
    initial_state = get_initial_state()
    initial_state["current_workflow"] = "test_design"
    
    initial_state["plan"] = [
        {"id": "clarify", "name": "需求澄清", "status": "active"},
        {"id": "strategy", "name": "测试策略", "status": "pending"},
    ]
    initial_state["current_stage_id"] = "clarify"
    
    service._lisa_session_states = {"test_session": initial_state}
    
    target_node = "workflow_test_design"
    
    new_plan = '''```json
{
  "plan": [
    {"id": "clarify", "name": "需求澄清", "status": "completed"},
    {"id": "strategy", "name": "测试策略", "status": "active"}
  ],
  "current_stage_id": "strategy",
  "artifacts": [],
  "message": "完成"
}
```'''
    
    mock_events = [
        ("messages", (AIMessageChunk(content=new_plan), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    state_events = []
    async for chunk in service._stream_graph_message("test_session", "test"):
        if isinstance(chunk, dict) and chunk.get("type") == "state":
            state_events.append(chunk)
    
    assert len(state_events) >= 1
    
    final_state_event = state_events[-1]
    progress = final_state_event.get("progress", {})
    
    assert progress.get("currentStageIndex") == 1


@pytest.mark.asyncio
async def test_stream_filters_aimessage_only_processes_aimessagechunk():
    """
    [TDD] 测试：stream_mode="messages" 只处理 AIMessageChunk，忽略 AIMessage
    
    真实场景：LangGraph stream_mode="messages" 会发送：
    1. AIMessageChunk（累积式，每次包含之前所有内容）
    2. AIMessage（节点返回的完整消息）
    
    问题：当 chunk 累积有丢字时，AIMessage 与累积内容互不包含，导致追加重复。
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    service._lisa_session_states = {"test_session": {"messages": [], "current_workflow": "test_design"}}
    
    target_node = "workflow_test_design"
    
    # 模拟 LangGraph 的实际行为：
    # 1. 先发送流式 chunks (AIMessageChunk) - 增量
    # 2. 最后发送完整消息 (AIMessage) - 这个应该被忽略
    mock_events = [
        # 流式 token chunks (增量)
        ("messages", (AIMessageChunk(content="你"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="好"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="世"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="界"), {"langgraph_node": target_node})),
        # 节点返回的完整消息（包含完整内容）- 应该被过滤掉
        ("messages", (AIMessage(content="你好世界"), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    collected_output = []
    async for chunk in service._stream_graph_message("test_session", "test"):
        if isinstance(chunk, str):
            collected_output.append(chunk)
    
    full_text = "".join(collected_output)
    
    # 期望：chunks 被累加 ("你好世界")，AIMessage 被过滤 (否则会变成 "你好世界你好世界")
    # 注意：我们已经删除了去重逻辑，所以如果 chunks 是累积的（如之前的测试），结果会是重复的
    # 但如果 chunks 是增量的（如现在），结果就是 "你好世界"
    assert full_text == "你好世界", f"Expected '你好世界', got '{full_text}'"
    assert collected_output == ["你", "好", "世", "界"], f"应该只有 4 个 chunks，实际: {collected_output}"


@pytest.mark.asyncio
async def test_stream_does_not_swallow_repeated_tokens():
    """
    [TDD] 测试：流式处理不应吞掉重复出现的字符（如 markdown 的 ** 或重复词）
    
    场景：
    1. Chunk 1: "**"
    2. Chunk 2: "重要"
    3. Chunk 3: "**" (如果不当去重，这个会被吞，因为 "**" 已在 full_response 中)
    
    期望：full_text 应为 "**重要**"
    """
    service = LangchainAssistantService("lisa")
    service.agent = MagicMock()
    service._lisa_session_states = {"test_session": {"messages": [], "current_workflow": "test_design"}}
    
    target_node = "workflow_test_design"
    
    mock_events = [
        ("messages", (AIMessageChunk(content="**"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="重要"), {"langgraph_node": target_node})),
        ("messages", (AIMessageChunk(content="**"), {"langgraph_node": target_node})),
    ]
    
    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event
    service.agent.astream = mock_astream
    
    collected_output = []
    async for chunk in service._stream_graph_message("test_session", "test"):
        if isinstance(chunk, str):
            collected_output.append(chunk)
    
    full_text = "".join(collected_output)
    
    assert full_text == "**重要**", f"Markdown 格式损坏！Got: '{full_text}'"
