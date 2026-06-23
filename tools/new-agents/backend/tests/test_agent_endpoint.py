import os
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior

from agent_contracts import AgentTurnOutput
from agent_runtime import AgentRuntimeDependencyError
from app import create_app
from models import AgentRun, LlmConfig, db
from run_persistence import (
    append_run_message,
    create_agent_run,
    get_run_snapshot,
    record_artifact_version,
    record_turn_metric,
)


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

VALID_CASES_ARTIFACT = """# 测试用例集

## 1. 用例统计
**统计摘要**：共 1 条用例，P0: 1 条 | P1: 0 条 | P2: 0 条

## 2. 用例设计依据
| 依据 ID | 来源类型 | 来源 ID | 设计依据 | 派生用例方向 |
|---|---|---|---|---|
| BASIS-001 | 测试点 | TP-001 | 登录主链路必须覆盖 | 正向功能 |

## 3. 按维度分组的用例清单

### 3.1 正向功能验证

| ID | 用例标题 | 优先级 | 测试维度 | 关联测试点 | 关联风险 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 | 断言 | 执行层级 | 自动化建议 | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC-001 | 用户登录成功 | P0 | 正向功能验证 | 登录主链路 | R-LOGIN-001 | 用户已注册 | 1. 输入账号密码 2. 点击登录 | 正确账号密码 | 进入工作台 | 工作台可见且登录态存在 | E2E | 优先自动化 | 可执行 |

## 4. 测试数据与环境
| 数据/环境 ID | 类型 | 内容 | 准备方式 | 关联用例 | 状态 |
|---|---|---|---|---|---|
| DATA-001 | 测试账号 | 正确账号密码 | 人工准备 | TC-001 | 已具备 |

## 5. 自动化候选
| 候选 ID | 用例 ID | 推荐自动化层级 | 自动化价值 | 前置条件 | 风险或限制 | 状态 |
|---|---|---|---|---|---|---|
| AUTO-001 | TC-001 | E2E | 高频回归 | 登录环境稳定 | 无 | 推荐 |

## 6. 测试点覆盖追溯

| 测试点 | 优先级 | 关联风险 | 覆盖用例 | 覆盖状态 |
|---|---|---|---|---|
| 登录主链路 | P0 | R-LOGIN-001 | TC-001 | 已覆盖 |

```ai4se-visual
{
  "type": "traceability-matrix",
  "title": "测试点-用例覆盖追溯矩阵",
  "columns": ["测试点", "优先级", "关联风险", "覆盖用例", "覆盖状态"],
  "rows": [
    {"测试点": "登录主链路", "优先级": "P0", "关联风险": "R-LOGIN-001", "覆盖用例": "TC-001", "覆盖状态": "已覆盖"}
  ]
}
```

## 7. 开放问题
| 问题 ID | 问题描述 | 关联用例/测试点 | 优先级 | 阻断性 | 责任方 | 状态 |
|---|---|---|---|---|---|---|
| CASE-Q-001 | 无开放问题 | TC-001 | P2 | 非阻断 | 测试 | 已确认 |

## 8. 阶段门禁
- [x] 所有 P0 测试点都有至少一条用例覆盖。
"""

VALID_BLUEPRINT_ARTIFACT = """# AI 测试资产管理平台需求蓝图

## 文档信息
| 维度 | 内容 |
| --- | --- |
| Artifact 名称 | 可评审需求蓝图 |
| 蓝图状态 | 可交接 Lisa |

## 1. 产品概述
AI 测试资产管理平台。

### 1.1 产品愿景
帮助团队沉淀测试资产。

### 1.2 定位声明
面向测试负责人，解决测试资产分散问题。

### 1.3 核心价值
| 维度 | 描述 |
| --- | --- |
| 用户价值 | 提升测试资产复用效率 |

## 2. 目标用户（摘要）
| 用户类型 | 核心痛点 | 优先级 |
| --- | --- | --- |
| 测试负责人 | 测试资产分散 | 核心用户 |

## 3. 核心需求
### 功能架构
```mermaid
mindmap
    root(("AI 测试资产管理平台"))
        ("测试资产")
            ["策略"]
            ["用例"]
```

### P0 需求（核心功能，必须实现）
| ID | 需求名称 | 用户故事 | 对应痛点 | 范围边界 | 依赖 | 验收标准 | 可测试性等级 | owner | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-001 | 自动生成测试策略和用例 | 作为测试负责人，我想生成测试资产，以便提升复用效率 | 测试资产分散 | 支持策略和用例生成 | LLM 配置 | 能生成可评审策略和用例 | 高 | 产品 | 已确认 |

### P1 需求（重要功能，应该实现）
| ID | 需求名称 | 用户故事 | 对应痛点 | 范围边界 | 依赖 | 验收标准 | 可测试性等级 | owner | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### P2 需求（增值功能，可以实现）
| ID | 需求名称 | 用户故事 | 对应痛点 | 范围边界 | 依赖 | 验收标准 | 可测试性等级 | owner | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 4. 核心流程
### 主流程图
```mermaid
flowchart TD
    A["输入需求"] --> B["生成策略"]
    B --> C["生成用例"]
```

## 5. 成功指标
| 指标类型 | 指标名称 | 目标值 | 衡量方式 |
| --- | --- | --- | --- |
| 产品指标 | 资产生成完成率 | 90% | 运行记录 |

## 6. MVP 范围与计划
### MVP 包含功能
- [x] F-001: 自动生成测试策略和用例

### 迭代路线
| 版本 | 时间 | 核心功能 | 目标 |
| --- | --- | --- | --- |
| v1.0 MVP | 4 周 | 核心资产生成 | 验证主价值 |

## 7. 非功能需求
| 类型 | 需求描述 | 指标/约束 | 验证方式 | owner | 状态 |
| --- | --- | --- | --- | --- | --- |
| 性能 | 生成响应可接受 | 60 秒内返回 | 冒烟测试 | 研发 | 已确认 |

## 8. 验收标准
| 验收 ID | 关联需求 | 验收标准 | 验证方式 | 可测试性等级 | owner | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | F-001 | 可生成策略和用例 artifact | 自动化测试 | 高 | 测试 | 已确认 |

## 9. 路线图
```ai4se-visual
{"type":"roadmap","columns":["版本","时间","核心功能","目标","成功指标"],"rows":[{"版本":"v1.0 MVP","时间":"4 周","核心功能":"核心资产生成","目标":"验证主价值","成功指标":"资产生成完成率"}]}
```

## 10. 风险评估
| 风险类型 | 风险描述 | 可能性 | 影响 | 缓解措施 | owner | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| 产品风险 | 输出质量不稳定 | 中 | 高 | 增加评审门禁 | 产品 | 已确认 |

## 11. Lisa Handoff 输入
| 输入类型 | ID | 内容 | 来源 | 给 Lisa 的用途 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 需求 | F-001 | 自动生成测试策略和用例 | P0 需求 | 需求评审 / 测试设计 | 已确认 |
| 验收标准 | AC-001 | 可生成策略和用例 artifact | 验收标准 | 测试断言 | 已确认 |
| 开放问题 | Q-001 | 锁定策略是否需要纳入首轮测试设计 | 待澄清问题 | 测试范围判断 | 待确认 |

## 12. 阶段门禁
- [x] P0 需求均具备验收标准、owner 和可测试性等级。
"""


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


@patch("stream_services.build_pydantic_agent_runtime")
def test_agent_runs_stream_persists_run_messages_and_final_artifact(
    mock_build_runtime,
    app,
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
    payloads = _parse_sse_event_payloads(response)
    run_id = payloads[0]["runId"]

    with app.app_context():
        snapshot = get_run_snapshot(run_id)

    assert snapshot["run"]["workflowId"] == "TEST_DESIGN"
    assert snapshot["run"]["agentId"] == "lisa"
    assert snapshot["run"]["currentStageId"] == "CLARIFY"
    assert snapshot["run"]["model"] == "test-model"
    assert [
        (message["role"], message["content"])
        for message in snapshot["messages"]
    ] == [
        ("user", "用户需求: 登录功能"),
        ("assistant", "已更新右侧需求分析文档。"),
    ]
    assert snapshot["artifacts"] == [
        {
            "stageId": "CLARIFY",
            "content": VALID_CLARIFY_ARTIFACT,
            "versionNumber": 1,
        }
    ]


@patch("stream_services.build_pydantic_agent_runtime")
def test_agent_runs_stream_reuses_existing_run_id(
    mock_build_runtime,
    app,
    client,
    default_config,
):
    runtime = FakeRuntime()
    mock_build_runtime.return_value = runtime

    first_response = client.post(
        "/api/agent/runs/stream",
        json={
            "prompt": "第一轮",
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
        },
    )
    run_id = _parse_sse_event_payloads(first_response)[0]["runId"]

    second_response = client.post(
        "/api/agent/runs/stream",
        json={
            "prompt": "第二轮",
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "runId": run_id,
        },
    )

    assert second_response.status_code == 200
    assert _parse_sse_event_payloads(second_response)[0]["runId"] == run_id
    with app.app_context():
        snapshot = get_run_snapshot(run_id)

    assert [
        (message["role"], message["content"])
        for message in snapshot["messages"]
    ] == [
        ("user", "第一轮"),
        ("assistant", "已更新右侧需求分析文档。"),
        ("user", "第二轮"),
        ("assistant", "已更新右侧需求分析文档。"),
    ]
    assert snapshot["artifacts"][0]["versionNumber"] == 2


@patch("stream_services.build_pydantic_agent_runtime")
def test_agent_run_snapshot_endpoint_returns_persisted_trace(
    mock_build_runtime,
    client,
    default_config,
):
    runtime = FakeRuntime()
    mock_build_runtime.return_value = runtime

    stream_response = client.post(
        "/api/agent/runs/stream",
        json={
            "prompt": "用户需求: 登录功能",
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
        },
    )
    run_id = _parse_sse_event_payloads(stream_response)[0]["runId"]

    response = client.get(f"/api/agent/runs/{run_id}")

    assert response.status_code == 200
    assert response.json["run"] == {
        "id": run_id,
        "workflowId": "TEST_DESIGN",
        "agentId": "lisa",
        "currentStageId": "CLARIFY",
        "status": "active",
        "model": "test-model",
    }
    assert [
        (message["role"], message["content"], message["sequenceIndex"])
        for message in response.json["messages"]
    ] == [
        ("user", "用户需求: 登录功能", 1),
        ("assistant", "已更新右侧需求分析文档。", 2),
    ]
    assert response.json["artifacts"] == [
        {
            "stageId": "CLARIFY",
            "content": VALID_CLARIFY_ARTIFACT,
            "versionNumber": 1,
        }
    ]


def test_agent_run_snapshot_endpoint_returns_404_for_unknown_run(
    client,
    default_config,
):
    response = client.get("/api/agent/runs/unknown-run")

    assert response.status_code == 404
    assert response.json == {"error": "未知 runId: unknown-run"}


def test_agent_run_context_summary_update_endpoint_persists_content(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(run.id, "STRATEGY", "# 阶段结论\n\n初始摘要")
        run_id = run.id

    response = client.patch(
        f"/api/agent/runs/{run_id}/context-summaries",
        json={
            "sourceType": "artifact",
            "sourceStageId": "STRATEGY",
            "summaryType": "stage_conclusion",
            "content": "人工校准后的阶段结论",
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "sourceType": "artifact",
        "sourceStageId": "STRATEGY",
        "summaryType": "stage_conclusion",
        "content": "人工校准后的阶段结论",
    }

    snapshot_response = client.get(f"/api/agent/runs/{run_id}")
    summaries = {
        summary["summaryType"]: summary["content"]
        for summary in snapshot_response.json["contextSummaries"]
    }
    assert summaries["stage_conclusion"] == "人工校准后的阶段结论"


def test_agent_run_context_summary_update_endpoint_rejects_invalid_payload(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(run.id, "STRATEGY", "# 阶段结论\n\n初始摘要")
        run_id = run.id

    response = client.patch(
        f"/api/agent/runs/{run_id}/context-summaries",
        json={
            "sourceType": "artifact",
            "sourceStageId": "STRATEGY",
            "summaryType": "stage_conclusion",
            "content": " ",
        },
    )

    assert response.status_code == 400
    assert response.json == {"error": "content 不能为空"}


def test_agent_run_context_summary_update_endpoint_returns_404_for_missing_summary(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        run_id = run.id

    response = client.patch(
        f"/api/agent/runs/{run_id}/context-summaries",
        json={
            "sourceType": "artifact",
            "sourceStageId": "STRATEGY",
            "summaryType": "stage_conclusion",
            "content": "人工校准后的阶段结论",
        },
    )

    assert response.status_code == 404
    assert response.json == {
        "error": "未知上下文摘要: artifact/STRATEGY/stage_conclusion"
    }


def test_agent_run_artifact_update_endpoint_records_manual_artifact_version(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(run.id, "STRATEGY", "# 测试策略蓝图\n\n初始版本")
        run_id = run.id

    response = client.post(
        f"/api/agent/runs/{run_id}/artifacts",
        json={
            "stageId": "STRATEGY",
            "content": "# 测试策略蓝图\n\n人工校准后的风险优先级",
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "stageId": "STRATEGY",
        "content": "# 测试策略蓝图\n\n人工校准后的风险优先级",
        "versionNumber": 2,
    }

    snapshot_response = client.get(f"/api/agent/runs/{run_id}")
    assert snapshot_response.json["artifacts"] == [response.json]
    assert snapshot_response.json["artifactAuditEvents"] == [
        {
            "stageId": "STRATEGY",
            "eventType": "artifact_saved",
            "summary": "保存了 STRATEGY 阶段产出物 v2",
            "createdAt": snapshot_response.json["artifactAuditEvents"][0]["createdAt"],
        }
    ]
    summaries = {
        summary["summaryType"]: summary["content"]
        for summary in snapshot_response.json["contextSummaries"]
        if summary["sourceStageId"] == "STRATEGY"
    }
    assert "人工校准后的风险优先级" in summaries["current_artifact"]


def test_agent_run_artifact_update_endpoint_accepts_expected_current_version(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(run.id, "STRATEGY", "# 测试策略蓝图\n\n初始版本")
        run_id = run.id

    response = client.post(
        f"/api/agent/runs/{run_id}/artifacts",
        json={
            "stageId": "STRATEGY",
            "content": "# 测试策略蓝图\n\n基于版本 1 的人工校准",
            "expectedVersionNumber": 1,
        },
    )

    assert response.status_code == 200
    assert response.json["versionNumber"] == 2
    assert response.json["content"] == "# 测试策略蓝图\n\n基于版本 1 的人工校准"


def test_agent_run_artifact_update_endpoint_returns_409_for_stale_version(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(run.id, "STRATEGY", "# 测试策略蓝图\n\n版本 1")
        record_artifact_version(run.id, "STRATEGY", "# 测试策略蓝图\n\n版本 2")
        run_id = run.id

    response = client.post(
        f"/api/agent/runs/{run_id}/artifacts",
        json={
            "stageId": "STRATEGY",
            "content": "# 测试策略蓝图\n\n基于旧版本的修改",
            "expectedVersionNumber": 1,
        },
    )

    assert response.status_code == 409
    assert response.json == {
        "error": "产出物已被更新，请刷新后再保存",
        "currentArtifact": {
            "stageId": "STRATEGY",
            "content": "# 测试策略蓝图\n\n版本 2",
            "versionNumber": 2,
        },
    }

    snapshot_response = client.get(f"/api/agent/runs/{run_id}")
    assert snapshot_response.json["artifacts"] == [
        {
            "stageId": "STRATEGY",
            "content": "# 测试策略蓝图\n\n版本 2",
            "versionNumber": 2,
        }
    ]


def test_agent_run_artifact_update_endpoint_rejects_invalid_stage(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        run_id = run.id

    response = client.post(
        f"/api/agent/runs/{run_id}/artifacts",
        json={
            "stageId": "REPORT",
            "content": "# 跨工作流产物",
        },
    )

    assert response.status_code == 400
    assert response.json == {
        "error": "workflowId 与 stageId 不匹配: TEST_DESIGN/REPORT"
    }


def test_agent_run_artifact_update_endpoint_rejects_blank_content(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        run_id = run.id

    response = client.post(
        f"/api/agent/runs/{run_id}/artifacts",
        json={
            "stageId": "STRATEGY",
            "content": " ",
        },
    )

    assert response.status_code == 400
    assert response.json == {"error": "content 不能为空"}


def test_agent_run_artifact_collaboration_endpoint_replaces_state(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        run_id = run.id

    response = client.put(
        f"/api/agent/runs/{run_id}/artifact-collaboration",
        json={
            "comments": [
                {
                    "id": "comment-1",
                    "stageId": "CLARIFY",
                    "content": "这里需要业务确认登录边界。",
                    "artifactExcerpt": "登录边界",
                    "anchorText": "登录边界",
                    "createdAt": 1710000000000,
                    "status": "resolved",
                    "resolvedAt": 1710000000300,
                    "replies": [
                        {
                            "id": "reply-1",
                            "content": "已补充登录异常边界。",
                            "createdAt": 1710000000200,
                        }
                    ],
                }
            ],
            "sectionLocks": [
                {
                    "id": "lock-1",
                    "stageId": "CLARIFY",
                    "heading": "## 业务规则",
                    "sectionAnchor": "h2:业务规则:1",
                    "content": "## 业务规则\n\n已确认登录规则。",
                    "createdAt": 1710000000100,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "artifactComments": [
            {
                "id": "comment-1",
                "stageId": "CLARIFY",
                "content": "这里需要业务确认登录边界。",
                "artifactExcerpt": "登录边界",
                "anchorText": "登录边界",
                "createdAt": 1710000000000,
                "status": "resolved",
                "resolvedAt": 1710000000300,
                "replies": [
                    {
                        "id": "reply-1",
                        "content": "已补充登录异常边界。",
                        "createdAt": 1710000000200,
                    }
                ],
            }
        ],
        "artifactSectionLocks": [
            {
                "id": "lock-1",
                "stageId": "CLARIFY",
                "heading": "## 业务规则",
                "sectionAnchor": "h2:业务规则:1",
                "content": "## 业务规则\n\n已确认登录规则。",
                "createdAt": 1710000000100,
            }
        ],
    }

    snapshot_response = client.get(f"/api/agent/runs/{run_id}")
    assert snapshot_response.json["artifactComments"] == response.json["artifactComments"]
    assert snapshot_response.json["artifactSectionLocks"] == response.json["artifactSectionLocks"]
    assert snapshot_response.json["artifactAuditEvents"] == [
        {
            "stageId": "CLARIFY",
            "eventType": "collaboration_updated",
            "summary": "更新了 CLARIFY 阶段协作状态：1 条批注，1 个章节锁",
            "createdAt": snapshot_response.json["artifactAuditEvents"][0]["createdAt"],
        }
    ]

    replacement_response = client.put(
        f"/api/agent/runs/{run_id}/artifact-collaboration",
        json={
            "comments": [],
            "sectionLocks": [
                {
                    "id": "lock-2",
                    "stageId": "CLARIFY",
                    "heading": "## 验收口径",
                    "sectionAnchor": "h2:验收口径:1",
                    "content": "## 验收口径\n\n验收标准已确认。",
                    "createdAt": 1710000000200,
                }
            ],
        },
    )

    assert replacement_response.status_code == 200
    assert replacement_response.json["artifactComments"] == []
    assert replacement_response.json["artifactSectionLocks"] == [
        {
            "id": "lock-2",
            "stageId": "CLARIFY",
            "heading": "## 验收口径",
            "sectionAnchor": "h2:验收口径:1",
            "content": "## 验收口径\n\n验收标准已确认。",
            "createdAt": 1710000000200,
        }
    ]


def test_agent_run_decision_summary_create_endpoint_persists_decision(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        run_id = run.id

    response = client.post(
        f"/api/agent/runs/{run_id}/context-summaries/decisions",
        json={
            "stageId": "STRATEGY",
            "content": "决定优先覆盖第三方登录回调失败",
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "sourceType": "artifact",
        "sourceStageId": "STRATEGY",
        "summaryType": "decision",
        "content": "决定优先覆盖第三方登录回调失败",
    }

    snapshot_response = client.get(f"/api/agent/runs/{run_id}")
    assert response.json in snapshot_response.json["contextSummaries"]


def test_agent_run_decision_summary_create_endpoint_rejects_invalid_stage(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        run_id = run.id

    response = client.post(
        f"/api/agent/runs/{run_id}/context-summaries/decisions",
        json={
            "stageId": "REPORT",
            "content": "跨工作流决策",
        },
    )

    assert response.status_code == 400
    assert response.json == {
        "error": "workflowId 与 stageId 不匹配: TEST_DESIGN/REPORT"
    }


def test_agent_runs_list_endpoint_returns_recent_runs_with_summaries(
    app,
    client,
    default_config,
):
    base_time = datetime(2026, 6, 19, 9, 0, 0)
    with app.app_context():
        older_run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY", model="gpt-old")
        append_run_message(older_run.id, "user", "旧需求")
        append_run_message(older_run.id, "assistant", "旧回复")
        record_artifact_version(
            older_run.id,
            "CLARIFY",
            "# 需求分析文档\n\n## 1. 被测系统与边界\n旧系统",
        )
        older_run_id = older_run.id

        newer_run = create_agent_run(
            "VALUE_DISCOVERY",
            "alex",
            "BLUEPRINT",
            model="gpt-new",
        )
        append_run_message(newer_run.id, "user", "新产品")
        append_run_message(newer_run.id, "assistant", "新回复")
        record_artifact_version(
            newer_run.id,
            "BLUEPRINT",
            "# 需求蓝图\n\n## 1. 产品概述\n新产品",
        )
        newer_run_id = newer_run.id

        db.session.get(AgentRun, older_run_id).updated_at = base_time
        db.session.get(AgentRun, newer_run_id).updated_at = base_time + timedelta(minutes=5)
        db.session.commit()

    response = client.get("/api/agent/runs")

    assert response.status_code == 200
    assert response.json["limit"] == 20
    assert [run["id"] for run in response.json["runs"]] == [
        newer_run_id,
        older_run_id,
    ]
    assert response.json["runs"][0] == {
        "id": newer_run_id,
        "workflowId": "VALUE_DISCOVERY",
        "agentId": "alex",
        "currentStageId": "BLUEPRINT",
        "status": "active",
        "model": "gpt-new",
        "createdAt": response.json["runs"][0]["createdAt"],
        "updatedAt": response.json["runs"][0]["updatedAt"],
        "lastMessage": {
            "role": "assistant",
            "content": "新回复",
            "sequenceIndex": 2,
        },
        "currentArtifact": {
            "stageId": "BLUEPRINT",
            "versionNumber": 1,
            "summary": response.json["runs"][0]["currentArtifact"]["summary"],
        },
    }
    assert "新产品" in response.json["runs"][0]["currentArtifact"]["summary"]


def test_agent_runs_list_endpoint_filters_by_workflow_id(
    app,
    client,
    default_config,
):
    with app.app_context():
        test_design_run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        value_run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        test_design_run_id = test_design_run.id
        value_run_id = value_run.id

    response = client.get("/api/agent/runs?workflowId=TEST_DESIGN&limit=1")

    assert response.status_code == 200
    assert response.json["limit"] == 1
    assert [run["id"] for run in response.json["runs"]] == [test_design_run_id]
    assert value_run_id not in [run["id"] for run in response.json["runs"]]


def test_agent_runs_list_endpoint_paginates_and_reports_more_runs(
    app,
    client,
    default_config,
):
    base_time = datetime(2026, 6, 19, 9, 0, 0)
    with app.app_context():
        oldest_run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        middle_run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        newest_run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        oldest_run_id = oldest_run.id
        middle_run_id = middle_run.id
        newest_run_id = newest_run.id

        db.session.get(AgentRun, oldest_run_id).updated_at = base_time
        db.session.get(AgentRun, middle_run_id).updated_at = base_time + timedelta(minutes=5)
        db.session.get(AgentRun, newest_run_id).updated_at = base_time + timedelta(minutes=10)
        db.session.commit()

    response = client.get("/api/agent/runs?workflowId=TEST_DESIGN&limit=1&offset=1")

    assert response.status_code == 200
    assert response.json["limit"] == 1
    assert response.json["offset"] == 1
    assert response.json["total"] == 3
    assert response.json["hasMore"] is True
    assert response.json["nextOffset"] == 2
    assert [run["id"] for run in response.json["runs"]] == [middle_run_id]
    assert newest_run_id not in [run["id"] for run in response.json["runs"]]


def test_agent_runs_list_endpoint_searches_messages_and_artifact_summaries(
    app,
    client,
    default_config,
):
    with app.app_context():
        message_run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(message_run.id, "user", "登录链路需要测试")
        artifact_run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(
            artifact_run.id,
            "STRATEGY",
            "# 测试策略蓝图\n\n支付链路要覆盖风控拦截",
        )
        create_agent_run("TEST_DESIGN", "lisa", "CASES")
        artifact_run_id = artifact_run.id

    response = client.get("/api/agent/runs?workflowId=TEST_DESIGN&query=支付&limit=10")

    assert response.status_code == 200
    assert response.json["query"] == "支付"
    assert response.json["total"] == 1
    assert response.json["hasMore"] is False
    assert response.json["nextOffset"] is None
    assert [run["id"] for run in response.json["runs"]] == [artifact_run_id]


def test_agent_runs_list_endpoint_rejects_unknown_workflow_id(
    client,
    default_config,
):
    response = client.get("/api/agent/runs?workflowId=UNKNOWN")

    assert response.status_code == 400
    assert response.json == {"error": "未知 workflowId: UNKNOWN"}


def test_agent_run_test_assets_endpoint_exports_cases_artifact(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    response = client.get(f"/api/agent/runs/{run_id}/test-assets")

    assert response.status_code == 200
    assert response.json["runId"] == run_id
    assert response.json["sourceStageId"] == "CASES"
    assert response.json["sourceArtifactVersion"] == 1
    assert response.json["testCases"] == [
        {
            "id": "TC-001",
            "title": "用户登录成功",
            "priority": "P0",
            "dimension": "正向功能验证",
            "testPoint": "登录主链路",
            "risk": "R-LOGIN-001",
            "precondition": "用户已注册",
            "steps": "1. 输入账号密码 2. 点击登录",
            "testData": "正确账号密码",
            "expectedResult": "进入工作台",
            "assertion": "工作台可见且登录态存在",
            "executionLayer": "E2E",
            "automationSuggestion": "优先自动化",
            "status": "可执行",
        }
    ]
    assert response.json["coverageTrace"] == [
        {
            "testPoint": "登录主链路",
            "priority": "P0",
            "risk": "R-LOGIN-001",
            "testCases": ["TC-001"],
            "status": "已覆盖",
        }
    ]
    assert response.json["coverageSummary"] == {
        "totalTestCases": 1,
        "totalTestPoints": 1,
        "coveredTestPoints": 1,
        "partiallyCoveredTestPoints": 0,
        "uncoveredTestPoints": 0,
        "coverageRate": 100.0,
        "byPriority": [
            {
                "priority": "P0",
                "total": 1,
                "covered": 1,
                "partial": 0,
                "uncovered": 0,
                "coverageRate": 100.0,
            }
        ],
    }
    assert response.json["assetIssues"] == []
    assert response.json["riskMatrix"] == [
        {
            "risk": "R-LOGIN-001",
            "testCases": ["TC-001"],
            "testPoints": ["登录主链路"],
            "priorities": ["P0"],
            "dimensions": ["正向功能验证"],
            "coverageStatuses": ["已覆盖"],
        }
    ]
    assert response.json["intentTesterDrafts"][0]["sourceCaseId"] == "TC-001"
    assert response.json["intentTesterDrafts"][0]["priority"] == 1
    assert response.json["intentTesterDrafts"][0]["steps"][0]["action"] == "ai_assert"


def test_agent_run_test_assets_materialize_endpoint_persists_collection(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    response = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize")

    assert response.status_code == 200
    collection_id = response.json["id"]
    assert response.json["runId"] == run_id
    assert response.json["sourceArtifactVersion"] == 1
    assert response.json["testCases"][0]["id"] == "TC-001"
    assert response.json["testCases"][0]["versionNumber"] == 1

    detail_response = client.get(f"/api/agent/test-assets/{collection_id}")

    assert detail_response.status_code == 200
    assert detail_response.json["id"] == collection_id
    assert detail_response.json["testCases"][0]["versions"][0]["title"] == "用户登录成功"


def test_agent_test_assets_case_update_endpoint_creates_new_version(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    response = client.patch(
        f"/api/agent/test-assets/{collection['id']}/test-cases/TC-001",
        json={"priority": "P1", "title": "登录成功后进入首页"},
    )

    assert response.status_code == 200
    assert response.json["id"] == "TC-001"
    assert response.json["priority"] == "P1"
    assert response.json["title"] == "登录成功后进入首页"
    assert response.json["versionNumber"] == 2


def test_agent_test_assets_intent_tester_case_endpoint_persists_mapping(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    response = client.patch(
        f"/api/agent/test-assets/{collection['id']}/intent-tester/cases/TC-001",
        json={
            "intentTesterCaseId": 42,
            "intentTesterCaseName": "TC-001 用户登录成功",
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "sourceCaseId": "TC-001",
        "intentTesterCaseId": 42,
        "intentTesterCaseName": "TC-001 用户登录成功",
        "latestExecution": None,
        "latestResult": None,
    }

    detail_response = client.get(f"/api/agent/test-assets/{collection['id']}")

    assert detail_response.status_code == 200
    assert detail_response.json["intentTesterMappings"] == [response.json]


def test_agent_test_assets_intent_tester_execution_endpoint_persists_latest_execution(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    client.patch(
        f"/api/agent/test-assets/{collection['id']}/intent-tester/cases/TC-001",
        json={
            "intentTesterCaseId": 42,
            "intentTesterCaseName": "TC-001 用户登录成功",
        },
    )
    response = client.patch(
        f"/api/agent/test-assets/{collection['id']}/intent-tester/cases/TC-001/execution",
        json={
            "executionId": "exec-123",
            "status": "pending",
            "mode": "headless",
            "browser": "chrome",
            "startTime": "2026-06-19T10:00:00",
            "endTime": None,
            "duration": None,
            "errorMessage": None,
        },
    )

    assert response.status_code == 200
    assert response.json["latestExecution"] == {
        "executionId": "exec-123",
        "testCaseId": 42,
        "status": "pending",
        "mode": "headless",
        "browser": "chrome",
        "startTime": "2026-06-19T10:00:00",
        "endTime": None,
        "duration": None,
        "errorMessage": None,
    }

    detail_response = client.get(f"/api/agent/test-assets/{collection['id']}")

    assert detail_response.status_code == 200
    assert detail_response.json["intentTesterMappings"] == [response.json]


def test_agent_test_assets_intent_tester_result_endpoint_persists_snapshot(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    client.patch(
        f"/api/agent/test-assets/{collection['id']}/intent-tester/cases/TC-001",
        json={
            "intentTesterCaseId": 42,
            "intentTesterCaseName": "TC-001 用户登录成功",
        },
    )
    response = client.patch(
        f"/api/agent/test-assets/{collection['id']}/intent-tester/cases/TC-001/result",
        json={
            "executionId": "exec-456",
            "status": "failed",
            "duration": 60,
            "errorMessage": "断言失败",
            "steps": [
                {
                    "stepIndex": 0,
                    "description": "打开登录页",
                    "status": "success",
                    "screenshotPath": "/static/screenshots/step-0.png",
                    "action": "ai_assert",
                },
                {
                    "stepIndex": 1,
                    "description": "验证预期结果",
                    "status": "failed",
                    "errorMessage": "未看到工作台",
                    "screenshotPath": "/static/screenshots/step-1.png",
                    "action": "ai_assert",
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json["latestResult"]["stepsTotal"] == 2
    assert response.json["latestResult"]["stepsPassed"] == 1
    assert response.json["latestResult"]["stepsFailed"] == 1
    assert response.json["latestResult"]["failedSteps"] == [
        {
            "stepIndex": 1,
            "description": "验证预期结果",
            "status": "failed",
            "errorMessage": "未看到工作台",
            "screenshotPath": "/static/screenshots/step-1.png",
            "action": "ai_assert",
        }
    ]

    detail_response = client.get(f"/api/agent/test-assets/{collection['id']}")

    assert detail_response.status_code == 200
    assert detail_response.json["intentTesterMappings"][0]["latestResult"] == response.json["latestResult"]


def test_agent_test_assets_issue_status_update_endpoint_persists_status(
    app,
    client,
    default_config,
):
    inconsistent_cases_artifact = VALID_CASES_ARTIFACT.replace(
        "TC-001 | 已覆盖",
        "TC-999 | 已覆盖",
    )
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", inconsistent_cases_artifact)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    issue_id = collection["assetIssues"][0]["id"]
    response = client.patch(
        f"/api/agent/test-assets/{collection['id']}/issues/{issue_id}",
        json={"status": "confirmed"},
    )

    assert response.status_code == 200
    assert response.json["id"] == issue_id
    assert response.json["status"] == "confirmed"

    detail_response = client.get(f"/api/agent/test-assets/{collection['id']}")

    assert detail_response.status_code == 200
    assert detail_response.json["assetIssues"][0]["status"] == "confirmed"


def test_agent_test_assets_test_point_update_endpoint_persists_calibration(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    response = client.patch(
        f"/api/agent/test-assets/{collection['id']}/test-points/登录主链路",
        json={
            "priority": "P1",
            "risk": "R-LOGIN-LOCK",
            "status": "未覆盖",
            "testCases": [],
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "testPoint": "登录主链路",
        "priority": "P1",
        "risk": "R-LOGIN-LOCK",
        "testCases": [],
        "status": "未覆盖",
    }

    detail_response = client.get(f"/api/agent/test-assets/{collection['id']}")

    assert detail_response.status_code == 200
    assert detail_response.json["coverageSummary"]["coveredTestPoints"] == 0
    assert detail_response.json["coverageSummary"]["uncoveredTestPoints"] == 1
    risk = next(
        item for item in detail_response.json["riskMatrix"] if item["risk"] == "R-LOGIN-LOCK"
    )
    assert risk["id"] > 0
    assert risk["isManual"] is False
    assert risk["testCases"] == []
    assert risk["testPoints"] == ["登录主链路"]
    assert risk["priorities"] == ["P1"]
    assert risk["dimensions"] == []
    assert risk["coverageStatuses"] == ["未覆盖"]
    assert risk["status"] == "open"
    assert risk["owner"] == ""
    assert risk["note"] == ""


def test_agent_test_assets_test_point_update_endpoint_returns_404_for_unknown_point(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    response = client.patch(
        f"/api/agent/test-assets/{collection['id']}/test-points/不存在的测试点",
        json={"status": "已覆盖"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "未知测试点: 不存在的测试点"}


def test_agent_test_assets_risk_lifecycle_update_endpoint_persists_status(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    response = client.patch(
        f"/api/agent/test-assets/{collection['id']}/risks/R-LOGIN-001",
        json={
            "status": "mitigating",
            "owner": "QA 王五",
            "note": "补充异常登录验证",
        },
    )

    assert response.status_code == 200
    assert response.json["risk"] == "R-LOGIN-001"
    assert response.json["status"] == "mitigating"
    assert response.json["owner"] == "QA 王五"
    assert response.json["note"] == "补充异常登录验证"

    detail_response = client.get(f"/api/agent/test-assets/{collection['id']}")

    assert detail_response.status_code == 200
    assert detail_response.json["riskMatrix"][0]["status"] == "mitigating"
    assert detail_response.json["riskMatrix"][0]["owner"] == "QA 王五"
    assert detail_response.json["riskMatrix"][0]["note"] == "补充异常登录验证"


def test_agent_test_assets_risk_lifecycle_update_endpoint_returns_404_for_unknown_risk(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    response = client.patch(
        f"/api/agent/test-assets/{collection['id']}/risks/R-UNKNOWN",
        json={"status": "closed"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "未知风险: R-UNKNOWN"}


def test_risk_library_create_endpoint_adds_manual_risk(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    response = client.post(
        f"/api/agent/test-assets/{collection['id']}/risks",
        json={
            "risk": "R-MANUAL-API",
            "status": "accepted",
            "owner": "QA API",
            "note": "通过 API 新增",
        },
    )

    assert response.status_code == 200
    assert response.json["risk"] == "R-MANUAL-API"
    assert response.json["isManual"] is True
    assert response.json["testCases"] == []
    assert response.json["status"] == "accepted"


def test_risk_library_update_by_id_endpoint_renames_linked_risk(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    risk_id = collection["riskMatrix"][0]["id"]
    response = client.patch(
        f"/api/agent/test-assets/{collection['id']}/risks/by-id/{risk_id}",
        json={"risk": "R-LOGIN-RENAMED", "status": "mitigating"},
    )

    assert response.status_code == 200
    assert response.json["id"] == risk_id
    assert response.json["risk"] == "R-LOGIN-RENAMED"
    assert response.json["status"] == "mitigating"

    detail_response = client.get(f"/api/agent/test-assets/{collection['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json["riskMatrix"][0]["id"] == risk_id
    assert detail_response.json["riskMatrix"][0]["risk"] == "R-LOGIN-RENAMED"
    assert detail_response.json["testPoints"][0]["risk"] == "R-LOGIN-RENAMED"
    assert detail_response.json["testCases"][0]["risk"] == "R-LOGIN-RENAMED"
    assert detail_response.json["testCases"][0]["versionNumber"] == 2


def test_risk_library_delete_endpoint_removes_unlinked_risk(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    created = client.post(
        f"/api/agent/test-assets/{collection['id']}/risks",
        json={"risk": "R-MANUAL-DELETE-API"},
    ).json

    response = client.delete(
        f"/api/agent/test-assets/{collection['id']}/risks/by-id/{created['id']}"
    )

    assert response.status_code == 200
    assert response.json == {"id": created["id"], "deleted": True}


def test_risk_library_delete_endpoint_rejects_linked_risk(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", VALID_CASES_ARTIFACT)
        run_id = run.id

    collection = client.post(f"/api/agent/runs/{run_id}/test-assets/materialize").json
    risk_id = collection["riskMatrix"][0]["id"]
    response = client.delete(
        f"/api/agent/test-assets/{collection['id']}/risks/by-id/{risk_id}"
    )

    assert response.status_code == 400
    assert response.json == {"error": "风险仍有关联资产，无法删除: R-LOGIN-001"}


def test_agent_run_test_assets_endpoint_returns_404_without_cases_artifact(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        run_id = run.id

    response = client.get(f"/api/agent/runs/{run_id}/test-assets")

    assert response.status_code == 404
    assert response.json == {"error": "缺少 TEST_DESIGN/CASES 测试用例集"}


def test_agent_run_handoffs_endpoint_exports_configured_targets(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(run.id, "BLUEPRINT", VALID_BLUEPRINT_ARTIFACT)
        run_id = run.id

    response = client.get(f"/api/agent/runs/{run_id}/handoffs")

    assert response.status_code == 200
    assert response.json["runId"] == run_id
    assert [
        (handoff["targetWorkflowId"], handoff["targetStageId"], handoff["targetAgentId"])
        for handoff in response.json["handoffs"]
    ] == [
        ("TEST_DESIGN", "CLARIFY", "lisa"),
        ("REQ_REVIEW", "REVIEW", "lisa"),
    ]
    assert response.json["handoffs"][0]["sourceArtifactVersion"] == 1
    assert response.json["handoffs"][0]["sourceSummary"].startswith(
        "AI 测试资产管理平台需求蓝图"
    )
    assert response.json["handoffs"][0]["unconfirmedItems"] == [
        "开放问题 Q-001: 锁定策略是否需要纳入首轮测试设计"
    ]
    assert response.json["handoffs"][0]["targetInputChecklist"] == [
        "复核来源版本 VALUE_DISCOVERY/BLUEPRINT v1",
        "确认目标阶段 TEST_DESIGN/CLARIFY 所需的需求、验收标准和约束均已覆盖",
        "处理 1 个未确认项后再进入目标产物生成",
    ]
    assert "来源版本: VALUE_DISCOVERY/BLUEPRINT v1" in response.json["handoffs"][0]["prompt"]
    assert "AI 测试资产管理平台" in response.json["handoffs"][0]["prompt"]


def test_agent_run_handoff_start_endpoint_creates_target_run(
    app,
    client,
    default_config,
):
    with app.app_context():
        run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(run.id, "BLUEPRINT", VALID_BLUEPRINT_ARTIFACT)
        run_id = run.id

    response = client.post(
        f"/api/agent/runs/{run_id}/handoffs/value-discovery-blueprint-to-test-design/start"
    )

    assert response.status_code == 200
    assert response.json["sourceRunId"] == run_id
    assert response.json["targetRunId"]
    assert response.json["targetWorkflowId"] == "TEST_DESIGN"
    assert response.json["targetStageId"] == "CLARIFY"
    assert response.json["targetAgentId"] == "lisa"
    assert response.json["sourceSummary"].startswith("AI 测试资产管理平台需求蓝图")
    assert response.json["unconfirmedItems"] == [
        "开放问题 Q-001: 锁定策略是否需要纳入首轮测试设计"
    ]
    assert response.json["targetInputChecklist"][0] == "复核来源版本 VALUE_DISCOVERY/BLUEPRINT v1"
    assert "AI 测试资产管理平台" in response.json["prompt"]


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


def test_agent_runs_stream_records_default_llm_missing_observability_issue(
    app,
    client,
):
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
    with app.app_context():
        assert AgentRun.query.count() == 0

    observability_response = client.get("/api/agent/observability")

    assert observability_response.status_code == 200
    assert observability_response.json["totals"]["turns"] == 1
    assert observability_response.json["totals"]["failedTurns"] == 1
    assert observability_response.json["totals"]["successRate"] == 0.0
    assert observability_response.json["totals"]["estimatedTokens"] == 0
    assert observability_response.json["totals"]["providerIssueCount"] == 1
    assert observability_response.json["totals"]["providerIssueCodes"] == {
        "DEFAULT_LLM_CONFIG_MISSING": 1
    }
    assert observability_response.json["byStage"] == [
        {
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "turns": 1,
            "failedTurns": 1,
            "successRate": 0.0,
            "avgDurationMs": 0.0,
            "estimatedTokens": 0,
            "errorCodes": {"DEFAULT_LLM_CONFIG_MISSING": 1},
            "providerIssueCount": 1,
            "providerIssueCodes": {"DEFAULT_LLM_CONFIG_MISSING": 1},
        }
    ]
    assert observability_response.json["byProvider"] == []
    assert observability_response.json["recentTurns"] == []


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
    payloads = _parse_sse_event_payloads(response)
    assert payloads[0]["type"] == "run_started"
    assert payloads[0]["runId"]
    assert payloads[1:] == [
        {
            "type": "error",
            "code": "SCHEMA_VALIDATION_FAILED",
            "message": (
                "模型连续生成的结构化结果未通过校验。请重试本轮操作；"
                "如果多次失败，请补充更明确的需求或阶段确认信息。"
            ),
        }
    ]


@patch("stream_services.build_pydantic_agent_runtime")
def test_agent_observability_endpoint_returns_runtime_turn_summary(
    mock_build_runtime,
    client,
    default_config,
):
    mock_build_runtime.return_value = FakeRuntime()
    success_response = client.post(
        "/api/agent/runs/stream",
        json={
            "prompt": "用户需求: 登录功能",
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
        },
    )
    assert success_response.status_code == 200
    success_response.get_data(as_text=True)

    mock_build_runtime.return_value = FailingRuntime(
        UnexpectedModelBehavior("Exceeded maximum output retries (3)")
    )
    error_response = client.post(
        "/api/agent/runs/stream",
        json={
            "prompt": "用户需求: 支付功能",
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
        },
    )
    assert error_response.status_code == 200
    error_response.get_data(as_text=True)

    response = client.get("/api/agent/observability")

    assert response.status_code == 200
    assert response.json["totals"]["turns"] == 2
    assert response.json["totals"]["failedTurns"] == 1
    assert response.json["totals"]["successRate"] == 50.0
    assert response.json["totals"]["estimatedTokens"] > 0
    assert response.json["byStage"] == [
        {
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "turns": 2,
            "failedTurns": 1,
            "successRate": 50.0,
            "avgDurationMs": response.json["byStage"][0]["avgDurationMs"],
            "estimatedTokens": response.json["byStage"][0]["estimatedTokens"],
            "errorCodes": {"SCHEMA_VALIDATION_FAILED": 1},
            "providerIssueCount": 0,
            "providerIssueCodes": {},
        }
    ]
    assert response.json["byProvider"] == [
        {
            "provider": "api.test.com",
            "turns": 2,
            "failedTurns": 1,
            "successRate": 50.0,
            "avgDurationMs": response.json["byProvider"][0]["avgDurationMs"],
            "estimatedTokens": response.json["byProvider"][0]["estimatedTokens"],
            "errorCodes": {"SCHEMA_VALIDATION_FAILED": 1},
            "providerIssueCount": 0,
            "providerIssueCodes": {},
        }
    ]
    assert response.json["recentTurns"][0]["runId"]
    assert response.json["recentTurns"][0]["provider"] == "api.test.com"
    assert response.json["recentTurns"][0]["status"] in {"success", "error"}


def test_agent_observability_endpoint_filters_by_workflow_and_stage(
    app,
    client,
    ):
    with app.app_context():
        clarify_run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        clarify_run_id = clarify_run.id
        record_turn_metric(
            run_id=clarify_run_id,
            workflow_id="TEST_DESIGN",
            stage_id="CLARIFY",
            model_name="test-model",
            provider="api.test.com",
            status="success",
            error_code=None,
            duration_ms=100,
            input_chars=100,
            output_chars=200,
            estimated_tokens=75,
            contract_retry_count=0,
        )
        strategy_run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_turn_metric(
            run_id=strategy_run.id,
            workflow_id="TEST_DESIGN",
            stage_id="STRATEGY",
            model_name="test-model",
            provider="api.test.com",
            status="error",
            error_code="SCHEMA_VALIDATION_FAILED",
            duration_ms=200,
            input_chars=150,
            output_chars=250,
            estimated_tokens=100,
            contract_retry_count=0,
        )
        value_run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_turn_metric(
            run_id=value_run.id,
            workflow_id="VALUE_DISCOVERY",
            stage_id="BLUEPRINT",
            model_name="test-model",
            provider="api.other.com",
            status="success",
            error_code=None,
            duration_ms=300,
            input_chars=200,
            output_chars=300,
            estimated_tokens=125,
            contract_retry_count=0,
        )

    response = client.get(
        "/api/agent/observability?workflowId=TEST_DESIGN&stageId=CLARIFY"
    )

    assert response.status_code == 200
    assert response.json["totals"]["turns"] == 1
    assert response.json["totals"]["failedTurns"] == 0
    assert response.json["byStage"] == [
        {
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "turns": 1,
            "failedTurns": 0,
            "successRate": 100.0,
            "avgDurationMs": 100.0,
            "estimatedTokens": 75,
            "errorCodes": {},
            "providerIssueCount": 0,
            "providerIssueCodes": {},
        }
    ]
    assert response.json["byProvider"][0]["provider"] == "api.test.com"
    assert response.json["recentTurns"] == [
        {
            "id": response.json["recentTurns"][0]["id"],
            "runId": clarify_run_id,
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "model": "test-model",
            "provider": "api.test.com",
            "status": "success",
            "errorCode": None,
            "durationMs": 100,
            "inputChars": 100,
            "outputChars": 200,
            "estimatedTokens": 75,
            "contractRetryCount": 0,
            "createdAt": response.json["recentTurns"][0]["createdAt"],
        }
    ]


def test_agent_observability_endpoint_groups_provider_issue_codes(
    app,
    client,
):
    with app.app_context():
        provider_run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        record_turn_metric(
            run_id=provider_run.id,
            workflow_id="TEST_DESIGN",
            stage_id="CLARIFY",
            model_name="test-model",
            provider="api.test.com",
            status="error",
            error_code="LLM_ERROR",
            duration_ms=200,
            input_chars=100,
            output_chars=50,
            estimated_tokens=40,
            contract_retry_count=0,
        )
        contract_run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_turn_metric(
            run_id=contract_run.id,
            workflow_id="TEST_DESIGN",
            stage_id="STRATEGY",
            model_name="test-model",
            provider="api.test.com",
            status="error",
            error_code="SCHEMA_VALIDATION_FAILED",
            duration_ms=300,
            input_chars=120,
            output_chars=80,
            estimated_tokens=50,
            contract_retry_count=3,
        )
        runtime_run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_turn_metric(
            run_id=runtime_run.id,
            workflow_id="TEST_DESIGN",
            stage_id="CASES",
            model_name="test-model",
            provider="api.test.com",
            status="error",
            error_code="AGENT_RUNTIME_UNAVAILABLE",
            duration_ms=250,
            input_chars=90,
            output_chars=10,
            estimated_tokens=25,
            contract_retry_count=0,
        )

    response = client.get("/api/agent/observability")

    assert response.status_code == 200
    assert response.json["totals"]["providerIssueCount"] == 1
    assert response.json["totals"]["providerIssueCodes"] == {"LLM_ERROR": 1}
    clarify_stage = next(
        stage for stage in response.json["byStage"]
        if stage["stageId"] == "CLARIFY"
    )
    strategy_stage = next(
        stage for stage in response.json["byStage"]
        if stage["stageId"] == "STRATEGY"
    )
    cases_stage = next(
        stage for stage in response.json["byStage"]
        if stage["stageId"] == "CASES"
    )
    assert clarify_stage["providerIssueCount"] == 1
    assert clarify_stage["providerIssueCodes"] == {"LLM_ERROR": 1}
    assert strategy_stage["providerIssueCount"] == 0
    assert strategy_stage["providerIssueCodes"] == {}
    assert cases_stage["providerIssueCount"] == 0
    assert cases_stage["providerIssueCodes"] == {}
    assert response.json["byProvider"][0]["providerIssueCount"] == 1
    assert response.json["byProvider"][0]["providerIssueCodes"] == {"LLM_ERROR": 1}


def test_agent_observability_endpoint_rejects_stage_without_workflow(client):
    response = client.get("/api/agent/observability?stageId=CLARIFY")

    assert response.status_code == 400
    assert response.json["error"] == "stageId 需要与 workflowId 一起使用"
