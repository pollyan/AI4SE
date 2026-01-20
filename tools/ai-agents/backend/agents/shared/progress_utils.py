"""
共享进度工具模块

提供 JSON 解析、响应清理等通用功能。
Lisa 和 Alex 智能体共用此模块。

采用"全量状态快照"模式：LLM 每次回复都输出完整的 Plan JSON（含 status）。

### 输出格式
LLM 在回复末尾输出 JSON 代码块 (```json ... ```)
"""

import re
import json
import logging
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# JSON 代码块解析
# ═══════════════════════════════════════════════════════════════════════════════

JSON_BLOCK_PATTERN = re.compile(
    r'```json\s*([\s\S]*?)\s*```',
    re.IGNORECASE
)




# ═══════════════════════════════════════════════════════════════════════════════
# 响应文本清理
# ═══════════════════════════════════════════════════════════════════════════════

def clean_response_text(text: str) -> str:
    """
    移除响应文本中的 JSON 代码块
    
    Args:
        text: 原始响应文本
        
    Returns:
        清理后的文本
    """
    result = JSON_BLOCK_PATTERN.sub('', text)
    
    # [NEW] 移除产出物 Markdown 块
    ARTIFACT_BLOCK_PATTERN = re.compile(r'```(?:markdown)?\s*\n#.*?(?:\n[\s\S]*?)?```', re.IGNORECASE | re.DOTALL)
    result = ARTIFACT_BLOCK_PATTERN.sub('', result)
    
    # 清理可能残留的多余空行
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()




def get_current_stage_id(plan: List[Dict]) -> Optional[str]:
    """
    从 Plan 中获取当前活跃阶段的 ID
    
    Args:
        plan: 计划列表
        
    Returns:
        活跃阶段的 ID，若无则返回 None
    """
    for stage in plan:
        if stage.get("status") == "active":
            return stage.get("id")
    return None
