"""
智能体结构化输出 Schema 定义

使用 Pydantic 定义 LLM 输出的结构化格式。
通过 PydanticOutputParser 引导 LLM 输出符合 Schema 的 JSON。

Lisa 和 Alex 智能体共用此模块。
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class WorkflowStage(BaseModel):
    """工作流阶段"""
    id: str = Field(description="阶段唯一标识，如 'clarify', 'strategy', 'cases'")
    name: str = Field(description="阶段显示名称，如 '需求澄清', '策略制定'")
    status: Literal["pending", "active", "completed"] = Field(
        description="阶段状态: pending=待开始, active=进行中, completed=已完成"
    )


class Artifact(BaseModel):
    """产出物（模板+内容合并）"""
    stage_id: str = Field(description="所属阶段 ID")
    key: str = Field(description="产出物唯一键，用于存储和检索")
    name: str = Field(description="产出物显示名称，如 '测试策略文档'")
    content: Optional[str] = Field(
        default=None,
        description="产出物内容（Markdown 格式），未生成时为 null"
    )


class LisaStructuredOutput(BaseModel):
    """Lisa 智能体结构化输出"""

    plan: List[WorkflowStage] = Field(
        description="工作流阶段计划，包含各阶段的 id、name 和 status"
    )

    current_stage_id: str = Field(
        description="当前活跃阶段的 ID"
    )

    artifacts: List[Artifact] = Field(
        default_factory=list,
        description="产出物列表，content 为 null 表示尚未生成"
    )

    # message 字段已移除，回复内容直接作为 LLM 响应的前半部分


class AlexStructuredOutput(BaseModel):
    """Alex 智能体结构化输出"""

    plan: List[WorkflowStage] = Field(
        description="工作流阶段计划，包含各阶段的 id、name 和 status"
    )

    current_stage_id: str = Field(
        description="当前活跃阶段的 ID"
    )

    artifacts: List[Artifact] = Field(
        default_factory=list,
        description="产出物列表，content 为 null 表示尚未生成"
    )

    # message 字段已移除，回复内容直接作为 LLM 响应的前半部分


def to_progress_info(output: LisaStructuredOutput | AlexStructuredOutput) -> dict:
    """
    将结构化输出转换为前端 ProgressInfo 格式

    Args:
        output: LLM 结构化输出对象

    Returns:
        前端兼容的 ProgressInfo 字典
    """
    current_index = next(
        (i for i, stage in enumerate(output.plan) if stage.id == output.current_stage_id),
        0
    )

    artifacts_dict = {
        a.key: a.content
        for a in output.artifacts
        if a.content is not None
    }

    artifact_progress = {
        "template": [
            {"stageId": a.stage_id, "artifactKey": a.key, "name": a.name}
            for a in output.artifacts
        ],
        "completed": [a.key for a in output.artifacts if a.content],
        "generating": next(
            (a.key for a in output.artifacts
             if a.stage_id == output.current_stage_id and not a.content),
            None
        )
    }

    current_task = "处理中..."
    if 0 <= current_index < len(output.plan):
        current_task = f"正在{output.plan[current_index].name}..."

    return {
        "stages": [s.model_dump() for s in output.plan],
        "currentStageIndex": current_index,
        "currentTask": current_task,
        "artifactProgress": artifact_progress,
        "artifacts": artifacts_dict,
    }
