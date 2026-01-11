"""
Progress 模块单元测试

测试 shared/progress.py 中的 get_progress_info 函数，
验证动态进度条基于 current_stage_id 正确计算。
"""

import pytest
from backend.agents.shared.progress import get_progress_info
from backend.agents.lisa.state import get_initial_state


class TestGetProgressInfo:
    """测试 get_progress_info 函数"""
    
    @pytest.fixture
    def base_state(self):
        """基础状态 fixture - 带有模拟的 plan"""
        state = get_initial_state()
        state["current_workflow"] = "test_design"
        # 手动添加 plan 用于测试（初始 state 现在是空 plan）
        state["plan"] = [
            {"id": "clarify", "name": "需求澄清", "status": "active"},
            {"id": "strategy", "name": "策略制定", "status": "pending"},
            {"id": "cases", "name": "用例编写", "status": "pending"},
            {"id": "delivery", "name": "文档交付", "status": "pending"},
        ]
        state["current_stage_id"] = "clarify"
        return state
    
    def test_returns_none_when_no_plan(self):
        """无 plan 时返回 None"""
        state = get_initial_state()
        # 初始 state 现在就是空 plan
        
        result = get_progress_info(state)
        
        assert result is None
        
    def test_empty_plan_returns_none(self):
        """空 plan 列表时返回 None"""
        state = get_initial_state()
        state["plan"] = []
        
        result = get_progress_info(state)
        
        assert result is None
        
    def test_with_plan_shows_progress(self, base_state):
        """有 plan 时应显示进度"""
        result = get_progress_info(base_state)
        
        assert result is not None
        assert result["currentStageIndex"] == 0
        assert result["stages"][0]["status"] == "active"
        assert result["stages"][1]["status"] == "pending"
        assert result["stages"][2]["status"] == "pending"
        assert result["stages"][3]["status"] == "pending"
    
    def test_second_stage_active(self, base_state):
        """第二阶段 active 时，第一阶段为 completed"""
        base_state["current_stage_id"] = "strategy"
        
        result = get_progress_info(base_state)
        
        assert result["currentStageIndex"] == 1
        assert result["stages"][0]["status"] == "completed"
        assert result["stages"][1]["status"] == "active"
        assert result["stages"][2]["status"] == "pending"
        assert result["stages"][3]["status"] == "pending"
    
    def test_third_stage_active(self, base_state):
        """第三阶段 active 时，前两阶段为 completed"""
        base_state["current_stage_id"] = "cases"
        
        result = get_progress_info(base_state)
        
        assert result["currentStageIndex"] == 2
        assert result["stages"][0]["status"] == "completed"
        assert result["stages"][1]["status"] == "completed"
        assert result["stages"][2]["status"] == "active"
        assert result["stages"][3]["status"] == "pending"
    
    def test_final_stage_active(self, base_state):
        """最终阶段 active 时，所有前置阶段为 completed"""
        base_state["current_stage_id"] = "delivery"
        
        result = get_progress_info(base_state)
        
        assert result["currentStageIndex"] == 3
        assert result["stages"][0]["status"] == "completed"
        assert result["stages"][1]["status"] == "completed"
        assert result["stages"][2]["status"] == "completed"
        assert result["stages"][3]["status"] == "active"
    
    def test_current_task_name_matches_stage(self, base_state):
        """currentTask 应包含当前阶段名称"""
        result = get_progress_info(base_state)
        
        assert "需求澄清" in result["currentTask"]
        
        base_state["current_stage_id"] = "strategy"
        result = get_progress_info(base_state)
        assert "策略制定" in result["currentTask"]
    
    def test_stages_preserve_original_names(self, base_state):
        """阶段名称应保持原始值"""
        result = get_progress_info(base_state)
        
        stage_names = [s["name"] for s in result["stages"]]
        assert stage_names == ["需求澄清", "策略制定", "用例编写", "文档交付"]
    
    def test_unknown_stage_id_defaults_to_first(self, base_state):
        """未知的 stage_id 应默认 index 为 0"""
        base_state["current_stage_id"] = "unknown_stage"
        
        result = get_progress_info(base_state)
        
        # 未找到匹配时 index 保持 0
        assert result["currentStageIndex"] == 0

