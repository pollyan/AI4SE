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
    """设置工作流计划及各阶段产出物模板。在确定用户意图后立即调用。
    
    Args:
        stages: 阶段列表，每个阶段包含:
            - id: 阶段唯一 ID (必需)
            - name: 阶段显示名称 (必需)
            - artifact_key: 该阶段产出物的键 (可选)
            - artifact_name: 该阶段产出物的名称 (可选)
            
    示例 (测试用例设计工作流):
        set_plan([
            {"id": "clarify", "name": "需求澄清", "artifact_key": "test_design_requirements", "artifact_name": "需求分析文档"},
            {"id": "strategy", "name": "策略制定", "artifact_key": "test_design_strategy", "artifact_name": "测试策略蓝图"},
            {"id": "cases", "name": "用例设计", "artifact_key": "test_design_cases", "artifact_name": "测试用例集"},
            {"id": "delivery", "name": "文档交付", "artifact_key": "test_design_final", "artifact_name": "测试设计文档"}
        ])
    
    示例 (需求评审工作流):
        set_plan([
            {"id": "understand", "name": "业务对齐"},
            {"id": "review", "name": "深度评审", "artifact_key": "requirement_review_report", "artifact_name": "需求评审报告"}
        ])
    
    Returns:
        确认消息
    """
    stage_count = len(stages) if stages else 0
    artifact_count = sum(1 for s in stages if s.get("artifact_key")) if stages else 0
    return f"已设置 {stage_count} 个阶段的工作流计划，包含 {artifact_count} 个产出物模板"


def update_stage(stage_id: str, status: str) -> str:
    """更新阶段状态。用户确认阶段产出物后，调用此工具将阶段设为 'completed'。
    
    重要说明:
    - 第一个阶段在 set_plan 时自动设为 'active'，无需手动调用
    - 调用 'completed' 后，系统会自动将下一个阶段设为 'active'
    - 因此通常只需要调用 update_stage(stage_id, 'completed')
    
    Args:
        stage_id: 要更新的阶段 ID
        status: 新状态，通常为 'completed'
        
    示例:
        update_stage("clarify", "completed")  # 需求澄清阶段完成
    
    Returns:
        确认消息
    """
    return f"阶段 '{stage_id}' 状态已更新为 '{status}'"


def save_artifact(key: str, content: str) -> str:
    """保存产出物文档。在用户确认产出物内容后调用。
    
    重要规则:
    - content 必须是完整的 Markdown 文档，不是摘要
    - 包含所有与用户达成共识的内容
    - 文档结构清晰，便于后续阅读
    
    Args:
        key: 产出物唯一键，必须与 set_plan 中定义的 artifact_key 匹配
        content: 产出物完整内容，Markdown 格式
        
    示例:
        save_artifact(
            key="test_design_requirements",
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
