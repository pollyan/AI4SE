# 源码树分析

> 生成日期: 2026-03-06 | 扫描级别: Deep Scan

## 完整目录结构

```text
AI4SE/                                    # 项目根目录 (Monorepo)
├── AGENTS.md                             # AI Agent 工作指引
├── docker-compose.dev.yml                # 开发环境 Docker 编排
├── docker-compose.prod.yml               # 生产环境 Docker 编排
├── pytest.ini                            # 全局 pytest 配置
├── requirements.txt                      # 根级 Python 依赖 ⚠️ 含待清理的废弃依赖
├── .env                                  # 环境变量（不入版本控制）
│
├── nginx/                                # 🔀 Nginx 反向代理
│   ├── nginx.conf                        # 路由规则：/ → frontend, /intent-tester → :5001, /new-agents → :80/:5002
│   └── ssl/                              # SSL 证书
│
├── scripts/                              # 🛠️ 运维脚本
│   ├── dev/
│   │   └── deploy-dev.sh                 # 本地 Docker 部署（增量/全量）
│   ├── test/
│   │   ├── test-local.sh                 # 类 CI 测试运行器（api/proxy/lint/smoke）
│   │   ├── check-architecture.sh         # 架构检查
│   │   └── check-docs.sh                # 文档检查
│   ├── ci/
│   │   ├── deploy.sh                     # 生产部署脚本（含备份回滚）
│   │   └── build-proxy-package.js        # MidScene 代理打包
│   └── health/
│       └── health_check.sh               # 服务健康检查
│
├── tools/                                # 📦 各工具/服务
│   ├── frontend/                         # 🌐 [Part: frontend] 统一门户
│   │   ├── src/
│   │   │   ├── main.tsx                  # ⚡ 入口
│   │   │   ├── App.tsx                   # 路由: / → Home, /profile → Profile
│   │   │   ├── components/               # Navbar, Footer, Layout
│   │   │   └── pages/
│   │   │       ├── Home/                 # Hero, Modules, Video, UseCases, QuickLinks
│   │   │       └── Profile/             # 个人中心
│   │   ├── package.json                  # React 19 + Vite 7 + Tailwind
│   │   └── dist/                         # 构建产物（挂载到 Nginx）
│   │
│   ├── intent-tester/                    # 🧪 [Part: intent-tester] 意图测试工具
│   │   ├── backend/                      # Flask API 层 (端口 5001)
│   │   │   ├── app.py                    # ⚡ Flask 应用工厂
│   │   │   ├── models/
│   │   │   │   └── models.py             # SQLAlchemy 模型: TestCase, ExecutionHistory, StepExecution, ExecutionVariable, RequirementsSession, RequirementsMessage, VariableReference, RequirementsAIConfig
│   │   │   ├── api/                      # Blueprint 路由
│   │   │   │   ├── testcases.py          # 测试用例 CRUD
│   │   │   │   ├── executions.py         # 执行管理
│   │   │   │   ├── midscene.py           # MidScene 集成
│   │   │   │   └── proxy.py              # 代理包下载
│   │   │   ├── services/                 # 业务逻辑层
│   │   │   │   ├── execution_service.py  # 测试执行编排
│   │   │   │   ├── ai_step_executor.py   # AI 步骤执行器
│   │   │   │   ├── variable_resolver_service.py  # 变量解析
│   │   │   │   ├── database_service.py   # 数据库操作
│   │   │   │   └── query_optimizer.py    # 查询优化
│   │   │   ├── utils/                    # 工具类
│   │   │   │   ├── error_handler.py      # 统一错误处理
│   │   │   │   ├── monitoring.py         # 性能监控
│   │   │   │   ├── logging_config.py     # 日志配置
│   │   │   │   ├── common_patterns.py    # 通用模式
│   │   │   │   └── db_optimization.py    # 数据库优化
│   │   │   ├── views.py                  # Jinja2 页面路由
│   │   │   └── extensions.py             # SocketIO 实例
│   │   │
│   │   ├── browser-automation/           # Node.js MidScene 代理
│   │   │   ├── midscene_server.js        # ⚡ Express + Playwright + MidScene AI 操作
│   │   │   └── midscene_python.py        # Python 集成脚本
│   │   │
│   │   ├── frontend/                     # Jinja2 模板 + 静态资源
│   │   │   ├── templates/                # HTML 模板
│   │   │   │   ├── base_layout.html      # 基础布局
│   │   │   │   ├── testcases.html        # 测试用例列表
│   │   │   │   ├── execution.html        # 执行控制台
│   │   │   │   ├── step_editor.html      # 步骤编辑器
│   │   │   │   └── local_proxy.html      # 本地代理
│   │   │   └── static/
│   │   │       ├── js/                   # 前端 JS (core/, services/, components/)
│   │   │       └── css/                  # 样式表
│   │   │
│   │   ├── midscene_framework/           # 本地 Python 框架
│   │   │   ├── config.py                 # 配置
│   │   │   ├── validators.py             # 验证器
│   │   │   ├── data_extractor.py         # 数据提取
│   │   │   ├── retry_handler.py          # 重试处理
│   │   │   └── mock_service.py           # Mock 服务
│   │   │
│   │   ├── tests/                        # 测试
│   │   │   ├── conftest.py               # 共享 fixtures
│   │   │   ├── proxy/                    # MidScene 代理 Jest 测试
│   │   │   └── test_*.py                 # Python API 测试
│   │   │
│   │   ├── docker/
│   │   │   └── Dockerfile                # Python 3.11-slim 镜像
│   │   ├── package.json                  # Node.js 依赖 (MidScene, Playwright, Express)
│   │   └── requirements.txt              # Python 依赖 (Flask, SQLAlchemy, Playwright)
│   │
│   ├── new-agents/                       # 🤖 [Part: new-agents] AI 智能体工作台
│   │   ├── frontend/                     # React SPA
│   │   │   ├── src/
│   │   │   │   ├── main.tsx              # ⚡ 入口
│   │   │   │   ├── App.tsx               # 路由: / → AgentSelect, /workflows/:id, /workspace/:a/:w
│   │   │   │   ├── pages/
│   │   │   │   │   ├── AgentSelect.tsx   # 智能体选择 (Lisa/Alex)
│   │   │   │   │   ├── WorkflowSelect.tsx # 工作流选择
│   │   │   │   │   └── Workspace.tsx     # 主工作台
│   │   │   │   ├── components/
│   │   │   │   │   ├── ChatPane.tsx      # 对话面板
│   │   │   │   │   ├── ArtifactPane.tsx  # 产出物面板
│   │   │   │   │   ├── Header.tsx        # 顶部栏
│   │   │   │   │   ├── SettingsModal.tsx # 设置弹窗
│   │   │   │   │   ├── WorkflowDropdown.tsx # 工作流下拉
│   │   │   │   │   └── Mermaid.tsx       # Mermaid 图表渲染
│   │   │   │   ├── core/
│   │   │   │   │   ├── store.ts          # Zustand 全局状态（含持久化）
│   │   │   │   │   ├── types.ts          # TypeScript 类型定义
│   │   │   │   │   ├── workflows.ts      # 5 个工作流定义
│   │   │   │   │   ├── llm.ts            # LLM 双模式调用
│   │   │   │   │   ├── buildSystemPrompt.ts  # 系统提示词构建
│   │   │   │   │   ├── config/
│   │   │   │   │   │   ├── agents.ts     # 智能体配置 (Alex, Lisa)
│   │   │   │   │   │   └── agentWorkflows.ts # 智能体工作流映射
│   │   │   │   │   ├── prompts/          # 提示词目录
│   │   │   │   │   │   ├── personas/     # 智能体人设 (lisa.ts, alex.ts)
│   │   │   │   │   │   ├── test_design/  # 测试设计 4 阶段
│   │   │   │   │   │   ├── req_review/   # 需求评审 2 阶段
│   │   │   │   │   │   ├── incident_review/  # 故障复盘 3 阶段
│   │   │   │   │   │   ├── idea_brainstorm/  # 创意头脑风暴 4 阶段
│   │   │   │   │   │   └── value_discovery/  # 价值发现 4 阶段
│   │   │   │   │   └── utils/            # 工具 (llmParser, mermaidSanitizer, markdownUtils)
│   │   │   │   └── services/
│   │   │   │       ├── chatService.ts    # 聊天服务 Hook
│   │   │   │       └── mermaidRetryService.ts  # Mermaid 重试
│   │   │   ├── package.json              # React 19 + Vite 6 + Zustand + OpenAI SDK
│   │   │   └── dist/                     # 构建产物
│   │   │
│   │   ├── backend/                      # Flask LLM 代理 (端口 5002)
│   │   │   ├── app.py                    # ⚡ Flask 应用 + SSE 流式代理
│   │   │   ├── models.py                 # LlmConfig 模型
│   │   │   ├── config.py                 # 配置类
│   │   │   ├── requirements.txt          # Flask + OpenAI + SQLAlchemy
│   │   │   ├── tests/
│   │   │   │   └── test_api.py           # API 测试
│   │   │   └── docker/
│   │   │       ├── Dockerfile            # Python 3.11 + Gunicorn
│   │   │       └── gunicorn.conf.py      # Gunicorn 配置
│   │   │
│   │   └── docker/
│   │       ├── Dockerfile                # 多阶段构建（Node → Nginx）仅生产环境
│   │       └── nginx.conf                # 子服务 Nginx 配置
│   │
│   └── shared/                           # 📚 [Part: shared] 共享 Python 工具
│       ├── __init__.py
│       ├── config/
│       │   └── __init__.py               # SharedConfig 配置类
│       ├── database/
│       │   └── __init__.py               # 数据库连接配置
│       └── tests/
│           └── api_client.py             # 测试用 API 客户端
│
├── tests/                                # 根级测试
│   └── e2e/
│       └── scenarios/                    # E2E 测试场景 (lisa-smoke, lisa-artifacts)
│
├── docs/                                 # 📖 项目文档
│   ├── ARCHITECTURE.md                   # 系统架构设计
│   ├── CODING_STANDARDS.md               # 编码规范
│   ├── DESIGN_PRINCIPLES.md              # 设计原则
│   ├── TESTING.md                        # 测试策略
│   ├── plans/                            # 迭代计划
│   │   └── completed/                    # 已完成的计划 (9 篇)
│   └── test_requirements/                # 测试需求文档
│
├── .github/
│   └── workflows/
│       └── deploy.yml                    # CI/CD: 测试 → 构建 → 部署腾讯云
│
├── logs/                                 # 应用日志（运行时生成）
├── assistant-bundles/                    # AI 助手配置包
└── dist/                                 # 全局构建产物
    └── intent-test-proxy/                # MidScene 代理打包产物
```

## 关键目录说明

| 目录 | 用途 | 关键文件 |
|------|------|----------|
| `tools/frontend/src/` | 统一门户 UI | `App.tsx`, `pages/Home/` |
| `tools/intent-tester/backend/` | 意图测试 API 核心 | `app.py`, `api/`, `services/`, `models/` |
| `tools/intent-tester/browser-automation/` | AI 浏览器自动化 | `midscene_server.js` |
| `tools/new-agents/frontend/src/` | AI 智能体工作台 UI 核心 | `core/store.ts`, `core/workflows.ts`, `core/prompts/` |
| `tools/new-agents/backend/` | LLM SSE 代理 | `app.py`, `models.py` |
| `tools/shared/` | 跨服务共享代码 | `config/__init__.py`, `database/__init__.py` |
| `nginx/` | 统一入口路由 | `nginx.conf` |
| `scripts/` | DevOps 自动化 | `dev/deploy-dev.sh`, `test/test-local.sh`, `ci/deploy.sh` |

## 入口文件

| 服务 | 入口 | 端口 |
|------|------|------|
| 统一门户 | `tools/frontend/src/main.tsx` | 80 (via Nginx) |
| 意图测试 Flask | `tools/intent-tester/backend/app.py` | 5001 |
| MidScene 代理 | `tools/intent-tester/browser-automation/midscene_server.js` | 3001 (本地) |
| AI Agent 前端 | `tools/new-agents/frontend/src/main.tsx` | 80 (via Nginx) |
| AI Agent 后端 | `tools/new-agents/backend/app.py` | 5002 |
