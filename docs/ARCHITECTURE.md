# AI4SE 架构文档

> 生成日期: 2026-03-06 | 扫描级别: Deep Scan

## 架构概述

AI4SE 采用**模块化单体仓库 (Modular Monorepo)** 架构，多个独立服务共存于一个 Git 仓库中，通过 Nginx 反向代理统一对外服务，共享 PostgreSQL 数据库和 `tools/shared/` 基础设施代码。

### 架构风格

- **前端**: 组件化 SPA (React + Vite)
- **后端**: Flask 微服务（应用工厂模式）
- **通信**: RESTful API + SSE 流式 + WebSocket (SocketIO)
- **部署**: Docker Compose 容器编排

---

## Docker 服务拓扑

```text
                    ┌─────────────────────────────────────────────┐
                    │      Nginx Gateway (80/443)                 │
                    │      容器: ai4se-gateway                     │
                    └──────────────┬──────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
┌───────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ /             │     │ /intent-tester/  │     │ /new-agents/     │
│ 静态文件       │     │ Flask :5001      │     │ Nginx :80        │
│ frontend/dist │     │ ai4se-intent-    │     │ ai4se-new-agents │
└───────────────┘     │ tester           │     └────────┬─────────┘
                      └────────┬─────────┘              │
                               │                        ▼
                               │              ┌──────────────────┐
                               │              │ /new-agents/api/ │
                               │              │ Flask :5002      │
                               │              │ ai4se-new-agents-│
                               │              │ backend          │
                               │              └────────┬─────────┘
                               │                       │
                               ▼                       ▼
                      ┌────────────────────────────────────┐
                      │      PostgreSQL 15 (:5432)         │
                      │      容器: ai4se-db                 │
                      └────────────────────────────────────┘
```

| 服务 | 容器名 | 端口 | 技术栈 |
|------|--------|------|--------|
| **postgres** | ai4se-db | 5432 | PostgreSQL 15 Alpine |
| **intent-tester** | ai4se-intent-tester | 5001 | Flask + SocketIO + MidScene |
| **new-agents** | ai4se-new-agents | - | Nginx (静态文件服务) |
| **new-agents-backend** | ai4se-new-agents-backend | 5002 | Flask + OpenAI SDK + PydanticAI + Gunicorn |
| **nginx** | ai4se-gateway | 80/443 | Nginx Alpine |

---

## Nginx 路由规则

| 路径 | 上游 | 说明 |
|------|------|------|
| `/` | 静态文件 `frontend/dist` | 统一门户 React SPA |
| `/assets/`, `/static/` | 同上 | 静态资源，30 天缓存 |
| `/intent-tester/` | `intent-tester:5001` | 意图测试工具（含 WebSocket 升级） |
| `/new-agents/api/` | `new-agents-backend:5002` | AI Agent 后端 API（路径重写为 `/api/$1`） |
| `/new-agents/` | `new-agents:80` | AI Agent 前端 SPA |
| `/health` | 直接返回 200 | 网关健康检查 |

---

## Part 1: frontend（统一门户）

**类型**: Web 前端 SPA  
**技术栈**: React 19 + Vite 7 + TypeScript 5.9 + Tailwind CSS 3 + React Router 7

### 架构模式

- 标准 React SPA，页面级路由
- `CompactLayout` 提供导航栏与响应式布局

### 路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | Home | 首页：Hero、模块介绍、视频演示、使用场景 |
| `/profile` | Profile | 个人中心 |

### 组件结构

```text
App (BrowserRouter)
├── CompactLayout
│   ├── Navbar
│   └── Footer
├── Route "/" → Home
│   ├── HeroSection
│   ├── ModulesSection
│   ├── VideoSection
│   ├── UseCasesSection
│   └── QuickLinksSection
└── Route "/profile" → Profile
```

---

## Part 2: intent-tester（意图测试工具）

**类型**: Full-Stack (Flask + Jinja2 + Node.js)  
**技术栈**: Flask 2.0+ + Flask-SocketIO + SQLAlchemy + Playwright + MidSceneJS

### 架构模式

- **后端**: Flask 应用工厂模式 + Blueprint 路由
- **前端**: 服务端渲染 (Jinja2 模板) + 原生 JS 组件
- **浏览器自动化**: 独立 Node.js Express 服务 (MidScene Server)

### 后端分层

```text
backend/
├── app.py              → Flask 应用工厂 (create_app)
├── models/models.py    → SQLAlchemy 数据模型 (8 个模型)
├── api/                → Blueprint 路由层
│   ├── testcases.py    → 测试用例 CRUD API
│   ├── executions.py   → 执行管理 API
│   ├── midscene.py     → MidScene 集成 API
│   └── proxy.py        → 代理包下载
├── services/           → 业务逻辑层
│   ├── execution_service.py   → 测试执行编排（线程调度）
│   ├── ai_step_executor.py    → AI 步骤执行器
│   └── variable_resolver_service.py → 变量解析与管理
├── utils/              → 工具层
│   ├── error_handler.py       → 统一异常处理 + 装饰器
│   └── monitoring.py          → 性能监控
└── extensions.py       → SocketIO 扩展实例
```

### MidScene 浏览器自动化架构

独立 Node.js 进程，通过 HTTP API 与 Flask 后端通信：

| 端点 | 说明 |
|------|------|
| `/api/execute-testcase` | 执行完整测试用例 |
| `/ai-tap`, `/ai-input`, `/ai-query`, `/ai-assert` | AI 驱动的浏览器操作 |
| `/goto`, `/screenshot`, `/page-info` | 基础浏览器控制 |

WebSocket 事件推送执行进度（step-start, step-completed, execution-completed 等）。

---

## Part 3: new-agents-frontend（AI 智能体工作台）

**类型**: Web 前端 SPA  
**技术栈**: React 19 + Vite 6 + TypeScript 5.8 + Zustand 5 + Tailwind CSS 4

### 架构模式

- **多智能体 + 多工作流**: 共享 manifest + 三层配置（`workflow_manifest.json` → agents / agentWorkflows / workflows）
- **阶段式工作流**: 每个工作流包含多个阶段，消费 typed Agent Runtime 事件推进
- **单一 LLM 主链路**: 主 Agent 对话统一通过后端 PydanticAI Agent Runtime SSE，不在浏览器保存或直连个人 API Key

### 智能体与工作流

| 智能体 | 角色 | 工作流 |
|--------|------|--------|
| **Lisa** | 测试专家 | 测试设计 (4 阶段)、需求评审 (2 阶段)、故障复盘 (3 阶段) |
| **Alex** | 业务分析师 | 创意头脑风暴 (4 阶段)、价值发现 (4 阶段) |

### 状态管理

- **Zustand** + `persist` 中间件
- 前端工作台状态当前仍持久化到 `localStorage` (key: `agent-workspace-storage`)
- 主要状态：工作流进度、对话历史、产出物版本
- 后端已具备通用 run/message/artifact/version 持久化模型和 repository，并通过现有 typed SSE 记录服务端 run；前端会保存并复用 `run_started.runId`，有服务端 run 时聊天历史上下文由后端 context builder 组装，但服务端会话恢复 UI 仍是后续工作

### 组件层级

```text
App (BrowserRouter, basename="/new-agents")
├── Route "/" → AgentSelect
├── Route "/workflows/:agentId" → WorkflowSelect
└── Route "/workspace/:agentId/:workflowId" → Workspace
    ├── Header + WorkflowDropdown (历史会话 / 运行统计 / Lisa 测试资产入口)
    ├── ChatPane (含 Mermaid 渲染)
    ├── ArtifactPane (Markdown 预览 + 版本历史)
    └── SettingsModal
```

### 关键特性

- **流式对话**: SSE 实时输出
- **产出物管理**: Markdown 产出物 + 版本历史 + 下载
- **左侧 Markdown 对话**: `ChatPane` 复用 ReactMarkdown / GFM / shared code renderer，只显示工作摘要、方法、关键结论和引导，不承载完整 artifact
- **Mermaid 图表**: 容错渲染（sanitize → 激进 sanitize → LLM 重试修复），关键阶段由后端 Mermaid contract 要求必需图类型
- **运行统计**: `Header` 的“运行统计”入口读取 `/api/agent/observability`，展示总览、阶段/供应商聚合和最近 turn
- **附件支持**: Base64 编码上传

### Workflow 配置源

- `tools/new-agents/workflow_manifest.json` 是在线 workflow 首轮共享元数据源，包含 workflow id、`agentId`、slug、展示文案、listing、stage id/name 和 onboarding。
- `frontend/src/core/workflows.ts` 从 manifest 读取基础元数据，并挂接 TypeScript prompt/template 常量，生成运行时 `WORKFLOWS`、`WORKFLOW_SLUGS` 和 `SLUG_TO_WORKFLOW`。
- `backend/agent_contracts.py` 仍维护 `WORKFLOW_STAGES`、`REQUIRED_ARTIFACT_HEADINGS`、`REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` 等后端契约；`backend/tests/test_workflow_contract_sync.py` 校验 manifest 与后端阶段/contract 同步。

---

## Part 4: new-agents-backend（结构化 Agent Runtime 后端）

**类型**: 后端 API  
**技术栈**: Flask 3.0 + SQLAlchemy 2.0 + OpenAI SDK + PydanticAI + Gunicorn

### 架构模式

- **应用工厂 + Blueprint**: `app.py` 负责应用装配，API route 位于 `routes.py`
- **结构化 Agent Runtime**: 主 Agent 对话通过 `/api/agent/runs/stream` 返回 typed SSE event
- **Mermaid 工具端点**: Mermaid 修复通过 `/api/utils/mermaid/repair` 返回 typed JSON
- **配置驱动**: 从 PostgreSQL `llm_config` 表读取 API Key
- **会话持久化基础层**: `models.py` 定义 `agent_runs`、`agent_messages`、`agent_artifacts`、`agent_artifact_versions`、`agent_context_summaries`，`run_persistence.py` 提供通用 repository；`/api/agent/runs/stream` 可选接收 `runId`，并在 `run_started.runId` 返回服务端 run
- **上下文构建基础层**: `context_builder.py` 基于已持久化 run 的有序 messages 和当前 artifact summary 构造 bounded runtime prompt；artifact summary 优先来自 `agent_context_summaries`，旧数据缺 summary 时回退 current artifact；截断时通过 `run_started.warnings=["context_truncated"]` 通知前端；首轮和附件内容仍由前端随当前请求提供
- **运行时可观测性基础层**: `agent_run_turn_metrics` 记录共享 Agent Runtime 每轮 workflow、stage、模型、provider、状态、错误码、耗时和估算 token；`GET /api/agent/observability` 提供只读聚合，前端 `Header` 以只读弹层展示
- **Lisa 测试资产基础层**: `test_assets.py` 从 `TEST_DESIGN/CASES` artifact 解析结构化测试用例和覆盖追溯，支持只读导出、服务端实体化、覆盖摘要、资产质量问题、测试点覆盖明细、风险矩阵、intent-tester 草稿和单条用例追加版本更新；前端 `Header` 的“测试资产”入口可实体化当前 run、展示资产质量问题、测试点覆盖与风险矩阵、编辑用例标题/优先级，手动单条或批量导入 intent-tester 草稿，并把已导入用例接力到 intent-tester 执行页，短期不分叉 Agent Runtime，也不在实体化时自动写入或直接执行 intent-tester 用例
- **跨工作流接力基础层**: `workflow_manifest.json` 顶层 `handoffs` 声明 Alex 到 Lisa 的配置化接力，`workflow_handoffs.py` 从 persisted run snapshot 生成 handoff context，并支持创建目标 Lisa run；继续复用 snapshot 恢复和 `/api/agent/runs/stream` 主链路，不新增 runtime 分支
- **Artifact 契约**: `AgentTurnOutput` 校验 chat/artifact 分离、阶段推进合法性、必需 artifact 字段和必需 Mermaid 图类型；非法模型输出在进入 SSE 层前失败

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/config` | 获取 LLM 配置（不含 API Key） |
| POST | `/api/config` | 创建或更新默认 LLM 配置（不返回 API Key） |
| POST | `/api/config/check` | 检测默认 LLM 配置是否可调用当前模型 |
| POST | `/api/agent/runs/stream` | 结构化 Agent Runtime SSE |
| GET | `/api/agent/runs/{runId}` | 已持久化 run snapshot |
| GET | `/api/agent/observability` | Agent Runtime 运行统计 |
| POST | `/api/agent/runs/{runId}/test-assets/materialize` | Lisa 测试资产实体化 |
| PATCH | `/api/agent/test-assets/{collectionId}/test-cases/{caseId}` | 追加更新单条测试用例版本 |
| POST | `/api/utils/mermaid/repair` | Mermaid 修复工具 |

### 安全设计

- API Key 仅存储于 PostgreSQL `llm_config` 表，不进入前端状态持久化
- `GET /api/config` 和 `POST /api/config` 响应都不返回 `api_key` / `apiKey` 字段
- `POST /api/config` 支持默认 LLM 配置更新和密钥轮换；已有配置时前端留空 API Key 会保留当前密钥
- 默认 LLM 配置 key 默认为 `default`，可通过 `NEW_AGENTS_DEFAULT_LLM_CONFIG_KEY` 在不同部署环境选择不同配置行和模型
- `POST /api/config/check` 使用当前默认配置执行最小模型调用，返回业务态 `ok` 和诊断消息，不回显密钥
- 前端获取 `hasDefault` 标志判断是否可用代理模式，并在设置弹层提供默认配置维护和可用性检测入口

---

## Part 5: shared（共享工具库）

**类型**: Python 库  
**技术栈**: Flask-SQLAlchemy + python-dotenv

### 模块

| 模块 | 说明 |
|------|------|
| `config/` | `SharedConfig` 类，从环境变量读取通用配置 |
| `database/` | `get_database_config()` 返回 SQLAlchemy 连接配置 |

### 使用方式

由 `intent-tester` 通过 `sys.path` 注入导入：

```python
from shared.config import SharedConfig
from shared.database import get_database_config
```

---

## 数据流

### 意图测试执行流

```text
用户 → Jinja2 UI → Flask API (:5001)
                        │
                        ├→ 创建 ExecutionHistory 记录
                        ├→ SocketIO 推送执行状态到前端
                        └→ HTTP 调用 MidScene Server (:3001)
                                    │
                                    ├→ Playwright 驱动浏览器
                                    ├→ @midscene/web AI 操作
                                    └→ WebSocket 回传步骤结果
```

### AI 智能体对话流

```text
用户 → React SPA → /new-agents/api/agent/runs/stream
                        │
                        ├→ Nginx 路由重写 → Flask :5002
                        ├→ 读取 llm_config 表获取 API Key
                        ├→ 创建或复用 agent_run，记录 user/assistant message
                        ├→ 有 runId 时基于服务端历史 messages 构造 runtime prompt
                        └→ PydanticAI Runtime → LLM API → typed SSE 响应 + artifact version 持久化

Mermaid 修复等工具调用使用 `/new-agents/api/utils/mermaid/repair`。
```

---

## 环境配置

### 必需的 `.env` 变量

```bash
# 数据库
DB_USER=ai4se_user
DB_PASSWORD=your_password

# 应用
SECRET_KEY=your-secret-key

# MidScene (本地运行浏览器自动化时需要)
OPENAI_API_KEY=your-openai-key    # MidScene AI 操作用
```

### LLM 配置来源

| 服务 | 配置来源 | 说明 |
|------|----------|------|
| **intent-tester** (MidScene) | 环境变量 `OPENAI_API_KEY` | MidScene 代理本地运行 |
| **new-agents-backend** | PostgreSQL `llm_config` 表 | 数据库驱动，禁止硬编码 |
