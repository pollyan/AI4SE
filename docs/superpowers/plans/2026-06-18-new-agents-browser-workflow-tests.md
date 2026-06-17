# New Agents Browser Workflow Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an independent browser test framework that verifies Lisa `test-design` and Alex `value-discovery` complete their full New Agents UI workflows without using the intent-tester tooling.

**Architecture:** Add a root-level `pytest-playwright` suite under `tests/e2e/new_agents_browser`. The suite starts the New Agents Vite frontend, mocks only `/new-agents/api/config` and `/new-agents/api/agent/runs/stream`, drives the real browser UI, and optionally runs an environment-configured LLM judge against final artifacts.

**Tech Stack:** Python 3.11, pytest, pytest-playwright, Playwright sync API, Vite dev server, React New Agents frontend.

---

## File Structure

- Create: `tests/e2e/new_agents_browser/__init__.py`
  - Marks the framework package.
- Create: `tests/e2e/new_agents_browser/conftest.py`
  - Starts/stops Vite, exposes browser page fixtures, resets storage, installs route mocks, records console errors.
- Create: `tests/e2e/new_agents_browser/sse_mock.py`
  - Defines deterministic stage artifacts and builds SSE responses.
- Create: `tests/e2e/new_agents_browser/workflow_runner.py`
  - Encapsulates reusable browser workflow actions and assertions.
- Create: `tests/e2e/new_agents_browser/llm_judge.py`
  - Provides optional environment-gated LLM artifact review.
- Create: `tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py`
  - Verifies Lisa `test-design` four-stage workflow.
- Create: `tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py`
  - Verifies Alex `value-discovery` four-stage workflow.
- Modify: `docs/TESTING.md`
  - Document the new browser workflow command and optional judge environment.

## Task 1: Deterministic SSE Mock

**Files:**
- Create: `tests/e2e/new_agents_browser/__init__.py`
- Create: `tests/e2e/new_agents_browser/sse_mock.py`

- [ ] **Step 1: Write the mock module**

Create `tests/e2e/new_agents_browser/__init__.py` as an empty file.

Create `tests/e2e/new_agents_browser/sse_mock.py` with:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StagePayload:
    chat: str
    markdown: str
    next_stage_id: str | None = None


STAGE_PAYLOADS: dict[tuple[str, str], StagePayload] = {
    ("TEST_DESIGN", "CLARIFY"): StagePayload(
        chat="需求澄清完成，请确认进入策略制定。",
        next_stage_id="STRATEGY",
        markdown="""# 需求分析文档

## 1. 被测系统与边界
登录与支付联动能力是本次被测系统，覆盖账号密码登录、短信验证码登录、支付提交、失败重试和账号锁定。

## 2. 系统交互与核心链路
用户从登录页进入，完成身份校验后进入支付页，支付结果回写订单中心。

## 3. 待澄清与阻断性问题
| 问题 | 状态 |
| --- | --- |
| 账号锁定阈值是否为 5 次失败 | 已确认 |

## 4. 隐式需求与非功能性考量
需要覆盖并发登录、敏感信息脱敏、安全审计和移动端兼容性。
""",
    ),
    ("TEST_DESIGN", "STRATEGY"): StagePayload(
        chat="测试策略蓝图完成，请确认进入用例编写。",
        next_stage_id="CASES",
        markdown="""# 测试策略蓝图

## 1. 质量目标
- P0 主链路上线前全部通过。
- 高风险安全场景必须有自动化或专项验证。

## 2. 风险分析

### 2.1 风险矩阵
| 风险 | 优先级 |
| --- | --- |
| 登录绕过 | P0 |

### 2.2 风险明细
| ID | 风险名称 | 缓解策略 |
| --- | --- | --- |
| R-001 | 账号锁定失效 | 覆盖连续失败和解锁流程 |

## 3. 测试技术选型
| ID | 技术 | 理由 |
| --- | --- | --- |
| TS-001 | API + E2E | 同时覆盖契约和主链路 |

## 4. 测试分层策略

### 4.1 测试金字塔
单元 50%，集成 30%，E2E 20%。

### 4.2 分层明细
| 层级 | 范围 |
| --- | --- |
| E2E | 登录到支付成功 |

## 5. 测试点拓扑
| ID | 测试点 | 优先级 |
| --- | --- | --- |
| TP-001 | 登录成功后支付 | P0 |
""",
    ),
    ("TEST_DESIGN", "CASES"): StagePayload(
        chat="测试用例集完成，请确认进入文档交付。",
        next_stage_id="DELIVERY",
        markdown="""# 测试用例集

## 1. 用例统计
共 6 条用例，P0 4 条，P1 2 条。

## 2. 用例清单
| ID | 用例标题 | 优先级 | 操作步骤 | 预期结果 |
| --- | --- | --- | --- | --- |
| TC-001 | 密码登录成功后支付 | P0 | 输入正确账号密码并提交支付 | 支付成功并生成订单 |
| TC-002 | 连续失败触发锁定 | P0 | 连续输入错误密码 | 账号被锁定并记录审计 |

## 3. 测试点覆盖追溯
| 测试点 | 覆盖用例 | 覆盖状态 |
| --- | --- | --- |
| 登录成功后支付 | TC-001 | 已覆盖 |
""",
    ),
    ("TEST_DESIGN", "DELIVERY"): StagePayload(
        chat="测试设计交付文档已完成。",
        markdown="""# 测试设计文档

## 文档信息
项目名称：登录支付链路测试设计。

## 第一部分：需求分析
覆盖登录、支付、失败重试、账号锁定和安全审计。

## 第二部分：测试策略
以 P0 主链路和高风险安全场景为优先级核心。

## 第三部分：测试用例
包含正向、异常、安全和兼容性用例。

## 附录：验收标准
- 所有 P0 用例通过。
- 高风险项均有对应缓解策略。
""",
    ),
    ("VALUE_DISCOVERY", "ELEVATOR"): StagePayload(
        chat="价值定位分析完成，请确认进入用户画像。",
        next_stage_id="PERSONA",
        markdown="""# 价值定位分析

## 产品核心定位
面向测试团队的 AI 测试设计助手，帮助从需求快速生成测试策略和用例。

## 目标用户概览
| 维度 | 描述 |
| --- | --- |
| 主要用户群体 | 中大型软件团队的测试负责人 |

## 独特价值主张
| 维度 | 我们 | 现有方案/竞品 |
| --- | --- | --- |
| 核心优势 | 结构化引导并沉淀产物 | 依赖人工经验 |

## 商业可行性初判
| 维度 | 判断 |
| --- | --- |
| 用户付费意愿 | 对节省测试设计时间有明确预算 |

## ✅ 60 秒电梯演讲
我们帮助测试团队把模糊需求快速转化为可执行测试资产。
""",
    ),
    ("VALUE_DISCOVERY", "PERSONA"): StagePayload(
        chat="用户画像分析完成，请确认进入用户旅程。",
        next_stage_id="JOURNEY",
        markdown="""# 用户画像分析

## 主要用户画像

### 画像 1：测试负责人

#### 基础特征
管理 5 到 20 人测试团队，关注质量风险和交付效率。

#### 行为特征
经常参与需求评审、测试计划制定和上线风险评估。

#### 需求动机
希望减少重复文档工作，同时提高风险识别完整度。

#### 核心痛点
| 痛点 | 频率 | 影响程度 | 现有方案不足 |
| --- | --- | --- | --- |
| 用例设计耗时 | 每周 | 高 | 人工依赖强 |

## 用户优先级排序
| 优先级 | 用户类型 | 理由 |
| --- | --- | --- |
| 核心用户 | 测试负责人 | 直接承担质量交付责任 |
""",
    ),
    ("VALUE_DISCOVERY", "JOURNEY"): StagePayload(
        chat="用户旅程分析完成，请确认进入需求蓝图。",
        next_stage_id="BLUEPRINT",
        markdown="""# 用户旅程分析

## 用户旅程地图
从需求输入到策略制定、用例编写、评审交付。

## 关键阶段详细分析
| 阶段 | 用户目标 | 主要痛点 |
| --- | --- | --- |
| 需求评审 | 找出风险 | 信息不完整 |

## 痛点优先级排序

### 🔥 高优先级痛点（必须解决）
测试设计耗时且遗漏风险。

### 📋 中等优先级痛点（应该解决）
用例格式和覆盖追溯不统一。

### 💡 低优先级痛点（可以解决）
导出格式需要适配团队模板。

## 核心机会点

### 🎯 主要机会点
用结构化智能体引导测试设计。

### 产品切入策略
优先切入需求评审后的测试策略和用例生成环节。
""",
    ),
    ("VALUE_DISCOVERY", "BLUEPRINT"): StagePayload(
        chat="需求蓝图已完成。",
        markdown="""# AI 测试设计助手需求蓝图

## 文档信息
| 维度 | 内容 |
| --- | --- |
| 产品方向 | AI 辅助测试设计 |

## 1. 产品概述

### 1.1 产品愿景
让测试团队更快识别风险并沉淀高质量测试资产。

### 1.2 定位声明
For 测试负责人 who 需要快速完成测试设计，the AI 测试设计助手 is a 结构化智能体工具 that 生成策略和用例。

### 1.3 核心价值
| 维度 | 描述 |
| --- | --- |
| 用户价值 | 节省测试设计时间 |

## 2. 目标用户（摘要）
测试负责人和资深测试工程师。

## 3. 核心需求

### 功能架构
需求输入、风险分析、策略生成、用例生成、交付导出。

### P0 需求（核心功能，必须实现）
| ID | 需求名称 | 验收标准 |
| --- | --- | --- |
| F-001 | 生成测试策略 | 包含风险和分层策略 |

### P1 需求（重要功能，应该实现）
团队模板适配。

### P2 需求（增值功能，可以实现）
历史项目复用。

## 4. 核心流程

### 主流程图
用户输入需求后，系统生成多阶段测试设计产物。

## 5. 成功指标
| 指标类型 | 指标名称 | 目标值 |
| --- | --- | --- |
| 产品指标 | 测试设计耗时降低 | 30% |

## 6. MVP 范围与计划

### MVP 包含功能
- F-001: 生成测试策略

### 迭代路线
| 版本 | 核心功能 |
| --- | --- |
| v1.0 | 策略和用例生成 |

## 7. 风险评估
| 风险类型 | 风险描述 | 缓解措施 |
| --- | --- | --- |
| 产品风险 | 输出不稳定 | 契约校验和人工确认 |
""",
    ),
}


def build_agent_sse_response(request_body: dict[str, Any]) -> str:
    workflow_id = request_body["workflowId"]
    stage_id = request_body["stageId"]
    payload = STAGE_PAYLOADS[(workflow_id, stage_id)]
    output: dict[str, Any] = {
        "chat": payload.chat,
        "artifact_update": {
            "type": "replace",
            "markdown": payload.markdown,
        },
        "stage_action": None,
        "warnings": [],
    }
    if payload.next_stage_id:
        output["stage_action"] = {
            "type": "request_next_stage",
            "target_stage_id": payload.next_stage_id,
        }
    event = {"type": "agent_turn", "output": output}
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\ndata: [DONE]\n\n"
```

- [ ] **Step 2: Run an import check**

Run:

```bash
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -q
```

Expected: pytest reports no tests collected or import success. If Playwright plugin is missing, install project requirements before continuing.

## Task 2: Browser Fixtures And Route Mocks

**Files:**
- Create: `tests/e2e/new_agents_browser/conftest.py`

- [ ] **Step 1: Write the fixture module**

Create `tests/e2e/new_agents_browser/conftest.py` with:

```python
from __future__ import annotations

import os
import socket
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import pytest
import requests
from playwright.sync_api import Browser, Page, Route, expect

from .sse_mock import build_agent_sse_response


ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = ROOT / "tools" / "new-agents" / "frontend"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + 30
    last_error = ""
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Vite dev server exited before becoming ready")
        try:
            response = requests.get(url, timeout=0.5)
            if response.status_code < 500:
                return
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise RuntimeError(f"Vite dev server did not start at {url}: {last_error}")


@pytest.fixture(scope="session")
def new_agents_base_url() -> Generator[str, None, None]:
    port = int(os.environ.get("NEW_AGENTS_E2E_PORT", "0")) or _free_port()
    base_url = f"http://127.0.0.1:{port}/new-agents/"
    command = [
        "npm",
        "run",
        "dev",
        "--",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--strictPort",
    ]
    env = {**os.environ, "DISABLE_HMR": "true"}
    process = subprocess.Popen(
        command,
        cwd=FRONTEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_server(base_url, process)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.fixture()
def new_agents_page(browser: Browser, new_agents_base_url: str) -> Generator[Page, None, None]:
    context = browser.new_context(base_url=new_agents_base_url)
    page = context.new_page()
    console_errors: list[str] = []
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )

    def route_config(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"hasDefault": true, "baseUrl": "mock", "model": "mock"}',
        )

    def route_agent_stream(route: Route) -> None:
        body = route.request.post_data_json
        route.fulfill(
            status=200,
            content_type="text/event-stream",
            body=build_agent_sse_response(body),
        )

    page.route("**/new-agents/api/config", route_config)
    page.route("**/new-agents/api/agent/runs/stream", route_agent_stream)
    page.goto(new_agents_base_url)
    page.evaluate("localStorage.clear()")
    page.reload()
    expect(page.get_by_text("选择你的 AI 助手")).to_be_visible(timeout=10000)

    yield page

    context.close()
    assert console_errors == []
```

- [ ] **Step 2: Run an import check**

Run:

```bash
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -q
```

Expected: pytest imports fixtures successfully. If browser binaries are missing, the next task's test run should fail with a Playwright browser installation message.

## Task 3: Workflow Runner And First Failing Lisa Test

**Files:**
- Create: `tests/e2e/new_agents_browser/workflow_runner.py`
- Create: `tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py`

- [ ] **Step 1: Write the workflow runner**

Create `tests/e2e/new_agents_browser/workflow_runner.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page, expect


@dataclass(frozen=True)
class StageExpectation:
    transition_label: str | None
    artifact_headings: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowScenario:
    agent_name: str
    workflow_name: str
    prompt: str
    initial_heading: str
    stages: tuple[StageExpectation, ...]


def _artifact_text(page: Page) -> str:
    return page.locator("section").nth(1).inner_text(timeout=10000)


def _assistant_messages_text(page: Page) -> str:
    messages = page.locator("text=/Lisa|Alex/").locator("..")
    return messages.all_inner_texts() and "\n".join(messages.all_inner_texts())


def _assert_artifact_contains(page: Page, headings: tuple[str, ...]) -> None:
    artifact = _artifact_text(page)
    for heading in headings:
        assert heading in artifact


def _assert_chat_does_not_contain_full_artifact(page: Page, forbidden_headings: tuple[str, ...]) -> None:
    chat_text = page.locator("section").nth(0).inner_text(timeout=10000)
    matched = [heading for heading in forbidden_headings if heading in chat_text]
    assert len(matched) <= 1, f"assistant chat appears to contain artifact headings: {matched}"


def run_complete_workflow(page: Page, scenario: WorkflowScenario) -> str:
    page.get_by_text(scenario.agent_name, exact=True).click()
    expect(page.get_by_text(f"{scenario.agent_name} 的工作流")).to_be_visible(timeout=10000)
    page.get_by_text(scenario.workflow_name, exact=True).click()
    expect(page.get_by_text(scenario.initial_heading, exact=True)).to_be_visible(timeout=10000)

    page.get_by_placeholder(
        "描述你想测试的功能，或粘贴需求文档..."
    ).or_(page.get_by_placeholder("描述你已有的产品方向或想法...")).fill(scenario.prompt)
    page.locator("#send-button").click()

    all_headings: list[str] = []
    for index, stage in enumerate(scenario.stages):
        _assert_artifact_contains(page, stage.artifact_headings)
        all_headings.extend(stage.artifact_headings)
        _assert_chat_does_not_contain_full_artifact(page, tuple(all_headings))

        if stage.transition_label:
            confirm_button = page.get_by_role("button", name=stage.transition_label)
            expect(confirm_button).to_be_visible(timeout=10000)
            confirm_button.click()
        else:
            expect(page.get_by_text("等待确认")).not_to_be_visible(timeout=10000)

    return _artifact_text(page)
```

- [ ] **Step 2: Write the failing Lisa browser test**

Create `tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py` with:

```python
from __future__ import annotations

import pytest

from .workflow_runner import StageExpectation, WorkflowScenario, run_complete_workflow


pytestmark = pytest.mark.e2e


def test_lisa_test_design_workflow_completes_all_stages(new_agents_page):
    final_artifact = run_complete_workflow(
        new_agents_page,
        WorkflowScenario(
            agent_name="Lisa",
            workflow_name="测试策略与用例设计",
            initial_heading="测试设计",
            prompt="请为登录和支付联动功能设计完整测试策略与测试用例。",
            stages=(
                StageExpectation(
                    transition_label="确认进入 策略制定",
                    artifact_headings=(
                        "# 需求分析文档",
                        "## 1. 被测系统与边界",
                        "## 4. 隐式需求与非功能性考量",
                    ),
                ),
                StageExpectation(
                    transition_label="确认进入 用例编写",
                    artifact_headings=(
                        "# 测试策略蓝图",
                        "## 1. 质量目标",
                        "## 5. 测试点拓扑",
                    ),
                ),
                StageExpectation(
                    transition_label="确认进入 文档交付",
                    artifact_headings=(
                        "# 测试用例集",
                        "## 1. 用例统计",
                        "## 3. 测试点覆盖追溯",
                    ),
                ),
                StageExpectation(
                    transition_label=None,
                    artifact_headings=(
                        "# 测试设计文档",
                        "## 文档信息",
                        "## 附录：验收标准",
                    ),
                ),
            ),
        ),
    )

    assert "登录支付链路测试设计" in final_artifact
```

- [ ] **Step 3: Run the Lisa test to verify RED or environment failure**

Run:

```bash
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py -m e2e -q
```

Expected before implementation fixes: fail if selectors or fixtures are incomplete. If the browser is missing, install Python Playwright browser binaries before continuing.

## Task 4: Fix Runner Selectors Until Lisa Passes

**Files:**
- Modify: `tests/e2e/new_agents_browser/workflow_runner.py`
- Modify if needed: `tests/e2e/new_agents_browser/conftest.py`

- [ ] **Step 1: Adjust selectors to match the real UI**

Use accessible text selectors where possible. The runner should:

```python
page.get_by_text(scenario.agent_name, exact=True).click()
page.get_by_text(scenario.workflow_name, exact=True).click()
page.locator("textarea").fill(scenario.prompt)
page.locator("#send-button").click()
```

For artifact reads, keep `page.locator("section").nth(1).inner_text()` because the UI has a two-pane layout.

- [ ] **Step 2: Run Lisa test to verify GREEN**

Run:

```bash
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py -m e2e -q
```

Expected: `1 passed`.

## Task 5: Alex Workflow Test

**Files:**
- Create: `tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py`

- [ ] **Step 1: Write the Alex browser test**

Create `tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py` with:

```python
from __future__ import annotations

import pytest

from .workflow_runner import StageExpectation, WorkflowScenario, run_complete_workflow


pytestmark = pytest.mark.e2e


def test_alex_value_discovery_workflow_completes_all_stages(new_agents_page):
    final_artifact = run_complete_workflow(
        new_agents_page,
        WorkflowScenario(
            agent_name="Alex",
            workflow_name="价值发现",
            initial_heading="价值发现",
            prompt="我们计划做一个 AI 测试设计助手，帮助测试负责人从需求生成测试策略和测试用例。",
            stages=(
                StageExpectation(
                    transition_label="确认进入 用户画像",
                    artifact_headings=(
                        "# 价值定位分析",
                        "## 产品核心定位",
                        "60 秒电梯演讲",
                    ),
                ),
                StageExpectation(
                    transition_label="确认进入 用户旅程",
                    artifact_headings=(
                        "# 用户画像分析",
                        "## 主要用户画像",
                        "## 用户优先级排序",
                    ),
                ),
                StageExpectation(
                    transition_label="确认进入 需求蓝图",
                    artifact_headings=(
                        "# 用户旅程分析",
                        "## 用户旅程地图",
                        "## 核心机会点",
                    ),
                ),
                StageExpectation(
                    transition_label=None,
                    artifact_headings=(
                        "需求蓝图",
                        "## 1. 产品概述",
                        "## 7. 风险评估",
                    ),
                ),
            ),
        ),
    )

    assert "AI 测试设计助手需求蓝图" in final_artifact
```

- [ ] **Step 2: Run the Alex test**

Run:

```bash
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py -m e2e -q
```

Expected: `1 passed`.

## Task 6: Optional LLM Judge

**Files:**
- Create: `tests/e2e/new_agents_browser/llm_judge.py`
- Modify: `tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py`
- Modify: `tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py`

- [ ] **Step 1: Write the optional judge module**

Create `tests/e2e/new_agents_browser/llm_judge.py` with:

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass

import pytest
import requests


@dataclass(frozen=True)
class JudgeResult:
    passed: bool
    score: int
    issues: list[str]


def _judge_enabled() -> bool:
    return os.environ.get("NEW_AGENTS_E2E_LLM_JUDGE") == "1"


def assert_llm_judges_artifact_quality(workflow_name: str, artifact: str) -> None:
    if not _judge_enabled():
        pytest.skip("NEW_AGENTS_E2E_LLM_JUDGE is not enabled")

    api_key = os.environ.get("NEW_AGENTS_E2E_JUDGE_API_KEY")
    base_url = os.environ.get("NEW_AGENTS_E2E_JUDGE_BASE_URL")
    model = os.environ.get("NEW_AGENTS_E2E_JUDGE_MODEL")
    missing = [
        name
        for name, value in {
            "NEW_AGENTS_E2E_JUDGE_API_KEY": api_key,
            "NEW_AGENTS_E2E_JUDGE_BASE_URL": base_url,
            "NEW_AGENTS_E2E_JUDGE_MODEL": model,
        }.items()
        if not value
    ]
    if missing:
        pytest.skip("missing LLM judge environment variables: " + ", ".join(missing))

    prompt = f"""
请评审以下 New Agents 浏览器测试最终产物是否满足 {workflow_name} 工作流质量要求。
只返回 JSON，不要返回 Markdown。
JSON 结构必须是：{{"pass": true/false, "score": 0-100, "issues": ["问题1"]}}
评审标准：
1. 覆盖工作流要求的主要章节。
2. 内容不是纯占位符。
3. 对真实用户有用。
4. 内部逻辑连贯。

产物：
{artifact}
""".strip()

    response = requests.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "你是严格的软件测试产物评审员。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        },
        timeout=60,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    result = JudgeResult(
        passed=bool(parsed["pass"]),
        score=int(parsed["score"]),
        issues=list(parsed.get("issues", [])),
    )
    assert result.passed, f"LLM judge failed with score {result.score}: {result.issues}"
    assert result.score >= 70, f"LLM judge score too low: {result.score}, issues: {result.issues}"
```

- [ ] **Step 2: Add skipped judge tests**

Append to `test_lisa_test_design_workflow.py`:

```python
from .llm_judge import assert_llm_judges_artifact_quality


def test_lisa_final_artifact_passes_optional_llm_judge(new_agents_page):
    final_artifact = run_complete_workflow(
        new_agents_page,
        WorkflowScenario(
            agent_name="Lisa",
            workflow_name="测试策略与用例设计",
            initial_heading="测试设计",
            prompt="请为登录和支付联动功能设计完整测试策略与测试用例。",
            stages=(
                StageExpectation("确认进入 策略制定", ("# 需求分析文档",)),
                StageExpectation("确认进入 用例编写", ("# 测试策略蓝图",)),
                StageExpectation("确认进入 文档交付", ("# 测试用例集",)),
                StageExpectation(None, ("# 测试设计文档",)),
            ),
        ),
    )
    assert_llm_judges_artifact_quality("Lisa 测试策略与用例设计", final_artifact)
```

Append to `test_alex_value_discovery_workflow.py`:

```python
from .llm_judge import assert_llm_judges_artifact_quality


def test_alex_final_artifact_passes_optional_llm_judge(new_agents_page):
    final_artifact = run_complete_workflow(
        new_agents_page,
        WorkflowScenario(
            agent_name="Alex",
            workflow_name="价值发现",
            initial_heading="价值发现",
            prompt="我们计划做一个 AI 测试设计助手，帮助测试负责人从需求生成测试策略和测试用例。",
            stages=(
                StageExpectation("确认进入 用户画像", ("# 价值定位分析",)),
                StageExpectation("确认进入 用户旅程", ("# 用户画像分析",)),
                StageExpectation("确认进入 需求蓝图", ("# 用户旅程分析",)),
                StageExpectation(None, ("需求蓝图",)),
            ),
        ),
    )
    assert_llm_judges_artifact_quality("Alex 价值发现", final_artifact)
```

- [ ] **Step 3: Run default tests and verify judge tests skip**

Run:

```bash
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q
```

Expected: deterministic workflow tests pass; judge tests skip.

## Task 7: Documentation And Final Verification

**Files:**
- Modify: `docs/TESTING.md`

- [ ] **Step 1: Document the command**

Add a short section to `docs/TESTING.md`:

```markdown
## New Agents 浏览器工作流测试

New Agents 另有一套独立于 intent-tester/MidScene 的浏览器级工作流测试，位于 `tests/e2e/new_agents_browser/`。它使用 Python Playwright 打开真实 React 前端，通过 mock typed SSE 响应验证 Lisa `test-design` 和 Alex `value-discovery` 的完整阶段组织逻辑。

默认确定性运行：

```bash
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q
```

可选 LLM judge 运行：

```bash
NEW_AGENTS_E2E_LLM_JUDGE=1 \
NEW_AGENTS_E2E_JUDGE_API_KEY=<api-key> \
NEW_AGENTS_E2E_JUDGE_BASE_URL=https://api.deepseek.com \
NEW_AGENTS_E2E_JUDGE_MODEL=deepseek-v4-flash \
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q
```

不要把 API key 写入仓库。默认测试不需要模型网络调用。
```

- [ ] **Step 2: Run final deterministic verification**

Run:

```bash
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q
```

Expected: workflow tests pass and judge tests skip unless enabled.

- [ ] **Step 3: Run frontend unit baseline**

Run:

```bash
cd tools/new-agents/frontend && npm test
```

Expected: existing frontend tests pass.

- [ ] **Step 4: Inspect changed files**

Run:

```bash
git status --short
```

Expected: only new browser-test files, `docs/TESTING.md`, and the plan are newly modified by this task, aside from pre-existing unrelated workspace changes.
