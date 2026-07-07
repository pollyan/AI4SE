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


CLARIFY_ARTIFACT_WITH_BLOCKING_OPEN_QUESTION = """# 需求分析文档

## 1. 需求事实清单
| 事实 ID | 需求事实 | 来源 | 证据等级 | 状态 |
|---|---|---|---|---|
| F-001 | 用户需要登录功能测试 | 用户描述 | 用户陈述 | 已确认 |

## 2. 被测系统与边界
| 类型 | 具体内容 | 测试含义 | 状态 |
|---|---|---|---|
| 测试范围 | 登录功能 | 覆盖主登录链路 | AI 假设 |

## 3. 业务规则与数据状态
| 规则 ID | 业务规则 | 触发条件 | 边界值/状态流转 | 异常处理 | 验收口径 | 状态 |
|---|---|---|---|---|---|---|
| BR-001 | 账号锁定策略待确认 | 连续登录失败 | 未确认 | 未确认 | 待确认 | 待确认 |

## 4. 核心链路与异常链路
```mermaid
flowchart TD
    User["用户"] --> Login["登录页"]
```

## 5. 待澄清问题
| 问题 ID | 问题描述 | 优先级 | 阻断性 | 影响范围 | 当前假设 | 责任方 | 状态 |
|---|---|---|---|---|---|---|---|
| Q-001 | 账号锁定和验证码触发策略未确认 | P0 | 阻断 | 策略优先级和风险判断 | 暂按常见登录风控处理 | 产品 | 待确认 |

## 6. 隐式质量需求
| 质量维度 | 需求或假设 | 可验证指标 | 风险 | 状态 |
|---|---|---|---|---|
| 安全 | 防止暴力破解 | 锁定策略生效 | 高风险 | 待确认 |

## 7. 后续测试设计输入
| 输入类型 | ID | 内容 | 来源 | 后续用途 |
|---|---|---|---|---|
| 风险种子 | R-SEED-001 | 账号锁定策略未确认 | Q-001 | 策略阶段 FMEA |

## 8. 阶段门禁
- [ ] P0 阻断问题已确认。"""


class FakePersistence:
    def __init__(self) -> None:
        self.calls = []
        self.context_warnings = []

    def ensure_run(self, agent_request, *, model_name: str) -> str:
        self.calls.append((
            "ensure_run",
            agent_request.workflow_id,
            agent_request.stage_id,
            agent_request.run_id,
            model_name,
        ))
        return "run-123"

    def append_user_message(self, run_id: str, content: str) -> None:
        self.calls.append(("append_user_message", run_id, content))

    def append_assistant_message(self, run_id: str, content: str) -> None:
        self.calls.append(("append_assistant_message", run_id, content))

    def record_artifact_version(
        self,
        run_id: str,
        stage_id: str,
        content: str,
        *,
        artifact_data=None,
    ) -> None:
        self.calls.append((
            "record_artifact_version",
            run_id,
            stage_id,
            content,
            artifact_data,
        ))

    def build_runtime_prompt(self, run_id: str, current_prompt: str) -> str:
        self.calls.append(("build_runtime_prompt", run_id, current_prompt))
        return f"服务端上下文\n\n[用户]\n{current_prompt}"

    def build_runtime_context(self, run_id: str, current_prompt: str):
        self.calls.append(("build_runtime_context", run_id, current_prompt))
        return f"服务端上下文\n\n[用户]\n{current_prompt}", self.context_warnings

    def record_turn_metric(self, **kwargs) -> None:
        self.calls.append(("record_turn_metric", kwargs))


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
    assert "## 1. 需求事实清单" in runtime_kwargs["system_prompt"]
    runtime.stream_turn.assert_called_once_with(
        "用户需求",
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_preserves_artifact_patch_metadata(
    mock_build_runtime: MagicMock,
) -> None:
    base = "# 文档\n\n## 范围\n\n旧范围"
    final = AgentTurnOutput.model_validate({
        "chat": "已追加风险章节。",
        "artifact_update": {
            "type": "replace",
            "markdown": f"{base}\n\n## 风险\n\n新风险",
        },
        "artifact_patch": {
            "operation": "add_after",
            "sectionAnchor": "h2:风险:1",
            "afterSectionAnchor": "h2:范围:1",
            "replacementMarkdown": "## 风险\n\n新风险",
            "baseContent": base,
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

    assert isinstance(events[1], AgentTurnDeltaEvent)
    assert events[1].output.artifact_patch == final.artifact_patch
    assert events[-1] == AgentTurnEvent(output=final)
    assert events[-1].output.artifact_patch == final.artifact_patch


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_records_turn_through_persistence_adapter(
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
    persistence = FakePersistence()
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
        persistence=persistence,
    ))

    assert events[0] == RunStartedEvent(run_id="run-123")
    assert events[-1] == AgentTurnEvent(output=final)
    assert persistence.calls[:-1] == [
        ("ensure_run", "TEST_DESIGN", "CLARIFY", None, "test-model"),
        ("build_runtime_context", "run-123", "用户需求"),
        ("append_user_message", "run-123", "用户需求"),
        ("append_assistant_message", "run-123", "已更新右侧需求分析文档，请确认。"),
        (
            "record_artifact_version",
            "run-123",
            "CLARIFY",
            VALID_CLARIFY_ARTIFACT,
            None,
        ),
    ]
    metric = persistence.calls[-1][1]
    assert persistence.calls[-1][0] == "record_turn_metric"
    assert metric["run_id"] == "run-123"
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
def test_stream_agent_run_events_records_artifact_data_through_persistence_adapter(
    mock_build_runtime: MagicMock,
) -> None:
    artifact_data = {
        "document_info": {
            "artifact_name": "用户故事卡片",
            "workflow": "USER_STORY_BREAKDOWN",
            "stage": "STORIES",
        },
        "story_cards": [
            {
                "story_id": "US-001",
                "title": "短信验证码登录",
            }
        ],
    }
    final = AgentTurnOutput.model_validate({
        "chat": "已更新右侧用户故事卡片，请确认。",
        "artifact_update": {
            "type": "replace",
            "markdown": VALID_CLARIFY_ARTIFACT,
        },
        "artifact_data": artifact_data,
        "stage_action": None,
        "warnings": [],
    })
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([final])
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()
    request = AgentRunStreamRequest.model_validate({
        "prompt": "用户需求",
        "systemPrompt": "你是 Alex。",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
    })

    events = list(stream_agent_run_events(
        request,
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
        persistence=persistence,
    ))

    assert events[-1] == AgentTurnEvent(output=final)
    assert (
        "record_artifact_version",
        "run-123",
        "CLARIFY",
        VALID_CLARIFY_ARTIFACT,
        artifact_data,
    ) in persistence.calls
    assert "artifact_data" not in events[-1].model_dump(mode="json")["output"]


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_records_real_token_usage_when_runtime_exposes_it(
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
    runtime.last_token_usage = 321
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
        persistence=persistence,
    ))

    assert events[-1] == AgentTurnEvent(output=final)
    metric = persistence.calls[-1][1]
    assert persistence.calls[-1][0] == "record_turn_metric"
    assert metric["estimated_tokens"] == 321


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_records_error_turn_metric(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeModelError(
        "provider API failed"
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
        persistence=persistence,
    ))

    assert events[0] == RunStartedEvent(run_id="run-123")
    error = events[1]
    assert isinstance(error, ErrorEvent)
    assert error.code == "LLM_ERROR"
    assert error.message == "provider API failed"
    assert error.diagnostic is not None
    assert error.diagnostic.phase == "provider"
    assert error.diagnostic.validator == "provider_error"
    metric = persistence.calls[-1][1]
    assert persistence.calls[-1][0] == "record_turn_metric"
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
    assert metric["diagnostic"]["validator"] == "provider_error"


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_records_schema_retry_count_from_runtime_error(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeSchemaError(
        "Exceeded maximum output retries (3)"
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
        persistence=persistence,
    ))

    assert events[0] == RunStartedEvent(run_id="run-123")
    error = events[1]
    assert isinstance(error, ErrorEvent)
    assert error.code == "SCHEMA_VALIDATION_FAILED"
    assert error.message == (
        "模型连续生成的结构化结果未通过校验。请重试本轮操作；"
        "如果多次失败，请补充更明确的需求或阶段确认信息。"
    )
    assert error.diagnostic is not None
    assert error.diagnostic.phase == "structured_output"
    assert error.diagnostic.validator == "pydantic_ai_output_retry"
    metric = persistence.calls[-1][1]
    assert persistence.calls[-1][0] == "record_turn_metric"
    assert metric["status"] == "error"
    assert metric["error_code"] == "SCHEMA_VALIDATION_FAILED"
    assert metric["contract_retry_count"] == 3
    assert metric["diagnostic"]["validator"] == "pydantic_ai_output_retry"


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_returns_typed_schema_diagnostic_and_metric(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeSchemaError(
        "Exceeded maximum output retries (2): "
        "artifact_data.requirement_facts.0.fact"
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.deepseek.com/v1",
        model_name="deepseek-chat",
        persistence=persistence,
    ))

    error = events[-1]
    assert isinstance(error, ErrorEvent)
    assert error.code == "SCHEMA_VALIDATION_FAILED"
    assert error.diagnostic is not None
    assert error.diagnostic.phase == "structured_output"
    assert error.diagnostic.workflow_id == "TEST_DESIGN"
    assert error.diagnostic.stage_id == "CLARIFY"
    assert error.diagnostic.field_path == "artifact_data"
    assert error.diagnostic.validator == "pydantic_ai_output_retry"
    assert error.diagnostic.retryable is True
    assert "右侧产出物已保持不变" in error.diagnostic.public_reason
    metric = persistence.calls[-1][1]
    assert persistence.calls[-1][0] == "record_turn_metric"
    assert metric["diagnostic"] == {
        "phase": "structured_output",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
        "fieldPath": "artifact_data",
        "validator": "pydantic_ai_output_retry",
        "retryable": True,
        "publicReason": error.diagnostic.public_reason,
    }


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_returns_typed_provider_diagnostic(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeModelError("401 invalid api key")
    mock_build_runtime.return_value = runtime

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.example.com/v1",
        model_name="test-model",
    ))

    error = events[-1]
    assert isinstance(error, ErrorEvent)
    assert error.code == "LLM_ERROR"
    assert error.diagnostic is not None
    assert error.diagnostic.phase == "provider"
    assert error.diagnostic.field_path == "provider"
    assert error.diagnostic.validator == "provider_authentication"
    assert error.diagnostic.retryable is False
    assert "模型供应商鉴权失败" in error.diagnostic.public_reason


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_sends_persisted_context_prompt_to_runtime(
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
    persistence = FakePersistence()

    list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
        persistence=persistence,
    ))

    runtime.stream_turn.assert_called_once_with(
        "服务端上下文\n\n[用户]\n用户需求",
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_emits_context_warnings_on_run_started(
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
    persistence = FakePersistence()
    persistence.context_warnings = ["context_truncated"]

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="test-model",
        persistence=persistence,
    ))

    assert events[0] == RunStartedEvent(
        run_id="run-123",
        warnings=["context_truncated"],
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
def test_stream_agent_run_events_blocks_next_stage_when_clarify_is_not_ready(
    mock_build_runtime: MagicMock,
) -> None:
    final = AgentTurnOutput.model_validate({
        "chat": "已更新需求分析文档，确认无误后可以进入下一阶段（策略制定）。",
        "artifact_update": {
            "type": "replace",
            "markdown": CLARIFY_ARTIFACT_WITH_BLOCKING_OPEN_QUESTION,
        },
        "stage_action": {
            "type": "request_next_stage",
            "target_stage_id": "STRATEGY",
        },
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

    delta_output = events[1].output
    final_output = events[-1].output
    assert isinstance(events[1], AgentTurnDeltaEvent)
    assert isinstance(events[-1], AgentTurnEvent)
    assert delta_output.stage_action is None
    assert final_output.stage_action is None
    assert "stage_readiness_blocked" in delta_output.warnings
    assert "stage_readiness_blocked" in final_output.warnings
    assert "还不能进入下一阶段" in final_output.chat
    assert "Q-001" in final_output.chat


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

    assert events[0] == RunStartedEvent()
    error = events[1]
    assert isinstance(error, ErrorEvent)
    assert error.code == "SCHEMA_VALIDATION_FAILED"
    assert error.message == (
        "模型连续生成的结构化结果未通过校验。请重试本轮操作；"
        "如果多次失败，请补充更明确的需求或阶段确认信息。"
    )
    assert error.diagnostic is not None
    assert error.diagnostic.phase == "structured_output"


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

    assert events[0] == RunStartedEvent()
    error = events[1]
    assert isinstance(error, ErrorEvent)
    assert error.code == "SCHEMA_VALIDATION_FAILED"
    assert error.message == (
        "模型连续生成的结构化结果未通过校验。请重试本轮操作；"
        "如果多次失败，请补充更明确的需求或阶段确认信息。"
    )
    assert error.diagnostic is not None
    assert error.diagnostic.validator == "pydantic_ai_output_retry"


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

    assert events[0] == RunStartedEvent()
    error = events[1]
    assert isinstance(error, ErrorEvent)
    assert error.code == "CONTRACT_VALIDATION_FAILED"
    assert error.message == "chat must not contain artifact markdown"
    assert error.diagnostic is not None
    assert error.diagnostic.phase == "contract_validation"
    assert error.diagnostic.validator == "workflow_contract"


def _request() -> AgentRunStreamRequest:
    return AgentRunStreamRequest.model_validate({
        "prompt": "用户需求",
        "systemPrompt": "你是 Lisa。",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
    })


@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_errors_after_partial_delta_without_persisting_artifact(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()

    def broken_stream_turn(*args, **kwargs):
        yield AgentTurnDeltaOutput.model_validate({
            "chat": "已更新需求文档。",
            "artifact_update": {
                "type": "replace",
                "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
            },
            "stage_action": None,
            "warnings": [],
        })
        raise AgentRuntimeSchemaError("Unterminated string in raw JSON stream")

    runtime.stream_turn.side_effect = broken_stream_turn
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.deepseek.com/v1",
        model_name="deepseek-chat",
        persistence=persistence,
    ))

    assert isinstance(events[0], RunStartedEvent)
    assert isinstance(events[1], AgentTurnDeltaEvent)
    assert isinstance(events[2], ErrorEvent)
    assert len(events) == 3
    assert events[2].code == "SCHEMA_VALIDATION_FAILED"
    assert events[2].diagnostic is not None
    assert events[2].diagnostic.phase == "structured_output"

    call_names = [call[0] for call in persistence.calls]
    assert "append_assistant_message" not in call_names
    assert "record_artifact_version" not in call_names
    assert persistence.calls[-1][0] == "record_turn_metric"
    metric = persistence.calls[-1][1]
    assert metric["status"] == "error"
    assert metric["error_code"] == "SCHEMA_VALIDATION_FAILED"
    assert metric["diagnostic"]["phase"] == "structured_output"


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

        assert len(events) == 1
        error = events[0]
        assert isinstance(error, ErrorEvent)
        assert error.code == "REQUEST_VALIDATION_FAILED"
        assert error.message == message
        assert error.diagnostic is not None
        assert error.diagnostic.phase == "request_validation"
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

    assert events[0] == RunStartedEvent()
    error = events[1]
    assert isinstance(error, ErrorEvent)
    assert error.code == "LLM_ERROR"
    assert error.message == "provider API failed"
    assert error.diagnostic is not None
    assert error.diagnostic.phase == "provider"
    assert error.diagnostic.validator == "provider_error"


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
