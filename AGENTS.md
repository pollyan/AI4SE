# AGENTS.md - AI4SE 代码库指南

> AI 编程智能体在本仓库中操作的综合指南。

## 项目概述

AI4SE 是一个 Python/TypeScript 单体仓库，包含 AI 驱动的软件工程工具：
- **intent-tester**: 意图测试框架，集成 MidSceneJS
- **ai-agents**: 基于 LangGraph 的 AI 助手（Alex: 需求分析师，Lisa: 测试专家）
- **frontend**: 共享的 React 前端（Vite + Tailwind）

## 快速参考

| 组件 | 后端 | 前端 | 端口 |
|------|------|------|------|
| intent-tester | Flask + SQLAlchemy | React | 5001 |
| ai-agents | Flask + LangGraph | React + assistant-ui | 5002 |
| nginx 网关 | - | - | 80/443 |

---

## 核心规则（必须遵守）

### DevOps 实践

- **环境一致性**: 本地环境与云端环境保持一致的部署方式
- **云端部署**: 通过 GitHub Actions 实现，**禁止直连云端服务器部署**
- **本地 Docker**: 使用 `scripts/deploy-dev.sh` 脚本启动和更新，**禁止直接操作 docker 命令**

```bash
# 正确方式：使用部署脚本
./scripts/deploy-dev.sh

# 错误方式：直接操作 docker（禁止）
docker-compose up -d  # ❌ 不要这样做
```

### 智能体逻辑判断

- **禁止关键词匹配**: 永远不要用关键词的方法来做智能体的逻辑判断
- **语义理解优先**: 必须根据上下文与语义综合判断用户意图
- **使用 LLM 路由**: 意图识别应通过 LLM 进行语义分析，而非正则或关键词

```python
# 正确方式：LLM 语义判断
def intent_router_node(state: LisaState, llm: BaseChatModel):
    """使用 LLM 分析用户意图，基于语义而非关键词。"""
    prompt = build_intent_prompt(state["messages"])
    response = llm.invoke(prompt)
    return {"current_workflow": parse_intent(response)}

# 错误方式：关键词匹配（禁止）
def bad_intent_router(message: str):  # ❌ 不要这样做
    if "测试" in message:
        return "test_design"
    if "需求" in message:
        return "requirement"
```

### 通用开发行为准则

以下规则适用于在本仓库中操作的所有 AI 编程智能体，涵盖所有模块（backend, frontend, intent-tester 等）：

1. **【强制】TDD 开发模式 (Test-Driven Development)**
   在此项目中，**所有**功能开发和 Bug 修复必须严格遵循 TDD 流程。你必须在编写实现代码之前先编写测试代码。

   **TDD 标准工作流：**
   1. **Red (红)**: 根据需求分析，先在 `tests/` 目录下创建或修改测试用例。运行测试，**必须**确认测试失败（或因编译错误失败），并向用户展示失败结果。
   2. **Green (绿)**: 编写最小量的实现代码以通过测试。运行测试，确认所有测试通过。
   3. **Refactor (重构)**: 优化代码结构，同时确保测试保持通过状态。

   **测试策略与分层：**
   * **L1 单元测试 (Unit)**:
     * **后端**: 使用 `pytest`。覆盖独立的 Graph 节点、工具函数、Prompt 构建逻辑。
       * 路径: `tools/ai-agents/backend/tests/`
       * 标记: `@pytest.mark.unit`
     * **前端**: 使用 `vitest`。覆盖 React 组件渲染、Hooks 逻辑、正则表达式、数据处理工具。
       * 路径: `tools/ai-agents/frontend/tests/`
   * **L2 集成测试 (Integration)**:
     * **后端**: 覆盖 Service 层调用、Graph 完整流转、数据库交互。
       * 路径: `tools/ai-agents/backend/tests/` (如 `test_lisa_integration.py`)
       * 标记: `@pytest.mark.integration`
   * **L3 意图/E2E 测试**:
     * **MidScene**: 用于验证完整的浏览器端业务流程。

   **禁止事项：**
   * 禁止在没有失败测试的情况下直接修改业务代码。
   * 禁止删除为了"通过"而失败的测试（除非测试本身逻辑错误）。

2. **临时文件清理**: 生成的一次性脚本与文档，在修复完成后必须清理删除

3. **自动化验证优先**: 每当完成变更或修复问题后，优先使用浏览器工具（Playwright）验证是否达到预期目标。只有在无法自动验证时才要求用户手动验证

4. **使用 Context7 查询文档**: 每当需要生成代码、安装配置步骤、或查询库/API 文档时，必须使用 Context7 MCP 工具来解析库 ID 并获取最新文档，无需用户显式要求

5. **【重要】中文交流**: 必须始终使用中文与用户交流，包括：
   - 结论与回答
   - 推理过程说明
   - 计划与任务列表
   - 错误信息与建议

---

## 架构说明

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户浏览器                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Nginx 网关 (80/443)                         │
│    /intent-tester/* → :5001    /ai-agents/* → :5002        │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│   intent-tester:5001    │     │    ai-agents:5002       │
│   Flask + SQLAlchemy    │     │   Flask + LangGraph     │
└─────────────────────────┘     └─────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL 数据库                          │
└─────────────────────────────────────────────────────────────┘
```

### MidScene Server 代理

MidScene Server 是**运行在客户端本地**的代理服务器：
- 配合服务器端 Web 系统实现自动化测试
- 驱动客户端浏览器运行测试用例
- 服务器端通过 API 与本地代理通信

```
┌──────────────────┐          ┌──────────────────┐
│   云端 Web 系统   │  ◄────►  │  本地 MidScene   │
│  (intent-tester) │   API    │     Server       │
└──────────────────┘          └────────┬─────────┘
                                       │ Playwright
                                       ▼
                              ┌──────────────────┐
                              │   本地浏览器      │
                              └──────────────────┘
```

### 模块化单体架构

- 核心业务逻辑封装在 `tools/` 下的独立模块中
- 各模块独立开发、独立测试，但共享部署
- 通用工具类放置在 `tools/shared/` 中，避免代码复制

---

## 构建与测试命令

### Python 后端（根目录）

```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/path/to/test_file.py

# 运行单个测试函数
pytest tests/path/to/test_file.py::test_function_name

# 按标记运行
pytest -m unit          # 仅单元测试
pytest -m integration   # 集成测试
pytest -m "not slow"    # 跳过慢速测试

# 覆盖率
pytest --cov=tools --cov-report=html
```

### AI Agents 模块

```bash
# 运行测试（从 tools/ai-agents/ 目录）
cd tools/ai-agents && pytest

# 单个测试
pytest backend/tests/test_lisa_graph.py::test_specific_function

# 代码检查
black backend/ --check
flake8 backend/
```

### 前端（React/Vite）

```bash
# tools/frontend/ 或 tools/ai-agents/frontend/
npm install
npm run dev      # 开发服务器
npm run build    # 生产构建
npm run lint     # ESLint 检查
npm run test     # Vitest（仅 ai-agents）
```

### Docker 本地环境

```bash
# 启动/更新本地开发环境（必须使用此脚本）
./scripts/deploy-dev.sh

# 查看日志
docker logs -f ai4se-intent-tester
docker logs -f ai4se-agents
```

---

## 代码风格指南

### Python

**导入顺序：**
```python
# 1. 标准库
import logging
import json
from typing import Dict, List, Optional, Any

# 2. 第三方库
from flask import Flask, request
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END

# 3. 本地导入
from ..models import RequirementsAIConfig
from .state import LisaState, get_initial_state
```

**命名规范：**
- 类名：`PascalCase`（如 `LangchainAssistantService`、`BaseAgentState`）
- 函数/方法：`snake_case`（如 `create_lisa_graph`、`get_initial_state`）
- 常量：`UPPER_SNAKE_CASE`（如 `SUPPORTED_ASSISTANTS`）
- 私有方法：`_单下划线` 前缀

**类型提示（必需）：**
```python
def create_lisa_graph(model_config: Dict[str, str]) -> CompiledStateGraph:
    """创建 Lisa LangGraph 图。"""
    ...
```

**文档字符串（Google 风格）：**
```python
def route_by_intent(state: LisaState) -> Literal["test_design", "clarify"]:
    """
    根据意图路由到对应节点。
    
    Args:
        state: 包含工作流信息的当前状态
        
    Returns:
        下一个节点名称
    """
```

### TypeScript/React

**导入顺序：**
```typescript
// 1. React/框架
import React, { useState, useEffect } from 'react';

// 2. 第三方库
import { marked } from 'marked';

// 3. 本地组件/工具
import { WorkflowProgress } from './WorkflowProgress';
import { backendService } from '../services/backendService';
```

**组件模式：**
```typescript
interface Props {
  sessionId: string;
  onComplete?: () => void;
}

export function AnalysisResultPanel({ sessionId, onComplete }: Props) {
  const [loading, setLoading] = useState(false);
  // ...
}
```

---

## 错误处理

**Python：**
```python
# 使用带上下文的具体异常
try:
    config = RequirementsAIConfig.get_default_config()
    if not config:
        raise ValueError("未找到 AI 配置")
except Exception as e:
    logger.error(f"初始化失败: {e}")
    raise
```

**禁止事项：**
- 静默吞掉错误
- 使用裸 `except:` 子句
- 无理由使用 `# type: ignore` 或 `as Any`

---

## 测试规范

**文件命名：** `test_*.py` / `*.test.ts`

**Pytest fixtures 模式：**
```python
@pytest.fixture(scope='function')
def app():
    """为测试创建应用。"""
    _app = create_app()
    _app.config['TESTING'] = True
    with _app.app_context():
        db.create_all()
        yield _app
        db.drop_all()
```

**测试标记：**
- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.slow` - 慢速测试
- `@pytest.mark.asyncio` - 异步测试

---

## 项目结构

```
AI4SE/
├── scripts/
│   └── deploy-dev.sh        # 本地 Docker 部署脚本（必须使用）
├── tools/
│   ├── ai-agents/           # AI 助手（Lisa, Alex）
│   │   ├── backend/
│   │   │   ├── agents/      # LangGraph 实现
│   │   │   │   ├── lisa/    # Lisa 图、节点、提示词
│   │   │   │   ├── alex/    # Alex 图、节点
│   │   │   │   └── shared/  # 共享状态、进度工具
│   │   │   ├── api/         # Flask API 路由
│   │   │   └── tests/
│   │   └── frontend/        # React UI
│   ├── intent-tester/       # 意图测试工具
│   │   ├── backend/
│   │   ├── frontend/
│   │   └── browser-automation/  # MidScene Server 代理
│   ├── frontend/            # 共享前端组件
│   └── shared/              # 共享 Python 工具（通用基类、工具函数）
├── .github/
│   └── workflows/           # GitHub Actions 云端部署
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── pytest.ini
└── requirements.txt
```

---

## 关键模式

**LangGraph 状态机：**
```python
graph = StateGraph(LisaState)
graph.add_node("intent_router", lambda s: intent_router_node(s, llm))
graph.add_node("workflow", lambda s: workflow_node(s, llm))
graph.add_edge(START, "intent_router")
graph.add_conditional_edges("intent_router", route_by_intent)
return graph.compile()
```

**Flask API 响应：**
```python
return jsonify({
    "code": 200,
    "message": "Success",
    "data": result
})
```

---

## 环境变量

`.env` 文件必需配置：
```
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
DATABASE_URL=postgresql://user:pass@localhost:5432/ai4se
SECRET_KEY=your-secret-key
```
