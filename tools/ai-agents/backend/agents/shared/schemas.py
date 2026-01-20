"""
智能体结构化输出 Schema 定义

使用 Pydantic 定义 LLM 输出的结构化格式。
通过 PydanticOutputParser 引导 LLM 输出符合 Schema 的 JSON。

Lisa 和 Alex 智能体共用此模块。
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union


class WorkflowSubTask(BaseModel):
    """阶段内的细分任务"""
    id: str = Field(description="任务唯一标识")
    name: str = Field(description="任务显示名称")
    status: Literal["pending", "active", "completed", "warning"] = Field(
        default="pending",
        description="任务状态"
    )


class WorkflowStage(BaseModel):
    """工作流阶段"""
    id: str = Field(description="阶段唯一标识，如 'clarify', 'strategy', 'cases'")
    name: str = Field(description="阶段显示名称，如 '需求澄清', '策略制定'")
    status: Literal["pending", "active", "completed"] = Field(
        description="阶段状态: pending=待开始, active=进行中, completed=已完成"
    )
    sub_tasks: List[WorkflowSubTask] = Field(
        default_factory=list,
        description="阶段下的细分任务列表"
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


