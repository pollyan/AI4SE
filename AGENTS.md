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
