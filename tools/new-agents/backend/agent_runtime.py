from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from agent_contracts import (
    AgentTurnOutput,
    ContractValidationError,
    validate_agent_turn,
)
from sse_schemas import AgentTurnDeltaOutput

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
    error_type
    for error_type in (UnexpectedModelBehavior,)
    if error_type is not None
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
    def __init__(self, agent: Any):
        self.agent = agent

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
            return AgentTurnDeltaOutput.model_validate(
                output.model_dump(mode="json")
            )
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
    return PydanticAgentRuntime(agent)
