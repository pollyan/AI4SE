import pytest

from agent_contracts import (
    AgentTurnOutput,
    ArtifactUpdate,
    ContractValidationError,
    REQUIRED_ARTIFACT_HEADINGS,
    REQUIRED_ARTIFACT_MERMAID_DIAGRAMS,
    REQUIRED_ARTIFACT_STRUCTURED_VISUALS,
    StageAction,
    WORKFLOW_STAGES,
    build_artifact_contract_prompt,
    validate_agent_turn,
)


def _complete_markdown(required_headings: list[str]) -> str:
    return "\n\n".join(
        f"{heading}\n该章节用于验证完整合法模板可通过契约校验。"
        for heading in required_headings
    )


def _complete_marked_heading_markdown(required_headings: list[str]) -> str:
    marked_headings = [
        heading.replace(" ", " <mark>", 1) + "</mark>"
        if heading.startswith("#")
        else heading
        for heading in required_headings
    ]
    return _complete_markdown(marked_headings)


def _minimal_mermaid_block(diagram_type: str) -> str:
    return f"```mermaid\n{diagram_type}\n```\n"


def _minimal_structured_visual_block(visual_type: str) -> str:
    return (
        "```ai4se-visual\n"
        "{\n"
        f'  "type": "{visual_type}",\n'
        '  "title": "需求-风险-测试点-用例追溯矩阵",\n'
        '  "columns": ["需求", "风险", "测试点", "用例", "覆盖状态"],\n'
        '  "rows": [\n'
        '    {"需求": "REQ-1", "风险": "RISK-1", "测试点": "TP-1", "用例": "TC-1", "覆盖状态": "已覆盖"}\n'
        "  ]\n"
        "}\n"
        "```\n"
    )


def _complete_markdown_for_stage(workflow_id: str, stage_id: str) -> str:
    markdown = _complete_markdown(
        REQUIRED_ARTIFACT_HEADINGS[(workflow_id, stage_id)]
    )
    visual_blocks = [
        _minimal_mermaid_block(diagram_type)
        for diagram_type in REQUIRED_ARTIFACT_MERMAID_DIAGRAMS.get(
            (workflow_id, stage_id),
            [],
        )
    ]
    visual_blocks.extend(
        _minimal_structured_visual_block(visual_type)
        for visual_type in REQUIRED_ARTIFACT_STRUCTURED_VISUALS.get(
            (workflow_id, stage_id),
            [],
        )
    )
    if visual_blocks:
        return markdown + "\n\n" + "\n\n".join(visual_blocks)
    return markdown


def test_agent_turn_output_accepts_structured_artifact_update():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧需求分析文档，请确认。",
            "artifact_update": {
                "type": "replace",
                "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
            },
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "STRATEGY",
            },
            "warnings": [],
        }
    )

    assert output.chat == "已更新右侧需求分析文档，请确认。"
    assert isinstance(output.artifact_update, ArtifactUpdate)
    assert output.artifact_update.type == "replace"
    assert isinstance(output.stage_action, StageAction)
    assert output.stage_action.target_stage_id == "STRATEGY"


def test_agent_turn_output_accepts_json_string_encoded_artifact_update():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧需求分析文档，请确认。",
            "artifact_update": (
                '{"type":"replace","markdown":"# 需求分析文档\\n\\n'
                '## 1. 被测系统与边界\\n内容"}'
            ),
            "stage_action": None,
            "warnings": [],
        }
    )

    assert isinstance(output.artifact_update, ArtifactUpdate)
    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown == (
        "# 需求分析文档\n\n## 1. 被测系统与边界\n内容"
    )


def test_artifact_contract_prompt_includes_exact_next_stage_action_target():
    prompt = build_artifact_contract_prompt(
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert '"target_stage_id": "STRATEGY"' in prompt
    assert "不要填写阶段中文名称" in prompt
    assert "前端显示确认控件" in prompt
    assert "自然工作对话" in prompt
    assert "简短中文说明" not in prompt
    assert "只有用户明确确认进入下一阶段时" not in prompt


def test_artifact_contract_prompt_requires_full_artifact_after_short_confirmations():
    prompt = build_artifact_contract_prompt(
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert "即使用户只回复“继续”“没问题”“确认”" in prompt
    assert "也必须保留所有必填标题" in prompt


def test_artifact_contract_prompt_requires_left_right_chat_bridge():
    prompt = build_artifact_contract_prompt(
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert "左侧对话" in prompt
    assert "自然顾问式对话" in prompt
    assert "短段落" in prompt
    assert "适度使用 bullet" in prompt
    assert "少量重点加粗" in prompt
    assert "固定栏目" in prompt
    assert "本轮总结" not in prompt
    assert "右侧产出物" in prompt


def test_artifact_contract_prompt_keeps_stage_transition_artifact_current():
    prompt = build_artifact_contract_prompt(
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert "不要在同一轮生成下一阶段产出物" in prompt
    assert "继续返回当前阶段的完整产出物" in prompt


def test_agent_turn_output_rejects_unknown_top_level_fields():
    with pytest.raises(ValueError, match="unexpected_top_level"):
        AgentTurnOutput.model_validate(
            {
                "chat": "已更新右侧需求分析文档，请确认。",
                "artifact_update": {
                    "type": "replace",
                    "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
                },
                "stage_action": None,
                "warnings": [],
                "unexpected_top_level": "must not be silently dropped",
            }
        )


def test_agent_turn_output_rejects_unknown_artifact_update_fields():
    with pytest.raises(ValueError, match="unexpected_nested"):
        AgentTurnOutput.model_validate(
            {
                "chat": "已更新右侧需求分析文档，请确认。",
                "artifact_update": {
                    "type": "replace",
                    "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
                    "unexpected_nested": "must not be silently dropped",
                },
                "stage_action": None,
                "warnings": [],
            }
        )


def test_agent_turn_output_rejects_unknown_stage_action_fields():
    with pytest.raises(ValueError, match="unexpected_stage_field"):
        AgentTurnOutput.model_validate(
            {
                "chat": "准备进入下一阶段。",
                "artifact_update": {"type": "none"},
                "stage_action": {
                    "type": "request_next_stage",
                    "target_stage_id": "STRATEGY",
                    "unexpected_stage_field": "must not be silently dropped",
                },
                "warnings": [],
            }
        )


def test_agent_turn_output_rejects_non_json_string_artifact_update():
    with pytest.raises(ValueError, match="artifact_update must be an object"):
        AgentTurnOutput.model_validate(
            {
                "chat": "已更新。",
                "artifact_update": "not-json",
                "stage_action": None,
                "warnings": [],
            }
        )


def test_agent_turn_output_rejects_empty_artifact_markdown():
    with pytest.raises(ValueError, match="artifact markdown cannot be empty"):
        AgentTurnOutput.model_validate(
            {
                "chat": "已更新。",
                "artifact_update": {"type": "replace", "markdown": "   "},
                "stage_action": None,
                "warnings": [],
            }
        )


def test_agent_turn_output_rejects_blank_chat():
    with pytest.raises(ValueError, match="chat cannot be blank"):
        AgentTurnOutput.model_validate(
            {
                "chat": "   ",
                "artifact_update": {
                    "type": "replace",
                    "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
                },
                "stage_action": None,
                "warnings": [],
            }
        )


def test_agent_turn_output_rejects_artifact_markdown_in_chat_when_updating():
    with pytest.raises(ValueError, match="chat must not contain artifact"):
        AgentTurnOutput.model_validate(
            {
                "chat": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
                "artifact_update": {
                    "type": "replace",
                    "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
                },
                "stage_action": None,
                "warnings": [],
            }
        )


@pytest.mark.parametrize(
    "chat",
    [
        "<CHART>我已经在右侧生成了《需求分析文档》框架。</CHART>",
        "说明\n<chart>旧标签协议不应进入聊天。</chart>",
        "<ARTIFACT>产出物正文</ARTIFACT>",
        "<CHAT>旧聊天标签正文</CHAT>",
    ],
)
def test_agent_turn_output_rejects_legacy_protocol_tags_in_chat(chat):
    with pytest.raises(ValueError, match="legacy protocol tags"):
        AgentTurnOutput.model_validate(
            {
                "chat": chat,
                "artifact_update": {"type": "none"},
                "stage_action": None,
                "warnings": [],
            }
        )


def test_agent_turn_output_allows_short_chat_when_updating_artifact():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧需求分析文档，并列出需要确认的关键问题。",
            "artifact_update": {
                "type": "replace",
                "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    assert output.chat == "已更新右侧需求分析文档，并列出需要确认的关键问题。"


def test_agent_turn_output_allows_ordinary_graph_wording_in_chat():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧文档，dependency graph 已补充到产出物中。",
            "artifact_update": {
                "type": "replace",
                "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    assert output.chat == "已更新右侧文档，dependency graph 已补充到产出物中。"


@pytest.mark.parametrize(
    "chat",
    [
        "graph TD\nA-->B",
        "flowchart LR\nA-->B",
        "sequenceDiagram\nA->>B: hello",
    ],
)
def test_agent_turn_output_rejects_mermaid_fragments_in_chat(chat):
    with pytest.raises(ValueError, match="chat must not contain artifact"):
        AgentTurnOutput.model_validate(
            {
                "chat": chat,
                "artifact_update": {
                    "type": "replace",
                    "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
                },
                "stage_action": None,
                "warnings": [],
            }
        )


def test_validate_agent_turn_rejects_invalid_next_stage_target():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "准备进入下一阶段。",
            "artifact_update": {"type": "none"},
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "UNKNOWN",
            },
            "warnings": [],
        }
    )

    with pytest.raises(ContractValidationError, match="invalid target stage"):
        validate_agent_turn(
            output,
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )


def test_agent_turn_output_rejects_blank_stage_action_target():
    with pytest.raises(ValueError, match="target_stage_id cannot be blank"):
        AgentTurnOutput.model_validate(
            {
                "chat": "准备进入下一阶段。",
                "artifact_update": {"type": "none"},
                "stage_action": {
                    "type": "request_next_stage",
                    "target_stage_id": "   ",
                },
                "warnings": [],
            }
        )


def test_validate_agent_turn_rejects_clarify_artifact_missing_headings():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新需求分析文档。",
            "artifact_update": {
                "type": "replace",
                "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )


def test_validate_agent_turn_rejects_headings_only_inside_code_block():
    markdown = (
        "这里描述了将要生成的模板，但没有真正生成 Markdown 标题。\n\n"
        "```markdown\n"
        "# 需求分析文档\n"
        "## 1. 被测系统与边界\n"
        "## 2. 系统交互与核心链路\n"
        "## 3. 待澄清与阻断性问题\n"
        "## 4. 隐式需求与非功能性考量\n"
        "```\n"
    )
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新需求分析文档。",
            "artifact_update": {
                "type": "replace",
                "markdown": markdown,
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )


def test_validate_agent_turn_rejects_required_artifact_stage_without_update():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "需求太模糊了，请先回答几个问题。",
            "artifact_update": {"type": "none"},
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="artifact update is required",
    ):
        validate_agent_turn(
            output,
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )


def test_required_artifact_headings_cover_every_known_workflow_stage():
    required_stage_keys = set(REQUIRED_ARTIFACT_HEADINGS)
    workflow_stage_keys = {
        (workflow_id, stage_id)
        for workflow_id, stage_ids in WORKFLOW_STAGES.items()
        for stage_id in stage_ids
    }

    assert required_stage_keys == workflow_stage_keys


def test_required_mermaid_contract_covers_every_known_workflow():
    workflows_with_required_visuals = {
        workflow_id
        for workflow_id, _stage_id in REQUIRED_ARTIFACT_MERMAID_DIAGRAMS
    }

    assert workflows_with_required_visuals == set(WORKFLOW_STAGES)


def test_first_stage_visual_contract_covers_every_known_workflow():
    visual_stage_keys = (
        set(REQUIRED_ARTIFACT_MERMAID_DIAGRAMS)
        | set(REQUIRED_ARTIFACT_STRUCTURED_VISUALS)
    )
    first_stage_keys = {
        (workflow_id, stage_ids[0])
        for workflow_id, stage_ids in WORKFLOW_STAGES.items()
    }

    assert first_stage_keys <= visual_stage_keys


def test_later_stage_structured_visual_contracts_cover_professional_views():
    expected_visual_contracts = {
        ("TEST_DESIGN", "STRATEGY"): ["risk-board"],
        ("INCIDENT_REVIEW", "IMPROVEMENT"): ["action-board"],
        ("VALUE_DISCOVERY", "JOURNEY"): ["journey-map"],
        ("TEST_DESIGN", "DELIVERY"): ["coverage-map"],
        ("REQ_REVIEW", "REPORT"): ["priority-board"],
        ("INCIDENT_REVIEW", "ROOT_CAUSE"): ["cause-map"],
        ("IDEA_BRAINSTORM", "CONCEPT"): ["mvp-map"],
        ("VALUE_DISCOVERY", "BLUEPRINT"): ["roadmap"],
    }

    for stage_key, visual_types in expected_visual_contracts.items():
        assert REQUIRED_ARTIFACT_STRUCTURED_VISUALS.get(stage_key) == visual_types


@pytest.mark.parametrize(
    ("workflow_id", "stage_id"),
    sorted(REQUIRED_ARTIFACT_HEADINGS),
)
def test_validate_agent_turn_accepts_complete_required_artifact_template(
    workflow_id,
    stage_id,
):
    markdown = _complete_markdown_for_stage(workflow_id, stage_id)
    if (workflow_id, stage_id) == ("VALUE_DISCOVERY", "BLUEPRINT"):
        markdown = f"# 产品需求蓝图\n合法的动态产品名 H1。\n\n{markdown}"

    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧当前阶段产出物，请查看。",
            "artifact_update": {
                "type": "replace",
                "markdown": markdown,
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    assert validate_agent_turn(
        output,
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    ) is output


def test_validate_agent_turn_accepts_required_headings_wrapped_in_mark_tags():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧问题域分析，请查看并确认。",
            "artifact_update": {
                "type": "replace",
                "markdown": (
                    _complete_marked_heading_markdown(
                        REQUIRED_ARTIFACT_HEADINGS[("IDEA_BRAINSTORM", "DEFINE")]
                    )
                    + "\n\n"
                    + _minimal_mermaid_block("mindmap")
                ),
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    assert validate_agent_turn(
        output,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DEFINE",
    ) is output


def test_build_artifact_contract_prompt_includes_required_update_and_headings():
    prompt = build_artifact_contract_prompt(
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert "artifact_update.type 必须为 replace" in prompt
    assert "# 需求分析文档" in prompt
    assert "## 1. 需求事实清单" in prompt
    assert "## 3. 业务规则与数据状态" in prompt
    assert "## 8. 阶段门禁" in prompt


def test_test_design_contracts_include_professional_artifact_fields():
    clarify_fields = REQUIRED_ARTIFACT_HEADINGS[("TEST_DESIGN", "CLARIFY")]
    strategy_fields = REQUIRED_ARTIFACT_HEADINGS[("TEST_DESIGN", "STRATEGY")]
    cases_fields = REQUIRED_ARTIFACT_HEADINGS[("TEST_DESIGN", "CASES")]
    delivery_fields = REQUIRED_ARTIFACT_HEADINGS[("TEST_DESIGN", "DELIVERY")]

    for field in [
        "事实 ID",
        "证据等级",
        "阻断性",
        "责任方",
        "状态",
    ]:
        assert field in clarify_fields
    for field in [
        "## 7. 资源与取舍",
        "## 8. 阶段门禁",
        "风险 ID",
        "测试点 ID",
        "覆盖建议",
    ]:
        assert field in strategy_fields
    for field in [
        "## 2. 用例设计依据",
        "## 4. 测试数据与环境",
        "## 5. 自动化候选",
        "## 7. 开放问题",
        "## 8. 阶段门禁",
        "断言",
        "执行层级",
        "自动化建议",
        "状态",
    ]:
        assert field in cases_fields
    for field in [
        "## 2. 执行摘要",
        "## 6. 覆盖地图",
        "## 7. 开放风险",
        "## 9. 签署确认",
        "## 10. 变更记录",
    ]:
        assert field in delivery_fields


def test_build_artifact_contract_prompt_includes_h1_keyword_requirements():
    prompt = build_artifact_contract_prompt(
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    )

    assert "H1 标题" in prompt
    assert "需求蓝图" in prompt


def test_build_artifact_contract_prompt_includes_required_mermaid_contract():
    prompt = build_artifact_contract_prompt(
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert "Mermaid" in prompt
    assert "quadrantChart" in prompt
    assert "block-beta" in prompt


def test_build_artifact_contract_prompt_includes_required_structured_visual_contract():
    prompt = build_artifact_contract_prompt(
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert "ai4se-visual" in prompt
    assert "traceability-matrix" in prompt
    assert '"columns"' in prompt
    assert '"rows"' in prompt
    assert "fenced:ai4se-visual" in prompt
    assert "data.requirements" in prompt
    assert "复杂 HTML" in prompt


def test_validate_agent_turn_rejects_missing_required_mermaid_contract():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新测试策略蓝图。",
            "artifact_update": {
                "type": "replace",
                "markdown": _complete_markdown(
                    REQUIRED_ARTIFACT_HEADINGS[("TEST_DESIGN", "STRATEGY")]
                ),
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact visualizations",
    ):
        validate_agent_turn(
            output,
            workflow_id="TEST_DESIGN",
            current_stage_id="STRATEGY",
        )


def test_validate_agent_turn_rejects_missing_required_structured_visual_contract():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新测试用例集。",
            "artifact_update": {
                "type": "replace",
                "markdown": _complete_markdown(
                    REQUIRED_ARTIFACT_HEADINGS[("TEST_DESIGN", "CASES")]
                ),
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact visualizations",
    ):
        validate_agent_turn(
            output,
            workflow_id="TEST_DESIGN",
            current_stage_id="CASES",
        )


def test_validate_agent_turn_rejects_legacy_traceability_matrix_shape():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新测试用例集。",
            "artifact_update": {
                "type": "replace",
                "markdown": (
                    _complete_markdown(
                        REQUIRED_ARTIFACT_HEADINGS[("TEST_DESIGN", "CASES")]
                    )
                    + "\n\n```ai4se-visual\n"
                    + "{\n"
                    + '  "type": "traceability-matrix",\n'
                    + '  "data": {\n'
                    + '    "requirements": ["用户名校验"],\n'
                    + '    "testCases": ["TC-001"],\n'
                    + '    "matrix": [[1]]\n'
                    + "  }\n"
                    + "}\n"
                    + "```\n"
                ),
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="traceability-matrix 必须使用 columns 和 rows",
    ):
        validate_agent_turn(
            output,
            workflow_id="TEST_DESIGN",
            current_stage_id="CASES",
        )


def test_build_artifact_contract_prompt_is_empty_without_required_headings():
    assert build_artifact_contract_prompt(
        workflow_id="UNKNOWN",
        current_stage_id="UNKNOWN",
    ) == ""


@pytest.mark.parametrize(
    ("stage_id", "markdown"),
    [
        (
            "STRATEGY",
            "# 测试策略蓝图\n\n## 1. 质量目标\n内容",
        ),
        (
            "CASES",
            "# 测试用例集\n\n## 1. 用例统计\n内容",
        ),
        (
            "DELIVERY",
            "# 测试设计文档\n\n## 文档信息\n内容",
        ),
    ],
)
def test_validate_agent_turn_rejects_test_design_artifact_missing_headings(
    stage_id,
    markdown,
):
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新当前阶段产出物。",
            "artifact_update": {
                "type": "replace",
                "markdown": markdown,
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="TEST_DESIGN",
            current_stage_id=stage_id,
        )


def test_validate_agent_turn_rejects_test_design_cases_missing_executable_fields():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新测试用例集。",
            "artifact_update": {
                "type": "replace",
                "markdown": (
                    "# 测试用例集\n\n"
                    "## 1. 用例统计\n"
                    "共 2 条用例。\n\n"
                    "## 2. 用例清单\n\n"
                    "| ID | 用例标题 | 优先级 | 关联风险 | 前置条件 | 操作步骤 | 预期结果 |\n"
                    "|---|---|---|---|---|---|---|\n"
                    "| TC-001 | 登录成功 | P0 | R-001 | 用户存在 | 输入账号密码并提交 | 登录成功 |\n\n"
                    "## 3. 测试点覆盖追溯\n\n"
                    "| 测试点 | 优先级 | 关联风险 | 覆盖用例 | 覆盖状态 |\n"
                    "|---|---|---|---|---|\n"
                    "| 登录链路 | P0 | R-001 | TC-001 | 已覆盖 |\n"
                ),
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="TEST_DESIGN",
            current_stage_id="CASES",
        )


@pytest.mark.parametrize(
    ("stage_id", "markdown"),
    [
        (
            "REVIEW",
            "# 需求评审问题清单\n\n## 评审概要\n内容",
        ),
        (
            "REPORT",
            "# 需求评审报告\n\n## 评审结论\n内容",
        ),
    ],
)
def test_validate_agent_turn_rejects_req_review_artifact_missing_headings(
    stage_id,
    markdown,
):
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新需求评审产出物。",
            "artifact_update": {
                "type": "replace",
                "markdown": markdown,
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="REQ_REVIEW",
            current_stage_id=stage_id,
        )


def test_validate_agent_turn_rejects_req_review_review_missing_actionable_issue_fields():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新需求评审问题清单。",
            "artifact_update": {
                "type": "replace",
                "markdown": (
                    "# 需求评审问题清单\n\n"
                    "## 评审概要\n内容\n\n"
                    "## 问题统计\n内容\n\n"
                    "## 1. 可测试性问题\n\n"
                    "| ID | 问题描述 | 优先级 | 所属需求章节 | 建议 |\n"
                    "|----|---------|--------|------------|------|\n"
                    "| Q-001 | 验收标准不明确 | P0 | 登录需求 | 补充断言 |\n"
                ),
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="REQ_REVIEW",
            current_stage_id="REVIEW",
        )


@pytest.mark.parametrize(
    ("stage_id", "markdown"),
    [
        (
            "TIMELINE",
            "# 故障复盘报告\n\n## 1. 事件概要\n内容",
        ),
        (
            "ROOT_CAUSE",
            "# 故障复盘报告\n\n## 6. 根因分析\n内容",
        ),
        (
            "IMPROVEMENT",
            "# 故障复盘报告\n\n## 报告信息\n内容",
        ),
    ],
)
def test_validate_agent_turn_rejects_incident_review_artifact_missing_headings(
    stage_id,
    markdown,
):
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新故障复盘产出物。",
            "artifact_update": {
                "type": "replace",
                "markdown": markdown,
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="INCIDENT_REVIEW",
            current_stage_id=stage_id,
        )


def test_validate_agent_turn_rejects_incident_review_improvement_missing_action_fields():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新故障复盘报告。",
            "artifact_update": {
                "type": "replace",
                "markdown": (
                    "# 故障复盘报告\n\n"
                    "## 报告信息\n内容\n\n"
                    "## 第一部分：事件还原\n内容\n\n"
                    "## 第二部分：根因分析\n内容\n\n"
                    "## 第三部分：改进措施\n\n"
                    "### 7. 改进措施\n\n"
                    "#### 7.1 改进优先级分布\n内容\n\n"
                    "#### 7.2 改进行动清单\n\n"
                    "| ID | 改进措施 | 类型 | 对应根因 | 建议负责人 | 完成期限 | 验收标准 | 优先级 |\n"
                    "|----|---------|------|---------|-----------|---------|---------|------|\n"
                    "| A-001 | 增加发布前检查 | 流程 | Why-3 | 测试负责人 | 2026-07-01 | 检查项上线 | 紧急 |\n\n"
                    "### 8. 防复发检查清单\n内容\n\n"
                    "### 9. 经验教训\n内容\n\n"
                    "## 签署确认\n内容\n"
                ),
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="INCIDENT_REVIEW",
            current_stage_id="IMPROVEMENT",
        )


@pytest.mark.parametrize(
    ("stage_id", "markdown"),
    [
        (
            "DEFINE",
            "# 问题域分析\n\n## 问题假设陈述\n内容",
        ),
        (
            "DIVERGE",
            "# 创意发散\n\n## 发散全景图\n内容",
        ),
        (
            "CONVERGE",
            "# 收敛聚焦\n\n## 决策矩阵\n内容",
        ),
        (
            "CONCEPT",
            "# 产品概念简报\n\n## 定位声明\n内容",
        ),
    ],
)
def test_validate_agent_turn_rejects_idea_brainstorm_artifact_missing_headings(
    stage_id,
    markdown,
):
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新创意工作流产出物。",
            "artifact_update": {
                "type": "replace",
                "markdown": markdown,
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="IDEA_BRAINSTORM",
            current_stage_id=stage_id,
        )


def test_validate_agent_turn_rejects_idea_brainstorm_converge_missing_decision_fields():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新收敛聚焦产出物。",
            "artifact_update": {
                "type": "replace",
                "markdown": (
                    "# 收敛聚焦\n\n"
                    "## 决策矩阵\n内容\n\n"
                    "## ICE 评估表\n\n"
                    "| 编号 | 创意名称 | 影响力 (1-5) | 信心 (1-5) | 实现难度 (1-5) | ICE得分 | 排名 | 结论 |\n"
                    "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                    "| C-01 | 智能推荐 | 4 | 3 | 4 | 48 | 1 | 入选 |\n\n"
                    "## 整合演进路径（如果触发合并）\n内容\n"
                ),
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="IDEA_BRAINSTORM",
            current_stage_id="CONVERGE",
        )


@pytest.mark.parametrize(
    ("stage_id", "markdown"),
    [
        (
            "ELEVATOR",
            "# 价值定位分析\n\n## 产品核心定位\n内容",
        ),
        (
            "PERSONA",
            "# 用户画像分析\n\n## 主要用户画像\n内容",
        ),
        (
            "JOURNEY",
            "# 用户旅程分析\n\n## 用户旅程地图\n内容",
        ),
        (
            "BLUEPRINT",
            "# 产品需求蓝图\n\n## 文档信息\n内容",
        ),
    ],
)
def test_validate_agent_turn_rejects_value_discovery_artifact_missing_headings(
    stage_id,
    markdown,
):
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新价值发现产出物。",
            "artifact_update": {
                "type": "replace",
                "markdown": markdown,
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="VALUE_DISCOVERY",
            current_stage_id=stage_id,
        )


def test_validate_agent_turn_rejects_value_discovery_journey_missing_stage_fields():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新用户旅程分析。",
            "artifact_update": {
                "type": "replace",
                "markdown": (
                    "# 用户旅程分析\n\n"
                    "## 用户旅程地图\n"
                    "journey\n\n"
                    "## 关键阶段详细分析\n\n"
                    "### 阶段 1：问题认知\n"
                    "| 维度 | 描述 |\n"
                    "| --- | --- |\n"
                    "| 用户目标 | 发现问题 |\n"
                    "| 用户行为 | 搜索资料 |\n"
                    "| 触点渠道 | 搜索引擎 |\n"
                    "| 主要痛点 | 信息分散 |\n"
                    "| 产品机会 | 聚合推荐 |\n\n"
                    "## 痛点优先级排序\n\n"
                    "### 高优先级痛点（必须解决）\n"
                    "内容\n\n"
                    "### 中等优先级痛点（应该解决）\n"
                    "内容\n\n"
                    "### 低优先级痛点（可以解决）\n"
                    "内容\n\n"
                    "## 核心机会点\n\n"
                    "### 主要机会点\n"
                    "内容\n\n"
                    "### 产品切入策略\n"
                    "内容\n"
                ),
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="VALUE_DISCOVERY",
            current_stage_id="JOURNEY",
        )


def test_validate_agent_turn_rejects_blueprint_without_h1_heading():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新需求蓝图。",
            "artifact_update": {
                "type": "replace",
                "markdown": "\n\n".join(
                    [
                        "这是一份需求蓝图正文说明，但不是 Markdown H1 标题。",
                        "## 文档信息\n内容",
                        "## 1. 产品概述\n内容",
                        "### 1.1 产品愿景\n内容",
                        "### 1.2 定位声明\n内容",
                        "### 1.3 核心价值\n内容",
                        "## 2. 目标用户（摘要）\n内容",
                        "## 3. 核心需求\n内容",
                        "### 功能架构\n内容",
                        "### P0 需求（核心功能，必须实现）\n内容",
                        "### P1 需求（重要功能，应该实现）\n内容",
                        "### P2 需求（增值功能，可以实现）\n内容",
                        "## 4. 核心流程\n内容",
                        "### 主流程图\n内容",
                        "## 5. 成功指标\n内容",
                        "## 6. MVP 范围与计划\n内容",
                        "### MVP 包含功能\n内容",
                        "### 迭代路线\n内容",
                        "## 7. 风险评估\n内容",
                    ]
                ),
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="missing required artifact headings",
    ):
        validate_agent_turn(
            output,
            workflow_id="VALUE_DISCOVERY",
            current_stage_id="BLUEPRINT",
        )


def test_validate_agent_turn_rejects_next_stage_from_last_stage():
    output = AgentTurnOutput.model_validate(
        {
            "chat": "准备进入下一阶段。",
            "artifact_update": {"type": "none"},
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "STRATEGY",
            },
            "warnings": [],
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="last stage cannot request next stage",
    ):
        validate_agent_turn(
            output,
            workflow_id="REQ_REVIEW",
            current_stage_id="REPORT",
        )
