import copy

import pytest
from pydantic import ValidationError

from agent_contracts import validate_agent_turn
from artifact_data_renderers import (
    CasesArtifactData,
    ClarifyArtifactData,
    DeliveryArtifactData,
    ReqReviewArtifactData,
    ReqReviewReportArtifactData,
    StrategyArtifactData,
    ValueDiscoveryElevatorArtifactData,
    ValueDiscoveryJourneyArtifactData,
    ValueDiscoveryPersonaArtifactData,
    render_agent_turn_from_artifact_data,
)
from test_asset_parsing import parse_lisa_test_asset_markdown

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
    assert "# 需求分析文档" in first.artifact_update.markdown
    assert "## 8. 阶段门禁" in first.artifact_update.markdown
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
    assert "# 测试设计文档" in first.artifact_update.markdown
    assert "## 10. 变更记录" in first.artifact_update.markdown
    assert "```ai4se-visual" in first.artifact_update.markdown
    assert '"type": "coverage-map"' in first.artifact_update.markdown
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
    assert "# 需求评审问题清单" in first.artifact_update.markdown
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
