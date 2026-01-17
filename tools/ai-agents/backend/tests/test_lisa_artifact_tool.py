"""
Lisa Artifact Tool Tests

测试 Lisa 智能体从 Regex 模式迁移到 Tool Calling 模式的核心逻辑。
"""
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, SystemMessage

from backend.agents.lisa.schemas import UpdateArtifact, ArtifactType
from backend.agents.lisa.nodes.workflow_test_design import workflow_execution_node
from backend.agents.lisa.state import LisaState, get_initial_state

@pytest.mark.unit
def test_update_artifact_schema_validation():
    """测试 UpdateArtifact Schema 的校验逻辑"""
    
    # 1. 有效输入
    valid_data = {
        "key": ArtifactType.TEST_DESIGN_REQUIREMENTS,
        "markdown_body": "# 需求文档",
        "metadata": {"risk": "High"}
    }
    model = UpdateArtifact(**valid_data)
    assert model.key == ArtifactType.TEST_DESIGN_REQUIREMENTS
    assert model.markdown_body == "# 需求文档"
    
    # 2. 无效 Key
    with pytest.raises(Exception):
        UpdateArtifact(key="invalid_key", markdown_body="content")

@pytest.mark.unit
def test_node_handles_tool_call():
    """
    [TDD Red] 测试节点能否处理 ToolCall
    
    当前节点只支持 Regex 提取，预期此测试会失败。
    """
    
    # 1. 构造 Mock LLM
    mock_llm = MagicMock()
    
    # 构造一个包含 tool_calls 的 AIMessage
    # 模拟 LLM 想要调用 UpdateArtifact 工具
    tool_call_id = "call_123"
    tool_args = {
        "key": "test_design_strategy",
        "markdown_body": "# 更新后的策略文档",
        "metadata": {"status": "final"}
    }
    
    mock_response = AIMessage(
        content="我已更新了策略文档。",
        tool_calls=[{
            "name": "UpdateArtifact",
            "args": tool_args,
            "id": tool_call_id
        }]
    )
    
    # Mock bind_tools chain
    # llm.model.bind_tools(...) -> returns bound_llm -> bound_llm.invoke(...) -> returns mock_response
    mock_bound_llm = MagicMock()
    mock_bound_llm.invoke.return_value = mock_response
    
    # Also mock stream to support the new implementation
    from langchain_core.messages import AIMessageChunk
    
    # Convert AIMessage to AIMessageChunk
    tool_call_chunks = []
    if mock_response.tool_calls:
        for i, tc in enumerate(mock_response.tool_calls):
            # Note: args in tool_call is dict, but in chunk it is json string
            # For this test we just need it to not crash
            import json
            tool_call_chunks.append({
                "name": tc["name"],
                "args": json.dumps(tc["args"]), 
                "id": tc["id"],
                "index": i
            })
            
    mock_chunk = AIMessageChunk(
        content=mock_response.content,
        tool_call_chunks=tool_call_chunks
    )
    
    mock_bound_llm.stream.return_value = [mock_chunk]
    
    mock_llm.model.bind_tools.return_value = mock_bound_llm
    
    # 2. 构造初始状态
    state = get_initial_state()
    state["current_workflow"] = "test_design"
    state["current_stage_id"] = "strategy" # 确保处于正确的阶段
    
    # 3. 执行节点
    # 注意: 这里我们需要 patch get_stream_writer 以避免副作用
    with patch("backend.agents.lisa.nodes.workflow_test_design.get_stream_writer") as mock_writer:
        new_state = workflow_execution_node(state, mock_llm)
    
    # 4. 断言 (Expected Behavior in Target Architecture)
    # 产出物应该被更新
    assert "test_design_strategy" in new_state["artifacts"]
    assert new_state["artifacts"]["test_design_strategy"] == "# 更新后的策略文档"


@pytest.mark.asyncio
async def test_node_handles_streaming_tool_args():
    """
    [TDD Red] 测试流式工具参数解析
    
    模拟 LLM 分片输出 JSON 参数，验证 Adapter 能实时提取并推送 partial artifact content。
    """
    from langchain_core.messages import AIMessageChunk
    
    # 1. 构造 Mock LLM Stream
    mock_llm = MagicMock()
    
    # 构造流式 chunks
    chunks = [
        # Chunk 0: 启动 Tool Call
        AIMessageChunk(content="", tool_call_chunks=[{
            "name": "UpdateArtifact", 
            "args": "", 
            "id": "call_1",
            "index": 0
        }]),
        # Chunk 1: 开始输出 key
        AIMessageChunk(content="", tool_call_chunks=[{
            "name": "UpdateArtifact", 
            "args": '{"key": "test_design_requirements"', 
            "id": "call_1",
            "index": 0
        }]),
        # Chunk 2: 开始输出 body
        AIMessageChunk(content="", tool_call_chunks=[{
            "name": "UpdateArtifact", 
            "args": ', "markdown_body": "# Header"', 
            "id": "call_1",
            "index": 0
        }]),
        # Chunk 3: 继续输出 body
        AIMessageChunk(content="", tool_call_chunks=[{
            "name": "UpdateArtifact", 
            "args": '}', 
            "id": "call_1",
            "index": 0
        }])
    ]
    
    # Mock bind_tools().stream()
    mock_bound_llm = MagicMock()
    mock_bound_llm.stream.return_value = chunks # 同步迭代器 (模拟)
    
    # 注意: 真实代码中 llm.stream 是同步还是异步取决于 invoke 调用方式
    # LangGraph 节点通常是同步函数调用 invoke，但为了支持 stream 我们可能需要把 node 改为 async 
    # 或者使用 sync stream。这里假设我们使用同步 stream。
    
    mock_llm.model.bind_tools.return_value = mock_bound_llm
    
    # 2. 执行节点 (需要 Mock StreamWriter 来捕获推送)
    state = get_initial_state()
    state["current_stage_id"] = "clarify"
    
    with patch("backend.agents.lisa.nodes.workflow_test_design.get_stream_writer") as mock_get_writer:
        mock_writer = MagicMock()
        mock_get_writer.return_value = mock_writer
        
        # 调用节点
        workflow_execution_node(state, mock_llm)
        
        # 3. 断言
        # 我们期望 writer 被调用多次，且 args 中的 artifacts 内容在变化
        assert mock_writer.call_count >= 1
        
        # 验证是否收到了 "# Header" 的片段推送
        # 这需要我们在实现中能够解析 partial JSON
        # 在 Red 阶段，因为我们还没实现流式解析，这里肯定会失败
        
        # 检查是否至少有一次调用包含了 artifacts 更新
        found_artifact_update = False
        for call in mock_writer.call_args_list:
            args, _ = call
            payload = args[0]
            if payload.get("type") == "progress" and "artifacts" in payload.get("progress", {}):
                artifacts = payload["progress"]["artifacts"]
                if "test_design_requirements" in artifacts:
                    content = artifacts["test_design_requirements"]
                    if "# Header" in content:
                        found_artifact_update = True
                        break
        
        assert found_artifact_update, "未检测到流式产出物更新"
