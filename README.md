# AI4SE

> 一个面向软件工程场景的 AI 工具平台 Demo，聚焦 **AI Agent 工作流**、**浏览器自动化测试** 和 **模块化工程组织**。

AI4SE（AI for Software Engineering）是一个个人项目型的 AI 软件工程平台。我用它来探索这样一件事：**能不能把需求分析、测试设计、浏览器自动化执行、产出物生成和多智能体工作流，放进一个结构清晰、可运行、可扩展的工程系统里。**

这个仓库不是单点功能 Demo，而是一个模块化 monorepo：前端、后端、测试工具、Agent 工作台、共享基础设施都放在同一个项目里，通过 Nginx + Docker Compose 统一编排，对外提供一致入口。

## 为什么这个项目值得看

- **不只是调接口**：项目里既有 AI 对话工作台，也有面向测试场景的浏览器自动化工具。
- **有明确工程边界**：前端、后端、共享库、自动化代理分层清楚，不是把所有逻辑堆在一个服务里。
- **支持真实交互流**：包含 SSE 流式输出、WebSocket 状态推送、数据库配置驱动等完整链路。
- **强调工程可运行性**：本地开发、Docker 部署、测试脚本、文档索引都比较完整。
- **适合作为作品集项目**：如果你是招聘方、开发者或访客，能很快看懂项目做了什么、复杂度在哪里、我关注的工程问题是什么。

## 项目包含什么

### 1. AI Agent 工作台

位于 `tools/new-agents/`，包含前后端两部分：

- **前端**：React + TypeScript + Zustand + Tailwind
- **后端**：Flask + OpenAI SDK + PydanticAI Agent Runtime + typed SSE

它支持多智能体、多工作流、多阶段输出，当前包含像 Lisa、Alex 这样的角色设定，以及测试设计、需求评审、头脑风暴、需求蓝图梳理等工作流。

这个模块更像一个 **AI 协作工作台**，而不是一个单纯聊天页面。它关注的是：

- 如何组织阶段式工作流
- 如何管理对话产出物
- 如何通过统一后端 Agent Runtime 管理 LLM 调用和 typed SSE 输出
- 如何让 Mermaid、Markdown、历史版本这些内容在真实 UI 中工作起来

### 2. 意图测试与浏览器自动化工具

位于 `tools/intent-tester/`，是一个面向测试场景的 Full-Stack 工具：

- Flask API + Jinja2 页面
- Playwright + MidSceneJS 浏览器自动化
- Socket.IO 实时执行状态推送

它的目标不是做一个通用测试平台，而是探索 **AI 如何参与测试步骤执行、状态跟踪和测试用例运行**。

### 3. 统一门户与共享基础设施

- `tools/frontend/`：平台统一门户
- `tools/shared/`：共享 Python 配置与数据库连接能力
- `nginx/`：统一网关和路径路由
- `scripts/`：开发、测试、部署脚本

## 核心工程特性

- **Modular Monorepo**：多个独立模块放在同一仓库，复用共享基础设施
- **统一网关入口**：通过 Nginx 将 `/`、`/intent-tester/`、`/new-agents/` 路由到不同服务
- **单一 LLM 主链路**：主 Agent 对话统一通过后端 PydanticAI Agent Runtime 调用 LLM
- **流式与实时能力**：SSE 用于 LLM 输出流式返回，WebSocket 用于测试执行状态同步
- **Docker 优先开发模式**：通过 Docker Compose 统一启动和验证整个系统
- **文档化较完整**：架构、API、数据模型、开发指南、部署指南都有对应文档

## 技术栈

| 类别 | 技术 |
|------|------|
| 前端 | React 19, TypeScript 5.8+, Vite, Tailwind CSS, Zustand |
| 后端 | Flask, SQLAlchemy, Gunicorn |
| 数据层 | PostgreSQL 15 |
| 实时通信 | SSE, Socket.IO |
| 自动化 | Playwright, MidSceneJS |
| AI 集成 | OpenAI Python SDK, PydanticAI |
| 部署 | Docker, Docker Compose, Nginx |
| 测试 | pytest, Jest, Vitest |

## 仓库结构

```text
AI4SE/
├── tools/
│   ├── frontend/                # 统一门户前端
│   ├── intent-tester/           # 意图测试 + 浏览器自动化工具
│   ├── new-agents/
│   │   ├── frontend/            # AI Agent 工作台前端
│   │   └── backend/             # AI Agent 工作台后端
│   └── shared/                  # 共享 Python 基础设施
├── docs/                        # 项目文档
├── scripts/                     # 开发 / 测试 / 部署脚本
├── nginx/                       # 网关配置
├── tests/                       # E2E 与其他测试资源
└── dist/                        # 构建产物
```

## 架构一览

```text
Nginx Gateway
├── /                  → frontend
├── /intent-tester/    → Flask + MidScene
└── /new-agents/       → React SPA + Flask API

Shared PostgreSQL
└── 为多个服务提供统一数据存储
```

项目整体采用 **Nginx + Docker Compose + PostgreSQL** 的组合：

- `frontend` 负责统一入口和项目展示
- `intent-tester` 负责测试执行与自动化相关能力
- `new-agents` 负责 AI 工作流交互界面
- `new-agents-backend` 负责代理式 LLM 调用与配置读取
- `shared` 提供通用配置和数据库接入能力

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+
- Docker
- Docker Compose v2+

### 1) 克隆仓库

```bash
git clone <repo-url> AI4SE
cd AI4SE
```

### 2) 配置环境变量

```bash
cp .env.example .env
```

至少需要补充数据库账号和应用密钥等配置。更完整的说明见 [`docs/development-guide.md`](docs/development-guide.md)。

### 3) 启动开发环境（推荐）

```bash
./scripts/dev/deploy-dev.sh
```

启动后可访问：

- 统一门户：`http://localhost`
- 意图测试：`http://localhost/intent-tester`
- AI Agent 工作台：`http://localhost/new-agents`

### 4) 查看日志

```bash
docker-compose -f docker-compose.dev.yml logs -f
```

## 测试与质量检查

运行本地确定性验证（不包含外部真实模型 smoke）：

```bash
./scripts/test/test-local.sh
```

真实模型 smoke 需显式运行 `./scripts/test/test-local.sh smoke`；缺少必需环境变量时会报告 `NOT_RUN` 并失败，不会伪装为绿色。

常用命令：

```bash
# Python 测试
pytest

# New Agents Backend
cd tools/new-agents/backend && pytest tests/test_api.py -c pytest.ini

# New Agents Frontend
cd tools/new-agents/frontend && npm test

# Python 关键 lint
flake8 --select=E9,F63,F7,F82 .
```

## 推荐阅读路径

如果你是第一次看这个仓库，建议按这个顺序：

1. [`docs/index.md`](docs/index.md) — 项目文档总入口
2. [`docs/project-overview.md`](docs/project-overview.md) — 项目组成与技术栈概览
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — 服务拓扑、路由和数据流
4. [`docs/development-guide.md`](docs/development-guide.md) — 本地开发、测试、构建方式
5. [`docs/api-contracts.md`](docs/api-contracts.md) — 后端接口定义

## 这个项目适合谁看

- **招聘方 / 面试官**：可以快速看到我在 AI 应用、工程组织、前后端协作和自动化测试上的实践。
- **开发者**：可以直接从 monorepo 结构、模块边界、文档和脚本里理解项目设计。
- **对 AI for SE 感兴趣的访客**：可以把它当作一个关于“AI 如何进入软件工程工作流”的实验项目来看。

## 后续可以继续增强的方向

如果后面你准备继续把这个仓库当作 GitHub 首页项目展示，我建议再补这几样：

- README 顶部加 **项目截图 / GIF 演示**
- 增加 **当前功能状态 / Roadmap**
- 增加 **我为什么做这个项目** 一节
- 增加 **Demo 视频 / 在线预览链接**（如果有）
- 增加 **贡献指南**（如果你准备开放协作）

## License

MIT
