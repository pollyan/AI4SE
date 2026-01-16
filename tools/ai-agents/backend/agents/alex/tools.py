"""
Alex 智能体 Tools 定义

使用 ADK FunctionTool 模式，通过 Tool Calling 更新工作流状态。
LLM 在合适的时机调用这些 Tools，后端捕获事件并更新状态。

Tools:
- set_plan: 设置工作流计划及产出物模板
- update_stage: 更新阶段状态
- save_artifact: 保存产出物内容
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 参数 Schema 定义
# ═══════════════════════════════════════════════════════════════════════════════

class StageDefinition(BaseModel):
    """阶段定义"""
    id: str = Field(description="阶段唯一 ID，如 'clarify', 'strategy', 'cases', 'delivery'")
    name: str = Field(description="阶段显示名称，如 '需求澄清', '策略制定'")
    artifact_key: Optional[str] = Field(
        default=None,
        description="该阶段产出物的键，如 'req_doc'。无产出物时为 null"
    )
    artifact_name: Optional[str] = Field(
        default=None,
        description="该阶段产出物的名称，如 '需求分析文档'。无产出物时为 null"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 函数定义
# ═══════════════════════════════════════════════════════════════════════════════

def set_plan(stages: List[dict]) -> str:
    """设置工作流计划及各阶段产出物模板。在确定用户意图后调用。
    
    Args:
        stages: 阶段列表，每个阶段包含:
            - id: 阶段唯一 ID (必需)
            - name: 阶段显示名称 (必需)
            - artifact_key: 该阶段产出物的键 (可选)
            - artifact_name: 该阶段产出物的名称 (可选)
            
    示例:
        set_plan([
            {"id": "clarify", "name": "需求澄清", "artifact_key": "req_doc", "artifact_name": "需求分析文档"},
            {"id": "strategy", "name": "策略制定", "artifact_key": "strategy_doc", "artifact_name": "测试策略蓝图"},
            {"id": "cases", "name": "用例设计", "artifact_key": "test_cases", "artifact_name": "测试用例集"},
            {"id": "delivery", "name": "文档交付", "artifact_key": "final_doc", "artifact_name": "最终交付文档"}
        ])
    
    Returns:
        确认消息
    """
    stage_count = len(stages) if stages else 0
    artifact_count = sum(1 for s in stages if s.get("artifact_key")) if stages else 0
    return f"已设置 {stage_count} 个阶段的工作流计划，包含 {artifact_count} 个产出物模板"


def update_stage(stage_id: str, status: str) -> str:
    """更新阶段状态。开始新阶段时设为 'active'，阶段完成时设为 'completed'。
    
    Args:
        stage_id: 要更新的阶段 ID
        status: 新状态，必须是 'active' 或 'completed'
        
    示例:
        update_stage("clarify", "completed")  # 需求澄清阶段完成
        update_stage("strategy", "active")    # 开始策略制定阶段
    
    Returns:
        确认消息
    """
    return f"阶段 '{stage_id}' 状态已更新为 '{status}'"


def save_artifact(key: str, content: str) -> str:
    """保存产出物文档。在生成完整的文档内容后调用。
    
    Args:
        key: 产出物唯一键，必须与 set_plan 中定义的 artifact_key 匹配
        content: 产出物完整内容，Markdown 格式
        
    示例:
        save_artifact(
            key="req_doc",
            content="# 需求分析文档\\n\\n## 1. 功能概述\\n..."
        )
    
    Returns:
        确认消息
    """
    content_length = len(content) if content else 0
    return f"产出物 '{key}' 已保存 ({content_length} 字符)"


# ═══════════════════════════════════════════════════════════════════════════════
# Tools 列表（供 Agent 使用）
# ═══════════════════════════════════════════════════════════════════════════════

ALEX_TOOLS = [
    set_plan,
    update_stage,
    save_artifact,
]
