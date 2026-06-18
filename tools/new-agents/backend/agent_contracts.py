import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


WORKFLOW_STAGES: dict[str, list[str]] = {
    "TEST_DESIGN": ["CLARIFY", "STRATEGY", "CASES", "DELIVERY"],
    "REQ_REVIEW": ["REVIEW", "REPORT"],
    "INCIDENT_REVIEW": ["TIMELINE", "ROOT_CAUSE", "IMPROVEMENT"],
    "IDEA_BRAINSTORM": ["DEFINE", "DIVERGE", "CONVERGE", "CONCEPT"],
    "VALUE_DISCOVERY": ["ELEVATOR", "PERSONA", "JOURNEY", "BLUEPRINT"],
}

REQUIRED_ARTIFACT_HEADINGS: dict[tuple[str, str], list[str]] = {
    ("TEST_DESIGN", "CLARIFY"): [
        "# 需求分析文档",
        "## 1. 被测系统与边界",
        "## 2. 系统交互与核心链路",
        "## 3. 待澄清与阻断性问题",
        "## 4. 隐式需求与非功能性考量",
    ],
    ("TEST_DESIGN", "STRATEGY"): [
        "# 测试策略蓝图",
        "## 1. 质量目标",
        "## 2. 风险分析",
        "### 2.1 风险矩阵",
        "### 2.2 风险明细",
        "## 3. 测试技术选型",
        "## 4. 测试分层策略",
        "### 4.1 测试金字塔",
        "### 4.2 分层明细",
        "## 5. 测试点拓扑",
    ],
    ("TEST_DESIGN", "CASES"): [
        "# 测试用例集",
        "## 1. 用例统计",
        "## 2. 用例清单",
        "## 3. 测试点覆盖追溯",
    ],
    ("TEST_DESIGN", "DELIVERY"): [
        "# 测试设计文档",
        "## 文档信息",
        "## 第一部分：需求分析",
        "## 第二部分：测试策略",
        "## 第三部分：测试用例",
        "## 附录：验收标准",
    ],
    ("REQ_REVIEW", "REVIEW"): [
        "# 需求评审问题清单",
        "## 评审概要",
        "## 问题统计",
    ],
    ("REQ_REVIEW", "REPORT"): [
        "# 需求评审报告",
        "## 评审结论",
        "### 判定标准",
        "## 评审信息",
        "## 问题统计",
        "## 待确认问题清单",
        "### P0 阻塞性问题",
        "### P1 重要问题",
        "### P2 优化建议",
        "## 评审意见签署",
    ],
    ("INCIDENT_REVIEW", "TIMELINE"): [
        "# 故障复盘报告",
        "## 1. 事件概要",
        "## 2. 事件时间线",
        "## 3. 事实摘要",
        "## 4. 参与人员",
        "## 5. 待补充信息",
    ],
    ("INCIDENT_REVIEW", "ROOT_CAUSE"): [
        "# 故障复盘报告",
        "## 6. 根因分析",
        "### 6.1 5-Why 分析链",
        "### 6.2 原因鱼骨图",
        "### 6.3 根因结论",
    ],
    ("INCIDENT_REVIEW", "IMPROVEMENT"): [
        "# 故障复盘报告",
        "## 报告信息",
        "## 第一部分：事件还原",
        "## 第二部分：根因分析",
        "## 第三部分：改进措施",
        "### 7. 改进措施",
        "#### 7.1 改进优先级分布",
        "#### 7.2 改进行动清单",
        "### 8. 防复发检查清单",
        "### 9. 经验教训",
        "## 签署确认",
    ],
    ("IDEA_BRAINSTORM", "DEFINE"): [
        "# 问题域分析",
        "## 问题假设陈述",
        "## 目标用户画像",
        "## 问题域全景",
        "## 问题-用户-场景匹配",
        "## 约束与边界",
        "## 反向验证（风险思考）",
    ],
    ("IDEA_BRAINSTORM", "DIVERGE"): [
        "# 创意发散",
        "## 发散全景图",
        "## 创意卡片库",
    ],
    ("IDEA_BRAINSTORM", "CONVERGE"): [
        "# 收敛聚焦",
        "## 决策矩阵",
        "## ICE 评估表",
        "## 整合演进路径（如果触发合并）",
    ],
    ("IDEA_BRAINSTORM", "CONCEPT"): [
        "# 产品概念简报",
        "## 定位声明",
        "## Lean Canvas 产品画布",
        "## MVP 功能分布",
        "## 核心增长漏斗",
        "## Pre-mortem 风险分析",
        "## 下一步行动",
    ],
    ("VALUE_DISCOVERY", "ELEVATOR"): [
        "# 价值定位分析",
        "## 产品核心定位",
        "## 目标用户概览",
        "## 独特价值主张",
        "## 商业可行性初判",
        "60 秒电梯演讲",
    ],
    ("VALUE_DISCOVERY", "PERSONA"): [
        "# 用户画像分析",
        "## 主要用户画像",
        "### 画像 1",
        "#### 基础特征",
        "#### 行为特征",
        "#### 需求动机",
        "#### 核心痛点",
        "## 用户优先级排序",
    ],
    ("VALUE_DISCOVERY", "JOURNEY"): [
        "# 用户旅程分析",
        "## 用户旅程地图",
        "## 关键阶段详细分析",
        "## 痛点优先级排序",
        "高优先级痛点",
        "中等优先级痛点",
        "低优先级痛点",
        "## 核心机会点",
        "主要机会点",
        "### 产品切入策略",
    ],
    ("VALUE_DISCOVERY", "BLUEPRINT"): [
        "需求蓝图",
        "## 文档信息",
        "## 1. 产品概述",
        "### 1.1 产品愿景",
        "### 1.2 定位声明",
        "### 1.3 核心价值",
        "## 2. 目标用户（摘要）",
        "## 3. 核心需求",
        "### 功能架构",
        "### P0 需求（核心功能，必须实现）",
        "### P1 需求（重要功能，应该实现）",
        "### P2 需求（增值功能，可以实现）",
        "## 4. 核心流程",
        "### 主流程图",
        "## 5. 成功指标",
        "## 6. MVP 范围与计划",
        "### MVP 包含功能",
        "### 迭代路线",
        "## 7. 风险评估",
    ],
}

REQUIRED_ARTIFACT_H1_KEYWORDS: dict[tuple[str, str], list[str]] = {
    ("VALUE_DISCOVERY", "BLUEPRINT"): ["需求蓝图"],
}


class ContractValidationError(ValueError):
    """Raised when a structured agent output violates workflow rules."""


class ArtifactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["replace", "none"]
    markdown: str | None = None

    @model_validator(mode="after")
    def validate_markdown(self) -> "ArtifactUpdate":
        has_markdown = self.markdown and self.markdown.strip()
        if self.type == "replace" and not has_markdown:
            raise ValueError("artifact markdown cannot be empty")
        if self.type == "none" and has_markdown:
            raise ValueError("none artifact update cannot include markdown")
        return self


class StageAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["request_next_stage"]
    target_stage_id: str = Field(min_length=1)

    @field_validator("target_stage_id")
    @classmethod
    def validate_target_stage_id_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("target_stage_id cannot be blank")
        return value


class AgentTurnOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chat: str = Field(min_length=1)
    artifact_update: ArtifactUpdate
    stage_action: StageAction | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("chat")
    @classmethod
    def validate_chat_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("chat cannot be blank")
        return value

    @field_validator("artifact_update", mode="before")
    @classmethod
    def parse_string_encoded_artifact_update(
        cls,
        value: Any,
    ) -> Any:
        if not isinstance(value, str):
            return value
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "artifact_update must be an object or JSON object string"
            ) from exc
        if not isinstance(decoded, dict):
            raise ValueError(
                "artifact_update must be an object or JSON object string"
            )
        return decoded

    @model_validator(mode="after")
    def validate_chat_artifact_separation(self) -> "AgentTurnOutput":
        if self.artifact_update.type != "replace":
            return self

        artifact_markdown_patterns = [
            r"(?m)^#{1,6}\s+\S",
            r"(?m)^\|?\s*-{3,}\s*\|",
            r"```",
            r"(?m)^\s*sequenceDiagram\b",
            r"(?m)^\s*flowchart\s+",
            r"(?m)^\s*graph\s+",
        ]
        if any(
            re.search(pattern, self.chat)
            for pattern in artifact_markdown_patterns
        ):
            raise ValueError(
                "chat must not contain artifact markdown; put full Markdown "
                "only in artifact_update.markdown"
            )
        return self


def validate_artifact_template(
    output: AgentTurnOutput,
    *,
    workflow_id: str,
    current_stage_id: str,
) -> None:
    stage_key = (workflow_id, current_stage_id)
    required_headings = REQUIRED_ARTIFACT_HEADINGS.get(stage_key)
    required_h1_keywords = REQUIRED_ARTIFACT_H1_KEYWORDS.get(stage_key, [])
    if not required_headings and not required_h1_keywords:
        return

    if output.artifact_update.type != "replace":
        raise ContractValidationError(
            "artifact update is required for "
            f"{workflow_id}/{current_stage_id}"
        )

    markdown = output.artifact_update.markdown or ""
    markdown_outside_code = strip_fenced_code_blocks(markdown)
    markdown_headings = extract_markdown_heading_lines(markdown)
    missing_headings = [
        heading
        for heading in required_headings
        if not has_required_artifact_heading(
            heading,
            markdown_outside_code=markdown_outside_code,
            markdown_headings=markdown_headings,
        )
    ]
    missing_h1_keyword_headings = [
        f"H1 标题包含 {keyword}"
        for keyword in required_h1_keywords
        if not has_heading_level_containing(
            markdown_headings,
            level=1,
            keyword=keyword,
        )
    ]
    all_missing_headings = missing_headings + missing_h1_keyword_headings
    if all_missing_headings:
        raise ContractValidationError(
            "missing required artifact headings: "
            + ", ".join(all_missing_headings)
        )


def strip_fenced_code_blocks(markdown: str) -> str:
    lines: list[str] = []
    in_fence = False
    fence_marker = ""
    for line in markdown.splitlines():
        stripped = line.lstrip()
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fence = True
            fence_marker = stripped[:3]
            continue
        if in_fence:
            if stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = ""
            continue
        lines.append(line)
    return "\n".join(lines)


def extract_markdown_heading_lines(markdown: str) -> set[str]:
    return {
        line.strip()
        for line in strip_fenced_code_blocks(markdown).splitlines()
        if re.match(r"^#{1,6}\s+\S", line.strip())
    }


def has_required_artifact_heading(
    heading: str,
    *,
    markdown_outside_code: str,
    markdown_headings: set[str],
) -> bool:
    if heading.startswith("#"):
        return heading in markdown_headings
    return heading in markdown_outside_code


def has_heading_level_containing(
    markdown_headings: set[str],
    *,
    level: int,
    keyword: str,
) -> bool:
    heading_prefix = "#" * level + " "
    return any(
        heading.startswith(heading_prefix) and keyword in heading[len(heading_prefix):]
        for heading in markdown_headings
    )


def build_artifact_contract_prompt(
    *,
    workflow_id: str,
    current_stage_id: str,
) -> str:
    stage_key = (workflow_id, current_stage_id)
    required_headings = REQUIRED_ARTIFACT_HEADINGS.get(stage_key)
    required_h1_keywords = REQUIRED_ARTIFACT_H1_KEYWORDS.get(stage_key, [])
    if not required_headings and not required_h1_keywords:
        return ""

    headings = "\n".join(
        f"- {heading}" for heading in (required_headings or [])
    )
    h1_keyword_requirements = ""
    if required_h1_keywords:
        keywords = "、".join(required_h1_keywords)
        h1_keyword_requirements = (
            f"真实 H1 标题必须包含以下关键词：{keywords}。\n"
        )
    return (
        "\n\n【结构化产出物契约】\n"
        "chat 只允许返回给用户看的简短中文说明，禁止包含 Markdown 标题、"
        "表格、代码块、Mermaid 图或完整文档正文。\n"
        "本阶段必须更新右侧产出物：artifact_update.type 必须为 replace。\n"
        "artifact_update.markdown 必须是完整 Markdown 文档，不能只返回片段，"
        "不能用省略号表示未修改内容。\n"
        f"{h1_keyword_requirements}"
        "以下以 # 开头的条目必须作为真实 Markdown 标题行出现，"
        "不能只放在正文描述或代码块中；非 # 开头条目必须出现在正文中：\n"
        f"{headings}\n"
        "如果用户需求信息不足，也要先生成需求分析/待澄清问题文档，"
        "把阻断问题写入对应章节，不能只在 chat 中提问。\n"
    )


def validate_agent_turn(
    output: AgentTurnOutput,
    *,
    workflow_id: str,
    current_stage_id: str,
) -> AgentTurnOutput:
    stages = WORKFLOW_STAGES.get(workflow_id)
    if stages is None:
        raise ContractValidationError(f"unknown workflow: {workflow_id}")
    if current_stage_id not in stages:
        raise ContractValidationError(
            f"unknown current stage: {current_stage_id}"
        )

    if output.stage_action is not None:
        current_index = stages.index(current_stage_id)
        if current_index == len(stages) - 1:
            raise ContractValidationError(
                "last stage cannot request next stage"
            )

        expected_target = stages[current_index + 1]
        if output.stage_action.target_stage_id not in stages:
            raise ContractValidationError(
                f"invalid target stage: {output.stage_action.target_stage_id}"
            )
        if output.stage_action.target_stage_id != expected_target:
            raise ContractValidationError(
                f"target stage must be next stage: {expected_target}"
            )

    validate_artifact_template(
        output,
        workflow_id=workflow_id,
        current_stage_id=current_stage_id,
    )

    return output
