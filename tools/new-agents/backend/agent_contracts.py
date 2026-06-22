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
    "STORY_BREAKDOWN": ["BACKLOG"],
}

REQUIRED_ARTIFACT_HEADINGS: dict[tuple[str, str], list[str]] = {
    ("TEST_DESIGN", "CLARIFY"): [
        "# 需求分析文档",
        "## 文档信息",
        "## 1. 需求事实清单",
        "## 2. 被测系统与边界",
        "## 3. 业务规则与数据状态",
        "## 4. 核心链路与异常链路",
        "## 5. 待澄清问题",
        "## 6. 隐式质量需求",
        "## 7. 后续测试设计输入",
        "## 8. 阶段门禁",
        "事实 ID",
        "证据等级",
        "阻断性",
        "责任方",
        "状态",
    ],
    ("TEST_DESIGN", "STRATEGY"): [
        "# 测试策略蓝图",
        "## 1. 策略摘要",
        "## 2. 质量目标",
        "## 3. 风险识别与 FMEA",
        "### 3.1 风险矩阵",
        "### 3.2 风险明细",
        "## 4. 测试技术选型",
        "## 5. 测试分层策略",
        "### 5.1 测试金字塔",
        "### 5.2 分层明细",
        "## 6. 测试点拓扑",
        "## 7. 资源与取舍",
        "## 8. 阶段门禁",
        "风险 ID",
        "测试点 ID",
        "覆盖建议",
    ],
    ("TEST_DESIGN", "CASES"): [
        "# 测试用例集",
        "## 1. 用例统计",
        "## 2. 用例设计依据",
        "## 3. 按维度分组的用例清单",
        "## 4. 测试数据与环境",
        "## 5. 自动化候选",
        "## 6. 测试点覆盖追溯",
        "## 7. 开放问题",
        "## 8. 阶段门禁",
        "ID",
        "用例标题",
        "优先级",
        "测试维度",
        "关联测试点",
        "关联风险",
        "前置条件",
        "操作步骤",
        "测试数据",
        "预期结果",
        "断言",
        "执行层级",
        "自动化建议",
        "状态",
    ],
    ("TEST_DESIGN", "DELIVERY"): [
        "# 测试设计文档",
        "## 1. 文档信息",
        "## 2. 执行摘要",
        "## 3. 需求分析摘要",
        "## 4. 测试策略摘要",
        "## 5. 测试用例摘要",
        "## 6. 覆盖地图",
        "## 7. 开放风险",
        "## 8. 交付验收清单",
        "## 9. 签署确认",
        "## 10. 变更记录",
    ],
    ("REQ_REVIEW", "REVIEW"): [
        "# 需求评审问题清单",
        "## 评审信息",
        "## 评审范围与不评审范围",
        "## 需求质量总览",
        "## 需求质量结构图",
        "## 问题统计",
        "## 按维度问题清单",
        "## 修订建议",
        "## 阶段门禁",
        "评审维度",
        "问题描述",
        "优先级",
        "阻断性",
        "所属需求章节",
        "影响范围",
        "证据/依据",
        "建议",
        "责任方/确认人",
        "状态",
    ],
    ("REQ_REVIEW", "REPORT"): [
        "# 需求评审报告",
        "## 评审结论",
        "### 判定标准",
        "## 评审信息",
        "## 问题统计",
        "## 优先级看板",
        "## 问题关闭清单",
        "### P0 阻塞性问题",
        "### P1 重要问题",
        "### P2 优化建议",
        "## 复审条件",
        "## 签署确认",
        "## 变更记录",
        "关闭状态",
        "复审条件",
        "签署状态",
    ],
    ("INCIDENT_REVIEW", "TIMELINE"): [
        "# 故障复盘报告",
        "## 1. 事件概要",
        "## 2. 影响量化",
        "## 3. 事实来源",
        "## 4. 事件时间线",
        "## 5. 事实/推测隔离",
        "## 6. 事实摘要",
        "## 7. 参与人员",
        "## 8. 待补充信息",
        "## 9. 阶段门禁",
        "可信度",
        "阻断性",
        "状态",
    ],
    ("INCIDENT_REVIEW", "ROOT_CAUSE"): [
        "# 故障复盘报告",
        "## 6. 根因分析",
        "### 6.1 5-Why 分析链",
        "### 6.2 根因证据表",
        "### 6.3 原因鱼骨图",
        "### 6.4 根因结论",
        "### 6.5 排除项",
        "### 6.6 未验证原因",
        "### 6.7 阶段门禁",
        "证据强度",
        "置信度",
        "可行动性",
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
        "#### 7.3 根因覆盖检查",
        "### 8. 防复发检查清单",
        "### 9. 复查计划",
        "### 10. 遗留风险与风险接受",
        "### 11. 经验教训",
        "### 12. 组织学习",
        "## 签署确认",
        "### 13. 阶段门禁",
        "ID",
        "改进措施",
        "类型",
        "对应根因",
        "建议负责人",
        "完成期限",
        "验证方式",
        "验收标准",
        "优先级",
        "当前状态",
        "追踪机制",
        "复查日期",
        "覆盖状态",
        "风险接受人",
    ],
    ("IDEA_BRAINSTORM", "DEFINE"): [
        "# 问题域分析",
        "## 问题假设陈述",
        "## 目标用户画像",
        "## 问题域全景",
        "## 证据与验证状态",
        "## 问题-用户-场景匹配",
        "## 约束与边界",
        "## 反向验证（风险思考）",
        "## 阶段门禁",
        "证据等级",
        "验证动作",
        "验证状态",
    ],
    ("IDEA_BRAINSTORM", "DIVERGE"): [
        "# 创意发散",
        "## 发散方法说明",
        "## 发散全景图",
        "## 创意卡片库",
        "## 创意来源与假设",
        "## 搁置/排除记录",
        "## 阶段门禁",
        "关键假设",
        "状态理由",
    ],
    ("IDEA_BRAINSTORM", "CONVERGE"): [
        "# 收敛聚焦",
        "## 决策矩阵",
        "## ICE 评估表",
        "## 资源约束",
        "## 敏感性分析",
        "## 验证实验",
        "## 整合演进路径（如果触发合并）",
        "## 阶段门禁",
        "评分口径",
        "影响力",
        "信心",
        "实现难度",
        "ICE得分",
        "淘汰理由",
        "推荐方案",
        "下一步验证",
        "合并逻辑",
        "证据来源",
        "用户确认状态",
    ],
    ("IDEA_BRAINSTORM", "CONCEPT"): [
        "# 产品概念简报",
        "## 定位声明",
        "## 核心假设",
        "## Lean Canvas 产品画布",
        "## MVP 功能分布",
        "## 核心增长漏斗",
        "## Pre-mortem 风险分析",
        "## 验证路线",
        "## 不可做范围",
        "## 决策记录",
        "## 下一步行动",
        "## 阶段门禁",
        "owner",
        "状态",
    ],
    ("VALUE_DISCOVERY", "ELEVATOR"): [
        "# 价值定位分析",
        "## 定位摘要",
        "## 价值结构图",
        "## 目标用户与场景",
        "## 痛点证据",
        "## 差异化价值",
        "## 商业可行性",
        "## 未验证假设",
        "## 60 秒电梯演讲",
        "## 阶段门禁",
        "证据等级",
        "验证动作",
        "状态",
        "60 秒电梯演讲",
    ],
    ("VALUE_DISCOVERY", "PERSONA"): [
        "# 用户画像分析",
        "## 画像摘要",
        "## 主要用户画像",
        "### 画像 1",
        "#### 基础特征",
        "#### 行为特征",
        "## 行为与场景",
        "## 决策链",
        "## 痛点证据",
        "## 反画像",
        "## 用户优先级排序",
        "## 阶段门禁",
        "证据等级",
        "验证状态",
    ],
    ("VALUE_DISCOVERY", "JOURNEY"): [
        "# 用户旅程分析",
        "## 用户旅程地图",
        "## 结构化旅程地图",
        "## 关键阶段详细分析",
        "## 痛点优先级排序",
        "高优先级痛点",
        "中等优先级痛点",
        "低优先级痛点",
        "## 机会评分",
        "## 产品切入策略",
        "## 验证实验",
        "## 阶段门禁",
        "旅程阶段",
        "触点渠道",
        "用户任务",
        "情绪评分",
        "关键痛点",
        "现有方案不足",
        "机会假设",
        "成功指标",
        "验证状态",
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
        "## 7. 非功能需求",
        "## 8. 验收标准",
        "## 9. 路线图",
        "## 10. 风险评估",
        "## 11. Lisa Handoff 输入",
        "## 12. 阶段门禁",
        "可测试性等级",
        "owner",
        "状态",
    ],
    ("STORY_BREAKDOWN", "BACKLOG"): [
        "# 用户故事拆解包",
        "## 文档信息",
        "## 输入理解与拆解边界",
        "## Epic 地图",
        "## User Story Backlog",
        "## 验收标准矩阵",
        "## 依赖与风险",
        "## Sprint 切片建议",
        "## Lisa Handoff 输入",
        "## 阶段门禁",
        "Story ID",
        "Epic",
        "优先级",
        "Sprint",
        "状态",
    ],
}

REQUIRED_ARTIFACT_H1_KEYWORDS: dict[tuple[str, str], list[str]] = {
    ("VALUE_DISCOVERY", "BLUEPRINT"): ["需求蓝图"],
}

REQUIRED_ARTIFACT_MERMAID_DIAGRAMS: dict[tuple[str, str], list[str]] = {
    ("TEST_DESIGN", "CLARIFY"): ["flowchart"],
    ("TEST_DESIGN", "STRATEGY"): ["quadrantChart", "block-beta"],
    ("REQ_REVIEW", "REVIEW"): ["flowchart"],
    ("REQ_REVIEW", "REPORT"): ["pie"],
    ("INCIDENT_REVIEW", "TIMELINE"): ["timeline"],
    ("INCIDENT_REVIEW", "ROOT_CAUSE"): ["mindmap"],
    ("INCIDENT_REVIEW", "IMPROVEMENT"): ["pie"],
    ("IDEA_BRAINSTORM", "DEFINE"): ["mindmap"],
    ("IDEA_BRAINSTORM", "DIVERGE"): ["mindmap"],
    ("IDEA_BRAINSTORM", "CONVERGE"): ["quadrantChart"],
    ("VALUE_DISCOVERY", "ELEVATOR"): ["flowchart"],
    ("VALUE_DISCOVERY", "JOURNEY"): ["journey"],
    ("STORY_BREAKDOWN", "BACKLOG"): ["flowchart"],
}

REQUIRED_ARTIFACT_STRUCTURED_VISUALS: dict[tuple[str, str], list[str]] = {
    ("REQ_REVIEW", "REVIEW"): ["score-matrix"],
    ("TEST_DESIGN", "STRATEGY"): ["risk-board"],
    ("TEST_DESIGN", "CASES"): ["traceability-matrix"],
    ("TEST_DESIGN", "DELIVERY"): ["coverage-map"],
    ("INCIDENT_REVIEW", "IMPROVEMENT"): ["action-board"],
    ("VALUE_DISCOVERY", "ELEVATOR"): ["score-matrix"],
    ("VALUE_DISCOVERY", "JOURNEY"): ["journey-map"],
    ("REQ_REVIEW", "REPORT"): ["priority-board"],
    ("INCIDENT_REVIEW", "ROOT_CAUSE"): ["cause-map"],
    ("IDEA_BRAINSTORM", "CONCEPT"): ["mvp-map"],
    ("VALUE_DISCOVERY", "BLUEPRINT"): ["roadmap"],
    ("STORY_BREAKDOWN", "BACKLOG"): ["story-map"],
}

STRUCTURED_VISUAL_SCHEMA_PROMPTS: dict[str, str] = {
    "traceability-matrix": (
        'traceability-matrix 必须严格使用如下 JSON 结构：{"type": '
        '"traceability-matrix", "title": "可选标题", "columns": ["测试点", '
        '"TC-001"], "rows": [{"测试点": "登录链路", "TC-001": "覆盖"}]}。'
        "columns 必须是非空字符串数组；rows 必须是对象数组，每个对象的 key "
        "必须对应 columns 中的列名。禁止使用 fenced:ai4se-visual 文本，"
        "禁止使用 data.requirements / data.testCases / data.matrix 旧结构。"
    ),
    "score-matrix": (
        'score-matrix 必须严格使用如下 JSON 结构：{"type": '
        '"score-matrix", "title": "可选标题", "columns": ["维度", '
        '"评分", "依据", "风险"], "rows": [{"维度": "可测试性", '
        '"评分": 3, "依据": "验收标准不完整", "风险": "用例断言不稳定"}]}。'
        "columns 必须是非空字符串数组；rows 必须是对象数组，每个对象的 key "
        "必须对应 columns 中的列名。禁止使用 data/matrix 嵌套旧结构。"
    ),
    "risk-board": (
        'risk-board 必须严格使用如下 JSON 结构：{"type": '
        '"risk-board", "title": "可选标题", "columns": ["风险", '
        '"S", "O", "D", "RPN", "缓解策略", "覆盖建议"], '
        '"rows": [{"风险": "支付失败", "S": 5, "O": 3, "D": 4, '
        '"RPN": 60, "缓解策略": "补充异常重试", "覆盖建议": "P0 用例"}]}。'
        "columns 必须是非空字符串数组；rows 必须是对象数组，每个对象的 key "
        "必须对应 columns 中的列名。"
    ),
    "action-board": (
        'action-board 必须严格使用如下 JSON 结构：{"type": '
        '"action-board", "title": "可选标题", "columns": ["行动", '
        '"对应根因", "负责人", "期限", "状态", "验证方式"], '
        '"rows": [{"行动": "增加发布门禁", "对应根因": "Why-3", '
        '"负责人": "测试负责人", "期限": "一周内", "状态": "待开始", '
        '"验证方式": "CI 检查通过"}]}。columns 必须是非空字符串数组；'
        "rows 必须是对象数组，每个对象的 key 必须对应 columns 中的列名。"
    ),
    "journey-map": (
        'journey-map 必须严格使用如下 JSON 结构：{"type": '
        '"journey-map", "title": "可选标题", "columns": ["阶段", '
        '"用户任务", "触点", "情绪评分", "关键痛点", "机会假设"], '
        '"rows": [{"阶段": "方案评估", "用户任务": "比较替代方案", '
        '"触点": "社区/官网", "情绪评分": 2, "关键痛点": "信息分散", '
        '"机会假设": "统一评估清单"}]}。columns 必须是非空字符串数组；'
        "rows 必须是对象数组，每个对象的 key 必须对应 columns 中的列名。"
    ),
    "coverage-map": (
        'coverage-map 必须严格使用如下 JSON 结构：{"type": '
        '"coverage-map", "title": "可选标题", "columns": ["需求", '
        '"风险", "测试点", "用例", "验收状态"], "rows": [{"需求": '
        '"REQ-1", "风险": "RISK-1", "测试点": "TP-1", "用例": '
        '"TC-001", "验收状态": "已覆盖"}]}。columns 必须是非空字符串数组；'
        "rows 必须是对象数组，每个对象的 key 必须对应 columns 中的列名。"
    ),
    "priority-board": (
        'priority-board 必须严格使用如下 JSON 结构：{"type": '
        '"priority-board", "title": "可选标题", "columns": ["问题", '
        '"优先级", "影响范围", "责任方", "下一步", "关闭状态"], "rows": [{"问题": '
        '"验收标准缺失", "优先级": "P0", "影响范围": "核心链路", '
        '"责任方": "产品负责人", "下一步": "补充验收标准", '
        '"关闭状态": "待修订"}]}。'
        "columns 必须是非空字符串数组；rows 必须是对象数组，每个对象的 key "
        "必须对应 columns 中的列名。"
    ),
    "story-map": (
        'story-map 必须严格使用如下 JSON 结构：{"type": '
        '"story-map", "title": "可选标题", "columns": ["Epic", '
        '"Story", "优先级", "Sprint", "状态"], "rows": [{"Epic": '
        '"EPIC-001 用户管理", "Story": "US-001 创建用户", "优先级": '
        '"P0", "Sprint": "Sprint 1", "状态": "待评审"}]}。'
        "columns 必须是非空字符串数组；rows 必须是对象数组，每个对象的 key "
        "必须对应 columns 中的列名。"
    ),
    "cause-map": (
        'cause-map 必须严格使用如下 JSON 结构：{"type": '
        '"cause-map", "title": "可选标题", "columns": ["层级", '
        '"问题", "回答", "原因类型", "证据"], "rows": [{"层级": '
        '"Why-2", "问题": "为什么未被拦截", "回答": "缺少发布门禁", '
        '"原因类型": "流程", "证据": "发布记录"}]}。columns 必须是非空字符串数组；'
        "rows 必须是对象数组，每个对象的 key 必须对应 columns 中的列名。"
    ),
    "mvp-map": (
        'mvp-map 必须严格使用如下 JSON 结构：{"type": '
        '"mvp-map", "title": "可选标题", "columns": ["模块", '
        '"MVP层级", "用户价值", "验证指标", "取舍理由"], "rows": [{"模块": '
        '"核心闭环", "MVP层级": "P0", "用户价值": "完成关键任务", '
        '"验证指标": "激活率", "取舍理由": "支撑定位声明"}]}。'
        "columns 必须是非空字符串数组；rows 必须是对象数组，每个对象的 key "
        "必须对应 columns 中的列名。"
    ),
    "roadmap": (
        'roadmap 必须严格使用如下 JSON 结构：{"type": '
        '"roadmap", "title": "可选标题", "columns": ["版本", '
        '"时间", "核心功能", "目标", "成功指标"], "rows": [{"版本": '
        '"v1.0 MVP", "时间": "4 周", "核心功能": "核心闭环", '
        '"目标": "验证主价值", "成功指标": "任务完成率"}]}。'
        "columns 必须是非空字符串数组；rows 必须是对象数组，每个对象的 key "
        "必须对应 columns 中的列名。"
    ),
}

LEGACY_PROTOCOL_TAG_PATTERN = re.compile(
    r"<\s*/?\s*(?:CHART|ARTIFACT|CHAT)\b[^>]*>",
    re.IGNORECASE,
)
MARK_TAG_PATTERN = re.compile(r"<\s*/?\s*mark\s*>", re.IGNORECASE)


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
        if LEGACY_PROTOCOL_TAG_PATTERN.search(value):
            raise ValueError(
                "chat must not contain legacy protocol tags; use structured "
                "artifact_update instead"
            )
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
    required_mermaid_diagrams = REQUIRED_ARTIFACT_MERMAID_DIAGRAMS.get(
        stage_key,
        [],
    )
    required_structured_visuals = REQUIRED_ARTIFACT_STRUCTURED_VISUALS.get(
        stage_key,
        [],
    )
    if (
        not required_headings
        and not required_h1_keywords
        and not required_mermaid_diagrams
        and not required_structured_visuals
    ):
        return

    if output.artifact_update.type != "replace":
        raise ContractValidationError(
            "artifact update is required for "
            f"{workflow_id}/{current_stage_id}"
        )

    markdown = output.artifact_update.markdown or ""
    markdown_outside_code = strip_mark_tags(strip_fenced_code_blocks(markdown))
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

    mermaid_blocks = extract_mermaid_code_blocks(markdown)
    missing_mermaid_diagrams = [
        f"Mermaid {diagram_type}"
        for diagram_type in required_mermaid_diagrams
        if not has_required_mermaid_diagram(
            mermaid_blocks,
            diagram_type=diagram_type,
        )
    ]
    if missing_mermaid_diagrams:
        raise ContractValidationError(
            "missing required artifact visualizations: "
            + ", ".join(missing_mermaid_diagrams)
        )

    structured_visual_blocks = extract_structured_visual_blocks(markdown)
    if required_structured_visuals and "fenced:ai4se-visual" in markdown:
        raise ContractValidationError(
            "ai4se-visual 必须使用 Markdown 三反引号代码块："
            "```ai4se-visual ... ```，不要使用 fenced:ai4se-visual"
        )
    missing_structured_visuals = [
        f"ai4se-visual {visual_type}"
        for visual_type in required_structured_visuals
        if not has_required_structured_visual(
            structured_visual_blocks,
            visual_type=visual_type,
        )
    ]
    if missing_structured_visuals:
        invalid_required_blocks = [
            block
            for block in structured_visual_blocks
            if block.get("type") in required_structured_visuals
        ]
        if invalid_required_blocks:
            invalid_type = str(invalid_required_blocks[0].get("type"))
            raise ContractValidationError(
                f"{invalid_type} 必须使用 columns 和 rows 结构；"
                "columns 必须是非空字符串数组，rows 必须是对象数组。"
            )
        raise ContractValidationError(
            "missing required artifact visualizations: "
            + ", ".join(missing_structured_visuals)
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


def strip_mark_tags(markdown: str) -> str:
    return MARK_TAG_PATTERN.sub("", markdown)


def extract_markdown_heading_lines(markdown: str) -> set[str]:
    return {
        strip_mark_tags(line.strip())
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


def extract_mermaid_code_blocks(markdown: str) -> list[str]:
    blocks: list[str] = []
    in_fence = False
    fence_marker = ""
    is_mermaid = False
    current_lines: list[str] = []

    for line in markdown.splitlines():
        stripped = line.lstrip()
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            fence_marker = stripped[:3]
            language = stripped[3:].strip().split(maxsplit=1)[0].lower()
            in_fence = True
            is_mermaid = language == "mermaid"
            current_lines = []
            continue

        if in_fence:
            if stripped.startswith(fence_marker):
                if is_mermaid:
                    blocks.append("\n".join(current_lines))
                in_fence = False
                fence_marker = ""
                is_mermaid = False
                current_lines = []
                continue
            if is_mermaid:
                current_lines.append(line)

    return blocks


def has_required_mermaid_diagram(
    mermaid_blocks: list[str],
    *,
    diagram_type: str,
) -> bool:
    diagram_pattern = re.compile(
        rf"(?im)^\s*{re.escape(diagram_type)}\b"
    )
    return any(diagram_pattern.search(block) for block in mermaid_blocks)


def extract_structured_visual_blocks(markdown: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    in_fence = False
    fence_marker = ""
    is_structured_visual = False
    current_lines: list[str] = []

    for line in markdown.splitlines():
        stripped = line.lstrip()
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            fence_marker = stripped[:3]
            language = stripped[3:].strip().split(maxsplit=1)[0].lower()
            in_fence = True
            is_structured_visual = language == "ai4se-visual"
            current_lines = []
            continue

        if in_fence:
            if stripped.startswith(fence_marker):
                if is_structured_visual:
                    try:
                        parsed = json.loads("\n".join(current_lines))
                    except json.JSONDecodeError:
                        parsed = None
                    if isinstance(parsed, dict):
                        blocks.append(parsed)
                in_fence = False
                fence_marker = ""
                is_structured_visual = False
                current_lines = []
                continue
            if is_structured_visual:
                current_lines.append(line)

    return blocks


def has_required_structured_visual(
    structured_visual_blocks: list[dict[str, Any]],
    *,
    visual_type: str,
) -> bool:
    return any(
        is_valid_structured_visual_block(block, visual_type=visual_type)
        for block in structured_visual_blocks
    )


def is_valid_structured_visual_block(
    block: dict[str, Any],
    *,
    visual_type: str,
) -> bool:
    if block.get("type") != visual_type:
        return False
    columns = block.get("columns")
    rows = block.get("rows")
    return (
        isinstance(columns, list)
        and bool(columns)
        and all(isinstance(column, str) and column.strip() for column in columns)
        and isinstance(rows, list)
        and all(isinstance(row, dict) for row in rows)
    )


def build_artifact_contract_prompt(
    *,
    workflow_id: str,
    current_stage_id: str,
) -> str:
    stage_key = (workflow_id, current_stage_id)
    required_headings = REQUIRED_ARTIFACT_HEADINGS.get(stage_key)
    required_h1_keywords = REQUIRED_ARTIFACT_H1_KEYWORDS.get(stage_key, [])
    required_mermaid_diagrams = REQUIRED_ARTIFACT_MERMAID_DIAGRAMS.get(
        stage_key,
        [],
    )
    required_structured_visuals = REQUIRED_ARTIFACT_STRUCTURED_VISUALS.get(
        stage_key,
        [],
    )
    if (
        not required_headings
        and not required_h1_keywords
        and not required_mermaid_diagrams
        and not required_structured_visuals
    ):
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
    mermaid_requirements = ""
    if required_mermaid_diagrams:
        diagrams = "、".join(required_mermaid_diagrams)
        mermaid_requirements = (
            "本阶段必须包含 fenced Mermaid 代码块，且代码块中必须出现以下图类型："
            f"{diagrams}。不要把 Mermaid 图放在 chat 中。\n"
        )
    structured_visual_requirements = ""
    if required_structured_visuals:
        visual_types = "、".join(required_structured_visuals)
        visual_schema_prompts = "".join(
            STRUCTURED_VISUAL_SCHEMA_PROMPTS.get(visual_type, "")
            for visual_type in required_structured_visuals
        )
        structured_visual_requirements = (
            "本阶段必须包含 fenced ai4se-visual 代码块，代码块内容必须是合法 JSON 对象，"
            f'且 type 必须包含以下结构化可视化类型：{visual_types}。'
            f"{visual_schema_prompts}"
            "优先输出结构化数据并交给前端共享组件渲染，不要手写复杂 HTML；"
            "不要把 ai4se-visual 放在 chat 中。\n"
        )
    stage_action_contract = build_stage_action_contract_prompt(
        workflow_id=workflow_id,
        current_stage_id=current_stage_id,
    )
    return (
        "\n\n【结构化产出物契约】\n"
        "chat 只允许返回给用户看的自然工作对话，禁止包含 Markdown 标题、"
        "表格、代码块、Mermaid 图、完整文档正文或 <CHART>/<ARTIFACT>/"
        "<CHAT> 旧标签协议。\n"
        "chat 必须承担左侧对话承接作用：像自然顾问式对话，"
        "用短段落说明本次判断、关键假设、右侧产出物更新和用户下一步；"
        "可以适度使用 bullet、少量重点加粗或引用块帮助扫读，但不要每轮都套用"
        "固定栏目或固定字段模板。如果当前阶段可推进，应自然引导用户查看右侧产出物，"
        "并由 stage_action 触发前端确认控件。\n"
        "本阶段必须更新右侧产出物：artifact_update.type 必须为 replace。\n"
        "artifact_update.markdown 必须是完整 Markdown 文档，不能只返回片段，"
        "不能用省略号表示未修改内容。\n"
        "即使用户只回复“继续”“没问题”“确认”等短确认，也必须保留所有必填标题，"
        "并把已确认信息写回当前阶段完整文档；不能只在 chat 中说明已生成或已确认。\n"
        "当当前阶段已经完成并建议进入下一阶段时，stage_action 请求前端显示确认控件即可，"
        "不要在同一轮生成下一阶段产出物；artifact_update.markdown "
        "继续返回当前阶段的完整产出物。用户点击确认控件后，系统才会切换阶段。\n"
        f"{h1_keyword_requirements}"
        "以下以 # 开头的条目必须作为真实 Markdown 标题行出现，"
        "不能只放在正文描述或代码块中；非 # 开头条目必须出现在正文中：\n"
        f"{headings}\n"
        f"{mermaid_requirements}"
        f"{structured_visual_requirements}"
        f"{stage_action_contract}"
        "如果用户需求信息不足，也要先生成需求分析/待澄清问题文档，"
        "把阻断问题写入对应章节，不能只在 chat 中提问。\n"
    )


def build_stage_action_contract_prompt(
    *,
    workflow_id: str,
    current_stage_id: str,
) -> str:
    stages = WORKFLOW_STAGES.get(workflow_id)
    if not stages or current_stage_id not in stages:
        return ""

    current_index = stages.index(current_stage_id)
    if current_index == len(stages) - 1:
        return "当前阶段是最后阶段，stage_action 必须为 null。\n"

    expected_target = stages[current_index + 1]
    return (
        "当当前阶段产出物已经完整、chat 已经建议用户进入下一阶段时，"
        "必须同一轮返回 stage_action，用于让前端显示确认控件；"
        '此时唯一合法值是 {"type": "request_next_stage", '
        f'"target_stage_id": "{expected_target}"}}。'
        f'target_stage_id 必须填写内部阶段 ID "{expected_target}"，'
        "不要填写阶段中文名称。"
        "stage_action 只请求用户确认，不代表已经切换阶段；"
        "用户点击确认控件后，系统才会进入下一阶段。\n"
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
