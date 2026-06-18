import pytest

from agent_contracts import (
    AgentTurnOutput,
    ArtifactUpdate,
    ContractValidationError,
    REQUIRED_ARTIFACT_HEADINGS,
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


@pytest.mark.parametrize(
    ("workflow_id", "stage_id"),
    sorted(REQUIRED_ARTIFACT_HEADINGS),
)
def test_validate_agent_turn_accepts_complete_required_artifact_template(
    workflow_id,
    stage_id,
):
    markdown = _complete_markdown(
        REQUIRED_ARTIFACT_HEADINGS[(workflow_id, stage_id)]
    )
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


def test_build_artifact_contract_prompt_includes_required_update_and_headings():
    prompt = build_artifact_contract_prompt(
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert "artifact_update.type 必须为 replace" in prompt
    assert "# 需求分析文档" in prompt
    assert "## 1. 被测系统与边界" in prompt
    assert "## 4. 隐式需求与非功能性考量" in prompt


def test_build_artifact_contract_prompt_includes_h1_keyword_requirements():
    prompt = build_artifact_contract_prompt(
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    )

    assert "H1 标题" in prompt
    assert "需求蓝图" in prompt


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
