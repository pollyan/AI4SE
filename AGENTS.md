# AGENTS.md - AI4SE 代码库指南

> AI 编程智能体在本仓库中操作的综合指南。

## 项目概述

AI4SE 是一个 Python/TypeScript 单体仓库，包含 AI 驱动的软件工程工具：
- **intent-tester**: 意图测试框架，集成 MidSceneJS
- **ai-agents**: 基于 LangGraph 的 AI 助手（Alex: 需求分析师，Lisa: 测试专家）
- **frontend**: 共享的 React 前端（Vite + Tailwind）

## 快速参考

| 组件 | 后端 | 前端 | 端口 |
|------|------|------|------|
| intent-tester | Flask + SQLAlchemy | React | 5001 |
| ai-agents | Flask + LangGraph | React + assistant-ui (AI SDK Data Stream) | 5002 |
| nginx 网关 | - | - | 80/443 |

---

## 核心规则（必须遵守）
### 通用开发行为准则

1. **【强制】TDD 开发模式**
   本项目严格执行测试驱动开发。具体执行协议已定义在 `.opencode/rules/tdd.mdc` 中，请务必遵守该规则文件中的 **Red-Green-Refactor** 流程。

   具体测试策略与分层请参考下文 **[项目测试策略](#项目测试策略)** 章节。

2. **临时文件清理**: 生成的一次性脚本与文档，在修复完成后必须清理删除

3. **自动化验证优先**: 每当完成变更或修复问题后，优先使用浏览器工具（Playwright）验证是否达到预期目标。只有在无法自动验证时才要求用户手动验证

4. **使用 Context7 查询文档**: 每当需要生成代码、安装配置步骤、或查询库/API 文档时，必须使用 Context7 MCP 工具来解析库 ID 并获取最新文档，无需用户显式要求

5. **【重要】中文交流**: 必须始终使用中文与用户交流，包括：
   - 结论与回答
   - 推理过程说明
   - 计划与任务列表
   - 错误信息与建议

### DevOps 实践

- **环境一致性**: 本地环境与云端环境保持一致的部署方式
- **云端部署**: 通过 GitHub Actions 实现，**禁止直连云端服务器部署**
- **本地 Docker**: 使用 `scripts/dev/deploy-dev.sh` 脚本启动和更新，**禁止直接操作 docker 命令**

### 智能体逻辑判断

- **禁止关键词匹配**: 永远不要用关键词的方法来做智能体的逻辑判断
- **语义理解优先**: 必须根据上下文与语义综合判断用户意图
- **使用 LLM 路由**: 意图识别应通过 LLM 进行语义分析，而非正则或关键词

---

## 项目测试策略

本项目采用模块化测试策略，各应用模块独立维护其测试套件。所有 PR 必须通过 CI/CD 流水线的所有检查。

### 1. 公共模块 (Common)

**Common Frontend (`tools/frontend`)**
- **类型**: 静态检查与构建验证
- **目标**: 确保共享 UI 组件库的代码规范和编译正确性。
- **工具**: `ESLint`, `TypeScript Compiler (tsc)`
- **命令**:
  ```bash
  cd tools/frontend
  npm run lint   # 代码风格检查
  npm run build  # 构建验证
  ```

### 2. AI 智能体 (AI Agents)

**前端 (`tools/ai-agents/frontend`)**
- **类型**: 单元与组件测试 (L1)
- **目标**: 验证 React 组件渲染、Hooks 逻辑及工具函数。
- **工具**: `Vitest`
- **路径**: `tools/ai-agents/frontend/tests/`
- **命令**: `cd tools/ai-agents/frontend && npm run test`

**后端 (`tools/ai-agents/backend`)**
- **类型**: 单元与集成测试 (L1/L2)
- **目标**: 验证 LangGraph 节点逻辑、Prompt 构建、API 端点及状态管理。
- **工具**: `pytest`
- **路径**: `tools/ai-agents/backend/tests/`
- **分层**:
  - **Unit**: 独立节点与工具函数 (`@pytest.mark.unit`)
  - **Integration**: 完整工作流与 Service 层 (`@pytest.mark.integration`)
- **命令**: `pytest tools/ai-agents/backend/tests/`

### 3. 意图测试工具 (Intent Tester)

**后端 (`tools/intent-tester`)**
- **类型**: API 与 服务层测试 (L1/L2)
- **目标**: 验证 REST API、数据库交互及核心业务逻辑。
- **工具**: `pytest`
- **路径**: `tools/intent-tester/tests/` (包含 `api/`, `services/`)
- **命令**: `pytest tools/intent-tester/tests/`

**本地代理服务 (`tools/intent-tester/browser-automation`)**
- **类型**: 代理服务测试 (Node.js)
- **目标**: 验证 MidScene 代理服务器的 HTTP/WebSocket 通信与 Mock 功能。
- **工具**: `Jest`
- **路径**: `tools/intent-tester/tests/proxy/`
- **命令**: `cd tools/intent-tester && npm run test:proxy`

### 4. 测试规范与最佳实践

**Pytest (后端)**
- **文件命名**: `test_*.py`
- **Fixtures 模式**:
  ```python
  @pytest.fixture(scope='function')
  def app():
      """为测试创建应用实例"""
      _app = create_app()
      ...
      yield _app
  ```
- **常用标记**:
  - `@pytest.mark.unit` - 单元测试
  - `@pytest.mark.integration` - 集成测试
  - `@pytest.mark.slow` - 慢速测试
  - `@pytest.mark.asyncio` - 异步测试

**持续集成 (CI)**
GitHub Actions 会在每次推送时运行以下工作流：
1. **Python Tests**: 运行 ai-agents 和 intent-tester 的 pytest。
2. **Frontend Tests**: 运行 ai-agents 的 vitest 和 common frontend 的构建验证。
3. **Proxy Tests**: 运行 intent-tester 代理服务的 jest 测试。
4. **Code Quality**: 运行 flake8 检查。

**本地全量测试**
在提交代码前，使用以下脚本运行与 CI 一致的全量测试：
```bash
./scripts/test/test-local.sh
```

---

## 架构与项目结构

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户浏览器                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Nginx 网关 (80/443)                         │
│    /intent-tester/* → :5001    /ai-agents/* → :5002        │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│   intent-tester:5001    │     │    ai-agents:5002       │
│   Flask + SQLAlchemy    │     │   Flask + LangGraph     │
└─────────────────────────┘     └─────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL 数据库                          │
└─────────────────────────────────────────────────────────────┘
```

### MidScene Server 代理

MidScene Server 是**运行在客户端本地**的代理服务器：
- 配合服务器端 Web 系统实现自动化测试
- 驱动客户端浏览器运行测试用例
- 服务器端通过 API 与本地代理通信

```
┌──────────────────┐          ┌──────────────────┐
│   云端 Web 系统   │  ◄────►  │  本地 MidScene   │
│  (intent-tester) │   API    │     Server       │
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
│   └── deploy-dev.sh        # 本地 Docker 部署脚本（必须使用）
├── tools/
│   ├── ai-agents/           # AI 助手（Lisa, Alex）
│   │   ├── backend/
│   │   │   ├── agents/      # LangGraph 实现
│   │   │   │   ├── lisa/    # Lisa 图、节点、提示词
│   │   │   │   ├── alex/    # Alex 图、节点
│   │   │   │   └── shared/  # 共享状态、进度工具
│   │   │   ├── api/         # Flask API 路由
│   │   │   └── tests/
│   │   └── frontend/        # React UI
│   ├── intent-tester/       # 意图测试工具
│   │   ├── backend/
│   │   ├── frontend/
│   │   └── browser-automation/  # MidScene Server 代理
│   ├── frontend/            # 共享前端组件
│   └── shared/              # 共享 Python 工具（通用基类、工具函数）
├── .github/
│   └── workflows/           # GitHub Actions 云端部署
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── pytest.ini
└── requirements.txt
```

### 模块化单体原则
- 核心业务逻辑封装在 `tools/` 下的独立模块中
- 各模块独立开发、独立测试，但共享部署
- 通用工具类放置在 `tools/shared/` 中，避免代码复制

---

## 开发规范

### 代码风格指南

**Python**
- **导入顺序**: 标准库 -> 第三方库 -> 本地导入
- **命名规范**:
  - 类名：`PascalCase`
  - 函数/方法：`snake_case`
  - 常量：`UPPER_SNAKE_CASE`
  - 私有方法：`_单下划线` 前缀
- **类型提示**: 必须为函数参数和返回值添加类型提示

**TypeScript/React**
- **组件模式**:
  ```typescript
  interface Props {
    sessionId: string;
    onComplete?: () => void;
  }

  export function AnalysisResultPanel({ sessionId, onComplete }: Props) {
    const [loading, setLoading] = useState(false);
    // ...
  }
  ```

### Prompt 工程规范

**1. 存储与管理**
- **禁止硬编码**: 禁止在业务逻辑代码（如节点函数、工具类）中直接编写长字符串 Prompt。
- **独立文件**: 所有 Prompt 模板必须提取到专门的 `prompts/` 目录中。
- **文件结构**:
  ```
  agents/lisa/prompts/
  ├── __init__.py
  ├── shared.py          # 共享的基础 Prompt (身份、风格、通用协议)
  ├── artifacts.py       # 产出物模板定义
  ├── workflow_engine.py # 引擎逻辑 (仅包含逻辑，Prompt 引用 shared.py)
  └── workflows/         # 具体工作流的 Prompt
      └── test_design.py
  ```

**2. 命名与格式**
- **常量命名**: 使用全大写蛇形命名法，并以 `_PROMPT` 或 `_TEMPLATE` 结尾。
  - ✅ `PLAN_SYNC_MECHANISM_PROMPT`
  - ✅ `RESPONSE_TEMPLATE`
  - ❌ `plan_prompt`
- **使用 f-string**: 在业务代码中通过 `.format()` 或 f-string 注入动态变量，保持模板的纯粹性。

**3. 复用原则**
- **共享优先**: 通用的机制（如进度同步、产出物格式）应定义在 `shared.py` 或专门的模块中，供多个工作流复用。
- **逻辑分离**: 生成复杂 Prompt 的逻辑（如根据参数拼接字符串）应封装为 Python 函数，而其使用的静态文本模板应作为常量分离存储。

### 错误处理 (Python)

- **使用具体异常**: 禁止使用裸 `except:`
- **明确的错误信息**:
  ```python
  try:
      config = RequirementsAIConfig.get_default_config()
      if not config:
          raise ValueError("未找到 AI 配置")
  except Exception as e:
      logger.error(f"初始化失败: {e}")
      raise
  ```
- **禁止静默失败**: 必须记录日志或重新抛出异常

### 关键模式

**LangGraph 状态机**
```python
graph = StateGraph(LisaState)
graph.add_node("intent_router", lambda s: intent_router_node(s, llm))
graph.add_node("workflow", lambda s: workflow_node(s, llm))
graph.add_edge(START, "intent_router")
graph.add_conditional_edges("intent_router", route_by_intent)
return graph.compile()
```

**Flask API 响应**
```python
return jsonify({
    "code": 200,
    "message": "Success",
    "data": result
})
```

---

## 环境变量

`.env` 文件必需配置：
```
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
DATABASE_URL=postgresql://user:pass@localhost:5432/ai4se
SECRET_KEY=your-secret-key
```
