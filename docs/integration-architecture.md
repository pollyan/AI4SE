# 集成架构文档

> 生成日期: 2026-03-06 | 扫描级别: Deep Scan

## 集成概览

AI4SE 各服务通过以下方式集成：

1. **Nginx 反向代理**: 统一入口，路径路由到各服务
2. **共享 PostgreSQL**: 所有服务连接同一数据库实例
3. **共享 Python 工具**: `tools/shared/` 提供配置和数据库连接
4. **HTTP API 调用**: Flask 后端 → MidScene Server
5. **SSE 流式**: 前端 ↔ 后端 LLM 代理

---

## 集成点矩阵

| # | 源 (From) | 目标 (To) | 类型 | 协议 | 详情 |
|---|-----------|-----------|------|------|------|
| 1 | Nginx | frontend/dist | 静态文件 | HTTP | `/` → 本地文件系统 |
| 2 | Nginx | intent-tester | 反向代理 | HTTP/WS | `/intent-tester/` → `:5001` |
| 3 | Nginx | new-agents (前端) | 反向代理 | HTTP | `/new-agents/` → `:80` |
| 4 | Nginx | new-agents-backend | 反向代理 | HTTP/SSE | `/new-agents/api/` → `:5002` (路径重写) |
| 5 | intent-tester Flask | MidScene Server | HTTP API | REST | `:5001` → `:3001` (跨容器 host.docker.internal) |
| 6 | intent-tester Flask | PostgreSQL | TCP | SQL | `:5001` → `:5432` |
| 7 | new-agents-backend | PostgreSQL | TCP | SQL | `:5002` → `:5432` |
| 8 | new-agents-frontend | new-agents-backend | SSE | HTTP | `/new-agents/api/chat/stream` (代理模式) |
| 9 | new-agents-frontend | 外部 LLM API | HTTPS | REST | OpenAI SDK 直连 (直连模式) |
| 10 | MidScene Server | 外部 LLM API | HTTPS | REST | AI 驱动的浏览器操作 |
| 11 | intent-tester Flask | 客户端浏览器 | WebSocket | SocketIO | 执行状态实时推送 |
| 12 | MidScene Server | intent-tester Flask | HTTP | REST | 执行开始/结果回调 |

---

## 数据流详解

### 1. 用户访问统一门户

```text
浏览器 → https://domain/
      → Nginx (80)
      → 静态文件 tools/frontend/dist/index.html
      → React SPA 加载
      → 导航到 /intent-tester/ 或 /new-agents/
```

### 2. 意图测试执行流

```text
用户操作                 Intent-Tester Flask (:5001)           MidScene Server (:3001)
   │                              │                                    │
   ├─ POST /api/executions ──────►│                                    │
   │                              ├─ 创建 ExecutionHistory              │
   │                              ├─ 启动执行线程                        │
   │  ◄── SocketIO: execution-start ─┤                                 │
   │                              ├─ POST /api/execute-testcase ──────►│
   │                              │                                    ├─ 启动 Playwright
   │                              │                                    ├─ 逐步执行 AI 操作
   │  ◄── SocketIO: step-start ──────┤◄─ WebSocket: step-start ───────┤
   │  ◄── SocketIO: step-completed ──┤◄─ WebSocket: step-completed ───┤
   │                              │                                    │
   │                              ├─ 更新 StepExecution 记录             │
   │                              ├─ 保存截图                           │
   │  ◄── SocketIO: execution-completed ─┤                             │
```

### 3. AI 智能体对话流（代理模式）

```text
用户输入                 React SPA                  Nginx              Flask :5002          外部 LLM
   │                      │                          │                     │                   │
   ├─ 发送消息 ──────────►│                          │                     │                   │
   │                      ├─ POST /new-agents/api/chat/stream ──────────►│                   │
   │                      │                          ├─ 重写为 /api/chat/stream ──────────────►│
   │                      │                          │                     ├─ 读取 llm_config   │
   │                      │                          │                     ├─ OpenAI SDK ──────►│
   │                      │◄─── SSE: delta chunks ────────────────────────┤◄── SSE chunks ────┤
   │  ◄── 流式渲染 ────────┤                          │                     │                   │
   │                      ├─ 解析 <CHAT>, <ARTIFACT>, <ACTION> 标签         │                   │
   │                      ├─ 更新 Zustand Store                            │                   │
   │  ◄── UI 更新 ─────────┤                          │                     │                   │
```

### 4. AI 智能体对话流（直连模式）

```text
用户输入                 React SPA                  外部 LLM API
   │                      │                            │
   ├─ 发送消息 ──────────►│                            │
   │                      ├─ OpenAI SDK (用户 API Key) ──►│
   │                      │◄──── SSE: delta chunks ───────┤
   │  ◄── 流式渲染 ────────┤                            │
```

---

## 共享资源

### 共享数据库 (PostgreSQL)

所有服务共享同一 PostgreSQL 实例，但使用**不同的表**：

| 服务 | 使用的表 |
|------|----------|
| intent-tester | test_cases, execution_history, step_executions, execution_variables, variable_references, requirements_sessions, requirements_messages, requirements_ai_configs |
| new-agents-backend | llm_config |

### 共享代码 (`tools/shared/`)

| 模块 | 使用方 | 功能 |
|------|--------|------|
| `shared.config.SharedConfig` | intent-tester | 通用配置（SECRET_KEY 等） |
| `shared.database.get_database_config` | intent-tester | SQLAlchemy 数据库配置 |

注意: `new-agents-backend` 有自己独立的 `config.py`，不使用 `shared/`。

### 共享网络 (`ai4se-network`)

所有 Docker 容器位于同一 Docker 网络 `ai4se-network`，通过容器名互相访问。

---

## 跨服务依赖关系

```text
nginx ──depends_on──► intent-tester ──depends_on──► postgres
      ──depends_on──► new-agents
      ──depends_on──► new-agents-backend ──depends_on──► postgres

intent-tester ──runtime_call──► MidScene Server (host.docker.internal:3001)
```

### 启动顺序

1. `postgres` (健康检查通过后)
2. `intent-tester` + `new-agents-backend` (等待 postgres 健康)
3. `new-agents` (无依赖)
4. `nginx` (等待所有上游服务)

---

## 环境隔离

| 环境 | Compose 文件 | 特点 |
|------|-------------|------|
| **开发** | `docker-compose.dev.yml` | 源码挂载、无资源限制、本地构建 |
| **生产** | `docker-compose.prod.yml` | 独立镜像、资源限制、备份回滚 |
| **测试** | 无容器 | SQLite 内存数据库、Mock 外部服务 |
