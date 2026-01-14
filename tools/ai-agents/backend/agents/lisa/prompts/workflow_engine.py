"""
工作流引擎规范 (Workflow Engine Specs)

提供进度同步机制的 Prompt 生成函数。
"""

import json
from typing import List, Dict
from .shared import STRUCTURED_OUTPUT_PROMPT


def get_plan_sync_instruction(default_stages: List[Dict]) -> str:
    """生成进度同步 Prompt（结构化输出协议 + 阶段示例）"""
    example_stages = [
        {**s, "status": "active" if i == 0 else "pending"}
        for i, s in enumerate(default_stages)
    ]
    
    example_obj = {
        "plan": example_stages,
        "current_stage_id": example_stages[0]["id"] if example_stages else "",
        "artifacts": []
    }
    
    example_json = json.dumps(example_obj, ensure_ascii=False, indent=2)
    
    return f"""{STRUCTURED_OUTPUT_PROMPT}

**阶段初始化示例**:
```json
{example_json}
```

**重要提醒**：
- 上面示例中 `artifacts` 为空是因为刚开始，后续每次回复都要填充 artifacts 的 content
- 用户每回答一个问题，你就要更新 artifacts 中对应产出物的 content（累积完整内容）"""
