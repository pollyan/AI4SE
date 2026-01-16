"""
Alex 智能体 Tools 定义

使用 ADK FunctionTool 模式，通过 Tool Calling 更新工作流状态。
后端捕获事件并更新状态。

Tools:
- update_progress: 全量更新工作流进度（阶段、状态、当前任务）
- update_artifact: 按章节增量更新产出物内容
"""

from typing import List, Dict, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 函数定义
# ═══════════════════════════════════════════════════════════════════════════════

def update_progress(
    stages: List[dict],
    current_stage_id: str,
    current_task: str
) -> str:
    """全量更新工作流进度。每一次回复用户时都必须调用此工具来同步最新状态。
    
    Args:
        stages: 全量阶段列表。每个阶段包含:
            - id: 阶段唯一 ID (必需)
            - name: 阶段显示名称 (必需)
            - status: 状态 'pending' | 'active' | 'completed' (必需)
            - artifact_key: 产出物键 (可选)
            - artifact_name: 产出物名称 (可选)
        current_stage_id: 当前活跃的阶段 ID
        current_task: 当前正在进行的具体任务描述，如 "正在分析需求文档..." 或 "正在生成测试用例..."
    
    Returns:
        确认消息
    """
    stage_count = len(stages) if stages else 0
    return f"进度已更新: {stage_count} 个阶段, 当前阶段 '{current_stage_id}', 任务 '{current_task}'"


def update_artifact(
    artifact_key: str,
    section_id: str,
    content: str
) -> str:
    """按章节增量更新产出物内容。
    
    重要：
    - 此工具为【章节级全量替换】模式。
    - 每次调用会用 content 完全替换指定章节的内容。
    - 如果需要保留历史内容，请在 content 中包含完整的章节内容。
    
    Args:
        artifact_key: 产出物唯一标识，如 "test_design_requirements"
        section_id: 要更新的章节 ID，如 "overview", "questions" 等
        content: 该章节的完整 Markdown 内容
        
    Returns:
        确认消息
    """
    return f"产出物 '{artifact_key}' 的章节 '{section_id}' 已更新"


# ═══════════════════════════════════════════════════════════════════════════════
# Tools 列表（供 Agent 使用）
# ═══════════════════════════════════════════════════════════════════════════════

ALEX_TOOLS = [
    update_progress,
    update_artifact,
]
