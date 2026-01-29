"""
Lisa Agent Artifact 数据模型

定义四阶段工作流的结构化产出物 Schema。
用于前后端契约、LLM 输出校验和增量 Diff。

设计文档: docs/plans/2026-01-22-test-agent-redesign.md
"""

from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# 通用类型定义
# ═══════════════════════════════════════════════════════════════════════════════

ArtifactPhase = Literal["requirement", "design", "cases", "delivery"]
Priority = Literal["P0", "P1", "P2", "P3"]
NodeType = Literal["group", "point"]
AssumptionStatus = Literal["pending", "assumed", "confirmed"]
RuleSource = Literal["user", "default"]


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: 需求澄清 (Requirement)
# ═══════════════════════════════════════════════════════════════════════════════


class RuleItem(BaseModel):
    """业务规则项"""

    id: str = Field(description="规则唯一标识，如 R1, R2")
    desc: str = Field(description="规则描述")
    source: RuleSource = Field(description="来源：user=用户提供, default=系统默认")


class AssumptionItem(BaseModel):
    """待确认/假设项"""

    id: str = Field(description="问题唯一标识，如 Q1, Q2")
    question: str = Field(description="问题描述")
    status: AssumptionStatus = Field(
        description="状态：pending/assumed/confirmed"
    )
    note: Optional[str] = Field(default=None, description="备注或假设值")


class RequirementDoc(BaseModel):
    """Phase 1 产出物：需求分析文档"""

    scope: List[str] = Field(description="被测对象范围列表")
    scope_mermaid: Optional[str] = Field(
        default=None, description="需求全景图 Mermaid Mindmap 代码"
    )
    flow_mermaid: str = Field(description="业务流程 Mermaid 代码")
    rules: List[RuleItem] = Field(default_factory=list, description="核心规则列表")
    assumptions: List[AssumptionItem] = Field(
        default_factory=list, description="待确认/假设列表"
    )
    nfr_markdown: Optional[str] = Field(
        default=None, description="非功能需求 Markdown"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: 策略与设计 (Design)
# ═══════════════════════════════════════════════════════════════════════════════


class DesignNode(BaseModel):
    """测试点树节点"""

    id: str = Field(description="节点唯一标识，如 GRP-001, TP-001")
    label: str = Field(description="节点标签/名称")
    type: NodeType = Field(description="节点类型：group=分组, point=测试点")
    method: Optional[str] = Field(
        default=None, description="测试方法论标签，如 边界值、等价类"
    )
    priority: Optional[Priority] = Field(default=None, description="优先级")
    is_new: Optional[bool] = Field(
        default=None, description="是否为新增节点（用于 Diff 高亮）"
    )
    children: Optional[List["DesignNode"]] = Field(
        default=None, description="子节点列表"
    )


class DesignDoc(BaseModel):
    """Phase 2 产出物：测试策略与设计"""

    strategy_markdown: str = Field(description="测试策略 Markdown 文档")
    test_points: DesignNode = Field(description="测试点树根节点")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: 用例生成 (Cases)
# ═══════════════════════════════════════════════════════════════════════════════


class CaseStep(BaseModel):
    """测试步骤"""

    action: str = Field(description="操作描述")
    expect: str = Field(description="预期结果")


class CaseItem(BaseModel):
    """单个测试用例"""

    id: str = Field(description="用例 ID，对应 DesignNode ID")
    title: str = Field(description="用例标题")
    precondition: Optional[str] = Field(default=None, description="前置条件")
    steps: List[CaseStep] = Field(default_factory=list, description="执行步骤列表")
    tags: List[str] = Field(
        default_factory=list, description="标签，如 Smoke, Regression"
    )
    script: Optional[str] = Field(default=None, description="自动化脚本片段")


class CaseDoc(BaseModel):
    """Phase 3 产出物：测试用例集"""

    cases: List[CaseItem] = Field(default_factory=list, description="用例列表")
    stats: Optional[dict] = Field(
        default=None, description="统计信息，如 total, p0_count"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: 交付 (Delivery) - 组装前三阶段内容
# ═══════════════════════════════════════════════════════════════════════════════


class DeliveryDoc(BaseModel):
    """Phase 4 产出物：最终交付文档"""

    title: str = Field(description="文档标题")
    version: str = Field(description="版本号")
    requirement: RequirementDoc = Field(description="需求文档")
    design: DesignDoc = Field(description="设计文档")
    cases: CaseDoc = Field(description="用例文档")
    summary_markdown: Optional[str] = Field(
        default=None, description="概览摘要 Markdown"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 通用 Artifact 信封
# ═══════════════════════════════════════════════════════════════════════════════


class AgentArtifact(BaseModel):
    """Agent 产出物通用信封"""

    phase: ArtifactPhase = Field(description="当前阶段")
    version: str = Field(description="版本号")
    content: Union[RequirementDoc, DesignDoc, CaseDoc, DeliveryDoc] = Field(
        description="阶段对应的内容"
    )


# 支持 DesignNode 的自引用
DesignNode.model_rebuild()
