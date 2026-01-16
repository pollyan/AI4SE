
import pytest
from backend.agents.alex.tools import update_progress, update_artifact

def test_update_progress():
    stages = [
        {"id": "clarify", "name": "需求澄清", "status": "active"},
        {"id": "strategy", "name": "策略制定", "status": "pending"}
    ]
    result = update_progress(stages, "clarify", "Testing task")
    assert "进度已更新" in result
    assert "2 个阶段" in result
    assert "当前阶段 'clarify'" in result

def test_update_progress_empty():
    result = update_progress([], "", "")
    assert "进度已更新: 0 个阶段" in result

def test_update_artifact():
    result = update_artifact("req_doc", "overview", "# Content")
    assert "产出物 'req_doc' 的章节 'overview' 已更新" in result
