"""
共享进度计算模块

根据智能体 State 生成两级进度信息（阶段 + 子任务）。
Lisa 和 Alex 智能体共用此模块。
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_progress_info(state: Dict[str, Any]) -> Optional[dict]:
    """
    根据智能体状态生成进度信息
    
    此函数通用于 Lisa 和 Alex，只依赖 state 中的以下字段：
    - plan: List[Dict] - 阶段计划列表
    - current_stage_id: str - 当前活跃阶段 ID
    - artifact_templates: List[Dict] - 产出物模板列表
    - artifacts: Dict[str, str] - 已生成的产出物
    
    Args:
        state: 智能体状态字典 (LisaState 或 AlexState)
        
    Returns:
        进度信息字典，若无 plan 则返回 None
        格式: {
            "stages": [{id, name, status, description}...],
            "currentStageIndex": int,
            "currentTask": str,
            "artifactProgress": {
                "template": [{stageId, artifactKey, name}...],
                "completed": [artifact_key...],
                "generating": artifact_key | null
            }
        }
    """
    plan = state.get("plan")
    
    # 只有存在 plan 才显示进度条
    if not plan or len(plan) == 0:
        return None
    
    # 获取当前活跃阶段 ID
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
    
    # 构建产出物进度信息
    artifact_templates = state.get("artifact_templates", [])
    artifacts = state.get("artifacts", {})
    
    # 转换模板格式为前端格式
    template_list = []
    for tmpl in artifact_templates:
        template_list.append({
            "stageId": tmpl.get("stage_id"),
            "artifactKey": tmpl.get("artifact_key"),
            "name": tmpl.get("name"),
        })
    
    # 计算已完成的产出物
    completed_keys = list(artifacts.keys())
    
    # 计算正在生成的产出物
    # 规则: 当前阶段 active 且该阶段的产出物尚未生成
    generating_key = None
    if current_stage_id:
        for tmpl in artifact_templates:
            if tmpl.get("stage_id") == current_stage_id:
                artifact_key = tmpl.get("artifact_key")
                if artifact_key and artifact_key not in artifacts:
                    generating_key = artifact_key
                break
    
    artifact_progress = {
        "template": template_list,
        "completed": completed_keys,
        "generating": generating_key,
    }
    
    return {
        "stages": stages,
        "currentStageIndex": current_index,
        "currentTask": current_task_name,
        "artifactProgress": artifact_progress,
        "artifacts": artifacts,
    }
