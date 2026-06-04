# E2E 自动化测试实施计划

> **给 Claude 的指示:** 必需子技能: 使用 `superpowers:executing-plans` 逐任务执行此计划。

**目标:** 使用 Playwright 为 Lisa 和 Alex 智能体实现基础的 E2E（端到端）冒烟测试，以确保在完全集成的环境中核心对话流程能够正常工作。

**架构:** 在 Python 中使用 `pytest-playwright` 编排浏览器与本地运行的 Docker 环境进行交互。`conftest.py` 中的 fixture 将处理页面设置和环境跳过逻辑（在 CI 中跳过以避免 LLM API 费用）。

**技术栈:** Python, pytest, pytest-playwright.

---

### Task 1: 设置 E2E 测试 Fixture 和配置

**文件:**
- 创建: `tests/e2e/__init__.py`
- 创建: `tests/e2e/conftest.py`

**步骤 1: 编写空的 `__init__.py`**

```python
# tests/e2e/__init__.py
```

**步骤 2: 编写 `conftest.py` 实现**

```python
import os
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: 标记为端到端(E2E)测试")

def pytest_collection_modifyitems(config, items):
    if os.environ.get("CI") == "true":
        skip_ci = pytest.mark.skip(reason="E2E 测试需要本地 Docker 和 LLM token，在 CI 中跳过")
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_ci)

@pytest.fixture(scope="session")
def base_url():
    """本地运行的应用程序前端 URL。"""
    return os.environ.get("BASE_URL", "http://localhost:5173")

# 注: playwright 和 page fixture 由 pytest-playwright 自动提供
```

**步骤 3: 提交代码**

```bash
git add tests/e2e/__init__.py tests/e2e/conftest.py
git commit -m "test(e2e): 设置初始的 pytest fixture 和针对 Playwright 的 CI 跳过逻辑"
```

### Task 2: 实现 Lisa 智能体冒烟测试 (基础与多轮对话)

**文件:**
- 创建: `tests/e2e/test_lisa_smoke.py`

**步骤 1: 编写失败的测试**

```python
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
def test_lisa_basic_conversation(page: Page, base_url: str):
    # 导航到 Lisa 测试设计工作流
    page.goto(f"{base_url}/workspace/lisa/test-design")
    
    # 等待系统稳定和智能体初始化
    page.wait_for_timeout(2000)
    
    # 定位聊天输入框
    chat_input = page.locator("textarea[placeholder*='描述你想测试的功能']")
    expect(chat_input).to_be_visible()
    
    # 发送一条消息
    chat_input.fill("你好，请简略回复'收到'")
    page.locator("button[title='发送']").click()
    
    # 等待回复（因为 LLM 较慢，最多等待 45秒）
    response_texts = page.locator(".flex.flex-col > .rounded-2xl.bg-\\[\\#151e32\\]")
    expect(response_texts.last).to_contain_text("收到", timeout=45000)

@pytest.mark.e2e
def test_lisa_multi_turn_conversation(page: Page, base_url: str):
    # 导航
    page.goto(f"{base_url}/workspace/lisa/test-design")
    page.wait_for_timeout(2000)
    
    chat_input = page.locator("textarea[placeholder*='描述你想测试的功能']")
    
    # 第一轮交互
    chat_input.fill("我正在设计一个极简的计算器网页。")
    page.locator("button[title='发送']").click()
    
    # 等待第一轮回复完成
    response_elements = page.locator(".flex.flex-col > .rounded-2xl.bg-\\[\\#151e32\\]")
    # 等待直到“停止生成”按钮消失通常表示生成完成，
    # 或者我们也可以直接等待代表回复的文本出现。
    expect(page.locator("button[title='停止生成']")).not_to_be_visible(timeout=60000)
    
    # 第二轮交互
    chat_input.fill("请继续，它有什么值得注意的测试点？")
    page.locator("button[title='发送']").click()
    
    # 等待第二轮回复完成
    expect(page.locator("button[title='停止生成']")).not_to_be_visible(timeout=60000)
    
    # 预期上下文中捕获了计算/UI等相关的引用
    expect(response_elements.last).to_contain_text(["计算", "边界", "输入", "边界值"], ignore_case=True, timeout=10000)
```

**步骤 2: 运行测试以验证它能工作**

运行: `python -m pytest tests/e2e/test_lisa_smoke.py -v -m e2e`
*(预期结果: 如果 Docker 环境正在运行则应该通过。可能需要通过 `playwright install chromium` 安装 playwright 浏览器)*

**步骤 3: 提交代码**

```bash
git add tests/e2e/test_lisa_smoke.py
git commit -m "test(e2e): 增加 Lisa 智能体对话流程的 Playwright 冒烟测试"
```

### Task 3: 实现 Alex 智能体冒烟测试

**文件:**
- 创建: `tests/e2e/test_alex_smoke.py`

**步骤 1: 编写测试**

```python
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
def test_alex_basic_conversation(page: Page, base_url: str):
    # 导航到 Alex 需求评审工作流
    page.goto(f"{base_url}/workspace/alex/req-review")
    
    # 等待 UI 加载
    page.wait_for_timeout(2000)
    
    # 发送消息
    chat_input = page.locator("textarea[placeholder*='需求文档']")
    expect(chat_input).to_be_visible()
    
    chat_input.fill("你好，我现在给你一个简单的用户登录模块需求，请检查是否有遗漏。")
    page.locator("button[title='发送']").click()
    
    # 等待生成完成
    expect(page.locator("button[title='停止生成']")).not_to_be_visible(timeout=60000)
    
    # 等待来自 Alex 指示已评审登录模块的响应
    response_texts = page.locator(".flex.flex-col > .rounded-2xl.bg-\\[\\#151e32\\]")
    expect(response_texts.last).to_be_visible()
    expect(response_texts.last).to_contain_text(["登录", "密码", "遗漏", "需求"], ignore_case=True, timeout=5000)
```

**步骤 2: 在本地运行测试以验证通过**

运行: `python -m pytest tests/e2e/test_alex_smoke.py -v -m e2e`

**步骤 3: 提交代码**

```bash
git add tests/e2e/test_alex_smoke.py
git commit -m "test(e2e): 增加 Alex 智能体基础冒烟测试"
```

### Task 4: 在技术规范文档中勾选 E2E 自动化阶段

**文件:**
- 修改: `_bmad-output/implementation-artifacts/tech-spec-agent-test-strategy-improvement.md`

**步骤 1: 勾选 Task 5-7 和 验收标准 AC 8-10**

在规范文档中找到 Tasks 5, 6, 7 和 AC-8, AC-9, AC-10，将 `- [ ]` 替换为 `- [x]`。

**步骤 2: 提交代码**

```bash
git add _bmad-output/implementation-artifacts/tech-spec-agent-test-strategy-improvement.md
git commit -m "docs: 勾选规范文档中 Phase 1 的 Tasks 5-7 (E2E Tests)"
```

---
