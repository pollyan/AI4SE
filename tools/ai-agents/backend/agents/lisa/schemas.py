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


class ArtifactType(str):
    """Artifact Key Constants for validation"""
    TEST_DESIGN_REQUIREMENTS = "test_design_requirements"
    TEST_DESIGN_STRATEGY = "test_design_strategy"
    TEST_DESIGN_CASES = "test_design_cases"
    TEST_DESIGN_FINAL = "test_design_final"
    REQ_REVIEW_RECORD = "req_review_record"
    REQ_REVIEW_RISK = "req_review_risk"
    REQ_REVIEW_REPORT = "req_review_report"


class UpdateArtifact(BaseModel):
    """
    更新工作流产出物。
    
    当需要保存或更新文档内容时调用此工具。
    严禁在普通对话中直接输出 Markdown 代码块，必须通过此工具提交。
    """
    
    key: Literal[
        "test_design_requirements",
        "test_design_strategy",
        "test_design_cases",
        "test_design_final",
        "req_review_record",
        "req_review_risk",
        "req_review_report"
    ] = Field(description="产出物的唯一标识符 (ID)")
    
    markdown_body: str = Field(description="完整的文档内容 (Markdown 格式)")
    
    metadata: Optional[dict] = Field(
        default=None, 
        description="可选的元数据，如 risk_level, status 等"
    )


class ReasoningResponse(BaseModel):
    """
    ReasoningNode 的结构化输出。
    包含对话思考和进度，不包含产出物内容（通过工具调用处理）。
    """
    thought: str = Field(description="思考过程、对用户的回复或澄清问题")
    
    progress_step: Optional[str] = Field(
        default=None,
        description="当前的具体步骤名称，例如：'正在分析需求', '生成测试用例'。用于更新前端进度条。"
    )
    
    should_update_artifact: bool = Field(
        default=False, 
        description="是否需要更新产出物。仅当完成了实质性分析且有新内容需要写入文档时返回 True"
    )


class WorkflowResponse(BaseModel):
    """
    [Legacy] 工作流响应结构。
    保留以兼容现有代码，未来将由 ReasoningResponse 替代。
    """
    thought: str = Field(description="思考过程、对用户的回复或澄清问题")
    
    progress_step: Optional[str] = Field(
        default=None,
        description="当前的具体步骤名称，例如：'正在分析需求', '生成测试用例'。用于更新前端进度条。"
    )
