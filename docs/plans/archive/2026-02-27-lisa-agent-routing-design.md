# Lisa Agent 入口对接设计方案

> 日期：2026-02-27
> 状态：已确认

## 1. 背景

现有系统在 `tools/ai-agents` 中包含一个前端入口页面（`CompactApp`），展示 Alex 和 Lisa 两个 AI 助手卡片。用户选择后进入对应的聊天界面，通过后端 Flask API 驱动 AI 交互。

同时，在 `tools/new-agents` 下新建了一个**纯前端**的 Lisa 测试专家 Agent，基于 Vite + React + TypeScript + Tailwind v4 + Zustand + OpenAI 兼容 API 构建，拥有独立的状态机驱动工作流（测试设计/需求评审）。

**目标**：用户在现有入口选择 Lisa 后，直接跳转到新 Agent 的独立页面。

## 2. 技术决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 对接方式 | **外链跳转**（方案 B）| 两个系统技术栈差异大，独立运行互不影响，改动最小 |
| URL 路径 | `/new-agents/` | 与代码目录名一致，未来可扩展更多 agent |
| 部署方式 | **Docker 容器** | 为未来扩展后端预留空间，与现有部署模式一致 |

## 3. 改动范围

### 3.1 现有入口对接 — `CompactApp.tsx`

修改 `handleSelectAssistant` 函数：
- 当 `id === 'lisa'` 时，执行 `window.location.href = '/new-agents/'` 跳转
- 当 `id === 'alex'` 时，保持原有行为不变

### 3.2 新 Agent Docker 化 — `tools/new-agents/`

创建 `Dockerfile`（多阶段构建）：
- **阶段一（构建）**：`node:20-alpine`，执行 `npm ci && npm run build`
- **阶段二（运行）**：`nginx:alpine`，将 `dist/` 复制到 Nginx serve 目录

### 3.3 Docker Compose 配置 — `docker-compose.yml`

在 `tools/ai-agents/docker/docker-compose.yml` 中添加 `new-agents` 服务：
- 构建上下文指向 `tools/new-agents`
- 容器名 `intent-test-new-agents`
- 内部端口 80（Nginx）

### 3.4 Nginx 路由 — `nginx/nginx.conf`

添加 `location /new-agents/` 配置：
- 反向代理到 `new-agents` 容器
- 支持 SPA 路由（`try_files`）

### 3.5 Vite 配置 — `vite.config.ts`

修改 `base` 为 `/new-agents/`，确保构建产物的资源路径正确。

## 4. 数据流

```
用户选择 Lisa
  → CompactApp: window.location.href = '/new-agents/'
  → Nginx: location /new-agents/ → proxy_pass new-agents 容器
  → new-agents 容器: Nginx serve 静态文件 (Vite build 产物)
  → 用户看到新 Agent 主页面

用户选择 Alex
  → 保持原有行为 → ai-agents 后端处理
```

## 5. 不在本次范围内（YAGNI）

- ❌ 不改变新 agent 内部的任何功能逻辑
- ❌ 不做统一登录/鉴权
- ❌ 不做跨 agent 的状态共享
- ❌ 不修改 Alex 的任何功能
