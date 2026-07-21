import ast
import copy
import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

import agent_runtime

from agent_contracts import (
    WORKFLOW_STAGES,
    AgentTurnOutput,
    ContractValidationError,
    validate_agent_turn,
)
from artifact_data_renderers import (
    ClarifyArtifactData,
    DeliveryArtifactData,
    IncidentImprovementArtifactData,
    IdeaConceptArtifactData,
    IdeaConvergeArtifactData,
    IdeaDefineArtifactData,
    render_agent_turn_from_artifact_data,
)
from artifact_data_value_schema import (
    ValueDiscoveryJourneyArtifactData,
    ValueDiscoveryPersonaArtifactData,
)
from agent_runtime import (
    AgentRuntimeModelError,
    RawJsonStreamTerminationError,
    AgentRuntimeSchemaError,
    AgentTurnValidationDeps,
    PydanticAgentRuntime,
    RawStreamingConfig,
    TEXT_STRUCTURED_OUTPUT_INSTRUCTION,
    build_artifact_data_progress_markdown,
    build_partial_agent_delta,
    build_agent_retries,
    build_model_settings,
    build_raw_json_retry_prompt,
    build_structured_output_instruction,
    extract_json_string_prefix,
    parse_agent_turn_output_text,
    register_contract_output_validator,
    resolve_structured_output_capability,
    supports_artifact_data_rendering,
)
from sse_schemas import AgentRetrySignal, AgentTurnDeltaOutput
from test_artifact_data_renderers import (
    ARTIFACT_DATA_STAGE_FIXTURES,
    VALID_IDEA_CONCEPT_ARTIFACT_DATA,
    VALID_IDEA_CONVERGE_ARTIFACT_DATA,
    VALID_IDEA_DEFINE_ARTIFACT_DATA,
    VALID_IDEA_DIVERGE_ARTIFACT_DATA,
    VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA,
    VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA,
    VALID_INCIDENT_TIMELINE_ARTIFACT_DATA,
    VALID_PRD_REVIEW_ARTIFACT_DATA,
    VALID_CASES_ARTIFACT_DATA,
    VALID_DELIVERY_ARTIFACT_DATA,
    VALID_REQ_REVIEW_ARTIFACT_DATA,
    VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
    VALID_STORY_BREAKDOWN_ARTIFACT_DATA,
    VALID_STRATEGY_ARTIFACT_DATA,
    VALID_VALUE_BLUEPRINT_ARTIFACT_DATA,
    VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
    VALID_VALUE_JOURNEY_ARTIFACT_DATA,
    VALID_VALUE_PERSONA_ARTIFACT_DATA,
)
from workflow_manifest import format_artifact_data_contract_instruction
from run_persistence import SAFE_SCHEMA_VALIDATORS
from safe_error_diagnostics import (
    SAFE_RESPONSE_SCHEMA_VALIDATORS,
    SAFE_SCHEMA_FIELD_PATHS,
    SAFE_STREAM_TERMINATION_VALIDATORS,
)

RUNTIME_MODULE = Path(__file__).resolve().parents[1] / "agent_runtime.py"
INSTRUCTION_REGISTRY_MODULE = (
    Path(__file__).resolve().parents[1] / "artifact_data_instruction_registry.py"
)


def test_runtime_safe_validator_registries_are_persistence_whitelisted():
    assert set(agent_runtime._SAFE_RETRY_VALIDATORS) <= SAFE_SCHEMA_VALIDATORS
    assert set(agent_runtime._SAFE_RETRY_CORRECTIONS) <= SAFE_SCHEMA_VALIDATORS
    assert set(SAFE_SCHEMA_FIELD_PATHS) <= SAFE_SCHEMA_VALIDATORS
    assert SAFE_RESPONSE_SCHEMA_VALIDATORS <= SAFE_SCHEMA_VALIDATORS
    assert RawJsonStreamTerminationError.SAFE_REASONS == frozenset(
        SAFE_STREAM_TERMINATION_VALIDATORS
    )


def _top_level_assignment_call_module(path: Path, name: str) -> str | None:
    module = ast.parse(path.read_text(encoding="utf-8"))
    for node in module.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if any(alias.name == name for alias in node.names):
            return node.module
    return None


def test_runtime_imports_structured_instruction_registry_from_dedicated_module():
    assert INSTRUCTION_REGISTRY_MODULE.is_file()
    assert (
        _top_level_assignment_call_module(
            RUNTIME_MODULE,
            "ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS",
        )
        == "artifact_data_instruction_registry"
    )


ARTIFACT_DATA_STREAMING_STAGES = sorted(ARTIFACT_DATA_STAGE_FIXTURES)


@pytest.mark.parametrize(("workflow_id", "stage_id"), ARTIFACT_DATA_STREAMING_STAGES)
def test_artifact_data_structured_output_instruction_puts_natural_chat_before_artifact_data(
    workflow_id: str,
    stage_id: str,
):
    instruction = build_structured_output_instruction(workflow_id, stage_id)

    assert '1. "chat"' in instruction
    assert '2. "artifact_data"' in instruction
    assert instruction.index('1. "chat"') < instruction.index('2. "artifact_data"')
    assert instruction.index('{\n  "chat"') < instruction.index('\n  "artifact_data"')


def test_artifact_data_structured_output_instruction_injects_visual_protocol():
    instruction = build_structured_output_instruction("VALUE_DISCOVERY", "JOURNEY")

    assert "【视觉产物协议】" in instruction
    assert "模型只输出 artifact_data 结构化业务数据" in instruction
    assert "Mermaid、D2、Graphviz DOT、PlantUML 代码块" in instruction
    assert "完整 Markdown 文档、Markdown 表格、ai4se-visual JSON 代码块" in instruction
    assert "Mermaid 只允许由后端确定性渲染器生成" in instruction
    assert "复杂业务图优先使用 ai4se-visual JSON" in instruction
    assert "timeline-map" in instruction
    assert (
        "后续复杂视觉类型包括 mindmap、sequence-flow、distribution-chart" in instruction
    )


def test_clarify_structured_output_uses_one_valid_question_status_example():
    instruction = build_structured_output_instruction("TEST_DESIGN", "CLARIFY")

    assert '"status": "待确认"' in instruction
    assert '"status": "已假设"' not in instruction
    assert '"status": "待确认/已确认/已假设/AI 假设"' not in instruction
    assert (
        "clarification_questions[].status 必须精确取值为待确认、已确认、"
        "已假设或 AI 假设之一；禁止组合值、同义词、括号说明或其它文本"
    ) in instruction


def _raw_json_chunks_after_artifact_data_members(
    final_json: str,
    member_names: list[str],
) -> list[str]:
    decoder = json.JSONDecoder()
    artifact_key_index = final_json.index('"artifact_data"')
    index = final_json.index("{", artifact_key_index) + 1
    prefixes: dict[str, str] = {}
    while index < len(final_json):
        while index < len(final_json) and final_json[index].isspace():
            index += 1
        if index < len(final_json) and final_json[index] == "}":
            break
        key, key_end = decoder.raw_decode(final_json[index:])
        assert isinstance(key, str)
        index += key_end
        while index < len(final_json) and final_json[index].isspace():
            index += 1
        assert final_json[index] == ":"
        index += 1
        while index < len(final_json) and final_json[index].isspace():
            index += 1
        _, value_end = decoder.raw_decode(final_json[index:])
        index += value_end
        if key in member_names:
            prefixes[key] = final_json[:index]
        while index < len(final_json) and final_json[index].isspace():
            index += 1
        if index < len(final_json) and final_json[index] == ",":
            index += 1

    missing = [name for name in member_names if name not in prefixes]
    assert not missing, f"artifact_data members not found: {missing}"

    ordered_prefixes = [prefixes[name] for name in member_names]
    chunks = [ordered_prefixes[0]]
    chunks.extend(
        ordered_prefixes[index][len(ordered_prefixes[index - 1]) :]
        for index in range(1, len(ordered_prefixes))
    )
    chunks.append(final_json[len(ordered_prefixes[-1]) :])
    return chunks


VALID_CLARIFY_ARTIFACT = """# 需求分析文档

## 1. 需求事实清单
| 事实 ID | 需求事实 | 来源 | 证据等级 | 状态 |
|---|---|---|---|---|
| F-001 | 用户需要登录功能 | 用户描述 | 用户陈述 | 已确认 |

## 2. 被测系统与边界
| 类型 | 具体内容 | 测试含义 | 状态 |
|---|---|---|---|
| 测试范围 | 登录页面和登录 API | 验证登录主链路 | 已确认 |

## 3. 业务规则与数据状态
| 规则 ID | 业务规则 | 触发条件 | 边界值/状态流转 | 异常处理 | 验收口径 | 状态 |
|---|---|---|---|---|---|---|
| BR-001 | 正确账号密码允许登录 | 用户提交凭证 | 未登录到已登录 | 返回错误提示 | 登录成功进入工作台 | 已确认 |

## 4. 核心链路与异常链路
```mermaid
flowchart TD
    User["用户"] --> Entry["登录页"]
    Entry --> Core["认证服务"]
    Core --> Data["用户库"]
    Core --> External["风控服务"]
    Core --> Result["工作台"]
    Core --> Failure["错误提示"]
```

## 5. 待澄清问题
| 问题 ID | 问题描述 | 优先级 | 阻断性 | 影响范围 | 当前假设 | 责任方 | 状态 |
|---|---|---|---|---|---|---|---|
| Q-001 | 锁定策略是否存在 | P1 | 非阻断 | 异常登录 | 暂按 5 次失败锁定 | 产品 | 待确认 |

## 6. 隐式质量需求
| 质量维度 | 需求或假设 | 可验证指标 | 风险 | 状态 |
|---|---|---|---|---|
| 安全 | 防止越权登录 | 未授权请求失败 | 账号风险 | AI 假设 |

## 7. 后续测试设计输入
| 输入类型 | ID | 内容 | 来源 | 后续用途 |
|---|---|---|---|---|
| 风险种子 | R-SEED-001 | 凭证校验失败处理 | BR-001 | 策略阶段 FMEA |

## 8. 阶段门禁
- [x] 测试范围和不测范围已明确。

## 文档信息
| 字段 | 内容 |
|---|---|
| Artifact 名称 | 测试需求分析与澄清基线 |"""

VALID_CLARIFY_ARTIFACT_JSON = json.dumps(
    VALID_CLARIFY_ARTIFACT,
    ensure_ascii=False,
)[1:-1]

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
        {"from_node": "用户", "to_node": "登录页", "label": "打开登录入口"},
        {"from_node": "登录页", "to_node": "认证服务", "label": "提交账号密码"},
        {"from_node": "认证服务", "to_node": "工作台", "label": "认证成功"},
        {"from_node": "认证服务", "to_node": "错误提示", "label": "认证失败"},
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

DEEPSEEK_FORMAT_STAGE_FIXTURES = copy.deepcopy(ARTIFACT_DATA_STAGE_FIXTURES)

DEEPSEEK_FORMAT_STAGE_CASES = [
    (workflow_id, stage_id, artifact_data)
    for (workflow_id, stage_id), artifact_data in sorted(
        DEEPSEEK_FORMAT_STAGE_FIXTURES.items()
    )
]


def test_deepseek_format_readiness_covers_every_online_stage():
    online_stages = {
        (workflow_id, stage_id)
        for workflow_id, stages in WORKFLOW_STAGES.items()
        for stage_id in stages
    }

    assert set(DEEPSEEK_FORMAT_STAGE_FIXTURES) == online_stages


@pytest.mark.parametrize(
    ("workflow_id", "stage_id", "artifact_data"),
    DEEPSEEK_FORMAT_STAGE_CASES,
)
def test_deepseek_format_readiness_uses_artifact_data_instructions(
    workflow_id,
    stage_id,
    artifact_data,
):
    instruction = build_structured_output_instruction(workflow_id, stage_id)
    retry_prompt = build_raw_json_retry_prompt(
        "请生成当前阶段产出物",
        ValueError("artifact_data.document_info 缺失"),
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )

    assert artifact_data
    assert supports_artifact_data_rendering(workflow_id, stage_id)
    assert "artifact_data" in instruction
    assert "artifact_update.markdown" not in instruction
    assert "不要输出完整 Markdown" in instruction
    assert "后端会负责确定性渲染" in instruction
    assert "必须修正上述 artifact_data 数据问题" in retry_prompt
    assert "后端会根据 artifact_data 渲染右侧产出物" in retry_prompt
    assert "artifact_update.type 必须为 replace" not in retry_prompt


def test_document_info_identity_is_declared_as_backend_derived_in_all_instructions():
    instructions_with_document_info = {
        stage_key: build_structured_output_instruction(*stage_key)
        for stage_key in ARTIFACT_DATA_STREAMING_STAGES
        for instruction in (build_structured_output_instruction(*stage_key),)
        if '"document_info"' in instruction
    }

    assert instructions_with_document_info
    for stage_key, instruction in instructions_with_document_info.items():
        document_info_line = next(
            line for line in instruction.splitlines() if '"document_info"' in line
        )
        assert '"workflow"' not in document_info_line, stage_key
        assert '"stage"' not in document_info_line, stage_key
        assert "document_info.workflow 和 document_info.stage 由后端注入" in instruction


@pytest.mark.parametrize(
    ("workflow_id", "stage_id", "artifact_data"),
    DEEPSEEK_FORMAT_STAGE_CASES,
)
def test_deepseek_format_readiness_renderers_pass_artifact_contract(
    workflow_id,
    stage_id,
    artifact_data,
):
    output = render_agent_turn_from_artifact_data(
        {
            "chat": "我已按结构化数据生成当前阶段产出物，请查看右侧文档。",
            "artifact_data": artifact_data,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )

    assert output is not None
    assert output.artifact_update.type == "replace"
    validate_agent_turn(output, workflow_id=workflow_id, current_stage_id=stage_id)


class FakeRunResult:
    def __init__(self, output):
        self.output = output


class FakeStreamResult:
    def __init__(self, outputs):
        self.outputs = outputs

    def stream_output(self, *, debounce_by=None):
        yield from self.outputs


class FakeAgent:
    def __init__(self, output):
        self.output = output
        self.prompts = []
        self.deps = []

    def run_sync(self, prompt, *, deps=None):
        self.prompts.append(prompt)
        self.deps.append(deps)
        return FakeRunResult(self.output)


class FakeStreamingAgent(FakeAgent):
    def __init__(self, outputs):
        super().__init__(outputs[-1])
        self.outputs = outputs

    def run_stream_sync(self, prompt, *, deps=None):
        self.prompts.append(prompt)
        self.deps.append(deps)
        return FakeStreamResult(self.outputs)


class FailingAgent:
    def __init__(self, error):
        self.error = error

    def run_sync(self, prompt, *, deps=None):
        raise self.error


def _install_raw_stream_fake(
    monkeypatch,
    stream_fake,
    *,
    default_finish_reason: str | None = "stop",
):
    def stream_with_finish_reason(**kwargs):
        finish_reason_reported = False
        on_finish_reason = kwargs["on_finish_reason"]

        def record_finish_reason(reason: str) -> None:
            nonlocal finish_reason_reported
            finish_reason_reported = True
            on_finish_reason(reason)

        yield from stream_fake(**{**kwargs, "on_finish_reason": record_finish_reason})
        if not finish_reason_reported and default_finish_reason is not None:
            on_finish_reason(default_finish_reason)

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        stream_with_finish_reason,
    )


def test_runtime_validates_pydantic_ai_output_before_returning_it():
    agent = FakeAgent(
        {
            "chat": "已更新右侧需求分析文档。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "STRATEGY",
            },
            "warnings": [],
        }
    )
    runtime = PydanticAgentRuntime(agent)

    output = runtime.run_turn(
        "用户需求: 登录功能",
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert isinstance(output, AgentTurnOutput)
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "STRATEGY"
    assert agent.prompts == ["用户需求: 登录功能"]
    assert agent.deps == [
        AgentTurnValidationDeps(
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    ]


def test_runtime_stream_turn_yields_partial_outputs_and_validates_final_output():
    partial = {"chat": "正在梳理需求。"}
    final = {
        "chat": "已更新右侧需求分析文档。",
        "artifact_update": {
            "type": "replace",
            "markdown": VALID_CLARIFY_ARTIFACT,
        },
        "stage_action": {
            "type": "request_next_stage",
            "target_stage_id": "STRATEGY",
        },
        "warnings": [],
    }
    agent = FakeStreamingAgent([partial, final])
    runtime = PydanticAgentRuntime(agent)

    outputs = list(
        runtime.stream_turn(
            "用户需求: 登录功能",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    assert outputs[0] == AgentTurnDeltaOutput(chat="正在梳理需求。")
    assert isinstance(outputs[1], AgentTurnOutput)
    assert outputs[1].stage_action is not None
    assert outputs[1].stage_action.target_stage_id == "STRATEGY"
    assert agent.prompts == ["用户需求: 登录功能"]
    assert agent.deps == [
        AgentTurnValidationDeps(
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    ]


def test_raw_streaming_instruction_keeps_left_chat_conversational():
    assert "简短中文说明" not in TEXT_STRUCTURED_OUTPUT_INSTRUCTION
    assert "像一次自然的工作对话" in TEXT_STRUCTURED_OUTPUT_INSTRUCTION
    assert "我本轮已经做了什么" in TEXT_STRUCTURED_OUTPUT_INSTRUCTION
    assert "本轮确认或假定的关键点" in TEXT_STRUCTURED_OUTPUT_INSTRUCTION
    assert "接下来需要用户确认或补充什么" in TEXT_STRUCTURED_OUTPUT_INSTRUCTION


def test_extract_json_string_prefix_reads_incomplete_streamed_string():
    text = (
        '{"chat":"正在梳理需求。",'
        '"artifact_update":{"type":"replace","markdown":"# 需求分析文档\\n\\n'
        "## 1. 被测系统与边界\\n内容"
    )

    assert extract_json_string_prefix(text, "chat") == "正在梳理需求。"
    assert (
        extract_json_string_prefix(
            text,
            "markdown",
        )
        == "# 需求分析文档\n\n## 1. 被测系统与边界\n内容"
    )


def test_build_partial_agent_delta_extracts_chat_and_artifact_markdown():
    delta = build_partial_agent_delta(
        '{"chat":"正在生成。","artifact_update":{"type":"replace",'
        '"markdown":"# 需求分析文档\\n\\n## 1. 被测系统与边界\\n内容"}}'
    )

    assert delta == AgentTurnDeltaOutput(
        chat="正在生成。",
        artifact_update={
            "type": "replace",
            "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
        },
    )


def test_build_partial_agent_delta_does_not_emit_progress_artifact_for_incomplete_artifact_data():
    delta = build_partial_agent_delta(
        '{"chat":"正在生成结构化产物。","artifact_data":{"document_info":',
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert delta == AgentTurnDeltaOutput(chat="正在生成结构化产物。")


def test_parse_agent_turn_output_text_accepts_plain_json_or_fenced_json():
    json_text = """{
      "chat": "已更新右侧需求分析文档。",
      "artifact_update": {
        "type": "replace",
        "markdown": "# 需求分析文档\\n\\n## 1. 被测系统与边界\\n内容\\n\\n## 2. 系统交互与核心链路\\n内容\\n\\n## 3. 待澄清与阻断性问题\\n内容\\n\\n## 4. 隐式需求与非功能性考量\\n内容"
      },
      "stage_action": null,
      "warnings": []
    }"""

    assert parse_agent_turn_output_text(json_text).chat == "已更新右侧需求分析文档。"
    assert parse_agent_turn_output_text(
        f"```json\n{json_text}\n```"
    ).artifact_update.markdown.startswith("# 需求分析文档")


def test_parse_agent_turn_output_text_renders_clarify_artifact_data():
    json_text = json.dumps(
        {
            "chat": "我已整理登录需求澄清基线，请确认右侧文档。",
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "STRATEGY",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 需求分析文档")
    assert "flowchart TD" in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "STRATEGY"


def test_parse_agent_turn_output_text_renders_story_breakdown_input_analysis_artifact_data():
    json_text = json.dumps(
        {
            "chat": "我已完成需求输入盘点，请确认右侧 Story 拆解基线。",
            "artifact_data": ARTIFACT_DATA_STAGE_FIXTURES[
                ("STORY_BREAKDOWN", "INPUT_ANALYSIS")
            ],
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "EPIC_MAPPING",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="STORY_BREAKDOWN",
        current_stage_id="INPUT_ANALYSIS",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 用户故事拆解包")
    assert "## 输入分析" in output.artifact_update.markdown
    assert "## Epic Map" in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "EPIC_MAPPING"


def test_parse_agent_turn_output_text_renders_strategy_artifact_data():
    json_text = json.dumps(
        {
            "chat": "我已形成风险驱动测试策略，请确认右侧蓝图。",
            "artifact_data": VALID_STRATEGY_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CASES",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 测试策略蓝图")
    assert "quadrantChart" in output.artifact_update.markdown
    assert "block-beta" in output.artifact_update.markdown
    assert '"type": "risk-board"' in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "CASES"


def test_parse_agent_turn_output_text_renders_strategy_artifact_data_without_model_rpn():
    artifact_data = copy.deepcopy(VALID_STRATEGY_ARTIFACT_DATA)
    artifact_data["risks"][0].pop("rpn")
    json_text = json.dumps(
        {
            "chat": "我已形成风险驱动测试策略，请确认右侧蓝图。",
            "artifact_data": artifact_data,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 测试策略蓝图")
    assert "| 5 | 3 | 4 | 60 |" in output.artifact_update.markdown
    assert '"RPN": 60' in output.artifact_update.markdown


def test_strategy_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "TEST_DESIGN",
        "STRATEGY",
    )

    assert "artifact_data" in instruction
    assert "quality_goals" in instruction
    assert "risks" in instruction
    assert "risk-board" in instruction
    assert "stage_action" in instruction
    assert '"target_stage_id": "CASES"' in instruction
    assert "不要输出完整 Markdown" in instruction
    assert '"rpn": 60' not in instruction
    assert "RPN 由后端根据 severity * occurrence * detection 计算" in instruction
    assert "rpn 必须等于" not in instruction
    assert "artifact_update.markdown" not in instruction


def test_strategy_structured_output_instruction_requests_internal_id_references():
    instruction = build_structured_output_instruction("TEST_DESIGN", "STRATEGY")

    assert (
        "test_points.quality_goal、test_points.risk、test_points.technique"
        in instruction
    )
    assert "只能引用 artifact_data 中已定义的 QG/R/TS ID" in instruction


def test_strategy_structured_output_instruction_uses_manifest_artifact_data_contract():
    instruction = build_structured_output_instruction("TEST_DESIGN", "STRATEGY")

    assert (
        format_artifact_data_contract_instruction("TEST_DESIGN", "STRATEGY")
        in instruction
    )
    assert (
        "risks[].rpn 由后端根据 severity * occurrence * detection 计算" in instruction
    )
    assert "quality_goals[].goal_id 必须唯一" in instruction
    assert (
        "test_points.quality_goal、test_points.risk、test_points.technique"
        in instruction
    )
    assert (
        "test_techniques.target、test_techniques.applies_to、test_layers.related"
        in instruction
    )
    assert (
        "不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 risk-board JSON 代码块"
        in instruction
    )
    assert "后端会负责确定性渲染" in instruction
    assert "右侧测试策略蓝图" in instruction
    assert "Mermaid quadrantChart" in instruction
    assert "Mermaid block-beta" in instruction
    assert "ai4se-visual risk-board" in instruction


def test_strategy_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "用户需求",
        ValueError("risks.0.rpn does not match severity * occurrence * detection"),
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "Mermaid、D2、Graphviz DOT、PlantUML 代码块或表格" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_parse_agent_turn_output_text_renders_cases_artifact_data():
    json_text = json.dumps(
        {
            "chat": "我已生成可执行测试用例集，请确认右侧内容。",
            "artifact_data": VALID_CASES_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "DELIVERY",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 测试用例集")
    assert '"type": "traceability-matrix"' in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "DELIVERY"


def test_cases_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "TEST_DESIGN",
        "CASES",
    )

    assert "artifact_data" in instruction
    assert "case_groups" in instruction
    assert "coverage_trace" in instruction
    assert "traceability-matrix" in instruction
    assert "stage_action" in instruction
    assert '"target_stage_id": "DELIVERY"' in instruction
    assert "不要输出完整 Markdown" in instruction
    assert "artifact_update.markdown" not in instruction


def test_cases_structured_output_instruction_omits_derived_statistics():
    instruction = build_structured_output_instruction("TEST_DESIGN", "CASES")

    assert '"case_statistics"' not in instruction
    assert "case_groups" in instruction
    assert "case_statistics 由后端根据 case_groups 计算，模型不要输出" in instruction


def test_cases_structured_output_instruction_omits_case_dimension_examples():
    instruction = build_structured_output_instruction("TEST_DESIGN", "CASES")

    assert (
        '"case_id": "TC-001", "title": "...", "priority": "P0", "dimension":'
        not in instruction
    )
    assert (
        "case_groups[].cases[].dimension 缺省时由后端按外层 "
        "case_groups[].dimension 派生"
    ) in instruction


def test_cases_structured_output_instruction_uses_manifest_artifact_data_contract():
    instruction = build_structured_output_instruction("TEST_DESIGN", "CASES")

    assert (
        format_artifact_data_contract_instruction("TEST_DESIGN", "CASES") in instruction
    )
    assert "case_statistics 由后端根据 case_groups 计算，模型不要输出" in instruction
    assert "case_groups[].cases[].case_id 必须唯一" in instruction
    assert "automation_candidates.case_id" in instruction
    assert "coverage_trace.covered_cases" in instruction
    assert (
        "不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 traceability-matrix JSON 代码块"
        in instruction
    )
    assert (
        "后端会负责确定性渲染右侧测试用例集和 ai4se-visual traceability-matrix"
        in instruction
    )


def test_cases_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "用户需求",
        ValueError("coverage_trace.0.covered_cases contains unknown case id TC-404"),
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "Mermaid、D2、Graphviz DOT、PlantUML 代码块或表格" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_parse_agent_turn_output_text_renders_delivery_artifact_data():
    json_text = json.dumps(
        {
            "chat": "我已整理测试设计交付文档，请确认右侧终稿。",
            "artifact_data": VALID_DELIVERY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 测试设计文档")
    assert '"type": "coverage-map"' in output.artifact_update.markdown
    assert output.stage_action is None


def test_parse_agent_turn_output_text_renders_delivery_without_derived_counts():
    artifact_data = copy.deepcopy(VALID_DELIVERY_ARTIFACT_DATA)
    artifact_data["delivery_metrics"].pop("total_cases")
    artifact_data["delivery_metrics"].pop("high_risk_count")
    for item in artifact_data["case_summary_items"]:
        item.pop("case_count")

    json_text = json.dumps(
        {
            "chat": "我已整理测试设计交付文档，请确认右侧终稿。",
            "artifact_data": artifact_data,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_data["delivery_metrics"]["total_cases"] == 2
    assert output.artifact_data["delivery_metrics"]["high_risk_count"] == 1
    assert [
        item["case_count"] for item in output.artifact_data["case_summary_items"]
    ] == [1, 1]
    assert '"type": "coverage-map"' in output.artifact_update.markdown


def test_delivery_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "TEST_DESIGN",
        "DELIVERY",
    )

    assert "artifact_data" in instruction
    assert "delivery_metrics" in instruction
    assert "coverage_map" in instruction
    assert "coverage-map" in instruction
    assert "stage_action" in instruction
    assert 'stage_action": null' in instruction
    assert "不要输出完整 Markdown" in instruction
    assert "artifact_update.markdown" not in instruction


def test_delivery_structured_output_instruction_omits_derived_delivery_counts():
    instruction = build_structured_output_instruction(
        "TEST_DESIGN",
        "DELIVERY",
    )

    assert '"case_count":' not in instruction
    assert '"total_cases":' not in instruction
    assert '"high_risk_count":' not in instruction
    assert (
        "case_summary_items[].case_count 由后端按 "
        "p0_count + p1_count + p2_count 派生，模型不要输出"
    ) in instruction
    assert (
        "delivery_metrics.total_cases 由后端按 "
        "case_summary_items[].case_count 总和派生，模型不要输出"
    ) in instruction
    assert (
        "delivery_metrics.high_risk_count 由后端按 open_risks 中 "
        "risk_type 包含“风险”且 acceptable 不为“是”的条目数量派生，模型不要输出"
    ) in instruction


@pytest.mark.parametrize(
    ("metric_name", "expected_field_path", "expected_validator"),
    [
        (
            "total_cases",
            "artifact_data.delivery_metrics.total_cases",
            "delivery_total_cases_mismatch",
        ),
        (
            "high_risk_count",
            "artifact_data.delivery_metrics.high_risk_count",
            "delivery_high_risk_count_mismatch",
        ),
    ],
)
def test_delivery_retry_prompt_identifies_derived_metric_to_omit(
    metric_name,
    expected_field_path,
    expected_validator,
):
    canary = "delivery-payload-canary"
    invalid = copy.deepcopy(VALID_DELIVERY_ARTIFACT_DATA)
    invalid["delivery_metrics"][metric_name] = 99
    invalid["delivery_metrics"]["project_name"] = canary

    with pytest.raises(ValidationError) as captured:
        DeliveryArtifactData.model_validate(invalid)

    prompt = build_raw_json_retry_prompt(
        "用户需求",
        captured.value,
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=schema_validation" in prompt
    assert f"fieldPath={expected_field_path}" in prompt
    assert f"validator={expected_validator}" in prompt
    assert (
        f"模型不要输出 {expected_field_path.removeprefix('artifact_data.')}" in prompt
    )
    assert "由后端派生" in prompt
    assert canary not in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "Mermaid、D2、Graphviz DOT、PlantUML 代码块或表格" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_parse_agent_turn_output_text_renders_req_review_artifact_data():
    json_text = json.dumps(
        {
            "chat": "我已完成需求质量诊断，请确认右侧问题清单。",
            "artifact_data": VALID_REQ_REVIEW_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "REPORT",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 需求评审问题清单")
    assert '"type": "score-matrix"' in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "REPORT"


def test_parse_agent_turn_output_text_renders_req_review_without_issue_counts():
    artifact_data = copy.deepcopy(VALID_REQ_REVIEW_ARTIFACT_DATA)
    artifact_data["issue_statistics"].pop("p0_count")
    artifact_data["issue_statistics"].pop("p1_count")
    artifact_data["issue_statistics"].pop("p2_count")

    json_text = json.dumps(
        {
            "chat": "我已完成需求质量诊断，请确认右侧问题清单。",
            "artifact_data": artifact_data,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "REPORT",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_data["issue_statistics"]["p0_count"] == 1
    assert output.artifact_data["issue_statistics"]["p1_count"] == 1
    assert output.artifact_data["issue_statistics"]["p2_count"] == 0
    assert '"type": "score-matrix"' in output.artifact_update.markdown


def test_req_review_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "REQ_REVIEW",
        "REVIEW",
    )

    assert "artifact_data" in instruction
    assert "issue_statistics" in instruction
    assert "issue_groups" in instruction
    assert "score-matrix" in instruction
    assert "stage_action" in instruction
    assert '"target_stage_id": "REPORT"' in instruction
    assert "不要输出完整 Markdown" in instruction
    assert "artifact_update.markdown" not in instruction


def test_req_review_structured_output_instruction_omits_issue_count_fields():
    instruction = build_structured_output_instruction(
        "REQ_REVIEW",
        "REVIEW",
    )

    assert '"p0_count":' not in instruction
    assert '"p1_count":' not in instruction
    assert '"p2_count":' not in instruction
    assert (
        "issue_statistics.p0_count/p1_count/p2_count 缺省时由后端按 "
        "issue_groups[].issues[].priority 中 P0/P1/P2 的数量派生"
    ) in instruction


def test_req_review_structured_output_instruction_omits_issue_dimension_examples():
    instruction = build_structured_output_instruction(
        "REQ_REVIEW",
        "REVIEW",
    )

    assert '"issue_id": "Q-001", "dimension":' not in instruction
    assert (
        "issue_groups[].issues[].dimension 缺省时由后端按外层 "
        "issue_groups[].dimension 派生"
    ) in instruction


def test_req_review_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "用户需求",
        ValueError("issue_statistics.p0_count must match issue_groups"),
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "Mermaid、D2、Graphviz DOT、PlantUML 代码块或表格" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_parse_agent_turn_output_text_renders_req_review_report_artifact_data():
    json_text = json.dumps(
        {
            "chat": "我已整理正式需求评审报告，请确认右侧内容。",
            "artifact_data": VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="REQ_REVIEW",
        current_stage_id="REPORT",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 需求评审报告")
    assert '"type": "priority-board"' in output.artifact_update.markdown
    assert output.stage_action is None


def test_parse_agent_turn_output_text_renders_req_review_report_without_statistics():
    artifact_data = copy.deepcopy(VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA)
    artifact_data.pop("issue_statistics")

    json_text = json.dumps(
        {
            "chat": "我已整理正式需求评审报告，请确认右侧内容。",
            "artifact_data": artifact_data,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="REQ_REVIEW",
        current_stage_id="REPORT",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_data["issue_statistics"] == {
        "p0_count": 1,
        "p1_count": 1,
        "p2_count": 1,
    }
    assert '"type": "priority-board"' in output.artifact_update.markdown


def test_req_review_report_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "REQ_REVIEW",
        "REPORT",
    )

    assert "artifact_data" in instruction
    assert "issue_statistics" in instruction
    assert "issue_closures" in instruction
    assert "priority-board" in instruction
    assert "stage_action" in instruction
    assert 'stage_action": null' in instruction
    assert "不要输出完整 Markdown" in instruction
    assert "artifact_update.markdown" not in instruction


def test_req_review_report_structured_output_instruction_omits_issue_statistics():
    instruction = build_structured_output_instruction(
        "REQ_REVIEW",
        "REPORT",
    )

    assert '"issue_statistics":' not in instruction
    assert (
        "issue_statistics.p0_count/p1_count/p2_count 缺省时由后端按 "
        "issue_closures[].priority 中 P0/P1/P2 的数量派生"
    ) in instruction


def test_req_review_report_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "用户需求",
        ValueError("issue_statistics.p0_count must match issue_closures"),
        workflow_id="REQ_REVIEW",
        current_stage_id="REPORT",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "Mermaid、D2、Graphviz DOT、PlantUML 代码块或表格" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_parse_agent_turn_output_text_renders_prd_review_artifact_data():
    json_text = json.dumps(
        {
            "chat": "我已整理 PRD 补全建议，请确认右侧内容。",
            "artifact_data": ARTIFACT_DATA_STAGE_FIXTURES[
                ("PRD_REVIEW", "COMPLETION_PLAN")
            ],
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "REVISION_BLUEPRINT",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="PRD_REVIEW",
        current_stage_id="COMPLETION_PLAN",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# PRD 补全建议")
    assert '"type": "action-board"' in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "REVISION_BLUEPRINT"


def test_prd_review_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "PRD_REVIEW",
        "COMPLETION_PLAN",
    )

    assert "artifact_data" in instruction
    assert "quality_findings" in instruction
    assert "completion_actions" in instruction
    assert "action-board" in instruction
    assert "stage_action" in instruction
    assert "不要输出完整 Markdown" in instruction
    assert "artifact_update.markdown" not in instruction


@pytest.mark.parametrize(
    "stage_id",
    ["INVENTORY", "QUALITY_AUDIT", "COMPLETION_PLAN", "REVISION_BLUEPRINT"],
)
def test_prd_review_structured_output_instruction_uses_manifest_artifact_data_contract(
    stage_id,
):
    instruction = build_structured_output_instruction(
        "PRD_REVIEW",
        stage_id,
    )
    contract_instruction = format_artifact_data_contract_instruction(
        "PRD_REVIEW",
        stage_id,
    )

    assert "契约外字段会被拒绝" in contract_instruction
    assert contract_instruction in instruction


@pytest.mark.parametrize(
    ("stage_id", "expected_stage_action"),
    [
        (
            "INVENTORY",
            '"stage_action": {"type": "request_next_stage", "target_stage_id": "QUALITY_AUDIT"}',
        ),
        (
            "QUALITY_AUDIT",
            '"stage_action": {"type": "request_next_stage", "target_stage_id": "COMPLETION_PLAN"}',
        ),
        (
            "COMPLETION_PLAN",
            '"stage_action": {"type": "request_next_stage", "target_stage_id": "REVISION_BLUEPRINT"}',
        ),
        ("REVISION_BLUEPRINT", '"stage_action": null'),
    ],
)
def test_prd_review_structured_output_instruction_targets_exact_next_stage(
    stage_id,
    expected_stage_action,
):
    instruction = build_structured_output_instruction(
        "PRD_REVIEW",
        stage_id,
    )

    assert expected_stage_action in instruction
    assert "QUALITY_AUDIT/COMPLETION_PLAN/REVISION_BLUEPRINT" not in instruction


def test_parse_agent_turn_output_text_renders_value_elevator_artifact_data():
    json_text = json.dumps(
        {
            "chat": "已生成价值定位分析。",
            "artifact_data": VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "PERSONA",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 价值定位分析")
    assert "flowchart TD" in output.artifact_update.markdown
    assert '"type": "score-matrix"' in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "PERSONA"


def test_parse_agent_turn_output_text_renders_value_elevator_without_model_score_totals():
    artifact_data = copy.deepcopy(VALID_VALUE_ELEVATOR_ARTIFACT_DATA)
    artifact_data["score_summary"].pop("total_score")
    artifact_data["score_summary"].pop("average_score")

    output = parse_agent_turn_output_text(
        json.dumps(
            {
                "chat": "已生成价值定位分析。",
                "artifact_data": artifact_data,
                "stage_action": {
                    "type": "request_next_stage",
                    "target_stage_id": "PERSONA",
                },
                "warnings": [],
            },
            ensure_ascii=False,
        ),
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert output.artifact_update.markdown is not None
    assert "总分 16，平均分 3.20" in output.artifact_update.markdown
    assert output.artifact_data is not None
    assert output.artifact_data["score_summary"]["total_score"] == 16
    assert output.artifact_data["score_summary"]["average_score"] == 3.2


def test_value_elevator_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "VALUE_DISCOVERY",
        "ELEVATOR",
    )

    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "value_flow" in instruction
    assert "score_matrix" in instruction
    assert '"score_summary": {"judgement": "..."}' in instruction
    assert '"total_score"' not in instruction
    assert "average_score" not in instruction
    assert "总分和平均分由后端根据 score_matrix.score 计算" in instruction
    assert '"target_stage_id": "PERSONA"' in instruction
    assert "不要输出完整 Markdown" in instruction
    assert "score-matrix" in instruction


def test_value_elevator_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "原始提示",
        ValueError("score_summary.total_score must equal score_matrix score sum"),
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_parse_agent_turn_output_text_renders_value_persona_artifact_data():
    json_text = json.dumps(
        {
            "chat": "已生成用户画像分析。",
            "artifact_data": VALID_VALUE_PERSONA_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "JOURNEY",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="PERSONA",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 用户画像分析")
    assert "### 画像 1" in output.artifact_update.markdown
    assert "## 用户优先级排序" in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "JOURNEY"


def test_parse_agent_turn_output_text_renders_value_journey_artifact_data():
    json_text = json.dumps(
        {
            "chat": "已生成用户旅程分析。",
            "artifact_data": VALID_VALUE_JOURNEY_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "BLUEPRINT",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="JOURNEY",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 用户旅程分析")
    assert "journey\n    title 核心用户旅程" in output.artifact_update.markdown
    assert '"type": "journey-map"' in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "BLUEPRINT"


def test_parse_agent_turn_output_text_renders_value_blueprint_artifact_data():
    json_text = json.dumps(
        {
            "chat": "已生成需求蓝图。",
            "artifact_data": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# AI4SE 测试设计助手 需求蓝图")
    assert "mindmap" in output.artifact_update.markdown
    assert "flowchart TD" in output.artifact_update.markdown
    assert '"type": "roadmap"' in output.artifact_update.markdown
    assert output.stage_action is None


def test_parse_agent_turn_output_text_renders_incident_timeline_artifact_data():
    json_text = json.dumps(
        {
            "chat": "已还原故障事件时间线。",
            "artifact_data": VALID_INCIDENT_TIMELINE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "ROOT_CAUSE",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="TIMELINE",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 故障复盘报告")
    assert "```ai4se-visual" in output.artifact_update.markdown
    assert '"type": "timeline-map"' in output.artifact_update.markdown
    assert '"time": "14:30"' in output.artifact_update.markdown
    assert "14:30 | 订单状态延迟告警触发" in output.artifact_update.markdown
    assert "```mermaid" not in output.artifact_update.markdown
    assert "14：30 : 订单状态延迟告警触发" not in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "ROOT_CAUSE"


def test_parse_agent_turn_output_text_renders_incident_root_cause_artifact_data():
    json_text = json.dumps(
        {
            "chat": "已完成根因分析。",
            "artifact_data": VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "IMPROVEMENT",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="ROOT_CAUSE",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 故障复盘报告")
    assert "### 6.1 5-Why 分析链" in output.artifact_update.markdown
    assert "mindmap" in output.artifact_update.markdown
    assert '"type": "cause-map"' in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "IMPROVEMENT"


def test_parse_agent_turn_output_text_renders_incident_improvement_artifact_data():
    json_text = json.dumps(
        {
            "chat": "已完成故障改进报告。",
            "artifact_data": VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="IMPROVEMENT",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 故障复盘报告")
    assert "### 7. 改进措施" in output.artifact_update.markdown
    assert "pie title 改进措施优先级分布" in output.artifact_update.markdown
    assert '"type": "action-board"' in output.artifact_update.markdown
    assert output.stage_action is None


def test_parse_agent_turn_output_text_renders_incident_improvement_without_statistics():
    artifact_data = copy.deepcopy(VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA)
    artifact_data["report_info"].pop("action_count")
    artifact_data.pop("priority_distribution")

    json_text = json.dumps(
        {
            "chat": "已完成故障改进报告。",
            "artifact_data": artifact_data,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="IMPROVEMENT",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_data["report_info"]["action_count"] == 3
    assert output.artifact_data["priority_distribution"] == {
        "urgent_count": 1,
        "important_count": 1,
        "normal_count": 1,
    }
    assert '"type": "action-board"' in output.artifact_update.markdown


def test_parse_agent_turn_output_text_renders_idea_define_artifact_data():
    json_text = json.dumps(
        {
            "chat": "已形成问题域验证基线。",
            "artifact_data": VALID_IDEA_DEFINE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "DIVERGE",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DEFINE",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 问题域分析")
    assert "## 问题域全景" in output.artifact_update.markdown
    assert "mindmap" in output.artifact_update.markdown
    assert "证据等级" in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "DIVERGE"


def test_parse_agent_turn_output_text_renders_idea_diverge_artifact_data():
    json_text = json.dumps(
        {
            "chat": "已形成创意发散候选集。",
            "artifact_data": VALID_IDEA_DIVERGE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CONVERGE",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DIVERGE",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 创意发散")
    assert "## 发散全景图" in output.artifact_update.markdown
    assert "mindmap" in output.artifact_update.markdown
    assert "## 创意卡片库" in output.artifact_update.markdown
    assert "关键假设" in output.artifact_update.markdown
    assert "状态理由" in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "CONVERGE"


def test_parse_agent_turn_output_text_renders_idea_converge_artifact_data():
    json_text = json.dumps(
        {
            "chat": "已完成创意收敛评估。",
            "artifact_data": VALID_IDEA_CONVERGE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CONCEPT",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONVERGE",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 收敛聚焦")
    assert "## 决策矩阵" in output.artifact_update.markdown
    assert "quadrantChart" in output.artifact_update.markdown
    assert "## ICE 评估表" in output.artifact_update.markdown
    assert "推荐方案" in output.artifact_update.markdown
    assert "用户确认状态" in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "CONCEPT"


def test_parse_agent_turn_output_text_renders_idea_converge_without_ice_score():
    artifact_data = copy.deepcopy(VALID_IDEA_CONVERGE_ARTIFACT_DATA)
    for item in artifact_data["ice_evaluations"]:
        item.pop("ice_score")

    json_text = json.dumps(
        {
            "chat": "已完成创意收敛评估。",
            "artifact_data": artifact_data,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CONCEPT",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONVERGE",
    )

    assert output.artifact_update.type == "replace"
    assert [item["ice_score"] for item in output.artifact_data["ice_evaluations"]] == [
        10.0,
        6.0,
        2.0,
    ]
    assert "## ICE 评估表" in output.artifact_update.markdown


def test_parse_agent_turn_output_text_renders_idea_converge_without_rank():
    artifact_data = copy.deepcopy(VALID_IDEA_CONVERGE_ARTIFACT_DATA)
    for item in artifact_data["ice_evaluations"]:
        item.pop("rank")

    json_text = json.dumps(
        {
            "chat": "已完成创意收敛评估。",
            "artifact_data": artifact_data,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CONCEPT",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONVERGE",
    )

    assert output.artifact_update.type == "replace"
    assert [item["rank"] for item in output.artifact_data["ice_evaluations"]] == [
        1,
        2,
        3,
    ]
    assert "## ICE 评估表" in output.artifact_update.markdown


def test_parse_agent_turn_output_text_renders_idea_concept_artifact_data():
    json_text = json.dumps(
        {
            "chat": "已完成产品概念简报。",
            "artifact_data": VALID_IDEA_CONCEPT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONCEPT",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 产品概念简报")
    assert "## 定位声明" in output.artifact_update.markdown
    assert "## Lean Canvas 产品画布" in output.artifact_update.markdown
    assert "pie title MVP 功能组成" in output.artifact_update.markdown
    assert "flowchart TD" in output.artifact_update.markdown
    assert '"type": "mvp-map"' in output.artifact_update.markdown
    assert "## 下一步行动" in output.artifact_update.markdown
    assert output.stage_action is None


def test_parse_agent_turn_output_text_renders_story_breakdown_artifact_data():
    json_text = json.dumps(
        {
            "chat": "已完成用户故事拆解包。",
            "artifact_data": ARTIFACT_DATA_STAGE_FIXTURES[
                ("STORY_BREAKDOWN", "SPRINT_PLAN")
            ],
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(
        json_text,
        workflow_id="STORY_BREAKDOWN",
        current_stage_id="SPRINT_PLAN",
    )

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 用户故事拆解包")
    assert "## Epic Map" in output.artifact_update.markdown
    assert "## User Story Backlog" in output.artifact_update.markdown
    assert "## Sprint 切片建议" in output.artifact_update.markdown
    assert '"type": "flow-map"' in output.artifact_update.markdown
    assert '"nodes"' in output.artifact_update.markdown
    assert '"edges"' in output.artifact_update.markdown
    assert '"type": "story-map"' in output.artifact_update.markdown
    assert "flowchart TD" not in output.artifact_update.markdown
    assert output.stage_action is None


def test_value_persona_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "VALUE_DISCOVERY",
        "PERSONA",
    )

    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "personas" in instruction
    assert "decision_chain" in instruction
    assert "priority_ranking" in instruction
    assert "personas[].behavior_features[] 每一项都必须包含非空 trigger" in instruction
    assert '"target_stage_id": "JOURNEY"' in instruction
    assert "不要输出完整 Markdown" in instruction


def test_value_journey_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "VALUE_DISCOVERY",
        "JOURNEY",
    )

    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "journey_stages" in instruction
    assert "pain_priorities" in instruction
    assert "opportunity_scores" in instruction
    assert "journey-map" in instruction
    assert '"target_stage_id": "BLUEPRINT"' in instruction
    assert "不要输出完整 Markdown" in instruction


def test_value_blueprint_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "VALUE_DISCOVERY",
        "BLUEPRINT",
    )

    assert (
        format_artifact_data_contract_instruction("VALUE_DISCOVERY", "BLUEPRINT")
        in instruction
    )
    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "product_overview" in instruction
    assert "requirements" in instruction
    assert "acceptance_criteria" in instruction
    assert "lisa_handoff_inputs" in instruction
    assert "roadmap" in instruction
    assert "不要输出完整 Markdown" in instruction


def test_incident_timeline_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "INCIDENT_REVIEW",
        "TIMELINE",
    )

    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "incident_summary" in instruction
    assert "impact_metrics" in instruction
    assert "fact_sources" in instruction
    assert "timeline_events" in instruction
    assert "fact_separation" in instruction
    assert '"target_stage_id": "ROOT_CAUSE"' in instruction
    assert "不要输出完整 Markdown" in instruction
    assert (
        format_artifact_data_contract_instruction("INCIDENT_REVIEW", "TIMELINE")
        in instruction
    )
    assert "timeline_events[].fact_ids 必须至少包含 1 个事实 ID" in instruction
    assert "fact_sources[].fact_id 必须唯一" in instruction
    assert "ai4se-visual timeline-map" in instruction
    assert "Mermaid timeline" not in instruction


def test_incident_root_cause_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "INCIDENT_REVIEW",
        "ROOT_CAUSE",
    )

    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "analysis_context" in instruction
    assert "why_chain" in instruction
    assert "cause_evidence" in instruction
    assert "fishbone_categories" in instruction
    assert "root_cause_conclusions" in instruction
    assert "cause-map" in instruction
    assert '"target_stage_id": "IMPROVEMENT"' in instruction
    assert "不要输出完整 Markdown" in instruction


def test_incident_improvement_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "INCIDENT_REVIEW",
        "IMPROVEMENT",
    )

    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "report_info" in instruction
    assert "improvement_actions" in instruction
    assert "root_cause_coverage" in instruction
    assert "review_plan" in instruction
    assert "residual_risks" in instruction
    assert "action-board" in instruction
    assert 'stage_action": null' in instruction
    assert "不要输出完整 Markdown" in instruction
    assert (
        format_artifact_data_contract_instruction("INCIDENT_REVIEW", "IMPROVEMENT")
        in instruction
    )
    assert "report_info.action_count" in instruction
    assert "improvement_actions[].action_id 必须唯一" in instruction
    assert "ai4se-visual action-board" in instruction


def test_incident_improvement_structured_output_instruction_omits_statistics():
    instruction = build_structured_output_instruction(
        "INCIDENT_REVIEW",
        "IMPROVEMENT",
    )

    assert '"action_count":' not in instruction
    assert '"priority_distribution":' not in instruction
    assert (
        "report_info.action_count 缺省时由后端按 improvement_actions 数量派生"
        in instruction
    )
    assert (
        "priority_distribution 缺省时由后端按 improvement_actions[].priority "
        "中紧急/重要/常规的数量派生"
    ) in instruction


def test_idea_define_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "DEFINE",
    )

    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "problem_statement" in instruction
    assert "target_users" in instruction
    assert "problem_landscape" in instruction
    assert "evidence_items" in instruction
    assert "problem_user_fit" in instruction
    assert '"target_stage_id": "DIVERGE"' in instruction
    assert "不要输出完整 Markdown" in instruction


def test_idea_define_structured_output_instruction_uses_problem_id_references():
    instruction = build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "DEFINE",
    )

    assert "root_problem_id" in instruction
    assert "related_problem_ids" in instruction
    assert "related_problem" in instruction
    assert "evidence_ids" in instruction
    assert "逐字出现在" not in instruction


def test_idea_diverge_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "DIVERGE",
    )

    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "divergence_method" in instruction
    assert "idea_landscape" in instruction
    assert "idea_cards" in instruction
    assert "idea_sources" in instruction
    assert "parked_or_excluded" in instruction
    assert '"target_stage_id": "CONVERGE"' in instruction
    assert "不要输出完整 Markdown" in instruction


def test_idea_converge_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "CONVERGE",
    )

    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "decision_matrix" in instruction
    assert "ice_evaluations" in instruction
    assert "resource_constraints" in instruction
    assert "sensitivity_analysis" in instruction
    assert "validation_experiments" in instruction
    assert "merge_paths" in instruction
    assert '"target_stage_id": "CONCEPT"' in instruction
    assert "不要输出完整 Markdown" in instruction


def test_idea_converge_structured_output_instruction_uses_manifest_artifact_data_contract():
    instruction = build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "CONVERGE",
    )

    assert "artifact_data 中所有字符串必须非空" in instruction
    assert "ice_evaluations.idea_id 必须唯一" in instruction
    assert "decision_matrix.recommended_idea_id" in instruction
    assert "validation_experiments.idea_ids" in instruction
    assert "merge_paths.source_idea_ids" in instruction
    assert "ice_score 缺省时由后端按 impact * confidence / effort 派生" in instruction
    assert "rank 缺省时由后端按 ICE 得分降序派生" in instruction
    assert (
        "不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 quadrantChart"
        in instruction
    )
    assert "后端会负责确定性渲染右侧收敛聚焦产物和 Mermaid quadrantChart" in instruction


def test_idea_converge_structured_output_instruction_omits_ice_score():
    instruction = build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "CONVERGE",
    )

    assert '"ice_score":' not in instruction
    assert "ice_score 缺省时由后端按 impact * confidence / effort 派生" in instruction


def test_idea_converge_structured_output_instruction_omits_rank():
    instruction = build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "CONVERGE",
    )

    assert '"rank":' not in instruction
    assert "rank 缺省时由后端按 ICE 得分降序派生" in instruction


def test_idea_concept_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "CONCEPT",
    )

    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "positioning_statement" in instruction
    assert "core_assumptions" in instruction
    assert "lean_canvas" in instruction
    assert "mvp_features" in instruction
    assert "growth_funnel" in instruction
    assert "premortem_risks" in instruction
    assert "validation_roadmap" in instruction
    assert "next_actions" in instruction
    assert '"stage_action": null' in instruction
    assert "不要输出完整 Markdown" in instruction


def test_story_breakdown_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "STORY_BREAKDOWN",
        "SPRINT_PLAN",
    )

    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "input_analysis" in instruction
    assert "epics" in instruction
    assert "user_stories" in instruction
    assert "acceptance_criteria" in instruction
    assert "sprint_slices" in instruction
    assert "lisa_handoff_inputs" in instruction
    assert '"stage_action": null' in instruction
    assert "不要输出完整 Markdown" in instruction


@pytest.mark.parametrize(
    "stage_id",
    ["INPUT_ANALYSIS", "EPIC_MAPPING", "STORY_BACKLOG", "SPRINT_PLAN"],
)
def test_story_breakdown_structured_output_instruction_omits_story_sprint_examples(
    stage_id,
):
    instruction = build_structured_output_instruction(
        "STORY_BREAKDOWN",
        stage_id,
    )

    forbidden_story_sprint_example = (
        '"story_id": "US-001", "epic_id": "EPIC-001", "title": "...", '
        '"user_story": "作为...我想...以便...", "priority": "P0/P1/P2", "sprint":'
    )

    assert forbidden_story_sprint_example not in instruction
    assert (
        "user_stories[].sprint 缺省时由后端按 sprint_slices[].story_ids "
        "所属 sprint_slices[].sprint_id 派生"
    ) in instruction


@pytest.mark.parametrize(
    "stage_id",
    ["INPUT_ANALYSIS", "EPIC_MAPPING", "STORY_BACKLOG", "SPRINT_PLAN"],
)
def test_story_breakdown_structured_output_instruction_uses_manifest_artifact_data_contract(
    stage_id,
):
    instruction = build_structured_output_instruction(
        "STORY_BREAKDOWN",
        stage_id,
    )

    assert (
        format_artifact_data_contract_instruction("STORY_BREAKDOWN", stage_id)
        in instruction
    )
    document_info_line = next(
        line for line in instruction.splitlines() if '"document_info"' in line
    )
    assert '"workflow"' not in document_info_line
    assert '"stage"' not in document_info_line
    assert "document_info.workflow 和 document_info.stage 由后端注入" in instruction


def test_value_persona_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "原始提示",
        ValueError("behavior_scenarios.0.persona_id references unknown persona ids"),
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="PERSONA",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_value_persona_retry_prompt_identifies_missing_behavior_trigger():
    invalid = copy.deepcopy(VALID_VALUE_PERSONA_ARTIFACT_DATA)
    invalid["personas"][0]["behavior_features"][1].pop("trigger")

    with pytest.raises(ValidationError) as captured:
        ValueDiscoveryPersonaArtifactData.model_validate(invalid)

    prompt = build_raw_json_retry_prompt(
        "原始提示",
        captured.value,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="PERSONA",
    )

    assert "failureCategory=schema_validation" in prompt
    assert "fieldPath=artifact_data.personas[].behavior_features[].trigger" in prompt
    assert "validator=missing" in prompt
    assert "该路径对应的每个对象都必须包含这个字段" in prompt


def test_value_journey_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "原始提示",
        ValueError("pain_priorities references unknown stage ids"),
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="JOURNEY",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_value_blueprint_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "原始提示",
        ValueError("acceptance_criteria references unknown requirement ids"),
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_incident_timeline_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "原始提示",
        ValueError("timeline_events references unknown fact ids"),
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="TIMELINE",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_incident_root_cause_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "原始提示",
        ValueError("fishbone_categories references unknown cause ids"),
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="ROOT_CAUSE",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_incident_improvement_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "原始提示",
        ValueError("root_cause_coverage references unknown action ids"),
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="IMPROVEMENT",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_idea_define_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "原始提示",
        ValueError("problem_user_fit references unknown evidence ids"),
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DEFINE",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_idea_diverge_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "原始提示",
        ValueError("idea_sources references unknown idea ids"),
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DIVERGE",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_idea_converge_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "原始提示",
        ValueError(
            "ice_evaluations.0.ice_score must equal impact * confidence / effort"
        ),
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONVERGE",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_idea_concept_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "原始提示",
        ValueError("growth_funnel missing required stages: Referral"),
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONCEPT",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_story_breakdown_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "请拆解用户故事",
        ValueError("acceptance_criteria references unknown story ids"),
        workflow_id="STORY_BREAKDOWN",
        current_stage_id="SPRINT_PLAN",
    )

    assert "artifact_data" in prompt
    assert "failureCategory=artifact_validation" in prompt
    assert "fieldPath=artifact_data" in prompt
    assert "validator=artifact_value" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt


def test_runtime_raw_json_stream_turn_yields_real_delta_before_final_output(
    monkeypatch,
):
    final_json = (
        '{"chat":"正在梳理需求。",'
        '"artifact_update":{"type":"replace","markdown":"'
        f"{VALID_CLARIFY_ARTIFACT_JSON}" + '"},'
        '"stage_action":null,"warnings":[]}'
    )
    first_chunk_end = len('{"chat":"正在')
    second_chunk_end = len(
        '{"chat":"正在梳理需求。",'
        '"artifact_update":{"type":"replace","markdown":"# 需求分析文档\\n\\n'
    )
    chunks = [
        final_json[:first_chunk_end],
        final_json[first_chunk_end:second_chunk_end],
        final_json[second_chunk_end:],
    ]
    calls = []

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            system_prompt="system prompt",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    assert isinstance(outputs[0], AgentTurnDeltaOutput)
    assert outputs[0].chat == "正在"
    assert isinstance(outputs[1], AgentTurnDeltaOutput)
    assert outputs[1].chat == "正在梳理需求。"
    assert outputs[-1].chat == "正在梳理需求。"
    assert outputs[-1].artifact_update.markdown == VALID_CLARIFY_ARTIFACT
    assert calls[0]["response_format"] == {"type": "json_object"}


def test_runtime_raw_json_stream_turn_renders_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "我已整理登录需求澄清基线，请确认右侧文档。",
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    chunks = [
        final_json[: final_json.index('"artifact_data"')],
        final_json[
            final_json.index('"artifact_data"') : final_json.index('"stage_action"')
        ],
        final_json[final_json.index('"stage_action"') :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是测试专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求: 登录功能",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert partial_markdowns
    assert partial_markdowns[0].startswith("# 需求分析文档")
    assert "flowchart TD" in partial_markdowns[0]
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 需求分析文档")
    assert "flowchart TD" in outputs[-1].artifact_update.markdown
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "TEST_DESIGN",
        "CLARIFY",
    )
    assert "结构化输出格式要求" in calls[0]["messages"][0]["content"]


def test_runtime_raw_json_stream_turn_does_not_synthesize_chat_for_artifact_first_progress(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "chat": "我已整理登录需求澄清基线，请确认右侧文档。",
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    chat_start = final_json.index('"chat"')

    def fake_stream_chat_completion_content(**kwargs):
        yield final_json[:chat_start]
        yield final_json[chat_start:]

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是测试专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求: 登录功能",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )
    first_artifact_delta = next(
        output
        for output in outputs
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
    )

    assert first_artifact_delta.chat is None
    assert first_artifact_delta.artifact_update.markdown is not None


def test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "我正在逐段形成需求分析文档。",
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    facts_prefix = prefix_after_artifact_data_member("requirement_facts")
    boundaries_prefix = prefix_after_artifact_data_member("system_boundaries")
    chunks = [
        facts_prefix,
        boundaries_prefix[len(facts_prefix) :],
        final_json[len(boundaries_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是测试专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求: 登录功能",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]
    partial_patches = [
        output.artifact_patch
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_patch is not None
    ]

    assert len(partial_markdowns) >= 2
    assert partial_markdowns[0].startswith("# 需求分析文档")
    assert "## 1. 需求事实清单" in partial_markdowns[0]
    assert "## 2. 被测系统与边界" not in partial_markdowns[0]
    assert "## 2. 被测系统与边界" in partial_markdowns[1]
    assert "## 3. 业务规则与数据状态" not in partial_markdowns[1]
    assert partial_patches == []
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert "## 3. 业务规则与数据状态" in outputs[-1].artifact_update.markdown


def test_runtime_raw_json_stream_turn_renders_strategy_artifact_data_before_final_output(
    monkeypatch,
):
    artifact_data = copy.deepcopy(VALID_STRATEGY_ARTIFACT_DATA)
    artifact_data["risks"][0].pop("rpn")
    final_json = json.dumps(
        {
            "chat": "我已形成风险驱动测试策略，请确认右侧蓝图。",
            "artifact_data": artifact_data,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    chunks = [
        final_json[: final_json.index('"artifact_data"')],
        final_json[
            final_json.index('"artifact_data"') : final_json.index('"stage_action"')
        ],
        final_json[final_json.index('"stage_action"') :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是测试专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请制定测试策略",
            workflow_id="TEST_DESIGN",
            current_stage_id="STRATEGY",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert partial_markdowns
    assert partial_markdowns[0].startswith("# 测试策略蓝图")
    assert "quadrantChart" in partial_markdowns[0]
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown.startswith("# 测试策略蓝图")


def test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "我正在逐段形成风险驱动测试策略。",
            "artifact_data": VALID_STRATEGY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    summary_prefix = prefix_after_artifact_data_member("strategy_summary")
    goals_prefix = prefix_after_artifact_data_member("quality_goals")
    chunks = [
        summary_prefix,
        goals_prefix[len(summary_prefix) :],
        final_json[len(goals_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是测试专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请制定测试策略",
            workflow_id="TEST_DESIGN",
            current_stage_id="STRATEGY",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[-1].startswith("# 测试策略蓝图")
    assert "## 1. 策略摘要" in partial_markdowns[-1]
    assert "## 2. 质量目标" in partial_markdowns[-1]
    assert "## 3. 风险识别与 FMEA" in partial_markdowns[-1]
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert "## 3. 风险识别与 FMEA" in outputs[-1].artifact_update.markdown


def test_runtime_raw_json_stream_turn_waits_for_strategy_references_before_sections_four_to_six(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "我正在逐段形成风险驱动测试策略。",
            "artifact_data": VALID_STRATEGY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    risks_prefix = prefix_after_artifact_data_member("risks")
    techniques_prefix = prefix_after_artifact_data_member("test_techniques")
    layers_prefix = prefix_after_artifact_data_member("test_layers")
    points_prefix = prefix_after_artifact_data_member("test_points")
    chunks = [
        risks_prefix,
        techniques_prefix[len(risks_prefix) :],
        layers_prefix[len(techniques_prefix) :],
        points_prefix[len(layers_prefix) :],
        final_json[len(points_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是测试专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请制定测试策略",
            workflow_id="TEST_DESIGN",
            current_stage_id="STRATEGY",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert "## 3. 风险识别与 FMEA" in partial_markdowns[-1]
    assert "## 4. 测试技术选型" in partial_markdowns[-1]
    assert "## 6. 测试点拓扑" in partial_markdowns[-1]
    assert isinstance(outputs[-1], AgentTurnOutput)


def test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "我正在逐段形成测试用例集。",
            "artifact_data": VALID_CASES_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    bases_prefix = prefix_after_artifact_data_member("design_bases")
    cases_prefix = prefix_after_artifact_data_member("case_groups")
    environment_prefix = prefix_after_artifact_data_member("test_data_environments")
    chunks = [
        bases_prefix,
        cases_prefix[len(bases_prefix) :],
        environment_prefix[len(cases_prefix) :],
        final_json[len(environment_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是测试专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请生成测试用例集",
            workflow_id="TEST_DESIGN",
            current_stage_id="CASES",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]
    partial_patches = [
        output.artifact_patch
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_patch is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 测试用例集")
    assert "## 2. 用例设计依据" in partial_markdowns[0]
    assert "## 1. 用例统计" in partial_markdowns[-1]
    assert "## 3. 按维度分组的用例清单" in partial_markdowns[-1]
    assert "## 4. 测试数据与环境" in partial_markdowns[-1]
    assert "## 5. 自动化候选" in partial_markdowns[-1]
    assert partial_patches == []
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert "## 3. 按维度分组的用例清单" in (outputs[-1].artifact_update.markdown)
    assert '"type": "traceability-matrix"' in outputs[-1].artifact_update.markdown


def test_runtime_raw_json_stream_turn_renders_cases_after_case_groups_without_model_statistics(
    monkeypatch,
):
    artifact_data = copy.deepcopy(VALID_CASES_ARTIFACT_DATA)
    artifact_data.pop("case_statistics")
    final_json = json.dumps(
        {
            "chat": "我正在逐段形成测试用例集。",
            "artifact_data": artifact_data,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    bases_prefix = prefix_after_artifact_data_member("design_bases")
    cases_prefix = prefix_after_artifact_data_member("case_groups")
    chunks = [
        bases_prefix,
        cases_prefix[len(bases_prefix) :],
        final_json[len(cases_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是测试专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请生成测试用例集",
            workflow_id="TEST_DESIGN",
            current_stage_id="CASES",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 测试用例集")
    assert "## 2. 用例设计依据" in partial_markdowns[0]
    assert "## 1. 用例统计" in partial_markdowns[-1]
    assert "## 3. 按维度分组的用例清单" in partial_markdowns[-1]
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_data["case_statistics"] == {
        "total": 2,
        "p0_count": 1,
        "p1_count": 1,
        "p2_count": 0,
    }


def test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "我已整理测试设计交付文档，请确认右侧终稿。",
            "artifact_data": VALID_DELIVERY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    summary_prefix = prefix_after_artifact_data_member("executive_summary")
    requirement_prefix = prefix_after_artifact_data_member("requirement_summary")
    chunks = [
        summary_prefix,
        requirement_prefix[len(summary_prefix) :],
        final_json[len(requirement_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是测试专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请交付测试设计文档",
            workflow_id="TEST_DESIGN",
            current_stage_id="DELIVERY",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]
    partial_patches = [
        output.artifact_patch
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_patch is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 测试设计文档")
    assert "## 2. 执行摘要" in partial_markdowns[0]
    assert "## 1. 文档信息" in partial_markdowns[-1]
    assert "## 2. 执行摘要" in partial_markdowns[-1]
    assert "## 3. 需求分析摘要" in partial_markdowns[-1]
    assert "## 4. 测试策略摘要" in partial_markdowns[-1]
    assert partial_patches == []
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 测试设计文档")
    assert "## 4. 测试策略摘要" in outputs[-1].artifact_update.markdown
    assert '"type": "coverage-map"' in outputs[-1].artifact_update.markdown
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "delivery_metrics" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "TEST_DESIGN",
        "DELIVERY",
    )


def test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "我已完成需求质量诊断，请确认右侧问题清单。",
            "artifact_data": VALID_REQ_REVIEW_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "REPORT",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    scope_prefix = prefix_after_artifact_data_member("scope_items")
    statistics_prefix = prefix_after_artifact_data_member("issue_statistics")
    chunks = [
        scope_prefix,
        statistics_prefix[len(scope_prefix) :],
        final_json[len(statistics_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是需求评审专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请评审会员权益需求",
            workflow_id="REQ_REVIEW",
            current_stage_id="REVIEW",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]
    partial_patches = [
        output.artifact_patch
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_patch is not None
    ]

    assert len(partial_markdowns) >= 3
    assert partial_markdowns[0].startswith("# 需求评审问题清单")
    assert "## 评审范围与不评审范围" in partial_markdowns[0]
    assert "## 需求质量总览" not in partial_markdowns[0]
    assert "## 需求质量总览" in partial_markdowns[1]
    assert "## 问题统计" not in partial_markdowns[1]
    assert "## 问题统计" in partial_markdowns[-1]
    assert "## 按维度问题清单" in partial_markdowns[-1]
    assert partial_patches == []
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 需求评审问题清单")
    assert '"type": "score-matrix"' in outputs[-1].artifact_update.markdown
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "issue_statistics" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "REQ_REVIEW",
        "REVIEW",
    )


def test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "我已整理正式需求评审报告，请确认右侧内容。",
            "artifact_data": VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    conclusion_prefix = prefix_after_artifact_data_member("conclusion")
    statistics_prefix = prefix_after_artifact_data_member("issue_statistics")
    chunks = [
        conclusion_prefix,
        statistics_prefix[len(conclusion_prefix) :],
        final_json[len(statistics_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是需求评审专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请生成需求评审报告",
            workflow_id="REQ_REVIEW",
            current_stage_id="REPORT",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]
    partial_patches = [
        output.artifact_patch
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_patch is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 需求评审报告")
    assert "## 评审上下文" in partial_markdowns[0]
    assert "## 评审信息" in partial_markdowns[0]
    assert partial_markdowns[0].index("## 评审上下文") < partial_markdowns[0].index(
        "## 评审信息"
    )
    assert "## 评审结论" in partial_markdowns[-1]
    assert "## 评审上下文" in partial_markdowns[-1]
    assert "## 评审信息" in partial_markdowns[-1]
    assert "## 问题统计" in partial_markdowns[-1]
    assert "## 优先级看板" in partial_markdowns[-1]
    assert partial_patches == []
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 需求评审报告")
    assert '"type": "priority-board"' in outputs[-1].artifact_update.markdown
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "issue_statistics" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "REQ_REVIEW",
        "REPORT",
    )


def test_runtime_raw_json_stream_turn_renders_value_elevator_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "已生成价值定位分析。",
            "artifact_data": VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "PERSONA",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []
    chunks = _raw_json_chunks_after_artifact_data_members(
        final_json,
        [
            "positioning_summary",
            "value_flow",
            "target_scenarios",
            "score_summary",
        ],
    )

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是需求蓝图梳理顾问。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请梳理 AI 测试设计助手的价值定位",
            workflow_id="VALUE_DISCOVERY",
            current_stage_id="ELEVATOR",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 价值定位分析")
    assert "## 定位摘要" in partial_markdowns[0]
    assert "## 价值结构图" in partial_markdowns[-1]
    assert "flowchart TD" in partial_markdowns[-1]
    assert "## 目标用户与场景" in partial_markdowns[-1]
    assert "## 痛点证据" in partial_markdowns[-1]
    assert "## 价值主张评分" in partial_markdowns[-1]
    assert '"type": "score-matrix"' in partial_markdowns[-1]

    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 价值定位分析")
    assert "flowchart TD" in outputs[-1].artifact_update.markdown
    assert '"type": "score-matrix"' in outputs[-1].artifact_update.markdown
    assert outputs[-1].stage_action is not None
    assert outputs[-1].stage_action.target_stage_id == "PERSONA"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "value_flow" in calls[0]["messages"][0]["content"]
    assert "score_matrix" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "VALUE_DISCOVERY",
        "ELEVATOR",
    )


def test_runtime_raw_json_stream_turn_renders_value_persona_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "已生成用户画像分析。",
            "artifact_data": VALID_VALUE_PERSONA_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "JOURNEY",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []
    chunks = _raw_json_chunks_after_artifact_data_members(
        final_json,
        [
            "persona_summary",
            "personas",
            "behavior_scenarios",
            "decision_chain",
        ],
    )

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是需求蓝图梳理顾问。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请基于价值定位继续构建用户画像",
            workflow_id="VALUE_DISCOVERY",
            current_stage_id="PERSONA",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 用户画像分析")
    assert "## 画像摘要" in partial_markdowns[0]
    assert "## 主要用户画像" in partial_markdowns[-1]
    assert "### 画像 1" in partial_markdowns[-1]
    assert "## 行为与场景" in partial_markdowns[-1]
    assert "## 决策链" in partial_markdowns[-1]

    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 用户画像分析")
    assert "## 决策链" in outputs[-1].artifact_update.markdown
    assert "## 用户优先级排序" in outputs[-1].artifact_update.markdown
    assert outputs[-1].stage_action is not None
    assert outputs[-1].stage_action.target_stage_id == "JOURNEY"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "personas" in calls[0]["messages"][0]["content"]
    assert "decision_chain" in calls[0]["messages"][0]["content"]
    assert "priority_ranking" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "VALUE_DISCOVERY",
        "PERSONA",
    )


def test_runtime_raw_json_stream_turn_renders_value_journey_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "已生成用户旅程分析。",
            "artifact_data": VALID_VALUE_JOURNEY_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "BLUEPRINT",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []
    chunks = _raw_json_chunks_after_artifact_data_members(
        final_json,
        [
            "journey_stages",
            "pain_priorities",
            "opportunity_scores",
        ],
    )

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是需求蓝图梳理顾问。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请基于用户画像继续生成用户旅程",
            workflow_id="VALUE_DISCOVERY",
            current_stage_id="JOURNEY",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 用户旅程分析")
    assert "## 旅程摘要" in partial_markdowns[0]
    assert "## 用户旅程地图" in partial_markdowns[-1]
    assert "journey\n    title 核心用户旅程" in partial_markdowns[-1]
    assert '"type": "journey-map"' in partial_markdowns[-1]
    assert "## 痛点优先级排序" in partial_markdowns[-1]
    assert "## 机会评分" in partial_markdowns[-1]

    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 用户旅程分析")
    assert "journey\n    title 核心用户旅程" in outputs[-1].artifact_update.markdown
    assert '"type": "journey-map"' in outputs[-1].artifact_update.markdown
    assert outputs[-1].stage_action is not None
    assert outputs[-1].stage_action.target_stage_id == "BLUEPRINT"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "journey_stages" in calls[0]["messages"][0]["content"]
    assert "journey-map" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "VALUE_DISCOVERY",
        "JOURNEY",
    )


def test_runtime_raw_json_stream_turn_renders_value_blueprint_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "已生成需求蓝图。",
            "artifact_data": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []
    chunks = _raw_json_chunks_after_artifact_data_members(
        final_json,
        [
            "product_overview",
            "target_users",
            "requirements",
            "main_flow",
            "roadmap",
            "lisa_handoff_inputs",
        ],
    )

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是需求蓝图梳理顾问。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请整合需求蓝图梳理前序成果生成需求蓝图",
            workflow_id="VALUE_DISCOVERY",
            current_stage_id="BLUEPRINT",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# AI4SE 测试设计助手 需求蓝图")
    assert "## 1. 产品概述" in partial_markdowns[0]
    assert "## 2. 目标用户（摘要）" in partial_markdowns[-1]
    assert "## 3. 核心需求" in partial_markdowns[-1]
    assert "mindmap" in partial_markdowns[-1]
    assert "## 4. 核心流程" in partial_markdowns[-1]
    assert "flowchart TD" in partial_markdowns[-1]
    assert '"type": "roadmap"' in partial_markdowns[-1]
    assert "## 11. Lisa Handoff 输入" in partial_markdowns[-1]

    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith(
        "# AI4SE 测试设计助手 需求蓝图"
    )
    assert "mindmap" in outputs[-1].artifact_update.markdown
    assert "flowchart TD" in outputs[-1].artifact_update.markdown
    assert '"type": "roadmap"' in outputs[-1].artifact_update.markdown
    assert outputs[-1].stage_action is None
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "product_overview" in calls[0]["messages"][0]["content"]
    assert "lisa_handoff_inputs" in calls[0]["messages"][0]["content"]
    assert "roadmap" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "VALUE_DISCOVERY",
        "BLUEPRINT",
    )


def test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "已还原故障事件时间线。",
            "artifact_data": VALID_INCIDENT_TIMELINE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "ROOT_CAUSE",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    summary_prefix = prefix_after_artifact_data_member("incident_summary")
    facts_prefix = prefix_after_artifact_data_member("fact_sources")
    timeline_prefix = prefix_after_artifact_data_member("timeline_events")
    chunks = [
        summary_prefix,
        facts_prefix[len(summary_prefix) :],
        timeline_prefix[len(facts_prefix) :],
        final_json[len(timeline_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是故障复盘专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "昨天支付回调失败影响 20 分钟，请做事件还原",
            workflow_id="INCIDENT_REVIEW",
            current_stage_id="TIMELINE",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 故障复盘报告")
    assert "## 1. 事件概要" in partial_markdowns[0]
    assert "## 2. 影响量化" in partial_markdowns[-1]
    assert "## 3. 事实来源" in partial_markdowns[-1]
    assert "## 4. 事件时间线" in partial_markdowns[-1]
    assert "```mermaid" not in partial_markdowns[-1]
    assert '"type": "timeline-map"' in partial_markdowns[-1]

    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 故障复盘报告")
    assert "```mermaid" not in outputs[-1].artifact_update.markdown
    assert '"type": "timeline-map"' in outputs[-1].artifact_update.markdown
    assert "14:30 | 订单状态延迟告警触发" in outputs[-1].artifact_update.markdown
    assert outputs[-1].stage_action is not None
    assert outputs[-1].stage_action.target_stage_id == "ROOT_CAUSE"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "incident_summary" in calls[0]["messages"][0]["content"]
    assert "timeline_events" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "INCIDENT_REVIEW",
        "TIMELINE",
    )


def test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "已完成根因分析。",
            "artifact_data": VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "IMPROVEMENT",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    context_prefix = prefix_after_artifact_data_member("analysis_context")
    why_prefix = prefix_after_artifact_data_member("why_chain")
    fishbone_prefix = prefix_after_artifact_data_member("fishbone_categories")
    chunks = [
        context_prefix,
        why_prefix[len(context_prefix) :],
        fishbone_prefix[len(why_prefix) :],
        final_json[len(fishbone_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是故障复盘专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "基于支付回调失败事件，请继续做根因分析",
            workflow_id="INCIDENT_REVIEW",
            current_stage_id="ROOT_CAUSE",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 故障复盘报告")
    assert "## 6. 根因分析" in partial_markdowns[0]
    assert "### 6.1 5-Why 分析链" in partial_markdowns[-1]
    assert '"type": "cause-map"' in partial_markdowns[-1]
    assert "### 6.3 原因鱼骨图" in partial_markdowns[-1]
    assert "mindmap" in partial_markdowns[-1]

    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 故障复盘报告")
    assert "### 6.1 5-Why 分析链" in outputs[-1].artifact_update.markdown
    assert "mindmap" in outputs[-1].artifact_update.markdown
    assert '"type": "cause-map"' in outputs[-1].artifact_update.markdown
    assert outputs[-1].stage_action is not None
    assert outputs[-1].stage_action.target_stage_id == "IMPROVEMENT"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "why_chain" in calls[0]["messages"][0]["content"]
    assert "cause_evidence" in calls[0]["messages"][0]["content"]
    assert "root_cause_conclusions" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "INCIDENT_REVIEW",
        "ROOT_CAUSE",
    )


def test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "已完成故障改进报告。",
            "artifact_data": VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    report_prefix = prefix_after_artifact_data_member("report_info")
    root_cause_prefix = prefix_after_artifact_data_member("root_cause_summary")
    actions_prefix = prefix_after_artifact_data_member("improvement_actions")
    chunks = [
        report_prefix,
        root_cause_prefix[len(report_prefix) :],
        actions_prefix[len(root_cause_prefix) :],
        final_json[len(actions_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是故障复盘专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "基于支付回调失败根因，请生成改进措施和复查计划",
            workflow_id="INCIDENT_REVIEW",
            current_stage_id="IMPROVEMENT",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 故障复盘报告")
    assert "## 第一部分：事件还原" in partial_markdowns[0]
    assert "## 报告信息" in partial_markdowns[0]
    assert partial_markdowns[0].index("## 第一部分：事件还原") < partial_markdowns[
        0
    ].index("## 报告信息")
    assert "## 报告信息" in partial_markdowns[-1]
    assert "## 报告概览" in partial_markdowns[-1]
    assert "## 第一部分：事件还原" in partial_markdowns[-1]
    assert "## 第二部分：根因分析" in partial_markdowns[-1]
    assert "## 第三部分：改进措施" in partial_markdowns[-1]
    assert "pie title 改进措施优先级分布" in partial_markdowns[-1]
    assert '"type": "action-board"' in partial_markdowns[-1]

    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 故障复盘报告")
    assert "### 7. 改进措施" in outputs[-1].artifact_update.markdown
    assert "pie title 改进措施优先级分布" in outputs[-1].artifact_update.markdown
    assert '"type": "action-board"' in outputs[-1].artifact_update.markdown
    assert outputs[-1].stage_action is None
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "improvement_actions" in calls[0]["messages"][0]["content"]
    assert "root_cause_coverage" in calls[0]["messages"][0]["content"]
    assert "residual_risks" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "INCIDENT_REVIEW",
        "IMPROVEMENT",
    )


def test_runtime_raw_json_stream_turn_renders_idea_define_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "已形成问题域验证基线。",
            "artifact_data": VALID_IDEA_DEFINE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "DIVERGE",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    statement_prefix = prefix_after_artifact_data_member("problem_statement")
    users_prefix = prefix_after_artifact_data_member("target_users")
    landscape_prefix = prefix_after_artifact_data_member("problem_landscape")
    chunks = [
        statement_prefix,
        users_prefix[len(statement_prefix) :],
        landscape_prefix[len(users_prefix) :],
        final_json[len(landscape_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是创新顾问。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "我想帮独立开发者解决变现难题，请先分析问题域",
            workflow_id="IDEA_BRAINSTORM",
            current_stage_id="DEFINE",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 问题域分析")
    assert "## 问题假设陈述" in partial_markdowns[0]
    assert "## 目标用户画像" in partial_markdowns[-1]
    assert "## 问题域全景" in partial_markdowns[-1]
    assert "mindmap" in partial_markdowns[-1]

    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 问题域分析")
    assert "## 问题域全景" in outputs[-1].artifact_update.markdown
    assert "mindmap" in outputs[-1].artifact_update.markdown
    assert "证据等级" in outputs[-1].artifact_update.markdown
    assert outputs[-1].stage_action is not None
    assert outputs[-1].stage_action.target_stage_id == "DIVERGE"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "problem_statement" in calls[0]["messages"][0]["content"]
    assert "evidence_items" in calls[0]["messages"][0]["content"]
    assert "problem_user_fit" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "DEFINE",
    )


def test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "已形成创意发散候选集。",
            "artifact_data": VALID_IDEA_DIVERGE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CONVERGE",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    method_prefix = prefix_after_artifact_data_member("divergence_method")
    cards_prefix = prefix_after_artifact_data_member("idea_cards")
    sources_prefix = prefix_after_artifact_data_member("idea_sources")
    chunks = [
        method_prefix,
        cards_prefix[len(method_prefix) :],
        sources_prefix[len(cards_prefix) :],
        final_json[len(sources_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是创新顾问。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请基于问题域发散多个产品创意",
            workflow_id="IDEA_BRAINSTORM",
            current_stage_id="DIVERGE",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 创意发散")
    assert "## 发散方法说明" in partial_markdowns[0]
    assert "## 发散全景图" in partial_markdowns[-1]
    assert "mindmap" in partial_markdowns[-1]
    assert "## 创意卡片库" in partial_markdowns[-1]
    assert "## 创意来源与假设" in partial_markdowns[-1]

    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 创意发散")
    assert "## 发散全景图" in outputs[-1].artifact_update.markdown
    assert "mindmap" in outputs[-1].artifact_update.markdown
    assert "## 创意卡片库" in outputs[-1].artifact_update.markdown
    assert "关键假设" in outputs[-1].artifact_update.markdown
    assert "状态理由" in outputs[-1].artifact_update.markdown
    assert outputs[-1].stage_action is not None
    assert outputs[-1].stage_action.target_stage_id == "CONVERGE"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "divergence_method" in calls[0]["messages"][0]["content"]
    assert "idea_cards" in calls[0]["messages"][0]["content"]
    assert "idea_sources" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "DIVERGE",
    )


def test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "已完成创意收敛评估。",
            "artifact_data": VALID_IDEA_CONVERGE_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CONCEPT",
            },
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    evaluations_prefix = prefix_after_artifact_data_member("ice_evaluations")
    resources_prefix = prefix_after_artifact_data_member("resource_constraints")
    experiments_prefix = prefix_after_artifact_data_member("validation_experiments")
    chunks = [
        evaluations_prefix,
        resources_prefix[len(evaluations_prefix) :],
        experiments_prefix[len(resources_prefix) :],
        final_json[len(experiments_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是创新顾问。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请对这些创意做 ICE 收敛评估",
            workflow_id="IDEA_BRAINSTORM",
            current_stage_id="CONVERGE",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 收敛聚焦")
    assert "## 决策矩阵" in partial_markdowns[0]
    assert "## ICE 评估表" in partial_markdowns[0]
    assert "## 资源约束" not in partial_markdowns[0]
    assert "## 决策矩阵" in partial_markdowns[-1]
    assert "quadrantChart" in partial_markdowns[-1]
    assert "## ICE 评估表" in partial_markdowns[-1]
    assert "## 资源约束" in partial_markdowns[-1]
    assert "## 验证实验" in partial_markdowns[-1]

    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 收敛聚焦")
    assert "## 决策矩阵" in outputs[-1].artifact_update.markdown
    assert "quadrantChart" in outputs[-1].artifact_update.markdown
    assert "## ICE 评估表" in outputs[-1].artifact_update.markdown
    assert "推荐方案" in outputs[-1].artifact_update.markdown
    assert "用户确认状态" in outputs[-1].artifact_update.markdown
    assert outputs[-1].stage_action is not None
    assert outputs[-1].stage_action.target_stage_id == "CONCEPT"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "decision_matrix" in calls[0]["messages"][0]["content"]
    assert "ice_evaluations" in calls[0]["messages"][0]["content"]
    assert "validation_experiments" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "CONVERGE",
    )


def test_runtime_raw_json_stream_turn_renders_idea_concept_artifact_data_before_final_output(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "已完成产品概念简报。",
            "artifact_data": VALID_IDEA_CONCEPT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    positioning_prefix = prefix_after_artifact_data_member("positioning_statement")
    assumptions_prefix = prefix_after_artifact_data_member("core_assumptions")
    mvp_prefix = prefix_after_artifact_data_member("mvp_features")
    chunks = [
        positioning_prefix,
        assumptions_prefix[len(positioning_prefix) :],
        mvp_prefix[len(assumptions_prefix) :],
        final_json[len(mvp_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是创新顾问。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请把收敛后的创意整理成产品概念简报",
            workflow_id="IDEA_BRAINSTORM",
            current_stage_id="CONCEPT",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 产品概念简报")
    assert "## 定位声明" in partial_markdowns[0]
    assert "## 核心假设" in partial_markdowns[-1]
    assert "## Lean Canvas 产品画布" in partial_markdowns[-1]
    assert "## MVP 功能分布" in partial_markdowns[-1]
    assert "pie title MVP 功能组成" in partial_markdowns[-1]
    assert '"type": "mvp-map"' in partial_markdowns[-1]

    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    assert outputs[-1].artifact_update.markdown.startswith("# 产品概念简报")
    assert "## 定位声明" in outputs[-1].artifact_update.markdown
    assert "## Lean Canvas 产品画布" in outputs[-1].artifact_update.markdown
    assert "pie title MVP 功能组成" in outputs[-1].artifact_update.markdown
    assert "flowchart TD" in outputs[-1].artifact_update.markdown
    assert '"type": "mvp-map"' in outputs[-1].artifact_update.markdown
    assert "## 下一步行动" in outputs[-1].artifact_update.markdown
    assert outputs[-1].stage_action is None
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "positioning_statement" in calls[0]["messages"][0]["content"]
    assert "mvp_features" in calls[0]["messages"][0]["content"]
    assert "growth_funnel" in calls[0]["messages"][0]["content"]
    assert "validation_roadmap" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "CONCEPT",
    )


@pytest.mark.parametrize(
    (
        "stage_id",
        "member_names",
        "expected_markers",
        "stage_action",
    ),
    [
        (
            "INPUT_ANALYSIS",
            ["input_analysis", "epics"],
            [
                "# 用户故事拆解包",
                "## 输入分析",
                "## Epic Map",
                '"type": "flow-map"',
                '"nodes"',
                '"edges"',
            ],
            {"type": "request_next_stage", "target_stage_id": "EPIC_MAPPING"},
        ),
        (
            "EPIC_MAPPING",
            ["epics", "user_stories"],
            [
                "## Epic Map",
                '"type": "flow-map"',
                "EPIC-001",
                "## User Story Backlog",
            ],
            {"type": "request_next_stage", "target_stage_id": "STORY_BACKLOG"},
        ),
        (
            "STORY_BACKLOG",
            ["user_stories", "acceptance_criteria"],
            [
                "## User Story Backlog",
                '"type": "flow-map"',
                "US-001",
                "## 验收标准",
            ],
            {"type": "request_next_stage", "target_stage_id": "SPRINT_PLAN"},
        ),
        (
            "SPRINT_PLAN",
            ["sprint_slices", "lisa_handoff_inputs"],
            [
                "## Sprint 切片建议",
                '"type": "flow-map"',
                '"type": "story-map"',
                "## Lisa Handoff 输入",
                "US-001",
            ],
            None,
        ),
    ],
)
def test_runtime_raw_json_stream_turn_renders_all_story_breakdown_stages_from_artifact_data(
    monkeypatch,
    stage_id,
    member_names,
    expected_markers,
    stage_action,
):
    final_json = json.dumps(
        {
            "chat": "我已完成用户故事拆解产物，请查看右侧文档。",
            "artifact_data": ARTIFACT_DATA_STAGE_FIXTURES[
                ("STORY_BREAKDOWN", stage_id)
            ],
            "stage_action": stage_action,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    chunks = _raw_json_chunks_after_artifact_data_members(final_json, member_names)
    calls = []

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是 Alex 用户故事拆解顾问。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请把需求蓝图拆成用户故事",
            workflow_id="STORY_BREAKDOWN",
            current_stage_id=stage_id,
        )
    )

    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_update.markdown is not None
    for marker in expected_markers:
        assert marker in outputs[-1].artifact_update.markdown
    assert "flowchart TD" not in outputs[-1].artifact_update.markdown
    if stage_action is None:
        assert outputs[-1].stage_action is None
    else:
        assert outputs[-1].stage_action is not None
        assert (
            outputs[-1].stage_action.target_stage_id == stage_action["target_stage_id"]
        )
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    for member_name in member_names:
        assert member_name in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in build_structured_output_instruction(
        "STORY_BREAKDOWN",
        stage_id,
    )


def test_raw_streaming_runtime_records_stream_usage(monkeypatch):
    final_json = (
        '{"chat":"正在梳理需求。",'
        '"artifact_update":{"type":"replace","markdown":"'
        f"{VALID_CLARIFY_ARTIFACT_JSON}" + '"},'
        '"stage_action":null,"warnings":[]}'
    )

    def fake_stream_chat_completion_content(**kwargs):
        kwargs["on_usage"](123)
        yield final_json

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            system_prompt="system prompt",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    assert outputs[-1].chat == "正在梳理需求。"
    assert runtime.last_token_usage == 123


def test_raw_streaming_runtime_accumulates_usage_across_retry_attempts(monkeypatch):
    final_json = (
        '{"chat":"正在梳理需求。",'
        '"artifact_update":{"type":"replace","markdown":"'
        f"{VALID_CLARIFY_ARTIFACT_JSON}" + '"},'
        '"stage_action":null,"warnings":[]}'
    )
    attempts = iter(((40, "{}"), (60, final_json)))

    def fake_stream_chat_completion_content(**kwargs):
        token_count, content = next(attempts)
        kwargs["on_usage"](token_count)
        yield content

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            system_prompt="system prompt",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    assert outputs[-1].chat == "正在梳理需求。"
    assert runtime.last_token_usage == 100


def test_runtime_raw_json_stream_turn_fails_final_json_truncation_after_partial_delta(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "已更新需求文档。",
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    chunks = _raw_json_chunks_after_artifact_data_members(
        final_json,
        ["document_info", "requirement_facts"],
    )[:2]

    call_count = 0

    def fake_stream_chat_completion_content(**kwargs):
        nonlocal call_count
        call_count += 1
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            system_prompt="system prompt",
        ),
    )

    stream = runtime.stream_turn(
        "用户需求",
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    emitted_deltas: list[AgentTurnDeltaOutput] = []
    retry_signals: list[AgentRetrySignal] = []
    with pytest.raises(AgentRuntimeSchemaError) as captured:
        for output in stream:
            if isinstance(output, AgentRetrySignal):
                retry_signals.append(output)
            else:
                assert isinstance(output, AgentTurnDeltaOutput)
                emitted_deltas.append(output)

    assert call_count == 2
    assert [signal.attempt_index for signal in retry_signals] == [2]
    assert isinstance(captured.value.__cause__, json.JSONDecodeError)
    artifact_deltas = [
        output for output in emitted_deltas if output.artifact_update is not None
    ]
    assert artifact_deltas
    first_markdown = artifact_deltas[0].artifact_update.markdown
    assert first_markdown is not None
    assert first_markdown.startswith("# 需求分析文档")
    assert not any("artifact_truncated" in output.warnings for output in emitted_deltas)


def test_runtime_raw_json_stream_turn_retries_json_decode_and_recovers(
    monkeypatch,
):
    canary = "first-attempt-output-canary"
    valid_json = json.dumps(
        {
            "chat": "已完成需求澄清并更新右侧文档，请确认关键假设。",
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    invalid_json = valid_json.replace(
        "已完成需求澄清并更新右侧文档，请确认关键假设。",
        canary,
    )[:-8]
    attempts = iter((invalid_json, valid_json))
    calls = []

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield next(attempts)

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            system_prompt="system prompt",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    retry_signals = [
        output for output in outputs if isinstance(output, AgentRetrySignal)
    ]
    assert len(calls) == 2
    assert [signal.attempt_index for signal in retry_signals] == [2]
    retry_prompt = calls[1]["messages"][1]["content"]
    assert "完整合法的 JSON" in retry_prompt
    assert canary not in retry_prompt
    assert isinstance(outputs[-1], AgentTurnOutput)


def test_runtime_raw_json_stream_turn_replaces_model_document_identity_without_retry(
    monkeypatch,
):
    invalid_artifact_data = copy.deepcopy(VALID_CLARIFY_ARTIFACT_DATA)
    invalid_artifact_data["document_info"]["workflow"] = "renderer-canary"
    invalid_json = json.dumps(
        {
            "chat": "已完成需求澄清并更新右侧文档，请确认关键假设。",
            "artifact_data": invalid_artifact_data,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield invalid_json

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            system_prompt="system prompt",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    assert len(calls) == 1
    assert not any(isinstance(output, AgentRetrySignal) for output in outputs)
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_data is not None
    assert outputs[-1].artifact_data["document_info"]["workflow"] == "TEST_DESIGN"
    assert outputs[-1].artifact_data["document_info"]["stage"] == "CLARIFY"


def test_runtime_raw_json_stream_turn_retries_length_termination_and_recovers(
    monkeypatch,
):
    canary = "first-truncated-output-canary"
    valid_json = json.dumps(
        {
            "chat": "已完成需求澄清并更新右侧文档，请确认关键假设。",
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    attempts = iter(((valid_json[:120] + canary, "length"), (valid_json, "stop")))
    calls = []

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        payload, reason = next(attempts)
        kwargs["on_finish_reason"](reason)
        yield payload

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="deepseek-v4-flash",
            system_prompt="system prompt",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    assert [
        output.attempt_index
        for output in outputs
        if isinstance(output, AgentRetrySignal)
    ] == [2]
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert calls[0]["max_tokens"] == 32768
    retry_prompt = calls[1]["messages"][1]["content"]
    assert "validator=output_truncated" in retry_prompt
    assert canary not in retry_prompt


def test_runtime_raw_json_stream_turn_reports_repeated_length_termination(
    monkeypatch,
):
    def fake_stream_chat_completion_content(**kwargs):
        kwargs["on_finish_reason"]("length")
        yield '{"chat":"partial'

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="deepseek-v4-flash",
            system_prompt="system prompt",
        ),
    )

    with pytest.raises(AgentRuntimeSchemaError) as captured:
        list(
            runtime.stream_turn(
                "用户需求",
                workflow_id="TEST_DESIGN",
                current_stage_id="CLARIFY",
            )
        )

    assert isinstance(captured.value.__cause__, RawJsonStreamTerminationError)
    assert captured.value.__cause__.reason == "length"


def test_runtime_raw_json_stream_turn_rejects_missing_finish_reason(
    monkeypatch,
):
    valid_json = json.dumps(
        {
            "chat": "已完成需求澄清并更新右侧文档，请确认关键假设。",
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    def fake_stream_chat_completion_content(**kwargs):
        yield valid_json

    _install_raw_stream_fake(
        monkeypatch,
        fake_stream_chat_completion_content,
        default_finish_reason=None,
    )
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            system_prompt="system prompt",
        ),
    )
    outputs = []

    with pytest.raises(AgentRuntimeSchemaError) as captured:
        for output in runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        ):
            outputs.append(output)

    assert isinstance(captured.value.__cause__, RawJsonStreamTerminationError)
    assert captured.value.__cause__.reason == "unknown"
    assert not any(isinstance(output, AgentTurnOutput) for output in outputs)


def test_runtime_raw_json_stream_turn_streams_artifact_progress_for_artifact_data(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "我正在逐步核对需求事实与边界，右侧会持续补充分析。",
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    chunks = [
        final_json[: final_json.index('"artifact_data"')],
        final_json[
            final_json.index('"artifact_data"') : final_json.index('"stage_action"')
        ],
        final_json[final_json.index('"stage_action"') :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        yield from chunks

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            system_prompt="system prompt",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    progress_deltas = [
        output
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
    ]

    assert progress_deltas
    progress_markdown = progress_deltas[0].artifact_update.markdown
    assert progress_markdown.startswith("# 需求分析文档")
    assert "## 文档信息" in progress_markdown
    assert (
        "| F-001 | 用户需要登录功能 | 用户描述 | 用户陈述 | 已确认 |"
        in progress_markdown
    )
    assert (
        "| 测试范围 | 登录页面和登录 API | 验证登录主链路 | 已确认 |"
        in progress_markdown
    )
    assert "```mermaid" in progress_markdown
    assert "# 产出物生成中" not in progress_markdown
    assert outputs[-1].artifact_update.markdown.startswith("# 需求分析文档")


def test_runtime_raw_json_stream_turn_streams_partial_artifact_data_in_final_format():
    final_json = json.dumps(
        {
            "chat": "我正在逐步核对需求事实与边界，右侧会持续补充分析。",
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    artifact_start = final_json.index('"artifact_data"')
    business_rules_start = final_json.index(',"business_rules"')
    partial_text = final_json[:business_rules_start]

    progress_markdown = build_artifact_data_progress_markdown(
        partial_text,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert progress_markdown is not None
    assert progress_markdown.startswith("# 需求分析文档")
    assert "## 文档信息" in progress_markdown
    assert (
        "| F-001 | 用户需要登录功能 | 用户描述 | 用户陈述 | 已确认 |"
        in progress_markdown
    )
    assert (
        "| 测试范围 | 登录页面和登录 API | 验证登录主链路 | 已确认 |"
        in progress_markdown
    )
    assert "## 3. 业务规则与数据状态" not in progress_markdown
    assert "# 产出物生成中" not in progress_markdown
    assert "已接收字符数" not in progress_markdown


def test_runtime_raw_json_stream_turn_retries_contract_failure_with_feedback(
    monkeypatch,
):
    invalid_json = (
        '{"chat":"我会先给出ICE评估建议。",'
        '"artifact_update":{"type":"none"},'
        '"stage_action":null,"warnings":[]}'
    )
    valid_json = (
        '{"chat":"已更新右侧需求分析文档。",'
        '"artifact_update":{"type":"replace","markdown":"'
        f"{VALID_CLARIFY_ARTIFACT_JSON}" + '"},'
        '"stage_action":null,"warnings":[]}'
    )
    calls = []

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield invalid_json if len(calls) == 1 else valid_json

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            system_prompt="system prompt",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    assert len(calls) == 2
    assert "上一轮结构化输出未通过校验" in calls[1]["messages"][1]["content"]
    assert "failureCategory=contract_validation" in calls[1]["messages"][1]["content"]
    assert "fieldPath=artifact_contract" in calls[1]["messages"][1]["content"]
    assert outputs[-1].chat == "已更新右侧需求分析文档。"
    assert outputs[-1].artifact_update.markdown == VALID_CLARIFY_ARTIFACT


def test_runtime_marks_retry_boundary_after_visible_partial_before_success(
    monkeypatch,
):
    invalid_artifact_data = copy.deepcopy(VALID_REQ_REVIEW_ARTIFACT_DATA)
    invalid_artifact_data["issue_statistics"]["p0_count"] = 99
    attempts = [
        json.dumps(
            {
                "chat": "我正在逐段形成需求评审结论，请查看右侧当前进度。",
                "artifact_data": invalid_artifact_data,
                "stage_action": None,
                "warnings": [],
            },
            ensure_ascii=False,
        ),
        json.dumps(
            {
                "chat": "我已修正需求评审统计并完成当前阶段产出物。",
                "artifact_data": VALID_REQ_REVIEW_ARTIFACT_DATA,
                "stage_action": None,
                "warnings": [],
            },
            ensure_ascii=False,
        ),
    ]
    calls = []

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield attempts[len(calls) - 1]

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            system_prompt="system prompt",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请评审会员权益需求",
            workflow_id="REQ_REVIEW",
            current_stage_id="REVIEW",
        )
    )

    retry_indexes = [
        index
        for index, output in enumerate(outputs)
        if getattr(output, "attempt_index", None) == 2
    ]
    artifact_delta_indexes = [
        index
        for index, output in enumerate(outputs)
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
    ]

    assert len(calls) == 2
    assert retry_indexes
    assert artifact_delta_indexes[0] < retry_indexes[0] < artifact_delta_indexes[-1]
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_data == VALID_REQ_REVIEW_ARTIFACT_DATA


def test_runtime_raw_json_stream_turn_retries_schema_shape_failure_with_feedback(
    monkeypatch,
):
    invalid_json = '{"chat":"已完成分析。","stage_action":null,"warnings":[]}'
    valid_json = (
        '{"chat":"已更新右侧需求分析文档。",'
        '"artifact_update":{"type":"replace","markdown":"'
        f"{VALID_CLARIFY_ARTIFACT_JSON}" + '"},'
        '"stage_action":null,"warnings":[]}'
    )
    calls = []

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield invalid_json if len(calls) == 1 else valid_json

    _install_raw_stream_fake(monkeypatch, fake_stream_chat_completion_content)
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            system_prompt="system prompt",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    assert len(calls) == 2
    assert "上一轮结构化输出未通过校验" in calls[1]["messages"][1]["content"]
    assert "artifact_update" in calls[1]["messages"][1]["content"]
    assert outputs[-1].chat == "已更新右侧需求分析文档。"
    assert outputs[-1].artifact_update.markdown == VALID_CLARIFY_ARTIFACT


def test_raw_json_retry_prompt_redacts_validation_error_model_data():
    canary = "model-input-canary"

    class StrictPayload(BaseModel):
        model_config = ConfigDict(extra="forbid")

        allowed: str

    with pytest.raises(ValidationError) as captured:
        StrictPayload.model_validate(
            {
                "allowed": "ok",
                "target_stage_id": canary,
                "model_field_canary": canary,
            }
        )

    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        captured.value,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert "failureCategory=schema_validation" in retry_prompt
    assert "fieldPath=structured_output" in retry_prompt
    assert "validator=extra_forbidden" in retry_prompt
    assert canary not in retry_prompt
    assert "target_stage_id" not in retry_prompt
    assert "model_field_canary" not in retry_prompt
    assert "input_value" not in retry_prompt


def test_raw_json_retry_prompt_projects_terminal_stage_action_missing_type():
    with pytest.raises(ValidationError) as captured:
        AgentTurnOutput.model_validate(
            {
                "chat": "我已完成需求评审报告并整理右侧产出物，请查看最终结论。",
                "artifact_update": {"type": "none", "markdown": None},
                "stage_action": {"target_stage_id": "REPORT"},
                "warnings": [],
            }
        )

    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        captured.value,
        workflow_id="REQ_REVIEW",
        current_stage_id="REPORT",
    )

    assert "failureCategory=schema_validation" in retry_prompt
    assert "fieldPath=stage_action.type" in retry_prompt
    assert "validator=missing" in retry_prompt
    assert "当前阶段是最后阶段，stage_action 必须为 null" in retry_prompt
    assert "artifact_data 数据问题" not in retry_prompt


def test_raw_json_retry_prompt_projects_non_terminal_stage_action_missing_type():
    with pytest.raises(ValidationError) as captured:
        AgentTurnOutput.model_validate(
            {
                "chat": "我已完成当前阶段分析并整理右侧产出物，请确认下一步。",
                "artifact_update": {"type": "none", "markdown": None},
                "stage_action": {"target_stage_id": "REPORT"},
                "warnings": [],
            }
        )

    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        captured.value,
        workflow_id="REQ_REVIEW",
        current_stage_id="REVIEW",
    )

    assert "fieldPath=stage_action.type" in retry_prompt
    assert '唯一合法值是 {"type": "request_next_stage"' in retry_prompt
    assert '"target_stage_id": "REPORT"}' in retry_prompt
    assert "artifact_data 数据问题" not in retry_prompt


def test_raw_json_retry_prompt_projects_journey_duplicate_id_to_fixed_feedback():
    canary = "sk-journey-duplicate-canary"
    invalid = copy.deepcopy(VALID_VALUE_JOURNEY_ARTIFACT_DATA)
    invalid["journey_stages"][0]["key_pain"] = canary
    invalid["journey_stages"][1]["pain_id"] = invalid["journey_stages"][0]["pain_id"]

    with pytest.raises(ValidationError) as captured:
        ValueDiscoveryJourneyArtifactData.model_validate(invalid)

    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        captured.value,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="JOURNEY",
    )

    assert "validator=journey_duplicate_pain_id" in retry_prompt
    assert "journey_stages 每一项的 pain_id 必须唯一" in retry_prompt
    assert canary not in retry_prompt


def test_raw_json_retry_prompt_projects_blank_string_to_fixed_feedback():
    invalid = copy.deepcopy(VALID_IDEA_CONVERGE_ARTIFACT_DATA)
    invalid["ice_evaluations"][0]["elimination_reason"] = ""

    with pytest.raises(ValidationError) as captured:
        IdeaConvergeArtifactData.model_validate(invalid)

    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        captured.value,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONVERGE",
    )

    assert "validator=idea_converge_blank_elimination_reason" in retry_prompt
    assert "elimination_reason" in retry_prompt
    assert "不淘汰" in retry_prompt


def test_raw_json_retry_prompt_explains_nested_non_empty_reference_arrays():
    invalid = copy.deepcopy(VALID_IDEA_DEFINE_ARTIFACT_DATA)
    invalid["problem_user_fit"][0]["evidence_ids"] = []

    with pytest.raises(ValidationError) as captured:
        IdeaDefineArtifactData.model_validate(invalid)

    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        captured.value,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DEFINE",
    )

    assert "validator=idea_define_empty_evidence_ids" in retry_prompt
    assert "problem_user_fit[].evidence_ids" in retry_prompt
    assert "evidence_items[].evidence_id" in retry_prompt


def test_raw_json_retry_prompt_projects_blank_incident_risk_acceptor():
    invalid = copy.deepcopy(VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA)
    invalid["root_cause_coverage"][0]["risk_acceptor"] = ""

    with pytest.raises(ValidationError) as captured:
        IncidentImprovementArtifactData.model_validate(invalid)

    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        captured.value,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="IMPROVEMENT",
    )

    assert "validator=incident_improvement_blank_risk_acceptor" in retry_prompt
    assert "risk_acceptor" in retry_prompt
    assert "不适用" in retry_prompt


@pytest.mark.parametrize(
    (
        "failure",
        "expected_validator",
        "expected_field_path",
        "expected_feedback",
    ),
    [
        (
            "duplicate_action",
            "incident_improvement_duplicate_action_id",
            "artifact_data.improvement_actions[].action_id",
            "improvement_actions[].action_id 必须唯一",
        ),
        (
            "action_count",
            "incident_improvement_action_count_mismatch",
            "artifact_data.report_info.action_count",
            "不要输出 report_info.action_count",
        ),
        (
            "priority_distribution",
            "incident_improvement_priority_distribution_mismatch",
            "artifact_data.priority_distribution",
            "不要输出 priority_distribution",
        ),
        (
            "duplicate_cause",
            "incident_improvement_duplicate_cause_id",
            "artifact_data.root_cause_coverage[].cause_id",
            "root_cause_coverage[].cause_id 必须唯一",
        ),
        (
            "unknown_action",
            "incident_improvement_unknown_action_reference",
            "artifact_data.root_cause_coverage[].action_ids",
            "只能引用 improvement_actions[].action_id",
        ),
        (
            "unknown_cause",
            "incident_improvement_unknown_cause_reference",
            "artifact_data.improvement_actions[].root_cause_id",
            "只能引用 root_cause_coverage[].cause_id",
        ),
        (
            "covered_without_actions",
            "incident_improvement_covered_without_actions",
            "artifact_data.root_cause_coverage[].action_ids",
            "coverage_status 为“已覆盖”",
        ),
        (
            "action_group_mismatch",
            "incident_improvement_action_group_mismatch",
            "artifact_data.root_cause_coverage[].action_ids",
            "必须精确等于",
        ),
    ],
)
def test_raw_json_retry_prompt_projects_incident_improvement_consistency_failures(
    failure: str,
    expected_validator: str,
    expected_field_path: str,
    expected_feedback: str,
):
    invalid = copy.deepcopy(VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA)
    if failure == "duplicate_action":
        invalid["improvement_actions"][1]["action_id"] = invalid["improvement_actions"][
            0
        ]["action_id"]
    elif failure == "action_count":
        invalid["report_info"]["action_count"] = 99
    elif failure == "priority_distribution":
        invalid["priority_distribution"]["urgent_count"] = 99
    elif failure == "duplicate_cause":
        invalid["root_cause_coverage"][1]["cause_id"] = invalid["root_cause_coverage"][
            0
        ]["cause_id"]
    elif failure == "unknown_action":
        invalid["root_cause_coverage"][0]["action_ids"].append("A-404")
    elif failure == "unknown_cause":
        invalid["improvement_actions"][0]["root_cause_id"] = "CAUSE-404"
    elif failure == "covered_without_actions":
        invalid["root_cause_coverage"][0]["action_ids"] = []
    elif failure == "action_group_mismatch":
        invalid["root_cause_coverage"][0]["action_ids"] = ["A-001"]
    else:
        raise AssertionError(f"unknown test failure: {failure}")

    with pytest.raises(ValidationError) as captured:
        IncidentImprovementArtifactData.model_validate(invalid)

    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        captured.value,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="IMPROVEMENT",
    )

    assert f"validator={expected_validator}" in retry_prompt
    assert f"fieldPath={expected_field_path}" in retry_prompt
    assert expected_feedback in retry_prompt
    assert "A-404" not in retry_prompt
    assert "CAUSE-404" not in retry_prompt


@pytest.mark.parametrize(
    ("failure", "expected_validator", "expected_feedback"),
    [
        (
            "duplicate_evidence",
            "idea_define_duplicate_evidence_id",
            "evidence_items[].evidence_id 必须唯一",
        ),
        (
            "duplicate_problem",
            "idea_define_duplicate_problem_id",
            "problem_landscape.subproblems[].problem_id 必须唯一",
        ),
        (
            "unknown_evidence",
            "idea_define_unknown_evidence_reference",
            "只能引用 evidence_items[].evidence_id",
        ),
        (
            "duplicate_root_problem_id",
            "idea_define_duplicate_root_problem_id",
            "root_problem_id 不能与",
        ),
        (
            "unknown_problem_reference",
            "idea_define_unknown_problem_reference",
            "related_problem_ids 只能引用",
        ),
        (
            "missing_root_problem_evidence",
            "idea_define_missing_root_problem_evidence",
            "至少一个 evidence_items[].related_problem_ids 必须包含",
        ),
        (
            "missing_fit_root_evidence_reference",
            "idea_define_missing_fit_root_evidence_reference",
            "至少一个 problem_user_fit[].evidence_ids 必须引用",
        ),
        (
            "unchecked_stage_gate",
            "stage_gate_unchecked",
            "stage_gate 至少包含一个 checked=true",
        ),
    ],
)
def test_raw_json_retry_prompt_projects_idea_define_consistency_failures(
    failure: str,
    expected_validator: str,
    expected_feedback: str,
):
    invalid = copy.deepcopy(VALID_IDEA_DEFINE_ARTIFACT_DATA)
    if failure == "duplicate_evidence":
        invalid["evidence_items"][1]["evidence_id"] = invalid["evidence_items"][0][
            "evidence_id"
        ]
    elif failure == "duplicate_problem":
        duplicate = copy.deepcopy(invalid["problem_landscape"]["subproblems"][0])
        invalid["problem_landscape"]["subproblems"].append(duplicate)
    elif failure == "unknown_evidence":
        invalid["problem_user_fit"][0]["evidence_ids"] = ["EV-UNKNOWN"]
    elif failure == "duplicate_root_problem_id":
        invalid["problem_landscape"]["root_problem_id"] = invalid["problem_landscape"][
            "subproblems"
        ][0]["problem_id"]
    elif failure == "unknown_problem_reference":
        invalid["evidence_items"][0]["related_problem_ids"] = ["P-UNKNOWN"]
    elif failure == "missing_root_problem_evidence":
        invalid["evidence_items"][0]["related_problem_ids"] = ["P-001"]
    elif failure == "missing_fit_root_evidence_reference":
        for item in invalid["problem_user_fit"]:
            item["evidence_ids"] = ["EV-002"]
    elif failure == "unchecked_stage_gate":
        for item in invalid["stage_gate"]:
            item["checked"] = False
    else:
        raise AssertionError(f"unknown test failure: {failure}")

    with pytest.raises(ValidationError) as captured:
        IdeaDefineArtifactData.model_validate(invalid)

    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        captured.value,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DEFINE",
    )

    assert f"validator={expected_validator}" in retry_prompt
    assert expected_feedback in retry_prompt
    assert "EV-UNKNOWN" not in retry_prompt
    assert "P-UNKNOWN" not in retry_prompt


@pytest.mark.parametrize(
    (
        "collection",
        "field",
        "expected_validator",
        "expected_field_path",
        "expected_feedback",
    ),
    [
        (
            "mvp_features",
            "assumption_ids",
            "idea_concept_empty_mvp_feature_assumption_ids",
            "artifact_data.mvp_features[].assumption_ids",
            "每个 mvp_features[].assumption_ids 必须至少引用一个",
        ),
        (
            "validation_roadmap",
            "assumption_ids",
            "idea_concept_empty_validation_assumption_ids",
            "artifact_data.validation_roadmap[].assumption_ids",
            "每个 validation_roadmap[].assumption_ids 必须至少引用一个",
        ),
        (
            "next_actions",
            "related_ids",
            "idea_concept_empty_next_action_related_ids",
            "artifact_data.next_actions[].related_ids",
            "每个 next_actions[].related_ids 必须至少引用一个",
        ),
    ],
)
def test_raw_json_retry_prompt_projects_empty_idea_concept_reference_arrays(
    collection: str,
    field: str,
    expected_validator: str,
    expected_field_path: str,
    expected_feedback: str,
):
    invalid = copy.deepcopy(VALID_IDEA_CONCEPT_ARTIFACT_DATA)
    invalid[collection][0][field] = []

    with pytest.raises(ValidationError) as captured:
        IdeaConceptArtifactData.model_validate(invalid)

    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        captured.value,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONCEPT",
    )

    assert f"validator={expected_validator}" in retry_prompt
    assert f"fieldPath={expected_field_path}" in retry_prompt
    assert expected_feedback in retry_prompt


def test_raw_json_retry_prompt_projects_clarification_question_status_literal():
    invalid = copy.deepcopy(VALID_CLARIFY_ARTIFACT_DATA)
    invalid["clarification_questions"][0]["status"] = "需要澄清"

    with pytest.raises(ValidationError) as captured:
        ClarifyArtifactData.model_validate(invalid)

    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        captured.value,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert "validator=clarify_question_status_literal" in retry_prompt
    assert "fieldPath=artifact_data.clarification_questions[].status" in retry_prompt
    assert "只能从“待确认”“已确认”“已假设”“AI 假设”中选择一个" in retry_prompt
    assert "需要澄清" not in retry_prompt


def test_raw_json_retry_prompt_projects_stage_transition_contract_error_safely():
    canary = "contract-error-canary"
    error = ContractValidationError(f"invalid target stage: target_stage_id={canary}")

    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        error,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert "failureCategory=contract_validation" in retry_prompt
    assert "fieldPath=stage_action.target_stage_id" in retry_prompt
    assert "validator=stage_transition" in retry_prompt
    assert '唯一合法值是 {"type": "request_next_stage"' in retry_prompt
    assert '"target_stage_id": "STRATEGY"}' in retry_prompt
    assert canary not in retry_prompt


def test_raw_json_retry_prompt_projects_terminal_stage_action_contract_error():
    retry_prompt = build_raw_json_retry_prompt(
        "用户需求",
        ContractValidationError("last stage cannot request next stage"),
        workflow_id="STORY_BREAKDOWN",
        current_stage_id="SPRINT_PLAN",
    )

    assert "failureCategory=contract_validation" in retry_prompt
    assert "fieldPath=stage_action" in retry_prompt
    assert "validator=terminal_stage_action" in retry_prompt
    assert "当前阶段是最后阶段，stage_action 必须为 null" in retry_prompt
    assert "artifact_data 数据问题" not in retry_prompt


def test_contract_output_validator_requests_model_retry_for_invalid_artifact():
    class ValidatorRecordingAgent:
        validator = None

        def output_validator(self, func):
            self.validator = func
            return func

    agent = ValidatorRecordingAgent()
    register_contract_output_validator(agent)
    invalid_output = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧需求分析文档。",
            "artifact_update": {
                "type": "replace",
                "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
            },
            "stage_action": None,
            "warnings": [],
        }
    )

    class FakeContext:
        deps = AgentTurnValidationDeps(
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )

    with pytest.raises(Exception, match="failureCategory=contract_validation") as exc:
        agent.validator(FakeContext(), invalid_output)

    assert exc.value.__class__.__name__ == "ModelRetry"


def test_contract_output_validator_model_retry_redacts_contract_error(
    monkeypatch,
):
    canary = "model-retry-contract-canary"

    class ValidatorRecordingAgent:
        validator = None

        def output_validator(self, func):
            self.validator = func
            return func

    def reject_output(*args, **kwargs):
        raise ContractValidationError(f"invalid target stage: target_stage_id={canary}")

    monkeypatch.setattr("agent_runtime.validate_agent_turn", reject_output)
    agent = ValidatorRecordingAgent()
    register_contract_output_validator(agent)
    output = AgentTurnOutput.model_validate(
        {
            "chat": "已完成当前阶段工作，请确认。",
            "artifact_update": {"type": "none"},
            "stage_action": None,
            "warnings": [],
        }
    )

    with pytest.raises(Exception) as captured:
        agent.validator(
            type(
                "FakeContext",
                (),
                {
                    "deps": AgentTurnValidationDeps(
                        workflow_id="TEST_DESIGN",
                        current_stage_id="CLARIFY",
                    )
                },
            )(),
            output,
        )

    message = str(captured.value)
    assert captured.value.__class__.__name__ == "ModelRetry"
    assert "failureCategory=contract_validation" in message
    assert "fieldPath=stage_action.target_stage_id" in message
    assert "validator=stage_transition" in message
    assert canary not in message


def test_runtime_rejects_structured_output_that_violates_workflow_rules():
    agent = FakeAgent(
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
    runtime = PydanticAgentRuntime(agent)

    with pytest.raises(ContractValidationError, match="invalid target stage"):
        runtime.run_turn(
            "用户需求: 登录功能",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )


def test_runtime_maps_pydantic_ai_schema_errors_to_runtime_schema_error(
    monkeypatch,
):
    class FakeSchemaError(Exception):
        pass

    monkeypatch.setattr(
        "agent_runtime.PYDANTIC_AI_SCHEMA_ERRORS",
        (FakeSchemaError,),
    )
    runtime = PydanticAgentRuntime(
        FailingAgent(FakeSchemaError("Exceeded maximum output retries (1)"))
    )

    with pytest.raises(
        AgentRuntimeSchemaError,
        match="Exceeded maximum output retries",
    ):
        runtime.run_turn(
            "用户需求: 登录功能",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )


def test_runtime_maps_pydantic_ai_model_errors_to_runtime_model_error(
    monkeypatch,
):
    class FakeModelError(Exception):
        pass

    monkeypatch.setattr(
        "agent_runtime.PYDANTIC_AI_MODEL_ERRORS",
        (FakeModelError,),
    )
    runtime = PydanticAgentRuntime(FailingAgent(FakeModelError("provider API failed")))

    with pytest.raises(AgentRuntimeModelError, match="provider API failed"):
        runtime.run_turn(
            "用户需求: 登录功能",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )


def test_runtime_rejects_blank_chat_before_returning_output():
    agent = FakeAgent(
        {
            "chat": "   ",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "stage_action": None,
            "warnings": [],
        }
    )
    runtime = PydanticAgentRuntime(agent)

    with pytest.raises(ValueError, match="chat cannot be blank"):
        runtime.run_turn(
            "用户需求: 登录功能",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )


def test_deepseek_v4_settings_disable_thinking_for_structured_output():
    settings = build_model_settings("deepseek-v4-flash")

    assert settings == {
        "extra_body": {
            "thinking": {
                "type": "disabled",
            }
        }
    }


def test_deepseek_v4_uses_more_structured_output_retries():
    assert build_agent_retries("deepseek-v4-flash") == 3


def test_non_deepseek_v4_uses_pydantic_ai_default_retries():
    assert build_agent_retries("gpt-4.1-mini") is None


def test_non_deepseek_v4_settings_keep_provider_defaults():
    assert build_model_settings("gpt-4.1-mini") is None


def test_deepseek_v4_resolves_json_object_only_capability():
    capability = resolve_structured_output_capability("deepseek-v4-flash")

    assert capability.tier == "json_object_only"
    assert capability.response_format == {"type": "json_object"}
    assert capability.max_output_tokens == 32768


import ast
from pathlib import Path
