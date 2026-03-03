# 系统架构设计 (Architecture)

## 项目结构

```text
AI4SE/
├── scripts/
│   ├── dev/deploy-dev.sh      # 本地 Docker 部署
│   ├── test/test-local.sh     # 类 CI 测试运行器
│   ├── health/                # 健康检查脚本
│   └── ci/                    # CI/CD 脚本
├── tools/
│   ├── new-agents/            # 新 Agent (Lisa 纯前端版 + 后端代理)
│   │   ├── src/               # React 前端 (Vite + React + Zustand)
│   │   │   ├── components/    # UI 组件 (ChatPane, ArtifactPane, Header 等)
│   │   │   ├── pages/         # 路由页面 (AgentSelect, WorkflowSelect, Workspace)
│   │   │   ├── llm.ts         # LLM 双模式调用 (直连/代理)
│   │   │   └── store.ts       # Zustand 状态管理
│   │   ├── backend/           # [端口: 5002] Flask LLM 代理
│   │   │   ├── app.py         # Flask 应用 (SSE 流式代理)
│   │   │   ├── models.py      # SQLAlchemy 模型 (LlmConfig)
│   │   │   ├── config.py      # 配置
│   │   │   ├── tests/         # Pytest 测试
│   │   │   └── docker/        # Dockerfile
│   │   └── docker/            # 前端 Dockerfile
│   ├── intent-tester/         # [端口: 5001] Flask + MidScene
│   │   ├── backend/           # Flask API (api/, models/, services/, utils/)
│   │   ├── browser-automation/# Node.js MidScene 代理
│   │   ├── frontend/          # Jinja2 模板 + 静态资源
│   │   └── tests/             # Python + Jest 测试
│   ├── frontend/              # [端口: 80] 统一门户 (Vite + React)
│   └── shared/                # 通用 Python 工具 (配置, 数据库)
├── nginx/                     # 反向代理配置
├── pytest.ini                 # 全局 pytest 配置
├── requirements.txt           # 根 Python 依赖
└── docker-compose.dev.yml     # 开发环境编排
```

## 架构背景

### 模块化单体仓库
- 独立的服务在一个仓库中，通过 `tools/shared` 共享工具
- **共享代码位置**: `tools/shared/` 包含跨工具的实用程序
- **数据库**: `tools/shared/database/` 中的共享 SQLAlchemy 连接池
- **配置**: `tools/shared/config/` 中的统一配置管理

### Docker 服务拓扑

| 服务 | 容器名 | 端口 | 技术栈 | 说明 |
|------|--------|------|--------|------|
| **postgres** | ai4se-db | 5432 | PostgreSQL 15 | 共享数据库 |
| **intent-tester** | ai4se-intent-tester | 5001 | Flask + MidScene | 意图测试工具 |
| **new-agents** | ai4se-new-agents | - | Vite + React (静态) | 新 Agent 前端 |
| **new-agents-backend** | ai4se-new-agents-backend | 5002 | Flask + OpenAI | LLM 代理后端 |
| **nginx** | ai4se-gateway | 80/443 | Nginx | 统一入口反向代理 |

### Nginx 路由规则

| 路径 | 上游 | 说明 |
|------|------|------|
| `/` | 静态文件 | 统一门户 React App |
| `/intent-tester/` | intent-tester:5001 | 意图测试工具 |
| `/new-agents/api/` | new-agents-backend:5002 | 新 Agent 后端 API (含 SSE) |
| `/new-agents/` | new-agents:80 | 新 Agent 前端 |
| `/health` | 直接返回 200 | 健康检查端点 |

### New Agents 架构

**前端 (纯 SPA)**:
- 基于 React + Vite 构建，Zustand 管理状态
- Lisa Agent: 测试专家 (测试设计, 需求评审工作流)
- 支持 **双模式 LLM 调用**:
  - **直连模式**: 用户自行配置 API Key，前端直接调用 LLM API
  - **代理模式**: 使用系统默认配置，通过后端代理转发 (API Key 不暴露给前端)

**后端代理 (LLM Proxy)**:
- Flask 应用，端口 5002
- 从 PostgreSQL `llm_config` 表读取 API Key（手动插入，不通过 API 暴露）
- 提供 SSE 流式转发 `/api/chat/stream`
- 提供配置查询 `/api/config` (不返回 API Key)

### MidScene 代理
本地 Node.js 服务器，通过 Playwright 驱动 Chrome 进行 AI 驱动的浏览器测试

### 数据流
- **intent-tester**: Flask + LangGraph/LangChain → SSE → 前端
- **new-agents 前端**: React + Zustand → OpenAI SDK / 后端代理 SSE → UI 渲染
- **new-agents 后端**: Flask → OpenAI API → SSE 流式响应

## 环境配置

必需的 `.env` 变量:

```bash
# 数据库
DB_USER=ai4se_user
DB_PASSWORD=your_password

# 应用
SECRET_KEY=your-secret-key

# LangSmith (可选, 用于 intent-tester 追踪)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=intent-test-framework
```

**🚨重要架构规则：智能体 LLM 配置来源于数据库**

> **注意**: New Agents 后端的 LLM API Key（包括 `base_url`, `model` 等模型通道配置）**必须保存在 PostgreSQL 的 `llm_config` 表中**，代理服务通过查询该表来发起 LLM 请求，**绝对不通过 `.env` 环境变量或代码硬编码来读取**。
> **目的**：为确保多租户隔离、动态配置切换以及避免应用环境中明文泄露高权限密钥，配置必须持久化在数据库层。若需更改系统默认调用的模型配置，请直接使用 SQL 工具修改 `llm_config` 表的对应记录。

## 部署规则

**本地开发**:
- 所有集成测试使用 `./scripts/dev/deploy-dev.sh`
- 修改需要重新构建才能在容器中生效

**生产环境**:
- **绝不** 直接部署到云服务器
- 推送到 `master` 分支 → GitHub Actions 运行 CI → 测试通过后自动部署
- 所有修改必须在推送前通过 `./scripts/test/test-local.sh`

**CI/CD 管道** (GitHub Actions):
1. **backend-api-test**: Intent Tester + New Agents Backend 测试
2. **common-frontend-test**: 统一门户前端 Lint + Build
3. **code-quality**: Flake8 代码质量检查
4. **proxy-test**: MidScene 代理 Jest 测试
5. **deploy-to-production**: 构建 + Rsync + SSH 部署到腾讯云
