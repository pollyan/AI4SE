import json
from unittest.mock import MagicMock, patch

from openai import APIError, AuthenticationError, RateLimitError
import httpx
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic_core import PydanticCustomError
from pydantic_ai.exceptions import UnexpectedModelBehavior
import pytest
from agent_contracts import AgentTurnOutput, ContractValidationError
from artifact_data_renderers import DeliveryArtifactData
from artifact_data_value_schema import ValueDiscoveryJourneyArtifactData
from agent_runtime import (
    AgentRuntimeModelError,
    AgentRuntimeSchemaError,
    RawJsonStreamTerminationError,
)
from request_schemas import AgentRunStreamRequest
from sse_schemas import (
    AgentRetryEvent,
    AgentRetrySignal,
    AgentTurnDeltaEvent,
    AgentTurnDeltaOutput,
    AgentTurnEvent,
    ErrorDiagnostic,
    ErrorEvent,
    RunStartedEvent,
)
from sse_response import build_sse_response
from stream_services import (
    CONTRACT_VALIDATION_PUBLIC_REASON,
    PROVIDER_AUTH_PUBLIC_REASON,
    PROVIDER_CONNECTION_PUBLIC_REASON,
    PROVIDER_ERROR_PUBLIC_REASON,
    PROVIDER_RATE_LIMIT_PUBLIC_REASON,
    REQUEST_VALIDATION_PUBLIC_REASON,
    SCHEMA_RETRY_EXHAUSTED_MESSAGE,
    STRUCTURED_OUTPUT_PUBLIC_REASON,
    VISUAL_VALIDATION_PUBLIC_REASON,
    stream_agent_run_events,
)
from run_persistence import (
    TurnPersistenceError,
    TurnRequestClaim,
    TurnRequestIdentityConflictError,
)

VALID_ARTIFACT_DATA = {
    "document_info": {
        "artifact_name": "测试需求分析与澄清基线",
    },
    "stage_gate": {
        "status": "需要用户补充",
        "blocking": True,
    },
}


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


def _diagnostic(
    *,
    phase: str,
    field_path: str,
    validator: str,
    retryable: bool,
    public_reason: str,
    workflow_id: str = "TEST_DESIGN",
    stage_id: str = "CLARIFY",
) -> ErrorDiagnostic:
    return ErrorDiagnostic(
        phase=phase,
        workflowId=workflow_id,
        stageId=stage_id,
        fieldPath=field_path,
        validator=validator,
        retryable=retryable,
        publicReason=public_reason,
    )


class FakePersistence:
    def __init__(self) -> None:
        self.calls = []
        self.context_warnings = []
        self.turn_request_claim = TurnRequestClaim(
            state="new",
            owner_token="owner-token-001",
            user_message_sequence=1,
        )

    def ensure_run(self, agent_request, *, model_name: str) -> str:
        self.calls.append(
            (
                "ensure_run",
                agent_request.workflow_id,
                agent_request.stage_id,
                agent_request.run_id,
                model_name,
            )
        )
        return "run-123"

    def claim_turn_request(
        self,
        run_id: str,
        agent_request,
        *,
        model_name: str,
    ) -> TurnRequestClaim:
        self.calls.append(("claim_turn_request", run_id, agent_request.request_id))
        return self.turn_request_claim

    def fail_turn_request(
        self,
        run_id: str,
        *,
        request_id: str,
        owner_token: str,
        terminal_event: dict,
    ) -> None:
        self.calls.append(
            (
                "fail_turn_request",
                run_id,
                request_id,
                terminal_event,
                owner_token,
            )
        )

    def abandon_turn_request(
        self,
        run_id: str,
        *,
        request_id: str,
        owner_token: str,
    ) -> None:
        self.calls.append(("abandon_turn_request", run_id, request_id, owner_token))

    def complete_agent_run_turn(
        self,
        run_id: str,
        *,
        stage_id: str,
        assistant_content: str,
        artifact_content: str | None,
        artifact_data=None,
        metric: dict,
        request_id: str | None = None,
        owner_token: str | None = None,
        terminal_event: dict | None = None,
    ) -> None:
        self.calls.append(
            (
                "complete_agent_run_turn",
                run_id,
                stage_id,
                assistant_content,
                artifact_content,
                artifact_data,
                request_id,
                terminal_event,
                metric,
                owner_token,
            )
        )

    def build_runtime_context(
        self,
        run_id: str,
        current_prompt: str,
        *,
        request_id: str,
    ):
        self.calls.append(("build_runtime_context", run_id, current_prompt, request_id))
        return f"服务端上下文\n\n[用户]\n{current_prompt}", self.context_warnings

    def record_turn_metric(self, **kwargs) -> None:
        self.calls.append(("record_turn_metric", kwargs))


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_yields_started_delta_and_final_events(
    mock_build_runtime: MagicMock,
) -> None:
    partial = AgentTurnDeltaOutput.model_validate(
        {
            "chat": "我正在梳理当前登录需求的业务边界。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "stage_action": None,
            "warnings": [],
        }
    )
    final = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧需求分析文档，请确认。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "artifact_data": VALID_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        }
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([partial, final])
    mock_build_runtime.return_value = runtime
    request = AgentRunStreamRequest.model_validate(
        {
            "prompt": "用户需求",
            "systemPrompt": "你是 Lisa。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "requestId": "stream-partial-001",
        }
    )

    events = list(
        stream_agent_run_events(
            request,
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    assert events[0] == RunStartedEvent()
    assert events[-1] == AgentTurnEvent(output=final)
    delta_events = [event for event in events if isinstance(event, AgentTurnDeltaEvent)]
    first_chat_index = next(
        index
        for index, event in enumerate(delta_events)
        if event.output.chat == "我正在梳理当前登录需求的业务边界。"
    )
    first_artifact_index = next(
        index
        for index, event in enumerate(delta_events)
        if event.output.artifact_update is not None
    )
    assert first_chat_index < first_artifact_index
    assert delta_events[first_chat_index].output.artifact_update is None
    runtime_kwargs = mock_build_runtime.call_args.kwargs
    assert runtime_kwargs["api_key"] == "test-api-key"
    assert runtime_kwargs["base_url"] == "https://api.test.com/v1"
    assert runtime_kwargs["model_name"] == "test-model"
    assert "你是 Lisa。" in runtime_kwargs["system_prompt"]
    assert "artifact_update.type 必须为 replace" in runtime_kwargs["system_prompt"]
    assert "chat 只允许返回给用户看的自然工作对话" in runtime_kwargs["system_prompt"]
    assert "前端显示确认控件" in runtime_kwargs["system_prompt"]
    assert "## 1. 需求事实清单" in runtime_kwargs["system_prompt"]
    runtime.stream_turn.assert_called_once_with(
        "用户需求",
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_exposes_retry_boundary_and_reapplies_chat_first(
    mock_build_runtime: MagicMock,
) -> None:
    final = AgentTurnOutput.model_validate(
        {
            "chat": "我已修正数据并完成右侧需求分析文档。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "artifact_data": VALID_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        }
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter(
        [
            AgentTurnDeltaOutput(chat="我正在核对第一次尝试的需求边界。"),
            AgentTurnDeltaOutput.model_validate(
                {
                    "artifact_update": {
                        "type": "replace",
                        "markdown": "# 第一次尝试\n\n## 需求事实\n\n待修正",
                    }
                }
            ),
            AgentRetrySignal(attemptIndex=2),
            AgentTurnDeltaOutput.model_validate(
                {
                    "artifact_update": {
                        "type": "replace",
                        "markdown": "# 第二次尝试",
                    }
                }
            ),
            AgentTurnDeltaOutput(chat="我已定位统计问题，正在重新形成结论。"),
            final,
        ]
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()
    request = AgentRunStreamRequest.model_validate(
        {
            "prompt": "用户需求",
            "systemPrompt": "你是 Lisa。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "requestId": "stream-retry-001",
        }
    )

    events = list(
        stream_agent_run_events(
            request,
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    retry_index = next(
        index
        for index, event in enumerate(events)
        if isinstance(event, AgentRetryEvent)
    )
    post_retry_deltas = [
        event
        for event in events[retry_index + 1 :]
        if isinstance(event, AgentTurnDeltaEvent)
    ]
    assert events[retry_index] == AgentRetryEvent(attemptIndex=2)
    assert post_retry_deltas[0].output.chat == "我已定位统计问题，正在重新形成结论。"
    assert post_retry_deltas[0].output.artifact_update is None
    assert post_retry_deltas[1].output.artifact_update is not None
    assert post_retry_deltas[1].output.artifact_update.markdown == "# 第二次尝试"
    complete_call = next(
        call for call in persistence.calls if call[0] == "complete_agent_run_turn"
    )
    assert complete_call[8]["contract_retry_count"] == 1


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_records_observed_retry_before_terminal_error(
    mock_build_runtime: MagicMock,
) -> None:
    def retry_then_error():
        yield AgentRetrySignal(attemptIndex=2)
        raise AgentRuntimeSchemaError("final structured output is invalid")

    runtime = MagicMock()
    runtime.stream_turn.return_value = retry_then_error()
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert any(isinstance(event, AgentRetryEvent) for event in events)
    assert isinstance(events[-1], ErrorEvent)
    metric_call = next(
        call for call in persistence.calls if call[0] == "record_turn_metric"
    )
    assert metric_call[1]["contract_retry_count"] == 1


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_prefers_observed_retry_over_exhaustion_text(
    mock_build_runtime: MagicMock,
) -> None:
    def retry_then_error():
        yield AgentRetrySignal(attemptIndex=2)
        raise UnexpectedModelBehavior("Exceeded maximum output retries (3)")

    runtime = MagicMock()
    runtime.stream_turn.return_value = retry_then_error()
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="deepseek-v4-flash",
            persistence=persistence,
        )
    )

    metric_call = next(
        call for call in persistence.calls if call[0] == "record_turn_metric"
    )
    assert metric_call[1]["contract_retry_count"] == 1


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_ignores_forged_untrusted_retry_count(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeSchemaError(
        "Exceeded maximum output retries (999999999)"
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="deepseek-v4-flash",
            persistence=persistence,
        )
    )

    metric_call = next(
        call for call in persistence.calls if call[0] == "record_turn_metric"
    )
    assert metric_call[1]["contract_retry_count"] == 0
    assert events[-1].message == STRUCTURED_OUTPUT_PUBLIC_REASON
    assert events[-1].diagnostic.validator == "structured_output"


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_clamps_trusted_retry_count_to_runtime_limit(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = UnexpectedModelBehavior(
        "Exceeded maximum output retries (999999999)"
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="deepseek-v4-flash",
            persistence=persistence,
        )
    )

    metric_call = next(
        call for call in persistence.calls if call[0] == "record_turn_metric"
    )
    assert metric_call[1]["contract_retry_count"] == 3


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_preserves_user_authorized_assumption_stage_action(
    mock_build_runtime: MagicMock,
) -> None:
    authorized_default_artifact = VALID_CLARIFY_ARTIFACT.replace(
        "| Q-001 | 锁定策略是否存在 | P1 | 非阻断 | 异常登录 | 暂按 5 次失败锁定 | 产品 | 待确认 |",
        "| Q-001 | 密码错误锁定阈值 | P1 | 阻断 | 异常登录 | 密码错误 3 次后锁定 12 小时 | 用户授权默认场景 | 已假设 |",
    )
    authorized_default_data = {
        "clarification_questions": [
            {
                "question_id": "Q-001",
                "question": "密码错误锁定阈值",
                "priority": "P1",
                "blocking": "阻断",
                "impact": "异常登录",
                "assumption": "密码错误 3 次后锁定 12 小时",
                "owner": "用户授权默认场景",
                "status": "已假设",
            }
        ]
    }
    final = AgentTurnOutput.model_validate(
        {
            "chat": "已按授权默认场景更新需求分析文档，请确认进入策略制定。",
            "artifact_update": {
                "type": "replace",
                "markdown": authorized_default_artifact,
            },
            "artifact_data": authorized_default_data,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "STRATEGY",
            },
            "warnings": [],
        }
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([final])
    mock_build_runtime.return_value = runtime
    request = AgentRunStreamRequest.model_validate(
        {
            "prompt": "我在测试当前工作流，帮我假定一个场景就好",
            "systemPrompt": "你是 Lisa。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "requestId": "stream-default-001",
        }
    )

    events = list(
        stream_agent_run_events(
            request,
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    chat_delta = events[1]
    action_delta = next(
        event
        for event in events
        if isinstance(event, AgentTurnDeltaEvent)
        and event.output.stage_action is not None
    )
    final_event = events[-1]
    assert isinstance(chat_delta, AgentTurnDeltaEvent)
    assert isinstance(final_event, AgentTurnEvent)
    assert chat_delta.output.chat == final.chat
    assert chat_delta.output.stage_action is None
    assert action_delta.output.stage_action == final.stage_action
    assert final_event.output.stage_action == final.stage_action
    assert "stage_readiness_blocked" not in action_delta.output.warnings
    assert "stage_readiness_blocked" not in final_event.output.warnings
    assert "阶段成熟度门禁判断" not in final_event.output.chat


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_records_turn_through_persistence_adapter(
    mock_build_runtime: MagicMock,
) -> None:
    final = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧需求分析文档，请确认。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "artifact_data": VALID_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        }
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([final])
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()
    request = AgentRunStreamRequest.model_validate(
        {
            "prompt": "用户需求",
            "systemPrompt": "你是 Lisa。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "requestId": "stream-persistence-001",
        }
    )

    events = list(
        stream_agent_run_events(
            request,
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert events[0] == RunStartedEvent(run_id="run-123")
    assert events[-1] == AgentTurnEvent(output=final)
    assert persistence.calls[:3] == [
        ("ensure_run", "TEST_DESIGN", "CLARIFY", None, "test-model"),
        ("claim_turn_request", "run-123", "stream-persistence-001"),
        (
            "build_runtime_context",
            "run-123",
            "用户需求",
            "stream-persistence-001",
        ),
    ]
    request_claim = persistence.calls[1]
    assert request_claim[:2] == ("claim_turn_request", "run-123")
    assert request_claim[2]
    completed_turn = persistence.calls[3]
    assert completed_turn[:6] == (
        "complete_agent_run_turn",
        "run-123",
        "CLARIFY",
        "已更新右侧需求分析文档，请确认。",
        VALID_CLARIFY_ARTIFACT,
        VALID_ARTIFACT_DATA,
    )
    assert completed_turn[6] == request_claim[2]
    assert completed_turn[7] == {
        "type": "agent_turn",
        "output": final.model_dump(mode="json"),
    }
    metric = completed_turn[8]
    assert completed_turn[9] == "owner-token-001"
    assert metric["workflow_id"] == "TEST_DESIGN"
    assert metric["stage_id"] == "CLARIFY"
    assert metric["model_name"] == "test-model"
    assert metric["provider"] == "api.test.com"
    assert metric["status"] == "success"
    assert metric["error_code"] is None
    assert metric["input_chars"] == len("用户需求")
    assert metric["output_chars"] == (
        len("已更新右侧需求分析文档，请确认。") + len(VALID_CLARIFY_ARTIFACT)
    )
    assert metric["estimated_tokens"] >= 1
    assert metric["duration_ms"] >= 0
    assert metric["contract_retry_count"] == 0


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_replays_completed_request_without_model_invocation(
    mock_build_runtime: MagicMock,
) -> None:
    final = AgentTurnOutput.model_validate(
        {
            "chat": "已完成登录需求分析。",
            "artifact_update": {"type": "none"},
            "stage_action": None,
            "warnings": [],
        }
    )
    persistence = FakePersistence()
    persistence.turn_request_claim = TurnRequestClaim(
        state="completed",
        terminal_event={
            "type": "agent_turn",
            "output": final.model_dump(mode="json"),
        },
    )

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert events == [
        RunStartedEvent(run_id="run-123"),
        AgentTurnDeltaEvent(output=AgentTurnDeltaOutput(chat=final.chat)),
        AgentTurnEvent(output=final),
    ]
    mock_build_runtime.assert_not_called()
    assert [call[0] for call in persistence.calls] == [
        "ensure_run",
        "claim_turn_request",
    ]


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_rejects_active_request_without_reading_context(
    mock_build_runtime: MagicMock,
) -> None:
    persistence = FakePersistence()
    persistence.turn_request_claim = TurnRequestClaim(state="active")

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert len(events) == 1
    assert events[0].code == "REQUEST_IN_PROGRESS"
    assert [call[0] for call in persistence.calls] == [
        "ensure_run",
        "claim_turn_request",
    ]
    mock_build_runtime.assert_not_called()


@pytest.mark.parametrize("failure_point", ["ensure_run", "claim_turn_request"])
@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_projects_pre_run_persistence_failure(
    mock_build_runtime: MagicMock,
    failure_point: str,
) -> None:
    canary = f"PRE-RUN-SQL-SECRET-{failure_point}-CANARY"
    persistence = FakePersistence()

    def fail_before_run(*args, **kwargs):
        raise TurnPersistenceError(canary)

    setattr(persistence, failure_point, fail_before_run)

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert len(events) == 1
    assert events[0].code == "PERSISTENCE_FAILED"
    assert events[0].diagnostic.phase == "persistence"
    assert events[0].diagnostic.field_path == "run_outcome"
    assert events[0].diagnostic.validator == "atomic_commit"
    assert canary not in events[0].model_dump_json()
    assert "fail_turn_request" not in [call[0] for call in persistence.calls]
    mock_build_runtime.assert_not_called()


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_terminalizes_owned_context_failure_without_leaking(
    mock_build_runtime: MagicMock,
) -> None:
    canary = "sk-context-read-failure-canary"
    persistence = FakePersistence()

    def fail_context(*args, **kwargs):
        raise TurnPersistenceError(canary)

    persistence.build_runtime_context = fail_context

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert len(events) == 1
    assert events[0].code == "PERSISTENCE_FAILED"
    failed_turn = next(
        call for call in persistence.calls if call[0] == "fail_turn_request"
    )
    assert failed_turn[2] == "stream-default-request-001"
    assert failed_turn[4] == "owner-token-001"
    assert "abandon_turn_request" not in [call[0] for call in persistence.calls]
    assert canary not in json.dumps(
        [events[0].model_dump(mode="json"), failed_turn],
        ensure_ascii=False,
    )
    mock_build_runtime.assert_not_called()


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_reports_request_identity_conflict_without_mutating_claim(
    mock_build_runtime: MagicMock,
) -> None:
    persistence = FakePersistence()

    def reject_identity_reuse(*args, **kwargs):
        raise TurnRequestIdentityConflictError("requestId identity conflict")

    persistence.claim_turn_request = reject_identity_reuse

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert len(events) == 1
    assert events[0].code == "REQUEST_IDENTITY_CONFLICT"
    assert events[0].diagnostic.phase == "persistence"
    assert events[0].diagnostic.field_path == "request_id"
    assert events[0].diagnostic.validator == "immutable_request_identity"
    assert events[0].diagnostic.retryable is False
    assert "requestId" in events[0].message
    assert "fail_turn_request" not in [call[0] for call in persistence.calls]
    assert "build_runtime_context" not in [call[0] for call in persistence.calls]
    mock_build_runtime.assert_not_called()


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_releases_active_claim_when_consumer_closes(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter(
        [AgentTurnDeltaOutput(chat="正在分析登录需求。")]
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()
    request = _request()

    events = stream_agent_run_events(
        request,
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
        persistence=persistence,
    )

    assert next(events) == RunStartedEvent(run_id="run-123")
    events.close()

    assert (
        "abandon_turn_request",
        "run-123",
        request.request_id,
        "owner-token-001",
    ) in persistence.calls
    assert "complete_agent_run_turn" not in [call[0] for call in persistence.calls]
    assert "fail_turn_request" not in [call[0] for call in persistence.calls]


@patch("stream_services.build_pydantic_agent_runtime")
def test_sse_response_close_propagates_to_owned_agent_stream(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter(
        [AgentTurnDeltaOutput(chat="我正在分析登录需求的业务边界。")]
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()
    inner_events = stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
        persistence=persistence,
    )
    response = build_sse_response(inner_events)

    next(response.response)
    response.close()

    assert (
        "abandon_turn_request",
        "run-123",
        "stream-default-request-001",
        "owner-token-001",
    ) in persistence.calls


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_close_uses_bounded_lease_when_abandon_persistence_fails(
    mock_build_runtime: MagicMock,
    caplog,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter(
        [AgentTurnDeltaOutput(chat="我正在分析登录需求的业务边界。")]
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()
    persistence_canary = "OWNER-TOKEN-AND-SQL-PARAMETER-CANARY"

    def fail_abandon(*args, **kwargs) -> None:
        raise TurnPersistenceError(persistence_canary)

    persistence.abandon_turn_request = fail_abandon
    events = stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
        persistence=persistence,
    )

    next(events)
    events.close()

    assert "bounded lease reclaim" in caplog.text
    assert persistence_canary not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.parametrize(
    ("stored_code", "stored_validator", "expected_code"),
    [
        ("SCHEMA_VALIDATION_FAILED", "legacy-validator", "SCHEMA_VALIDATION_FAILED"),
        ("SECRET_LEGACY_CODE", "legacy-validator", "LLM_ERROR"),
        ("LLM_ERROR", {"nested": "legacy-validator"}, "LLM_ERROR"),
    ],
)
@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_sanitizes_legacy_failed_request_replay(
    mock_build_runtime: MagicMock,
    stored_code: str,
    stored_validator,
    expected_code: str,
) -> None:
    canary = "sk-qg020-legacy-replay-canary"
    persistence = FakePersistence()
    persistence.turn_request_claim = TurnRequestClaim(
        state="failed",
        terminal_event={
            "type": "error",
            "code": stored_code,
            "message": f"legacy provider output {canary}",
            "diagnostic": {
                "phase": canary,
                "workflowId": "TEST_DESIGN",
                "stageId": "CLARIFY",
                "fieldPath": canary,
                "validator": stored_validator,
                "retryable": True,
                "publicReason": canary,
            },
        },
    )

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert events[0] == RunStartedEvent(run_id="run-123")
    assert isinstance(events[-1], ErrorEvent)
    assert events[-1].code == expected_code
    assert canary not in json.dumps(
        events[-1].model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
    )
    assert [call[0] for call in persistence.calls] == [
        "ensure_run",
        "claim_turn_request",
    ]
    mock_build_runtime.assert_not_called()


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_preserves_safe_auth_replay_semantics(
    mock_build_runtime: MagicMock,
) -> None:
    canary = "OpaqueLegacyAuthMessage987"
    persistence = FakePersistence()
    persistence.turn_request_claim = TurnRequestClaim(
        state="failed",
        terminal_event={
            "type": "error",
            "code": "LLM_ERROR",
            "message": canary,
            "diagnostic": {
                "phase": "provider",
                "workflowId": "TEST_DESIGN",
                "stageId": "CLARIFY",
                "fieldPath": "provider",
                "validator": "provider_authentication",
                "retryable": True,
                "publicReason": canary,
            },
        },
    )

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    error = events[-1]
    assert error.code == "LLM_ERROR"
    assert error.diagnostic.validator == "provider_authentication"
    assert error.diagnostic.retryable is False
    assert error.message == PROVIDER_AUTH_PUBLIC_REASON
    assert canary not in error.model_dump_json()
    mock_build_runtime.assert_not_called()


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_reports_atomic_persistence_failure_without_success_event(
    mock_build_runtime: MagicMock,
) -> None:
    final = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧需求分析文档，请确认。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "artifact_data": VALID_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        }
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([final])
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    def fail_completed_turn(*args, **kwargs) -> None:
        raise TurnPersistenceError("simulated database failure")

    persistence.complete_agent_run_turn = fail_completed_turn

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert len(events) == 2
    assert isinstance(events[0], RunStartedEvent)
    assert events[-1] == ErrorEvent(
        code="PERSISTENCE_FAILED",
        message="本轮结果未能安全保存，请重试。",
        diagnostic=_diagnostic(
            phase="persistence",
            field_path="run_outcome",
            validator="atomic_commit",
            retryable=True,
            public_reason=(
                "本轮结果未能安全保存，右侧产出物和历史版本均未作为成功结果提交。"
            ),
        ),
    )
    assert not any(isinstance(event, AgentTurnEvent) for event in events)
    assert "record_turn_metric" not in [call[0] for call in persistence.calls]


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_withholds_all_complete_snapshots_until_commit(
    mock_build_runtime: MagicMock,
) -> None:
    first_complete_snapshot = AgentTurnOutput.model_validate(
        {
            "chat": "第一份完整快照也不能提前作为成功结果发送。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "artifact_data": VALID_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        }
    )
    final = first_complete_snapshot.model_copy(
        update={"chat": "最终完整快照同样必须等待持久化。"}
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([first_complete_snapshot, final])
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    def fail_completed_turn(*args, **kwargs) -> None:
        raise TurnPersistenceError("simulated database failure")

    persistence.complete_agent_run_turn = fail_completed_turn

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert len(events) == 2
    assert isinstance(events[0], RunStartedEvent)
    assert isinstance(events[1], ErrorEvent)
    assert events[1].code == "PERSISTENCE_FAILED"
    assert not any(isinstance(event, AgentTurnDeltaEvent) for event in events)
    assert not any(isinstance(event, AgentTurnEvent) for event in events)


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_keeps_true_partials_but_withholds_final_delta_until_commit(
    mock_build_runtime: MagicMock,
) -> None:
    partial_chat = "正在梳理真实的流式片段。"
    partial_markdown = "# 处理中\n\n## 已识别事实\n\n- 登录需求"
    final_chat = "最终完整对话不应在持久化失败时发送。"
    final = AgentTurnOutput.model_validate(
        {
            "chat": final_chat,
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "artifact_data": VALID_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        }
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter(
        [
            AgentTurnDeltaOutput(chat=partial_chat),
            AgentTurnDeltaOutput.model_validate(
                {
                    "artifact_update": {
                        "type": "replace",
                        "markdown": partial_markdown,
                    }
                }
            ),
            AgentTurnDeltaOutput.model_validate(
                {
                    "artifact_update": {
                        "type": "replace",
                        "markdown": VALID_CLARIFY_ARTIFACT,
                    }
                }
            ),
            final,
        ]
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    def fail_completed_turn(*args, **kwargs) -> None:
        raise TurnPersistenceError("simulated database failure")

    persistence.complete_agent_run_turn = fail_completed_turn

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    deltas = [
        event.output for event in events if isinstance(event, AgentTurnDeltaEvent)
    ]
    assert any(delta.chat == partial_chat for delta in deltas)
    assert any(
        delta.artifact_update is not None
        and delta.artifact_update.markdown == partial_markdown
        for delta in deltas
    )
    assert all(delta.chat != final_chat for delta in deltas)
    assert all(
        delta.artifact_update is None
        or delta.artifact_update.markdown != VALID_CLARIFY_ARTIFACT
        for delta in deltas
    )
    assert isinstance(events[-1], ErrorEvent)
    assert events[-1].code == "PERSISTENCE_FAILED"
    assert not any(isinstance(event, AgentTurnEvent) for event in events)


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_does_not_flush_final_artifact_when_chat_arrives_later(
    mock_build_runtime: MagicMock,
) -> None:
    partial_chat = "正在分析真实需求，稍后给出最终结论。"
    final = AgentTurnOutput.model_validate(
        {
            "chat": "最终对话必须等待持久化成功。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "artifact_data": VALID_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        }
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter(
        [
            AgentTurnDeltaOutput.model_validate(
                {
                    "artifact_update": {
                        "type": "replace",
                        "markdown": VALID_CLARIFY_ARTIFACT,
                    }
                }
            ),
            AgentTurnDeltaOutput(chat=partial_chat),
            final,
        ]
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()
    persistence.complete_agent_run_turn = MagicMock(
        side_effect=TurnPersistenceError("simulated database failure")
    )

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    deltas = [
        event.output for event in events if isinstance(event, AgentTurnDeltaEvent)
    ]
    assert any(delta.chat == partial_chat for delta in deltas)
    assert all(
        delta.artifact_update is None
        or delta.artifact_update.markdown != VALID_CLARIFY_ARTIFACT
        for delta in deltas
    )
    assert isinstance(events[-1], ErrorEvent)
    assert events[-1].code == "PERSISTENCE_FAILED"


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_rejects_visual_failure_before_persistence(
    mock_build_runtime: MagicMock,
) -> None:
    invalid_visual_artifact = (
        VALID_CLARIFY_ARTIFACT + "\n\n```ai4se-visual\n" + "{ broken" + "\n```\n"
    )
    final = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧需求分析文档，请确认。",
            "artifact_update": {
                "type": "replace",
                "markdown": invalid_visual_artifact,
            },
            "artifact_data": VALID_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        }
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([final])
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert events == [
        RunStartedEvent(run_id="run-123"),
        ErrorEvent(
            code="VISUAL_VALIDATION_FAILED",
            message=VISUAL_VALIDATION_PUBLIC_REASON,
            diagnostic=_diagnostic(
                phase="visual_validation",
                field_path="artifact_update.markdown",
                validator="ai4se_visual_json",
                retryable=False,
                public_reason="产出物中的可视化内容未通过校验，右侧产出物已保持不变。",
            ),
        ),
    ]
    call_names = [call[0] for call in persistence.calls]
    assert "append_assistant_message" not in call_names
    assert "record_artifact_version" not in call_names
    assert not any(
        call[0] == "record_turn_metric" and call[1]["status"] == "success"
        for call in persistence.calls
    )
    error_metric = next(
        call for call in persistence.calls if call[0] == "record_turn_metric"
    )
    assert error_metric[0] == "record_turn_metric"
    assert error_metric[1]["status"] == "error"
    assert error_metric[1]["error_code"] == "VISUAL_VALIDATION_FAILED"


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_records_real_token_usage_when_runtime_exposes_it(
    mock_build_runtime: MagicMock,
) -> None:
    final = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧需求分析文档，请确认。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "stage_action": None,
            "warnings": [],
        }
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([final])
    runtime.last_token_usage = 321
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert events[-1] == AgentTurnEvent(output=final)
    assert persistence.calls[-1][0] == "complete_agent_run_turn"
    metric = persistence.calls[-1][8]
    assert metric["estimated_tokens"] == 321


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_records_error_turn_metric(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeModelError("provider API failed")
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    diagnostic = _diagnostic(
        phase="provider",
        field_path="provider",
        validator="provider_error",
        retryable=True,
        public_reason=PROVIDER_ERROR_PUBLIC_REASON,
    )
    assert events == [
        RunStartedEvent(run_id="run-123"),
        ErrorEvent(
            code="LLM_ERROR",
            message=PROVIDER_ERROR_PUBLIC_REASON,
            diagnostic=diagnostic,
        ),
    ]
    metric_call = next(
        call for call in persistence.calls if call[0] == "record_turn_metric"
    )
    metric = metric_call[1]
    assert metric_call[0] == "record_turn_metric"
    assert metric["run_id"] == "run-123"
    assert metric["workflow_id"] == "TEST_DESIGN"
    assert metric["stage_id"] == "CLARIFY"
    assert metric["model_name"] == "test-model"
    assert metric["provider"] == "api.test.com"
    assert metric["status"] == "error"
    assert metric["error_code"] == "LLM_ERROR"
    assert metric["input_chars"] == len("用户需求")
    assert metric["output_chars"] == 0
    assert metric["estimated_tokens"] >= 1
    assert metric["duration_ms"] >= 0
    assert metric["contract_retry_count"] == 0
    assert metric["diagnostic"] == diagnostic.model_dump(mode="json", by_alias=True)


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_maps_metric_persistence_failure_to_safe_error(
    mock_build_runtime: MagicMock,
) -> None:
    canary = "opaque-provider-and-metric-failure-canary"
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeModelError(
        f"provider response included {canary}"
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    def fail_metric_write(**kwargs) -> None:
        raise TurnPersistenceError(f"metric database included {canary}")

    persistence.record_turn_metric = fail_metric_write

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    diagnostic = _diagnostic(
        phase="persistence",
        field_path="run_outcome",
        validator="atomic_commit",
        retryable=True,
        public_reason=(
            "本轮结果未能安全保存，右侧产出物和历史版本均未作为成功结果提交。"
        ),
    )
    assert events == [
        RunStartedEvent(run_id="run-123"),
        ErrorEvent(
            code="PERSISTENCE_FAILED",
            message="本轮结果未能安全保存，请重试。",
            diagnostic=diagnostic,
        ),
    ]
    failed_turn = next(
        call for call in persistence.calls if call[0] == "fail_turn_request"
    )
    serialized = json.dumps(
        [event.model_dump(mode="json") for event in events] + [failed_turn],
        ensure_ascii=False,
    )
    assert failed_turn[3]["code"] == "PERSISTENCE_FAILED"
    assert canary not in serialized


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_records_schema_retry_count_from_runtime_error(
    mock_build_runtime: MagicMock,
) -> None:
    trusted_cause = UnexpectedModelBehavior("Exceeded maximum output retries (3)")
    runtime_error = AgentRuntimeSchemaError(str(trusted_cause))
    runtime_error.__cause__ = trusted_cause
    runtime = MagicMock()
    runtime.stream_turn.side_effect = runtime_error
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="deepseek-v4-flash",
            persistence=persistence,
        )
    )

    diagnostic = _diagnostic(
        phase="structured_output",
        field_path="artifact_data",
        validator="pydantic_ai_output_retry",
        retryable=True,
        public_reason=STRUCTURED_OUTPUT_PUBLIC_REASON,
    )
    assert events == [
        RunStartedEvent(run_id="run-123"),
        ErrorEvent(
            code="SCHEMA_VALIDATION_FAILED",
            message=SCHEMA_RETRY_EXHAUSTED_MESSAGE,
            diagnostic=diagnostic,
        ),
    ]
    metric_call = next(
        call for call in persistence.calls if call[0] == "record_turn_metric"
    )
    metric = metric_call[1]
    assert metric_call[0] == "record_turn_metric"
    assert metric["status"] == "error"
    assert metric["error_code"] == "SCHEMA_VALIDATION_FAILED"
    assert metric["contract_retry_count"] == 3
    assert metric["diagnostic"] == diagnostic.model_dump(mode="json", by_alias=True)


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_sends_persisted_context_prompt_to_runtime(
    mock_build_runtime: MagicMock,
) -> None:
    final = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧需求分析文档，请确认。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "stage_action": None,
            "warnings": [],
        }
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([final])
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    runtime.stream_turn.assert_called_once_with(
        "服务端上下文\n\n[用户]\n用户需求",
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_emits_context_warnings_on_run_started(
    mock_build_runtime: MagicMock,
) -> None:
    final = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧需求分析文档，请确认。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "stage_action": None,
            "warnings": [],
        }
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([final])
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()
    persistence.context_warnings = ["context_truncated"]

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    assert events[0] == RunStartedEvent(
        run_id="run-123",
        warnings=["context_truncated"],
    )


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_splits_single_final_output_into_chat_then_artifact_delta(
    mock_build_runtime: MagicMock,
) -> None:
    final = AgentTurnOutput.model_validate(
        {
            "chat": "已更新右侧需求分析文档，请确认。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "stage_action": None,
            "warnings": [],
        }
    )
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([final])
    mock_build_runtime.return_value = runtime

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    assert events == [
        RunStartedEvent(),
        AgentTurnDeltaEvent(output=AgentTurnDeltaOutput(chat=final.chat)),
        AgentTurnDeltaEvent(
            output=AgentTurnDeltaOutput(
                artifact_update=final.artifact_update,
            )
        ),
        AgentTurnEvent(output=final),
    ]


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_classifies_wrapped_json_decode_without_error_text(
    mock_build_runtime: MagicMock,
) -> None:
    cause = json.JSONDecodeError("contains-sensitive-provider-output", "{", 1)
    runtime_error = AgentRuntimeSchemaError("contains-sensitive-provider-output")
    runtime_error.__cause__ = cause
    runtime = MagicMock()
    runtime.stream_turn.side_effect = runtime_error
    mock_build_runtime.return_value = runtime

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    error_event = events[-1]
    assert isinstance(error_event, ErrorEvent)
    assert error_event.diagnostic == _diagnostic(
        phase="structured_output",
        field_path="response_json",
        validator="json_decode",
        retryable=True,
        public_reason=STRUCTURED_OUTPUT_PUBLIC_REASON,
    )
    assert "contains-sensitive-provider-output" not in error_event.model_dump_json()


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_classifies_output_truncation_without_raw_text(
    mock_build_runtime: MagicMock,
) -> None:
    cause = RawJsonStreamTerminationError("length")
    runtime_error = AgentRuntimeSchemaError("raw output was truncated")
    runtime_error.__cause__ = cause
    runtime = MagicMock()
    runtime.stream_turn.side_effect = runtime_error
    mock_build_runtime.return_value = runtime

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="deepseek-v4-flash",
        )
    )

    error_event = events[-1]
    assert isinstance(error_event, ErrorEvent)
    assert error_event.diagnostic == _diagnostic(
        phase="structured_output",
        field_path="response_json",
        validator="output_truncated",
        retryable=True,
        public_reason=STRUCTURED_OUTPUT_PUBLIC_REASON,
    )


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_projects_journey_duplicate_id_diagnostic(
    mock_build_runtime: MagicMock,
) -> None:
    from test_artifact_data_renderers import VALID_VALUE_JOURNEY_ARTIFACT_DATA

    invalid = json.loads(json.dumps(VALID_VALUE_JOURNEY_ARTIFACT_DATA))
    invalid["journey_stages"][1]["pain_id"] = invalid["journey_stages"][0]["pain_id"]
    with pytest.raises(ValidationError) as captured:
        ValueDiscoveryJourneyArtifactData.model_validate(invalid)
    runtime_error = AgentRuntimeSchemaError("structured output failed")
    runtime_error.__cause__ = captured.value
    runtime = MagicMock()
    runtime.stream_turn.side_effect = runtime_error
    mock_build_runtime.return_value = runtime

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="deepseek-v4-flash",
        )
    )

    assert events[-1].diagnostic.validator == "journey_duplicate_pain_id"


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
def test_stream_agent_run_events_projects_delivery_derived_metric_validator(
    metric_name: str,
    expected_field_path: str,
    expected_validator: str,
) -> None:
    from test_artifact_data_renderers import VALID_DELIVERY_ARTIFACT_DATA

    invalid = json.loads(json.dumps(VALID_DELIVERY_ARTIFACT_DATA))
    invalid["delivery_metrics"][metric_name] = 99
    with pytest.raises(ValidationError) as captured:
        DeliveryArtifactData.model_validate(invalid)
    runtime_error = AgentRuntimeSchemaError("structured output failed")
    runtime_error.__cause__ = captured.value

    with patch("stream_services.build_pydantic_agent_runtime") as build_runtime:
        runtime = MagicMock()
        runtime.stream_turn.side_effect = runtime_error
        build_runtime.return_value = runtime
        events = list(
            stream_agent_run_events(
                _request(),
                api_key="test-api-key",
                base_url="https://api.test.com/v1",
                model_name="deepseek-v4-flash",
            )
        )

    assert events[-1].diagnostic.field_path == expected_field_path
    assert events[-1].diagnostic.validator == expected_validator


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_rejects_unknown_live_schema_validator(
    mock_build_runtime: MagicMock,
) -> None:
    class ModelControlledValidatorPayload(BaseModel):
        value: str

        @field_validator("value")
        @classmethod
        def reject_value(cls, value: str) -> str:
            raise PydanticCustomError(
                "model_controlled_validator",
                "do not expose this validator",
            )

    with pytest.raises(ValidationError) as captured:
        ModelControlledValidatorPayload.model_validate({"value": "unsafe"})
    runtime_error = AgentRuntimeSchemaError("structured output failed")
    runtime_error.__cause__ = captured.value
    runtime = MagicMock()
    runtime.stream_turn.side_effect = runtime_error
    mock_build_runtime.return_value = runtime

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="deepseek-v4-flash",
        )
    )

    assert events[-1].diagnostic.validator == "pydantic_validation"


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_does_not_emit_or_persist_provider_error_text(
    mock_build_runtime: MagicMock,
) -> None:
    secret = "sk-provider-error-canary"
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeModelError(
        f"Authorization: Bearer {secret}"
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    serialized_event = events[-1].model_dump_json()
    failed_turn = next(
        call for call in persistence.calls if call[0] == "fail_turn_request"
    )
    assert secret not in serialized_event
    assert secret not in json.dumps(failed_turn)
    assert events[-1].message == PROVIDER_AUTH_PUBLIC_REASON


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_does_not_persist_model_controlled_extra_field_name(
    mock_build_runtime: MagicMock,
) -> None:
    secret = "sk_model_controlled_field"

    class StrictPayload(BaseModel):
        model_config = ConfigDict(extra="forbid")

        allowed: str

    with pytest.raises(ValidationError) as captured:
        StrictPayload.model_validate({"allowed": "ok", secret: "value"})
    runtime_error = AgentRuntimeSchemaError("structured output failed")
    runtime_error.__cause__ = captured.value
    runtime = MagicMock()
    runtime.stream_turn.side_effect = runtime_error
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            persistence=persistence,
        )
    )

    failed_turn = next(
        call for call in persistence.calls if call[0] == "fail_turn_request"
    )
    serialized = events[-1].model_dump_json() + json.dumps(failed_turn)
    assert secret not in serialized
    assert events[-1].diagnostic.field_path == "artifact_data.extra_field"
    assert events[-1].diagnostic.validator == "extra_forbidden"


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_maps_pydantic_ai_output_failure_to_error_event(
    mock_build_runtime: MagicMock,
) -> None:
    trusted_cause = UnexpectedModelBehavior("Exceeded maximum output retries (1)")
    runtime_error = AgentRuntimeSchemaError(str(trusted_cause))
    runtime_error.__cause__ = trusted_cause
    runtime = MagicMock()
    runtime.stream_turn.side_effect = runtime_error
    mock_build_runtime.return_value = runtime
    request = AgentRunStreamRequest.model_validate(
        {
            "prompt": "用户需求",
            "systemPrompt": "你是 Lisa。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "requestId": "stream-schema-error-001",
        }
    )

    events = list(
        stream_agent_run_events(
            request,
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    assert events == [
        RunStartedEvent(),
        ErrorEvent(
            code="SCHEMA_VALIDATION_FAILED",
            message=SCHEMA_RETRY_EXHAUSTED_MESSAGE,
            diagnostic=_diagnostic(
                phase="structured_output",
                field_path="artifact_data",
                validator="pydantic_ai_output_retry",
                retryable=True,
                public_reason=STRUCTURED_OUTPUT_PUBLIC_REASON,
            ),
        ),
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

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    assert events == [
        RunStartedEvent(),
        ErrorEvent(
            code="SCHEMA_VALIDATION_FAILED",
            message=SCHEMA_RETRY_EXHAUSTED_MESSAGE,
            diagnostic=_diagnostic(
                phase="structured_output",
                field_path="artifact_data",
                validator="pydantic_ai_output_retry",
                retryable=True,
                public_reason=STRUCTURED_OUTPUT_PUBLIC_REASON,
            ),
        ),
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
    request = AgentRunStreamRequest.model_validate(
        {
            "prompt": "用户需求",
            "systemPrompt": "你是 Lisa。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "requestId": "stream-contract-error-001",
        }
    )

    events = list(
        stream_agent_run_events(
            request,
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    assert events == [
        RunStartedEvent(),
        ErrorEvent(
            code="CONTRACT_VALIDATION_FAILED",
            message=CONTRACT_VALIDATION_PUBLIC_REASON,
            diagnostic=_diagnostic(
                phase="contract_validation",
                field_path="artifact_contract",
                validator="workflow_contract",
                retryable=False,
                public_reason=CONTRACT_VALIDATION_PUBLIC_REASON,
            ),
        ),
    ]


def _request() -> AgentRunStreamRequest:
    return AgentRunStreamRequest.model_validate(
        {
            "prompt": "用户需求",
            "systemPrompt": "你是 Lisa。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "requestId": "stream-default-request-001",
        }
    )


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_validates_workflow_stage_before_building_runtime(
    mock_build_runtime: MagicMock,
) -> None:
    requests = [
        (
            AgentRunStreamRequest.model_validate(
                {
                    "prompt": "用户需求",
                    "systemPrompt": "你是 Lisa。",
                    "workflowId": "UNKNOWN_WORKFLOW",
                    "stageId": "CLARIFY",
                    "requestId": "stream-invalid-workflow-001",
                }
            ),
            _diagnostic(
                phase="request_validation",
                workflow_id="UNKNOWN_WORKFLOW",
                stage_id="CLARIFY",
                field_path="request",
                validator="request_schema",
                retryable=False,
                public_reason=REQUEST_VALIDATION_PUBLIC_REASON,
            ),
        ),
        (
            AgentRunStreamRequest.model_validate(
                {
                    "prompt": "用户需求",
                    "systemPrompt": "你是 Lisa。",
                    "workflowId": "TEST_DESIGN",
                    "stageId": "REPORT",
                    "requestId": "stream-invalid-stage-001",
                }
            ),
            _diagnostic(
                phase="request_validation",
                workflow_id="TEST_DESIGN",
                stage_id="REPORT",
                field_path="request",
                validator="request_schema",
                retryable=False,
                public_reason=REQUEST_VALIDATION_PUBLIC_REASON,
            ),
        ),
    ]

    for request, diagnostic in requests:
        events = list(
            stream_agent_run_events(
                request,
                api_key="test-api-key",
                base_url="https://api.test.com/v1",
                model_name="test-model",
            )
        )

        assert events == [
            ErrorEvent(
                code="REQUEST_VALIDATION_FAILED",
                message=REQUEST_VALIDATION_PUBLIC_REASON,
                diagnostic=diagnostic,
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

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    assert len(events) == 2
    assert events[0] == RunStartedEvent()
    assert events[1].code == "LLM_ERROR"
    assert events[1].message == PROVIDER_ERROR_PUBLIC_REASON


@patch("stream_services.NaturalChatFirstDeltaSequencer.discard", autospec=True)
@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_discards_buffered_artifact_before_runtime_error(
    mock_build_runtime: MagicMock,
    mock_discard: MagicMock,
) -> None:
    def artifact_then_error():
        yield AgentTurnDeltaOutput.model_validate(
            {
                "artifact_update": {
                    "type": "replace",
                    "markdown": VALID_CLARIFY_ARTIFACT,
                }
            }
        )
        raise AgentRuntimeModelError("provider failed after partial artifact")

    runtime = MagicMock()
    runtime.stream_turn.return_value = artifact_then_error()
    mock_build_runtime.return_value = runtime

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    assert not any(isinstance(event, AgentTurnDeltaEvent) for event in events)
    assert events[-1].code == "LLM_ERROR"
    mock_discard.assert_called_once()


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_maps_model_api_error_to_llm_error_event(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeModelError("provider API failed")
    mock_build_runtime.return_value = runtime

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    assert events == [
        RunStartedEvent(),
        ErrorEvent(
            code="LLM_ERROR",
            message=PROVIDER_ERROR_PUBLIC_REASON,
            diagnostic=_diagnostic(
                phase="provider",
                field_path="provider",
                validator="provider_error",
                retryable=True,
                public_reason=PROVIDER_ERROR_PUBLIC_REASON,
            ),
        ),
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

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    assert len(events) == 2
    assert events[0] == RunStartedEvent()
    assert events[1].code == "LLM_ERROR"
    assert events[1].message == PROVIDER_AUTH_PUBLIC_REASON


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

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    assert len(events) == 2
    assert events[0] == RunStartedEvent()
    assert events[1].code == "LLM_ERROR"
    assert events[1].message == PROVIDER_RATE_LIMIT_PUBLIC_REASON


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

    events = list(
        stream_agent_run_events(
            _request(),
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
        )
    )

    assert len(events) == 2
    assert events[0] == RunStartedEvent()
    assert events[1].code == "LLM_ERROR"
    assert events[1].message == PROVIDER_CONNECTION_PUBLIC_REASON
