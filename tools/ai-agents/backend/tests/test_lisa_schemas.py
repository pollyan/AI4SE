from backend.agents.lisa.schemas import WorkflowResponse, UpdateArtifact

def test_workflow_response_structure_full():
    """测试包含所有字段的完整响应结构"""
    data = {
        "thought": "正在生成文档",
        "progress_step": "正在生成测试策略",
        "update_artifact": {
            "key": "test_design_strategy",
            "markdown_body": "# Strategy"
        }
    }
    resp = WorkflowResponse(**data)
    assert resp.thought == "正在生成文档"
    assert resp.progress_step == "正在生成测试策略"
    assert resp.update_artifact.key == "test_design_strategy"
    assert resp.update_artifact.markdown_body == "# Strategy"

def test_workflow_response_optional_artifact():
    """测试不包含 artifact 的响应结构"""
    data = {
        "thought": "我需要更多信息",
        "progress_step": "等待用户输入"
    }
    resp = WorkflowResponse(**data)
    assert resp.thought == "我需要更多信息"
    assert resp.progress_step == "等待用户输入"
    assert resp.update_artifact is None

def test_workflow_response_minimal():
    """测试最小响应结构（只有 thought）"""
    data = {
        "thought": "思考中..."
    }
    resp = WorkflowResponse(**data)
    assert resp.thought == "思考中..."
    assert resp.progress_step is None
    assert resp.update_artifact is None
