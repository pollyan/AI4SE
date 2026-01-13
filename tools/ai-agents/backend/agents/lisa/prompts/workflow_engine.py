"""
工作流引擎规范 (Workflow Engine Specs)

提供进度同步机制的 Prompt 生成函数。
采用"全量状态快照"模式：每次回复都输出完整的 Plan JSON。
"""

import json
from typing import List, Dict
from .shared import PLAN_SYNC_MECHANISM_PROMPT


def get_plan_sync_instruction(default_stages: List[Dict]) -> str:
    """
    生成进度同步机制的 Prompt。
    
    采用"全量快照"模式：每次回复都输出完整的 Plan JSON，
    包含所有阶段的当前状态。
    
    Args:
        default_stages: 默认的阶段列表，例如:
            [{"id": "clarify", "name": "需求澄清"}, {"id": "strategy", "name": "策略制定"}]
    
    Returns:
        格式化好的 Prompt 片段，可直接嵌入 System Prompt
    """
    # 构建示例：将第一个阶段设为 active，其他 pending
    example_stages = []
    for i, stage in enumerate(default_stages):
        s = stage.copy()
        s["status"] = "active" if i == 0 else "pending"
        example_stages.append(s)
    
    # 构建符合 LisaStructuredOutput Schema 的完整示例对象
    example_obj = {
        "plan": example_stages,
        "current_stage_id": example_stages[0]["id"] if example_stages else "",
        "artifacts": []
    }
    
    example_json = json.dumps(example_obj, ensure_ascii=False, indent=2)

    return PLAN_SYNC_MECHANISM_PROMPT.format(example_json=example_json)
