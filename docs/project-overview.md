# AI4SE 项目概览

> 生成日期: 2026-03-06 | 扫描级别: Deep Scan

## 项目简介

AI4SE（AI for Software Engineering）是一个面向软件工程的 AI 辅助工具平台，采用模块化单体仓库（Modular Monorepo）架构。平台集成了多种 AI 驱动的软件工程工具，包括意图测试框架、AI 智能体工作台等，通过统一的 Nginx 网关对外提供服务。

## 仓库类型

**Monorepo** — 多个独立服务共存于同一仓库，通过 `tools/shared/` 共享基础设施代码。

## 技术栈总览

| 类别 | 技术 | 版本 |
|------|------|------|
| **前端框架** | React | 19.x |
| **前端构建** | Vite | 6.x / 7.x |
| **前端语言** | TypeScript | 5.8+ |
| **CSS 框架** | Tailwind CSS | 3.x / 4.x |
| **状态管理** | Zustand | 5.x |
| **后端框架** | Flask | 3.0.x |
| **ORM** | Flask-SQLAlchemy / SQLAlchemy | 2.0.x |
| **数据库** | PostgreSQL | 15 |
| **实时通信** | Flask-SocketIO / Socket.IO | 5.x / 4.x |
| **浏览器自动化** | Playwright + MidSceneJS | 1.56+ / 0.30.x |
| **LLM 客户端** | OpenAI Python/JS SDK | 1.58+ / 6.x |
| **容器化** | Docker + Docker Compose | - |
| **反向代理** | Nginx | Alpine |
| **CI/CD** | GitHub Actions | - |
| **测试** | pytest / Jest / Vitest | - |

## 项目组成（5 个部分）

| Part | 路径 | 类型 | 说明 |
|------|------|------|------|
| **frontend** | `tools/frontend/` | Web 前端 | 统一门户 SPA，展示平台首页与导航 |
| **intent-tester** | `tools/intent-tester/` | Full-Stack | 意图测试工具：Flask API + Jinja2 前端 + MidScene 浏览器自动化 |
| **new-agents-frontend** | `tools/new-agents/frontend/` | Web 前端 | AI 智能体工作台 SPA（Lisa/Alex 多工作流） |
| **new-agents-backend** | `tools/new-agents/backend/` | 后端 API | LLM SSE 流式代理服务 |
| **shared** | `tools/shared/` | 共享库 | 跨工具共享的 Python 配置与数据库连接 |

## 架构模式

- **服务编排**: Docker Compose 管理所有服务
- **入口网关**: Nginx 反向代理，路径路由到各服务
- **数据层**: 共享 PostgreSQL 实例
- **LLM 集成**: 双模式（前端直连 / 后端代理 SSE 转发）
- **实时通信**: WebSocket（SocketIO）用于测试执行状态推送

## 相关文档

- [架构详情](./architecture.md)
- [源码树分析](./source-tree-analysis.md)
- [开发指南](./development-guide.md)
- [API 契约](./api-contracts.md)
- [数据模型](./data-models.md)
- [集成架构](./integration-architecture.md)
- [部署指南](./deployment-guide.md)
