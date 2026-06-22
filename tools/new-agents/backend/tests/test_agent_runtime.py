import json

import pytest

from agent_contracts import AgentTurnOutput, ContractValidationError
from agent_runtime import (
    AgentRuntimeModelError,
    AgentRuntimeSchemaError,
    AgentTurnValidationDeps,
    PydanticAgentRuntime,
    RawStreamingConfig,
    TEXT_STRUCTURED_OUTPUT_INSTRUCTION,
    build_partial_agent_delta,
    build_agent_retries,
    build_model_settings,
    build_raw_json_retry_prompt,
    build_structured_output_instruction,
    extract_json_string_prefix,
    parse_agent_turn_output_text,
    register_contract_output_validator,
    resolve_structured_output_capability,
)
from sse_schemas import AgentTurnDeltaOutput
from test_artifact_data_renderers import VALID_STRATEGY_ARTIFACT_DATA

VALID_CLARIFY_ARTIFACT = """# 需求分析文档

## 文档信息
| 字段 | 内容 |
|---|---|
| Artifact 名称 | 测试需求分析与澄清基线 |

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
- [x] 测试范围和不测范围已明确。"""

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
    assert "artifact_update.markdown" not in instruction


def test_strategy_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "用户需求",
        ValueError("risks.0.rpn does not match severity * occurrence * detection"),
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert "artifact_data" in prompt
    assert "risks.0.rpn" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "Mermaid 代码块或表格" in prompt
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

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
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

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield final_json

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )
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

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
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

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    assert outputs[-1].chat == "正在梳理需求。"
    assert runtime.last_token_usage == 123


def test_runtime_raw_json_stream_turn_keeps_latest_delta_when_final_json_is_truncated(
    monkeypatch,
):
    chunks = [
        '{"chat":"已更新需求文档。",',
        '"artifact_update":{"type":"replace","markdown":"# 需求分析文档\\n\\n'
        "## 1. 被测系统与边界\\n内容",
    ]

    def fake_stream_chat_completion_content(**kwargs):
        yield from chunks

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
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

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    assert isinstance(outputs[0], AgentTurnDeltaOutput)
    assert outputs[-1].chat == "已更新需求文档。"
    assert outputs[-1].artifact_update.markdown == (
        "# 需求分析文档\n\n## 1. 被测系统与边界\n内容"
    )
    assert outputs[-1].stage_action is None
    assert outputs[-1].warnings == ["artifact_truncated"]


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

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
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

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    assert len(calls) == 2
    assert "上一轮结构化输出未通过校验" in calls[1]["messages"][1]["content"]
    assert "artifact update is required" in calls[1]["messages"][1]["content"]
    assert outputs[-1].chat == "已更新右侧需求分析文档。"
    assert outputs[-1].artifact_update.markdown == VALID_CLARIFY_ARTIFACT


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

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
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

    with pytest.raises(Exception, match="missing required artifact headings") as exc:
        agent.validator(FakeContext(), invalid_output)

    assert exc.value.__class__.__name__ == "ModelRetry"


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
