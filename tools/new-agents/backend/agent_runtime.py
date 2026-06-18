from typing import Any

from agent_contracts import AgentTurnOutput, validate_agent_turn

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


class PydanticAgentRuntime:
    def __init__(self, agent: Any):
        self.agent = agent

    def run_turn(
        self,
        prompt: str,
        *,
        workflow_id: str,
        current_stage_id: str,
    ) -> AgentTurnOutput:
        try:
            result = self.agent.run_sync(prompt)
        except PYDANTIC_AI_SCHEMA_ERRORS as exc:
            raise AgentRuntimeSchemaError(str(exc)) from exc
        except PYDANTIC_AI_MODEL_ERRORS as exc:
            raise AgentRuntimeModelError(str(exc)) from exc

        output = result.output
        if not isinstance(output, AgentTurnOutput):
            output = AgentTurnOutput.model_validate(output)
        return validate_agent_turn(
            output,
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
        output_type=AgentTurnOutput,
        system_prompt=system_prompt,
        retries=build_agent_retries(model_name),
    )
    return PydanticAgentRuntime(agent)
