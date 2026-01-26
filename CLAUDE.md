# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

## 语言要求

**重要**: 在与用户交流时,请始终使用**中文**回复。代码、命令、技术术语可以保持英文,但所有解释、说明和对话必须用中文。

## 项目概述

**AI4SE** 是一个模块化单体仓库(Monorepo),用于构建 AI 驱动的软件工程工具,使用 Python/TypeScript 开发。项目在**本地 Docker 容器**中运行,用于开发和测试。

### 核心组件

- **ai-agents** (端口 5002): 基于 Flask + LangGraph + Vercel AI SDK 构建的 AI 助手 (Lisa)
- **intent-tester** (端口 5001): 使用 MidSceneJS + Playwright 的自然语言测试自动化工具
- **frontend**: 基于 React + Vite + Tailwind 的共享主页和门户

## 必备命令

### 开发与部署

**关键**: 源代码修改不会自动反映到运行中的应用程序。必须部署到 Docker:

```bash
# 部署所有服务到本地 Docker (增量模式)
./scripts/dev/deploy-dev.sh

# 完全重建 (清除缓存)
./scripts/dev/deploy-dev.sh full

# 跳过前端构建 (仅后端)
./scripts/dev/deploy-dev.sh --skip-frontend

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f

# 停止服务
docker-compose -f docker-compose.dev.yml down
```

### 测试

```bash
# 运行所有测试 (与 CI 流程一致)
./scripts/test/test-local.sh

# 运行特定测试套件
./scripts/test/test-local.sh api      # Python 后端测试
./scripts/test/test-local.sh proxy    # MidScene 代理测试
./scripts/test/test-local.sh lint     # 代码质量检查

# 直接运行 Python 测试
pytest tools/intent-tester/tests/ -v
pytest tools/ai-agents/backend/tests/ -v

# 运行单个测试文件
pytest tools/ai-agents/backend/tests/test_specific.py -v

# 前端测试
cd tools/ai-agents/frontend && npm run test        # 使用 Vitest 运行
cd tools/ai-agents/frontend && npm run test -- --run  # CI 模式 (不监听)

# 代理测试
cd tools/intent-tester && npm run test:proxy
```

### 构建前端组件

```bash
# AI Agents 前端
cd tools/ai-agents/frontend
npm install
npm run build    # 构建到 dist/
npm run dev      # 开发模式 (不用于 Docker 测试)

# 公共前端 (主页/个人中心)
cd tools/frontend
npm install
npm run build    # TypeScript 编译 + Vite 构建
npm run lint     # ESLint 检查

# Intent Tester 代理
cd tools/intent-tester
npm install
npm start        # 本地启动 MidScene 服务器
```

### Python 环境

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 设置 PYTHONPATH 用于本地测试
export PYTHONPATH=$PWD:$PWD/tools/intent-tester:$PWD/tools/ai-agents:$PYTHONPATH
```

## 架构深入解析

### Docker 优先的开发模式

**关键规则**: 开发环境在 Docker 容器中运行。永远不要假设本地文件修改会立即生效。

- **集成测试**: 测试前必须使用 `./scripts/dev/deploy-dev.sh` 部署
- **本地开发服务器**: 在宿主机上运行 `npm run dev` 或 `flask run` 仅用于隔离开发
- **构建产物**: 前端构建在部署期间被复制到 Docker 镜像中

### LangGraph Agent 架构

**Lisa Agent** 使用双节点架构,基于工具的产出物更新:

```
START → intent_router → reasoning_node → artifact_node → END
                     ↓
                  clarify_intent → END
```

**产出物更新流程** (强制要求):
1. `reasoning_node` 设置 `should_update_artifact=True`
2. 通过 Command 路由到 `artifact_node`
3. `artifact_node` 调用 `update_artifact` 工具
4. 前端接收 `tool-call` 事件进行追踪

**禁止**直接在节点中修改 `state["artifacts"]` - 必须使用工具以确保前端可观测性。

### 数据流与流式传输

- **后端**: Flask + LangGraph 通过服务器发送事件 (SSE) 流式传输响应
- **前端**: Vercel AI SDK (`useChat` hook) 消费流
- **协议**: Vercel AI SDK Data Stream Protocol
- **迁移说明**: 之前使用 `@assistant-ui/react`,现已迁移到 Vercel AI SDK

### 共享代码模式

- **位置**: `tools/shared/` 包含跨工具的实用程序
- **数据库**: `tools/shared/database/` 中的共享 SQLAlchemy 连接池
- **配置**: `tools/shared/config/` 中的统一配置管理

## 代码质量标准

### 死代码清理

重构或替换库时:
- **验证零引用**: `grep -r "ComponentName" tools/`
- **立即删除**: 删除未使用的文件,不要注释掉
- **清理测试**: 删除相关测试文件以防止 CI 失败

### 特性废弃协议

移除特性时(例如整个 agent):
1. 删除 Pydantic schemas/models
2. 更新服务级 docstrings 以移除提及
3. 删除特性专属的测试文件
4. 搜索特性名称的所有变体: `grep -ri "feature_name" tools/`

### 单一事实来源 (SSOT)

**反模式**: 在前端常量中复制后端 prompt 逻辑

风险示例: 前端 `LISA_SUGGESTIONS` 硬编码以匹配后端 prompt 选项
- **当前**: 在 MVP 阶段记录这种重复
- **未来**: 通过 API 端点暴露配置

### Prompt 维护

当工作流机制改变时(例如 JSON-in-Markdown → Tool Calls):
- **立即移除过时的 prompt 辅助函数**: 不要"以防万一"保留
- **风险**: 废弃的 prompts 会产生矛盾的 LLM 指令
- **行动**: 删除函数定义、文件和所有模板引用

## 测试指南

### Python 测试

- **框架**: pytest 带异步支持 (`--asyncio-mode=auto`)
- **覆盖率**: 使用 `--cov=tools/component/backend` 生成覆盖率报告
- **标记**: `@pytest.mark.unit`, `@pytest.mark.api`, `@pytest.mark.integration`

### 前端测试

- **框架**: Vitest (AI Agents), ESLint + 构建验证 (公共前端)
- **Mock**: 当库 API 改变时更新 mocks
  ```typescript
  // 示例: 迁移后 mock react-markdown
  vi.mock('react-markdown', () => ({
    default: ({ children }: any) => <div data-testid="markdown">{children}</div>
  }));
  ```

### MidScene 代理测试

- **框架**: Jest
- **运行**: 在 `tools/intent-tester/` 中执行 `npm run test:proxy`
- **CI 模式**: `npm run test:proxy:ci` 包含覆盖率

## 环境配置

必需的 `.env` 变量:

```bash
# 数据库
DB_USER=ai4se_user
DB_PASSWORD=your_password

# 应用
SECRET_KEY=your-secret-key

# OpenAI (AI agents 必需)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# LangSmith (可选)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=ai4se
```

## 核心目录结构

```
AI4SE/
├── tools/
│   ├── ai-agents/
│   │   ├── backend/
│   │   │   ├── agents/lisa/      # LangGraph 节点、状态、工具
│   │   │   │   ├── graph.py      # StateGraph 定义
│   │   │   │   ├── nodes.py      # 图节点
│   │   │   │   └── tools.py      # update_artifact 工具
│   │   │   ├── api/              # Flask 路由
│   │   │   └── models/           # SQLAlchemy 模型
│   │   └── frontend/             # React + Vercel AI SDK
│   ├── intent-tester/
│   │   ├── backend/              # Flask API
│   │   ├── browser-automation/   # MidSceneJS 服务器
│   │   └── tests/                # Python + Jest 测试
│   ├── frontend/                 # 公共主页/个人中心
│   └── shared/                   # 跨工具实用程序
├── scripts/
│   ├── dev/deploy-dev.sh         # 本地部署
│   └── test/test-local.sh        # 测试运行器
├── docker-compose.dev.yml
├── pytest.ini
└── requirements.txt
```

## 开发前检查清单

修改前:
- [ ] 我是在 Docker 中运行吗? 如果是,我部署了吗 (`./scripts/dev/deploy-dev.sh`)?
- [ ] 导入的库是否真的存在于 `package.json`/`requirements.txt` 中?
- [ ] 我是否在前端和后端之间重复了逻辑 (违反 SSOT)?

实施后:
- [ ] 我删除了未使用的文件 (死代码) 吗?
- [ ] 如果移除了特性,我更新了所有相关的 docstrings 和 schemas 吗?
- [ ] 我更新了测试以匹配 API 变更 (props, imports, mocks) 吗?
- [ ] 我验证了测试通过 (`./scripts/test/test-local.sh`) 吗?

## 部署规则

**本地开发**:
- 所有集成测试使用 `./scripts/dev/deploy-dev.sh`
- 修改需要重新构建才能在容器中生效

**生产环境**:
- **绝不**直接部署到云服务器
- 推送到 `master` 分支 → GitHub Actions 运行 CI → 测试通过后自动部署
- 所有修改必须在推送前通过 `./scripts/test/test-local.sh`
