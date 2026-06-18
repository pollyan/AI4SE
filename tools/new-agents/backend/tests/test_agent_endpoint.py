import os
import json
import tempfile
from unittest.mock import patch

import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior

from agent_contracts import AgentTurnOutput
from agent_runtime import AgentRuntimeDependencyError
from app import create_app
from models import LlmConfig, db


VALID_CLARIFY_ARTIFACT = """# 需求分析文档

## 1. 被测系统与边界
内容

## 2. 系统交互与核心链路
内容

## 3. 待澄清与阻断性问题
内容

## 4. 隐式需求与非功能性考量
内容"""


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def default_config(app):
    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="test-api-key",
                base_url="https://api.test.com/v1",
                model="test-model",
                description="Test config",
            )
        )
        db.session.commit()


class FakeRuntime:
    def __init__(self):
        self.calls = []

    def stream_turn(self, prompt, *, workflow_id, current_stage_id):
        self.calls.append(
            {
                "prompt": prompt,
                "workflow_id": workflow_id,
                "current_stage_id": current_stage_id,
            }
        )
        yield AgentTurnOutput.model_validate({
            "chat": "正在梳理登录需求。",
            "artifact_update": {
                "type": "replace",
                "markdown": VALID_CLARIFY_ARTIFACT,
            },
            "stage_action": None,
            "warnings": [],
        })
        yield AgentTurnOutput.model_validate({
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
        })


class FailingRuntime:
    def __init__(self, error):
        self.error = error

    def stream_turn(self, prompt, *, workflow_id, current_stage_id):
        raise self.error
        yield


def _parse_sse_event_payloads(response):
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.get_data(as_text=True).splitlines()
        if line.startswith("data: {")
    ]


@patch("stream_services.build_pydantic_agent_runtime")
def test_agent_runs_stream_returns_started_delta_and_final_sse_events(
    mock_build_runtime,
    client,
    default_config,
):
    runtime = FakeRuntime()
    mock_build_runtime.return_value = runtime

    response = client.post(
        "/api/agent/runs/stream",
        json={
            "prompt": "用户需求: 登录功能",
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
        },
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"

    payloads = _parse_sse_event_payloads(response)
    assert [payload["type"] for payload in payloads] == [
        "run_started",
        "agent_delta",
        "agent_delta",
        "agent_turn",
    ]
    assert response.get_data(as_text=True).strip().endswith("data: [DONE]")

    event = payloads[-1]
    output = event["output"]
    assert output["chat"] == "已更新右侧需求分析文档。"
    assert "# 需求分析文档" not in output["chat"]
    assert output["artifact_update"]["type"] == "replace"
    assert "# 需求分析文档" in output["artifact_update"]["markdown"]
    assert output["stage_action"]["target_stage_id"] == "STRATEGY"
    assert runtime.calls == [
        {
            "prompt": "用户需求: 登录功能",
            "workflow_id": "TEST_DESIGN",
            "current_stage_id": "CLARIFY",
        }
    ]


def test_agent_runs_stream_rejects_missing_prompt(client, default_config):
    response = client.post(
        "/api/agent/runs/stream",
        json={
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
        },
    )

    assert response.status_code == 400
    assert response.json == {"error": "prompt 不能为空"}


def test_agent_runs_stream_returns_json_error_for_empty_json_body(
    client,
    default_config,
):
    response = client.post(
        "/api/agent/runs/stream",
        data="",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == {"error": "请求体为空"}


def test_agent_runs_stream_returns_json_error_for_malformed_json_body(
    client,
    default_config,
):
    response = client.post(
        "/api/agent/runs/stream",
        data="{broken",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == {"error": "请求体不是合法 JSON"}


@patch("stream_services.build_pydantic_agent_runtime")
def test_agent_runs_stream_rejects_stage_outside_workflow_before_runtime(
    mock_build_runtime,
    client,
    default_config,
):
    response = client.post(
        "/api/agent/runs/stream",
        json={
            "prompt": "用户需求: 登录功能",
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "REPORT",
        },
    )

    assert response.status_code == 400
    assert response.json == {
        "error": "workflowId 与 stageId 不匹配: TEST_DESIGN/REPORT"
    }
    mock_build_runtime.assert_not_called()


def test_agent_runs_stream_returns_503_when_default_config_missing(client):
    response = client.post(
        "/api/agent/runs/stream",
        json={
            "prompt": "用户需求: 登录功能",
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
        },
    )

    assert response.status_code == 503
    assert response.json == {
        "error": "系统未配置默认 LLM，请维护后端默认 LLM 配置后重试"
    }


@patch("stream_services.build_pydantic_agent_runtime")
def test_agent_runs_stream_returns_typed_error_when_runtime_dependency_missing(
    mock_build_runtime,
    client,
    default_config,
):
    mock_build_runtime.side_effect = AgentRuntimeDependencyError(
        "pydantic-ai runtime unavailable"
    )

    response = client.post(
        "/api/agent/runs/stream",
        json={
            "prompt": "用户需求: 登录功能",
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
        },
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert response.get_data(as_text=True).strip().endswith("data: [DONE]")
    assert _parse_sse_event_payloads(response) == [
        {
            "type": "error",
            "code": "AGENT_RUNTIME_UNAVAILABLE",
            "message": "pydantic-ai runtime unavailable",
        }
    ]


@patch("stream_services.build_pydantic_agent_runtime")
def test_agent_runs_stream_returns_typed_error_when_model_output_exceeds_retries(
    mock_build_runtime,
    client,
    default_config,
):
    mock_build_runtime.return_value = FailingRuntime(
        UnexpectedModelBehavior("Exceeded maximum output retries (3)")
    )

    response = client.post(
        "/api/agent/runs/stream",
        json={
            "prompt": "用户需求: 登录功能",
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
        },
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert response.get_data(as_text=True).strip().endswith("data: [DONE]")
    assert _parse_sse_event_payloads(response) == [
        {
            "type": "run_started",
        },
        {
            "type": "error",
            "code": "SCHEMA_VALIDATION_FAILED",
            "message": (
                "模型连续生成的结构化结果未通过校验。请重试本轮操作；"
                "如果多次失败，请补充更明确的需求或阶段确认信息。"
            ),
        }
    ]
