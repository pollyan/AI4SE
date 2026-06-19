from unittest.mock import MagicMock, patch

from openai import APIError, AuthenticationError, RateLimitError
import httpx
from agent_contracts import AgentTurnOutput, ContractValidationError
from agent_runtime import AgentRuntimeModelError, AgentRuntimeSchemaError
from request_schemas import AgentRunStreamRequest
from sse_schemas import (
    AgentTurnDeltaEvent,
    AgentTurnDeltaOutput,
    AgentTurnEvent,
    ErrorEvent,
    RunStartedEvent,
)
from stream_services import stream_agent_run_events


VALID_CLARIFY_ARTIFACT = """# 需求分析文档

## 1. 被测系统与边界
内容

## 2. 系统交互与核心链路
内容

## 3. 待澄清与阻断性问题
内容

## 4. 隐式需求与非功能性考量
内容"""


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_yields_started_delta_and_final_events(
    mock_build_runtime: MagicMock,
) -> None:
    partial = AgentTurnOutput.model_validate({
        "chat": "正在梳理需求。",
        "artifact_update": {
            "type": "replace",
            "markdown": VALID_CLARIFY_ARTIFACT,
        },
        "stage_action": None,
        "warnings": [],
    })
    final = AgentTurnOutput.model_validate({
        "chat": "已更新右侧需求分析文档，请确认。",
        "artifact_update": {
            "type": "replace",
            "markdown": VALID_CLARIFY_ARTIFACT,
        },
        "stage_action": None,
        "warnings": [],
    })
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([partial, final])
    mock_build_runtime.return_value = runtime
    request = AgentRunStreamRequest.model_validate({
        "prompt": "用户需求",
        "systemPrompt": "你是 Lisa。",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
    })

    events = list(stream_agent_run_events(
        request,
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
    ))

    assert events == [
        RunStartedEvent(),
        AgentTurnDeltaEvent(output=AgentTurnDeltaOutput.model_validate(
            partial.model_dump(mode="json")
        )),
        AgentTurnDeltaEvent(output=AgentTurnDeltaOutput.model_validate(
            final.model_dump(mode="json")
        )),
        AgentTurnEvent(output=final),
    ]
    runtime_kwargs = mock_build_runtime.call_args.kwargs
    assert runtime_kwargs["api_key"] == "test-api-key"
    assert runtime_kwargs["base_url"] == "https://api.test.com/v1"
    assert runtime_kwargs["model_name"] == "test-model"
    assert "你是 Lisa。" in runtime_kwargs["system_prompt"]
    assert "artifact_update.type 必须为 replace" in (
        runtime_kwargs["system_prompt"]
    )
    assert "chat 只允许返回给用户看的自然工作对话" in (
        runtime_kwargs["system_prompt"]
    )
    assert "前端显示确认控件" in (
        runtime_kwargs["system_prompt"]
    )
    assert "## 1. 被测系统与边界" in runtime_kwargs["system_prompt"]
    runtime.stream_turn.assert_called_once_with(
        "用户需求",
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_yields_started_and_final_without_delta_for_single_output(
    mock_build_runtime: MagicMock,
) -> None:
    final = AgentTurnOutput.model_validate({
        "chat": "已更新右侧需求分析文档，请确认。",
        "artifact_update": {
            "type": "replace",
            "markdown": VALID_CLARIFY_ARTIFACT,
        },
        "stage_action": None,
        "warnings": [],
    })
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([final])
    mock_build_runtime.return_value = runtime

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
    ))

    assert events == [
        RunStartedEvent(),
        AgentTurnDeltaEvent(output=AgentTurnDeltaOutput.model_validate(
            final.model_dump(mode="json")
        )),
        AgentTurnEvent(output=final),
    ]


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_maps_pydantic_ai_output_failure_to_error_event(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeSchemaError(
        "Exceeded maximum output retries (1)"
    )
    mock_build_runtime.return_value = runtime
    request = AgentRunStreamRequest.model_validate({
        "prompt": "用户需求",
        "systemPrompt": "你是 Lisa。",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
    })

    events = list(stream_agent_run_events(
        request,
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
    ))

    assert events == [
        RunStartedEvent(),
        ErrorEvent(
            code="SCHEMA_VALIDATION_FAILED",
            message=(
                "模型连续生成的结构化结果未通过校验。请重试本轮操作；"
                "如果多次失败，请补充更明确的需求或阶段确认信息。"
            ),
        )
    ]


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_maps_raw_pydantic_ai_schema_error_to_error_event(
    mock_build_runtime: MagicMock,
    monkeypatch,
) -> None:
    class RawSchemaError(RuntimeError):
        pass

    monkeypatch.setattr(
        "stream_services.PYDANTIC_AI_SCHEMA_ERRORS",
        (RawSchemaError,),
        raising=False,
    )
    runtime = MagicMock()
    runtime.stream_turn.side_effect = RawSchemaError(
        "Exceeded maximum output retries (3)"
    )
    mock_build_runtime.return_value = runtime

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
    ))

    assert events == [
        RunStartedEvent(),
        ErrorEvent(
            code="SCHEMA_VALIDATION_FAILED",
            message=(
                "模型连续生成的结构化结果未通过校验。请重试本轮操作；"
                "如果多次失败，请补充更明确的需求或阶段确认信息。"
            ),
        )
    ]


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_maps_contract_failure_to_error_event(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = ContractValidationError(
        "chat must not contain artifact markdown"
    )
    mock_build_runtime.return_value = runtime
    request = AgentRunStreamRequest.model_validate({
        "prompt": "用户需求",
        "systemPrompt": "你是 Lisa。",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
    })

    events = list(stream_agent_run_events(
        request,
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
    ))

    assert events == [
        RunStartedEvent(),
        ErrorEvent(
            code="CONTRACT_VALIDATION_FAILED",
            message="chat must not contain artifact markdown",
        )
    ]


def _request() -> AgentRunStreamRequest:
    return AgentRunStreamRequest.model_validate({
        "prompt": "用户需求",
        "systemPrompt": "你是 Lisa。",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
    })


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_validates_workflow_stage_before_building_runtime(
    mock_build_runtime: MagicMock,
) -> None:
    requests = [
        (
            AgentRunStreamRequest.model_validate({
                "prompt": "用户需求",
                "systemPrompt": "你是 Lisa。",
                "workflowId": "UNKNOWN_WORKFLOW",
                "stageId": "CLARIFY",
            }),
            "未知 workflowId: UNKNOWN_WORKFLOW",
        ),
        (
            AgentRunStreamRequest.model_validate({
                "prompt": "用户需求",
                "systemPrompt": "你是 Lisa。",
                "workflowId": "TEST_DESIGN",
                "stageId": "REPORT",
            }),
            "workflowId 与 stageId 不匹配: TEST_DESIGN/REPORT",
        ),
    ]

    for request, message in requests:
        events = list(stream_agent_run_events(
            request,
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        ))

        assert events == [
            ErrorEvent(
                code="REQUEST_VALIDATION_FAILED",
                message=message,
            )
        ]
    mock_build_runtime.assert_not_called()


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_maps_model_http_error_to_llm_error_event(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeModelError(
        "503: upstream unavailable"
    )
    mock_build_runtime.return_value = runtime

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
    ))

    assert len(events) == 2
    assert events[0] == RunStartedEvent()
    assert events[1].code == "LLM_ERROR"
    assert "503" in events[1].message


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_maps_model_api_error_to_llm_error_event(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeModelError("provider API failed")
    mock_build_runtime.return_value = runtime

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
    ))

    assert events == [
        RunStartedEvent(),
        ErrorEvent(
            code="LLM_ERROR",
            message="provider API failed",
        )
    ]


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_maps_openai_auth_error_to_llm_error_event(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    response = httpx.Response(
        401,
        request=httpx.Request("POST", "https://api.test.com/v1/chat"),
    )
    runtime.stream_turn.side_effect = AuthenticationError(
        "invalid api key",
        response=response,
        body={"error": "invalid api key"},
    )
    mock_build_runtime.return_value = runtime

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
    ))

    assert len(events) == 2
    assert events[0] == RunStartedEvent()
    assert events[1].code == "LLM_ERROR"
    assert "invalid api key" in events[1].message


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_maps_openai_rate_limit_error_to_llm_error_event(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://api.test.com/v1/chat"),
    )
    runtime.stream_turn.side_effect = RateLimitError(
        "rate limit exceeded",
        response=response,
        body={"error": "rate limit exceeded"},
    )
    mock_build_runtime.return_value = runtime

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
    ))

    assert len(events) == 2
    assert events[0] == RunStartedEvent()
    assert events[1].code == "LLM_ERROR"
    assert "rate limit exceeded" in events[1].message


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_maps_openai_api_error_to_llm_error_event(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    request = httpx.Request("POST", "https://api.test.com/v1/chat")
    runtime.stream_turn.side_effect = APIError(
        "connection failed",
        request=request,
        body={"error": "connection failed"},
    )
    mock_build_runtime.return_value = runtime

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
    ))

    assert len(events) == 2
    assert events[0] == RunStartedEvent()
    assert events[1].code == "LLM_ERROR"
    assert "connection failed" in events[1].message
