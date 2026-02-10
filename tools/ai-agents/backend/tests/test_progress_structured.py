import pytest
from backend.agents.shared.progress import get_progress_info

def test_get_progress_info_returns_structured_artifacts():
    """测试 get_progress_info 包含 structured_artifacts"""
    state = {
        "plan": [{"id": "S1", "name": "Stage 1"}],
        "current_stage_id": "S1",
        "artifacts": {"key1": "markdown content"},
        "structured_artifacts": {"key1": {"some": "data", "_diff": "added"}}
    }
    info = get_progress_info(state)
    
    assert info is not None
    # 目前实现中尚未添加 structured_artifacts 字段，预期失败
    assert "structured_artifacts" in info
    assert info["structured_artifacts"]["key1"]["some"] == "data"
    assert info["structured_artifacts"]["key1"]["_diff"] == "added"
