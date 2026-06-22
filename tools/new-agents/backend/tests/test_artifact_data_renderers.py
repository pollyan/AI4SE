import pytest
from pydantic import ValidationError

from agent_contracts import validate_agent_turn
from artifact_data_renderers import (
    CasesArtifactData,
    ClarifyArtifactData,
    StrategyArtifactData,
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
