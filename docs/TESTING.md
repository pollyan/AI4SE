# 测试策略 (Testing Strategy)

## 测试金字塔

```
        ┌─────────────┐
        │    E2E      │  ← 少量，验证关键用户流程 (Chrome DevTools MCP)
        │  (手动/MCP) │
        ├─────────────┤
        │ Integration │  ← 中等，验证模块协作 (mock 外部服务)
        ├─────────────┤
        │     API     │  ← 较多，验证端点契约 (Flask test_client)
        ├─────────────┤
        │    Unit     │  ← 最多，验证纯逻辑 (无 I/O)
        └─────────────┘
```

## 测试类型与边界定义

| 类型 | 框架 | 测什么 | Mock 范围 |
|------|------|--------|-----------|
| **后端单元** | pytest | 纯函数、Pydantic 模型、工具类 | 无外部依赖 |
| **后端 API** | pytest + Flask test_client | HTTP 端点、请求/响应格式、状态码 | LLM 服务、外部 API |
| **后端集成** | pytest | 多模块协作、状态流转、工作流 | LLM、外部服务 |
| **代理测试** | Jest | MidScene Server API、WebSocket | Playwright 调用 |

## Mock 策略

| 被 Mock 对象 | Mock 方式 | 使用场景 |
|-------------|-----------|----------|
| **LLM 服务** | `unittest.mock.patch` + `FakeLLM` | 所有非 `slow` 标记的测试 |
| **数据库** | SQLite `:memory:` (conftest.py / test fixtures) | 所有需要持久化的测试 |
| **外部 API** | `responses` 库 / `httpx.MockTransport` | API 测试 |
| **OpenAI Client** | `unittest.mock.patch('llm_client.OpenAI')` | new-agents-backend 测试 |

## 测试文件组织

```text
tools/intent-tester/tests/
├── conftest.py              # 共享 fixtures
├── proxy/                   # MidScene API 测试 (Jest)
└── test_*.py                # Python 测试

tools/new-agents/backend/tests/
├── conftest.py              # Flask app / SQLite / 环境隔离 fixtures
├── test_api.py              # 基础 API 端点测试
├── test_agent_*.py          # PydanticAI Agent Runtime 与 typed SSE 端点测试
├── test_*_service.py        # 后端 service 层单元测试
└── test_backend_layering.py # 后端分层架构约束测试
```

## 测试命名规范

| 类型 | 命名模式 | 示例 |
|------|----------|------|
| Python 测试文件 | `test_<模块名>.py` | `test_api.py` |
| Python 测试函数 | `test_<行为>_<条件>` | `test_chat_stream_returns_sse` |
| TypeScript 测试文件 | `<组件名>.test.tsx` | `ArtifactPane.test.tsx` |
| TypeScript 测试用例 | `it('<动作> when <条件>')` | `it('renders error when fetch fails')` |

## 何时写哪种测试

| 场景 | 推荐测试类型 | 理由 |
|------|-------------|------|
| 新增 Pydantic 模型 | `unit` | 验证字段约束，快速反馈 |
| 新增 API 端点 | `api` | 验证契约，mock 下游服务 |
| 新增 React 组件 | component test | 验证渲染和交互 |
| 修复线上 Bug | 先写复现测试 | 防止回归 |
| 重构已有代码 | 确保已有测试通过 | 不新增测试，除非发现覆盖盲区 |

## 场景覆盖率口径与准入标准

这里的“覆盖率”首先指**场景覆盖率**，不是单纯的工具行覆盖率。对于 LLM/Agent 功能，优先看关键不变量是否被机械保护，再看 `pytest-cov` / Vitest coverage 这类辅助指标。

场景覆盖率按以下维度审计：

| 维度 | 必须回答的问题 | 示例 |
|------|----------------|------|
| 正向场景 | 主路径是否能产出正确字段、状态和 UI 写入 | `agent_turn` 成功返回后，左侧只显示 `chat`，右侧更新 `artifact_update.markdown` |
| 异常场景 | 输入缺失、模型输出非法、协议损坏、依赖缺失是否会明确失败 | 缺默认 LLM 配置返回 503；坏 SSE JSON 直接报错 |
| 边界场景 | 空值、最后阶段、非法阶段、无 artifact 更新等边界是否被保护 | 最后阶段不能请求下一阶段；必需 artifact 阶段不能返回 `none` |
| 跨字段不变量 | 多个字段之间是否存在串位风险，并被测试明确约束 | `chat` 禁止承载 Markdown artifact；`NEXT_STAGE` 不直接写入未确认下一阶段产物 |
| 跨层不变量 | 后端契约、SSE、前端解析、状态写入是否在同一规则下协作 | API 测试解析 SSE JSON；前端状态层只消费 `chatResponse` / `newArtifact` |
| 供应商兼容 | 真实模型或供应商特性是否有可选冒烟验证 | DeepSeek V4 禁用 thinking、提高 retries；真实模型 smoke 只显式运行 |

### 当前准入标准

| 区域 | 必跑命令 | 当前要求 |
|------|----------|----------|
| `tools/new-agents/backend` | `cd tools/new-agents/backend && python3 -m pytest -m "not slow" -q` | 常规门禁通过；真实模型冒烟单独运行 |
| `tools/new-agents/backend` 场景覆盖 | 对照本文件 New Agents 职责分层和审计清单逐项确认 | 新增或修改智能体链路时必须补正向/异常/边界/跨层不变量测试 |
| `tools/new-agents/backend` 工具覆盖率 | `cd tools/new-agents/backend && python3 -m pytest -m "not slow" --cov=<关键模块> --cov-report=term-missing -q` | 辅助审计指标；不得替代场景矩阵判断 |
| `tools/new-agents/frontend` | `cd tools/new-agents/frontend && npm test` | 全量通过 |
| `tools/new-agents/frontend` 类型检查 | `cd tools/new-agents/frontend && npm run lint` | 必须通过 |
| 全仓关键 Python 语法检查 | `flake8 --select=E9,F63,F7,F82 .` | 必须通过 |

### 覆盖率解释规则

- **契约层优先**：`agent_contracts.py`、`request_schemas.py`、`sse_schemas.py` 这类边界模型应追求高覆盖率，因为它们承担机械拦截职责。
- **场景矩阵优先于百分比**：如果测试只覆盖 happy path，即使工具行覆盖率很高，也不能认为智能体链路已被保护。
- **编排层看路径覆盖**：`stream_services.py`、`routes.py` 应覆盖成功、请求错误、LLM 错误、契约错误，不追求模拟所有 Flask/供应商细节。
- **前端状态层看行为覆盖**：`chatService.ts`、`agentCore.ts` 必须覆盖左侧消息、右侧 artifact、阶段推进三类状态写入，不能只看组件渲染覆盖。
- **协议错误不能静默跳过**：typed SSE、结构化 JSON、Pydantic 输出一旦损坏，应报错暴露问题，不通过“忽略坏事件继续处理”制造假成功。
- **真实模型不纳入覆盖率门禁**：`test_agent_real_smoke.py` 是供应商兼容冒烟，依赖环境变量和额度，只作为发布前/本地专项验证。
- **前端覆盖率工具链需显式安装**：如果运行 `npm test -- --coverage` 报缺少 `@vitest/coverage-v8`，说明只能确认测试通过，不能声称已有前端覆盖率数据。
- **覆盖率下降必须解释**：如果新增代码导致覆盖率下降，要么补测试，要么在变更说明中明确为什么该代码不适合覆盖率衡量。

## New Agents 测试职责分层

New Agents 的核心风险不是单个函数错误，而是 LLM 输出、后端契约、SSE 传输、前端状态写入之间的职责混用。测试必须覆盖跨字段不变量，不能只验证 happy path。

### 后端契约层：`agent_contracts.py`

职责：定义 AgentTurnOutput 的唯一合法形态，机械拦截模型输出污染。

必须覆盖：
- `chat` 只承载左侧对话的简短说明，禁止包含 Markdown 标题、表格、代码块、Mermaid、完整 artifact 正文或 `<CHART>/<ARTIFACT>/<CHAT>` 旧标签协议。
- `artifact_update.type=replace` 时 `markdown` 必须非空。
- 有必需模板的阶段必须更新 artifact，不能返回 `artifact_update.type=none`。
- 各工作流阶段的必需标题必须完整出现。
- 阶段推进只能指向下一个合法阶段，最后阶段不能请求下一阶段。
- 外部模型偶发把嵌套对象编码成 JSON 字符串时，只接受可解析为对象的 JSON 字符串，拒绝非 JSON 字符串。

典型测试文件：`tools/new-agents/backend/tests/test_agent_contracts.py`

### 后端运行时层：`agent_runtime.py`

职责：把 PydanticAI 输出转成项目契约对象，并在返回前调用工作流契约校验。

必须覆盖：
- PydanticAI 返回 dict 或模型对象时都经过 `AgentTurnOutput` 校验。
- 违反工作流规则的输出会被拒绝，不进入 SSE 层。
- 模型特定配置可测，例如 DeepSeek V4 禁用 thinking、提高结构化输出 retries。

典型测试文件：`tools/new-agents/backend/tests/test_agent_runtime.py`

### 后端服务与 API 层：`stream_services.py` / `routes.py`

职责：只做编排、异常映射和 typed SSE 输出，不承担模型修补。

必须覆盖：
- 成功事件必须是 typed `agent_turn`，且 mock 输出本身要满足当前阶段契约。
- PydanticAI 输出失败必须映射为 typed `error`，不能泄露 HTML 500。
- 注入 runtime 的 system prompt 必须包含 artifact 更新契约和 chat/artifact 分离契约。
- API 测试要解析 SSE JSON，分别断言 `chat` 与 `artifact_update.markdown`，避免用字符串包含掩盖字段混用。

典型测试文件：
- `tools/new-agents/backend/tests/test_stream_services.py`
- `tools/new-agents/backend/tests/test_agent_endpoint.py`

### 前端 LLM 流解析层：`core/llm.ts`

职责：消费 typed SSE，把 `agent_turn.output.chat` 转成左侧渐进文本，把 `artifact_update.markdown` 转成右侧产物更新。

必须覆盖：
- 只调用 `/new-agents/api/agent/runs/stream`，不回退旧 `/chat/stream`。
- 单个 `agent_turn` 的长 chat 会渐进拆分，但最终 chunk 才携带 artifact 更新。
- artifact 中 Mermaid 语法错误时拒绝写入右侧。
- SSE `error` 事件直接抛出用户可见错误。

典型测试文件：`tools/new-agents/frontend/src/core/__tests__/llm.test.ts`

### 前端状态编排层：`chatService.ts` / `agentCore.ts`

职责：决定左侧消息、右侧 artifact、阶段推进状态分别写入哪里。

必须覆盖：
- assistant 消息只写 `chatResponse`，不能把 `newArtifact` 拼进左侧对话。
- `hasArtifactUpdate=true` 时只更新当前阶段 artifact。
- `NEXT_STAGE` 只设置待确认推进，不直接写入未确认下一阶段产物。
- 用户确认阶段推进时保存来源阶段 artifact，并载入目标阶段 artifact。

典型测试文件：
- `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`
- `tools/new-agents/frontend/src/core/__tests__/agentCore.test.ts`

### 真实模型冒烟层：`test_agent_real_smoke.py`

职责：少量验证真实模型与 PydanticAI/供应商兼容性，不替代确定性单元测试。

必须覆盖：
- 真实模型能返回合法 `AgentTurnOutput`。
- `artifact_update.markdown` 包含阶段必需标题。
- `chat` 不包含 artifact Markdown 结构。
- 仅在显式提供 `NEW_AGENTS_SMOKE_*` 环境变量时运行，避免普通测试依赖外部网络和额度。

## New Agents 策略符合性审计清单

当智能体链路发生重构、模型供应商切换、输出协议变更或 UI 左右栏行为变化时，必须逐项审计：

| 审计项 | 通过标准 | 主要测试文件 |
|--------|----------|--------------|
| 字段职责分离 | `chat` 不承载 artifact；`artifact_update.markdown` 承载完整 Markdown | `test_agent_contracts.py`, `chatService.test.ts` |
| 阶段产物完整性 | 有模板的阶段必须 `replace` 并包含必需标题 | `test_agent_contracts.py` |
| 阶段推进安全 | 只能请求合法下一阶段；前端只设置待确认推进 | `test_agent_contracts.py`, `agentCore.test.ts`, `chatService.test.ts` |
| SSE 契约稳定 | 成功/错误事件都是 typed SSE；API 测试解析 JSON 字段 | `test_stream_services.py`, `test_agent_endpoint.py`, `test_sse_encoder.py` |
| 供应商兼容性 | DeepSeek/OpenAI 等模型特定设置有单测；真实冒烟可选运行 | `test_agent_runtime.py`, `test_agent_real_smoke.py` |
| 前端写入边界 | assistant message 只来自 `chatResponse`；artifact 只来自 `newArtifact` | `llm.test.ts`, `chatService.test.ts`, `agentCore.test.ts` |
| 旧协议清理 | 前端不再调用旧 `/api/chat/stream`，不保留 `<CHAT>/<ARTIFACT>` 协议 | `testHygiene.test.ts` |

## New Agents 浏览器工作流测试

New Agents 另有一套独立于 intent-tester/MidScene 的浏览器级工作流测试，位于 `tests/e2e/new_agents_browser/`。它使用 Python Playwright 打开真实 React 前端，通过 mock typed SSE 响应验证 Lisa `test-design` 和 Alex `value-discovery` 的完整阶段组织逻辑。

默认确定性运行：

```bash
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q
```

可选 LLM judge 运行：

```bash
NEW_AGENTS_E2E_LLM_JUDGE=1 \
NEW_AGENTS_E2E_JUDGE_API_KEY=<api-key> \
NEW_AGENTS_E2E_JUDGE_BASE_URL=https://api.deepseek.com \
NEW_AGENTS_E2E_JUDGE_MODEL=deepseek-v4-flash \
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q
```

不要把 API key 写入仓库。默认测试不需要模型网络调用。

## 测试标记 (pytest)

```bash
pytest -m unit        # 仅单元测试
pytest -m api         # 仅 API 测试
pytest -m integration # 集成测试
pytest -m "not slow"  # 跳过慢速测试
```
