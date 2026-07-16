from __future__ import annotations

import json
import re
from typing import Any

from artifact_data_renderer_base import (
    DocumentInfo,
    StageGateCheck,
    render_compact_metadata,
)
from artifact_data_value_schema import (
    PositioningSummary,
    ValueFlowNode,
    ValueFlowLink,
    ValueFlow,
    TargetScenario,
    PainEvidence,
    Differentiator,
    BusinessFeasibility,
    ValueScore,
    ValueScoreSummary,
    ValueAssumption,
    ValueDiscoveryElevatorArtifactData,
    PersonaSummary,
    PersonaFeature,
    PersonaBehaviorFeature,
    PersonaProfile,
    PersonaBehaviorScenario,
    PersonaDecisionRole,
    PersonaPainEvidence,
    AntiPersona,
    PersonaPriorityRanking,
    ValueDiscoveryPersonaArtifactData,
    JourneySummary,
    JourneyStage,
    JourneyPainPriority,
    JourneyOpportunityScore,
    JourneyEntryStrategy,
    JourneyValidationExperiment,
    ValueDiscoveryJourneyArtifactData,
    BlueprintDocumentInfo,
    BlueprintProductOverview,
    BlueprintTargetUser,
    BlueprintFeatureItem,
    BlueprintFeatureModule,
    BlueprintRequirement,
    BlueprintFlowNode,
    BlueprintFlowLink,
    BlueprintMainFlow,
    BlueprintSuccessMetric,
    BlueprintMvpFeature,
    BlueprintIteration,
    BlueprintMvpPlan,
    BlueprintNonFunctionalRequirement,
    BlueprintAcceptanceCriterion,
    BlueprintRoadmapItem,
    BlueprintRisk,
    BlueprintLisaHandoffInput,
    ValueDiscoveryBlueprintArtifactData,
)


def _render_value_positioning_summary(summary: PositioningSummary) -> str:
    rows = [
        ("一句话定位", summary.one_liner),
        ("核心用户", summary.core_user),
        ("核心痛点", summary.core_pain),
        ("独特价值", summary.unique_value),
        ("当前判断", summary.current_judgement),
    ]
    return "## 定位摘要\n" + _markdown_table(["字段", "内容"], rows)


def _render_value_flow(flow: ValueFlow) -> str:
    node_lookup = {node.node_id: node for node in flow.nodes}
    safe_ids: dict[str, str] = {}
    rendered_ids = {
        node.node_id: _node_id(node.node_id, safe_ids) for node in flow.nodes
    }
    lines = ["```mermaid", "flowchart TD"]
    for node in flow.nodes:
        lines.append(
            f'    {rendered_ids[node.node_id]}["{_escape_mermaid_label(node.label)}<br/>'
            f'{_escape_mermaid_label(node.description)}"]'
        )
    for link in flow.links:
        lines.append(
            f"    {rendered_ids[link.from_node]} -->|"
            f'"{_escape_mermaid_label(link.label)}"| '
            f"{rendered_ids[link.to_node]}"
        )
    lines.append("```")

    rows = [
        (node.node_id, node.label, node.description) for node in node_lookup.values()
    ]
    return (
        "## 价值结构图\n"
        + "\n".join(lines)
        + "\n\n"
        + _markdown_table(["节点 ID", "节点", "说明"], rows)
    )


def _render_target_scenarios(items: list[TargetScenario]) -> str:
    rows = [
        (item.dimension, item.description, item.evidence_level, item.status)
        for item in items
    ]
    return "## 目标用户与场景\n" + _markdown_table(
        ["维度", "描述", "证据等级", "状态"],
        rows,
    )


def _render_pain_evidence(items: list[PainEvidence]) -> str:
    rows = [
        (
            item.pain_id,
            item.description,
            item.scene,
            item.impact,
            item.evidence_level,
            item.validation_action,
            item.status,
        )
        for item in items
    ]
    return "## 痛点证据\n" + _markdown_table(
        ["痛点 ID", "痛点描述", "发生场景", "影响程度", "证据等级", "验证动作", "状态"],
        rows,
    )


def _render_differentiators(items: list[Differentiator]) -> str:
    rows = [
        (
            item.dimension,
            item.our_value,
            item.existing_solution,
            item.evidence,
            item.status,
        )
        for item in items
    ]
    return "## 差异化价值\n" + _markdown_table(
        ["维度", "我们", "现有方案/竞品", "差异化证据", "状态"],
        rows,
    )


def _render_business_feasibility(items: list[BusinessFeasibility]) -> str:
    rows = [
        (
            item.dimension,
            item.judgement,
            item.basis,
            item.validation_action,
            item.status,
        )
        for item in items
    ]
    return "## 商业可行性\n" + _markdown_table(
        ["维度", "判断", "依据", "验证动作", "状态"],
        rows,
    )


def _render_value_score_matrix(
    items: list[ValueScore],
    summary: ValueScoreSummary,
) -> str:
    rows = [
        (item.dimension, item.score, item.basis, item.next_validation) for item in items
    ]
    visual = {
        "type": "score-matrix",
        "title": "价值主张初筛评分矩阵",
        "columns": ["评估维度", "评分", "依据", "下一步验证"],
        "rows": [
            {
                "评估维度": item.dimension,
                "评分": item.score,
                "依据": item.basis,
                "下一步验证": item.next_validation,
            }
            for item in items
        ],
    }
    return (
        "## 价值主张评分\n"
        + _markdown_table(["评估维度", "评分", "依据", "下一步验证"], rows)
        + "\n\n"
        + "```ai4se-visual\n"
        + json.dumps(visual, ensure_ascii=False, indent=2)
        + "\n```"
        + "\n\n"
        + f"> **评分结论**：总分 {summary.total_score}，平均分 "
        + f"{summary.average_score:.2f}。{summary.judgement}"
    )


def _render_value_assumptions(items: list[ValueAssumption]) -> str:
    rows = [
        (
            item.assumption_id,
            item.content,
            item.impact,
            item.validation_action,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 未验证假设\n" + _markdown_table(
        ["假设 ID", "假设内容", "影响范围", "验证动作", "责任方/验证人", "状态"],
        rows,
    )


def _render_elevator_pitch(pitch: str) -> str:
    return "## 60 秒电梯演讲\n\n> " + pitch


def _render_value_stage_gate(checks: list[StageGateCheck]) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "## 阶段门禁\n" + "\n".join(lines)


def _persona_names(personas: list[PersonaProfile]) -> dict[str, str]:
    return {persona.persona_id: persona.name for persona in personas}


def _render_persona_summary(summary: PersonaSummary) -> str:
    rows = [
        ("核心用户判断", summary.core_user_judgement),
        ("主要痛点", summary.primary_pain),
        ("验证状态", summary.validation_status),
        ("进入旅程阶段判断", summary.journey_readiness),
    ]
    return "## 画像摘要\n" + _markdown_table(["字段", "内容"], rows)


def _render_persona_profiles(personas: list[PersonaProfile]) -> str:
    sections = ["## 主要用户画像"]
    for index, persona in enumerate(personas, start=1):
        basic_rows = [
            (
                item.dimension,
                item.description,
                item.evidence_level,
                item.validation_status,
            )
            for item in persona.basic_features
        ]
        behavior_rows = [
            (
                item.dimension,
                item.description,
                item.trigger,
                item.evidence_level,
                item.validation_status,
            )
            for item in persona.behavior_features
        ]
        sections.append(
            f"### 画像 {index}\n\n"
            f"**用户类型名称**：{persona.name}（{persona.priority}）\n\n"
            f"> {persona.summary}\n\n"
            "#### 基础特征\n"
            + _markdown_table(
                ["维度", "描述", "证据等级", "验证状态"],
                basic_rows,
            )
            + "\n\n"
            + "#### 行为特征\n"
            + _markdown_table(
                ["维度", "描述", "场景触发", "证据等级", "验证状态"],
                behavior_rows,
            )
        )
    return "\n\n".join(sections)


def _render_persona_behavior_scenarios(
    items: list[PersonaBehaviorScenario],
    personas: list[PersonaProfile],
) -> str:
    persona_names = _persona_names(personas)
    rows = [
        (
            item.scenario_id,
            persona_names[item.persona_id],
            item.scenario,
            item.trigger,
            item.user_goal,
            item.current_solution,
            item.status,
        )
        for item in items
    ]
    return "## 行为与场景\n" + _markdown_table(
        ["场景 ID", "用户类型", "场景描述", "触发条件", "用户目标", "当前做法", "状态"],
        rows,
    )


def _render_persona_decision_chain(
    items: list[PersonaDecisionRole],
    personas: list[PersonaProfile],
) -> str:
    persona_names = _persona_names(personas)
    rows = [
        (
            item.role,
            persona_names[item.persona_id],
            item.concern,
            item.influence,
            item.payment_relation,
            item.evidence_level,
            item.validation_status,
        )
        for item in items
    ]
    return "## 决策链\n" + _markdown_table(
        [
            "决策角色",
            "用户类型/岗位",
            "关注点",
            "影响力",
            "付费/采购关系",
            "证据等级",
            "验证状态",
        ],
        rows,
    )


def _render_persona_pain_evidence(
    items: list[PersonaPainEvidence],
    personas: list[PersonaProfile],
) -> str:
    persona_names = _persona_names(personas)
    rows = [
        (
            item.pain_id,
            persona_names[item.persona_id],
            item.pain,
            item.frequency,
            item.impact,
            item.existing_solution_gap,
            item.evidence_level,
            item.validation_status,
        )
        for item in items
    ]
    return "## 痛点证据\n" + _markdown_table(
        [
            "痛点 ID",
            "用户类型",
            "痛点",
            "频率",
            "影响程度",
            "现有方案不足",
            "证据等级",
            "验证状态",
        ],
        rows,
    )


def _render_anti_personas(items: list[AntiPersona]) -> str:
    rows = [
        (item.name, item.reason, item.boundary, item.risk, item.status)
        for item in items
    ]
    return "## 反画像\n" + _markdown_table(
        ["非目标用户", "为什么不是当前核心用户", "不服务的边界", "风险", "状态"],
        rows,
    )


def _render_persona_priority_ranking(
    items: list[PersonaPriorityRanking],
    personas: list[PersonaProfile],
) -> str:
    persona_names = _persona_names(personas)
    rows = [
        (
            item.priority,
            persona_names[item.persona_id],
            item.reason,
            item.related_pain,
            item.evidence_level,
            item.validation_status,
        )
        for item in items
    ]
    return "## 用户优先级排序\n" + _markdown_table(
        ["优先级", "用户类型", "理由", "关联痛点", "证据等级", "验证状态"],
        rows,
    )


def _render_journey_map(stages: list[JourneyStage]) -> str:
    lines = [
        "```mermaid",
        "journey",
        "    title 核心用户旅程",
    ]
    for stage in stages:
        lines.append(f"    section {_escape_journey_text(stage.stage_name)}")
        lines.append(
            f"        {_escape_journey_text(stage.user_task)}: "
            f"{stage.emotion_score}: 用户"
        )
    lines.append("```")
    return (
        "## 用户旅程地图\n"
        + "\n".join(lines)
        + "\n\n> 数字为情绪评分：1=非常沮丧，5=非常满意"
    )


def _render_journey_map_visual(stages: list[JourneyStage]) -> str:
    visual = {
        "type": "journey-map",
        "title": "用户旅程结构化地图",
        "columns": [
            "阶段",
            "用户任务",
            "触点",
            "情绪评分",
            "关键痛点",
            "机会假设",
            "成功指标",
            "验证状态",
        ],
        "rows": [
            {
                "阶段": item.stage_name,
                "用户任务": item.user_task,
                "触点": item.touchpoint,
                "情绪评分": item.emotion_score,
                "关键痛点": item.key_pain,
                "机会假设": item.opportunity_hypothesis,
                "成功指标": item.success_metric,
                "验证状态": item.validation_status,
            }
            for item in stages
        ],
    }
    return (
        "## 结构化旅程地图\n"
        "```ai4se-visual\n" + json.dumps(visual, ensure_ascii=False, indent=2) + "\n```"
    )


def _render_journey_stage_details(stages: list[JourneyStage]) -> str:
    sections = ["## 关键阶段详细分析"]
    for index, stage in enumerate(stages, start=1):
        rows = [
            ("旅程阶段", f"{stage.stage_id} {stage.stage_name}"),
            ("触点渠道", stage.touchpoint),
            ("用户任务", stage.user_task),
            ("用户目标", stage.user_goal),
            ("用户行为", stage.user_behavior),
            ("情绪评分", f"{stage.emotion_score} 分：{stage.emotion_reason}"),
            ("关键痛点", f"{stage.pain_id} {stage.key_pain}"),
            ("现有方案不足", stage.existing_solution_gap),
            ("机会假设", f"{stage.opportunity_id} {stage.opportunity_hypothesis}"),
            ("成功指标", stage.success_metric),
            ("验证状态", stage.validation_status),
        ]
        sections.append(
            f"### 阶段 {index}：{stage.stage_name}\n"
            + _markdown_table(["维度", "描述"], rows)
        )
    return "\n\n".join(sections)


def _render_journey_pain_priorities(
    items: list[JourneyPainPriority],
    stages: list[JourneyStage],
) -> str:
    stage_names = {stage.stage_id: stage.stage_name for stage in stages}
    sections = ["## 痛点优先级排序"]
    priority_levels = ["高优先级痛点", "中等优先级痛点", "低优先级痛点"]
    headers = ["痛点 ID", "痛点", "影响阶段", "影响程度", "发生频率", "现有方案不足"]
    for level in priority_levels:
        rows = [
            (
                item.pain_id,
                item.pain,
                stage_names[item.stage_id],
                item.impact,
                item.frequency,
                item.existing_solution_gap,
            )
            for item in items
            if item.priority_level == level
        ]
        if not rows:
            rows = [("无", "本轮未识别", "无", "无", "无", "无")]
        sections.append(f"### {level}\n" + _markdown_table(headers, rows))
    return "\n\n".join(sections)


def _render_journey_opportunity_scores(
    items: list[JourneyOpportunityScore],
) -> str:
    rows = [
        (
            item.opportunity_id,
            item.opportunity,
            item.pain_id,
            item.value_potential,
            item.competition_strength,
            item.feasibility,
            item.success_metric,
            item.validation_status,
        )
        for item in items
    ]
    return "## 机会评分\n" + _markdown_table(
        [
            "机会 ID",
            "机会",
            "对应痛点",
            "价值潜力",
            "竞争强度",
            "实现可行性",
            "成功指标",
            "验证状态",
        ],
        rows,
    )


def _render_journey_entry_strategy(items: list[JourneyEntryStrategy]) -> str:
    rows = [
        (
            item.strategy_item,
            item.content,
            item.related_opportunity,
            item.tradeoff_reason,
            item.status,
        )
        for item in items
    ]
    return "## 产品切入策略\n" + _markdown_table(
        ["策略项", "内容", "关联机会", "取舍理由", "状态"],
        rows,
    )


def _render_journey_validation_experiments(
    items: list[JourneyValidationExperiment],
) -> str:
    rows = [
        (
            item.experiment_id,
            item.hypothesis,
            item.opportunity_id,
            item.method,
            item.success_metric,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 验证实验\n" + _markdown_table(
        ["实验 ID", "验证假设", "关联机会", "实验方式", "成功指标", "责任方", "状态"],
        rows,
    )


def _render_journey_summary(summary: JourneySummary) -> str:
    rows = [
        ("核心用户", summary.core_persona),
        ("核心痛点", summary.core_pain),
        ("产品切入策略", summary.entry_strategy),
        ("需求蓝图就绪判断", summary.blueprint_readiness),
    ]
    return "## 旅程摘要\n" + _markdown_table(["字段", "内容"], rows)


def _escape_journey_text(value: str) -> str:
    return value.replace("\n", " ").replace(":", "：").replace("|", "｜")


def _escape_mermaid_time(value: str) -> str:
    return value.replace("\n", " ").replace(":", "：")


def _escape_mermaid_timeline_text(value: str) -> str:
    return value.replace("\n", " ").replace(":", "：").replace("|", "｜")


def _escape_mermaid_mindmap_text(value: str) -> str:
    return (
        value.replace("\n", " ").replace(":", "：").replace("|", "｜").replace('"', "'")
    )


def _render_blueprint_document_info(info: BlueprintDocumentInfo) -> str:
    return render_compact_metadata(
        "## 文档信息",
        (
            ("文档版本", info.version),
            ("创建日期", info.created_at),
            ("Artifact 名称", info.artifact_name),
            ("蓝图状态", info.blueprint_status),
        ),
    )


def _render_blueprint_overview(info: BlueprintDocumentInfo) -> str:
    return "## 需求蓝图概览\n" + _markdown_table(
        ["字段", "内容"],
        [("产品方向", info.product_direction)],
    )


def _render_value_document_info(info: DocumentInfo) -> str:
    return render_compact_metadata(
        "## 文档信息",
        (
            ("Artifact 名称", info.artifact_name),
            ("Workflow", info.workflow),
            ("Stage", info.stage),
            ("状态", info.status),
        ),
    )


def _render_blueprint_product_overview(overview: BlueprintProductOverview) -> str:
    core_value_rows = [
        ("用户价值", overview.user_value),
        ("商业价值", overview.business_value),
        ("商业模式", overview.business_model),
    ]
    return (
        "## 1. 产品概述\n\n"
        "### 1.1 产品愿景\n"
        f"> {overview.vision}\n\n"
        "### 1.2 定位声明\n"
        f"**For** {overview.positioning_for} **who** {overview.positioning_who},\n"
        f"**the** {overview.positioning_product} **is a** "
        f"{overview.positioning_category}\n"
        f"**that** {overview.positioning_value}. **Unlike** "
        f"{overview.positioning_unlike},\n"
        f"**our product** {overview.positioning_differentiator}.\n\n"
        "### 1.3 核心价值\n" + _markdown_table(["维度", "描述"], core_value_rows)
    )


def _render_blueprint_target_users(items: list[BlueprintTargetUser]) -> str:
    rows = [(item.user_type, item.core_pain, item.priority) for item in items]
    return "## 2. 目标用户（摘要）\n" + _markdown_table(
        ["用户类型", "核心痛点", "优先级"], rows
    )


def _render_blueprint_requirements(
    modules: list[BlueprintFeatureModule],
    requirements: list[BlueprintRequirement],
) -> str:
    sections = [
        "## 3. 核心需求",
        "### 功能架构\n" + _render_blueprint_feature_mindmap(modules),
    ]
    headings = [
        ("P0", "### P0 需求（核心功能，必须实现）"),
        ("P1", "### P1 需求（重要功能，应该实现）"),
        ("P2", "### P2 需求（增值功能，可以实现）"),
    ]
    headers = [
        "ID",
        "需求名称",
        "用户故事",
        "对应痛点",
        "范围边界",
        "依赖",
        "验收标准",
        "可测试性等级",
        "owner",
        "状态",
    ]
    for priority, heading in headings:
        rows = [
            (
                item.requirement_id,
                item.name,
                item.user_story,
                item.related_pain,
                item.scope,
                item.dependency,
                item.acceptance,
                item.testability_level,
                item.owner,
                item.status,
            )
            for item in requirements
            if item.priority == priority
        ]
        if not rows:
            rows = [
                ("无", "本轮未规划", "无", "无", "无", "无", "无", "无", "无", "无")
            ]
        sections.append(heading + "\n" + _markdown_table(headers, rows))
    return "\n\n".join(sections)


def _render_blueprint_feature_mindmap(modules: list[BlueprintFeatureModule]) -> str:
    lines = ["```mermaid", "mindmap", '    root(("产品名称"))']
    for module in modules:
        lines.append(f'        ("{_escape_mermaid_label(module.module_name)}")')
        for feature in module.features:
            lines.append(
                f'            ["{_escape_mermaid_label(feature.feature_name)}"]'
            )
    lines.append("```")
    return "\n".join(lines)


def _render_blueprint_main_flow(flow: BlueprintMainFlow) -> str:
    node_lookup = {node.node_id: node for node in flow.nodes}
    existing_ids: dict[str, str] = {}
    safe_ids = {
        node.node_id: _node_id(node.node_id, existing_ids) for node in flow.nodes
    }
    lines = ["```mermaid", "flowchart TD"]
    for node in flow.nodes:
        lines.append(
            f'    {safe_ids[node.node_id]}["{_escape_mermaid_label(node.label)}"]'
        )
    for link in flow.links:
        lines.append(
            f"    {safe_ids[link.from_node]} -->|"
            f'"{_escape_mermaid_label(link.label)}"| {safe_ids[link.to_node]}'
        )
    lines.append("```")
    rows = [
        (
            link.from_node,
            node_lookup[link.from_node].label,
            link.label,
            link.to_node,
            node_lookup[link.to_node].label,
        )
        for link in flow.links
    ]
    return "## 4. 核心流程\n\n" "### 主流程图\n" + "\n".join(
        lines
    ) + "\n\n" + _markdown_table(["起点 ID", "起点", "动作", "终点 ID", "终点"], rows)


def _render_blueprint_success_metrics(
    items: list[BlueprintSuccessMetric],
) -> str:
    rows = [
        (item.metric_type, item.metric_name, item.target, item.measurement)
        for item in items
    ]
    return "## 5. 成功指标\n" + _markdown_table(
        ["指标类型", "指标名称", "目标值", "衡量方式"],
        rows,
    )


def _render_blueprint_mvp_plan(plan: BlueprintMvpPlan) -> str:
    feature_lines = [
        f"- [{'x' if item.included else ' '}] {item.requirement_id}: "
        f"{item.feature_name} — {item.release}"
        for item in plan.included_features
    ]
    iteration_rows = [
        (item.version, item.time, item.core_features, item.goal)
        for item in plan.iterations
    ]
    return (
        "## 6. MVP 范围与计划\n"
        "### MVP 包含功能\n" + "\n".join(feature_lines) + "\n\n"
        "### 迭代路线\n"
        + _markdown_table(["版本", "时间", "核心功能", "目标"], iteration_rows)
    )


def _render_blueprint_non_functional_requirements(
    items: list[BlueprintNonFunctionalRequirement],
) -> str:
    rows = [
        (
            item.type,
            item.description,
            item.metric_or_constraint,
            item.verification,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 7. 非功能需求\n" + _markdown_table(
        ["类型", "需求描述", "指标/约束", "验证方式", "owner", "状态"],
        rows,
    )


def _render_blueprint_acceptance_criteria(
    items: list[BlueprintAcceptanceCriterion],
) -> str:
    rows = [
        (
            item.acceptance_id,
            item.requirement_id,
            item.criterion,
            item.verification,
            item.testability_level,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 8. 验收标准\n" + _markdown_table(
        [
            "验收 ID",
            "关联需求",
            "验收标准",
            "验证方式",
            "可测试性等级",
            "owner",
            "状态",
        ],
        rows,
    )


def _render_blueprint_roadmap(items: list[BlueprintRoadmapItem]) -> str:
    visual = {
        "type": "roadmap",
        "title": "产品迭代路线图",
        "columns": ["版本", "时间", "核心功能", "目标", "成功指标"],
        "rows": [
            {
                "版本": item.version,
                "时间": item.time,
                "核心功能": item.core_features,
                "目标": item.goal,
                "成功指标": item.success_metric,
            }
            for item in items
        ],
    }
    return (
        "## 9. 路线图\n"
        "```ai4se-visual\n" + json.dumps(visual, ensure_ascii=False, indent=2) + "\n```"
    )


def _render_blueprint_risks(items: list[BlueprintRisk]) -> str:
    rows = [
        (
            item.risk_type,
            item.description,
            item.probability,
            item.impact,
            item.mitigation,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 10. 风险评估\n" + _markdown_table(
        ["风险类型", "风险描述", "可能性", "影响", "缓解措施", "owner", "状态"],
        rows,
    )


def _render_blueprint_lisa_handoff_inputs(
    items: list[BlueprintLisaHandoffInput],
) -> str:
    rows = [
        (
            item.input_type,
            item.reference_id,
            item.content,
            item.source,
            item.usage,
            item.status,
        )
        for item in items
    ]
    return "## 11. Lisa Handoff 输入\n" + _markdown_table(
        ["输入类型", "ID", "内容", "来源", "给 Lisa 的用途", "状态"],
        rows,
    )


def _render_blueprint_stage_gate(checks: list[StageGateCheck]) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "## 12. 阶段门禁\n" + "\n".join(lines)


def _markdown_table(headers: list[str], rows: list[tuple[Any, ...]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(_escape_table_cell(cell) for cell in row) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def _escape_table_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _node_id(label: str, existing: dict[str, str]) -> str:
    if label in existing:
        return existing[label]
    base = re.sub(r"[^0-9A-Za-z_]+", "_", label).strip("_")
    if not base or base[0].isdigit():
        base = f"N_{base}" if base else "N"
    candidate = base
    suffix = 2
    while candidate in existing.values():
        candidate = f"{base}_{suffix}"
        suffix += 1
    existing[label] = candidate
    return candidate


def _escape_mermaid_label(value: str) -> str:
    return value.replace('"', "'")
