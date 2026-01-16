
import pytest
from backend.agents.alex.tools import set_plan, update_stage, update_task, save_artifact

def test_set_plan():
    stages = [
        {"id": "s1", "name": "Stage 1", "artifact_key": "a1", "artifact_name": "Artifact 1"},
        {"id": "s2", "name": "Stage 2"}
    ]
    result = set_plan(stages)
    assert "已设置 2 个阶段的工作流计划" in result
    assert "包含 1 个产出物模板" in result

def test_set_plan_empty():
    result = set_plan([])
    assert "已设置 0 个阶段的工作流计划" in result

def test_update_stage():
    result = update_stage("s1", "completed")
    assert "阶段 's1' 状态已更新为 'completed'" in result

def test_update_task():
    result = update_task("正在进行测试...")
    assert "当前任务已更新为: '正在进行测试...'" in result

def test_save_artifact():
    result = save_artifact("a1", "# Content")
    assert "产出物 'a1' 已保存" in result
    assert "(9 字符)" in result

def test_save_artifact_empty():
    result = save_artifact("a1", "")
    assert "产出物 'a1' 已保存" in result
    assert "(0 字符)" in result
