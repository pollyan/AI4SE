import pytest
from backend.agents.shared.progress import get_progress_info

def test_artifact_templates_processing():
    """验证 artifact_templates 和 artifacts 能正确被 get_progress_info 处理"""
    
    # 模拟 service.py 中构建的 current_state
    mock_state = {
        "plan": [
            {"id": "clarify", "name": "需求澄清", "status": "active"},
            {"id": "strategy", "name": "策略制定", "status": "pending"}
        ],
        "current_stage_id": "clarify",
        # 验证点 1: 包含 artifact_templates
        "artifact_templates": [
            {"stage_id": "clarify", "artifact_key": "test_design_requirements", "name": "需求澄清报告"},
            {"stage_id": "strategy", "artifact_key": "test_design_strategy", "name": "测试策略蓝图"}
        ],
        # 验证点 2: 包含 artifacts 内容
        "artifacts": {
            "test_design_requirements": "# 需求报告内容..."
        }
    }
    
    progress_info = get_progress_info(mock_state)
    
    assert progress_info is not None
    artifact_progress = progress_info["artifactProgress"]
    
    # 验证点 3: template 列表包含所有阶段的模板
    templates = artifact_progress["template"]
    assert len(templates) == 2
    assert templates[0]["name"] == "需求澄清报告"
    assert templates[1]["name"] == "测试策略蓝图"
    
    # 验证点 4: completed 列表包含已生成的 key
    assert "test_design_requirements" in artifact_progress["completed"]

def test_workflow_test_design_templates():
    """验证 workflow_test_design 模块中的模板定义"""
    from backend.agents.lisa.nodes.workflow_test_design import get_artifact_templates
    
    # 测试设计工作流
    templates = get_artifact_templates("test_design")
    assert len(templates) == 4
    assert templates[0]["artifact_key"] == "test_design_requirements"
    assert templates[1]["artifact_key"] == "test_design_strategy"
    
    # 需求评审工作流
    templates_review = get_artifact_templates("requirement_review")
    assert len(templates_review) == 4
    assert templates_review[0]["artifact_key"] == "req_review_record"
