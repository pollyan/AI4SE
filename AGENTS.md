# AGENTS.md - AI4SE Agent 指南

> **身份**: 你是一个在模块化单体仓库 (Modular Monorepo) (Python/TypeScript) 中工作的专家级 AI 软件工程师。
> **主要指令**: 遵循 TDD，使用中文交流，使用 Context7 查询外部库文档。

---

## 快速命令速查表

### Python (后端)

| 任务 | 命令 |
|------|---------|
| **安装依赖** | `pip install -r requirements.txt` |
| **测试所有** | `pytest` |
| **测试单个文件** | `pytest tools/ai-agents/backend/tests/test_agent.py` |
| **测试单个函数** | `pytest tools/ai-agents/backend/tests/test_agent.py::test_workflow` |
| **按关键字测试** | `pytest -k "workflow_node"` |
| **按标记测试** | `pytest -m unit` (标记: `unit`, `api`, `integration`, `e2e`, `slow`) |
| **Lint (关键)** | `flake8 --select=E9,F63,F7,F82 .` |
| **Lint (完整)** | `flake8 .` |
| **格式化** | `black .` |

### TypeScript/React (前端)

| 任务 | 命令 | 目录 |
|------|---------|-----------|
| **安装** | `npm install` | `tools/frontend` 或 `tools/ai-agents/frontend` |
| **开发服务器** | `npm run dev` | 任意前端目录 |
| **构建** | `npm run build` | 任意前端目录 |
| **测试所有** | `npm run test` | `tools/ai-agents/frontend` |
| **测试单个文件** | `npx vitest run src/components/Panel.test.tsx` | `tools/ai-agents/frontend` |
| **测试过滤器** | `npx vitest -t "renders correctly"` | `tools/ai-agents/frontend` |
| **Lint** | `npm run lint` | 任意前端目录 |

### Node.js (MidScene 代理)

| 任务 | 命令 | 目录 |
|------|---------|-----------|
| **安装** | `npm install` | `tools/intent-tester` |
| **启动代理** | `npm start` | `tools/intent-tester` |
| **测试代理** | `npm run test:proxy` | `tools/intent-tester` |
| **覆盖率测试** | `npm run test:proxy:coverage` | `tools/intent-tester` |

### DevOps (Docker)

| 任务 | 命令 |
|------|---------|
| **部署开发环境** | `./scripts/dev/deploy-dev.sh` |
| **完全重建** | `./scripts/dev/deploy-dev.sh full` |
| **运行所有测试 (类CI)** | `./scripts/test/test-local.sh` |
| **测试子集** | `./scripts/test/test-local.sh [api|proxy|lint]` |

> **警告**: 切勿直接运行 `docker` 命令。始终使用脚本。

### E2E 测试 (浏览器)

| 任务 | 命令 | 说明 |
|------|------|------|
| **运行冒烟测试** | `/e2e` | 使用 Chrome DevTools MCP 测试 Lisa |
| **测试 Lisa** | `/e2e lisa` | Lisa 智能体完整测试 |
| **测试全部** | `/e2e all` | 运行所有 E2E 测试 |

> **前置条件**: Docker 环境运行中 + Chrome DevTools MCP 连接

---

## 核心规则 (不可协商)

### 1. TDD 协议 (红-绿-重构)

1. **红**: 首先编写一个失败的测试 (`pytest` 或 `vitest`)
2. **绿**: 编写最少量的代码使其通过
3. **重构**: 在保持测试通过的同时清理代码

如果你发现自己在没有测试的情况下编写实现代码，**停止**。回滚。先写测试。

### 2. Agent 行为

- **彻底坦诚**: 挑战模糊的需求。指出用户方法中的缺陷。
- **谋定而后动**: 分析 -> 计划 -> 执行。不要匆忙。
- **自我纠正**: 发现自己违反了 TDD？立即停止并纠正。

### 3. 沟通与工具

- **语言**: 始终用**中文**解释（计划、错误、推理）
- **Context7**: 主动使用 `context7` 工具查询外部库文档
- **验证**: 在声称完成之前运行 `lsp_diagnostics` 和测试

---

## 代码风格与模式

### Python (`ai-agents`, `intent-tester`, `shared`)

| 方面 | 规则 |
|--------|------|
| **风格** | PEP 8, Black 格式化器 |
| **类型** | **强制** 所有参数/返回值的类型提示: `def func(x: int) -> str:` |
| **命名** | `snake_case` (变量/函数), `PascalCase` (类), `UPPER_SNAKE` (常量) |
| **导入** | 标准库 -> 第三方 -> 本地。使用从包根目录的绝对导入。 |
| **错误处理** | 仅特定异常。切勿使用裸露的 `except Exception:` 而不重新抛出/记录日志。 |
| **提示词** | 存储在 `prompts/` 目录中。逻辑文件中没有硬编码的提示词。 |
| **模式** | 使用带有 `Field` 验证器的 Pydantic `BaseModel` 用于结构化数据。 |

**导入模式示例:**
```python
from typing import Dict, Optional
from langchain_core.messages import AIMessage  # 第三方
from backend.agents.lisa.state import LisaState  # 本地绝对路径
from ..shared.checkpointer import get_checkpointer  # 本地相对路径 (包内)
```

### TypeScript/React (`frontend`, `ai-agents/frontend`)

| 方面 | 规则 |
|--------|------|
| **风格** | ESLint + TypeScript 严格模式 |
| **组件** | 仅使用 Hooks 的函数式组件 |
| **文件命名** | `PascalCase.tsx` (组件), `camelCase.ts` (工具) |
| **状态** | React Context / React Query > 全局 Store |
| **测试** | Vitest + React Testing Library |
| **样式** | Tailwind CSS 工具类 |

### Node.js (`intent-tester/browser-automation`)

| 方面 | 规则 |
|--------|------|
| **运行时** | Node.js 20+ |
| **测试** | Jest |
| **浏览器自动化** | Playwright + MidSceneJS |

---

## 项目结构

```text
AI4SE/
├── scripts/
│   ├── dev/deploy-dev.sh      # 本地 Docker 部署
│   ├── test/test-local.sh     # 类 CI 测试运行器
│   └── ci/                    # CI/CD 脚本
├── tools/
│   ├── ai-agents/             # [端口: 5002] Flask + LangGraph
│   │   ├── backend/
│   │   │   ├── agents/        # Alex, Lisa (LangGraph 状态机)
│   │   │   │   ├── lisa/      # 测试专家 Agent
│   │   │   │   ├── shared/    # 共享状态, 检查点, 工具
│   │   │   │   └── llm.py     # LLM 工厂
│   │   │   ├── api/           # REST API 端点
│   │   │   ├── models/        # SQLAlchemy 模型
│   │   │   └── tests/         # Pytest 测试
│   │   └── frontend/          # React UI (assistant-ui)
│   ├── intent-tester/         # [端口: 5001] Flask + MidScene
│   │   ├── backend/           # Flask API
│   │   ├── browser-automation/# Node.js MidScene 代理
│   │   └── tests/             # Python + Jest 测试
│   ├── frontend/              # [端口: 80] 统一门户 (Vite + React)
│   └── shared/                # 通用 Python 工具 (配置, 数据库)
├── nginx/                     # 反向代理配置
├── pytest.ini                 # 全局 pytest 配置
├── requirements.txt           # 根 Python 依赖
└── docker-compose.dev.yml     # 开发环境编排
```

---

## 架构背景

- **模块化单体仓库**: 独立的服务在一个仓库中，通过 `tools/shared` 共享工具
- **AI Agents**: 用于多轮对话的 LangGraph StateGraph，支持 SSE 流式传输
  - **Lisa**: 测试专家 (测试设计, 需求评审工作流)
  - **Alex**: 需求分析师
- **MidScene 代理**: 本地 Node.js 服务器，通过 Playwright 驱动 Chrome 进行 AI 驱动的浏览器测试

---

## AI Agents 架构策略

### Artifact (产出物) 格式分离原则

**核心原则**: Artifact 的格式约束应在 **数据模型 + 渲染逻辑** 中定义，而非在提示词中硬编码。

| 层级 | 职责 | 文件位置 |
|------|------|----------|
| **数据模型** | 定义字段、类型、枚举值 | `artifact_models.py` |
| **渲染逻辑** | 将结构化数据转为 Markdown | `utils/markdown_generator.py` |
| **提示词** | 告诉 LLM **做什么**，而非**格式细节** | `prompts/*.py` |

**为什么这样设计**:
1. **SSOT (Single Source of Truth)**: 格式定义只在一处，避免提示词与代码脱节
2. **可维护性**: 修改格式只需改模型/渲染器，无需更新多处提示词
3. **一致性**: LLM 通过工具 Schema 约束输出，比自然语言描述更可靠

**提示词中应该写什么**:
- ✅ 业务逻辑（如"为每个问题设置优先级 P0/P1/P2"）
- ✅ 行为指导（如"分析完成后告知用户问题数量"）
- ❌ Markdown 表格结构示例
- ❌ 详细的格式模板

**示例对比**:

```python
# ❌ 错误：在提示词中写格式
PROMPT = '''
问题必须按以下格式输出：
| ID | 问题描述 | 状态 |
|----|----------|------|
| Q1 | xxx | 待确认 |
'''

# ✅ 正确：在提示词中只写业务逻辑
PROMPT = '''
为每个问题设置优先级：P0(阻塞)、P1(重要)、P2(可选)
'''
# 格式由 AssumptionItem 模型和 markdown_generator.py 控制
```

---

## 测试策略

### 测试金字塔

```
        ┌─────────────┐
        │    E2E      │  ← 少量，验证关键用户流程 (Chrome DevTools MCP)
        │  (手动/MCP) │
        ├─────────────┤
        │ Integration │  ← 中等，验证模块协作 (mock 外部服务)
        ├─────────────┤
        │     API     │  ← 较多，验证端点契约 (Flask test_client)
        ├─────────────┤
        │    Unit     │  ← 最多，验证纯逻辑 (无 I/O)
        └─────────────┘
```

### 测试类型与边界定义

| 类型 | 框架 | 测什么 | 不测什么 | Mock 范围 |
|------|------|--------|----------|-----------|
| **后端单元** | pytest | 纯函数、Pydantic 模型、工具类 | 数据库、网络、LLM | 无外部依赖 |
| **后端 API** | pytest + Flask test_client | HTTP 端点、请求/响应格式、状态码 | 业务逻辑细节 | LLM 服务、外部 API |
| **后端集成** | pytest | 多模块协作、状态流转、工作流 | UI 渲染 | LLM、外部服务 |
| **前端组件** | Vitest + React Testing Library | 组件渲染、用户交互、Hooks | 后端通信 | 无 (隔离组件) |
| **前端集成** | Vitest + MSW | 组件间协作、数据流、SSE 流 | 真实后端 | 后端 API (MSW) |
| **代理测试** | Jest | MidScene Server API、WebSocket | 真实浏览器 | Playwright 调用 |

### Mock 策略

| 被 Mock 对象 | Mock 方式 | 使用场景 |
|-------------|-----------|----------|
| **LLM 服务** | `unittest.mock.patch` + `FakeLLM` | 所有非 `slow` 标记的测试 |
| **数据库** | SQLite `:memory:` (conftest.py) | 所有需要持久化的测试 |
| **外部 API** | `responses` 库 / `httpx.MockTransport` | API 测试 |
| **前端后端** | MSW (Mock Service Worker) | 前端集成测试 |
| **LangGraph 节点** | 直接调用节点函数，mock 依赖 | 节点单元测试 |

#### LLM Mock 模式

```python
# conftest.py 或测试文件中
@pytest.fixture
def mock_llm():
    """提供可控的 LLM mock"""
    from langchain_core.language_models.fake import FakeListChatModel
    return FakeListChatModel(responses=["模拟回复1", "模拟回复2"])

@pytest.fixture
def mock_ai_service():
    """Mock 完整的 AI 服务"""
    mock_service = MagicMock()
    mock_service.stream_message = AsyncMock(return_value=iter(["Hello", " World"]))
    return mock_service
```

### LangGraph Agent 测试模式

#### 节点测试 (推荐)

```python
def test_reasoning_node_extracts_intent():
    """直接测试单个节点，不运行完整图"""
    state = LisaState(
        messages=[HumanMessage(content="帮我设计登录测试")],
        artifacts=[]
    )
    # 直接调用节点函数
    with patch('backend.agents.llm.get_llm', return_value=mock_llm):
        result = reasoning_node(state)
    
    assert result["current_intent"] == "test_design"
```

#### 工作流测试

```python
def test_workflow_routes_to_correct_node():
    """测试路由逻辑，mock 所有 LLM 调用"""
    graph = build_lisa_graph()
    
    with patch.multiple('backend.agents.lisa.nodes',
                        reasoning_node=MagicMock(return_value={...}),
                        clarify_node=MagicMock(return_value={...})):
        result = graph.invoke(initial_state)
    
    # 验证路由决策
    assert result["next_node"] == "clarify"
```

### 测试文件组织

```
tools/ai-agents/backend/tests/
├── conftest.py              # 共享 fixtures: app, client, db_session, mock_ai_service
├── test_artifact_models.py  # [unit] Pydantic 模型
├── test_json_patch.py       # [unit] JSON Patch 逻辑
├── test_intent_parser.py    # [unit] 意图解析
├── test_api_v2_stream.py    # [api] SSE 流端点
├── test_sync_endpoint.py    # [api] 同步端点
├── test_workflow_integration.py  # [integration] 完整工作流
└── test_clarify_integration.py   # [integration] 澄清节点集成

tools/ai-agents/frontend/tests/
├── mocks/
│   └── server.ts            # MSW 服务器配置
├── utils/
│   └── stream-mock.ts       # SSE 流模拟工具
├── integration/
│   └── ChatFlow.test.tsx    # [integration] 聊天流程
├── ArtifactPanel.test.tsx   # [component] Artifact 面板
├── MarkdownText.test.tsx    # [component] Markdown 渲染
└── useVercelChat.test.tsx   # [hook] 自定义 Hook

tools/intent-tester/tests/
├── conftest.py              # 共享 fixtures
├── test_data_manager.py     # [unit] 数据管理
└── proxy/
    ├── midscene-server-api.test.js   # [api] MidScene API
    └── midscene-integration.test.js  # [integration] MidScene 集成
```

### 测试命名规范

| 类型 | 命名模式 | 示例 |
|------|----------|------|
| Python 测试文件 | `test_<模块名>.py` | `test_artifact_models.py` |
| Python 测试函数 | `test_<行为>_<条件>` | `test_create_session_returns_201` |
| TypeScript 测试文件 | `<组件名>.test.tsx` | `ArtifactPanel.test.tsx` |
| TypeScript 测试用例 | `it('<动作> when <条件>')` | `it('renders error when fetch fails')` |

### 何时写哪种测试

| 场景 | 推荐测试类型 | 理由 |
|------|-------------|------|
| 新增 Pydantic 模型 | `unit` | 验证字段约束，快速反馈 |
| 新增 API 端点 | `api` | 验证契约，mock 下游服务 |
| 新增 LangGraph 节点 | `unit` + `integration` | 单独测节点逻辑 + 测路由集成 |
| 新增 React 组件 | component test | 验证渲染和交互 |
| 修复线上 Bug | 先写复现测试 (任意层级) | 防止回归 |
| 重构已有代码 | 确保已有测试通过 | 不新增测试，除非发现覆盖盲区 |

---

## 测试标记 (pytest)

使用标记运行特定类别的测试:

```bash
pytest -m unit        # 仅单元测试
pytest -m api         # 仅 API 测试
pytest -m integration # 集成测试
pytest -m "not slow"  # 跳过慢速测试
```

---

## 禁止模式

| 类别 | 绝不 |
|----------|----------|
| **类型安全** | `as any`, `@ts-ignore`, `@ts-expect-error` |
| **错误处理** | 空 catch 块, 裸露的 `except Exception:` |
| **测试** | 删除失败的测试以"通过", 跳过 TDD |
| **提交** | 未经明确用户请求即提交 |
| **Docker** | 直接运行 `docker` 命令 (使用脚本) |

---

## 验证清单 (声称完成前)

- [ ] 更改的文件上 `lsp_diagnostics` 清零
- [ ] 所有测试通过 (`pytest` / `npm run test`)
- [ ] 构建通过 (前端 `npm run build`)
- [ ] 没有新的 lint 错误 (`flake8` / `npm run lint`)
