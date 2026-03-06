# AI4SE 项目文档索引

> 生成日期: 2026-03-06 | 扫描级别: Deep Scan | 工具: BMAD Document Project Workflow v1.2.0

---

## 项目概述

- **项目名称**: AI4SE (AI for Software Engineering)
- **仓库类型**: Monorepo（模块化单体仓库）— 5 个部分
- **主要语言**: Python 3.11 + TypeScript 5.8+
- **架构风格**: Docker Compose 容器编排 + Nginx 网关路由
- **数据库**: PostgreSQL 15（共享实例）

---

## 快速参考

### 各部分概览

| Part | 类型 | 技术栈 | 端口 | 路径 |
|------|------|--------|------|------|
| **frontend** | Web 前端 | React 19 + Vite + Tailwind | 80 (Nginx) | `/` |
| **intent-tester** | Full-Stack | Flask + SocketIO + MidScene/Playwright | 5001 | `/intent-tester/` |
| **new-agents-frontend** | Web 前端 | React 19 + Zustand + OpenAI SDK | 80 (Nginx) | `/new-agents/` |
| **new-agents-backend** | 后端 API | Flask + SQLAlchemy + OpenAI + Gunicorn | 5002 | `/new-agents/api/` |
| **shared** | 共享库 | Python (配置 + 数据库) | - | 内部导入 |

### 常用命令

```bash
# 部署开发环境
./scripts/dev/deploy-dev.sh

# 运行全部测试
./scripts/test/test-local.sh

# 代码质量检查
flake8 --select=E9,F63,F7,F82 .
```

---

## 生成的文档

### 核心文档

- [项目概览](./project-overview.md) — 项目简介、技术栈总览、组成部分
- [架构文档](./architecture.md) — 服务拓扑、各部分架构、数据流
- [源码树分析](./source-tree-analysis.md) — 完整目录结构与注解

### API 与数据

- [API 契约](./api-contracts.md) — 所有 REST/WebSocket 端点详细定义
- [数据模型](./data-models.md) — 数据库表结构与 ER 关系
- [集成架构](./integration-architecture.md) — 服务间通信、数据流、共享资源

### 开发与部署

- [开发指南](./development-guide.md) — 环境配置、本地开发、测试、构建
- [部署指南](./deployment-guide.md) — Docker 部署、CI/CD 流程、生产环境

### 组件

- [组件清单](./component-inventory.md) — React 组件、JS 模块、提示词模块

### 元数据

- [项目部分定义](./project-parts.json) — 结构化的项目组成元数据 (JSON)

---

## 现有文档（项目知识库）

以下文档在本次扫描之前就已存在于 `docs/` 中，内容仍有参考价值：

- [系统架构设计](./ARCHITECTURE.md) — 原有架构文档（Docker 服务拓扑、路由规则、数据流）
- [编码规范](./CODING_STANDARDS.md) — Python/TypeScript/Node.js 代码风格标准
- [设计原则](./DESIGN_PRINCIPLES.md) — Agent-First 哲学、确定性优先、Artifact 格式分离
- [测试策略](./TESTING.md) — 测试金字塔、Mock 策略、命名规范

### 迭代计划（已完成）

- [2026-02-28 New Agents 测试实施](./plans/completed/2026-02-28-new-agents-tests-implementation.md)
- [2026-02-28 New Agents 测试设计](./plans/completed/2026-02-28-new-agents-tests-design.md)
- [2026-02-27 New Agents 后端代理](./plans/completed/2026-02-27-new-agents-backend-proxy.md)
- [2026-02-27 归档旧 Agents](./plans/completed/2026-02-27-archive-old-agents.md)
- [2026-02-27 Lisa Agent 路由](./plans/completed/2026-02-27-lisa-agent-routing.md)
- [2026-02-27 Lisa Agent 路由设计](./plans/completed/2026-02-27-lisa-agent-routing-design.md)
- [2026-02-21 冒烟测试 Artifact 语义验证](./plans/completed/2026-02-21-smoke-test-artifact-semantic-validation.md)
- [2026-02-21 Artifact Hint 状态同步](./plans/completed/2026-02-21-artifact-hint-status-sync.md)
- [2026-02-21 P1 冒烟测试用例](./plans/completed/2026-02-21-p1-smoke-test-cases.md)
- [2026-02-11 Artifact 内联差异设计](./plans/completed/2026-02-11-artifact-inline-diff-design.md)
- [2026-02-10 需求 Artifact 重构](./plans/completed/2026-02-10-requirement-artifact-refactor.md)
- [2026-02-09 结构化增量更新](./plans/completed/2026-02-09-structured-incremental-update.md)

### 测试需求文档

- [Lisa Artifact 同步](./test_requirements/lisa_artifact_sync.md)
- [登录功能](./test_requirements/login.md)
- [优惠券 API](./test_requirements/requirements_coupon_api.md)

---

## 快速上手

### 开发环境搭建

1. 克隆仓库并配置环境变量（参见 [开发指南](./development-guide.md)）
2. 运行 `./scripts/dev/deploy-dev.sh` 启动所有服务
3. 访问 http://localhost 查看统一门户

### AI 辅助开发

当使用 AI 辅助进行开发时，建议按以下方式提供上下文：

- **全栈特性**: 提供 `architecture.md` + `integration-architecture.md`
- **前端特性 (new-agents)**: 提供 `architecture.md` (Part 3 部分) + `component-inventory.md`
- **后端特性 (intent-tester)**: 提供 `architecture.md` (Part 2 部分) + `api-contracts.md` + `data-models.md`
- **部署/运维**: 提供 `deployment-guide.md`
- **Brownfield PRD**: 提供本 `index.md` 作为入口

### 技术债务

- [x] 根 `requirements.txt` 中残留的 LangChain/LangGraph/Google ADK 依赖已清理
- [x] `tools/shared/config/__init__.py` 中残留的 LANGCHAIN 相关配置已清理

---

## 与 AGENTS.md 的关系

本索引是项目知识库的主入口。[AGENTS.md](../AGENTS.md) 是 AI Agent 的行为准则与工作指引，其「深层文档导航」部分会根据场景指向本索引及各子文档。

- **AGENTS.md** → 定义 Agent "怎么做"（规则、禁止模式、TDD 协议、命令速查）
- **docs/index.md** → 定义项目 "是什么"（架构、API、数据模型、组件、部署）

Agent 首次接触项目时，应先阅读本索引获取全局视野，再按需查阅子文档。

---

## 文档维护

本文档由 BMAD Document Project Workflow 自动生成。如需更新：

1. 修改代码后重新运行 `/bmad-bmm-document-project`
2. 选择 "Re-scan entire project" 进行全量更新
3. 或选择 "Deep-dive into specific area" 针对特定区域深度扫描
