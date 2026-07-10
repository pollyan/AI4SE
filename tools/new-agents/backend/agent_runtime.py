from collections.abc import Iterator
from dataclasses import dataclass
import json
import re
from typing import Any

from pydantic import ValidationError

from agent_contracts import (
    AgentTurnOutput,
    ContractValidationError,
    validate_agent_turn,
)
from artifact_data_renderers import (
    get_artifact_data_renderer_stage_keys,
    render_agent_turn_from_artifact_data,
    render_partial_artifact_data_markdown,
)
from artifact_data_instruction_registry import (
    ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS,
)
from llm_client import LlmClientError, stream_chat_completion_content
from sse_schemas import AgentTurnDeltaOutput
from workflow_manifest import format_visual_protocol_instruction

try:
    from pydantic_ai.exceptions import (
        ModelAPIError,
        ModelHTTPError,
        UnexpectedModelBehavior,
    )
except ImportError:
    ModelAPIError = None
    ModelHTTPError = None
    UnexpectedModelBehavior = None

PYDANTIC_AI_SCHEMA_ERRORS = tuple(
    error_type for error_type in (UnexpectedModelBehavior,) if error_type is not None
)
PYDANTIC_AI_MODEL_ERRORS = tuple(
    error_type
    for error_type in (ModelHTTPError, ModelAPIError)
    if error_type is not None
)


class AgentRuntimeDependencyError(RuntimeError):
    """Raised when the configured agent runtime dependency is unavailable."""


class AgentRuntimeSchemaError(RuntimeError):
    """Raised when PydanticAI cannot produce valid structured output."""


class AgentRuntimeModelError(RuntimeError):
    """Raised when the underlying model provider reports an error."""


@dataclass(frozen=True)
class AgentTurnValidationDeps:
    workflow_id: str
    current_stage_id: str


@dataclass(frozen=True)
class RawStreamingConfig:
    api_key: str
    base_url: str | None
    model_name: str
    system_prompt: str


@dataclass(frozen=True)
class StructuredOutputCapability:
    tier: str
    response_format: dict[str, Any] | None


TEXT_STRUCTURED_OUTPUT_INSTRUCTION = """

【结构化输出格式要求】
你必须只输出一个 JSON 对象，不要输出 Markdown 代码围栏，不要输出 JSON 之外的任何解释。
为了支持前端实时显示，请严格按照以下字段顺序输出：
1. "chat"
2. "artifact_update"
3. "stage_action"
4. "warnings"

JSON 对象结构：
{
  "chat": "面向用户的自然工作对话。说明我本轮已经做了什么、本轮确认或假定的关键点、右侧产出物更新了哪些部分、接下来需要用户确认或补充什么。不要复制完整产出物正文。",
  "artifact_update": {
    "type": "replace 或 none",
    "markdown": "当 type 为 replace 时，这里必须是完整 Markdown 产出物"
  },
  "stage_action": null 或 {"type": "request_next_stage", "target_stage_id": "下一阶段内部 ID"},
  "warnings": []
}

chat 字段必须像一次自然的工作对话，不要只用一两句模板化提示；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时可以适度使用短列表；不要每轮套用固定 bullet 数量、固定标签或固定栏目，让左侧对话有独立阅读价值。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""

RAW_JSON_STREAMING_MAX_ATTEMPTS = 2


def get_artifact_data_ready_stages() -> set[tuple[str, str]]:
    return set(ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS)


def supports_artifact_data_rendering(workflow_id: str, current_stage_id: str) -> bool:
    stage_key = (workflow_id, current_stage_id)
    return (
        stage_key in ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS
        and stage_key in get_artifact_data_renderer_stage_keys()
    )


def _find_json_object_end(text: str, object_start_index: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    for index in range(object_start_index, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    return -1


def _normalize_artifact_data_instruction_order(instruction: str) -> str:
    if '"artifact_data"' not in instruction:
        return instruction

    normalized = instruction.replace(
        '1. "chat"\n2. "artifact_data"',
        '1. "artifact_data"\n2. "chat"',
    )
    json_object_start = normalized.find('{\n  "chat"')
    if json_object_start < 0:
        return normalized

    chat_line_start = normalized.find('  "chat"', json_object_start)
    artifact_block_start = normalized.find('  "artifact_data"', chat_line_start)
    if chat_line_start < 0 or artifact_block_start < 0:
        return normalized

    chat_line_end = normalized.find("\n", chat_line_start)
    artifact_value_start = normalized.find("{", artifact_block_start)
    if chat_line_end < 0 or artifact_value_start < 0:
        return normalized

    artifact_value_end = _find_json_object_end(normalized, artifact_value_start)
    if artifact_value_end < 0:
        return normalized

    artifact_block_end = artifact_value_end
    if normalized[artifact_block_end:artifact_block_end + 2] == ",\n":
        artifact_block_end += 2
    elif artifact_block_end < len(normalized) and normalized[artifact_block_end] == "\n":
        artifact_block_end += 1

    chat_line = normalized[chat_line_start:chat_line_end + 1]
    artifact_block = normalized[artifact_block_start:artifact_block_end]
    return (
        normalized[:chat_line_start]
        + artifact_block
        + chat_line
        + normalized[chat_line_end + 1:artifact_block_start]
        + normalized[artifact_block_end:]
    )


def build_structured_output_instruction(
    workflow_id: str,
    current_stage_id: str,
) -> str:
    stage_key = (workflow_id, current_stage_id)
    instruction = ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS.get(stage_key)
    if instruction is None:
        return TEXT_STRUCTURED_OUTPUT_INSTRUCTION
    return (
        _normalize_artifact_data_instruction_order(instruction).rstrip()
        + "\n\n"
        + format_visual_protocol_instruction()
        + "\n"
    )



def build_raw_json_retry_prompt(
    prompt: str,
    error: Exception,
    *,
    workflow_id: str | None = None,
    current_stage_id: str | None = None,
) -> str:
    if (
        workflow_id is not None
        and current_stage_id is not None
        and supports_artifact_data_rendering(workflow_id, current_stage_id)
    ):
        return (
            f"{prompt}\n\n"
            "【上一轮结构化输出未通过校验】\n"
            f"{error}\n\n"
            "请立刻重新输出一个完整合法的 JSON 对象，不要输出 JSON 之外的解释。"
            "必须修正上述 artifact_data 数据问题；所有必填字段必须存在，"
            "所有字符串必须非空，数组必须至少包含一项。不要输出 Markdown 文档、"
            "Mermaid、D2、Graphviz DOT、PlantUML 代码块或表格，"
            "后端会根据 artifact_data 渲染右侧产出物。"
        )
    return (
        f"{prompt}\n\n"
        "【上一轮结构化输出未通过校验】\n"
        f"{error}\n\n"
        "请立刻重新输出一个完整合法的 JSON 对象，不要输出 JSON 之外的解释。"
        "必须修正上述问题；如果当前阶段要求右侧产出物，"
        "artifact_update.type 必须为 replace，markdown 必须包含当前阶段完整 Markdown 文档、"
        "所有必填标题、必需 Mermaid/ai4se-visual 可视化和阶段门禁。"
    )


def register_contract_output_validator(agent: Any) -> None:
    from pydantic_ai.exceptions import ModelRetry

    @agent.output_validator
    def validate_contract(ctx: Any, output: AgentTurnOutput) -> AgentTurnOutput:
        try:
            return validate_agent_turn(
                output,
                workflow_id=ctx.deps.workflow_id,
                current_stage_id=ctx.deps.current_stage_id,
            )
        except ContractValidationError as exc:
            raise ModelRetry(
                f"结构化输出不符合业务契约，请重新生成完整合法输出：{exc}"
            ) from exc


class PydanticAgentRuntime:
    def __init__(
        self,
        agent: Any,
        raw_streaming_config: RawStreamingConfig | None = None,
    ):
        self.agent = agent
        self.raw_streaming_config = raw_streaming_config
        self.last_token_usage: int | None = None

    @staticmethod
    def _coerce_output(output: Any) -> AgentTurnOutput:
        if isinstance(output, AgentTurnOutput):
            return output
        return AgentTurnOutput.model_validate(output)

    @staticmethod
    def _coerce_delta_output(output: Any) -> AgentTurnDeltaOutput:
        if isinstance(output, AgentTurnDeltaOutput):
            return output
        if isinstance(output, AgentTurnOutput):
            return AgentTurnDeltaOutput.model_validate(output.model_dump(mode="json"))
        return AgentTurnDeltaOutput.model_validate(output)

    def run_turn(
        self,
        prompt: str,
        *,
        workflow_id: str,
        current_stage_id: str,
    ) -> AgentTurnOutput:
        try:
            result = self.agent.run_sync(
                prompt,
                deps=AgentTurnValidationDeps(
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                ),
            )
        except PYDANTIC_AI_SCHEMA_ERRORS as exc:
            raise AgentRuntimeSchemaError(str(exc)) from exc
        except PYDANTIC_AI_MODEL_ERRORS as exc:
            raise AgentRuntimeModelError(str(exc)) from exc

        output = result.output
        output = self._coerce_output(output)
        return validate_agent_turn(
            output,
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )

    def stream_turn(
        self,
        prompt: str,
        *,
        workflow_id: str,
        current_stage_id: str,
    ) -> Iterator[AgentTurnDeltaOutput | AgentTurnOutput]:
        if self.raw_streaming_config is not None:
            try:
                yield from self._stream_raw_json_turn(
                    prompt,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
                return
            except LlmClientError as exc:
                raise AgentRuntimeModelError(str(exc)) from exc
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                raise AgentRuntimeSchemaError(str(exc)) from exc

        if not hasattr(self.agent, "run_stream_sync"):
            yield self.run_turn(
                prompt,
                workflow_id=workflow_id,
                current_stage_id=current_stage_id,
            )
            return

        deps = AgentTurnValidationDeps(
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )
        final_output: AgentTurnOutput | None = None
        try:
            result = self.agent.run_stream_sync(prompt, deps=deps)
            for raw_output in result.stream_output(debounce_by=None):
                try:
                    delta_output = self._coerce_delta_output(raw_output)
                except (ValidationError, ValueError):
                    continue
                if (
                    delta_output.chat is None
                    and delta_output.artifact_update is None
                    and delta_output.stage_action is None
                    and not delta_output.warnings
                ):
                    continue
                try:
                    final_output = self._coerce_output(raw_output)
                    yield final_output
                except (ValidationError, ValueError):
                    yield delta_output
            if final_output is None and hasattr(result, "get_output"):
                final_output = self._coerce_output(result.get_output())
                yield final_output
        except PYDANTIC_AI_SCHEMA_ERRORS as exc:
            raise AgentRuntimeSchemaError(str(exc)) from exc
        except PYDANTIC_AI_MODEL_ERRORS as exc:
            raise AgentRuntimeModelError(str(exc)) from exc

        if final_output is None:
            raise AgentRuntimeSchemaError("PydanticAI stream produced no output")
        validate_agent_turn(
            final_output,
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )

    def _stream_raw_json_turn(
        self,
        prompt: str,
        *,
        workflow_id: str,
        current_stage_id: str,
    ) -> Iterator[AgentTurnDeltaOutput | AgentTurnOutput]:
        assert self.raw_streaming_config is not None
        config = self.raw_streaming_config
        self.last_token_usage = None
        extra_body = None
        model_settings = build_model_settings(config.model_name)
        if model_settings:
            extra_body = model_settings.get("extra_body")
        structured_output_capability = resolve_structured_output_capability(
            config.model_name
        )

        attempt_prompt = prompt
        for attempt_index in range(RAW_JSON_STREAMING_MAX_ATTEMPTS):
            accumulated = ""
            latest_chat = ""
            latest_markdown = ""
            emitted_any_delta = False

            for text_chunk in stream_chat_completion_content(
                api_key=config.api_key,
                base_url=config.base_url,
                model=config.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            config.system_prompt
                            + build_structured_output_instruction(
                                workflow_id,
                                current_stage_id,
                            )
                        ),
                    },
                    {"role": "user", "content": attempt_prompt},
                ],
                temperature=0,
                response_format=structured_output_capability.response_format,
                extra_body=extra_body,
                on_usage=lambda total_tokens: setattr(
                    self,
                    "last_token_usage",
                    total_tokens,
                ),
            ):
                accumulated += text_chunk
                delta = build_partial_agent_delta(
                    accumulated,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
                if delta is None:
                    continue
                next_chat = delta.chat or latest_chat
                next_markdown = (
                    delta.artifact_update.markdown
                    if delta.artifact_update and delta.artifact_update.markdown
                    else latest_markdown
                )
                if not should_emit_partial_delta(
                    latest_chat=latest_chat,
                    next_chat=next_chat,
                    latest_markdown=latest_markdown,
                    next_markdown=next_markdown,
                ):
                    continue
                latest_chat = next_chat
                latest_markdown = next_markdown
                emitted_any_delta = True
                yield delta

            try:
                final_output = parse_agent_turn_output_text(
                    accumulated,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
            except json.JSONDecodeError:
                raise
            except ValidationError as exc:
                if attempt_index >= RAW_JSON_STREAMING_MAX_ATTEMPTS - 1:
                    raise
                attempt_prompt = build_raw_json_retry_prompt(
                    prompt,
                    exc,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
                continue

            try:
                final_output = validate_agent_turn(
                    final_output,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
            except (ContractValidationError, ValidationError) as exc:
                if attempt_index >= RAW_JSON_STREAMING_MAX_ATTEMPTS - 1:
                    raise
                attempt_prompt = build_raw_json_retry_prompt(
                    prompt,
                    exc,
                    workflow_id=workflow_id,
                    current_stage_id=current_stage_id,
                )
                continue

            if not emitted_any_delta:
                yield AgentTurnDeltaOutput.model_validate(
                    final_output.model_dump(mode="json")
                )
            yield final_output
            return

        raise AgentRuntimeSchemaError(
            "Raw JSON streaming did not produce valid structured output"
        )


def build_model_settings(model_name: str) -> dict[str, Any] | None:
    if model_name.startswith("deepseek-v4-"):
        return {
            "extra_body": {
                "thinking": {
                    "type": "disabled",
                }
            }
        }
    return None


def build_agent_retries(model_name: str) -> int | None:
    if model_name.startswith("deepseek-v4-"):
        return 3
    return None


def resolve_structured_output_capability(
    model_name: str,
) -> StructuredOutputCapability:
    if model_name.startswith("deepseek-v4-"):
        return StructuredOutputCapability(
            tier="json_object_only",
            response_format={"type": "json_object"},
        )
    return StructuredOutputCapability(
        tier="json_object_only",
        response_format={"type": "json_object"},
    )


def strip_json_fence(text: str) -> str:
    stripped = text.strip()
    fence_match = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fence_match:
        return fence_match.group(1).strip()
    return stripped


def parse_agent_turn_output_text(
    text: str,
    *,
    workflow_id: str | None = None,
    current_stage_id: str | None = None,
) -> AgentTurnOutput:
    parsed = json.loads(strip_json_fence(text))
    if "artifact_data" in parsed:
        if workflow_id is None or current_stage_id is None:
            raise ValueError(
                "workflow_id and current_stage_id are required for artifact_data"
            )
        rendered = render_agent_turn_from_artifact_data(
            parsed,
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )
        if rendered is None:
            raise ValueError(
                f"artifact_data renderer is not configured for {workflow_id}/{current_stage_id}"
            )
        return rendered
    return AgentTurnOutput.model_validate(parsed)


def extract_json_string_prefix(text: str, key: str) -> str | None:
    key_match = re.search(rf'"{re.escape(key)}"\s*:', text)
    if not key_match:
        return None
    index = key_match.end()
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] != '"':
        return None
    index += 1
    chars: list[str] = []
    while index < len(text):
        char = text[index]
        if char == '"':
            return "".join(chars)
        if char != "\\":
            chars.append(char)
            index += 1
            continue

        index += 1
        if index >= len(text):
            break
        escape = text[index]
        if escape == "n":
            chars.append("\n")
        elif escape == "r":
            chars.append("\r")
        elif escape == "t":
            chars.append("\t")
        elif escape == "b":
            chars.append("\b")
        elif escape == "f":
            chars.append("\f")
        elif escape in {'"', "\\", "/"}:
            chars.append(escape)
        elif escape == "u":
            hex_value = text[index + 1 : index + 5]
            if len(hex_value) < 4 or not re.fullmatch(r"[0-9a-fA-F]{4}", hex_value):
                break
            chars.append(chr(int(hex_value, 16)))
            index += 4
        else:
            chars.append(escape)
        index += 1
    return "".join(chars) if chars else None


def build_partial_agent_delta(
    text: str,
    *,
    workflow_id: str | None = None,
    current_stage_id: str | None = None,
) -> AgentTurnDeltaOutput | None:
    chat = extract_json_string_prefix(text, "chat")
    markdown = extract_json_string_prefix(text, "markdown")
    if not markdown and re.search(r'"artifact_data"\s*:', text):
        markdown = build_artifact_data_progress_markdown(
            text,
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )
    if not chat and not markdown:
        return None
    return AgentTurnDeltaOutput(
        chat=chat,
        artifact_update=(
            {"type": "replace", "markdown": markdown} if markdown else None
        ),
    )


def build_artifact_data_progress_markdown(
    text: str,
    *,
    workflow_id: str | None = None,
    current_stage_id: str | None = None,
) -> str | None:
    complete_markdown = render_complete_streamed_artifact_data_markdown(
        text,
        workflow_id=workflow_id,
        current_stage_id=current_stage_id,
    )
    if complete_markdown:
        return complete_markdown
    return render_partial_streamed_artifact_data_markdown(
        text,
        workflow_id=workflow_id,
        current_stage_id=current_stage_id,
    )


def extract_complete_json_value_after_key(text: str, key: str) -> Any | None:
    key_match = re.search(rf'"{re.escape(key)}"\s*:', text)
    if key_match is None:
        return None
    index = key_match.end()
    while index < len(text) and text[index].isspace():
        index += 1
    try:
        value, _ = json.JSONDecoder().raw_decode(text[index:])
    except json.JSONDecodeError:
        return None
    return value


def extract_partial_json_object_after_key(text: str, key: str) -> dict[str, Any] | None:
    key_match = re.search(rf'"{re.escape(key)}"\s*:', text)
    if key_match is None:
        return None
    index = key_match.end()
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] != "{":
        return None

    decoder = json.JSONDecoder()
    index += 1
    partial: dict[str, Any] = {}
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index < len(text) and text[index] == ",":
            index += 1
            continue
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text) or text[index] == "}":
            break

        try:
            field_name, next_index = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            break
        if not isinstance(field_name, str):
            break
        index += next_index

        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text) or text[index] != ":":
            break
        index += 1
        while index < len(text) and text[index].isspace():
            index += 1

        try:
            field_value, next_index = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            break
        partial[field_name] = field_value
        index += next_index

    return partial or None


def render_complete_streamed_artifact_data_markdown(
    text: str,
    *,
    workflow_id: str | None,
    current_stage_id: str | None,
) -> str | None:
    if workflow_id is None or current_stage_id is None:
        return None
    artifact_data = extract_complete_json_value_after_key(text, "artifact_data")
    if artifact_data is None:
        return None
    try:
        rendered = render_agent_turn_from_artifact_data(
            {
                "chat": (
                    extract_json_string_prefix(text, "chat")
                    or "正在生成右侧产出物。"
                ),
                "artifact_data": artifact_data,
                "stage_action": None,
                "warnings": [],
            },
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )
    except (ValidationError, ValueError):
        return None
    if rendered is None:
        return None
    artifact_update = rendered.artifact_update
    if artifact_update.type != "replace" or not artifact_update.markdown:
        return None
    return artifact_update.markdown


def render_partial_streamed_artifact_data_markdown(
    text: str,
    *,
    workflow_id: str | None,
    current_stage_id: str | None,
) -> str | None:
    if workflow_id is None or current_stage_id is None:
        return None
    artifact_data = extract_partial_json_object_after_key(text, "artifact_data")
    if artifact_data is None:
        return None
    return render_partial_artifact_data_markdown(
        artifact_data,
        workflow_id=workflow_id,
        current_stage_id=current_stage_id,
    )


def should_emit_partial_delta(
    *,
    latest_chat: str,
    next_chat: str,
    latest_markdown: str,
    next_markdown: str,
) -> bool:
    if next_chat == latest_chat and next_markdown == latest_markdown:
        return False
    if not latest_chat and next_chat:
        return True
    if not latest_markdown and next_markdown:
        return True
    if len(next_chat) - len(latest_chat) >= 4:
        return True
    if next_chat != latest_chat and next_chat.endswith(("。", "！", "？", "\n")):
        return True
    if len(next_markdown) - len(latest_markdown) >= 32:
        return True
    if next_markdown.count("\n") > latest_markdown.count("\n"):
        return True
    return False


def build_pydantic_agent_runtime(
    *,
    api_key: str,
    base_url: str,
    model_name: str,
    system_prompt: str,
) -> PydanticAgentRuntime:
    try:
        from pydantic_ai import Agent
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
    except ImportError as exc:
        raise AgentRuntimeDependencyError(
            "pydantic-ai-slim[openai] is required for PydanticAgentRuntime; "
            "install tools/new-agents/backend/requirements.txt"
        ) from exc

    model = OpenAIChatModel(
        model_name,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        settings=build_model_settings(model_name),
    )
    agent = Agent(
        model,
        deps_type=AgentTurnValidationDeps,
        output_type=AgentTurnOutput,
        system_prompt=system_prompt,
        retries=build_agent_retries(model_name),
    )
    register_contract_output_validator(agent)
    return PydanticAgentRuntime(
        agent,
        raw_streaming_config=RawStreamingConfig(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            system_prompt=system_prompt,
        ),
    )
