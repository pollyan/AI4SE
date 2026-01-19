from typing import List, Any
import pytest
from unittest.mock import MagicMock, call

from backend.agents.lisa.schemas import WorkflowResponse, UpdateArtifact
# We will create this module in the next step
from backend.agents.lisa.stream_utils import process_workflow_stream

class MockAttributes:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

def test_process_workflow_stream_thought_only():
    """测试仅有 thought 变化的流"""
    # 模拟流数据 (Partial Updates)
    # Pydantic v2 stream usually returns partial models
    chunks = [
        WorkflowResponse(thought="A", progress_step=None, update_artifact=None),
        WorkflowResponse(thought="AB", progress_step=None, update_artifact=None),
        WorkflowResponse(thought="ABC", progress_step=None, update_artifact=None),
    ]
    
    # 模拟 writer
    mock_writer = MagicMock()
    
    # 执行流处理
    final_response = process_workflow_stream(chunks, mock_writer, [], "current_stage", {})
    
    # 验证最终结果
    assert final_response.thought == "ABC"
    
    # 验证 writer 调用 (expect text-delta events)
    # We expect verify that writer was called for deltas "A", "B", "C"
    # Note: exact calls depend on implementation details of stream_text_delta wrapping
    assert mock_writer.call_count >= 3 
    
    # Check args. Events are dicts like {'type': 'data_stream_event', 'event': {...}}
    calls = mock_writer.call_args_list
    assert len(calls) == 3
    # First call delta "A"
    assert "A" in str(calls[0]) 
    # Second call delta "B" (diff of AB - A)
    assert "B" in str(calls[1])
    # Third call delta "C" (diff of ABC - AB)
    assert "C" in str(calls[2])

def test_process_workflow_stream_progress_update():
    """测试 progress_step 更新"""
    chunks = [
        WorkflowResponse(thought="Thinking", progress_step="Step 1", update_artifact=None),
        # thought unchanged, step changed
        WorkflowResponse(thought="Thinking", progress_step="Step 2", update_artifact=None),
    ]
    
    mock_writer = MagicMock()
    plan = [{"id": "current_stage", "name": "Test Stage"}]
    
    final_response = process_workflow_stream(chunks, mock_writer, plan, "current_stage", {})
    
    assert final_response.progress_step == "Step 2"
    
    # Should produce progress events
    # We expect 2 calls (one for "Step 1" initial/change, one for "Step 2")
    # Actually, thought didn't change (len same), so no text delta.
    
    progress_calls = [c for c in mock_writer.call_args_list if "progress" in str(c)]
    assert len(progress_calls) >= 2
    assert "Step 1" in str(progress_calls[0])
    assert "Step 2" in str(progress_calls[1])

def test_process_workflow_stream_artifact_update():
    """测试 artifact 更新"""
    chunks = [
        WorkflowResponse(
            thought="Gen", 
            progress_step="Gen Art", 
            update_artifact=UpdateArtifact(key="test_design_strategy", markdown_body="C")
        ),
        WorkflowResponse(
            thought="Gen", 
            progress_step="Gen Art", 
            update_artifact=UpdateArtifact(key="test_design_strategy", markdown_body="Content")
        ),
    ]
    
    mock_writer = MagicMock()
    artifacts = {"test_design_strategy": ""}
    
    final = process_workflow_stream(chunks, mock_writer, [], "stage", artifacts)
    
    assert final.update_artifact.markdown_body == "Content"
    
    # Should see progress events with updated artifacts
    artifact_calls = [c for c in mock_writer.call_args_list if "artifacts" in str(c)]
    assert len(artifact_calls) >= 2
    # Verify content growth
    assert "Content" in str(artifact_calls[-1])
