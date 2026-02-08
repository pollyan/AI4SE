# AI4SE 项目指南 (KSGC.md)

## 项目概述

**AI4SE (AI for Software Engineering)** 是一个模块化的 AI 辅助软件工程平台，采用 Modular Monorepo 架构。项目旨在通过 AI 智能体和自动化工具提升开发效率，包含以下核心模块：

| 模块 | 端口 | 技术栈 | 用途 |
|------|------|--------|------|
| **ai-agents** | 5002 | Flask + LangGraph | AI 智能体 (Lisa - 测试专家, Alex - 需求分析师) |
| **intent-tester** | 5001 | Flask + SQLAlchemy | 意图驱动测试工具 |
| **frontend** | 80/443 | React + Vite | 统一开发门户 |
| **postgres** | 5432 | PostgreSQL 15 | 共享数据库 |

### 核心特性

- **🧠 AI 需求分析**: 与 Alex 协作梳理需求，生成 PRD 文档
- **🧪 AI 测试设计**: 与 Lisa 协作进行测试策略设计和需求评审
- **🎯 意图驱动测试**: 使用自然语言描述测试用例，由 MidScene 自动执行浏览器操作
- **🏠 统一门户**: React 集成所有工具入口

---

## 快速命令速查

### Docker 部署

```bash
# 本地开发环境部署 (推荐)
./scripts/dev/deploy-dev.sh

# 完全重建 (清理缓存)
./scripts/dev/deploy-dev.sh full

# 跳过前端构建
./scripts/dev/deploy-dev.sh --skip-frontend

# 查看服务状态
docker-compose -f docker-compose.dev.yml ps

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f

# 停止服务
docker-compose -f docker-compose.dev.yml down
```

### Python 后端

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest                                    # 所有测试
pytest tools/ai-agents/backend/tests/   # 特定目录测试
pytest -m unit                           # 仅单元测试
pytest -k "workflow_node"                # 按关键字筛选

# 代码质量
flake8 --select=E9,F63,F7,F82 .          # 关键错误检查
flake8 .                                 # 完整 Lint
black .                                  # 格式化代码

# 启动服务 (本地开发)
cd tools/ai-agents && python -m backend.app
cd tools/intent-tester && python -m backend.app
```

### TypeScript/React 前端

```bash
# 统一门户
cd tools/frontend
npm install
npm run dev              # 开发模式
npm run build            # 生产构建
npm run test             # 运行测试
npm run lint             # Lint 检查

# AI Agents 前端
cd tools/ai-agents/frontend
npm install
npm run dev
npm run build
```

### Node.js 代理 (MidScene)

```bash
cd tools/intent-tester
npm install
npm start                # 启动代理 (端口 3001)
npm run test:proxy       # 代理测试
```

### 综合测试

```bash
# 运行全量本地测试 (与 CI 一致)
./scripts/test/test-local.sh

# 测试特定部分
./scripts/test/test-local.sh api      # API 测试
./scripts/test/test-local.sh proxy    # 代理测试
./scripts/test/test-local.sh lint    # Lint 检查
```

---

## 项目结构

```
AI4SE/
├── scripts/
│   ├── dev/deploy-dev.sh         # 本部 Docker 部署脚本
│   ├── ci/                       # CI/CD 脚本
│   ├── health/                   # 健康检查脚本
│   └── test/test-local.sh        # 本地测试脚本
├── tools/
│   ├── ai-agents/                # AI 智能体服务 (端口: 5002)
│   │   ├── backend/
│   │   │   ├── agents/           # 智能体核心逻辑
│   │   │   │   ├── lisa/         # Lisa (测试专家)
│   │   │   │   ├── alex/         # Alex (需求分析师)
│   │   │   │   └── shared/       # 共享状态、检查点、工具
│   │   │   ├── api/              # REST API 端点
│   │   │   └── models/           # SQLAlchemy 模型
│   │   ├── frontend/             # React UI (assistant-ui)
│   │   └── docker/               # Dockerfile
│   ├── intent-tester/            # 意图测试工具 (端口: 5001)
│   │   ├── backend/              # Flask 后端
│   │   ├── frontend/             # Jinja2 模板 + 静态资源
│   │   ├── browser-automation/   # MidScene Server (Node.js)
│   │   └── tests/                # 测试套件
│   ├── frontend/                 # 统一门户前端 (React)
│   │   ├── src/                  # 组件与页面
│   │   └── dist/                 # 构建产物
│   └── shared/                   # 共享 Python 工具库
│       ├── config/               # 统一配置管理
│       └── database/             # 数据库连接池
├── nginx/
│   └── nginx.conf                # Nginx 反向代理配置
├── requirements.txt              # Python 依赖
├── pytest.ini                    # Pytest 配置
├── docker-compose.dev.yml        # 开发环境编排
└── AGENTS.md                     # AI 编程智能体指南
```

---

## 核心架构

### 模块化单体仓库

- 所有服务代码在同一个仓库中
- 每个工具保持独立部署和运行的能力
- 通过 `tools/shared` 共享 Python 工具库

### 微服务通信流向

```
用户浏览器
    ↓
Nginx (80/443)
    ├── / → tools/frontend (React SPA)
    ├── /intent-tester → intent-tester:5001 (Flask)
    ├── /ai-agents → ai-agents:5002 (Flask)
    └── /static → Nginx 静态文件
```

### MidScene 本地代理架构

```
意图测试后端 (intent-tester:5001)
    ↓ WebSocket
本地 MidScene Server (:3001)
    ↓ Playwright
浏览器自动化执行
    ↓ 实时截图
返回执行结果
```

### AI Agents 架构

- 基于 **LangGraph StateGraph** 构建状态机
- 支持多轮对话和 SSE 流式响应
- 使用 Checkpointer 实现会话持久化

---

## 开发规范

### Python 代码规范

| 方面 | 规则 |
|------|------|
| **风格** | PEP 8, Black 格式化器 |
| **类型** | 强制所有参数/返回值使用类型提示: `def func(x: int) -> str:` |
| **命名** | `snake_case` (变量/函数), `PascalCase` (类), `UPPER_SNAKE` (常量) |
| **导入** | 标准库 → 第三方 → 本地。使用从包根目录的绝对导入 |
| **错误处理** | 仅捕获特定异常，避免裸露的 `except Exception:` |
| **提示词** | 存储在 `prompts/` 目录中，逻辑文件中不硬编码 |
| **数据模型** | 使用 Pydantic `BaseModel` + `Field` 验证器 |

**导入示例:**
```python
from typing import Dict, Optional
from langchain_core.messages import AIMessage  # 第三方
from backend.agents.lisa.state import LisaState  # 本地绝对路径
from ..shared.checkpointer import get_checkpointer  # 本地相对路径
```

### TypeScript/React 规范

| 方面 | 规则 |
|------|------|
| **风格** | ESLint + TypeScript 严格模式 |
| **组件** | 仅使用 Hooks 的函数式组件 |
| **文件命名** | `PascalCase.tsx` (组件), `camelCase.ts` (工具) |
| **状态** | React Context / React Query > 全局 Store |
| **测试** | Vitest + React Testing Library |
| **样式** | Tailwind CSS 工具类 |

### TDD 开发协议

遵循**红-绿-重构**循环：

1. **红**: 编写一个失败的测试
2. **绿**: 编写最少量的代码使测试通过
3. **重构**: 在保持测试通过的同时清理代码

**绝不要**在没有测试的情况下编写实现代码。

---

## AI Agents 架构策略

### Artifact 格式分离原则

**核心原则**: Artifact 的格式约束应在 **数据模型 + 渲染逻辑** 中定义，而非在提示词中硬编码。

| 层级 | 职责 | 文件位置 |
|------|------|----------|
| **数据模型** | 定义字段、类型、枚举值 | `artifact_models.py` |
| **渲染逻辑** | 将结构化数据转为 Markdown | `utils/markdown_generator.py` |
| **提示词** | 告诉 LLM **做什么**，而非**格式细节** | `prompts/*.py` |

**设计优势**:
1. **SSOT**: 格式定义只在一处，避免提示词与代码脱节
2. **可维护性**: 修改格式只需改模型/渲染器
3. **一致性**: LLM 通过工具 Schema 约束输出，比自然语言描述更可靠

---

## 测试

### Pytest 标记

```bash
pytest -m unit         # 仅单元测试
pytest -m api          # 仅 API 测试
pytest -m integration  # 集成测试
pytest -m slow         # 慢速测试
pytest -m "not slow"   # 跳过慢速测试
```

### 测试配置

测试配置位于 `pytest.ini`，包含:
- 测试路径: `tests`
- Python 文件模式: `test_*.py`
- 测试类模式: `Test*`
- 测试函数模式: `test_*`
- 最小 Python 版本: 3.11

---

## 环境变量

创建 `.env` 文件 (可从 `.env.example` 复制):

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

## 常见任务

### 启动本地开发环境

```bash
# 1. 检查环境变量
cp .env.example .env
vim .env  # 编辑配置

# 2. 部署
./scripts/dev/deploy-dev.sh

# 3. 访问
# 主页: http://localhost
# AI 智能体: http://localhost/ai-agents
# 意图测试: http://localhost/intent-tester
```

### 启动 MidScene 本地代理

```bash
cd tools/intent-tester
npm install
npm start  # 运行在 http://localhost:3001
```

### 运行健康检查

```bash
bash scripts/health/health_check.sh local
```

---

## 禁止模式

| 类别 | 绝不 |
|------|------|
| **类型安全** | `as any`, `@ts-ignore`, `@ts-expect-error` |
| **错误处理** | 空 catch 块, 裸露的 `except Exception:` |
| **测试** | 删除失败的测试以"通过", 跳过 TDD |
| **提交** | 未经明确用户请求即提交 |
| **Docker** | 直接运行 `docker` 命令 (使用脚本) |

---

## 验证清单

在声称工作完成前，确保:

- [ ] LSP 诊断清零 (`lsp_diagnostics`)
- [ ] 所有测试通过 (`pytest` / `npm run test`)
- [ ] 构建通过 (前端 `npm run build`)
- [ ] 没有新的 lint 错误 (`flake8` / `npm run lint`)
- [ ] 临时文件已清理

---

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 主语言 |
| Flask | 2.0+ | Web 框架 |
| LangGraph | 0.2+ | AI 智能体图结构 |
| LangChain | 0.3+ | LLM 集成 |
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

### 代理服务

| 技术 | 版本 | 用途 |
|------|------|------|
| Node.js | 20+ | 运行时 |
| Playwright | 1.56+ | 浏览器自动化 |
| MidSceneJS | 0.30+ | AI 驱动的测试 |
| Express | 4.21+ | HTTP 服务 |
| Socket.IO | 4.7+ | 实时通信 |

---

## 关键文件说明

| 文件 | 说明 |
|------|------|
| `requirements.txt` | Python 依赖根文件 |
| `pytest.ini` | Pytest 全局配置 |
| `docker-compose.dev.yml` | 开发环境 Docker 编排 |
| `AGENTS.md` | AI 编程智能体详细指南 |
| `scripts/dev/deploy-dev.sh` | 本部部署脚本 |
| `scripts/test/test-local.sh` | 本地测试运行器 |

---

## 参考资源

-完整文档参考 [README.md](README.md)
- AI Agent 详细指南参考 [AGENTS.md](AGENTS.md)
- API 文档参考 [docs/api-contracts.md](docs/api-contracts.md)
