import copy

import pytest
from pydantic import ValidationError

from agent_contracts import validate_agent_turn
from artifact_data_renderers import (
    CasesArtifactData,
    ClarifyArtifactData,
    DeliveryArtifactData,
    IdeaConceptArtifactData,
    IdeaDefineArtifactData,
    IdeaConvergeArtifactData,
    IdeaDivergeArtifactData,
    IncidentImprovementArtifactData,
    IncidentRootCauseArtifactData,
    IncidentTimelineArtifactData,
    ReqReviewArtifactData,
    ReqReviewReportArtifactData,
    StrategyArtifactData,
    ValueDiscoveryBlueprintArtifactData,
    ValueDiscoveryElevatorArtifactData,
    ValueDiscoveryJourneyArtifactData,
    ValueDiscoveryPersonaArtifactData,
    render_agent_turn_from_artifact_data,
    render_partial_agent_turn_from_artifact_data,
)
from test_asset_parsing import parse_lisa_test_asset_markdown


def _extract_mermaid_block(markdown: str, marker: str) -> str:
    for chunk in markdown.split("```mermaid\n")[1:]:
        block = chunk.split("\n```", 1)[0]
        if marker in block:
            return block
    raise AssertionError(f"Mermaid block not found: {marker}")


VALID_CLARIFY_ARTIFACT_DATA = {
    "document_info": {
        "artifact_name": "测试需求分析与澄清基线",
        "workflow": "TEST_DESIGN",
        "stage": "CLARIFY",
        "status": "可进入策略制定",
    },
    "requirement_facts": [
        {
            "fact_id": "F-001",
            "fact": "用户需要登录功能",
            "source": "用户描述",
            "evidence_level": "用户陈述",
            "status": "已确认",
        }
    ],
    "system_boundaries": [
        {
            "boundary_type": "测试范围",
            "content": "登录页面和登录 API",
            "testing_meaning": "验证登录主链路",
            "status": "已确认",
        }
    ],
    "business_rules": [
        {
            "rule_id": "BR-001",
            "rule": "正确账号密码允许登录",
            "trigger": "用户提交凭证",
            "state_transition": "未登录到已登录",
            "exception_handling": "错误凭证返回错误提示",
            "acceptance": "登录成功进入工作台",
            "status": "已确认",
        }
    ],
    "flow_links": [
        {
            "from_node": "用户",
            "to_node": "登录页",
            "label": "打开登录入口",
        },
        {
            "from_node": "登录页",
            "to_node": "认证服务",
            "label": "提交账号密码",
        },
        {
            "from_node": "认证服务",
            "to_node": "工作台",
            "label": "认证成功",
        },
        {
            "from_node": "认证服务",
            "to_node": "错误提示",
            "label": "认证失败",
        },
    ],
    "clarification_questions": [
        {
            "question_id": "Q-001",
            "question": "连续失败后是否锁定账号",
            "priority": "P1",
            "blocking": "非阻断",
            "impact": "异常登录",
            "assumption": "暂按 5 次失败锁定",
            "owner": "产品",
            "status": "待确认",
        }
    ],
    "quality_requirements": [
        {
            "dimension": "安全",
            "requirement_or_assumption": "防止越权登录",
            "metric": "未授权请求失败",
            "risk": "账号风险",
            "status": "AI 假设",
        }
    ],
    "downstream_inputs": [
        {
            "input_type": "风险种子",
            "input_id": "R-SEED-001",
            "content": "凭证校验失败处理",
            "source": "BR-001",
            "usage": "策略阶段 FMEA",
        }
    ],
    "stage_gate": [
        {
            "checked": True,
            "item": "测试范围和不测范围已明确",
        }
    ],
}

VALID_IDEA_DEFINE_ARTIFACT_DATA = {
    "problem_statement": {
        "target_user": "独立开发者",
        "scenario": "业余时间维护多个小产品并尝试变现",
        "core_pain": "不知道哪个产品方向最值得继续投入",
        "existing_alternative": "凭直觉查看收入、反馈和社群讨论",
        "alternative_gap": "缺少证据化的问题优先级和下一步验证动作",
        "consequence": "继续投入低价值方向，浪费开发时间和获客预算",
        "validation_status": "待验证",
    },
    "target_users": [
        {
            "dimension": "角色定义",
            "description": "每周投入 10 小时以上做副业产品的独立开发者",
            "evidence_level": "用户陈述",
            "validation_status": "部分验证",
        },
        {
            "dimension": "核心痛点",
            "description": "产品方向多但缺少筛选标准，容易反复换方向",
            "evidence_level": "合理推断",
            "validation_status": "待验证",
        },
        {
            "dimension": "付费意愿",
            "description": "愿意为能减少试错时间的工具支付小额订阅",
            "evidence_level": "待验证",
            "validation_status": "待验证",
        },
    ],
    "problem_landscape": {
        "root_problem": "独立开发者变现方向选择困难",
        "subproblems": [
            {
                "problem_id": "P-001",
                "problem": "缺少可比较的问题优先级",
                "symptoms": ["多个想法同时推进", "无法判断先做哪个 MVP"],
            },
            {
                "problem_id": "P-002",
                "problem": "缺少低成本验证动作",
                "symptoms": ["先开发再找用户", "验证周期长且反馈稀疏"],
            },
        ],
    },
    "evidence_items": [
        {
            "evidence_id": "EV-001",
            "related_problem": "独立开发者变现方向选择困难",
            "source": "独立开发者访谈摘要",
            "evidence_level": "用户陈述",
            "validation_action": "访谈 5 位独立开发者并记录当前方向筛选方式",
            "owner": "产品负责人",
            "validation_status": "部分验证",
        },
        {
            "evidence_id": "EV-002",
            "related_problem": "缺少低成本验证动作",
            "source": "社群帖子和产品复盘文章",
            "evidence_level": "合理推断",
            "validation_action": "收集 20 篇变现失败复盘并归类失败原因",
            "owner": "用户研究",
            "validation_status": "待验证",
        },
    ],
    "problem_user_fit": [
        {
            "dimension": "问题是否真实存在？",
            "current_judgement": "是，但仍需扩大样本",
            "evidence_or_assumption": "EV-001 显示多个受访者有方向选择焦虑",
            "evidence_ids": ["EV-001"],
            "validation_action": "补充访谈和问卷验证频率",
            "validation_status": "部分验证",
        },
        {
            "dimension": "用户是否在主动寻求解决方案？",
            "current_judgement": "待验证",
            "evidence_or_assumption": "EV-002 提示社群中有相关讨论",
            "evidence_ids": ["EV-002"],
            "validation_action": "统计社群问题和工具推荐频次",
            "validation_status": "待验证",
        },
    ],
    "constraints_boundaries": [
        {
            "boundary_type": "约束",
            "content": "首轮只能用访谈、问卷和手工分析验证问题真实性",
            "impact": "不先开发复杂自动化产品",
            "status": "已确认",
        },
        {
            "boundary_type": "不可做边界",
            "content": "不替用户直接承诺具体收入增长",
            "impact": "避免把验证工具包装成收益保证",
            "status": "已确认",
        },
    ],
    "reverse_validation": [
        {
            "failure_hypothesis": "目标用户其实更缺流量而不是方向筛选",
            "trigger_signal": "访谈中多数用户提到获客渠道而非方向判断",
            "validation_action": "在访谈中区分方向选择、开发效率和获客问题",
            "validation_status": "待验证",
        }
    ],
    "stage_gate": [
        {"checked": True, "item": "目标用户、核心场景和核心问题已明确。"},
        {"checked": True, "item": "至少一个关键问题有证据等级和验证动作。"},
        {"checked": True, "item": "AI 假设和已验证信息已区分。"},
        {"checked": True, "item": "不可做边界或关键约束已记录。"},
        {"checked": True, "item": "可进入创意发散的 HMW 问题已形成。"},
    ],
}

VALID_IDEA_DIVERGE_ARTIFACT_DATA = {
    "divergence_method": {
        "method_name": "HMW + 类比创新 + 约束反转",
        "goal": "围绕独立开发者方向选择困难发散可验证产品创意",
        "input_basis": "DEFINE 阶段的问题域分析、证据项和约束边界",
        "coverage_dimensions": ["效率提升", "证据收集", "决策辅助"],
        "constraints": "首轮创意必须能在两周内用低代码或人工服务验证",
    },
    "idea_landscape": {
        "root_theme": "独立开发者变现方向选择辅助",
        "groups": [
            {
                "group_id": "G-001",
                "theme": "问题优先级判断",
                "idea_ids": ["ID-001", "ID-002"],
            },
            {
                "group_id": "G-002",
                "theme": "低成本验证动作",
                "idea_ids": ["ID-003"],
            },
        ],
    },
    "idea_cards": [
        {
            "idea_id": "ID-001",
            "title": "方向证据评分卡",
            "one_liner": "把收入、访谈、社群信号转成可比较的问题优先级",
            "target_user": "维护多个副业产品的独立开发者",
            "scenario": "周末复盘多个产品方向并决定下一周投入重点",
            "value_proposition": "减少凭直觉换方向的试错成本",
            "key_hypotheses": ["用户愿意记录每个方向的证据", "证据评分能影响投入决策"],
            "novelty_source": "把 FMEA/ICE 的评分思想迁移到个人产品方向选择",
            "evidence_level": "合理推断",
            "validation_action": "用表格手工服务 5 位开发者并观察是否改变排序",
            "status": "候选",
            "status_reason": "贴合核心问题且验证成本低",
        },
        {
            "idea_id": "ID-002",
            "title": "每周方向复盘助手",
            "one_liner": "用固定问题引导开发者复盘投入、反馈和下周实验",
            "target_user": "有多个待验证想法的独立开发者",
            "scenario": "每周结束时整理本周反馈并生成下一步验证任务",
            "value_proposition": "把混乱反馈转成可执行的验证计划",
            "key_hypotheses": [
                "固定复盘节奏能降低拖延",
                "用户需要下一步动作而不只是总结",
            ],
            "novelty_source": "把项目周报和用户研究复盘结合",
            "evidence_level": "待验证",
            "validation_action": "发放 Notion 模板并追踪 2 周使用留存",
            "status": "候选",
            "status_reason": "适合作为轻量 MVP，但主动使用频率待验证",
        },
        {
            "idea_id": "ID-003",
            "title": "登陆页实验生成器",
            "one_liner": "针对某个方向快速生成登陆页文案和访谈问题",
            "target_user": "准备验证新方向的独立开发者",
            "scenario": "在开发前先发布登陆页并收集早期兴趣",
            "value_proposition": "让验证动作先于开发投入发生",
            "key_hypotheses": ["开发者愿意先做需求验证", "登陆页转化能作为方向信号"],
            "novelty_source": "约束反转：先验证需求，再写产品功能",
            "evidence_level": "合理推断",
            "validation_action": "为 3 个方向生成登陆页并比较报名转化率",
            "status": "候选",
            "status_reason": "能验证低成本实验需求，但实现依赖生成质量",
        },
    ],
    "idea_sources": [
        {
            "source_id": "SRC-001",
            "source_type": "问题域证据",
            "source": "DEFINE 阶段 EV-001：多个受访者有方向选择焦虑",
            "idea_ids": ["ID-001", "ID-002"],
            "key_assumption": "方向选择焦虑可以通过结构化复盘缓解",
            "status_reason": "证据与核心问题直接相关",
        },
        {
            "source_id": "SRC-002",
            "source_type": "约束反转",
            "source": "不先开发复杂产品，先做低成本验证",
            "idea_ids": ["ID-003"],
            "key_assumption": "登陆页实验足以过滤低价值方向",
            "status_reason": "符合首轮低成本验证约束",
        },
    ],
    "parked_or_excluded": [
        {
            "record_id": "PK-001",
            "idea_or_direction": "全自动收入预测引擎",
            "reason": "需要大量真实收入数据，首轮不可获得",
            "revisit_condition": "当用户愿意接入收入和流量数据后再评估",
            "status_reason": "超出当前低成本验证边界",
        }
    ],
    "stage_gate": [
        {"checked": True, "item": "至少形成 3 个可区分创意方向。"},
        {"checked": True, "item": "每个候选创意都有关键假设和验证动作。"},
        {"checked": True, "item": "创意来源和状态理由已记录。"},
        {"checked": True, "item": "高成本或越界方向已搁置或排除。"},
        {"checked": True, "item": "可进入收敛评估的候选集已形成。"},
    ],
}

VALID_IDEA_CONVERGE_ARTIFACT_DATA = {
    "decision_matrix": {
        "scoring_rubric": "优先选择高影响、高信心、低实现难度且能两周内验证的创意",
        "recommended_idea_id": "ID-001",
        "recommendation": "方向证据评分卡",
        "user_confirmation_status": "待确认",
        "decision_items": [
            {
                "idea_id": "ID-001",
                "idea_name": "方向证据评分卡",
                "decision": "推荐方案",
                "reason": "直接命中核心问题，验证成本低，证据收集路径清晰",
                "evidence_source": "SRC-001 / DEFINE EV-001",
            },
            {
                "idea_id": "ID-002",
                "idea_name": "每周方向复盘助手",
                "decision": "备选",
                "reason": "使用频率和主动复盘意愿仍需验证",
                "evidence_source": "SRC-001",
            },
            {
                "idea_id": "ID-003",
                "idea_name": "登陆页实验生成器",
                "decision": "暂缓",
                "reason": "依赖生成质量和投放渠道，首轮验证成本较高",
                "evidence_source": "SRC-002",
            },
        ],
    },
    "ice_evaluations": [
        {
            "idea_id": "ID-001",
            "idea_name": "方向证据评分卡",
            "impact": 5,
            "confidence": 4,
            "effort": 2,
            "ice_score": 10.0,
            "rank": 1,
            "conclusion": "推荐方案",
            "elimination_reason": "不淘汰",
            "evidence_source": "独立开发者访谈摘要",
            "next_validation": "用手工评分卡服务 5 位开发者并观察排序是否改变",
        },
        {
            "idea_id": "ID-002",
            "idea_name": "每周方向复盘助手",
            "impact": 4,
            "confidence": 3,
            "effort": 2,
            "ice_score": 6.0,
            "rank": 2,
            "conclusion": "备选",
            "elimination_reason": "不淘汰，但需先验证复盘频率",
            "evidence_source": "社群复盘讨论",
            "next_validation": "发布 Notion 模板并追踪两周使用留存",
        },
        {
            "idea_id": "ID-003",
            "idea_name": "登陆页实验生成器",
            "impact": 4,
            "confidence": 2,
            "effort": 4,
            "ice_score": 2.0,
            "rank": 3,
            "conclusion": "暂缓",
            "elimination_reason": "验证链路依赖外部流量，首轮成本较高",
            "evidence_source": "约束反转分析",
            "next_validation": "等推荐方案验证后再评估是否需要登陆页实验",
        },
    ],
    "resource_constraints": [
        {
            "constraint_type": "时间",
            "content": "首轮验证必须在两周内完成",
            "impact": "优先选择人工服务或表格原型",
            "handling": "暂不开发完整 SaaS",
            "status": "已确认",
        },
        {
            "constraint_type": "数据",
            "content": "无法直接接入用户收入和流量数据",
            "impact": "评分先基于用户自填和访谈证据",
            "handling": "用证据等级标注不确定性",
            "status": "待确认",
        },
    ],
    "sensitivity_analysis": [
        {
            "variable": "用户愿意记录证据的程度",
            "change": "如果记录意愿低",
            "impact": "方向证据评分卡价值下降",
            "signal": "用户不愿每周填写 5 分钟表格",
            "next_validation": "访谈中测试表格填写意愿并观察试用完成率",
        },
        {
            "variable": "访谈样本是否代表目标用户",
            "change": "如果样本偏向高自律用户",
            "impact": "评分卡对普通独立开发者的适配性下降",
            "signal": "低自律用户试用中断",
            "next_validation": "补充不同经验层级的开发者试用",
        },
    ],
    "validation_experiments": [
        {
            "experiment_id": "EXP-001",
            "idea_ids": ["ID-001"],
            "goal": "验证方向证据评分卡是否改变投入优先级",
            "method": "手工访谈 + 表格评分服务",
            "success_metric": "5 位试用者中至少 3 位调整下一周投入方向",
            "owner": "产品负责人",
            "next_validation": "招募 5 位独立开发者完成一次方向复盘",
            "status": "待执行",
        },
        {
            "experiment_id": "EXP-002",
            "idea_ids": ["ID-002"],
            "goal": "验证每周复盘助手的主动使用频率",
            "method": "发布 Notion 模板并追踪两周复盘提交",
            "success_metric": "两周后至少 40% 试用者完成第二次复盘",
            "owner": "用户研究",
            "next_validation": "作为备选实验排期",
            "status": "待排期",
        },
    ],
    "merge_paths": [
        {
            "path_id": "MERGE-001",
            "source_idea_ids": ["ID-001", "ID-002"],
            "merge_logic": "评分卡负责决策，复盘助手负责持续输入证据",
            "integrated_concept": "方向证据评分卡 + 每周复盘提醒",
            "applicable_condition": "当用户愿意每周持续记录证据时合并",
            "risk": "合并后流程变重，可能降低首次试用完成率",
            "user_confirmation_status": "待确认",
        }
    ],
    "stage_gate": [
        {"checked": True, "item": "已形成至少一个推荐方案。"},
        {"checked": True, "item": "推荐方案有 ICE 评分、证据来源和下一步验证。"},
        {"checked": True, "item": "淘汰或暂缓理由已记录。"},
        {"checked": True, "item": "关键资源约束和敏感性已记录。"},
        {"checked": True, "item": "可进入产品概念简报阶段。"},
    ],
}

VALID_IDEA_CONCEPT_ARTIFACT_DATA = {
    "positioning_statement": {
        "target_user": "维护多个副业产品的独立开发者",
        "user_need": "他们需要用证据选择下一周最值得投入的产品方向",
        "product_name": "方向证据评分卡",
        "category": "轻量级产品方向验证工具",
        "value_proposition": "把访谈、收入和社群信号转成可比较的投入优先级",
        "alternative": "凭直觉复盘、普通 Notion 表格或临时咨询",
        "differentiation": "把 ICE 评分、证据等级和验证实验合成一张决策卡",
    },
    "core_assumptions": [
        {
            "assumption_id": "H-001",
            "assumption": "独立开发者愿意每周记录产品方向证据",
            "source": "DEFINE EV-001 / CONVERGE ID-001",
            "importance": "高",
            "validation_action": "让 5 位开发者用表格完成一次方向复盘",
            "owner": "产品负责人",
            "status": "待验证",
        },
        {
            "assumption_id": "H-002",
            "assumption": "证据评分会改变下一周投入排序",
            "source": "CONVERGE EXP-001",
            "importance": "高",
            "validation_action": "比较使用前后的方向排序变化",
            "owner": "用户研究",
            "status": "待验证",
        },
    ],
    "lean_canvas": [
        {
            "cell": "问题",
            "content": "独立开发者同时推进多个方向，缺少可比较的证据优先级",
        },
        {
            "cell": "用户群体",
            "content": "维护多个副业产品且每周需要取舍投入重点的独立开发者",
        },
        {
            "cell": "独特价值主张",
            "content": "用证据评分替代主观纠结，帮助用户决定下一周投入重点",
        },
        {
            "cell": "解决方案",
            "content": "方向证据评分卡、每周复盘提醒、验证实验建议",
        },
        {
            "cell": "渠道",
            "content": "独立开发者社群、产品复盘文章、模板市场",
        },
        {
            "cell": "收入来源",
            "content": "模板付费、轻量订阅和验证咨询服务",
        },
        {
            "cell": "成本结构",
            "content": "表格原型维护、访谈服务、内容分发和用户支持",
        },
        {
            "cell": "关键指标",
            "content": "复盘完成率、排序变化率、二次使用率、付费转化率",
        },
        {
            "cell": "竞争壁垒",
            "content": "沉淀独立开发者方向证据样本和评分口径",
        },
    ],
    "mvp_features": [
        {
            "module": "核心评分卡",
            "mvp_level": "P0",
            "user_value": "把多个方向放到同一套证据口径中比较",
            "validation_metric": "至少 3/5 试用者调整投入排序",
            "tradeoff_reason": "直接验证定位声明和核心假设",
            "assumption_ids": ["H-001", "H-002"],
            "status": "待验证",
        },
        {
            "module": "验证实验建议",
            "mvp_level": "P1",
            "user_value": "把评分结果转成下一步实验",
            "validation_metric": "至少 2 位试用者执行建议实验",
            "tradeoff_reason": "提升行动转化，但可先人工生成",
            "assumption_ids": ["H-002"],
            "status": "待排期",
        },
        {
            "module": "每周复盘提醒",
            "mvp_level": "P2",
            "user_value": "持续收集证据形成习惯",
            "validation_metric": "两周后 40% 试用者完成第二次复盘",
            "tradeoff_reason": "验证成本高于核心评分卡，先不放首轮",
            "assumption_ids": ["H-001"],
            "status": "暂缓",
        },
    ],
    "growth_funnel": [
        {
            "stage": "Acquisition",
            "user_behavior": "从独立开发者社群或复盘文章进入模板介绍页",
            "metric": "模板访问数",
            "mvp_implementation": "发布评分卡样例和使用前后对比",
        },
        {
            "stage": "Activation",
            "user_behavior": "填入 2 到 3 个产品方向并完成首次评分",
            "metric": "首次评分完成率",
            "mvp_implementation": "提供手工表格和引导问题",
        },
        {
            "stage": "Retention",
            "user_behavior": "一周后回到评分卡更新证据",
            "metric": "7 日复盘率",
            "mvp_implementation": "人工提醒和复盘邮件",
        },
        {
            "stage": "Revenue",
            "user_behavior": "购买进阶模板或验证咨询",
            "metric": "付费转化率",
            "mvp_implementation": "提供一次人工复盘服务",
        },
        {
            "stage": "Referral",
            "user_behavior": "分享方向排序结果或复盘模板",
            "metric": "分享率",
            "mvp_implementation": "输出可复制的复盘摘要",
        },
    ],
    "premortem_risks": [
        {
            "risk_id": "R-001",
            "dimension": "市场风险",
            "failure_reason": "用户愿意讨论方向选择，但不愿持续记录证据",
            "likelihood": "高",
            "mitigation": "首轮只要求一次 15 分钟复盘，验证最低记录成本",
        },
        {
            "risk_id": "R-002",
            "dimension": "产品风险",
            "failure_reason": "评分结果不能明显改变投入决策",
            "likelihood": "中",
            "mitigation": "把排序变化作为核心成功指标",
        },
    ],
    "validation_roadmap": [
        {
            "validation_id": "V0",
            "stage": "问题验证",
            "goal": "确认方向选择困难真实且高频",
            "experiment": "访谈 5 位独立开发者",
            "success_metric": "至少 4 位每月经历方向取舍",
            "time_window": "1 周",
            "owner": "用户研究",
            "status": "待执行",
            "assumption_ids": ["H-001"],
        },
        {
            "validation_id": "V1",
            "stage": "价值验证",
            "goal": "确认评分卡能改变投入排序",
            "experiment": "手工表格评分服务",
            "success_metric": "至少 3/5 试用者调整下一周投入重点",
            "time_window": "2 周",
            "owner": "产品负责人",
            "status": "待执行",
            "assumption_ids": ["H-002"],
        },
    ],
    "out_of_scope": [
        {
            "item": "自动接入收入和流量数据",
            "reason": "首轮验证无需接入外部账号且用户授权成本高",
            "reconsider_condition": "当 5 位试用者都愿意持续使用评分卡后再评估",
            "status": "已确认",
        }
    ],
    "decision_records": [
        {
            "decision": "推荐概念",
            "conclusion": "优先验证方向证据评分卡",
            "basis": "CONVERGE 阶段 ID-001 ICE 得分最高且验证成本最低",
            "decider": "产品负责人",
            "date": "2026-06-23",
            "status": "待确认",
        }
    ],
    "next_actions": [
        {
            "action_id": "ACT-001",
            "action": "招募 5 位独立开发者完成首次评分卡复盘",
            "related_ids": ["H-001", "V0"],
            "owner": "用户研究",
            "due_date": "2026-06-30",
            "acceptance": "完成访谈记录并确认是否存在方向取舍痛点",
            "status": "待开始",
        },
        {
            "action_id": "ACT-002",
            "action": "运行手工评分服务并记录排序变化",
            "related_ids": ["H-002", "V1", "R-002"],
            "owner": "产品负责人",
            "due_date": "2026-07-07",
            "acceptance": "至少 3 位试用者调整下一周投入排序",
            "status": "待开始",
        },
    ],
    "stage_gate": [
        {"checked": True, "item": "定位声明能在 3 秒内说明目标用户、品类和核心价值。"},
        {"checked": True, "item": "MVP 功能能验证至少一个核心假设。"},
        {"checked": True, "item": "验证路线有成功指标、owner 和状态。"},
        {"checked": True, "item": "不可做范围和决策记录已明确。"},
        {"checked": True, "item": "下一步行动具备 owner、截止时间、验收标准和状态。"},
    ],
}

VALID_INCIDENT_TIMELINE_ARTIFACT_DATA = {
    "incident_summary": {
        "incident_name": "支付回调失败导致订单状态延迟",
        "severity": "P1",
        "detected_at": "2026-06-23 14:30",
        "recovered_at": "2026-06-23 14:50",
        "duration": "20 分钟",
        "impact_scope": "支付成功用户的订单状态同步延迟",
        "current_status": "已恢复",
    },
    "impact_metrics": [
        {
            "dimension": "用户影响",
            "quantification": "约 120 笔订单状态延迟更新",
            "confidence": "中",
            "source": "订单监控和客服工单",
            "status": "待确认",
        },
        {
            "dimension": "业务影响",
            "quantification": "未发现实际扣款失败，主要影响订单展示",
            "confidence": "中",
            "source": "支付平台对账和业务监控",
            "status": "待确认",
        },
    ],
    "fact_sources": [
        {
            "fact_id": "FACT-001",
            "fact": "14:30 订单状态延迟告警触发",
            "source": "监控告警",
            "confidence": "高",
            "status": "已确认",
        },
        {
            "fact_id": "FACT-002",
            "fact": "14:37 值班同学重启回调消费者",
            "source": "值班记录",
            "confidence": "中",
            "status": "待确认",
        },
        {
            "fact_id": "FACT-003",
            "fact": "14:50 订单延迟队列恢复到正常水位",
            "source": "监控面板",
            "confidence": "高",
            "status": "已确认",
        },
    ],
    "timeline_events": [
        {
            "section": "故障发生",
            "occurred_at": "14:30",
            "event": "订单状态延迟告警触发",
            "fact_ids": ["FACT-001"],
        },
        {
            "section": "发现与响应",
            "occurred_at": "14:35",
            "event": "值班同学确认支付回调堆积",
            "fact_ids": ["FACT-001"],
        },
        {
            "section": "处理与恢复",
            "occurred_at": "14:37",
            "event": "重启回调消费者并观察队列水位",
            "fact_ids": ["FACT-002"],
        },
        {
            "section": "恢复确认",
            "occurred_at": "14:50",
            "event": "订单延迟队列恢复到正常水位",
            "fact_ids": ["FACT-003"],
        },
    ],
    "fact_separation": [
        {
            "item_type": "事实",
            "content": "告警、重启操作和队列水位恢复均有来源记录。",
            "handling": "纳入事实摘要和时间线",
            "blocking": "否",
            "status": "已确认",
        },
        {
            "item_type": "推测",
            "content": "可能是上游支付平台回调抖动。",
            "handling": "移入根因分析阶段验证",
            "blocking": "否",
            "status": "待确认",
        },
        {
            "item_type": "待确认",
            "content": "实际受影响订单数需要数据仓库复核。",
            "handling": "补充订单查询结果",
            "blocking": "非阻断",
            "status": "待补充",
        },
    ],
    "fact_summary": [
        "2026-06-23 14:30，支付回调相关订单状态延迟告警触发。",
        "值班同学确认存在回调堆积，并在 14:37 重启回调消费者。",
        "14:50，订单延迟队列恢复到正常水位，当前状态为已恢复。",
    ],
    "participants": [
        {
            "role": "发现者",
            "person": "监控系统",
            "action": "触发订单状态延迟告警",
            "participated_at": "14:30",
            "status": "已确认",
        },
        {
            "role": "一线响应",
            "person": "支付值班同学",
            "action": "确认堆积并重启回调消费者",
            "participated_at": "14:35-14:37",
            "status": "待确认",
        },
    ],
    "missing_information": [
        {
            "item": "最终受影响订单数",
            "reason": "影响量化和严重等级确认需要精确数据",
            "supplement_method": "查询订单状态延迟记录和客服工单",
            "blocking": "非阻断",
            "owner": "数据分析",
            "status": "待补充",
        }
    ],
    "stage_gate": [
        {
            "checked": True,
            "item": "故障表现、发现时间、恢复时间和当前状态已记录。",
        },
        {
            "checked": True,
            "item": "影响范围和影响量化已记录，或明确标注为待补充。",
        },
        {"checked": True, "item": "关键事实有来源和可信度。"},
        {"checked": True, "item": "推测未混入事实摘要。"},
        {"checked": True, "item": "阻断进入根因分析的信息已明确列出。"},
    ],
}

VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA = {
    "analysis_context": {
        "incident_name": "支付回调失败导致订单状态延迟",
        "scope": "基于事件还原阶段已确认的告警、回调堆积和恢复记录分析根因",
        "upstream_facts": "14:30 告警触发，14:37 重启回调消费者，14:50 队列恢复。",
        "current_judgement": "初步判断故障与回调消费者缺少积压保护和发布前回归门禁有关。",
    },
    "why_chain": [
        {
            "level": "现象",
            "question": "发生了什么？",
            "answer": "支付成功后订单状态延迟同步，队列在 20 分钟后恢复。",
            "cause_type": "现象",
            "evidence": "FACT-001 / FACT-003",
            "evidence_strength": "高",
            "confidence": "高",
            "actionability": "不适用",
            "verification_status": "已确认",
        },
        {
            "level": "Why-1",
            "question": "为什么订单状态会延迟同步？",
            "answer": "支付回调消费者出现堆积，无法及时处理回调消息。",
            "cause_type": "技术",
            "evidence": "队列水位监控和重启记录",
            "evidence_strength": "高",
            "confidence": "高",
            "actionability": "可行动",
            "verification_status": "已确认",
        },
        {
            "level": "Why-2",
            "question": "为什么消费者堆积没有被自动削峰或告警前置拦截？",
            "answer": "回调消费者缺少积压保护和自动扩容策略。",
            "cause_type": "技术",
            "evidence": "消费者配置和监控告警策略",
            "evidence_strength": "中",
            "confidence": "中",
            "actionability": "可行动",
            "verification_status": "待验证",
        },
        {
            "level": "Why-3",
            "question": "为什么发布前没有发现消费者保护缺口？",
            "answer": "发布前缺少支付回调关键路径容量回归门禁。",
            "cause_type": "流程",
            "evidence": "发布检查清单未覆盖回调堆积场景",
            "evidence_strength": "中",
            "confidence": "中",
            "actionability": "可行动",
            "verification_status": "待验证",
        },
    ],
    "cause_evidence": [
        {
            "cause_id": "CAUSE-001",
            "cause": "支付回调消费者出现堆积",
            "related_level": "Why-1",
            "evidence": "队列水位监控和重启记录",
            "evidence_strength": "高",
            "confidence": "高",
            "actionability": "可行动",
            "verification_status": "已确认",
        },
        {
            "cause_id": "CAUSE-002",
            "cause": "回调消费者缺少积压保护和自动扩容策略",
            "related_level": "Why-2",
            "evidence": "消费者配置和监控告警策略",
            "evidence_strength": "中",
            "confidence": "中",
            "actionability": "可行动",
            "verification_status": "待验证",
        },
        {
            "cause_id": "CAUSE-003",
            "cause": "发布前缺少支付回调关键路径容量回归门禁",
            "related_level": "Why-3",
            "evidence": "发布检查清单未覆盖回调堆积场景",
            "evidence_strength": "中",
            "confidence": "中",
            "actionability": "可行动",
            "verification_status": "待验证",
        },
    ],
    "fishbone_categories": [
        {
            "category": "技术",
            "causes": ["回调消费者缺少积压保护", "缺少自动扩容策略"],
            "cause_ids": ["CAUSE-001", "CAUSE-002"],
        },
        {
            "category": "流程",
            "causes": ["发布前容量回归门禁缺失"],
            "cause_ids": ["CAUSE-003"],
        },
    ],
    "root_cause_conclusions": [
        {
            "conclusion_type": "直接原因",
            "description": "支付回调消费者堆积导致订单状态延迟同步。",
            "category": "技术",
            "related_cause_id": "CAUSE-001",
            "evidence_strength": "高",
            "confidence": "高",
            "actionability": "可行动",
            "verification_status": "已确认",
        },
        {
            "conclusion_type": "根本原因",
            "description": "支付回调关键路径缺少容量回归门禁和积压保护机制。",
            "category": "流程",
            "related_cause_id": "CAUSE-003",
            "evidence_strength": "中",
            "confidence": "中",
            "actionability": "可行动",
            "verification_status": "待验证",
        },
        {
            "conclusion_type": "促成因素",
            "description": "监控告警只在订单状态延迟后触发，缺少更早的队列积压预警。",
            "category": "度量",
            "related_cause_id": "CAUSE-002",
            "evidence_strength": "中",
            "confidence": "中",
            "actionability": "可行动",
            "verification_status": "待验证",
        },
    ],
    "excluded_causes": [
        {
            "exclusion_id": "EX-001",
            "suspected_cause": "支付平台实际扣款失败",
            "basis": "支付平台对账未发现扣款失败，主要影响订单状态展示。",
            "evidence_strength": "中",
            "still_monitor": "是",
        }
    ],
    "unverified_causes": [
        {
            "cause": "上游支付平台回调短时抖动",
            "reason": "当前只有内部队列和订单侧证据，缺少上游平台回调日志。",
            "possible_impact": "若成立，需要补充第三方回调重试和超时保护。",
            "verification_action": "拉取支付平台回调日志并与队列堆积时间对齐。",
            "owner": "支付研发",
            "status": "待验证",
        }
    ],
    "stage_gate": [
        {"checked": True, "item": "至少完成 3 层 5-Why 追问。"},
        {"checked": True, "item": "根本原因具有可行动性，或明确说明不可行动原因。"},
        {"checked": True, "item": "鱼骨图至少覆盖 2 个相关原因维度。"},
        {"checked": True, "item": "关键根因有证据强度、置信度和验证状态。"},
        {"checked": True, "item": "排除项和未验证原因已记录。"},
    ],
}

VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA = {
    "report_info": {
        "incident_name": "支付回调失败导致订单状态延迟",
        "severity": "P1",
        "version": "v1.0",
        "generated_at": "2026-06-23 16:30",
        "action_count": 3,
        "review_date": "2026-07-07",
        "closure_status": "待复查",
    },
    "timeline_summary": {
        "key_events": [
            "14:30 订单状态延迟告警触发",
            "14:37 重启支付回调消费者",
            "14:50 队列水位恢复正常",
        ],
        "impact_summary": "约 120 笔订单状态延迟更新，未发现实际扣款失败。",
        "recovery_summary": "通过重启回调消费者恢复处理能力，并确认延迟队列恢复。",
    },
    "root_cause_summary": {
        "direct_cause": "支付回调消费者堆积导致订单状态延迟同步。",
        "root_cause": "支付回调关键路径缺少容量回归门禁和积压保护机制。",
        "contributing_factors": [
            "监控告警只在订单状态延迟后触发",
            "发布检查清单未覆盖回调堆积场景",
        ],
        "evidence_summary": "队列水位监控、重启记录和发布检查清单共同支撑结论。",
    },
    "priority_distribution": {
        "urgent_count": 1,
        "important_count": 1,
        "normal_count": 1,
    },
    "improvement_actions": [
        {
            "action_id": "A-001",
            "improvement": "为支付回调消费者增加积压保护和自动扩容策略",
            "action_type": "纠正措施",
            "root_cause_id": "CAUSE-002",
            "root_cause_type": "技术",
            "owner": "支付研发",
            "deadline": "2026-06-30",
            "verification_method": "压测回调队列并验证扩容触发",
            "acceptance_criteria": "队列积压达到阈值后 2 分钟内自动扩容且无订单状态延迟告警",
            "priority": "紧急",
            "status": "待执行",
            "tracking_method": "故障改进行动看板每日报告",
        },
        {
            "action_id": "A-002",
            "improvement": "将支付回调容量回归纳入发布门禁",
            "action_type": "预防措施",
            "root_cause_id": "CAUSE-003",
            "root_cause_type": "流程",
            "owner": "测试负责人",
            "deadline": "2026-07-03",
            "verification_method": "检查发布流水线是否阻断未完成容量回归的版本",
            "acceptance_criteria": "支付回调相关变更必须附带容量回归结果才可发布",
            "priority": "重要",
            "status": "待执行",
            "tracking_method": "发布门禁记录和复盘复查会",
        },
        {
            "action_id": "A-003",
            "improvement": "补充支付回调队列积压前置预警",
            "action_type": "监控改进",
            "root_cause_id": "CAUSE-002",
            "root_cause_type": "技术",
            "owner": "SRE",
            "deadline": "2026-07-05",
            "verification_method": "模拟队列积压并确认预警早于订单延迟告警触发",
            "acceptance_criteria": "队列积压预警至少提前 5 分钟触达值班群",
            "priority": "常规",
            "status": "待执行",
            "tracking_method": "监控规则变更单和告警演练记录",
        },
    ],
    "root_cause_coverage": [
        {
            "cause_id": "CAUSE-002",
            "cause_type": "技术",
            "description": "缺少积压保护、自动扩容和前置预警",
            "action_ids": ["A-001", "A-003"],
            "coverage_status": "已覆盖",
            "uncovered_reason": "不适用",
            "risk_acceptor": "支付研发负责人",
        },
        {
            "cause_id": "CAUSE-003",
            "cause_type": "流程",
            "description": "发布前缺少支付回调关键路径容量回归门禁",
            "action_ids": ["A-002"],
            "coverage_status": "已覆盖",
            "uncovered_reason": "不适用",
            "risk_acceptor": "测试负责人",
        },
    ],
    "prevention_checklist": [
        {
            "item": "支付回调容量回归是否完成",
            "related_cause_id": "CAUSE-003",
            "owner": "测试负责人",
            "status": "待纳入发布门禁",
        },
        {
            "item": "队列积压保护和前置告警是否启用",
            "related_cause_id": "CAUSE-002",
            "owner": "SRE",
            "status": "待验证",
        },
    ],
    "review_plan": [
        {
            "review_item": "改进行动完成复查",
            "review_date": "2026-07-07",
            "reviewer": "事故复盘主持人",
            "evidence": "行动看板、发布门禁记录、压测报告、告警演练记录",
            "pass_criteria": "所有行动项完成且验收标准通过",
            "status": "待复查",
        }
    ],
    "residual_risks": [
        {
            "risk_id": "RR-001",
            "risk": "第三方支付平台短时回调抖动仍可能造成局部延迟",
            "impact": "少量订单状态展示延迟",
            "acceptance_reason": "第三方日志仍需补齐，先通过内部积压保护降低影响",
            "risk_acceptor": "支付业务负责人",
            "review_due_date": "2026-07-14",
            "status": "有条件接受",
        }
    ],
    "lessons_learned": [
        {
            "lesson_id": "L-001",
            "lesson": "高频支付回调链路必须同时具备容量回归、积压保护和前置告警。",
            "scope": "支付、订单、消息队列相关关键路径",
            "sharing_suggestion": "纳入季度故障案例复盘",
        }
    ],
    "organizational_learning": [
        {
            "learning_item": "更新关键链路发布门禁模板",
            "audience": "研发、测试、SRE",
            "channel": "工程效能例会",
            "owner": "质量负责人",
            "due_date": "2026-07-10",
            "status": "待宣导",
        }
    ],
    "signoffs": [
        {
            "role": "事故复盘主持人",
            "owner": "Oncall Lead",
            "confirmation": "复盘报告内容完整且行动项可追踪",
            "status": "待签署",
        },
        {
            "role": "业务负责人",
            "owner": "支付业务负责人",
            "confirmation": "遗留风险已明确接受人与复查期限",
            "status": "待签署",
        },
    ],
    "stage_gate": [
        {"checked": True, "item": "每个根因至少有一项对应改进措施或风险接受说明。"},
        {"checked": True, "item": "改进行动具备负责人、期限、验证方式和验收标准。"},
        {"checked": True, "item": "复查计划和遗留风险接受人已记录。"},
    ],
}

VALID_STRATEGY_ARTIFACT_DATA = {
    "document_info": {
        "artifact_name": "风险驱动测试策略蓝图",
        "workflow": "TEST_DESIGN",
        "stage": "STRATEGY",
        "status": "可进入用例编写",
    },
    "strategy_summary": {
        "conclusion": "围绕登录主链路采用风险驱动策略，优先覆盖认证失败、锁定策略和越权风险。",
        "basis": "F-001 / BR-001 / R-SEED-001 / Q-001",
        "case_stage_readiness": "可进入",
    },
    "quality_goals": [
        {
            "goal_id": "QG-001",
            "goal": "核心登录链路正确性",
            "metric": "正确凭证登录成功率 100%，错误凭证均给出明确提示",
            "source": "F-001 / BR-001",
            "priority": "P0",
            "status": "已确认",
        }
    ],
    "risks": [
        {
            "risk_id": "R-001",
            "name": "错误凭证绕过认证",
            "failure_mode": "认证服务未正确拒绝错误密码",
            "impact": "未授权用户进入工作台",
            "source": "BR-001",
            "severity": 5,
            "occurrence": 3,
            "detection": 4,
            "rpn": 60,
            "mitigation": "增加负向认证和越权断言",
            "coverage": "P0 测试点覆盖错误凭证、空密码和锁定后重试",
            "status": "待覆盖",
        }
    ],
    "test_techniques": [
        {
            "technique_id": "TS-001",
            "target": "QG-001 / R-001",
            "category": "设计技术",
            "technique": "等价类 + 边界值 + 状态迁移",
            "reason": "登录凭证和账号锁定同时涉及输入分类和状态变化",
            "applies_to": "R-001 / TP-001",
        }
    ],
    "test_layers": [
        {
            "layer": "单元测试",
            "ratio": "40%",
            "scope": "认证规则、失败计数和锁定状态",
            "related": "R-001 / TP-001",
            "tools": "pytest",
            "entry_condition": "认证逻辑可注入用户状态",
        },
        {
            "layer": "集成测试",
            "ratio": "40%",
            "scope": "登录 API、会话和用户库交互",
            "related": "R-001 / TP-002",
            "tools": "pytest + Flask test client",
            "entry_condition": "测试库和账号夹具可用",
        },
        {
            "layer": "E2E 测试",
            "ratio": "20%",
            "scope": "用户从登录页进入工作台",
            "related": "QG-001 / TP-003",
            "tools": "Playwright",
            "entry_condition": "稳定测试账号和浏览器环境可用",
        },
    ],
    "test_points": [
        {
            "point_id": "TP-001",
            "point": "错误凭证必须被拒绝",
            "priority": "P0",
            "quality_goal": "QG-001",
            "risk": "R-001",
            "technique": "TS-001 等价类",
            "layer": "单元/集成",
            "estimated_cases": 6,
            "coverage": "覆盖空密码、错误密码、锁定前后重试",
            "status": "待生成用例",
        }
    ],
    "tradeoffs": [
        {
            "item": "E2E 覆盖比例",
            "decision": "保留主链路和一个失败路径",
            "impact": "降低端到端维护成本，同时保留关键用户路径信心",
            "owner": "测试负责人",
            "status": "AI 假设",
        }
    ],
    "stage_gate": [
        {
            "checked": True,
            "item": "所有 P0 风险都有覆盖建议",
        },
        {
            "checked": True,
            "item": "测试点拓扑能追溯到质量目标、风险或澄清阶段输入",
        },
    ],
}

VALID_CASES_ARTIFACT_DATA = {
    "document_info": {
        "artifact_name": "登录功能测试用例集",
        "workflow": "TEST_DESIGN",
        "stage": "CASES",
        "status": "可进入交付汇总",
    },
    "case_statistics": {
        "total": 2,
        "p0_count": 1,
        "p1_count": 1,
        "p2_count": 0,
    },
    "design_bases": [
        {
            "basis_id": "BASIS-001",
            "source_type": "测试点",
            "source_id": "TP-001",
            "basis": "错误凭证必须被拒绝且不能创建登录会话",
            "case_direction": "异常与边界值",
        }
    ],
    "case_groups": [
        {
            "dimension": "正向功能验证",
            "cases": [
                {
                    "case_id": "TC-001",
                    "title": "用户使用正确密码登录成功",
                    "priority": "P0",
                    "dimension": "正向功能验证",
                    "test_point": "登录主链路",
                    "risk": "R-LOGIN-001",
                    "precondition": "用户已注册且账号可用",
                    "steps": "1. 打开登录页 2. 输入正确账号密码 3. 点击登录",
                    "test_data": "user@example.com / 正确密码",
                    "expected_result": "跳转到工作台",
                    "assertion": "工作台 URL、用户昵称和登录态均正确",
                    "execution_layer": "E2E",
                    "automation_suggestion": "优先自动化",
                    "status": "可执行",
                }
            ],
        },
        {
            "dimension": "异常与边界值",
            "cases": [
                {
                    "case_id": "TC-002",
                    "title": "密码错误时提示失败",
                    "priority": "P1",
                    "dimension": "异常与边界值",
                    "test_point": "登录错误处理",
                    "risk": "R-LOGIN-002",
                    "precondition": "用户已注册且账号未锁定",
                    "steps": "1. 输入正确账号 2. 输入错误密码 3. 点击登录",
                    "test_data": "user@example.com / 错误密码",
                    "expected_result": "显示密码错误提示",
                    "assertion": "错误提示文案出现且不会创建登录会话",
                    "execution_layer": "E2E",
                    "automation_suggestion": "可自动化",
                    "status": "可执行",
                }
            ],
        },
    ],
    "test_data_environments": [
        {
            "data_id": "DATA-001",
            "type": "测试账号",
            "content": "已注册普通用户账号",
            "preparation": "测试环境预置",
            "related_cases": "TC-001, TC-002",
            "status": "已具备",
        }
    ],
    "automation_candidates": [
        {
            "candidate_id": "AUTO-001",
            "case_id": "TC-001",
            "recommended_layer": "E2E",
            "value": "核心登录链路高频回归",
            "prerequisite": "稳定测试账号和浏览器环境",
            "risk_or_limit": "需要隔离登录态",
            "status": "推荐",
        }
    ],
    "coverage_trace": [
        {
            "test_point": "登录主链路",
            "priority": "P0",
            "risk": "R-LOGIN-001",
            "covered_cases": ["TC-001"],
            "status": "已覆盖",
        },
        {
            "test_point": "登录错误处理",
            "priority": "P1",
            "risk": "R-LOGIN-002",
            "covered_cases": ["TC-002"],
            "status": "部分覆盖",
        },
    ],
    "open_questions": [
        {
            "question_id": "CASE-Q-001",
            "question": "连续错误密码后是否锁定账号",
            "related": "TC-002 / 登录错误处理",
            "priority": "P1",
            "blocking": "非阻断",
            "owner": "产品",
            "status": "待确认",
        }
    ],
    "stage_gate": [
        {
            "checked": True,
            "item": "所有 P0 测试点都有至少一条用例覆盖",
        },
        {
            "checked": True,
            "item": "每条用例都有测试数据、预期结果和断言",
        },
    ],
}

VALID_DELIVERY_ARTIFACT_DATA = {
    "document_info": {
        "artifact_name": "登录功能测试设计交付评审文档",
        "workflow": "TEST_DESIGN",
        "stage": "DELIVERY",
        "status": "可签署",
    },
    "delivery_metrics": {
        "project_name": "登录功能",
        "version": "v1.0",
        "generated_at": "2026-06-23",
        "delivery_status": "可签署",
        "total_cases": 2,
        "high_risk_count": 1,
    },
    "executive_summary": [
        {
            "summary_item": "测试范围",
            "conclusion": "覆盖登录页面、登录 API、认证服务和登录态创建。",
            "evidence_source": "CLARIFY / STRATEGY / CASES",
            "status": "已确认",
        },
        {
            "summary_item": "交付判断",
            "conclusion": "P0 登录主链路可进入评审，账号锁定策略需作为非阻断风险确认。",
            "evidence_source": "阶段门禁",
            "status": "可签署",
        },
    ],
    "requirement_summary": [
        {
            "content_type": "事实",
            "reference": "F-001",
            "conclusion": "用户需要通过正确账号密码登录进入工作台。",
            "open_status": "已确认",
        },
        {
            "content_type": "澄清问题",
            "reference": "Q-001",
            "conclusion": "连续错误密码后是否锁定账号仍需产品确认。",
            "open_status": "待确认",
        },
    ],
    "strategy_summary_items": [
        {
            "strategy_item": "高风险项",
            "conclusion": "错误凭证绕过认证为 P0 风险，必须由负向认证用例覆盖。",
            "related": "R-001 / TP-001",
            "coverage_status": "已覆盖",
        },
        {
            "strategy_item": "测试分层",
            "conclusion": "单元、集成、E2E 分层覆盖认证规则、API 会话和用户主链路。",
            "related": "TP-001 / TP-002 / TP-003",
            "coverage_status": "已确认",
        },
    ],
    "case_summary_items": [
        {
            "dimension": "正向功能验证",
            "case_count": 1,
            "p0_count": 1,
            "p1_count": 0,
            "p2_count": 0,
            "automation_candidates": 1,
            "blocked_or_needs_env": 0,
        },
        {
            "dimension": "异常与边界值",
            "case_count": 1,
            "p0_count": 0,
            "p1_count": 1,
            "p2_count": 0,
            "automation_candidates": 0,
            "blocked_or_needs_env": 0,
        },
    ],
    "coverage_map": [
        {
            "requirement": "REQ-登录",
            "risk": "R-LOGIN-001",
            "test_point": "登录主链路",
            "case_ids": ["TC-001"],
            "acceptance_status": "已覆盖",
        },
        {
            "requirement": "REQ-登录",
            "risk": "R-LOGIN-002",
            "test_point": "登录错误处理",
            "case_ids": ["TC-002"],
            "acceptance_status": "部分覆盖",
        },
    ],
    "open_risks": [
        {
            "risk_id": "OPEN-001",
            "risk_type": "风险接受",
            "description": "账号锁定策略尚未由产品确认。",
            "impact": "锁定前后重试路径只能按 AI 假设覆盖。",
            "acceptable": "否",
            "owner": "产品",
            "next_step": "确认连续失败次数和解锁方式。",
            "status": "待处理",
        }
    ],
    "acceptance_checklist": [
        {
            "checked": True,
            "item": "所有 P0 风险均有用例覆盖或风险接受结论",
        },
        {
            "checked": True,
            "item": "coverage-map 中需求、风险、测试点、用例、验收状态可追溯",
        },
    ],
    "signoffs": [
        {
            "role": "产品负责人",
            "owner": "产品",
            "opinion": "有条件通过",
            "status": "待签署",
        },
        {
            "role": "测试负责人",
            "owner": "测试",
            "opinion": "通过",
            "status": "待签署",
        },
    ],
    "change_log": [
        {
            "version": "v1.0",
            "date": "2026-06-23",
            "change": "首次生成测试设计交付文档",
            "reason": "完成测试设计阶段交付",
            "owner": "Lisa",
        }
    ],
}

VALID_REQ_REVIEW_ARTIFACT_DATA = {
    "review_info": {
        "artifact_name": "需求质量诊断与评审问题清单",
        "requirement_name": "会员权益需求",
        "review_date": "2026-06-23",
        "requirement_summary": "会员可在权益中心查看、领取和使用优惠权益，系统需要明确领取限制、使用规则和异常处理。",
        "conclusion": "存在阻断问题，需补充关键业务规则后进入报告阶段。",
    },
    "scope_items": [
        {
            "scope_type": "评审范围",
            "content": "权益展示、领取、使用和失效流程",
            "review_impact": "纳入问题扫描和测试风险评估",
            "status": "已确认",
        },
        {
            "scope_type": "不评审范围",
            "content": "营销投放策略和财务结算",
            "review_impact": "避免将运营策略误判为需求缺口",
            "status": "AI 假设",
        },
    ],
    "quality_overview": [
        {
            "dimension": "可测试性",
            "quality_judgement": "严重缺失",
            "severity_score": 5,
            "evidence": "验收标准未说明每种权益状态的可见性和断言口径",
            "testing_risk": "测试用例无法稳定判断展示结果是否正确",
            "status": "待 PM 确认",
        },
        {
            "dimension": "边界与规则定义",
            "quality_judgement": "部分缺失",
            "severity_score": 4,
            "evidence": "领取次数、过期时间和重复领取规则未定义",
            "testing_risk": "边界值和异常路径可能漏测",
            "status": "待 PM 确认",
        },
    ],
    "issue_statistics": {
        "p0_count": 1,
        "p1_count": 1,
        "p2_count": 0,
        "p0_description": "必须在开发前解答，否则无法测试",
        "p1_description": "建议在开发前明确，否则可能返工",
        "p2_description": "优化性建议，可排入后续迭代",
    },
    "issue_groups": [
        {
            "dimension": "可测试性",
            "issues": [
                {
                    "issue_id": "Q-001",
                    "dimension": "可测试性",
                    "description": "权益状态缺少可验收的展示断言。",
                    "priority": "P0",
                    "blocking": "阻断",
                    "requirement_section": "权益中心展示",
                    "impact": "影响权益展示主链路测试设计",
                    "evidence": "PRD 只写展示可用权益，未定义已领取、已过期、不可用状态",
                    "suggestion": "补充每种权益状态的展示字段、排序和空态验收标准",
                    "owner": "PM",
                    "status": "待 PM 确认",
                }
            ],
        },
        {
            "dimension": "边界与规则定义",
            "issues": [
                {
                    "issue_id": "Q-002",
                    "dimension": "边界与规则定义",
                    "description": "领取次数和过期时间缺少边界规则。",
                    "priority": "P1",
                    "blocking": "非阻断",
                    "requirement_section": "权益领取规则",
                    "impact": "影响边界值和异常路径覆盖",
                    "evidence": "PRD 未说明同一用户每日、每周期或总领取次数",
                    "suggestion": "明确领取次数、过期时间和重复领取提示",
                    "owner": "PM / 研发",
                    "status": "待 PM 确认",
                }
            ],
        },
    ],
    "revision_suggestions": [
        {
            "suggestion_id": "FIX-001",
            "related_issues": ["Q-001"],
            "suggestion": "补充权益状态展示验收标准表。",
            "acceptance": "每个权益状态都有字段、排序、空态和错误态断言",
            "owner": "PM",
            "status": "待处理",
        },
        {
            "suggestion_id": "FIX-002",
            "related_issues": ["Q-002"],
            "suggestion": "补充领取次数和过期边界规则。",
            "acceptance": "给出每日、每周期和总次数限制及过期计算口径",
            "owner": "PM / 研发",
            "status": "待处理",
        },
    ],
    "stage_gate": [
        {
            "checked": True,
            "item": "评审范围与不评审范围已明确",
        },
        {
            "checked": True,
            "item": "所有 P0 问题都有证据/依据、修订建议和责任方/确认人",
        },
    ],
}

VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA = {
    "conclusion": {
        "artifact_name": "可签署需求评审报告",
        "review_result": "不通过",
        "reason": "存在 1 个 P0 阻塞性问题，必须修订需求后重新评审。",
        "development_gate": "暂缓",
        "needs_recheck": "是",
        "summary": "会员权益需求当前缺少核心展示验收标准，暂不建议进入开发和测试设计。",
    },
    "review_info": {
        "requirement_name": "会员权益需求",
        "review_date": "2026-06-23",
        "review_input": "REQ_REVIEW/REVIEW 问题清单 v1.0",
        "participants": "产品 / 研发 / 测试",
    },
    "issue_statistics": {
        "p0_count": 1,
        "p1_count": 1,
        "p2_count": 1,
    },
    "issue_closures": [
        {
            "issue_id": "Q-001",
            "priority": "P0",
            "description": "权益状态缺少可验收的展示断言。",
            "requirement_section": "权益中心展示",
            "impact": "影响权益展示主链路测试设计",
            "owner": "PM",
            "next_step": "补充每种权益状态的展示字段、排序和空态验收标准。",
            "closure_status": "待修订",
            "recheck_condition": "修订 PRD 后覆盖已领取、已过期、不可用状态断言。",
        },
        {
            "issue_id": "Q-002",
            "priority": "P1",
            "description": "领取次数和过期时间缺少边界规则。",
            "requirement_section": "权益领取规则",
            "impact": "影响边界值和异常路径覆盖",
            "owner": "PM / 研发",
            "next_step": "明确领取次数、过期时间和重复领取提示。",
            "closure_status": "待修订",
            "recheck_condition": "补充每日、每周期和总次数限制。",
        },
        {
            "issue_id": "Q-003",
            "priority": "P2",
            "description": "建议补充权益运营配置示例。",
            "requirement_section": "配置说明",
            "impact": "提升测试数据准备效率",
            "owner": "PM",
            "next_step": "补充典型权益配置样例。",
            "closure_status": "待排期",
            "recheck_condition": "后续迭代补充即可。",
        },
    ],
    "review_conditions": [
        {
            "condition_id": "RC-001",
            "condition": "P0 问题 Q-001 关闭后重新评审。",
            "related_issues": ["Q-001"],
            "verification": "检查修订 PRD 中权益状态展示验收标准。",
            "owner": "产品 / 测试",
            "status": "待满足",
        },
        {
            "condition_id": "RC-002",
            "condition": "P1 问题 Q-002 给出明确边界规则。",
            "related_issues": ["Q-002"],
            "verification": "检查领取次数和过期计算口径。",
            "owner": "产品 / 研发",
            "status": "待满足",
        },
    ],
    "signoffs": [
        {
            "role": "产品负责人",
            "owner": "PM",
            "opinion": "不通过",
            "status": "待签署",
        },
        {
            "role": "测试负责人",
            "owner": "测试",
            "opinion": "不通过",
            "status": "待签署",
        },
    ],
    "change_log": [
        {
            "version": "v1.0",
            "date": "2026-06-23",
            "change": "首次生成需求评审报告",
            "reason": "完成 REVIEW 阶段问题清单汇总",
            "owner": "Lisa",
        }
    ],
}

VALID_VALUE_ELEVATOR_ARTIFACT_DATA = {
    "document_info": {
        "artifact_name": "价值定位诊断报告",
        "workflow": "VALUE_DISCOVERY",
        "stage": "ELEVATOR",
        "status": "可进入用户画像",
    },
    "positioning_summary": {
        "one_liner": "面向中小测试团队的 AI 测试设计助手，帮助把需求快速转成可评审测试资产。",
        "core_user": "缺少专职测试架构师的测试负责人",
        "core_pain": "需求到测试策略和用例之间缺少稳定方法，返工成本高。",
        "unique_value": "把需求澄清、风险分析和用例追溯统一到可审阅 artifact。",
        "current_judgement": "可继续画像分析",
    },
    "value_flow": {
        "nodes": [
            {
                "node_id": "USER",
                "label": "目标用户",
                "description": "测试负责人",
            },
            {
                "node_id": "SCENE",
                "label": "高价值场景",
                "description": "需求评审后快速产出测试设计",
            },
            {
                "node_id": "PAIN",
                "label": "核心痛点",
                "description": "测试设计依赖个人经验",
            },
            {
                "node_id": "EXISTING",
                "label": "现有方案",
                "description": "手工模板和零散评审",
            },
            {
                "node_id": "GAP",
                "label": "现有方案不足",
                "description": "缺少追溯和风险门禁",
            },
            {
                "node_id": "VALUE",
                "label": "产品独特价值",
                "description": "结构化生成可评审测试资产",
            },
            {
                "node_id": "PROOF",
                "label": "证据与验证动作",
                "description": "试点项目对比返工率",
            },
            {
                "node_id": "BUSINESS",
                "label": "商业可行性判断",
                "description": "按团队订阅或项目包付费",
            },
        ],
        "links": [
            {"from_node": "USER", "to_node": "SCENE", "label": "负责"},
            {"from_node": "SCENE", "to_node": "PAIN", "label": "暴露"},
            {"from_node": "PAIN", "to_node": "EXISTING", "label": "当前依赖"},
            {"from_node": "EXISTING", "to_node": "GAP", "label": "不足"},
            {"from_node": "GAP", "to_node": "VALUE", "label": "形成价值"},
            {"from_node": "VALUE", "to_node": "PROOF", "label": "需要验证"},
            {"from_node": "PROOF", "to_node": "BUSINESS", "label": "支撑"},
        ],
    },
    "target_scenarios": [
        {
            "dimension": "主要用户群体",
            "description": "中小研发团队中的测试负责人",
            "evidence_level": "用户陈述",
            "status": "AI 假设",
        },
        {
            "dimension": "核心使用场景",
            "description": "需求评审后 1 天内形成测试设计初稿",
            "evidence_level": "合理推断",
            "status": "待验证",
        },
    ],
    "pain_evidence": [
        {
            "pain_id": "PAIN-001",
            "description": "测试设计质量受个人经验影响大",
            "scene": "新需求进入开发前",
            "impact": "返工和漏测风险增加",
            "evidence_level": "用户陈述",
            "validation_action": "访谈 5 位测试负责人并收集返工案例",
            "status": "待验证",
        }
    ],
    "differentiators": [
        {
            "dimension": "核心优势",
            "our_value": "把需求、风险、测试点和用例放在同一追溯链",
            "existing_solution": "通用文档模板和人工评审",
            "evidence": "已有测试设计 workflow 可生成覆盖矩阵",
            "status": "AI 假设",
        }
    ],
    "business_feasibility": [
        {
            "dimension": "用户付费意愿",
            "judgement": "若能减少返工，团队负责人有试点预算",
            "basis": "测试质量与交付风险直接相关",
            "validation_action": "设置试点报价页并访谈预算负责人",
            "status": "待验证",
        }
    ],
    "score_matrix": [
        {
            "dimension": "痛点强度",
            "score": 4,
            "basis": "返工和漏测影响核心交付目标",
            "next_validation": "收集 3 个近期返工案例",
        },
        {
            "dimension": "目标用户清晰度",
            "score": 4,
            "basis": "测试负责人角色明确",
            "next_validation": "细分团队规模和行业",
        },
        {
            "dimension": "差异化",
            "score": 3,
            "basis": "追溯链和阶段门禁有差异，但需竞品对比",
            "next_validation": "对比 3 个测试管理工具",
        },
        {
            "dimension": "付费意愿",
            "score": 3,
            "basis": "预算假设尚未验证",
            "next_validation": "访谈预算负责人",
        },
        {
            "dimension": "证据强度",
            "score": 2,
            "basis": "当前主要来自合理推断",
            "next_validation": "完成用户访谈",
        },
    ],
    "score_summary": {
        "total_score": 16,
        "average_score": 3.2,
        "judgement": "值得进入用户画像，但必须补强证据。",
    },
    "assumptions": [
        {
            "assumption_id": "H-001",
            "content": "目标团队愿意为减少测试设计返工付费",
            "impact": "影响商业模式和定价",
            "validation_action": "定价访谈和试点报价",
            "owner": "产品",
            "status": "待验证",
        }
    ],
    "elevator_pitch": "我们为缺少专职测试架构师的中小测试团队提供 AI 测试设计助手。它能把需求澄清、风险分析、测试策略和用例追溯统一成可评审产物，减少因经验不一致造成的返工和漏测。不同于普通文档模板，它输出可追溯、可签署、可继续交给测试资产链路的专业 artifact。下一步需要通过测试负责人访谈验证痛点强度和付费意愿。",
    "stage_gate": [
        {"checked": True, "item": "目标用户、核心场景和核心痛点已明确。"},
        {"checked": True, "item": "痛点证据至少标注了证据等级和验证动作。"},
        {
            "checked": True,
            "item": "独特价值和商业可行性没有被写成未标注的事实。",
        },
        {
            "checked": True,
            "item": "未验证假设已列入假设清单，可被用户画像阶段继续验证。",
        },
    ],
}

VALID_VALUE_PERSONA_ARTIFACT_DATA = {
    "document_info": {
        "artifact_name": "用户画像与决策链分析",
        "workflow": "VALUE_DISCOVERY",
        "stage": "PERSONA",
        "status": "可进入用户旅程",
    },
    "persona_summary": {
        "artifact_name": "用户画像与决策链分析",
        "core_user_judgement": "最优先服务缺少测试架构支持的中小团队测试负责人",
        "primary_pain": "PAIN-001 测试设计质量受个人经验影响大",
        "validation_status": "部分验证",
        "journey_readiness": "可进入",
    },
    "personas": [
        {
            "persona_id": "PER-001",
            "name": "中小研发团队测试负责人",
            "priority": "核心用户",
            "summary": "负责把需求转成测试策略和用例，但缺少稳定方法和架构师支持。",
            "basic_features": [
                {
                    "dimension": "用户类型",
                    "description": "管理 3-8 名测试或质量成员的测试负责人",
                    "evidence_level": "用户陈述",
                    "validation_status": "部分验证",
                },
                {
                    "dimension": "企业属性",
                    "description": "20-100 人研发团队，需求变化快，交付节奏紧",
                    "evidence_level": "合理推断",
                    "validation_status": "待验证",
                },
                {
                    "dimension": "技术水平",
                    "description": "熟悉测试管理工具，愿意试用 AI 辅助设计",
                    "evidence_level": "合理推断",
                    "validation_status": "待验证",
                },
                {
                    "dimension": "决策角色",
                    "description": "既是使用者，也是工具试点影响者",
                    "evidence_level": "用户陈述",
                    "validation_status": "部分验证",
                },
            ],
            "behavior_features": [
                {
                    "dimension": "日常工作模式",
                    "description": "围绕需求评审、测试设计、用例评审和上线风险跟踪工作",
                    "trigger": "新需求进入开发前",
                    "evidence_level": "用户陈述",
                    "validation_status": "部分验证",
                },
                {
                    "dimension": "信息获取方式",
                    "description": "通过团队复盘、测试社区和竞品文档寻找方法",
                    "trigger": "现有模板无法覆盖新业务",
                    "evidence_level": "合理推断",
                    "validation_status": "待验证",
                },
                {
                    "dimension": "决策模式",
                    "description": "先试点一个需求，再向研发负责人证明返工减少",
                    "trigger": "有明确项目试点机会",
                    "evidence_level": "合理推断",
                    "validation_status": "待验证",
                },
                {
                    "dimension": "工具使用习惯",
                    "description": "常用测试管理、文档协作和缺陷跟踪工具",
                    "trigger": "需求进入测试设计阶段",
                    "evidence_level": "用户陈述",
                    "validation_status": "部分验证",
                },
            ],
        }
    ],
    "behavior_scenarios": [
        {
            "scenario_id": "SC-001",
            "persona_id": "PER-001",
            "scenario": "需求评审结束后，需要在一天内输出测试设计初稿",
            "trigger": "需求确认进入开发排期",
            "user_goal": "快速形成可评审的风险、测试点和用例方向",
            "current_solution": "复制历史模板并人工补充风险清单",
            "status": "AI 假设",
        }
    ],
    "decision_chain": [
        {
            "role": "使用者",
            "persona_id": "PER-001",
            "concern": "产物是否减少测试设计返工",
            "influence": "高",
            "payment_relation": "提出试点需求但不直接采购",
            "evidence_level": "合理推断",
            "validation_status": "待验证",
        },
        {
            "role": "决策者",
            "persona_id": "PER-001",
            "concern": "ROI、数据安全和团队采用成本",
            "influence": "中",
            "payment_relation": "影响预算审批",
            "evidence_level": "合理推断",
            "validation_status": "待验证",
        },
    ],
    "pain_evidence": [
        {
            "pain_id": "PAIN-001",
            "persona_id": "PER-001",
            "pain": "测试设计依赖个人经验，评审返工多",
            "frequency": "每个新需求",
            "impact": "返工、漏测和上线风险",
            "existing_solution_gap": "模板只能记录结论，不能强制风险追溯",
            "evidence_level": "用户陈述",
            "validation_status": "部分验证",
        }
    ],
    "anti_personas": [
        {
            "name": "大型成熟测试平台团队",
            "reason": "已有完备质量平台和测试架构师支持，痛点不够强",
            "boundary": "暂不覆盖深度平台定制和多团队权限治理",
            "risk": "过早服务会拉高集成和权限复杂度",
            "status": "AI 假设",
        }
    ],
    "priority_ranking": [
        {
            "priority": "核心用户",
            "persona_id": "PER-001",
            "reason": "痛点强、场景高频、能直接验证价值",
            "related_pain": "PAIN-001",
            "evidence_level": "用户陈述",
            "validation_status": "部分验证",
        }
    ],
    "stage_gate": [
        {
            "checked": True,
            "item": "至少一个核心用户画像包含角色、场景、痛点、影响程度和证据等级。",
        },
        {
            "checked": True,
            "item": "使用者、决策者、付费者的关系已说明，或明确标注为待验证。",
        },
        {
            "checked": True,
            "item": "反画像已列出，避免下一阶段旅程范围过宽。",
        },
        {
            "checked": True,
            "item": "可进入旅程阶段的核心场景已明确。",
        },
    ],
}

VALID_VALUE_JOURNEY_ARTIFACT_DATA = {
    "document_info": {
        "artifact_name": "用户旅程与机会地图",
        "workflow": "VALUE_DISCOVERY",
        "stage": "JOURNEY",
        "status": "可进入需求蓝图",
    },
    "journey_summary": {
        "core_persona": "中小研发团队测试负责人",
        "core_pain": "测试设计质量受个人经验影响大，评审返工多。",
        "entry_strategy": "优先切入需求评审后的测试设计初稿阶段。",
        "blueprint_readiness": "可进入需求蓝图，但需继续验证试点节省时间指标。",
    },
    "journey_stages": [
        {
            "stage_id": "JS-001",
            "stage_name": "问题认知",
            "user_task": "意识到新需求缺少系统化测试设计方法",
            "touchpoint": "需求评审会议和历史测试模板",
            "user_goal": "确认本次需求是否存在高风险测试盲区",
            "user_behavior": "翻找历史案例并询问资深同事",
            "emotion_score": 2,
            "emotion_reason": "风险判断依赖个人经验，时间压力大",
            "pain_id": "PAIN-001",
            "key_pain": "需求评审后不知道从哪里开始拆测试策略",
            "existing_solution_gap": "历史模板只能记录结论，不能提示风险遗漏",
            "opportunity_id": "OPP-001",
            "opportunity_hypothesis": "用 AI 引导式澄清和风险种子降低启动成本",
            "success_metric": "测试设计初稿产出时间减少 30%",
            "validation_status": "待验证",
        },
        {
            "stage_id": "JS-002",
            "stage_name": "方案评估",
            "user_task": "比较模板、测试管理工具和 AI 辅助方案",
            "touchpoint": "团队文档库、测试平台、AI 助手试用",
            "user_goal": "找到能直接产出可评审测试资产的方法",
            "user_behavior": "试用不同工具并向研发负责人解释投入产出",
            "emotion_score": 3,
            "emotion_reason": "有潜在方案，但缺少可信度证明",
            "pain_id": "PAIN-002",
            "key_pain": "通用工具无法证明测试设计质量是否足够",
            "existing_solution_gap": "工具关注管理流程，不关注测试设计专业门禁",
            "opportunity_id": "OPP-002",
            "opportunity_hypothesis": "提供可追溯 artifact 和质量门禁提升采纳信心",
            "success_metric": "评审一次通过率提升到 80%",
            "validation_status": "AI 假设",
        },
        {
            "stage_id": "JS-003",
            "stage_name": "试点使用",
            "user_task": "用 AI4SE 为一个真实需求生成测试设计初稿",
            "touchpoint": "New Agents 工作台和右侧 artifact",
            "user_goal": "快速获得可编辑、可评审、可交接的测试设计",
            "user_behavior": "输入需求背景，审阅澄清、策略和用例产物",
            "emotion_score": 4,
            "emotion_reason": "如果产物结构完整，能显著降低手工整理成本",
            "pain_id": "PAIN-003",
            "key_pain": "AI 输出如果格式不稳定会增加返工",
            "existing_solution_gap": "直接让模型写 Markdown 容易漏标题和图表",
            "opportunity_id": "OPP-003",
            "opportunity_hypothesis": "后端确定性渲染结构化产物降低格式失败",
            "success_metric": "artifact contract 首次通过率达到 95%",
            "validation_status": "部分验证",
        },
    ],
    "pain_priorities": [
        {
            "priority_level": "高优先级痛点",
            "pain_id": "PAIN-001",
            "pain": "需求评审后不知道从哪里开始拆测试策略",
            "stage_id": "JS-001",
            "impact": "严重",
            "frequency": "每个新需求",
            "existing_solution_gap": "历史模板不能主动发现风险遗漏",
        },
        {
            "priority_level": "中等优先级痛点",
            "pain_id": "PAIN-002",
            "pain": "工具无法证明测试设计质量是否足够",
            "stage_id": "JS-002",
            "impact": "中等",
            "frequency": "高频",
            "existing_solution_gap": "现有工具缺少专业门禁说明",
        },
        {
            "priority_level": "低优先级痛点",
            "pain_id": "PAIN-003",
            "pain": "AI 输出格式不稳定会增加返工",
            "stage_id": "JS-003",
            "impact": "轻微",
            "frequency": "中频",
            "existing_solution_gap": "直接生成 Markdown 依赖模型稳定性",
        },
    ],
    "opportunity_scores": [
        {
            "opportunity_id": "OPP-001",
            "opportunity": "需求评审后自动生成测试设计启动框架",
            "pain_id": "PAIN-001",
            "value_potential": "高",
            "competition_strength": "中",
            "feasibility": "高",
            "success_metric": "测试设计初稿产出时间减少 30%",
            "validation_status": "待验证",
        },
        {
            "opportunity_id": "OPP-002",
            "opportunity": "把质量门禁和追溯链作为评审依据",
            "pain_id": "PAIN-002",
            "value_potential": "中",
            "competition_strength": "弱",
            "feasibility": "中",
            "success_metric": "评审一次通过率提升到 80%",
            "validation_status": "AI 假设",
        },
        {
            "opportunity_id": "OPP-003",
            "opportunity": "以结构化数据驱动稳定 artifact 输出",
            "pain_id": "PAIN-003",
            "value_potential": "中",
            "competition_strength": "弱",
            "feasibility": "高",
            "success_metric": "artifact contract 首次通过率达到 95%",
            "validation_status": "部分验证",
        },
    ],
    "entry_strategy": [
        {
            "strategy_item": "优先切入阶段",
            "content": "需求评审结束后的测试设计启动阶段",
            "related_opportunity": "OPP-001",
            "tradeoff_reason": "该阶段痛点强、频率高、能最快证明节省时间价值",
            "status": "已确认",
        },
        {
            "strategy_item": "暂缓阶段",
            "content": "深度测试平台集成和多团队治理",
            "related_opportunity": "OPP-002",
            "tradeoff_reason": "会拉高实现复杂度，适合在试点价值验证后推进",
            "status": "AI 假设",
        },
    ],
    "validation_experiments": [
        {
            "experiment_id": "EXP-001",
            "hypothesis": "结构化测试设计助手能把初稿产出时间减少 30%",
            "opportunity_id": "OPP-001",
            "method": "选择 3 个真实需求做人工模板与 AI4SE 对照试点",
            "success_metric": "平均初稿时间、返工次数和评审通过率",
            "owner": "产品",
            "status": "待执行",
        },
        {
            "experiment_id": "EXP-002",
            "hypothesis": "确定性 renderer 能显著减少 artifact 格式失败",
            "opportunity_id": "OPP-003",
            "method": "对比 Markdown 直出与 artifact_data 渲染的 contract 通过率",
            "success_metric": "首次 contract 通过率达到 95%",
            "owner": "研发",
            "status": "部分验证",
        },
    ],
    "stage_gate": [
        {"checked": True, "item": "主要机会点关联到高优先级痛点。"},
        {"checked": True, "item": "每个主要机会点都有成功指标和验证实验。"},
        {"checked": True, "item": "产品切入策略说明了优先做什么和暂缓什么。"},
        {"checked": True, "item": "可进入蓝图阶段的 P0 机会已明确。"},
    ],
}

VALID_VALUE_BLUEPRINT_ARTIFACT_DATA = {
    "document_info": {
        "product_name": "AI4SE 测试设计助手",
        "version": "v1.0",
        "created_at": "2026-06-23",
        "product_direction": "面向中小研发团队的 AI 测试设计工作台",
        "artifact_name": "可评审需求蓝图",
        "blueprint_status": "可交接 Lisa",
    },
    "product_overview": {
        "vision": "让缺少测试架构师支持的团队，也能稳定产出可评审、可追溯的测试设计资产。",
        "positioning_for": "中小研发团队测试负责人",
        "positioning_who": "需要在需求评审后快速形成测试策略和用例方向",
        "positioning_product": "AI 测试设计助手",
        "positioning_category": "质量工程工作台",
        "positioning_value": "把需求澄清、风险分析、测试策略和用例追溯统一成可审阅 artifact。",
        "positioning_unlike": "通用文档模板和零散 AI 对话",
        "positioning_differentiator": "输出通过后端 contract 校验、可交接 Lisa 的结构化测试资产。",
        "user_value": "减少测试设计启动成本和评审返工。",
        "business_value": "提升需求交付质量，降低漏测和返工成本。",
        "business_model": "按团队订阅或按试点项目包收费。",
    },
    "target_users": [
        {
            "user_type": "中小研发团队测试负责人",
            "core_pain": "测试设计依赖个人经验，评审返工多。",
            "priority": "核心用户",
        },
        {
            "user_type": "产品负责人",
            "core_pain": "需求交接到测试时经常暴露遗漏和歧义。",
            "priority": "重要用户",
        },
    ],
    "feature_modules": [
        {
            "module_id": "MOD-001",
            "module_name": "需求澄清",
            "features": [
                {
                    "feature_id": "F-001",
                    "feature_name": "结构化需求澄清",
                    "requirement_id": "F-001",
                }
            ],
        },
        {
            "module_id": "MOD-002",
            "module_name": "风险驱动测试设计",
            "features": [
                {
                    "feature_id": "F-002",
                    "feature_name": "风险与测试策略生成",
                    "requirement_id": "F-002",
                }
            ],
        },
    ],
    "requirements": [
        {
            "requirement_id": "F-001",
            "priority": "P0",
            "name": "结构化需求澄清",
            "user_story": "作为测试负责人，我想把需求输入转成澄清清单，以便在开发前发现遗漏。",
            "related_pain": "PAIN-001",
            "scope": "覆盖需求事实、边界、业务规则、待澄清问题和质量需求；不替代 PM 决策。",
            "dependency": "需要用户提供需求背景和业务规则来源。",
            "acceptance": "同一输入能生成包含必填标题和阶段门禁的需求分析 artifact。",
            "testability_level": "高",
            "owner": "产品",
            "status": "已确认",
        },
        {
            "requirement_id": "F-002",
            "priority": "P0",
            "name": "风险驱动测试策略生成",
            "user_story": "作为测试负责人，我想自动获得风险、测试点和测试层级建议，以便快速组织评审。",
            "related_pain": "PAIN-002",
            "scope": "覆盖 FMEA、质量目标、测试点和资源取舍；不自动执行测试。",
            "dependency": "依赖需求澄清输出和风险偏好。",
            "acceptance": "能生成通过 contract 的测试策略蓝图，并包含风险可视化。",
            "testability_level": "高",
            "owner": "研发",
            "status": "已确认",
        },
        {
            "requirement_id": "F-003",
            "priority": "P1",
            "name": "测试用例追溯矩阵",
            "user_story": "作为测试负责人，我想把测试点转成用例和覆盖追溯，以便评审覆盖完整性。",
            "related_pain": "PAIN-002",
            "scope": "生成用例集、覆盖矩阵和开放问题；不连接外部测试管理系统。",
            "dependency": "依赖测试策略蓝图。",
            "acceptance": "生成的用例集可被测试资产解析器识别。",
            "testability_level": "中",
            "owner": "测试",
            "status": "AI 假设",
        },
    ],
    "main_flow": {
        "nodes": [
            {"node_id": "START", "label": "输入需求背景"},
            {"node_id": "CLARIFY", "label": "生成需求澄清"},
            {"node_id": "STRATEGY", "label": "生成测试策略"},
            {"node_id": "CASES", "label": "生成测试用例"},
            {"node_id": "HANDOFF", "label": "交接 Lisa 评审"},
        ],
        "links": [
            {"from_node": "START", "to_node": "CLARIFY", "label": "澄清"},
            {"from_node": "CLARIFY", "to_node": "STRATEGY", "label": "风险分析"},
            {"from_node": "STRATEGY", "to_node": "CASES", "label": "用例设计"},
            {"from_node": "CASES", "to_node": "HANDOFF", "label": "交付"},
        ],
    },
    "success_metrics": [
        {
            "metric_type": "业务指标",
            "metric_name": "试点团队采用率",
            "target": "3 个团队完成试点",
            "measurement": "试点项目记录",
        },
        {
            "metric_type": "用户指标",
            "metric_name": "测试设计初稿时间",
            "target": "减少 30%",
            "measurement": "人工模板与 AI4SE 对照",
        },
    ],
    "mvp_plan": {
        "included_features": [
            {
                "requirement_id": "F-001",
                "feature_name": "结构化需求澄清",
                "included": True,
                "release": "v1.0 MVP",
            },
            {
                "requirement_id": "F-002",
                "feature_name": "风险驱动测试策略生成",
                "included": True,
                "release": "v1.0 MVP",
            },
            {
                "requirement_id": "F-003",
                "feature_name": "测试用例追溯矩阵",
                "included": False,
                "release": "v1.1",
            },
        ],
        "iterations": [
            {
                "version": "v1.0 MVP",
                "time": "4 周",
                "core_features": "F-001, F-002",
                "goal": "验证测试设计启动价值",
            },
            {
                "version": "v1.1",
                "time": "8 周",
                "core_features": "F-003",
                "goal": "完善用例追溯闭环",
            },
        ],
    },
    "non_functional_requirements": [
        {
            "type": "性能",
            "description": "单阶段生成在可接受时间内返回进度和最终 artifact。",
            "metric_or_constraint": "SSE 持续输出，最终响应不超过试点阈值",
            "verification": "接口测试和运行统计",
            "owner": "研发",
            "status": "AI 假设",
        },
        {
            "type": "安全",
            "description": "模型供应商密钥只存在后端环境变量中。",
            "metric_or_constraint": "前端 bundle 不包含密钥",
            "verification": "配置审查",
            "owner": "研发",
            "status": "已确认",
        },
    ],
    "acceptance_criteria": [
        {
            "acceptance_id": "AC-001",
            "requirement_id": "F-001",
            "criterion": "给定需求文本时，系统生成包含需求事实、边界、业务规则和阶段门禁的 artifact。",
            "verification": "后端 contract test",
            "testability_level": "高",
            "owner": "测试",
            "status": "已确认",
        },
        {
            "acceptance_id": "AC-002",
            "requirement_id": "F-002",
            "criterion": "生成的测试策略蓝图包含风险矩阵、测试点和资源取舍。",
            "verification": "后端 renderer test",
            "testability_level": "高",
            "owner": "测试",
            "status": "已确认",
        },
    ],
    "roadmap": [
        {
            "version": "v1.0 MVP",
            "time": "4 周",
            "core_features": "结构化需求澄清、风险驱动测试策略",
            "goal": "验证主价值",
            "success_metric": "初稿时间减少 30%",
        },
        {
            "version": "v1.1",
            "time": "8 周",
            "core_features": "测试用例追溯矩阵",
            "goal": "完善交付闭环",
            "success_metric": "用例评审通过率达到 80%",
        },
    ],
    "risks": [
        {
            "risk_type": "产品风险",
            "description": "AI 产物专业质量不足导致用户不信任。",
            "probability": "中",
            "impact": "高",
            "mitigation": "用 artifact contract、质量门禁和可编辑审阅闭环降低风险。",
            "owner": "产品",
            "status": "待验证",
        },
        {
            "risk_type": "执行风险",
            "description": "不同模型输出格式差异导致 artifact 失败。",
            "probability": "中",
            "impact": "高",
            "mitigation": "采用 artifact_data schema 和后端确定性 renderer。",
            "owner": "研发",
            "status": "部分验证",
        },
    ],
    "lisa_handoff_inputs": [
        {
            "input_type": "需求",
            "reference_id": "F-001",
            "content": "结构化需求澄清能力需要 Lisa 做需求可测试性评审。",
            "source": "P0 需求",
            "usage": "需求评审 / 测试设计",
            "status": "已确认",
        },
        {
            "input_type": "验收标准",
            "reference_id": "AC-001",
            "content": "需求澄清 artifact 必须包含必填标题和阶段门禁。",
            "source": "验收标准",
            "usage": "测试断言",
            "status": "已确认",
        },
        {
            "input_type": "风险",
            "reference_id": "RISK-001",
            "content": "AI 产物质量不足可能造成评审返工。",
            "source": "风险评估",
            "usage": "测试策略风险种子",
            "status": "待验证",
        },
    ],
    "stage_gate": [
        {"checked": True, "item": "P0 需求均具备验收标准、owner 和可测试性等级。"},
        {
            "checked": True,
            "item": "非功能需求中的性能、安全、兼容性或可观测性已按实际场景标注。",
        },
        {"checked": True, "item": "roadmap 与 MVP 范围一致。"},
        {"checked": True, "item": "Lisa Handoff 输入足以支撑需求评审或测试设计。"},
    ],
}


def test_clarify_artifact_data_rejects_blank_required_values():
    invalid = {
        **VALID_CLARIFY_ARTIFACT_DATA,
        "requirement_facts": [
            {
                **VALID_CLARIFY_ARTIFACT_DATA["requirement_facts"][0],
                "fact": "   ",
            }
        ],
    }

    with pytest.raises(ValidationError, match="fact"):
        ClarifyArtifactData.model_validate(invalid)


def test_clarify_artifact_data_rejects_empty_required_lists():
    invalid = {
        **VALID_CLARIFY_ARTIFACT_DATA,
        "business_rules": [],
    }

    with pytest.raises(ValidationError, match="business_rules"):
        ClarifyArtifactData.model_validate(invalid)


def test_idea_define_artifact_data_rejects_duplicate_evidence_id():
    invalid = copy.deepcopy(VALID_IDEA_DEFINE_ARTIFACT_DATA)
    invalid["evidence_items"].append(copy.deepcopy(invalid["evidence_items"][0]))

    with pytest.raises(ValidationError, match="duplicate evidence_id"):
        IdeaDefineArtifactData.model_validate(invalid)


def test_idea_define_artifact_data_rejects_duplicate_problem_id():
    invalid = copy.deepcopy(VALID_IDEA_DEFINE_ARTIFACT_DATA)
    invalid["problem_landscape"]["subproblems"][1]["problem_id"] = "P-001"

    with pytest.raises(ValidationError, match="duplicate problem_id"):
        IdeaDefineArtifactData.model_validate(invalid)


def test_idea_define_artifact_data_rejects_unknown_fit_evidence_reference():
    invalid = copy.deepcopy(VALID_IDEA_DEFINE_ARTIFACT_DATA)
    invalid["problem_user_fit"][0]["evidence_ids"] = ["EV-404"]

    with pytest.raises(ValidationError, match="unknown evidence ids"):
        IdeaDefineArtifactData.model_validate(invalid)


def test_idea_define_artifact_data_requires_root_problem_coverage():
    invalid = copy.deepcopy(VALID_IDEA_DEFINE_ARTIFACT_DATA)
    invalid["evidence_items"][0]["related_problem"] = "其它问题"
    invalid["problem_user_fit"][0]["evidence_or_assumption"] = "其它判断"

    with pytest.raises(ValidationError, match="root_problem"):
        IdeaDefineArtifactData.model_validate(invalid)


def test_idea_define_artifact_data_requires_checked_stage_gate():
    invalid = copy.deepcopy(VALID_IDEA_DEFINE_ARTIFACT_DATA)
    invalid["stage_gate"] = [
        {**item, "checked": False} for item in invalid["stage_gate"]
    ]

    with pytest.raises(ValidationError, match="stage_gate"):
        IdeaDefineArtifactData.model_validate(invalid)


def test_idea_diverge_artifact_data_rejects_duplicate_idea_id():
    invalid = copy.deepcopy(VALID_IDEA_DIVERGE_ARTIFACT_DATA)
    invalid["idea_cards"].append(copy.deepcopy(invalid["idea_cards"][0]))

    with pytest.raises(ValidationError, match="duplicate idea_id"):
        IdeaDivergeArtifactData.model_validate(invalid)


def test_idea_diverge_artifact_data_rejects_duplicate_source_id():
    invalid = copy.deepcopy(VALID_IDEA_DIVERGE_ARTIFACT_DATA)
    invalid["idea_sources"].append(copy.deepcopy(invalid["idea_sources"][0]))

    with pytest.raises(ValidationError, match="duplicate source_id"):
        IdeaDivergeArtifactData.model_validate(invalid)


def test_idea_diverge_artifact_data_rejects_duplicate_parked_record_id():
    invalid = copy.deepcopy(VALID_IDEA_DIVERGE_ARTIFACT_DATA)
    invalid["parked_or_excluded"].append(
        copy.deepcopy(invalid["parked_or_excluded"][0])
    )

    with pytest.raises(ValidationError, match="duplicate record_id"):
        IdeaDivergeArtifactData.model_validate(invalid)


def test_idea_diverge_artifact_data_rejects_unknown_landscape_idea_reference():
    invalid = copy.deepcopy(VALID_IDEA_DIVERGE_ARTIFACT_DATA)
    invalid["idea_landscape"]["groups"][0]["idea_ids"] = ["ID-404"]

    with pytest.raises(
        ValidationError, match="idea_landscape references unknown idea ids"
    ):
        IdeaDivergeArtifactData.model_validate(invalid)


def test_idea_diverge_artifact_data_rejects_unknown_source_idea_reference():
    invalid = copy.deepcopy(VALID_IDEA_DIVERGE_ARTIFACT_DATA)
    invalid["idea_sources"][0]["idea_ids"] = ["ID-404"]

    with pytest.raises(
        ValidationError, match="idea_sources references unknown idea ids"
    ):
        IdeaDivergeArtifactData.model_validate(invalid)


def test_idea_diverge_artifact_data_requires_checked_stage_gate():
    invalid = copy.deepcopy(VALID_IDEA_DIVERGE_ARTIFACT_DATA)
    invalid["stage_gate"] = [
        {**item, "checked": False} for item in invalid["stage_gate"]
    ]

    with pytest.raises(ValidationError, match="stage_gate"):
        IdeaDivergeArtifactData.model_validate(invalid)


def test_idea_converge_artifact_data_rejects_duplicate_idea_id():
    invalid = copy.deepcopy(VALID_IDEA_CONVERGE_ARTIFACT_DATA)
    invalid["ice_evaluations"].append(copy.deepcopy(invalid["ice_evaluations"][0]))

    with pytest.raises(ValidationError, match="duplicate idea_id"):
        IdeaConvergeArtifactData.model_validate(invalid)


def test_idea_converge_artifact_data_rejects_duplicate_rank():
    invalid = copy.deepcopy(VALID_IDEA_CONVERGE_ARTIFACT_DATA)
    invalid["ice_evaluations"][1]["rank"] = 1

    with pytest.raises(ValidationError, match="duplicate rank"):
        IdeaConvergeArtifactData.model_validate(invalid)


def test_idea_converge_artifact_data_rejects_invalid_ice_score():
    invalid = copy.deepcopy(VALID_IDEA_CONVERGE_ARTIFACT_DATA)
    invalid["ice_evaluations"][0]["ice_score"] = 9.5

    with pytest.raises(ValidationError, match="ice_score"):
        IdeaConvergeArtifactData.model_validate(invalid)


def test_idea_converge_artifact_data_rejects_unknown_recommended_idea():
    invalid = copy.deepcopy(VALID_IDEA_CONVERGE_ARTIFACT_DATA)
    invalid["decision_matrix"]["recommended_idea_id"] = "ID-404"

    with pytest.raises(ValidationError, match="recommended_idea_id"):
        IdeaConvergeArtifactData.model_validate(invalid)


def test_idea_converge_artifact_data_rejects_unknown_decision_matrix_idea():
    invalid = copy.deepcopy(VALID_IDEA_CONVERGE_ARTIFACT_DATA)
    invalid["decision_matrix"]["decision_items"][0]["idea_id"] = "ID-404"

    with pytest.raises(ValidationError, match="decision_matrix"):
        IdeaConvergeArtifactData.model_validate(invalid)


def test_idea_converge_artifact_data_rejects_unknown_validation_experiment_idea():
    invalid = copy.deepcopy(VALID_IDEA_CONVERGE_ARTIFACT_DATA)
    invalid["validation_experiments"][0]["idea_ids"] = ["ID-404"]

    with pytest.raises(ValidationError, match="validation_experiments"):
        IdeaConvergeArtifactData.model_validate(invalid)


def test_idea_converge_artifact_data_rejects_unknown_merge_path_idea():
    invalid = copy.deepcopy(VALID_IDEA_CONVERGE_ARTIFACT_DATA)
    invalid["merge_paths"][0]["source_idea_ids"] = ["ID-404"]

    with pytest.raises(ValidationError, match="merge_paths"):
        IdeaConvergeArtifactData.model_validate(invalid)


def test_idea_converge_artifact_data_requires_recommended_idea():
    invalid = copy.deepcopy(VALID_IDEA_CONVERGE_ARTIFACT_DATA)
    invalid["decision_matrix"]["recommended_idea_id"] = "ID-002"
    invalid["ice_evaluations"][0]["conclusion"] = "备选"

    with pytest.raises(ValidationError, match="recommended"):
        IdeaConvergeArtifactData.model_validate(invalid)


def test_idea_converge_artifact_data_requires_checked_stage_gate():
    invalid = copy.deepcopy(VALID_IDEA_CONVERGE_ARTIFACT_DATA)
    invalid["stage_gate"] = [
        {**item, "checked": False} for item in invalid["stage_gate"]
    ]

    with pytest.raises(ValidationError, match="stage_gate"):
        IdeaConvergeArtifactData.model_validate(invalid)


def test_idea_concept_artifact_data_rejects_duplicate_assumption_id():
    invalid = copy.deepcopy(VALID_IDEA_CONCEPT_ARTIFACT_DATA)
    invalid["core_assumptions"].append(copy.deepcopy(invalid["core_assumptions"][0]))

    with pytest.raises(ValidationError, match="duplicate assumption_id"):
        IdeaConceptArtifactData.model_validate(invalid)


def test_idea_concept_artifact_data_rejects_duplicate_validation_id():
    invalid = copy.deepcopy(VALID_IDEA_CONCEPT_ARTIFACT_DATA)
    invalid["validation_roadmap"].append(
        copy.deepcopy(invalid["validation_roadmap"][0])
    )

    with pytest.raises(ValidationError, match="duplicate validation_id"):
        IdeaConceptArtifactData.model_validate(invalid)


def test_idea_concept_artifact_data_rejects_duplicate_action_id():
    invalid = copy.deepcopy(VALID_IDEA_CONCEPT_ARTIFACT_DATA)
    invalid["next_actions"].append(copy.deepcopy(invalid["next_actions"][0]))

    with pytest.raises(ValidationError, match="duplicate action_id"):
        IdeaConceptArtifactData.model_validate(invalid)


def test_idea_concept_artifact_data_rejects_missing_lean_canvas_cell():
    invalid = copy.deepcopy(VALID_IDEA_CONCEPT_ARTIFACT_DATA)
    invalid["lean_canvas"] = invalid["lean_canvas"][:-1]

    with pytest.raises(ValidationError, match="lean_canvas"):
        IdeaConceptArtifactData.model_validate(invalid)


def test_idea_concept_artifact_data_rejects_missing_growth_funnel_stage():
    invalid = copy.deepcopy(VALID_IDEA_CONCEPT_ARTIFACT_DATA)
    invalid["growth_funnel"] = invalid["growth_funnel"][:-1]

    with pytest.raises(ValidationError, match="growth_funnel"):
        IdeaConceptArtifactData.model_validate(invalid)


def test_idea_concept_artifact_data_rejects_unknown_mvp_feature_assumption():
    invalid = copy.deepcopy(VALID_IDEA_CONCEPT_ARTIFACT_DATA)
    invalid["mvp_features"][0]["assumption_ids"] = ["H-404"]

    with pytest.raises(ValidationError, match="mvp_features"):
        IdeaConceptArtifactData.model_validate(invalid)


def test_idea_concept_artifact_data_rejects_unknown_validation_assumption():
    invalid = copy.deepcopy(VALID_IDEA_CONCEPT_ARTIFACT_DATA)
    invalid["validation_roadmap"][0]["assumption_ids"] = ["H-404"]

    with pytest.raises(ValidationError, match="validation_roadmap"):
        IdeaConceptArtifactData.model_validate(invalid)


def test_idea_concept_artifact_data_rejects_unknown_next_action_reference():
    invalid = copy.deepcopy(VALID_IDEA_CONCEPT_ARTIFACT_DATA)
    invalid["next_actions"][0]["related_ids"] = ["UNKNOWN-404"]

    with pytest.raises(ValidationError, match="next_actions"):
        IdeaConceptArtifactData.model_validate(invalid)


def test_idea_concept_artifact_data_requires_checked_stage_gate():
    invalid = copy.deepcopy(VALID_IDEA_CONCEPT_ARTIFACT_DATA)
    invalid["stage_gate"] = [
        {**item, "checked": False} for item in invalid["stage_gate"]
    ]

    with pytest.raises(ValidationError, match="stage_gate"):
        IdeaConceptArtifactData.model_validate(invalid)


def test_incident_timeline_artifact_data_rejects_duplicate_fact_id():
    invalid = copy.deepcopy(VALID_INCIDENT_TIMELINE_ARTIFACT_DATA)
    invalid["fact_sources"].append(copy.deepcopy(invalid["fact_sources"][0]))

    with pytest.raises(ValidationError, match="duplicate fact_id"):
        IncidentTimelineArtifactData.model_validate(invalid)


def test_incident_timeline_artifact_data_rejects_unknown_timeline_fact_reference():
    invalid = copy.deepcopy(VALID_INCIDENT_TIMELINE_ARTIFACT_DATA)
    invalid["timeline_events"][0]["fact_ids"] = ["FACT-404"]

    with pytest.raises(ValidationError, match="references unknown fact ids"):
        IncidentTimelineArtifactData.model_validate(invalid)


def test_incident_root_cause_artifact_data_rejects_insufficient_why_depth():
    invalid = copy.deepcopy(VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA)
    invalid["why_chain"] = invalid["why_chain"][:3]

    with pytest.raises(ValidationError, match="at least 3 Why rows"):
        IncidentRootCauseArtifactData.model_validate(invalid)


def test_incident_root_cause_artifact_data_rejects_duplicate_cause_id():
    invalid = copy.deepcopy(VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA)
    invalid["cause_evidence"].append(copy.deepcopy(invalid["cause_evidence"][0]))

    with pytest.raises(ValidationError, match="duplicate cause_id"):
        IncidentRootCauseArtifactData.model_validate(invalid)


def test_incident_root_cause_artifact_data_rejects_unknown_fishbone_cause_reference():
    invalid = copy.deepcopy(VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA)
    invalid["fishbone_categories"][0]["cause_ids"] = ["CAUSE-404"]

    with pytest.raises(ValidationError, match="fishbone_categories references unknown"):
        IncidentRootCauseArtifactData.model_validate(invalid)


def test_incident_root_cause_artifact_data_rejects_unknown_conclusion_cause_reference():
    invalid = copy.deepcopy(VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA)
    invalid["root_cause_conclusions"][0]["related_cause_id"] = "CAUSE-404"

    with pytest.raises(
        ValidationError,
        match="root_cause_conclusions references unknown",
    ):
        IncidentRootCauseArtifactData.model_validate(invalid)


def test_incident_root_cause_artifact_data_requires_root_cause_conclusion():
    invalid = copy.deepcopy(VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA)
    invalid["root_cause_conclusions"] = [
        item
        for item in invalid["root_cause_conclusions"]
        if item["conclusion_type"] != "根本原因"
    ]

    with pytest.raises(ValidationError, match="must include root cause conclusion"):
        IncidentRootCauseArtifactData.model_validate(invalid)


def test_incident_improvement_artifact_data_rejects_duplicate_action_id():
    invalid = copy.deepcopy(VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA)
    invalid["improvement_actions"][1]["action_id"] = "A-001"

    with pytest.raises(ValidationError, match="action_id"):
        IncidentImprovementArtifactData.model_validate(invalid)


def test_incident_improvement_artifact_data_rejects_action_count_mismatch():
    invalid = copy.deepcopy(VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA)
    invalid["report_info"]["action_count"] = 4

    with pytest.raises(ValidationError, match="action_count"):
        IncidentImprovementArtifactData.model_validate(invalid)


def test_incident_improvement_artifact_data_rejects_priority_distribution_mismatch():
    invalid = copy.deepcopy(VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA)
    invalid["priority_distribution"]["urgent_count"] = 2

    with pytest.raises(ValidationError, match="priority_distribution"):
        IncidentImprovementArtifactData.model_validate(invalid)


def test_incident_improvement_artifact_data_rejects_unknown_coverage_action_reference():
    invalid = copy.deepcopy(VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA)
    invalid["root_cause_coverage"][0]["action_ids"] = ["A-404"]

    with pytest.raises(ValidationError, match="root_cause_coverage"):
        IncidentImprovementArtifactData.model_validate(invalid)


def test_incident_improvement_artifact_data_rejects_unknown_action_root_cause_reference():
    invalid = copy.deepcopy(VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA)
    invalid["improvement_actions"][0]["root_cause_id"] = "CAUSE-404"

    with pytest.raises(ValidationError, match="root_cause_id"):
        IncidentImprovementArtifactData.model_validate(invalid)


def test_incident_improvement_artifact_data_rejects_covered_cause_without_actions():
    invalid = copy.deepcopy(VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA)
    invalid["root_cause_coverage"][0]["action_ids"] = []

    with pytest.raises(ValidationError, match="coverage_status"):
        IncidentImprovementArtifactData.model_validate(invalid)


def test_render_clarify_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "我已整理登录需求澄清基线，请确认右侧文档。",
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "STRATEGY",
            },
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "我已整理登录需求澄清基线，请确认右侧文档。",
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "STRATEGY",
            },
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    clarify_markdown = first.artifact_update.markdown
    assert "# 需求分析文档" in first.artifact_update.markdown
    assert "## 8. 阶段门禁" in first.artifact_update.markdown
    assert clarify_markdown.index("## 1. 需求事实清单") < clarify_markdown.index(
        "## 附录：文档信息"
    )
    assert "| 字段 | 内容 |" not in clarify_markdown
    assert "- **Artifact 名称**：测试需求分析与澄清基线" in clarify_markdown
    assert "flowchart TD" in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
        == first
    )


def test_strategy_artifact_data_rejects_inconsistent_rpn():
    invalid = {
        **VALID_STRATEGY_ARTIFACT_DATA,
        "risks": [
            {
                **VALID_STRATEGY_ARTIFACT_DATA["risks"][0],
                "rpn": 999,
            }
        ],
    }

    with pytest.raises(ValidationError, match="rpn"):
        StrategyArtifactData.model_validate(invalid)


def test_strategy_artifact_data_computes_missing_rpn_for_generated_visuals():
    data = copy.deepcopy(VALID_STRATEGY_ARTIFACT_DATA)
    data["risks"][0].pop("rpn")

    artifact = StrategyArtifactData.model_validate(data)
    assert artifact.risks[0].rpn == 60

    output = render_agent_turn_from_artifact_data(
        {
            "chat": "我已形成风险驱动测试策略，请确认右侧蓝图。",
            "artifact_data": data,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert output is not None
    assert output.artifact_update.markdown is not None
    strategy_markdown = output.artifact_update.markdown
    assert "| R-001 | 错误凭证绕过认证 |" in strategy_markdown
    assert "| 5 | 3 | 4 | 60 |" in strategy_markdown
    assert '"RPN": 60' in strategy_markdown
    assert (
        validate_agent_turn(
            output,
            workflow_id="TEST_DESIGN",
            current_stage_id="STRATEGY",
        )
        == output
    )


def test_strategy_mermaid_labels_are_normalized_for_special_characters():
    data = copy.deepcopy(VALID_STRATEGY_ARTIFACT_DATA)
    data["risks"][0]["name"] = '认证 "绕过" \\ 高风险\n二行'
    data["test_layers"][0]["layer"] = '单元 "核心" \\ 层\nBeta'
    data["test_layers"][0]["scope"] = '认证 "规则"\n锁定 \\ 状态'

    output = render_agent_turn_from_artifact_data(
        {
            "chat": "我已形成风险驱动测试策略，请确认右侧蓝图。",
            "artifact_data": data,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert output is not None
    assert output.artifact_update.markdown is not None
    strategy_markdown = output.artifact_update.markdown
    risk_block = _extract_mermaid_block(strategy_markdown, "quadrantChart")
    pyramid_block = _extract_mermaid_block(strategy_markdown, "block-beta")

    assert '"认证 \\"绕过\\" \\\\ 高风险 二行": [0.60, 1.00]' in risk_block
    assert "\n二行" not in risk_block
    assert (
        '单元 \\"核心\\" \\\\ 层 Beta (40%) - '
        '认证 \\"规则\\" 锁定 \\\\ 状态'
    ) in pyramid_block
    assert "\n锁定" not in pyramid_block
    assert (
        validate_agent_turn(
            output,
            workflow_id="TEST_DESIGN",
            current_stage_id="STRATEGY",
        )
        == output
    )


def test_render_strategy_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "我已形成风险驱动测试策略，请确认右侧蓝图。",
            "artifact_data": VALID_STRATEGY_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CASES",
            },
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "我已形成风险驱动测试策略，请确认右侧蓝图。",
            "artifact_data": VALID_STRATEGY_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CASES",
            },
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert "# 测试策略蓝图" in first.artifact_update.markdown
    assert "quadrantChart" in first.artifact_update.markdown
    assert "block-beta" in first.artifact_update.markdown
    assert "```ai4se-visual" in first.artifact_update.markdown
    assert '"type": "risk-board"' in first.artifact_update.markdown
    strategy_markdown = first.artifact_update.markdown
    assert "| 字段 | 内容 |" not in strategy_markdown
    assert "- **策略结论**：" in strategy_markdown
    assert "| 风险 ID | 风险名称 |" in strategy_markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="TEST_DESIGN",
            current_stage_id="STRATEGY",
        )
        == first
    )


def test_cases_artifact_data_rejects_inconsistent_statistics():
    invalid = {
        **VALID_CASES_ARTIFACT_DATA,
        "case_statistics": {
            "total": 99,
            "p0_count": 1,
            "p1_count": 1,
            "p2_count": 0,
        },
    }

    with pytest.raises(ValidationError, match="case_statistics"):
        CasesArtifactData.model_validate(invalid)


def test_cases_artifact_data_rejects_unknown_coverage_case_reference():
    invalid = {
        **VALID_CASES_ARTIFACT_DATA,
        "coverage_trace": [
            {
                **VALID_CASES_ARTIFACT_DATA["coverage_trace"][0],
                "covered_cases": ["TC-404"],
            }
        ],
    }

    with pytest.raises(ValidationError, match="coverage_trace"):
        CasesArtifactData.model_validate(invalid)


def test_delivery_artifact_data_rejects_inconsistent_case_totals():
    invalid = {
        **VALID_DELIVERY_ARTIFACT_DATA,
        "delivery_metrics": {
            **VALID_DELIVERY_ARTIFACT_DATA["delivery_metrics"],
            "total_cases": 99,
        },
    }

    with pytest.raises(ValidationError, match="total_cases"):
        DeliveryArtifactData.model_validate(invalid)


def test_req_review_artifact_data_rejects_inconsistent_issue_statistics():
    invalid = {
        **VALID_REQ_REVIEW_ARTIFACT_DATA,
        "issue_statistics": {
            **VALID_REQ_REVIEW_ARTIFACT_DATA["issue_statistics"],
            "p0_count": 99,
        },
    }

    with pytest.raises(ValidationError, match="issue_statistics"):
        ReqReviewArtifactData.model_validate(invalid)


def test_req_review_report_artifact_data_rejects_inconsistent_issue_statistics():
    invalid = {
        **VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
        "issue_statistics": {
            **VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA["issue_statistics"],
            "p0_count": 99,
        },
    }

    with pytest.raises(ValidationError, match="issue_statistics"):
        ReqReviewReportArtifactData.model_validate(invalid)


def test_value_elevator_artifact_data_rejects_inconsistent_score_summary():
    invalid = copy.deepcopy(VALID_VALUE_ELEVATOR_ARTIFACT_DATA)
    invalid["score_summary"]["total_score"] = 99

    with pytest.raises(ValidationError, match="score_summary.total_score"):
        ValueDiscoveryElevatorArtifactData.model_validate(invalid)


def test_value_elevator_artifact_data_rejects_unknown_value_flow_reference():
    invalid = copy.deepcopy(VALID_VALUE_ELEVATOR_ARTIFACT_DATA)
    invalid["value_flow"]["links"][0]["to_node"] = "UNKNOWN"

    with pytest.raises(
        ValidationError,
        match="value_flow.links references unknown node ids",
    ):
        ValueDiscoveryElevatorArtifactData.model_validate(invalid)


def test_value_persona_artifact_data_rejects_unknown_persona_reference():
    invalid = copy.deepcopy(VALID_VALUE_PERSONA_ARTIFACT_DATA)
    invalid["behavior_scenarios"][0]["persona_id"] = "USER-404"

    with pytest.raises(ValidationError, match="references unknown persona ids"):
        ValueDiscoveryPersonaArtifactData.model_validate(invalid)


def test_value_persona_artifact_data_rejects_duplicate_priority_persona():
    invalid = copy.deepcopy(VALID_VALUE_PERSONA_ARTIFACT_DATA)
    invalid["priority_ranking"].append(
        {
            **invalid["priority_ranking"][0],
            "priority": "重要用户",
        }
    )

    with pytest.raises(
        ValidationError,
        match="priority_ranking contains duplicate persona_id",
    ):
        ValueDiscoveryPersonaArtifactData.model_validate(invalid)


def test_value_journey_artifact_data_rejects_unknown_stage_reference():
    invalid = copy.deepcopy(VALID_VALUE_JOURNEY_ARTIFACT_DATA)
    invalid["pain_priorities"][0]["stage_id"] = "JS-404"

    with pytest.raises(ValidationError, match="references unknown stage ids"):
        ValueDiscoveryJourneyArtifactData.model_validate(invalid)


def test_value_journey_artifact_data_rejects_unknown_opportunity_reference():
    invalid = copy.deepcopy(VALID_VALUE_JOURNEY_ARTIFACT_DATA)
    invalid["validation_experiments"][0]["opportunity_id"] = "OPP-404"

    with pytest.raises(ValidationError, match="references unknown opportunity ids"):
        ValueDiscoveryJourneyArtifactData.model_validate(invalid)


def test_value_blueprint_artifact_data_rejects_unknown_requirement_reference():
    invalid = copy.deepcopy(VALID_VALUE_BLUEPRINT_ARTIFACT_DATA)
    invalid["acceptance_criteria"][0]["requirement_id"] = "F-404"

    with pytest.raises(ValidationError, match="references unknown requirement ids"):
        ValueDiscoveryBlueprintArtifactData.model_validate(invalid)


def test_value_blueprint_artifact_data_rejects_unknown_handoff_reference():
    invalid = copy.deepcopy(VALID_VALUE_BLUEPRINT_ARTIFACT_DATA)
    invalid["lisa_handoff_inputs"][1]["reference_id"] = "AC-404"

    with pytest.raises(ValidationError, match="references unknown acceptance ids"):
        ValueDiscoveryBlueprintArtifactData.model_validate(invalid)


def test_render_cases_artifact_data_is_contract_valid_and_asset_parseable():
    output = render_agent_turn_from_artifact_data(
        {
            "chat": "我已生成可执行测试用例集，请确认右侧内容。",
            "artifact_data": VALID_CASES_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "DELIVERY",
            },
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert output is not None
    assert output.artifact_update.markdown is not None
    assert "# 测试用例集" in output.artifact_update.markdown
    assert "```ai4se-visual" in output.artifact_update.markdown
    assert '"type": "traceability-matrix"' in output.artifact_update.markdown
    assert (
        validate_agent_turn(
            output,
            workflow_id="TEST_DESIGN",
            current_stage_id="CASES",
        )
        == output
    )

    parsed = parse_lisa_test_asset_markdown(output.artifact_update.markdown)
    assert [case["id"] for case in parsed["testCases"]] == ["TC-001", "TC-002"]
    assert parsed["coverageSummary"]["totalTestCases"] == 2
    assert parsed["riskMatrix"][0]["risk"] == "R-LOGIN-001"


def test_render_partial_cases_artifact_data_builds_formal_incremental_markdown_and_patch():
    statistics_payload = {
        "chat": "我正在生成测试用例集。",
        "artifact_data": {
            "document_info": VALID_CASES_ARTIFACT_DATA["document_info"],
            "case_statistics": VALID_CASES_ARTIFACT_DATA["case_statistics"],
        },
        "stage_action": None,
        "warnings": [],
    }

    statistics_output = render_partial_agent_turn_from_artifact_data(
        statistics_payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert statistics_output is not None
    assert statistics_output.artifact_update.markdown.startswith("# 测试用例集")
    assert "## 1. 用例统计" in statistics_output.artifact_update.markdown
    assert "## 2. 用例设计依据" not in statistics_output.artifact_update.markdown
    assert statistics_output.artifact_patch is None

    bases_payload = {
        **statistics_payload,
        "artifact_data": {
            **statistics_payload["artifact_data"],
            "design_bases": VALID_CASES_ARTIFACT_DATA["design_bases"],
        },
    }

    bases_output = render_partial_agent_turn_from_artifact_data(
        bases_payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert bases_output is not None
    assert "## 2. 用例设计依据" in bases_output.artifact_update.markdown
    assert "## 3. 按维度分组的用例清单" not in bases_output.artifact_update.markdown
    assert bases_output.artifact_patch is not None
    assert bases_output.artifact_patch.operation == "add_after"
    assert bases_output.artifact_patch.section_anchor == "h2:2. 用例设计依据:1"
    assert bases_output.artifact_patch.after_section_anchor == "h2:1. 用例统计:1"
    assert (
        bases_output.artifact_patch.base_content
        == statistics_output.artifact_update.markdown
    )
    assert "## 2. 用例设计依据" in (bases_output.artifact_patch.replacement_markdown)


def test_render_partial_delivery_artifact_data_builds_formal_incremental_markdown_and_patch():
    summary_payload = {
        "chat": "我正在形成测试设计交付文档。",
        "artifact_data": {
            "document_info": VALID_DELIVERY_ARTIFACT_DATA["document_info"],
            "executive_summary": VALID_DELIVERY_ARTIFACT_DATA["executive_summary"],
        },
        "stage_action": None,
        "warnings": [],
    }

    summary_output = render_partial_agent_turn_from_artifact_data(
        summary_payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    )

    assert summary_output is not None
    assert summary_output.artifact_update.markdown.startswith("# 测试设计文档")
    assert "## 1. 执行摘要" in summary_output.artifact_update.markdown
    assert "## 2. 需求分析摘要" not in summary_output.artifact_update.markdown
    assert "## 附录：文档信息" not in summary_output.artifact_update.markdown
    assert summary_output.artifact_patch is None

    requirement_payload = {
        **summary_payload,
        "artifact_data": {
            **summary_payload["artifact_data"],
            "requirement_summary": VALID_DELIVERY_ARTIFACT_DATA[
                "requirement_summary"
            ],
        },
    }
    requirement_output = render_partial_agent_turn_from_artifact_data(
        requirement_payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    )

    assert requirement_output is not None
    assert "## 2. 需求分析摘要" in requirement_output.artifact_update.markdown
    assert "## 3. 测试策略摘要" not in requirement_output.artifact_update.markdown
    assert requirement_output.artifact_patch is not None
    assert requirement_output.artifact_patch.operation == "add_after"
    assert (
        requirement_output.artifact_patch.section_anchor
        == "h2:2. 需求分析摘要:1"
    )
    assert (
        requirement_output.artifact_patch.after_section_anchor
        == "h2:1. 执行摘要:1"
    )
    assert (
        requirement_output.artifact_patch.base_content
        == summary_output.artifact_update.markdown
    )


def test_render_partial_req_review_artifact_data_builds_formal_incremental_markdown_and_patch():
    scope_payload = {
        "chat": "我正在生成需求评审问题清单。",
        "artifact_data": {
            "review_info": VALID_REQ_REVIEW_ARTIFACT_DATA["review_info"],
            "scope_items": VALID_REQ_REVIEW_ARTIFACT_DATA["scope_items"],
        },
        "stage_action": None,
        "warnings": [],
    }

    scope_output = render_partial_agent_turn_from_artifact_data(
        scope_payload,
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )

    assert scope_output is not None
    assert scope_output.artifact_update.markdown.startswith("# 需求评审问题清单")
    assert "## 评审范围与不评审范围" in scope_output.artifact_update.markdown
    assert "## 需求质量总览" not in scope_output.artifact_update.markdown
    assert scope_output.artifact_patch is None

    statistics_payload = {
        **scope_payload,
        "artifact_data": {
            **scope_payload["artifact_data"],
            "quality_overview": VALID_REQ_REVIEW_ARTIFACT_DATA[
                "quality_overview"
            ],
            "issue_statistics": VALID_REQ_REVIEW_ARTIFACT_DATA[
                "issue_statistics"
            ],
        },
    }
    statistics_output = render_partial_agent_turn_from_artifact_data(
        statistics_payload,
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )

    assert statistics_output is not None
    assert "## 问题统计" in statistics_output.artifact_update.markdown
    assert '"type": "score-matrix"' in statistics_output.artifact_update.markdown
    assert "## 按维度问题清单" not in statistics_output.artifact_update.markdown
    assert statistics_output.artifact_patch is not None
    assert statistics_output.artifact_patch.operation == "add_after"
    assert statistics_output.artifact_patch.section_anchor == "h2:问题统计:1"
    assert (
        statistics_output.artifact_patch.after_section_anchor
        == "h2:需求质量结构图:1"
    )


def test_render_partial_req_review_report_artifact_data_builds_formal_incremental_markdown_and_patch():
    conclusion_payload = {
        "chat": "我正在生成需求评审报告。",
        "artifact_data": {
            "conclusion": VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA["conclusion"],
        },
        "stage_action": None,
        "warnings": [],
    }

    conclusion_output = render_partial_agent_turn_from_artifact_data(
        conclusion_payload,
        workflow_id="REQ_REVIEW",
        current_stage_id="REPORT",
    )

    assert conclusion_output is not None
    assert conclusion_output.artifact_update.markdown.startswith("# 需求评审报告")
    assert "## 评审结论" in conclusion_output.artifact_update.markdown
    assert "## 评审信息" not in conclusion_output.artifact_update.markdown
    assert conclusion_output.artifact_patch is None

    statistics_payload = {
        **conclusion_payload,
        "artifact_data": {
            **conclusion_payload["artifact_data"],
            "review_info": VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA["review_info"],
            "issue_statistics": VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA[
                "issue_statistics"
            ],
        },
    }
    statistics_output = render_partial_agent_turn_from_artifact_data(
        statistics_payload,
        workflow_id="REQ_REVIEW",
        current_stage_id="REPORT",
    )

    assert statistics_output is not None
    assert "## 问题统计" in statistics_output.artifact_update.markdown
    assert "## 优先级看板" not in statistics_output.artifact_update.markdown
    assert statistics_output.artifact_patch is not None
    assert statistics_output.artifact_patch.operation == "add_after"
    assert statistics_output.artifact_patch.section_anchor == "h2:问题统计:1"
    assert (
        statistics_output.artifact_patch.after_section_anchor
        == "h2:评审信息:1"
    )


def test_render_partial_incident_timeline_artifact_data_builds_formal_incremental_markdown_and_patch():
    summary_payload = {
        "chat": "我正在还原故障事件时间线。",
        "artifact_data": {
            "incident_summary": VALID_INCIDENT_TIMELINE_ARTIFACT_DATA[
                "incident_summary"
            ],
        },
        "stage_action": None,
        "warnings": [],
    }

    summary_output = render_partial_agent_turn_from_artifact_data(
        summary_payload,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="TIMELINE",
    )

    assert summary_output is not None
    assert summary_output.artifact_update.markdown.startswith("# 故障复盘报告")
    assert "## 1. 事件概要" in summary_output.artifact_update.markdown
    assert "## 2. 影响量化" not in summary_output.artifact_update.markdown
    assert summary_output.artifact_patch is None

    impact_payload = {
        **summary_payload,
        "artifact_data": {
            **summary_payload["artifact_data"],
            "impact_metrics": VALID_INCIDENT_TIMELINE_ARTIFACT_DATA[
                "impact_metrics"
            ],
        },
    }
    impact_output = render_partial_agent_turn_from_artifact_data(
        impact_payload,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="TIMELINE",
    )

    assert impact_output is not None
    assert "## 2. 影响量化" in impact_output.artifact_update.markdown
    assert "## 3. 事实来源" not in impact_output.artifact_update.markdown
    assert impact_output.artifact_patch is not None
    assert impact_output.artifact_patch.operation == "add_after"
    assert impact_output.artifact_patch.section_anchor == "h2:2. 影响量化:1"
    assert (
        impact_output.artifact_patch.after_section_anchor
        == "h2:1. 事件概要:1"
    )


def test_render_partial_incident_root_cause_artifact_data_builds_formal_incremental_markdown_and_patch():
    context_payload = {
        "chat": "我正在分析故障根因。",
        "artifact_data": {
            "analysis_context": VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA[
                "analysis_context"
            ],
        },
        "stage_action": None,
        "warnings": [],
    }

    context_output = render_partial_agent_turn_from_artifact_data(
        context_payload,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="ROOT_CAUSE",
    )

    assert context_output is not None
    assert context_output.artifact_update.markdown.startswith("# 故障复盘报告")
    assert "## 6. 根因分析" in context_output.artifact_update.markdown
    assert "### 6.1 5-Why 分析链" not in context_output.artifact_update.markdown
    assert context_output.artifact_patch is None

    why_payload = {
        **context_payload,
        "artifact_data": {
            **context_payload["artifact_data"],
            "why_chain": VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA["why_chain"],
        },
    }
    why_output = render_partial_agent_turn_from_artifact_data(
        why_payload,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="ROOT_CAUSE",
    )

    assert why_output is not None
    assert "### 6.1 5-Why 分析链" in why_output.artifact_update.markdown
    assert '"type": "cause-map"' in why_output.artifact_update.markdown
    assert "### 6.2 根因证据表" not in why_output.artifact_update.markdown
    assert why_output.artifact_patch is not None
    assert why_output.artifact_patch.operation == "add_after"
    assert why_output.artifact_patch.section_anchor == "h3:6.1 5-Why 分析链:1"
    assert (
        why_output.artifact_patch.after_section_anchor
        == "h2:6. 根因分析:1"
    )


def test_render_partial_incident_improvement_artifact_data_builds_formal_incremental_markdown_and_patch():
    report_payload = {
        "chat": "我正在生成故障改进报告。",
        "artifact_data": {
            "report_info": VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA[
                "report_info"
            ],
        },
        "stage_action": None,
        "warnings": [],
    }

    report_output = render_partial_agent_turn_from_artifact_data(
        report_payload,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="IMPROVEMENT",
    )

    assert report_output is not None
    assert report_output.artifact_update.markdown.startswith("# 故障复盘报告")
    assert "## 报告信息" in report_output.artifact_update.markdown
    assert "## 第一部分：事件还原" not in report_output.artifact_update.markdown
    assert report_output.artifact_patch is None

    timeline_payload = {
        **report_payload,
        "artifact_data": {
            **report_payload["artifact_data"],
            "timeline_summary": VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA[
                "timeline_summary"
            ],
        },
    }
    timeline_output = render_partial_agent_turn_from_artifact_data(
        timeline_payload,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="IMPROVEMENT",
    )

    assert timeline_output is not None
    assert "## 第一部分：事件还原" in timeline_output.artifact_update.markdown
    assert "## 第二部分：根因分析" not in timeline_output.artifact_update.markdown
    assert timeline_output.artifact_patch is not None
    assert timeline_output.artifact_patch.operation == "add_after"
    assert (
        timeline_output.artifact_patch.section_anchor
        == "h2:第一部分：事件还原:1"
    )
    assert timeline_output.artifact_patch.after_section_anchor == "h2:报告信息:1"

    actions_payload = {
        **timeline_payload,
        "artifact_data": {
            **timeline_payload["artifact_data"],
            "root_cause_summary": VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA[
                "root_cause_summary"
            ],
            "priority_distribution": VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA[
                "priority_distribution"
            ],
            "improvement_actions": VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA[
                "improvement_actions"
            ],
        },
    }
    actions_output = render_partial_agent_turn_from_artifact_data(
        actions_payload,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="IMPROVEMENT",
    )

    assert actions_output is not None
    assert "## 第三部分：改进措施" in actions_output.artifact_update.markdown
    assert (
        "pie title 改进措施优先级分布"
        in actions_output.artifact_update.markdown
    )
    assert '"type": "action-board"' in actions_output.artifact_update.markdown
    assert "#### 7.3 根因覆盖检查" not in actions_output.artifact_update.markdown


def test_render_partial_idea_define_artifact_data_builds_formal_incremental_markdown_and_patch():
    statement_payload = {
        "chat": "我正在分析问题域。",
        "artifact_data": {
            "problem_statement": VALID_IDEA_DEFINE_ARTIFACT_DATA[
                "problem_statement"
            ],
        },
        "stage_action": None,
        "warnings": [],
    }

    statement_output = render_partial_agent_turn_from_artifact_data(
        statement_payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DEFINE",
    )

    assert statement_output is not None
    assert statement_output.artifact_update.markdown.startswith("# 问题域分析")
    assert "## 问题假设陈述" in statement_output.artifact_update.markdown
    assert "## 目标用户画像" not in statement_output.artifact_update.markdown
    assert statement_output.artifact_patch is None

    users_payload = {
        **statement_payload,
        "artifact_data": {
            **statement_payload["artifact_data"],
            "target_users": VALID_IDEA_DEFINE_ARTIFACT_DATA["target_users"],
        },
    }
    users_output = render_partial_agent_turn_from_artifact_data(
        users_payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DEFINE",
    )

    assert users_output is not None
    assert "## 目标用户画像" in users_output.artifact_update.markdown
    assert "## 问题域全景" not in users_output.artifact_update.markdown
    assert users_output.artifact_patch is not None
    assert users_output.artifact_patch.operation == "add_after"
    assert users_output.artifact_patch.section_anchor == "h2:目标用户画像:1"
    assert (
        users_output.artifact_patch.after_section_anchor
        == "h2:问题假设陈述:1"
    )
    assert (
        users_output.artifact_patch.base_content
        == statement_output.artifact_update.markdown
    )

    landscape_payload = {
        **users_payload,
        "artifact_data": {
            **users_payload["artifact_data"],
            "problem_landscape": VALID_IDEA_DEFINE_ARTIFACT_DATA[
                "problem_landscape"
            ],
        },
    }
    landscape_output = render_partial_agent_turn_from_artifact_data(
        landscape_payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DEFINE",
    )

    assert landscape_output is not None
    assert "## 问题域全景" in landscape_output.artifact_update.markdown
    assert "mindmap" in landscape_output.artifact_update.markdown
    assert "## 证据与验证状态" not in landscape_output.artifact_update.markdown
    assert landscape_output.artifact_patch is not None
    assert landscape_output.artifact_patch.section_anchor == "h2:问题域全景:1"
    assert (
        landscape_output.artifact_patch.after_section_anchor
        == "h2:目标用户画像:1"
    )


def test_render_partial_idea_diverge_artifact_data_builds_formal_incremental_markdown_and_patch():
    method_payload = {
        "chat": "我正在发散产品创意。",
        "artifact_data": {
            "divergence_method": VALID_IDEA_DIVERGE_ARTIFACT_DATA[
                "divergence_method"
            ],
        },
        "stage_action": None,
        "warnings": [],
    }

    method_output = render_partial_agent_turn_from_artifact_data(
        method_payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DIVERGE",
    )

    assert method_output is not None
    assert method_output.artifact_update.markdown.startswith("# 创意发散")
    assert "## 发散方法说明" in method_output.artifact_update.markdown
    assert "## 发散全景图" not in method_output.artifact_update.markdown
    assert method_output.artifact_patch is None

    cards_payload = {
        **method_payload,
        "artifact_data": {
            **method_payload["artifact_data"],
            "idea_landscape": VALID_IDEA_DIVERGE_ARTIFACT_DATA[
                "idea_landscape"
            ],
            "idea_cards": VALID_IDEA_DIVERGE_ARTIFACT_DATA["idea_cards"],
        },
    }
    cards_output = render_partial_agent_turn_from_artifact_data(
        cards_payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DIVERGE",
    )

    assert cards_output is not None
    assert "## 发散全景图" in cards_output.artifact_update.markdown
    assert "mindmap" in cards_output.artifact_update.markdown
    assert "## 创意卡片库" in cards_output.artifact_update.markdown
    assert "## 创意来源与假设" not in cards_output.artifact_update.markdown
    assert cards_output.artifact_patch is None

    sources_payload = {
        **cards_payload,
        "artifact_data": {
            **cards_payload["artifact_data"],
            "idea_sources": VALID_IDEA_DIVERGE_ARTIFACT_DATA["idea_sources"],
        },
    }
    sources_output = render_partial_agent_turn_from_artifact_data(
        sources_payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DIVERGE",
    )

    assert sources_output is not None
    assert "## 创意来源与假设" in sources_output.artifact_update.markdown
    assert "## 搁置/排除记录" not in sources_output.artifact_update.markdown
    assert sources_output.artifact_patch is not None
    assert sources_output.artifact_patch.operation == "add_after"
    assert (
        sources_output.artifact_patch.section_anchor
        == "h2:创意来源与假设:1"
    )
    assert (
        sources_output.artifact_patch.after_section_anchor
        == "h2:创意卡片库:1"
    )


def test_render_partial_idea_converge_artifact_data_builds_formal_incremental_markdown_and_patch():
    matrix_payload = {
        "chat": "我正在收敛创意方向。",
        "artifact_data": {
            "decision_matrix": VALID_IDEA_CONVERGE_ARTIFACT_DATA[
                "decision_matrix"
            ],
        },
        "stage_action": None,
        "warnings": [],
    }

    assert (
        render_partial_agent_turn_from_artifact_data(
            matrix_payload,
            workflow_id="IDEA_BRAINSTORM",
            current_stage_id="CONVERGE",
        )
        is None
    )

    evaluations_payload = {
        **matrix_payload,
        "artifact_data": {
            **matrix_payload["artifact_data"],
            "ice_evaluations": VALID_IDEA_CONVERGE_ARTIFACT_DATA[
                "ice_evaluations"
            ],
        },
    }
    evaluations_output = render_partial_agent_turn_from_artifact_data(
        evaluations_payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONVERGE",
    )

    assert evaluations_output is not None
    assert evaluations_output.artifact_update.markdown.startswith("# 收敛聚焦")
    assert "## 决策矩阵" in evaluations_output.artifact_update.markdown
    assert "quadrantChart" in evaluations_output.artifact_update.markdown
    assert "## ICE 评估表" in evaluations_output.artifact_update.markdown
    assert "## 资源约束" not in evaluations_output.artifact_update.markdown
    assert evaluations_output.artifact_patch is None

    resources_payload = {
        **evaluations_payload,
        "artifact_data": {
            **evaluations_payload["artifact_data"],
            "resource_constraints": VALID_IDEA_CONVERGE_ARTIFACT_DATA[
                "resource_constraints"
            ],
        },
    }
    resources_output = render_partial_agent_turn_from_artifact_data(
        resources_payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONVERGE",
    )

    assert resources_output is not None
    assert "## 资源约束" in resources_output.artifact_update.markdown
    assert "## 敏感性分析" not in resources_output.artifact_update.markdown
    assert resources_output.artifact_patch is not None
    assert resources_output.artifact_patch.operation == "add_after"
    assert resources_output.artifact_patch.section_anchor == "h2:资源约束:1"
    assert (
        resources_output.artifact_patch.after_section_anchor
        == "h2:ICE 评估表:1"
    )


def test_render_partial_idea_concept_artifact_data_builds_formal_incremental_markdown_and_patch():
    positioning_payload = {
        "chat": "我正在形成产品概念简报。",
        "artifact_data": {
            "positioning_statement": VALID_IDEA_CONCEPT_ARTIFACT_DATA[
                "positioning_statement"
            ],
        },
        "stage_action": None,
        "warnings": [],
    }

    positioning_output = render_partial_agent_turn_from_artifact_data(
        positioning_payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONCEPT",
    )

    assert positioning_output is not None
    assert positioning_output.artifact_update.markdown.startswith("# 产品概念简报")
    assert "## 定位声明" in positioning_output.artifact_update.markdown
    assert "## 核心假设" not in positioning_output.artifact_update.markdown
    assert positioning_output.artifact_patch is None

    assumptions_payload = {
        **positioning_payload,
        "artifact_data": {
            **positioning_payload["artifact_data"],
            "core_assumptions": VALID_IDEA_CONCEPT_ARTIFACT_DATA[
                "core_assumptions"
            ],
        },
    }
    assumptions_output = render_partial_agent_turn_from_artifact_data(
        assumptions_payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONCEPT",
    )

    assert assumptions_output is not None
    assert "## 核心假设" in assumptions_output.artifact_update.markdown
    assert "## Lean Canvas 产品画布" not in assumptions_output.artifact_update.markdown
    assert assumptions_output.artifact_patch is not None
    assert assumptions_output.artifact_patch.operation == "add_after"
    assert assumptions_output.artifact_patch.section_anchor == "h2:核心假设:1"
    assert (
        assumptions_output.artifact_patch.after_section_anchor
        == "h2:定位声明:1"
    )

    canvas_payload = {
        **assumptions_payload,
        "artifact_data": {
            **assumptions_payload["artifact_data"],
            "lean_canvas": VALID_IDEA_CONCEPT_ARTIFACT_DATA["lean_canvas"],
        },
    }
    canvas_output = render_partial_agent_turn_from_artifact_data(
        canvas_payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONCEPT",
    )

    assert canvas_output is not None
    assert "## Lean Canvas 产品画布" in canvas_output.artifact_update.markdown
    assert "## MVP 功能分布" not in canvas_output.artifact_update.markdown
    assert canvas_output.artifact_patch is not None
    assert (
        canvas_output.artifact_patch.section_anchor
        == "h2:Lean Canvas 产品画布:1"
    )

    mvp_payload = {
        **canvas_payload,
        "artifact_data": {
            **canvas_payload["artifact_data"],
            "mvp_features": VALID_IDEA_CONCEPT_ARTIFACT_DATA["mvp_features"],
        },
    }
    mvp_output = render_partial_agent_turn_from_artifact_data(
        mvp_payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONCEPT",
    )

    assert mvp_output is not None
    assert "## MVP 功能分布" in mvp_output.artifact_update.markdown
    assert "pie title MVP 功能组成" in mvp_output.artifact_update.markdown
    assert '"type": "mvp-map"' in mvp_output.artifact_update.markdown
    assert "## 核心增长漏斗" not in mvp_output.artifact_update.markdown
    assert mvp_output.artifact_patch is not None
    assert mvp_output.artifact_patch.section_anchor == "h2:MVP 功能分布:1"
    assert (
        mvp_output.artifact_patch.after_section_anchor
        == "h2:Lean Canvas 产品画布:1"
    )


def test_render_partial_value_elevator_artifact_data_builds_formal_incremental_markdown_and_patch():
    summary_payload = {
        "chat": "我正在生成价值定位分析。",
        "artifact_data": {
            "document_info": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["document_info"],
            "positioning_summary": VALID_VALUE_ELEVATOR_ARTIFACT_DATA[
                "positioning_summary"
            ],
        },
        "stage_action": None,
        "warnings": [],
    }

    summary_output = render_partial_agent_turn_from_artifact_data(
        summary_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert summary_output is not None
    assert summary_output.artifact_update.markdown.startswith("# 价值定位分析")
    assert "## 定位摘要" in summary_output.artifact_update.markdown
    assert "## 价值结构图" not in summary_output.artifact_update.markdown
    assert summary_output.artifact_patch is None

    flow_payload = {
        **summary_payload,
        "artifact_data": {
            **summary_payload["artifact_data"],
            "value_flow": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["value_flow"],
        },
    }
    flow_output = render_partial_agent_turn_from_artifact_data(
        flow_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert flow_output is not None
    assert "## 价值结构图" in flow_output.artifact_update.markdown
    assert "flowchart TD" in flow_output.artifact_update.markdown
    assert "## 目标用户与场景" not in flow_output.artifact_update.markdown
    assert flow_output.artifact_patch is not None
    assert flow_output.artifact_patch.operation == "add_after"
    assert flow_output.artifact_patch.section_anchor == "h2:价值结构图:1"
    assert flow_output.artifact_patch.after_section_anchor == "h2:定位摘要:1"

    score_payload = {
        **flow_payload,
        "artifact_data": {
            **flow_payload["artifact_data"],
            "target_scenarios": VALID_VALUE_ELEVATOR_ARTIFACT_DATA[
                "target_scenarios"
            ],
            "pain_evidence": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["pain_evidence"],
            "differentiators": VALID_VALUE_ELEVATOR_ARTIFACT_DATA[
                "differentiators"
            ],
            "business_feasibility": VALID_VALUE_ELEVATOR_ARTIFACT_DATA[
                "business_feasibility"
            ],
            "score_matrix": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["score_matrix"],
            "score_summary": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["score_summary"],
        },
    }
    score_output = render_partial_agent_turn_from_artifact_data(
        score_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert score_output is not None
    assert "## 价值主张评分" in score_output.artifact_update.markdown
    assert '"type": "score-matrix"' in score_output.artifact_update.markdown
    assert "## 未验证假设" not in score_output.artifact_update.markdown
    assert score_output.artifact_patch is not None
    assert score_output.artifact_patch.section_anchor == "h2:价值主张评分:1"


def test_render_partial_value_persona_artifact_data_builds_formal_incremental_markdown_and_patch():
    summary_payload = {
        "chat": "我正在生成用户画像分析。",
        "artifact_data": {
            "document_info": VALID_VALUE_PERSONA_ARTIFACT_DATA["document_info"],
            "persona_summary": VALID_VALUE_PERSONA_ARTIFACT_DATA["persona_summary"],
        },
        "stage_action": None,
        "warnings": [],
    }

    summary_output = render_partial_agent_turn_from_artifact_data(
        summary_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="PERSONA",
    )

    assert summary_output is not None
    assert summary_output.artifact_update.markdown.startswith("# 用户画像分析")
    assert "## 画像摘要" in summary_output.artifact_update.markdown
    assert "## 主要用户画像" not in summary_output.artifact_update.markdown
    assert summary_output.artifact_patch is None

    personas_payload = {
        **summary_payload,
        "artifact_data": {
            **summary_payload["artifact_data"],
            "personas": VALID_VALUE_PERSONA_ARTIFACT_DATA["personas"],
        },
    }
    personas_output = render_partial_agent_turn_from_artifact_data(
        personas_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="PERSONA",
    )

    assert personas_output is not None
    assert "## 主要用户画像" in personas_output.artifact_update.markdown
    assert "### 画像 1" in personas_output.artifact_update.markdown
    assert "#### 基础特征" in personas_output.artifact_update.markdown
    assert "## 行为与场景" not in personas_output.artifact_update.markdown
    assert personas_output.artifact_patch is None

    behavior_payload = {
        **personas_payload,
        "artifact_data": {
            **personas_payload["artifact_data"],
            "behavior_scenarios": VALID_VALUE_PERSONA_ARTIFACT_DATA[
                "behavior_scenarios"
            ],
        },
    }
    behavior_output = render_partial_agent_turn_from_artifact_data(
        behavior_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="PERSONA",
    )

    assert behavior_output is not None
    assert "## 行为与场景" in behavior_output.artifact_update.markdown
    assert "## 决策链" not in behavior_output.artifact_update.markdown
    assert behavior_output.artifact_patch is not None
    assert behavior_output.artifact_patch.section_anchor == "h2:行为与场景:1"


def test_render_partial_value_journey_artifact_data_builds_formal_incremental_markdown_and_patch():
    stages_payload = {
        "chat": "我正在生成用户旅程分析。",
        "artifact_data": {
            "document_info": VALID_VALUE_JOURNEY_ARTIFACT_DATA["document_info"],
            "journey_stages": VALID_VALUE_JOURNEY_ARTIFACT_DATA["journey_stages"],
        },
        "stage_action": None,
        "warnings": [],
    }

    stages_output = render_partial_agent_turn_from_artifact_data(
        stages_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="JOURNEY",
    )

    assert stages_output is not None
    assert stages_output.artifact_update.markdown.startswith("# 用户旅程分析")
    assert "## 用户旅程地图" in stages_output.artifact_update.markdown
    assert "journey\n    title 核心用户旅程" in stages_output.artifact_update.markdown
    assert '"type": "journey-map"' in stages_output.artifact_update.markdown
    assert "## 痛点优先级排序" not in stages_output.artifact_update.markdown
    assert stages_output.artifact_patch is None

    pain_payload = {
        **stages_payload,
        "artifact_data": {
            **stages_payload["artifact_data"],
            "pain_priorities": VALID_VALUE_JOURNEY_ARTIFACT_DATA[
                "pain_priorities"
            ],
        },
    }
    pain_output = render_partial_agent_turn_from_artifact_data(
        pain_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="JOURNEY",
    )

    assert pain_output is not None
    assert "## 痛点优先级排序" in pain_output.artifact_update.markdown
    assert "高优先级痛点" in pain_output.artifact_update.markdown
    assert "## 机会评分" not in pain_output.artifact_update.markdown

    opportunity_payload = {
        **pain_payload,
        "artifact_data": {
            **pain_payload["artifact_data"],
            "opportunity_scores": VALID_VALUE_JOURNEY_ARTIFACT_DATA[
                "opportunity_scores"
            ],
        },
    }
    opportunity_output = render_partial_agent_turn_from_artifact_data(
        opportunity_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="JOURNEY",
    )

    assert opportunity_output is not None
    assert "## 机会评分" in opportunity_output.artifact_update.markdown
    assert "## 产品切入策略" not in opportunity_output.artifact_update.markdown
    assert opportunity_output.artifact_patch is not None
    assert opportunity_output.artifact_patch.section_anchor == "h2:机会评分:1"


def test_render_partial_value_blueprint_artifact_data_builds_formal_incremental_markdown_and_patch():
    overview_payload = {
        "chat": "我正在生成需求蓝图。",
        "artifact_data": {
            "document_info": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA["document_info"],
            "product_overview": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA[
                "product_overview"
            ],
        },
        "stage_action": None,
        "warnings": [],
    }

    overview_output = render_partial_agent_turn_from_artifact_data(
        overview_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    )

    assert overview_output is not None
    assert overview_output.artifact_update.markdown.startswith(
        "# AI4SE 测试设计助手 需求蓝图"
    )
    assert "## 1. 产品概述" in overview_output.artifact_update.markdown
    assert "## 2. 目标用户（摘要）" not in overview_output.artifact_update.markdown
    assert overview_output.artifact_patch is None

    users_payload = {
        **overview_payload,
        "artifact_data": {
            **overview_payload["artifact_data"],
            "target_users": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA["target_users"],
        },
    }
    users_output = render_partial_agent_turn_from_artifact_data(
        users_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    )

    assert users_output is not None
    assert "## 2. 目标用户（摘要）" in users_output.artifact_update.markdown
    assert "## 3. 核心需求" not in users_output.artifact_update.markdown
    assert users_output.artifact_patch is not None
    assert users_output.artifact_patch.section_anchor == "h2:2. 目标用户（摘要）:1"

    requirements_payload = {
        **users_payload,
        "artifact_data": {
            **users_payload["artifact_data"],
            "feature_modules": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA[
                "feature_modules"
            ],
            "requirements": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA["requirements"],
        },
    }
    requirements_output = render_partial_agent_turn_from_artifact_data(
        requirements_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    )

    assert requirements_output is not None
    assert "## 3. 核心需求" in requirements_output.artifact_update.markdown
    assert "mindmap" in requirements_output.artifact_update.markdown
    assert "## 4. 核心流程" not in requirements_output.artifact_update.markdown

    flow_payload = {
        **requirements_payload,
        "artifact_data": {
            **requirements_payload["artifact_data"],
            "main_flow": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA["main_flow"],
        },
    }
    flow_output = render_partial_agent_turn_from_artifact_data(
        flow_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    )

    assert flow_output is not None
    assert "## 4. 核心流程" in flow_output.artifact_update.markdown
    assert "flowchart TD" in flow_output.artifact_update.markdown
    assert "## 5. 成功指标" not in flow_output.artifact_update.markdown


def test_render_delivery_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "我已整理测试设计交付文档，请确认右侧终稿。",
            "artifact_data": VALID_DELIVERY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "我已整理测试设计交付文档，请确认右侧终稿。",
            "artifact_data": VALID_DELIVERY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    delivery_markdown = first.artifact_update.markdown
    assert "# 测试设计文档" in first.artifact_update.markdown
    assert "## 9. 变更记录" in delivery_markdown
    assert delivery_markdown.index("## 1. 执行摘要") < delivery_markdown.index(
        "## 附录：文档信息"
    )
    assert "```ai4se-visual" in first.artifact_update.markdown
    assert '"type": "coverage-map"' in first.artifact_update.markdown
    assert '"type": "traceability-matrix"' in first.artifact_update.markdown
    assert "需求/风险/测试点" in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="TEST_DESIGN",
            current_stage_id="DELIVERY",
        )
        == first
    )


def test_render_req_review_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "我已完成需求质量诊断，请确认右侧问题清单。",
            "artifact_data": VALID_REQ_REVIEW_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "REPORT",
            },
            "warnings": [],
        },
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "我已完成需求质量诊断，请确认右侧问题清单。",
            "artifact_data": VALID_REQ_REVIEW_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "REPORT",
            },
            "warnings": [],
        },
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    review_markdown = first.artifact_update.markdown
    assert "# 需求评审问题清单" in first.artifact_update.markdown
    assert review_markdown.index("## 需求质量总览") < review_markdown.index(
        "## 附录：评审信息"
    )
    assert "flowchart TD" in first.artifact_update.markdown
    assert "```ai4se-visual" in first.artifact_update.markdown
    assert '"type": "score-matrix"' in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="REQ_REVIEW",
            current_stage_id="REVIEW",
        )
        == first
    )


def test_render_req_review_report_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "我已整理正式需求评审报告，请确认右侧内容。",
            "artifact_data": VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="REQ_REVIEW",
        current_stage_id="REPORT",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "我已整理正式需求评审报告，请确认右侧内容。",
            "artifact_data": VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="REQ_REVIEW",
        current_stage_id="REPORT",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert "# 需求评审报告" in first.artifact_update.markdown
    assert "pie title 评审问题优先级分布" in first.artifact_update.markdown
    assert "```ai4se-visual" in first.artifact_update.markdown
    assert '"type": "priority-board"' in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="REQ_REVIEW",
            current_stage_id="REPORT",
        )
        == first
    )


def test_render_value_elevator_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成价值定位分析。",
            "artifact_data": VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "PERSONA",
            },
            "warnings": [],
        },
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成价值定位分析。",
            "artifact_data": VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "PERSONA",
            },
            "warnings": [],
        },
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert first.artifact_update.type == "replace"
    assert first.stage_action is not None
    assert first.stage_action.target_stage_id == "PERSONA"
    assert "# 价值定位分析" in first.artifact_update.markdown
    assert "flowchart TD" in first.artifact_update.markdown
    assert '"type": "score-matrix"' in first.artifact_update.markdown
    assert "60 秒电梯演讲" in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="VALUE_DISCOVERY",
            current_stage_id="ELEVATOR",
        )
        == first
    )


def test_render_value_persona_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成用户画像分析。",
            "artifact_data": VALID_VALUE_PERSONA_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "JOURNEY",
            },
            "warnings": [],
        },
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="PERSONA",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成用户画像分析。",
            "artifact_data": VALID_VALUE_PERSONA_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "JOURNEY",
            },
            "warnings": [],
        },
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="PERSONA",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert first.artifact_update.type == "replace"
    assert first.stage_action is not None
    assert first.stage_action.target_stage_id == "JOURNEY"
    assert "# 用户画像分析" in first.artifact_update.markdown
    assert "### 画像 1" in first.artifact_update.markdown
    assert "#### 基础特征" in first.artifact_update.markdown
    assert "#### 行为特征" in first.artifact_update.markdown
    assert "## 决策链" in first.artifact_update.markdown
    assert "## 用户优先级排序" in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="VALUE_DISCOVERY",
            current_stage_id="PERSONA",
        )
        == first
    )


def test_render_value_journey_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成用户旅程分析。",
            "artifact_data": VALID_VALUE_JOURNEY_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "BLUEPRINT",
            },
            "warnings": [],
        },
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="JOURNEY",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成用户旅程分析。",
            "artifact_data": VALID_VALUE_JOURNEY_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "BLUEPRINT",
            },
            "warnings": [],
        },
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="JOURNEY",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert first.artifact_update.type == "replace"
    assert first.stage_action is not None
    assert first.stage_action.target_stage_id == "BLUEPRINT"
    assert "# 用户旅程分析" in first.artifact_update.markdown
    assert "journey\n    title 核心用户旅程" in first.artifact_update.markdown
    assert "## 结构化旅程地图" in first.artifact_update.markdown
    assert '"type": "journey-map"' in first.artifact_update.markdown
    assert "## 痛点优先级排序" in first.artifact_update.markdown
    assert "高优先级痛点" in first.artifact_update.markdown
    assert "中等优先级痛点" in first.artifact_update.markdown
    assert "低优先级痛点" in first.artifact_update.markdown
    assert "## 机会评分" in first.artifact_update.markdown
    assert "## 产品切入策略" in first.artifact_update.markdown
    assert "## 验证实验" in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="VALUE_DISCOVERY",
            current_stage_id="JOURNEY",
        )
        == first
    )


def test_render_value_blueprint_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成需求蓝图。",
            "artifact_data": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成需求蓝图。",
            "artifact_data": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    blueprint_markdown = first.artifact_update.markdown
    assert first.artifact_update.type == "replace"
    assert first.stage_action is None
    assert "# AI4SE 测试设计助手 需求蓝图" in first.artifact_update.markdown
    assert blueprint_markdown.index("## 1. 产品概述") < blueprint_markdown.index(
        "## 附录：文档信息"
    )
    assert "### 功能架构" in first.artifact_update.markdown
    assert "mindmap" in first.artifact_update.markdown
    assert "### 主流程图" in first.artifact_update.markdown
    assert "flowchart TD" in first.artifact_update.markdown
    assert "## 9. 路线图" in first.artifact_update.markdown
    assert '"type": "roadmap"' in first.artifact_update.markdown
    assert "## 11. Lisa Handoff 输入" in first.artifact_update.markdown
    assert "可测试性等级" in first.artifact_update.markdown
    assert "owner" in first.artifact_update.markdown
    assert "状态" in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="VALUE_DISCOVERY",
            current_stage_id="BLUEPRINT",
        )
        == first
    )


def test_render_incident_timeline_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已还原故障事件时间线。",
            "artifact_data": VALID_INCIDENT_TIMELINE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "ROOT_CAUSE",
            },
            "warnings": [],
        },
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="TIMELINE",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已还原故障事件时间线。",
            "artifact_data": VALID_INCIDENT_TIMELINE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "ROOT_CAUSE",
            },
            "warnings": [],
        },
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="TIMELINE",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert first.artifact_update.type == "replace"
    assert first.stage_action is not None
    assert first.stage_action.target_stage_id == "ROOT_CAUSE"
    assert "# 故障复盘报告" in first.artifact_update.markdown
    assert "## 1. 事件概要" in first.artifact_update.markdown
    assert "## 2. 影响量化" in first.artifact_update.markdown
    assert "## 3. 事实来源" in first.artifact_update.markdown
    assert "## 4. 事件时间线" in first.artifact_update.markdown
    assert "timeline\n    title 支付回调失败导致订单状态延迟 事件时间线" in (
        first.artifact_update.markdown
    )
    assert "14：30 : 订单状态延迟告警触发" in first.artifact_update.markdown
    assert "14:30 : 订单状态延迟告警触发" not in first.artifact_update.markdown
    assert "## 5. 事实/推测隔离" in first.artifact_update.markdown
    assert "## 6. 事实摘要" in first.artifact_update.markdown
    assert "## 7. 参与人员" in first.artifact_update.markdown
    assert "## 8. 待补充信息" in first.artifact_update.markdown
    assert "## 9. 阶段门禁" in first.artifact_update.markdown
    assert "可信度" in first.artifact_update.markdown
    assert "阻断性" in first.artifact_update.markdown
    assert "状态" in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="INCIDENT_REVIEW",
            current_stage_id="TIMELINE",
        )
        == first
    )


def test_render_incident_root_cause_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已完成根因分析，请确认右侧 5-Why 和鱼骨图。",
            "artifact_data": VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "IMPROVEMENT",
            },
            "warnings": [],
        },
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="ROOT_CAUSE",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已完成根因分析，请确认右侧 5-Why 和鱼骨图。",
            "artifact_data": VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "IMPROVEMENT",
            },
            "warnings": [],
        },
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="ROOT_CAUSE",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert first.artifact_update.type == "replace"
    assert first.stage_action is not None
    assert first.stage_action.target_stage_id == "IMPROVEMENT"
    assert "# 故障复盘报告" in first.artifact_update.markdown
    assert "## 6. 根因分析" in first.artifact_update.markdown
    assert "### 6.1 5-Why 分析链" in first.artifact_update.markdown
    assert '"type": "cause-map"' in first.artifact_update.markdown
    assert "### 6.2 根因证据表" in first.artifact_update.markdown
    assert "### 6.3 原因鱼骨图" in first.artifact_update.markdown
    assert "mindmap" in first.artifact_update.markdown
    assert 'root(("支付回调失败导致订单状态延迟"))' in (first.artifact_update.markdown)
    assert "### 6.4 根因结论" in first.artifact_update.markdown
    assert "### 6.5 排除项" in first.artifact_update.markdown
    assert "### 6.6 未验证原因" in first.artifact_update.markdown
    assert "### 6.7 阶段门禁" in first.artifact_update.markdown
    assert "证据强度" in first.artifact_update.markdown
    assert "置信度" in first.artifact_update.markdown
    assert "可行动性" in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="INCIDENT_REVIEW",
            current_stage_id="ROOT_CAUSE",
        )
        == first
    )


def test_render_incident_improvement_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已完成故障改进报告，请确认右侧行动项和复查计划。",
            "artifact_data": VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="IMPROVEMENT",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已完成故障改进报告，请确认右侧行动项和复查计划。",
            "artifact_data": VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="IMPROVEMENT",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert first.artifact_update.type == "replace"
    assert first.stage_action is None
    assert "# 故障复盘报告" in first.artifact_update.markdown
    assert "## 报告信息" in first.artifact_update.markdown
    assert "## 第一部分：事件还原" in first.artifact_update.markdown
    assert "## 第二部分：根因分析" in first.artifact_update.markdown
    assert "## 第三部分：改进措施" in first.artifact_update.markdown
    assert "### 7. 改进措施" in first.artifact_update.markdown
    assert "#### 7.1 改进优先级分布" in first.artifact_update.markdown
    assert "pie title 改进措施优先级分布" in first.artifact_update.markdown
    assert "#### 7.2 改进行动清单" in first.artifact_update.markdown
    assert '"type": "action-board"' in first.artifact_update.markdown
    assert "#### 7.3 根因覆盖检查" in first.artifact_update.markdown
    assert "### 8. 防复发检查清单" in first.artifact_update.markdown
    assert "### 9. 复查计划" in first.artifact_update.markdown
    assert "### 10. 遗留风险与风险接受" in first.artifact_update.markdown
    assert "### 11. 经验教训" in first.artifact_update.markdown
    assert "### 12. 组织学习" in first.artifact_update.markdown
    assert "## 签署确认" in first.artifact_update.markdown
    assert "### 13. 阶段门禁" in first.artifact_update.markdown
    for keyword in [
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
    ]:
        assert keyword in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="INCIDENT_REVIEW",
            current_stage_id="IMPROVEMENT",
        )
        == first
    )


def test_render_idea_define_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已形成问题域验证基线，请确认右侧问题域分析。",
            "artifact_data": VALID_IDEA_DEFINE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "DIVERGE",
            },
            "warnings": [],
        },
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DEFINE",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已形成问题域验证基线，请确认右侧问题域分析。",
            "artifact_data": VALID_IDEA_DEFINE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "DIVERGE",
            },
            "warnings": [],
        },
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DEFINE",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert first.artifact_update.type == "replace"
    assert first.stage_action is not None
    assert first.stage_action.target_stage_id == "DIVERGE"
    assert "# 问题域分析" in first.artifact_update.markdown
    assert "## 问题假设陈述" in first.artifact_update.markdown
    assert "## 目标用户画像" in first.artifact_update.markdown
    assert "## 问题域全景" in first.artifact_update.markdown
    assert "mindmap" in first.artifact_update.markdown
    assert 'root(("独立开发者变现方向选择困难"))' in (first.artifact_update.markdown)
    assert "## 证据与验证状态" in first.artifact_update.markdown
    assert "## 问题-用户-场景匹配" in first.artifact_update.markdown
    assert "## 约束与边界" in first.artifact_update.markdown
    assert "## 反向验证（风险思考）" in first.artifact_update.markdown
    assert "## 阶段门禁" in first.artifact_update.markdown
    assert "证据等级" in first.artifact_update.markdown
    assert "验证动作" in first.artifact_update.markdown
    assert "验证状态" in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="IDEA_BRAINSTORM",
            current_stage_id="DEFINE",
        )
        == first
    )


def test_render_idea_diverge_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已形成创意发散候选集，请确认右侧创意卡片库。",
            "artifact_data": VALID_IDEA_DIVERGE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CONVERGE",
            },
            "warnings": [],
        },
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DIVERGE",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已形成创意发散候选集，请确认右侧创意卡片库。",
            "artifact_data": VALID_IDEA_DIVERGE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CONVERGE",
            },
            "warnings": [],
        },
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DIVERGE",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert first.artifact_update.type == "replace"
    assert first.stage_action is not None
    assert first.stage_action.target_stage_id == "CONVERGE"
    assert "# 创意发散" in first.artifact_update.markdown
    assert "## 发散方法说明" in first.artifact_update.markdown
    assert "## 发散全景图" in first.artifact_update.markdown
    assert "mindmap" in first.artifact_update.markdown
    assert 'root(("独立开发者变现方向选择辅助"))' in (first.artifact_update.markdown)
    assert "## 创意卡片库" in first.artifact_update.markdown
    assert "## 创意来源与假设" in first.artifact_update.markdown
    assert "## 搁置/排除记录" in first.artifact_update.markdown
    assert "## 阶段门禁" in first.artifact_update.markdown
    assert "关键假设" in first.artifact_update.markdown
    assert "状态理由" in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="IDEA_BRAINSTORM",
            current_stage_id="DIVERGE",
        )
        == first
    )


def test_render_idea_converge_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已完成创意收敛评估，请确认右侧推荐方案。",
            "artifact_data": VALID_IDEA_CONVERGE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CONCEPT",
            },
            "warnings": [],
        },
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONVERGE",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已完成创意收敛评估，请确认右侧推荐方案。",
            "artifact_data": VALID_IDEA_CONVERGE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CONCEPT",
            },
            "warnings": [],
        },
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONVERGE",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert first.artifact_update.type == "replace"
    assert first.stage_action is not None
    assert first.stage_action.target_stage_id == "CONCEPT"
    assert "# 收敛聚焦" in first.artifact_update.markdown
    assert "## 决策矩阵" in first.artifact_update.markdown
    assert "quadrantChart" in first.artifact_update.markdown
    assert "## ICE 评估表" in first.artifact_update.markdown
    assert "## 资源约束" in first.artifact_update.markdown
    assert "## 敏感性分析" in first.artifact_update.markdown
    assert "## 验证实验" in first.artifact_update.markdown
    assert "## 整合演进路径（如果触发合并）" in first.artifact_update.markdown
    assert "## 阶段门禁" in first.artifact_update.markdown
    for keyword in [
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
    ]:
        assert keyword in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="IDEA_BRAINSTORM",
            current_stage_id="CONVERGE",
        )
        == first
    )


def test_render_idea_concept_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已完成产品概念简报，请查看右侧 MVP 和验证路线。",
            "artifact_data": VALID_IDEA_CONCEPT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONCEPT",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已完成产品概念简报，请查看右侧 MVP 和验证路线。",
            "artifact_data": VALID_IDEA_CONCEPT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONCEPT",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert first.artifact_update.type == "replace"
    assert first.stage_action is None
    assert "# 产品概念简报" in first.artifact_update.markdown
    assert "## 定位声明" in first.artifact_update.markdown
    assert "## 核心假设" in first.artifact_update.markdown
    assert "## Lean Canvas 产品画布" in first.artifact_update.markdown
    assert "## MVP 功能分布" in first.artifact_update.markdown
    assert "pie title MVP 功能组成" in first.artifact_update.markdown
    assert "## 核心增长漏斗" in first.artifact_update.markdown
    assert "flowchart TD" in first.artifact_update.markdown
    assert '"type": "mvp-map"' in first.artifact_update.markdown
    assert "## Pre-mortem 风险分析" in first.artifact_update.markdown
    assert "## 验证路线" in first.artifact_update.markdown
    assert "## 不可做范围" in first.artifact_update.markdown
    assert "## 决策记录" in first.artifact_update.markdown
    assert "## 下一步行动" in first.artifact_update.markdown
    assert "## 阶段门禁" in first.artifact_update.markdown
    assert "owner" in first.artifact_update.markdown
    assert "状态" in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="IDEA_BRAINSTORM",
            current_stage_id="CONCEPT",
        )
        == first
    )
