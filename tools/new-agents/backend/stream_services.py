from collections.abc import Iterator

from openai import APIError, AuthenticationError, RateLimitError
from pydantic import ValidationError

from agent_contracts import (
    AgentTurnOutput,
    ContractValidationError,
    build_artifact_contract_prompt,
)
from agent_runtime import (
    AgentRuntimeDependencyError,
    AgentRuntimeModelError,
    AgentRuntimeSchemaError,
    PYDANTIC_AI_SCHEMA_ERRORS,
    build_pydantic_agent_runtime,
)
from request_schemas import (
    AgentRunStreamRequest,
    RequestValidationError,
    parse_agent_run_stream_request,
)
from sse_schemas import (
    AgentTurnDeltaEvent,
    AgentTurnDeltaOutput,
    AgentTurnEvent,
    ErrorEvent,
    RunStartedEvent,
    SseEvent,
)


SCHEMA_RETRY_EXHAUSTED_MESSAGE = (
    "模型连续生成的结构化结果未通过校验。请重试本轮操作；"
    "如果多次失败，请补充更明确的需求或阶段确认信息。"
)


def build_runtime_system_prompt(agent_request: AgentRunStreamRequest) -> str:
    artifact_contract = build_artifact_contract_prompt(
        workflow_id=agent_request.workflow_id,
        current_stage_id=agent_request.stage_id,
    )
    return f"{agent_request.system_prompt}{artifact_contract}"


def format_schema_validation_error_message(error: Exception) -> str:
    message = str(error)
    if "Exceeded maximum output retries" in message:
        return SCHEMA_RETRY_EXHAUSTED_MESSAGE
    return message


def stream_agent_run_events(
    agent_request: AgentRunStreamRequest,
    *,
    api_key: str,
    base_url: str | None,
    model_name: str,
) -> Iterator[SseEvent]:
    try:
        agent_request = parse_agent_run_stream_request(
            agent_request.model_dump(by_alias=True)
        )
        runtime = build_pydantic_agent_runtime(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            system_prompt=build_runtime_system_prompt(agent_request),
        )
        yield RunStartedEvent()
        final_output = None
        for output in runtime.stream_turn(
            agent_request.prompt,
            workflow_id=agent_request.workflow_id,
            current_stage_id=agent_request.stage_id,
        ):
            if isinstance(output, AgentTurnOutput):
                yield AgentTurnDeltaEvent(
                    output=AgentTurnDeltaOutput.model_validate(
                        output.model_dump(mode="json")
                    )
                )
                final_output = output
            else:
                yield AgentTurnDeltaEvent(output=output)
        if final_output is not None:
            yield AgentTurnEvent(output=final_output)
    except ContractValidationError as e:
        yield ErrorEvent(
            code="CONTRACT_VALIDATION_FAILED",
            message=str(e),
        )
    except ValidationError as e:
        yield ErrorEvent(
            code="SCHEMA_VALIDATION_FAILED",
            message=format_schema_validation_error_message(e),
        )
    except AgentRuntimeSchemaError as e:
        yield ErrorEvent(
            code="SCHEMA_VALIDATION_FAILED",
            message=format_schema_validation_error_message(e),
        )
    except PYDANTIC_AI_SCHEMA_ERRORS as e:
        yield ErrorEvent(
            code="SCHEMA_VALIDATION_FAILED",
            message=format_schema_validation_error_message(e),
        )
    except RequestValidationError as e:
        yield ErrorEvent(
            code="REQUEST_VALIDATION_FAILED",
            message=str(e),
        )
    except AgentRuntimeDependencyError as e:
        yield ErrorEvent(
            code="AGENT_RUNTIME_UNAVAILABLE",
            message=str(e),
        )
    except AgentRuntimeModelError as e:
        yield ErrorEvent(
            code="LLM_ERROR",
            message=str(e),
        )
    except (AuthenticationError, RateLimitError, APIError) as e:
        yield ErrorEvent(
            code="LLM_ERROR",
            message=str(e),
        )
