# AI4SE Agent 指南

> **身份**: 你是一个在模块化单体仓库 (Modular Monorepo) (Python/TypeScript) 中工作的专家级 AI 软件工程师。
> **主要指令**: 遵循 TDD，使用中文交流，使用 Context7 查询外部库文档。

# 语言规则【最高优先级】
- **全程使用中文思考**：在处理所有问题时，内部思维过程（Thinking Process）必须全程使用中文。
- **中文回答**：除非明确要求使用其他语言，否则所有输出和解释都必须使用中文。
- **逻辑拆解**：在思维链中，请用中文进行需求分析和逻辑拆解。


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
| **跳过前端构建** | `./scripts/dev/deploy-dev.sh --skip-frontend` |
| **运行所有测试 (类CI)** | `./scripts/test/test-local.sh` |
| **测试子集** | `./scripts/test/test-local.sh [api|proxy|lint]` |
| **查看日志** | `docker-compose -f docker-compose.dev.yml logs -f` |

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

### 4. Docker 优先的开发模式

**关键规则**: 开发环境在 Docker 容器中运行。永远不要假设本地文件修改会立即生效。

- **集成测试**: 测试前必须使用 `./scripts/dev/deploy-dev.sh` 部署
- **本地开发服务器**: 在宿主机上运行 `npm run dev` 或 `flask run` 仅用于隔离开发
- **构建产物**: 前端构建在部署期间被复制到 Docker 镜像中

---

## 代码风格与模式

### Python (`ai-agents`, `intent-tester`, `shared`)

| 方面 | 规则 |
|--------|------|
| **风格** | PEP 8, Black 格式化器 |
| **类型** | **强制** 所有参数/返回值的类型提示 |
| **命名** | `snake_case` (变量/函数), `PascalCase` (类), `UPPER_SNAKE` (常量) |
| **导入** | 标准库 -> 第三方 -> 本地。使用从包根目录的绝对导入。 |
| **错误处理** | 仅特定异常。切勿使用裸露的 `except Exception:` 而不重新抛出/记录日志。 |
| **提示词** | 存储在 `prompts/` 目录中。逻辑文件中没有硬编码的提示词。 |
| **模式** | 使用带有 `Field` 验证器的 Pydantic `BaseModel` 用于结构化数据。 |

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
│   │   │   │   │   ├── graph.py      # StateGraph 定义
│   │   │   │   │   ├── nodes.py      # 图节点
│   │   │   │   │   └── tools.py      # update_artifact 工具
│   │   │   │   └── shared/    # 共享状态, 检查点, 工具
│   │   │   ├── api/           # REST API 端点
│   │   │   ├── models/        # SQLAlchemy 模型
│   │   │   └── tests/         # Pytest 测试
│   │   └── frontend/          # React UI (Vercel AI SDK)
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

### 模块化单体仓库

- 独立的服务在一个仓库中，通过 `tools/shared` 共享工具
- **共享代码位置**: `tools/shared/` 包含跨工具的实用程序
- **数据库**: `tools/shared/database/` 中的共享 SQLAlchemy 连接池
- **配置**: `tools/shared/config/` 中的统一配置管理

### AI Agents 架构

- **Lisa**: 测试专家 (测试设计, 需求评审工作流)
- **Alex**: 需求分析师

**Lisa Agent 双节点架构**:

```
START → intent_router → reasoning_node → artifact_node → END
                     ↓
                  clarify_intent → END
```

**产出物更新流程** (强制要求):
1. `reasoning_node` 设置 `should_update_artifact=True`
2. 通过 Command 路由到 `artifact_node`
3. `artifact_node` 调用 `update_artifact` 工具
4. 前端接收 `tool-call` 事件进行追踪

> **禁止** 直接在节点中修改 `state["artifacts"]` - 必须使用工具以确保前端可观测性。

### 数据流与流式传输

- **后端**: Flask + LangGraph 通过服务器发送事件 (SSE) 流式传输响应
- **前端**: Vercel AI SDK (`useChat` hook) 消费流
- **协议**: Vercel AI SDK Data Stream Protocol

### MidScene 代理

本地 Node.js 服务器，通过 Playwright 驱动 Chrome 进行 AI 驱动的浏览器测试

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

| 类型 | 框架 | 测什么 | Mock 范围 |
|------|------|--------|-----------|
| **后端单元** | pytest | 纯函数、Pydantic 模型、工具类 | 无外部依赖 |
| **后端 API** | pytest + Flask test_client | HTTP 端点、请求/响应格式、状态码 | LLM 服务、外部 API |
| **后端集成** | pytest | 多模块协作、状态流转、工作流 | LLM、外部服务 |
| **前端组件** | Vitest + React Testing Library | 组件渲染、用户交互、Hooks | 无 (隔离组件) |
| **前端集成** | Vitest + MSW | 组件间协作、数据流、SSE 流 | 后端 API (MSW) |
| **代理测试** | Jest | MidScene Server API、WebSocket | Playwright 调用 |

### Mock 策略

| 被 Mock 对象 | Mock 方式 | 使用场景 |
|-------------|-----------|----------|
| **LLM 服务** | `unittest.mock.patch` + `FakeLLM` | 所有非 `slow` 标记的测试 |
| **数据库** | SQLite `:memory:` (conftest.py) | 所有需要持久化的测试 |
| **外部 API** | `responses` 库 / `httpx.MockTransport` | API 测试 |
| **前端后端** | MSW (Mock Service Worker) | 前端集成测试 |
| **LangGraph 节点** | 直接调用节点函数，mock 依赖 | 节点单元测试 |

### 测试文件组织

```
tools/ai-agents/backend/tests/
├── conftest.py              # 共享 fixtures
├── test_artifact_models.py  # [unit]
├── test_api_v2_stream.py    # [api]
└── test_workflow_integration.py  # [integration]

tools/ai-agents/frontend/tests/
├── mocks/server.ts          # MSW 服务器配置
├── integration/             # [integration]
└── *.test.tsx               # [component]

tools/intent-tester/tests/
├── conftest.py              # 共享 fixtures
└── proxy/                   # MidScene API 测试
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
| 修复线上 Bug | 先写复现测试 | 防止回归 |
| 重构已有代码 | 确保已有测试通过 | 不新增测试，除非发现覆盖盲区 |

### 测试标记 (pytest)

```bash
pytest -m unit        # 仅单元测试
pytest -m api         # 仅 API 测试
pytest -m integration # 集成测试
pytest -m "not slow"  # 跳过慢速测试
```

---

## 代码质量标准

### 死代码清理

重构或替换库时:
- **验证零引用**: `grep -r "ComponentName" tools/`
- **立即删除**: 删除未使用的文件，不要注释掉
- **清理测试**: 删除相关测试文件以防止 CI 失败

### 特性废弃协议

移除特性时:
1. 删除 Pydantic schemas/models
2. 更新服务级 docstrings 以移除提及
3. 删除特性专属的测试文件
4. 搜索特性名称的所有变体: `grep -ri "feature_name" tools/`

### 单一事实来源 (SSOT)

**反模式**: 在前端常量中复制后端 prompt 逻辑

### Prompt 维护

当工作流机制改变时:
- **立即移除过时的 prompt 辅助函数**: 不要"以防万一"保留
- **风险**: 废弃的 prompts 会产生矛盾的 LLM 指令
- **行动**: 删除函数定义、文件和所有模板引用

---

## 环境配置

必需的 `.env` 变量:

```bash
# 数据库
DB_USER=ai4se_user
DB_PASSWORD=your_password

# 应用
SECRET_KEY=your-secret-key

# OpenAI (AI agents 必需)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# LangSmith (可选)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=ai4se
```

---

## 部署规则

**本地开发**:
- 所有集成测试使用 `./scripts/dev/deploy-dev.sh`
- 修改需要重新构建才能在容器中生效

**生产环境**:
- **绝不** 直接部署到云服务器
- 推送到 `master` 分支 → GitHub Actions 运行 CI → 测试通过后自动部署
- 所有修改必须在推送前通过 `./scripts/test/test-local.sh`

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

---

## 开发前检查清单

修改前:
- [ ] 我是在 Docker 中运行吗? 如果是，我部署了吗 (`./scripts/dev/deploy-dev.sh`)?
- [ ] 导入的库是否真的存在于 `package.json`/`requirements.txt` 中?
- [ ] 我是否在前端和后端之间重复了逻辑 (违反 SSOT)?

实施后:
- [ ] 我删除了未使用的文件 (死代码) 吗?
- [ ] 如果移除了特性，我更新了所有相关的 docstrings 和 schemas 吗?
- [ ] 我更新了测试以匹配 API 变更 (props, imports, mocks) 吗?
- [ ] 我验证了测试通过 (`./scripts/test/test-local.sh`) 吗?
