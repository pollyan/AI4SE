<div align="center">
  <h1>🤖 AI4SE</h1>
  <p><strong>AI for Software Engineering</strong></p>
  <p>AI 驱动的软件工程工具平台</p>

  <p>
    <a href="#快速开始">快速开始</a> •
    <a href="#核心功能">核心功能</a> •
    <a href="#架构设计">架构设计</a> •
    <a href="#开发指南">开发指南</a> •
    <a href="#api-文档">API 文档</a>
  </p>
</div>

---

## 📖 项目概述

AI4SE（AI for Software Engineering）是一个模块化的 AI 辅助软件工程平台，旨在通过 AI 智能体和自动化工具提升开发效率。

### 核心能力

| 功能 | 描述 |
|------|------|
| **🧠 AI 需求分析** | 与 AI 智能体 (Alex) 协作，快速梳理需求并生成 PRD |
| **🧪 AI 测试设计** | 与测试专家 (Lisa) 协作，进行测试策略设计和需求评审 |
| **🎯 意图驱动测试** | 使用自然语言描述测试用例，由 AI (MidScene) 自动执行浏览器操作 |
| **🏠 统一开发门户** | 全新的 React 门户，集成所有工具入口 |

### 架构类型

**Modular Monorepo** (模块化单体) - 所有工具代码在同一个仓库中，但保持独立部署和运行的能力。

---

## 🚀 快速开始

### 环境要求

- **Docker** & **Docker Compose** (必需)
- **Node.js 20+** (本地开发需要)
- **Python 3.11+** (本地开发需要)

### 一键启动 (推荐)

```bash
# 克隆项目
git clone https://github.com/your-org/AI4SE.git
cd AI4SE

# 复制环境变量文件
cp .env.example .env
# 编辑 .env 文件，填入必要的配置（OPENAI_API_KEY 等）

# 启动本地开发环境
./scripts/dev/deploy-dev.sh
```

### 访问地址

启动成功后，通过以下地址访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| 🏠 主页 | http://localhost | 统一门户首页 |
| 🤖 AI 智能体 | http://localhost/new-agents | Lisa 对话界面 |
| 🧪 意图测试 | http://localhost/intent-tester | 测试用例管理与执行 |

### 本地 MidScene 代理 (用于自动化测试)

```bash
cd tools/intent-tester
npm install
npm start
# 代理运行在 http://localhost:3001
```

---

## 🏗️ 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户浏览器                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Nginx 网关 (80/443)                          │
│    /              → React SPA (统一门户)                     │
│    /intent-tester → :5001 (意图测试服务)                     │
│    /new-agents/api→ :5002 (新 Agent 后端 API)                │
│    /new-agents/   → new-agents:80 (新 Agent 前端)            │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│   intent-tester:5001    │     │ new-agents-backend:5002 │
│   Flask + SQLAlchemy    │     │   Flask + OpenAI Proxy  │
│   + SocketIO            │     │   + SSE Streaming       │
└─────────────────────────┘     └─────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL 数据库                          │
└─────────────────────────────────────────────────────────────┘
```

### MidScene 本地代理架构

```
┌──────────────────┐          ┌──────────────────┐
│   云端 Web 系统   │  ◄────►  │  本地 MidScene   │
│  (intent-tester) │  WebSocket│     Server       │
└──────────────────┘          └────────┬─────────┘
                                       │ Playwright
                                       ▼
                              ┌──────────────────┐
                              │   本地浏览器      │
                              └──────────────────┘
```

### 目录结构

```
AI4SE/
├── scripts/
│   ├── dev/deploy-dev.sh      # 本地 Docker 部署脚本
│   ├── ci/                    # CI/CD 脚本
│   ├── health/                # 健康检查脚本
│   └── test/test-local.sh     # 本地测试脚本
├── tools/
│   ├── new-agents/            # [Backend+Frontend] 新 Agent 架构
│   │   ├── backend/           # Flask [5002] LLM 代理，数据库读取 API Key
│   │   │   ├── app.py         # Flask 主程序 (SSE API)
│   │   │   ├── models.py      # LLM 配置模型
│   │   │   └── api/           # REST API
│   │   ├── src/               # React 前端 (Zustand 状态管理)
│   │   └── docker/            # Dockerfile
│   ├── intent-tester/         # [Web + Proxy] 意图测试工具
│   │   ├── backend/           # Flask 后端 + API
│   │   ├── frontend/          # Jinja2 模板 + 静态资源
│   │   ├── browser-automation/# MidScene Server (Node.js)
│   │   └── tests/             # 测试套件
│   ├── frontend/              # [Web] 统一门户前端 (React)
│   │   ├── src/               # 组件与页面
│   │   └── dist/              # 构建产物
│   └── shared/                # [Lib] 共享工具库
│       ├── config/            # 统一配置管理
│       └── database/          # 数据库连接池
├── nginx/nginx.conf           # Nginx 配置
├── docker-compose.dev.yml     # 开发环境编排
├── docker-compose.prod.yml    # 生产环境编排
├── requirements.txt           # Python 依赖
└── .github/workflows/         # GitHub Actions
```

---

## ✨ 核心功能

### 1. AI 智能体 (AI Agents)

基于 **LangGraph** 构建的智能对话系统，支持多轮对话和流式响应。

#### Lisa - 测试专家
- 基于新的 SPA 前端架构，双模式调用 (直连 LLM / 代理模式)
- 测试策略设计与规划
- 需求评审与工作流支持

### 2. 意图测试工具 (Intent Tester)

使用自然语言描述测试意图，AI 自动理解并执行浏览器操作。

**核心组件：**
- **Web 管理界面**: 测试用例 CRUD、执行历史查看
- **本地代理服务器**: 基于 MidSceneJS + Playwright
- **实时通信**: WebSocket 实时状态同步

**工作流程：**
1. 在 Web 界面创建测试用例（自然语言描述）
2. 服务器通过 WebSocket 发送指令到本地代理
3. 本地代理使用 AI 理解意图并控制浏览器
4. 执行结果实时回传到服务器

### 3. 统一门户 (Common Frontend)

基于 **React + Vite + Tailwind CSS** 的现代化前端应用。

**页面结构：**
- 首页 (Hero, Features, UseCases)
- 用户个人中心
- 工具导航入口

---

## 🛠️ 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 主语言 |
| Flask | 2.0+ | Web 框架 |
| LangGraph | 1.0+ | AI 智能体图结构 |
| LangChain | 1.0+ | LLM 集成 |
| SQLAlchemy | 3.0+ | ORM |
| PostgreSQL | 15 | 数据库 |
| Flask-SocketIO | 5.0+ | WebSocket 支持 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19.x | UI 框架 |
| Vite | 7.x | 构建工具 |
| Tailwind CSS | 3.4+ | 样式框架 |
| assistant-ui | 0.11+ | AI 对话组件 |
| Lucide React | 0.56+ | 图标库 |

### 代理服务 (MidScene Server)

| 技术 | 版本 | 用途 |
|------|------|------|
| Node.js | 20+ | 运行时 |
| Playwright | 1.57 | 浏览器自动化 |
| MidSceneJS | 0.30+ | AI 驱动的测试 |
| Express | 4.21+ | HTTP 服务 |
| Socket.IO | 4.7+ | 实时通信 |

### DevOps

| 技术 | 用途 |
|------|------|
| Docker Compose | 容器编排 |
| Nginx | 反向代理 |
| GitHub Actions | CI/CD |
| Pytest | Python 测试 |
| Vitest | 前端测试 |
| Jest | Node.js 测试 |

---

## 📚 API 文档

### AI 智能体 API

**Base URL:** `/new-agents/api`

| 端点 | 方法 | 描述 |
|------|------|------|
| `/chat/stream` | POST | 代理调用 LLM 流式输出 |
| `/config` | GET | 获取基本配置（不暴露 API Key） |

### 意图测试 API

**Base URL:** `/intent-tester/api`

| 端点 | 方法 | 描述 |
|------|------|------|
| `/testcases` | GET | 获取用例列表 |
| `/testcases` | POST | 创建测试用例 |
| `/testcases/<id>` | PUT | 更新测试用例 |
| `/executions/<id>/start` | POST | 启动执行 |
| `/health` | GET | 健康检查 |

详细 API 文档请参阅 [docs/api-contracts.md](docs/api-contracts.md)。

---

## 👨‍💻 开发指南

### 本地开发

#### Python 后端

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动 New Agents Backend 服务
cd tools/new-agents/backend
flask run -p 5002

# 启动 Intent Tester 服务
cd tools/intent-tester
flask run -p 5001
```

#### React 前端

```bash
# 统一门户
cd tools/frontend
npm install
npm run dev  # 开发模式
npm run build  # 生产构建

# New Agents 前端
cd tools/new-agents
npm install
npm run dev
```

### 测试

```bash
# 运行全量本地测试 (与 CI 一致)
./scripts/test/test-local.sh

# Python 测试
cd tools/new-agents/backend && pytest tests/test_api.py -v
cd tools/intent-tester && pytest tests/ -v

# 前端测试
cd tools/new-agents && npm run test

# 代理服务测试
cd tools/intent-tester && npm run test:proxy
```

### 代码规范

- **Python**: 遵循 PEP 8，使用 Black 格式化，Flake8 检查
- **TypeScript/React**: ESLint + Prettier
- **提交信息**: 遵循 Conventional Commits

---

## 🔧 环境变量

创建 `.env` 文件：

```bash
# 数据库配置
DB_USER=ai4se_user
DB_PASSWORD=your_password

# 应用密钥
SECRET_KEY=your-secret-key

# OpenAI API (AI 智能体必需)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# LangSmith 追踪 (可选)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=ai4se
```

---

## 🚢 部署

### 本地 Docker 部署

```bash
# 增量部署 (推荐)
./scripts/dev/deploy-dev.sh

# 全量重建
./scripts/dev/deploy-dev.sh full

# 跳过前端构建
./scripts/dev/deploy-dev.sh --skip-frontend
```

### 生产部署

生产环境通过 GitHub Actions 自动部署：

1. 推送代码到 `master` 分支
2. CI 自动运行测试
3. 测试通过后自动部署到云服务器

**禁止直连云端服务器进行部署操作。**

---

## 📁 文档索引

| 文档 | 描述 |
|------|------|
| [docs/index.md](docs/index.md) | 文档入口 |
| [docs/source-tree-analysis.md](docs/source-tree-analysis.md) | 源码结构分析 |
| [docs/api-contracts.md](docs/api-contracts.md) | API 接口契约 |
| [docs/data-models.md](docs/data-models.md) | 数据模型定义 |
| [docs/component-inventory.md](docs/component-inventory.md) | 前端组件清单 |
| [AGENTS.md](AGENTS.md) | AI 编程智能体指南 |

---

## 🤝 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 开发规范

- 遵循 **TDD 开发模式** (红-绿-重构)
- 所有 PR 必须通过 CI 检查
- 临时文件完成后必须清理
- 中文交流，保持文档同步更新

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。

---

<div align="center">
  <p>Made with ❤️ by the AI4SE Team</p>
</div>
