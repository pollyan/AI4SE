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
| **new-agents-backend** | ai4se-new-agents-backend | 5002 | Flask + OpenAI + Gunicorn |
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
**技术栈**: React 19 + Vite 6 + TypeScript 5.8 + Zustand 5 + Tailwind CSS 4 + OpenAI SDK 6

### 架构模式

- **多智能体 + 多工作流**: 三层配置（agents → agentWorkflows → workflows）
- **阶段式工作流**: 每个工作流包含多个阶段，LLM 输出 `<ACTION>NEXT_STAGE</ACTION>` 推进
- **双通道 LLM 调用**: 用户 API Key 直连 或 后端代理 SSE 转发

### 智能体与工作流

| 智能体 | 角色 | 工作流 |
|--------|------|--------|
| **Lisa** | 测试专家 | 测试设计 (4 阶段)、需求评审 (2 阶段)、故障复盘 (3 阶段) |
| **Alex** | 业务分析师 | 创意头脑风暴 (4 阶段)、价值发现 (4 阶段) |

### 状态管理

- **Zustand** + `persist` 中间件
- 持久化到 `localStorage` (key: `agent-workspace-storage`)
- 主要状态：LLM 配置、工作流进度、对话历史、产出物版本

### 组件层级

```text
App (BrowserRouter, basename="/new-agents")
├── Route "/" → AgentSelect
├── Route "/workflows/:agentId" → WorkflowSelect
└── Route "/workspace/:agentId/:workflowId" → Workspace
    ├── Header + WorkflowDropdown
    ├── ChatPane (含 Mermaid 渲染)
    ├── ArtifactPane (Markdown 预览 + 版本历史)
    └── SettingsModal
```

### 关键特性

- **流式对话**: SSE 实时输出
- **产出物管理**: Markdown 产出物 + 版本历史 + 下载
- **Mermaid 图表**: 容错渲染（sanitize → 激进 sanitize → LLM 重试修复）
- **附件支持**: Base64 编码上传

---

## Part 4: new-agents-backend（LLM 代理后端）

**类型**: 后端 API  
**技术栈**: Flask 3.0 + SQLAlchemy 2.0 + OpenAI SDK 1.58 + Gunicorn

### 架构模式

- **单体应用**: 所有路由集中在 `app.py`
- **代理模式**: SSE 流式转发 LLM 请求
- **配置驱动**: 从 PostgreSQL `llm_config` 表读取 API Key

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/config` | 获取 LLM 配置（不含 API Key） |
| POST | `/api/chat/stream` | SSE 流式聊天代理 |

### 安全设计

- API Key 仅存储于 PostgreSQL `llm_config` 表，手动 SQL 插入
- `/api/config` 端点不返回 `api_key` 字段
- 前端获取 `hasDefault` 标志判断是否可用代理模式

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
用户 → React SPA → 判断 LLM 模式
                        │
                        ├→ [直连模式] OpenAI SDK → LLM API
                        │
                        └→ [代理模式] /new-agents/api/chat/stream
                                    │
                                    ├→ Nginx 路由重写 → Flask :5002
                                    ├→ 读取 llm_config 表获取 API Key
                                    └→ OpenAI SDK → LLM API → SSE 流式响应
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
| **new-agents-frontend** (直连) | 用户在 Settings 中手动输入 | 存储于 localStorage |
