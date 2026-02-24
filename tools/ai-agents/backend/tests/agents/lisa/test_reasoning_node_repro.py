import pytest
from unittest.mock import MagicMock
from langchain_core.messages import HumanMessage
from backend.agents.lisa.nodes.reasoning_node import reasoning_node
from backend.agents.lisa.state import LisaState

@pytest.mark.asyncio
async def test_reasoning_node_initialization_sends_templates():
    """
    Regression Test: 验证 ReasoningNode 在工作流初始化时，
    是否在流式输出中正确发送了 artifact_templates。
    
    场景：用户发送第一条消息（或上传文件），State 中没有 plan 和 templates。
    期望：stream_utils 处理后的 progress 事件中包含完整的 artifactProgress.template。
    """
    
    # 1. 模拟初始状态 (无 plan, 无 templates)
    state = LisaState(
        messages=[HumanMessage(content="分析需求")],
        artifacts={},
        plan=[],
        artifact_templates=[], # Empty!
        current_workflow="test_design",
        current_stage_id="clarify"
    )
    
    # 2. Mock LLM and Stream Writer
    mock_llm = MagicMock()
    # 模拟 LLM 文本响应
    mock_llm.model.invoke.return_value.content = '{"thought": "Thinking...", "progress_step": "初始化中...", "should_update_artifact": false, "intent": "provide_material", "confidence": 0.9}'
    
    # Mock get_robust_stream_writer
    mock_writer = MagicMock()
    
    # Patch get_robust_stream_writer to capture output
    # 直接 patch 目标模块的全局命名空间
    import sys
    target_module = sys.modules["backend.agents.lisa.nodes.reasoning_node"]
    
    with pytest.MonkeyPatch().context() as m:
        m.setattr(target_module, "get_robust_stream_writer", lambda *args, **kwargs: mock_writer)
        
        # 3. 执行 ReasoningNode
        reasoning_node(state, None, mock_llm)
        
        # 4. 验证 Writer 调用
        # 我们期望至少有一次调用包含 'progress' 且 'artifactProgress.template' 不为空
        
        calls = mock_writer.call_args_list
        found_templates = False
        
        print("\n=== Writer Calls ===")
        for call in calls:
            data = call[0][0]
            print(data)
            
            if data.get("type") == "progress":
                progress = data.get("progress", {})
                
                # 检查 artifactProgress
                artifact_progress = progress.get("artifactProgress")
                if artifact_progress:
                    templates = artifact_progress.get("template")
                    if templates and len(templates) > 0:
                        found_templates = True
                        print(f"✅ Found templates: {len(templates)}")
                        
                # 同时也检查直接的 artifact_templates (初始化事件)
                raw_templates = progress.get("artifact_templates")
                if raw_templates and len(raw_templates) > 0:
                    print(f"✅ Found raw templates in init event: {len(raw_templates)}")

        assert found_templates, "❌ 未在流式输出中找到 artifactProgress.template，前端会导致内容消失！"
