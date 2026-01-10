"""
Lisa 进度计算模块

根据 LisaState 生成两级进度信息（阶段 + 子任务）。
"""

from typing import Optional
from .state import LisaState, ArtifactKeys


# 阶段对应的产出物 Key (用于兜底逻辑)
STAGE_ARTIFACT_MAP = {
    "clarify": ArtifactKeys.TEST_DESIGN_REQUIREMENTS,
    "strategy": ArtifactKeys.TEST_DESIGN_STRATEGY,
    "cases": ArtifactKeys.TEST_DESIGN_CASES,
    "delivery": ArtifactKeys.TEST_DESIGN_FINAL,
}


def get_progress_info(state: LisaState) -> Optional[dict]:
    """
    根据 LisaState 生成进度信息
    
    Args:
        state: Lisa 状态
        
    Returns:
        进度信息字典，若无 plan 则返回 None
    """
    plan = state.get("plan")
    
    # 只要有 plan 就显示进度条，不限制特定 workflow
    if not plan:
        return None
    
    # 获取当前活跃阶段 ID (唯一来源)
    current_stage_id = state.get("current_stage_id")
    
    # 找到当前阶段的索引
    current_index = 0
    for i, step in enumerate(plan):
        if step.get("id") == current_stage_id:
            current_index = i
            break
    
    # 构建阶段列表，动态计算 status
    stages = []
    for i, step in enumerate(plan):
        stage_id = step.get("id")
        
        # 根据 current_stage_id 动态计算状态
        if i < current_index:
            status = "completed"
        elif i == current_index:
            status = "active"
        else:
            status = "pending"
        
        stages.append({
            "id": stage_id,
            "name": step.get("name"),
            "status": status,
            "description": step.get("description", "")
        })
    
    # 获取当前子任务描述
    current_task_name = "处理中..."
    if 0 <= current_index < len(stages):
        stage = stages[current_index]
        current_task_name = f"正在{stage['name']}..."
    
    return {
        "stages": stages,
        "currentStageIndex": current_index,
        "currentTask": current_task_name,
    }

