"""
意图识别 Pydantic 模型 - 用于 Tool Calling
"""

from typing import Literal
try:
    from pydantic.v1 import BaseModel, Field
except ImportError:
    from pydantic import BaseModel, Field


class DetectedIntent(BaseModel):
    """
    当且仅当用户的测试意图已经非常清晰，或者用户明确做出了选择时，
    LLM 调用此工具来锁定意图并进入下一阶段。
    
    使用示例：
    - 用户说"我要写测试用例" → intent_code="A"
    - 用户说"帮我分析线上Bug" → intent_code="C"
    - 用户直接输入"A" → intent_code="A"
    """
    intent_code: Literal["A", "B", "C", "D", "E", "F"] = Field(
        description="匹配到的工作流代码 (A-F)"
    )
    workflow_name: str = Field(
        description="工作流的中文名称，如：新需求/功能测试设计"
    )
    confidence: float = Field(
        description="置信度 (0.0-1.0)，表示对此判断的信心",
        ge=0.0,
        le=1.0
    )
    transition_message: str = Field(
        description="一句简短、自然的过渡语，告诉用户我们即将开始该工作流。要像真人专家说话，不要机械化。"
    )
