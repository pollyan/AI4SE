from collections.abc import Iterator
from math import ceil
import re
from time import perf_counter
from typing import Protocol
from urllib.parse import urlparse

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
from stage_readiness import apply_stage_readiness_gate
from sse_schemas import (
    AgentTurnDeltaEvent,
    AgentTurnDeltaOutput,
    AgentTurnEvent,
    ErrorDiagnostic,
    ErrorEvent,
    RunStartedEvent,
    SseEvent,
)


SCHEMA_RETRY_EXHAUSTED_MESSAGE = (
    "模型连续生成的结构化结果未通过校验。请重试本轮操作；"
    "如果多次失败，请补充更明确的需求或阶段确认信息。"
)
STRUCTURED_OUTPUT_PUBLIC_REASON = (
    "模型输出的结构化字段未通过校验，右侧产出物已保持不变。"
)
CONTRACT_VALIDATION_PUBLIC_REASON = (
    "模型输出未满足当前工作流产物契约，右侧产出物已保持不变。"
)
REQUEST_VALIDATION_PUBLIC_REASON = "请求参数未通过校验，本轮生成未开始。"
RUNTIME_UNAVAILABLE_PUBLIC_REASON = (
    "智能体运行时依赖不可用，本轮生成未开始。"
)
PROVIDER_AUTH_PUBLIC_REASON = (
    "模型供应商鉴权失败，请检查 API Key、Base URL、模型名称和供应商权限。"
)
PROVIDER_RATE_LIMIT_PUBLIC_REASON = (
    "模型供应商限流或额度不足，请稍后重试或检查供应商额度。"
)
PROVIDER_CONNECTION_PUBLIC_REASON = (
    "模型供应商连接失败，请检查网络、Base URL 或供应商服务状态。"
)
PROVIDER_ERROR_PUBLIC_REASON = (
    "模型供应商返回错误，本轮生成未完成，右侧产出物已保持不变。"
)


class StreamPersistence(Protocol):
    def ensure_run(
        self,
        agent_request: AgentRunStreamRequest,
        *,
        model_name: str,
    ) -> str:
        ...

    def append_user_message(self, run_id: str, content: str) -> None:
        ...

    def build_runtime_prompt(self, run_id: str, current_prompt: str) -> str:
        ...

    def build_runtime_context(
        self,
        run_id: str,
        current_prompt: str,
    ) -> tuple[str, list[str]]:
        ...

    def append_assistant_message(self, run_id: str, content: str) -> None:
        ...

    def record_artifact_version(
        self,
        run_id: str,
        stage_id: str,
        content: str,
        *,
        artifact_data: dict | None = None,
    ) -> None:
        ...

    def record_turn_metric(self, **kwargs) -> None:
        ...


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


def extract_contract_retry_count(error: Exception) -> int:
    match = re.search(r"Exceeded maximum output retries \((\d+)\)", str(error))
    if match is None:
        return 0
    return int(match.group(1))


def _first_validation_error(error: ValidationError) -> tuple[str, str]:
    errors = error.errors()
    if not errors:
        return "artifact_data", "pydantic_validation"

    first_error = errors[0]
    location = first_error.get("loc") or ("artifact_data",)
    field_path = ".".join(str(part) for part in location)
    validator = str(first_error.get("type") or "pydantic_validation")
    return field_path or "artifact_data", validator


def _provider_diagnostic_details(error: Exception) -> tuple[str, bool, str]:
    message = str(error).lower()
    if any(
        marker in message
        for marker in (
            "401",
            "403",
            "api key",
            "auth",
            "unauthorized",
            "forbidden",
            "permission",
        )
    ):
        return "provider_authentication", False, PROVIDER_AUTH_PUBLIC_REASON
    if any(
        marker in message
        for marker in (
            "429",
            "quota",
            "rate limit",
            "ratelimit",
            "too many requests",
        )
    ):
        return "provider_rate_limit", True, PROVIDER_RATE_LIMIT_PUBLIC_REASON
    if any(
        marker in message
        for marker in (
            "timeout",
            "network",
            "unreachable",
            "connection",
            "connect",
        )
    ):
        return "provider_connection", True, PROVIDER_CONNECTION_PUBLIC_REASON
    return "provider_error", True, PROVIDER_ERROR_PUBLIC_REASON


def _build_error_diagnostic(
    *,
    code: str,
    error: Exception,
    workflow_id: str,
    stage_id: str,
) -> ErrorDiagnostic:
    if code == "SCHEMA_VALIDATION_FAILED":
        field_path = "artifact_data"
        validator = "structured_output"
        if isinstance(error, ValidationError):
            field_path, validator = _first_validation_error(error)
        elif "Exceeded maximum output retries" in str(error):
            validator = "pydantic_ai_output_retry"
        return ErrorDiagnostic(
            phase="structured_output",
            workflowId=workflow_id,
            stageId=stage_id,
            fieldPath=field_path,
            validator=validator,
            retryable=True,
            publicReason=STRUCTURED_OUTPUT_PUBLIC_REASON,
        )

    if code == "CONTRACT_VALIDATION_FAILED":
        return ErrorDiagnostic(
            phase="contract_validation",
            workflowId=workflow_id,
            stageId=stage_id,
            fieldPath="artifact_contract",
            validator="workflow_contract",
            retryable=False,
            publicReason=CONTRACT_VALIDATION_PUBLIC_REASON,
        )

    if code == "REQUEST_VALIDATION_FAILED":
        return ErrorDiagnostic(
            phase="request_validation",
            workflowId=workflow_id,
            stageId=stage_id,
            fieldPath="request",
            validator="request_schema",
            retryable=False,
            publicReason=REQUEST_VALIDATION_PUBLIC_REASON,
        )

    if code == "AGENT_RUNTIME_UNAVAILABLE":
        return ErrorDiagnostic(
            phase="runtime",
            workflowId=workflow_id,
            stageId=stage_id,
            fieldPath="runtime",
            validator="runtime_dependency",
            retryable=False,
            publicReason=RUNTIME_UNAVAILABLE_PUBLIC_REASON,
        )

    if code == "LLM_ERROR":
        validator, retryable, public_reason = _provider_diagnostic_details(error)
        return ErrorDiagnostic(
            phase="provider",
            workflowId=workflow_id,
            stageId=stage_id,
            fieldPath="provider",
            validator=validator,
            retryable=retryable,
            publicReason=public_reason,
        )

    return ErrorDiagnostic(
        phase="unknown",
        workflowId=workflow_id,
        stageId=stage_id,
        fieldPath="unknown",
        validator="unknown",
        retryable=False,
        publicReason="本轮生成失败，右侧产出物已保持不变。",
    )


def _error_diagnostic_payload(
    diagnostic: ErrorDiagnostic | None,
) -> dict | None:
    if diagnostic is None:
        return None
    return diagnostic.model_dump(mode="json", by_alias=True)


def _estimated_tokens(input_chars: int, output_chars: int) -> int:
    total_chars = max(0, input_chars) + max(0, output_chars)
    if total_chars == 0:
        return 0
    return max(1, ceil(total_chars / 4))


def infer_provider_name(base_url: str | None) -> str:
    if not base_url:
        return "openai"
    hostname = urlparse(base_url).hostname
    if not hostname:
        return "unknown"
    hostname = hostname.lower()
    if hostname == "api.openai.com":
        return "openai"
    if hostname.endswith(".deepseek.com") or hostname == "api.deepseek.com":
        return "deepseek"
    if "dashscope" in hostname or hostname.endswith(".aliyuncs.com"):
        return "dashscope"
    if hostname.endswith(".siliconflow.cn"):
        return "siliconflow"
    return hostname


def _record_turn_metric(
    persistence: StreamPersistence | None,
    *,
    run_id: str | None,
    workflow_id: str,
    stage_id: str,
    model_name: str,
    provider: str,
    status: str,
    error_code: str | None,
    duration_ms: int,
    input_chars: int,
    output_chars: int,
    contract_retry_count: int = 0,
    actual_token_count: int | None = None,
    diagnostic: ErrorDiagnostic | None = None,
) -> None:
    if persistence is None or run_id is None:
        return
    record_metric = getattr(persistence, "record_turn_metric", None)
    if record_metric is None:
        return
    record_metric(
        run_id=run_id,
        workflow_id=workflow_id,
        stage_id=stage_id,
        model_name=model_name,
        provider=provider,
        status=status,
        error_code=error_code,
        duration_ms=duration_ms,
        input_chars=input_chars,
        output_chars=output_chars,
        estimated_tokens=(
            actual_token_count
            if actual_token_count is not None and actual_token_count >= 0
            else _estimated_tokens(input_chars, output_chars)
        ),
        contract_retry_count=contract_retry_count,
        diagnostic=_error_diagnostic_payload(diagnostic),
    )


def stream_agent_run_events(
    agent_request: AgentRunStreamRequest,
    *,
    api_key: str,
    base_url: str | None,
    model_name: str,
    persistence: StreamPersistence | None = None,
) -> Iterator[SseEvent]:
    started_at = perf_counter()
    run_id = None
    input_chars = len(agent_request.prompt)
    output_chars = 0
    provider = infer_provider_name(base_url)

    def duration_ms() -> int:
        return max(0, int((perf_counter() - started_at) * 1000))

    def record_metric(
        status: str,
        error_code: str | None = None,
        *,
        contract_retry_count: int = 0,
        actual_token_count: int | None = None,
        diagnostic: ErrorDiagnostic | None = None,
    ) -> None:
        _record_turn_metric(
            persistence,
            run_id=run_id,
            workflow_id=agent_request.workflow_id,
            stage_id=agent_request.stage_id,
            model_name=model_name,
            provider=provider,
            status=status,
            error_code=error_code,
            duration_ms=duration_ms(),
            input_chars=input_chars,
            output_chars=output_chars,
            contract_retry_count=contract_retry_count,
            actual_token_count=actual_token_count,
            diagnostic=diagnostic,
        )

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
        runtime_prompt = agent_request.prompt
        context_warnings = []
        if persistence is not None:
            run_id = persistence.ensure_run(agent_request, model_name=model_name)
            runtime_prompt, context_warnings = persistence.build_runtime_context(
                run_id,
                agent_request.prompt,
            )
            persistence.append_user_message(run_id, agent_request.prompt)
        yield RunStartedEvent(
            run_id=run_id,
            warnings=context_warnings or None,
        )
        final_output = None
        for output in runtime.stream_turn(
            runtime_prompt,
            workflow_id=agent_request.workflow_id,
            current_stage_id=agent_request.stage_id,
        ):
            if isinstance(output, AgentTurnOutput):
                output = apply_stage_readiness_gate(
                    output,
                    workflow_id=agent_request.workflow_id,
                    current_stage_id=agent_request.stage_id,
                )
                yield AgentTurnDeltaEvent(
                    output=AgentTurnDeltaOutput.model_validate(
                        output.model_dump(mode="json")
                    )
                )
                final_output = output
            else:
                yield AgentTurnDeltaEvent(output=output)
        if final_output is not None:
            if persistence is not None and run_id is not None:
                persistence.append_assistant_message(run_id, final_output.chat)
                artifact_update = final_output.artifact_update
                if artifact_update.type == "replace" and artifact_update.markdown:
                    persistence.record_artifact_version(
                        run_id,
                        agent_request.stage_id,
                        artifact_update.markdown,
                        artifact_data=final_output.artifact_data,
                    )
                    output_chars = len(final_output.chat) + len(
                        artifact_update.markdown
                    )
                else:
                    output_chars = len(final_output.chat)
                runtime_token_usage = getattr(runtime, "last_token_usage", None)
                record_metric(
                    "success",
                    actual_token_count=(
                        runtime_token_usage
                        if isinstance(runtime_token_usage, int)
                        else None
                    ),
                )
            yield AgentTurnEvent(output=final_output)
    except ContractValidationError as e:
        diagnostic = _build_error_diagnostic(
            code="CONTRACT_VALIDATION_FAILED",
            error=e,
            workflow_id=agent_request.workflow_id,
            stage_id=agent_request.stage_id,
        )
        record_metric("error", "CONTRACT_VALIDATION_FAILED", diagnostic=diagnostic)
        yield ErrorEvent(
            code="CONTRACT_VALIDATION_FAILED",
            message=str(e),
            diagnostic=diagnostic,
        )
    except ValidationError as e:
        diagnostic = _build_error_diagnostic(
            code="SCHEMA_VALIDATION_FAILED",
            error=e,
            workflow_id=agent_request.workflow_id,
            stage_id=agent_request.stage_id,
        )
        record_metric(
            "error",
            "SCHEMA_VALIDATION_FAILED",
            contract_retry_count=extract_contract_retry_count(e),
            diagnostic=diagnostic,
        )
        yield ErrorEvent(
            code="SCHEMA_VALIDATION_FAILED",
            message=format_schema_validation_error_message(e),
            diagnostic=diagnostic,
        )
    except AgentRuntimeSchemaError as e:
        diagnostic = _build_error_diagnostic(
            code="SCHEMA_VALIDATION_FAILED",
            error=e,
            workflow_id=agent_request.workflow_id,
            stage_id=agent_request.stage_id,
        )
        record_metric(
            "error",
            "SCHEMA_VALIDATION_FAILED",
            contract_retry_count=extract_contract_retry_count(e),
            diagnostic=diagnostic,
        )
        yield ErrorEvent(
            code="SCHEMA_VALIDATION_FAILED",
            message=format_schema_validation_error_message(e),
            diagnostic=diagnostic,
        )
    except PYDANTIC_AI_SCHEMA_ERRORS as e:
        diagnostic = _build_error_diagnostic(
            code="SCHEMA_VALIDATION_FAILED",
            error=e,
            workflow_id=agent_request.workflow_id,
            stage_id=agent_request.stage_id,
        )
        record_metric(
            "error",
            "SCHEMA_VALIDATION_FAILED",
            contract_retry_count=extract_contract_retry_count(e),
            diagnostic=diagnostic,
        )
        yield ErrorEvent(
            code="SCHEMA_VALIDATION_FAILED",
            message=format_schema_validation_error_message(e),
            diagnostic=diagnostic,
        )
    except RequestValidationError as e:
        diagnostic = _build_error_diagnostic(
            code="REQUEST_VALIDATION_FAILED",
            error=e,
            workflow_id=agent_request.workflow_id,
            stage_id=agent_request.stage_id,
        )
        record_metric("error", "REQUEST_VALIDATION_FAILED", diagnostic=diagnostic)
        yield ErrorEvent(
            code="REQUEST_VALIDATION_FAILED",
            message=str(e),
            diagnostic=diagnostic,
        )
    except ValueError as e:
        diagnostic = _build_error_diagnostic(
            code="REQUEST_VALIDATION_FAILED",
            error=e,
            workflow_id=agent_request.workflow_id,
            stage_id=agent_request.stage_id,
        )
        record_metric("error", "REQUEST_VALIDATION_FAILED", diagnostic=diagnostic)
        yield ErrorEvent(
            code="REQUEST_VALIDATION_FAILED",
            message=str(e),
            diagnostic=diagnostic,
        )
    except AgentRuntimeDependencyError as e:
        diagnostic = _build_error_diagnostic(
            code="AGENT_RUNTIME_UNAVAILABLE",
            error=e,
            workflow_id=agent_request.workflow_id,
            stage_id=agent_request.stage_id,
        )
        record_metric("error", "AGENT_RUNTIME_UNAVAILABLE", diagnostic=diagnostic)
        yield ErrorEvent(
            code="AGENT_RUNTIME_UNAVAILABLE",
            message=str(e),
            diagnostic=diagnostic,
        )
    except AgentRuntimeModelError as e:
        diagnostic = _build_error_diagnostic(
            code="LLM_ERROR",
            error=e,
            workflow_id=agent_request.workflow_id,
            stage_id=agent_request.stage_id,
        )
        record_metric("error", "LLM_ERROR", diagnostic=diagnostic)
        yield ErrorEvent(
            code="LLM_ERROR",
            message=str(e),
            diagnostic=diagnostic,
        )
    except (AuthenticationError, RateLimitError, APIError) as e:
        diagnostic = _build_error_diagnostic(
            code="LLM_ERROR",
            error=e,
            workflow_id=agent_request.workflow_id,
            stage_id=agent_request.stage_id,
        )
        record_metric("error", "LLM_ERROR", diagnostic=diagnostic)
        yield ErrorEvent(
            code="LLM_ERROR",
            message=str(e),
            diagnostic=diagnostic,
        )
