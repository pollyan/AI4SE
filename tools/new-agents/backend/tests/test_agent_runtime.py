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
    extract_json_string_prefix,
    parse_agent_turn_output_text,
    register_contract_output_validator,
)
from sse_schemas import AgentTurnDeltaOutput


VALID_CLARIFY_ARTIFACT = """# 需求分析文档

## 1. 被测系统与边界
内容

## 2. 系统交互与核心链路
```mermaid
flowchart TD
    User["用户"] --> Login["登录入口"]
    Login --> Auth["认证服务"]
    Auth --> Session["会话状态"]
```

内容

## 3. 待澄清与阻断性问题
内容

## 4. 隐式需求与非功能性考量
内容"""

VALID_CLARIFY_ARTIFACT_JSON = (
    "# 需求分析文档\\n\\n"
    "## 1. 被测系统与边界\\n内容\\n\\n"
    "## 2. 系统交互与核心链路\\n"
    "```mermaid\\n"
    "flowchart TD\\n"
    "    User[\\\"用户\\\"] --> Login[\\\"登录入口\\\"]\\n"
    "    Login --> Auth[\\\"认证服务\\\"]\\n"
    "    Auth --> Session[\\\"会话状态\\\"]\\n"
    "```\\n\\n"
    "内容\\n\\n"
    "## 3. 待澄清与阻断性问题\\n内容\\n\\n"
    "## 4. 隐式需求与非功能性考量\\n内容"
)


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

    outputs = list(runtime.stream_turn(
        "用户需求: 登录功能",
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    ))

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
        '## 1. 被测系统与边界\\n内容'
    )

    assert extract_json_string_prefix(text, "chat") == "正在梳理需求。"
    assert extract_json_string_prefix(
        text,
        "markdown",
    ) == "# 需求分析文档\n\n## 1. 被测系统与边界\n内容"


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


def test_runtime_raw_json_stream_turn_yields_real_delta_before_final_output(
    monkeypatch,
):
    final_json = (
        '{"chat":"正在梳理需求。",'
        '"artifact_update":{"type":"replace","markdown":"'
        f'{VALID_CLARIFY_ARTIFACT_JSON}' + '"},'
        '"stage_action":null,"warnings":[]}'
    )
    chunks = [
        '{"chat":"正在',
        '梳理需求。","artifact_update":{"type":"replace","markdown":"# 需求分析文档\\n\\n',
        '## 1. 被测系统与边界\\n内容',
    ]
    chunks = [chunks[0], chunks[1], chunks[2], final_json[len("".join(chunks[:3])):]]
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

    outputs = list(runtime.stream_turn(
        "用户需求",
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    ))

    assert isinstance(outputs[0], AgentTurnDeltaOutput)
    assert outputs[0].chat == "正在"
    assert isinstance(outputs[1], AgentTurnDeltaOutput)
    assert outputs[1].chat == "正在梳理需求。"
    assert outputs[-1].chat == "正在梳理需求。"
    assert outputs[-1].artifact_update.markdown == VALID_CLARIFY_ARTIFACT
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert "结构化输出格式要求" in calls[0]["messages"][0]["content"]


def test_raw_streaming_runtime_records_stream_usage(monkeypatch):
    final_json = (
        '{"chat":"正在梳理需求。",'
        '"artifact_update":{"type":"replace","markdown":"'
        f'{VALID_CLARIFY_ARTIFACT_JSON}' + '"},'
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

    outputs = list(runtime.stream_turn(
        "用户需求",
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    ))

    assert outputs[-1].chat == "正在梳理需求。"
    assert runtime.last_token_usage == 123


def test_runtime_raw_json_stream_turn_keeps_latest_delta_when_final_json_is_truncated(
    monkeypatch,
):
    chunks = [
        '{"chat":"已更新需求文档。",',
        '"artifact_update":{"type":"replace","markdown":"# 需求分析文档\\n\\n'
        '## 1. 被测系统与边界\\n内容',
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

    outputs = list(runtime.stream_turn(
        "用户需求",
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    ))

    assert isinstance(outputs[0], AgentTurnDeltaOutput)
    assert outputs[-1].chat == "已更新需求文档。"
    assert outputs[-1].artifact_update.markdown == (
        "# 需求分析文档\n\n## 1. 被测系统与边界\n内容"
    )
    assert outputs[-1].stage_action is None
    assert outputs[-1].warnings == ["artifact_truncated"]


def test_contract_output_validator_requests_model_retry_for_invalid_artifact():
    class ValidatorRecordingAgent:
        validator = None

        def output_validator(self, func):
            self.validator = func
            return func

    agent = ValidatorRecordingAgent()
    register_contract_output_validator(agent)
    invalid_output = AgentTurnOutput.model_validate({
        "chat": "已更新右侧需求分析文档。",
        "artifact_update": {
            "type": "replace",
            "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
        },
        "stage_action": None,
        "warnings": [],
    })

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
    runtime = PydanticAgentRuntime(
        FailingAgent(FakeModelError("provider API failed"))
    )

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
