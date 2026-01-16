from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional


class IntentResult(BaseModel):
    intent: Optional[Literal["START_TEST_DESIGN", "START_REQUIREMENT_REVIEW"]] = Field(
        default=None,
        description="识别出的意图类型，无明确意图时为 null"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="置信度 0.0-1.0"
    )
    entities: list[str] = Field(
        default_factory=list,
        description="提取的实体（功能模块、页面名称等）"
    )
    reason: str = Field(
        description="简短分类理由"
    )
    clarification: Optional[str] = Field(
        default=None,
        description="当 confidence < 0.9 时的确认问题"
    )
    
    @field_validator('intent', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """将空字符串转换为 None，兼容 LLM 结构化输出"""
        if v == '':
            return None
        return v
