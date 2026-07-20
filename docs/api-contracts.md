# API 契约文档

> 生成日期: 2026-03-06 | 扫描级别: Deep Scan

## Intent-Tester API (端口 5001)

基础路径: `/intent-tester/api/`（经 Nginx 路由后 Flask 接收 `/api/`）

### 访问与浏览器安全契约

- `restricted`：匿名页面请求重定向到 `/intent-tester/login`，匿名 API 返回 `401/AUTH_REQUIRED`；operator session 才能读取完整用例、写入和执行。
- `public-readonly`：匿名只允许读取用例摘要和代理包/version；详情、写入、执行和本地 proxy ticket 返回 `403/READ_ONLY_MODE`。operator 登录后仍可使用完整能力。
- 所有 session unsafe request 都要求 `Origin` 精确等于 `INTENT_PUBLIC_ORIGIN`，并要求 session CSRF；missing、foreign 和 `null` Origin 都返回 `403/ORIGIN_REJECTED`。唯一 proxy lifecycle route 使用 backend bearer，不使用 session CSRF。
- 所有 routed endpoint 都必须在共享 policy registry 中机械分类；未分类路由使应用在数据库初始化前启动失败。页面通过 response-local nonce CSP 与 `/intent-tester/static/**` 本地资产渲染，不允许 inline handler、远程 CDN 或未编码持久化内容。

### 测试用例 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/testcases` | 获取测试用例列表（支持分页、筛选） |
| POST | `/api/testcases` | 创建测试用例 |
| GET | `/api/testcases/<id>` | 获取单个测试用例详情 |
| PUT | `/api/testcases/<id>` | 更新测试用例 |
| DELETE | `/api/testcases/<id>` | 删除测试用例（软删除） |

#### 测试用例数据结构

```json
{
  "id": 1,
  "name": "登录流程测试",
  "description": "验证用户登录功能",
  "steps": [
    {"action": "goto", "params": {"url": "https://example.com/login"}},
    {"action": "ai_input", "params": {"query": "在用户名输入框输入 test@example.com"}},
    {"action": "ai_tap", "params": {"query": "点击登录按钮"}},
    {"action": "ai_assert", "params": {"assertion": "页面显示欢迎信息"}}
  ],
  "tags": ["login", "smoke"],
  "category": "authentication",
  "priority": 1,
  "is_active": true,
  "execution_count": 5,
  "success_rate": 80.0
}
```

### 执行管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/executions` | 获取执行历史列表 |
| GET | `/api/executions/<id>` | 获取执行详情（含步骤） |
| POST | `/api/executions` | 触发新的测试执行 |
| POST | `/api/executions/<id>/lifecycle` | 接收 Node 的 `started` / `result` lifecycle callback |
| POST | `/api/executions/<id>/reconcile` | Flask 主动读取 Node 同 ID 状态并补偿遗漏的 lifecycle callback |
| POST | `/api/executions/<id>/retry` | 使用同一个 durable execution ID 重新调度 pending/running 执行 |
| POST | `/api/executions/<id>/stop` | 停止正在运行的执行 |
| POST | `/api/executions/<id>/proxy-ticket` | local-host operator 为同一 execution ID 获取 60 秒 HMAC Socket ticket；managed/disabled 时拒绝 |

Flask `ExecutionHistory` 是执行状态权威。`POST /api/executions` 先持久化唯一 `execution_id`，再把该 ID 交给 MidScene Server；Node 不生成第二个执行 ID。lifecycle payload 只接受 `started/running` 或 `result/success|failed|stopped`，时间必须是有效 ISO-8601，terminal step 的 index 必须唯一且状态只允许 `success|failed|skipped|stopped`。重复的相同 callback 是幂等 no-op，非法回退、未知 ID 和终态 retry 显式返回 4xx。页面有界轮询仍未得到 durable 终态时，只调用 Flask `reconcile`；Flask 再读取 Node 的同 ID 状态并按相同状态转移规则补偿。Node 不可用、ID 不匹配或响应非法时显式返回 502，不伪造成功。

#### 执行历史数据结构

```json
{
  "execution_id": "uuid-string",
  "test_case_id": 1,
  "test_case_name": "登录流程测试",
  "status": "success",
  "mode": "headless",
  "browser": "chrome",
  "start_time": "2026-03-06T10:00:00.000Z",
  "end_time": "2026-03-06T10:01:30.000Z",
  "duration": 90,
  "steps_total": 4,
  "steps_passed": 4,
  "steps_failed": 0
}
```

### 已退役的 MidScene 写入口

`POST /api/midscene/execution-start` 与 `POST /api/midscene/execution-result` 不再注册并固定返回 404。Node 只能向 canonical `/api/executions/<id>/lifecycle` 回传，不存在第二条 durable 写路径。

### WebSocket 事件（SocketIO）

| 事件 | 方向 | 说明 |
|------|------|------|
| `execution-start` | Server → Client | 执行开始 |
| `step-start` | Server → Client | 步骤开始 |
| `step-completed` | Server → Client | 步骤完成 |
| `step-failed` | Server → Client | 步骤失败 |
| `execution-completed` | Server → Client | 执行完成 |
| `execution-stopped` | Server → Client | 执行停止 |
| `lifecycle-callback-failed` | MidScene Server → Client | started/result callback 有界重试耗尽；只包含 execution ID、event、固定诊断码和 attempts |
| `screenshot-taken` | Server → Client | 截图完成 |
| `log-message` | Server → Client | 日志消息 |

浏览器 Socket 仅在 `local-host` topology 开放。握手必须同时携带 Flask 颁发的 `auth.ticket` 和相同 `auth.executionId`，Origin、audience、签名和 60 秒有效期全部校验后只加入 `execution:<id>` room。`managed` topology 禁止浏览器 Socket；WebSocket 只触发同 ID 对账，不是 durable 状态权威。

### 其他 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/proxy/download` | 下载 MidScene 代理包 |

---

## MidScene Server API (端口 3001，本地运行)

独立的 Node.js Express 服务，由 Python 后端通过 HTTP 调用。除最小 `/health` 外，所有 HTTP route 都要求 `Authorization: Bearer <INTENT_PROXY_TOKEN>`；token 不进入浏览器、响应或日志。

### AI 浏览器操作

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/goto` | 导航到 URL |
| POST | `/ai-tap` | AI 识别并点击元素 |
| POST | `/ai-input` | AI 识别并输入文本 |
| POST | `/ai-query` | AI 查询页面数据（返回 JSON） |
| POST | `/ai-assert` | AI 断言验证 |
| POST | `/ai-action` | AI 执行复合操作 |
| POST | `/ai-wait-for` | AI 等待条件满足 |
| POST | `/ai-scroll` | AI 滚动页面 |
| POST | `/screenshot` | 截取页面截图 |
| GET | `/page-info` | 获取页面信息 |

### 测试执行管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/execute-testcase` | 执行完整测试用例 |
| GET | `/api/execution-status/:id` | 获取执行状态 |
| GET | `/api/execution-report/:id` | 获取执行报告 |
| GET | `/api/executions` | 获取执行列表 |
| POST | `/api/stop-execution/:id` | 停止执行 |
| POST | `/set-browser-mode` | 设置浏览器模式 (headless/headed) |
| POST | `/cleanup` | 清理浏览器资源 |

`POST /api/execute-testcase` 必须由 Flask 提供非空 `executionId`；响应、内存状态、WebSocket 事件和 lifecycle callback 都复用该 ID。Node 必须从显式 `MAIN_APP_URL` 得到 lifecycle callback 基址，不提供 localhost fallback。`local-host` 只绑定 `127.0.0.1` 并要求 exact loopback HTTP `INTENT_PUBLIC_ORIGIN`；`managed` 在容器网络监听但禁用 browser Socket。每个 started/result callback 最多尝试 3 次；耗尽时只在 canonical execution state 和 `lifecycle-callback-failed` 事件中保留脱敏诊断，不广播上游原始错误。

---

## New Agents Backend API (端口 5002)

基础路径: `/new-agents/api/`（经 Nginx 路由重写为 `/api/`）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/health` | 健康检查 | 无 |
| GET | `/api/config` | 获取默认 LLM 配置和浏览器管理 capability（不含 API Key） | 无 |
| POST | `/api/config` | 创建或更新默认 LLM 配置（不返回 API Key） | `X-API-Key: NEW_AGENTS_CONFIG_ADMIN_API_KEY` |
| POST | `/api/config/check` | 检测默认 LLM 配置或设置表单临时 LLM 配置是否可调用当前模型 | `X-API-Key: NEW_AGENTS_CONFIG_ADMIN_API_KEY` |
| POST | `/api/config/default/check` | 只检测服务端已保存的默认模型，不接受目标覆盖 | 后端代理密钥或受信网关 |
| POST | `/api/agent/runs/stream` | 结构化 Agent Runtime SSE | 后端代理密钥或受信网关 |
| GET | `/api/agent/runs/{runId}` | 获取已持久化 run snapshot | 无 |
| POST | `/api/agent/runs/{runId}/artifacts` | 保存人工校准后的当前阶段 artifact 版本 | 无 |
| PUT | `/api/agent/runs/{runId}/artifact-collaboration` | 替换 run 的 artifact 批注与章节锁协作状态 | 无 |
| GET | `/api/agent/observability` | 获取 Agent Runtime 运行统计 | 无 |
| GET | `/api/agent/workflow-handoff-candidates` | 按目标 workflow/stage 查询可继承的上游产物 | 无 |
| GET | `/api/agent/runs/{runId}/story-handoff-candidates` | 查询 Alex ready story 单故事需求包候选 | 无 |
| GET | `/api/agent/runs/{runId}/story-handoff-packets` | 读取已持久化单故事需求包 | 无 |
| POST | `/api/agent/runs/{runId}/story-handoff-packets` | 从单张 ready story 生成并持久化需求包 | 无 |
| GET | `/api/agent/runs/{runId}/test-assets` | 只读导出 Lisa 测试资产 | 无 |
| POST | `/api/agent/runs/{runId}/test-assets/materialize` | 将 Lisa CASES artifact 实体化为可编辑测试资产集 | 无 |
| GET | `/api/agent/test-assets/{collectionId}` | 读取已实体化测试资产集 | 无 |
| PATCH | `/api/agent/test-assets/{collectionId}/test-cases/{caseId}` | 追加更新单条测试用例版本 | 无 |
| POST | `/api/utils/mermaid/repair` | Mermaid 修复工具 | 后端代理密钥或受信网关 |

`POST /api/config` 和 `POST /api/config/check` 是独立的配置管理能力：固定的 `X-AI4SE-Gateway` 标记和运行时 `PROXY_API_KEY` 都不能替代 `NEW_AGENTS_CONFIG_ADMIN_API_KEY`。生产环境缺少管理密钥时必须 fail-closed 并返回 401。三类 `NEW_AGENTS_DEFAULT_LLM_API_KEY`、`NEW_AGENTS_CONFIG_ADMIN_API_KEY`、`PROXY_API_KEY` 必须两两不同，碰撞时服务端和部署校验均 fail-closed。仅明确的 `development`、`local`、`test` 环境可显式设置 `NEW_AGENTS_CONFIG_ADMIN_ALLOW_UNAUTHENTICATED=true`；开发 Compose 默认关闭该开关并只将网关发布到 loopback。

### GET `/api/config` 响应

```json
// 有默认配置时:
{
  "hasDefault": true,
  "baseUrl": "https://api.example.com/v1",
  "model": "gpt-4o",
  "description": "默认配置",
  "browserConfigAdminAvailable": false
}

// 无默认配置时:
{
  "hasDefault": false,
  "browserConfigAdminAvailable": false
}
```

### POST `/api/config` 请求

创建或更新后端默认 LLM 配置。默认配置 key 为 `default`；部署环境可通过 `NEW_AGENTS_DEFAULT_LLM_CONFIG_KEY` 选择不同配置 key，从而让不同环境启用不同模型。已有默认配置时，`apiKey` 可省略或留空，表示保留当前密钥；提供新 `apiKey` 时用于密钥轮换。响应永不返回密钥。

请求必须由受控管理客户端在 `X-API-Key` 中携带配置管理密钥；浏览器和公开 Nginx 网关不持有该密钥。

```json
{
  "apiKey": "sk-...",
  "baseUrl": "https://api.example.com/v1",
  "model": "gpt-4o",
  "description": "默认配置"
}
```

### POST `/api/config` 响应

```json
{
  "hasDefault": true,
  "baseUrl": "https://api.example.com/v1",
  "model": "gpt-4o",
  "description": "默认配置"
}
```

### POST `/api/config/check` 响应

无请求体时，使用当前默认 LLM 配置执行一次最小模型调用。缺少默认配置时返回 503。

该端点与配置写入使用相同的独立管理认证，避免请求方替换 `baseUrl` 后诱导服务端转发已保存的模型密钥。

带 JSON 请求体时，检测设置表单中的临时配置，不持久化配置、不回显密钥。请求体复用 `POST /api/config` 字段：`baseUrl`、`model`、`description` 和可选 `apiKey`。如果请求体未提供 `apiKey`，后端复用已保存默认配置的密钥；若没有已保存密钥则返回 400。

供应商不可用、鉴权失败或限流时返回 200 且 `ok: false`，由调用方展示稳定的公开业务状态；供应商原始异常和凭证不会进入响应。

```json
{
  "ok": true,
  "baseUrl": "https://api.example.com/v1",
  "model": "gpt-4o",
  "message": "模型配置可用"
}
```

### POST `/api/config/default/check` 响应

浏览器的连接诊断调用该运行时端点。它只读取服务端已保存的 Base URL、模型和密钥，不接受任何 JSON 目标覆盖；携带请求体时返回 400。它复用运行时代理/网关认证，因此不需要、也不会向浏览器暴露配置管理密钥。

### POST `/api/agent/runs/stream` 请求

```json
{
  "prompt": "用户输入与必要上下文",
  "systemPrompt": "当前智能体和阶段提示词",
  "workflowId": "TEST_DESIGN",
  "stageId": "CLARIFY",
  "runId": "可选，复用已有服务端 run"
}
```

### Agent Runtime SSE 响应格式

```text
data: {"type": "run_started", "runId": "0c6d6d3f-9e0c-4f9b-b0d5-1a8e8c8c8c8c"}

data: {"type": "agent_delta", "output": {"chat": "正在生成右侧产出物。", "artifact_update": {"type": "replace", "markdown": "# 需求分析文档\n\n## 1. 需求事实清单\n| 事实 ID | 需求事实 |\n|---|---|\n| F-001 | 用户需要登录功能 |"}, "artifact_patch": null, "stage_action": null, "warnings": []}}

data: {"type": "agent_delta", "output": {"chat": null, "artifact_update": {"type": "replace", "markdown": "# 需求分析文档\n\n## 1. 需求事实清单\n| 事实 ID | 需求事实 |\n|---|---|\n| F-001 | 用户需要登录功能 |\n\n## 2. 被测系统与边界\n| 类型 | 具体内容 |\n|---|---|\n| 测试范围 | 登录页面和登录 API |"}, "artifact_patch": {"operation": "add_after", "sectionAnchor": "h2:2. 被测系统与边界:1", "afterSectionAnchor": "h2:1. 需求事实清单:1", "replacementMarkdown": "## 2. 被测系统与边界\n| 类型 | 具体内容 |\n|---|---|\n| 测试范围 | 登录页面和登录 API |", "baseContent": "# 需求分析文档\n\n## 1. 需求事实清单\n| 事实 ID | 需求事实 |\n|---|---|\n| F-001 | 用户需要登录功能 |"}, "stage_action": null, "warnings": []}}

data: {"type": "agent_turn", "output": {"chat": "已更新右侧文档，请查看关键风险和待确认问题。", "artifact_update": {"type": "replace", "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n登录功能覆盖 Web 登录页和登录 API。\n\n## 2. 系统交互与核心链路\n用户提交凭证后，认证服务校验用户库并返回会话状态。\n\n## 3. 待澄清与阻断性问题\n- 待确认异常路径的锁定策略和错误提示。\n\n## 4. 隐式需求与非功能性考量\n- 安全与性能需要进入后续测试策略。"}, "stage_action": null, "warnings": []}}

data: [DONE]
```

`runId` 为空时，后端会为本轮创建服务端 run 并通过 `run_started.runId` 返回；后续请求带回同一个 `runId` 时，会复用该 run 并追加消息与产物版本。

`agent_delta` 可以在最终 `agent_turn` 前出现多次，用于左侧 chat 增量和右侧 artifact 正式局部产物增量。`agent_delta.output` 结构为 `AgentTurnDeltaOutput`，字段包括：

- `chat`：可选，承载左侧对话的渐进文本。
- `artifact_update`：可选，结构与最终 `agent_turn.output.artifact_update` 相同。`type="replace"` 时，`markdown` 必须是正式 renderer 生成的完整或局部 Markdown。
- `artifact_patch`：可选，描述本次 `replace.markdown` 相对上一版的局部应用元数据。
- `stage_action`：可选，通常由最终 `agent_turn` 承载；partial delta 不应提前推进阶段。
- `warnings`：可选，承载本次 delta 相关警告。

raw structured output 校验失败且运行时准备开始新的模型尝试时，会在两次 attempt 之间发送：

```text
data: {"type": "agent_retry", "attemptIndex": 2}
```

`attemptIndex` 是从 1 开始的模型尝试序号，`agent_retry` 只允许从 2 开始。它要求客户端清空上一 attempt 的 chat 累计、artifact replace 单调基线和尚未展示的 artifact 缓冲，并让新 attempt 重新遵循 natural-chat-first；上一 attempt 已显示的 UI 可保留到新 attempt 产生新的自然 chat 和合法 artifact。该边界事件不持久化消息或 artifact version、不触发 handoff，也不推进 stage。

`artifact_patch` 的 JSON 字段为 `operation`、`sectionAnchor`、`replacementMarkdown`、可选 `baseContent` 和可选 `afterSectionAnchor`。`operation="add_after"` 表示 `replacementMarkdown` 是一个新增章节，客户端可在 `afterSectionAnchor` 后追加；`operation="replace"` 表示替换 `sectionAnchor` 指向的章节，且不能携带 `afterSectionAnchor`。任何 `artifact_patch` 都必须伴随 `artifact_update.type="replace"`；缺少 `artifact_patch` 不代表流式失败，模型字段一次新增多个标题或依赖多个顶层字段时，客户端应以完整 `replace.markdown` 更新右侧 artifact。

### PUT `/api/agent/runs/{runId}/artifact-collaboration` 请求

替换指定 run 的 Artifact 协作状态，包括批注和章节锁。非空 `comments` / `sectionLocks` 引用的 `stageId` 必须已有持久化 artifact version；缺失 run 返回 404，缺失目标 artifact 返回 400，数据库保存异常返回 500 且响应 `{ "error": "协作状态保存失败" }`。

```json
{
  "comments": [
    {
      "id": "comment-1",
      "stageId": "CLARIFY",
      "content": "这里需要业务确认登录边界。",
      "artifactExcerpt": "登录边界",
      "anchorText": "登录边界",
      "createdAt": 1710000000000,
      "status": "open",
      "resolvedAt": null,
      "replies": []
    }
  ],
  "sectionLocks": []
}
```

当服务端上下文构建器因为历史过长裁剪了较早对话时，`run_started` 可携带 `warnings:["context_truncated"]`；前端应在左侧对话首帧提示用户本轮模型只看到了最近上下文。这不同于 artifact 输出截断。

`artifact_update.type="replace"` 表示右侧 artifact 被正式 Markdown 文档替换；有必需 artifact contract 的阶段必须使用 `replace` 并包含当前阶段必需标题、字段和可视化契约。`replace.markdown` 只能承载正式产物或经过正式 renderer 生成的局部正式产物，不能承载调试式进度占位，例如 `# 产出物生成中`、字符数、已识别字段名或裸 `artifact_data` 解析状态。同一 attempt 内的多个 `replace` 必须是累计且单调的：已经出现的章节不能消失或改写，只能由后续闭合章节按最终文档顺序补入；前端必须显式拒绝回退 replace。`agent_retry` 开启新的 attempt 后允许从较短的修正版重新累计，但新 attempt 内仍受同一单调规则约束。`artifact_update.type="none"` 仅用于本轮不更新右侧 artifact 的合法场景，不能用来跳过必需产出物阶段。最终 `agent_turn` 仍必须通过完整 workflow artifact contract、持久化和下游消费校验；partial delta 不能替代 final contract。

错误时：
```text
data: {"type": "error", "code": "SCHEMA_VALIDATION_FAILED", "message": "模型连续生成的结构化结果未通过校验。", "diagnostic": {"phase": "structured_output", "workflowId": "TEST_DESIGN", "stageId": "CLARIFY", "fieldPath": "artifact_data.requirement_facts.0.fact", "validator": "string_too_short", "retryable": true, "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。"}}
```

`diagnostic` 为可选字段。存在时只包含可公开诊断信息，用于前端错误卡片和运行统计排查；不得包含 API Key、完整用户输入、完整 prompt 或完整模型输出。`phase` 表示失败发生位置，常见值包括 `structured_output`、`contract_validation`、`request_validation`、`runtime`、`provider`。`fieldPath` 和 `validator` 用于定位结构化字段或供应商错误分类；错误仍然是显式失败，不得持久化为正式 artifact，也不得自动推进阶段。

### GET `/api/agent/runs/{runId}` 响应

```json
{
  "run": {
    "id": "0c6d6d3f-9e0c-4f9b-b0d5-1a8e8c8c8c8c",
    "workflowId": "TEST_DESIGN",
    "agentId": "lisa",
    "currentStageId": "CLARIFY",
    "status": "active",
    "model": "gpt-4o"
  },
  "messages": [
    {
      "role": "user",
      "content": "用户需求",
      "sequenceIndex": 1
    },
    {
      "role": "assistant",
      "content": "已更新右侧需求分析文档。",
      "sequenceIndex": 2
    }
  ],
  "artifacts": [
    {
      "stageId": "CLARIFY",
      "content": "# 需求分析文档\n...",
      "versionNumber": 1
    }
  ],
  "contextSummaries": [
    {
      "sourceType": "artifact",
      "sourceStageId": "CLARIFY",
      "summaryType": "current_artifact",
      "content": "# 需求分析文档\n..."
    }
  ]
}
```

未知 run：

```json
{
  "error": "未知 runId: unknown-run"
}
```

### GET `/api/agent/observability` 响应

返回 Agent Runtime turn metric 的只读统计摘要，支持 `limit` 查询参数限制 `recentTurns` 数量，并支持 `workflowId` 与 `stageId` 聚焦某个工作流/阶段。`stageId` 必须与 `workflowId` 一起使用，未知 workflow 或不匹配 stage 会返回 JSON 错误。统计包含总体、按 workflow/stage、按 provider 和最近 turn 明细；`estimatedTokens` 在 provider 未返回 usage 时按字符估算，raw streaming 返回 usage 时记录所有 retry attempt 的累计 token；`contractRetryCount` 记录本轮实际观察到的模型结构化输出重试次数，成功与失败终态都会保留该计数。

```json
{
  "totals": {
    "turns": 3,
    "failedTurns": 1,
    "successRate": 66.67,
    "avgDurationMs": 1200.0,
    "estimatedTokens": 900
  },
  "byStage": [
    {
      "workflowId": "TEST_DESIGN",
      "stageId": "CLARIFY",
      "turns": 2,
      "failedTurns": 1,
      "successRate": 50.0,
      "avgDurationMs": 1500.0,
      "estimatedTokens": 700,
      "errorCodes": {"SCHEMA_VALIDATION_FAILED": 1}
    }
  ],
  "byProvider": [
    {
      "provider": "api.test.com",
      "turns": 3,
      "failedTurns": 1,
      "successRate": 66.67,
      "avgDurationMs": 1200.0,
      "estimatedTokens": 900,
      "errorCodes": {"SCHEMA_VALIDATION_FAILED": 1}
    }
  ],
  "recentTurns": [
    {
      "id": 11,
      "runId": "0c6d6d3f-9e0c-4f9b-b0d5-1a8e8c8c8c8c",
      "workflowId": "TEST_DESIGN",
      "stageId": "CLARIFY",
      "model": "gpt-4o",
      "provider": "api.test.com",
      "status": "error",
      "errorCode": "SCHEMA_VALIDATION_FAILED",
      "durationMs": 1500,
      "inputChars": 300,
      "outputChars": 600,
      "estimatedTokens": 225,
      "contractRetryCount": 0,
      "diagnostic": {
        "phase": "structured_output",
        "fieldPath": "artifact_data.requirement_facts.0.fact",
        "validator": "string_too_short",
        "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。",
        "retryable": true
      },
      "createdAt": "2026-06-19T10:00:00"
    }
  ]
}
```

`recentTurns[].diagnostic` 为可选对象或 `null`，仅记录脱敏后的失败定位信息。workflow、stage、provider、model 和 error code 已在 turn 顶层字段中提供，因此 diagnostic 内不重复记录完整异常文本。

### GET `/api/agent/runs/{runId}/test-assets` 响应

该端点只读导出 Lisa `TEST_DESIGN/CASES` artifact 中的结构化测试资产；缺少测试用例集或非 `TEST_DESIGN` run 时返回 JSON 错误，不返回空成功。

```json
{
  "runId": "0c6d6d3f-9e0c-4f9b-b0d5-1a8e8c8c8c8c",
  "workflowId": "TEST_DESIGN",
  "sourceStageId": "CASES",
  "sourceArtifactVersion": 1,
  "testCases": [
    {
      "id": "TC-001",
      "title": "用户登录成功",
      "priority": "P0",
      "dimension": "正向功能验证",
      "testPoint": "登录主链路",
      "risk": "R-LOGIN-001",
      "precondition": "用户已注册",
      "steps": "1. 输入账号密码 2. 点击登录",
      "testData": "正确账号密码",
      "expectedResult": "进入工作台"
    }
  ],
  "coverageTrace": [
    {
      "testPoint": "登录主链路",
      "priority": "P0",
      "risk": "R-LOGIN-001",
      "testCases": ["TC-001"],
      "status": "已覆盖"
    }
  ],
  "coverageSummary": {
    "totalTestCases": 1,
    "totalTestPoints": 1,
    "coveredTestPoints": 1,
    "partiallyCoveredTestPoints": 0,
    "uncoveredTestPoints": 0,
    "coverageRate": 100.0,
    "byPriority": [
      {
        "priority": "P0",
        "total": 1,
        "covered": 1,
        "partial": 0,
        "uncovered": 0,
        "coverageRate": 100.0
      }
    ]
  },
  "assetIssues": [],
  "riskMatrix": [
    {
      "risk": "R-LOGIN-001",
      "testCases": ["TC-001"],
      "testPoints": ["登录主链路"],
      "priorities": ["P0"],
      "dimensions": ["正向功能验证"],
      "coverageStatuses": ["已覆盖"]
    }
  ],
  "intentTesterDrafts": [
    {
      "sourceCaseId": "TC-001",
      "name": "TC-001 用户登录成功",
      "description": "来源: New Agents Lisa TEST_DESIGN/CASES\n测试点: 登录主链路\n关联风险: R-LOGIN-001\n前置条件: 用户已注册\n测试数据: 正确账号密码\n预期结果: 进入工作台",
      "category": "正向功能验证",
      "priority": 1,
      "tags": ["lisa", "new-agents", "TC-001", "P0", "R-LOGIN-001"],
      "steps": [
        {
          "action": "ai_assert",
          "params": {"prompt": "验证预期结果：进入工作台"}
        }
      ],
      "draftWarnings": [
        "该草稿由 Lisa Markdown 用例派生，导入 intent-tester 前需要人工校准页面 URL、定位语义和可执行步骤。"
      ]
    }
  ]
}
```

`assetIssues` 为非阻断质量问题列表，例如覆盖追溯引用不存在的用例 ID，或某条测试用例未被任何测试点引用。缺少 `TEST_DESIGN/CASES` artifact 或 Markdown 表格不可解析时仍返回 JSON 错误。
`intentTesterDrafts` 是 intent-tester `/api/testcases` 创建 payload 草稿；后端导出不会自动写入 intent-tester，前端测试资产弹层可由用户手动触发单条或批量草稿导入。

### POST `/api/agent/runs/{runId}/test-assets/materialize` 响应

该端点会读取当前 `TEST_DESIGN/CASES` artifact 并创建或刷新同一 run 的可编辑测试资产集。响应在只读导出结构基础上增加集合 `id`、`testPoints`，并为每条 `testCases[]` 增加当前 `versionNumber` 与历史 `versions`。

```json
{
  "id": 7,
  "runId": "0c6d6d3f-9e0c-4f9b-b0d5-1a8e8c8c8c8c",
  "workflowId": "TEST_DESIGN",
  "sourceStageId": "CASES",
  "sourceArtifactVersion": 2,
  "coverageSummary": {
    "totalTestCases": 1,
    "totalTestPoints": 1,
    "coveredTestPoints": 1,
    "partiallyCoveredTestPoints": 0,
    "uncoveredTestPoints": 0,
    "coverageRate": 100.0,
    "byPriority": []
  },
  "testCases": [
    {
      "id": "TC-001",
      "title": "用户登录成功",
      "priority": "P0",
      "dimension": "正向功能验证",
      "testPoint": "登录主链路",
      "risk": "R-LOGIN-001",
      "precondition": "用户已注册",
      "steps": "1. 输入账号密码",
      "testData": "正确账号密码",
      "expectedResult": "进入工作台",
      "versionNumber": 1,
      "versions": [
        {
          "versionNumber": 1,
          "title": "用户登录成功",
          "priority": "P0",
          "dimension": "正向功能验证",
          "testPoint": "登录主链路",
          "risk": "R-LOGIN-001",
          "precondition": "用户已注册",
          "steps": "1. 输入账号密码",
          "testData": "正确账号密码",
          "expectedResult": "进入工作台"
        }
      ]
    }
  ],
  "testPoints": [
    {
      "testPoint": "登录主链路",
      "priority": "P0",
      "risk": "R-LOGIN-001",
      "testCases": ["TC-001"],
      "status": "已覆盖"
    }
  ],
  "coverageTrace": [],
  "assetIssues": [],
  "riskMatrix": [],
  "intentTesterDrafts": []
}
```

### GET `/api/agent/test-assets/{collectionId}` 响应

返回已实体化测试资产集，结构与 `POST /api/agent/runs/{runId}/test-assets/materialize` 相同。未知集合返回 JSON 错误。

### PATCH `/api/agent/test-assets/{collectionId}/test-cases/{caseId}` 请求与响应

请求体只允许更新测试用例可编辑字段，当前字段包括 `title`、`priority`、`dimension`、`testPoint`、`risk`、`precondition`、`steps`、`testData` 和 `expectedResult`；未知字段或空字符串会返回 JSON 错误。成功后不会覆盖旧版本，而是追加新版本并返回更新后的当前测试用例。

```json
{
  "title": "登录成功后进入首页",
  "priority": "P1"
}
```

```json
{
  "id": "TC-001",
  "title": "登录成功后进入首页",
  "priority": "P1",
  "dimension": "正向功能验证",
  "testPoint": "登录主链路",
  "risk": "R-LOGIN-001",
  "precondition": "用户已注册",
  "steps": "1. 输入账号密码",
  "testData": "正确账号密码",
  "expectedResult": "进入工作台",
  "versionNumber": 2,
  "versions": [
    {
      "versionNumber": 1,
      "title": "用户登录成功",
      "priority": "P0",
      "dimension": "正向功能验证",
      "testPoint": "登录主链路",
      "risk": "R-LOGIN-001",
      "precondition": "用户已注册",
      "steps": "1. 输入账号密码",
      "testData": "正确账号密码",
      "expectedResult": "进入工作台"
    },
    {
      "versionNumber": 2,
      "title": "登录成功后进入首页",
      "priority": "P1",
      "dimension": "正向功能验证",
      "testPoint": "登录主链路",
      "risk": "R-LOGIN-001",
      "precondition": "用户已注册",
      "steps": "1. 输入账号密码",
      "testData": "正确账号密码",
      "expectedResult": "进入工作台"
    }
  ]
}
```

### GET `/api/agent/runs/{runId}/handoffs` 响应

该端点只读返回当前 source run 可用的配置化 workflow handoff。当前覆盖 Alex `IDEA_BRAINSTORM/CONCEPT` 到 `VALUE_DISCOVERY/ELEVATOR`，Alex `VALUE_DISCOVERY/BLUEPRINT` 到 `STORY_BREAKDOWN/INPUT_ANALYSIS`，以及 Alex `STORY_BREAKDOWN/SPRINT_PLAN` 到 Lisa `TEST_DESIGN/CLARIFY` 与 `REQ_REVIEW/REVIEW`。端点不会自动创建目标 run，也不改变 `/api/agent/runs/stream` 主链路。

```json
{
  "runId": "0c6d6d3f-9e0c-4f9b-b0d5-1a8e8c8c8c8c",
  "sourceWorkflowId": "VALUE_DISCOVERY",
  "handoffs": [
    {
      "id": "value-discovery-blueprint-to-story-breakdown",
      "label": "从需求蓝图继续拆用户故事",
      "sourceRunId": "0c6d6d3f-9e0c-4f9b-b0d5-1a8e8c8c8c8c",
      "sourceWorkflowId": "VALUE_DISCOVERY",
      "sourceStageId": "BLUEPRINT",
      "sourceArtifactVersion": 1,
      "sourceArtifactDigest": "sha256:3f4b...",
      "targetWorkflowId": "STORY_BREAKDOWN",
      "targetStageId": "INPUT_ANALYSIS",
      "targetAgentId": "alex",
      "prompt": "请基于以下上游产物继续工作..."
    },
    {
      "id": "value-discovery-blueprint-to-test-design",
      "label": "交给 Lisa 做测试设计",
      "sourceRunId": "0c6d6d3f-9e0c-4f9b-b0d5-1a8e8c8c8c8c",
      "sourceWorkflowId": "VALUE_DISCOVERY",
      "sourceStageId": "BLUEPRINT",
      "sourceArtifactVersion": 1,
      "sourceArtifactDigest": "sha256:3f4b...",
      "targetWorkflowId": "TEST_DESIGN",
      "targetStageId": "CLARIFY",
      "targetAgentId": "lisa",
      "prompt": "请基于以下 Alex 产出的需求蓝图继续工作..."
    }
  ]
}
```

### GET `/api/agent/workflow-handoff-candidates` 响应

该端点只读返回某个目标 workflow/stage 可以继承的上游产物，用于目标工作流空会话启动时展示“开启新话题 / 基于已有内容继续”。当前系统没有用户概念，因此候选只按已持久化 run、workflow、stage 和 artifact 当前版本筛选，不做权限或 owner 过滤。

请求示例：

```text
GET /api/agent/workflow-handoff-candidates?targetWorkflowId=VALUE_DISCOVERY&targetStageId=ELEVATOR
GET /api/agent/workflow-handoff-candidates?targetWorkflowId=STORY_BREAKDOWN&targetStageId=INPUT_ANALYSIS
```

响应示例：

```json
{
  "targetWorkflowId": "VALUE_DISCOVERY",
  "targetStageId": "ELEVATOR",
  "handoffs": [
    {
      "id": "idea-brainstorm-concept-to-value-discovery",
      "label": "从产品概念简报继续梳理需求蓝图",
      "sourceRunId": "idea-run-123",
      "sourceWorkflowId": "IDEA_BRAINSTORM",
      "sourceStageId": "CONCEPT",
      "sourceArtifactVersion": 1,
      "sourceArtifactDigest": "sha256:3f4b...",
      "sourceArtifactSummary": "# 产品概念简报 AI 测试资产管理平台...",
      "targetWorkflowId": "VALUE_DISCOVERY",
      "targetStageId": "ELEVATOR",
      "targetAgentId": "alex",
      "prompt": "请基于以下上游产物继续工作..."
    }
  ]
}
```

未知 `targetWorkflowId` 或与 workflow 不匹配的 `targetStageId` 返回 JSON 400。没有可用上游 artifact 时返回 200 和空 `handoffs` 数组。

### GET `/api/agent/runs/{runId}/story-handoff-candidates` 响应

该端点只用于 Alex `STORY_BREAKDOWN/SPRINT_PLAN` 当前 artifact version。后端读取当前版本持久化的 `artifactData`，用 `StoryBreakdownArtifactData` 重新校验后返回可生成 packet 的 ready stories；不得从 Markdown 反解析故事。

```http
GET /api/agent/runs/{runId}/story-handoff-candidates?stageId=SPRINT_PLAN
```

```json
{
  "runId": "run-user-story",
  "workflowId": "STORY_BREAKDOWN",
  "stageId": "SPRINT_PLAN",
  "sourceArtifactVersion": 1,
  "sourceArtifactDigest": "sha256:...",
  "candidates": [
    {
      "storyId": "US-001",
      "title": "生成澄清问题",
      "requirementIds": ["REQ-001"],
      "userValue": "测试负责人能在设计前发现缺失业务规则",
      "readyReason": "验收标准和业务规则已明确"
    }
  ]
}
```

未知 run 返回 JSON 404；stage 不是 `SPRINT_PLAN`、run workflow 不是 `STORY_BREAKDOWN`、当前 artifact 缺失或缺少结构化 `artifactData` 返回 JSON 400。

### POST `/api/agent/runs/{runId}/story-handoff-packets` 请求与响应

从当前 `SPRINT_PLAN` artifactData 中选中一张 ready story，生成并持久化单故事需求包。packet 只包含需求信息和追溯信息，不包含任务、文件路径、实现计划、测试命令或架构方案。

```json
{
  "stageId": "SPRINT_PLAN",
  "storyId": "US-001"
}
```

响应为已保存的 packet payload：

```json
{
  "sourceRunId": "run-user-story",
  "sourceWorkflowId": "STORY_BREAKDOWN",
  "sourceStageId": "SPRINT_PLAN",
  "sourceArtifactVersion": 1,
  "sourceArtifactDigest": "sha256:...",
  "createdAt": 1710000000000,
  "storyId": "US-001",
  "requirementIds": ["REQ-001"],
  "userStory": "作为测试负责人，我想要输入需求后看到待澄清问题和隐式风险，以便在测试设计前补齐缺失业务规则",
  "acceptanceCriteria": ["输出需求事实清单"],
  "businessRules": ["问题必须标注阻断性、责任方和状态"],
  "nonFunctionalNotes": ["输出内容需要可追溯、可评审"],
  "outOfScope": ["不直接生成用例"],
  "dependencies": ["用户提供需求文本"],
  "openQuestions": ["问题分类口径可在试点中继续校准"]
}
```

未知 story、非 ready story 或 artifactData 校验失败返回 JSON 400，不写入 packet。

### GET `/api/agent/runs/{runId}/story-handoff-packets` 响应

返回当前 run 已保存的单故事需求包，并对比当前 `SPRINT_PLAN` artifact version/digest 标记 stale。

```http
GET /api/agent/runs/{runId}/story-handoff-packets?stageId=SPRINT_PLAN
```

```json
{
  "runId": "run-user-story",
  "workflowId": "STORY_BREAKDOWN",
  "stageId": "SPRINT_PLAN",
  "sourceArtifactVersion": 2,
  "sourceArtifactDigest": "sha256:new",
  "packets": [
    {
      "id": "1",
      "storyId": "US-001",
      "createdAt": 1710000000000,
      "isStale": true,
      "currentSourceArtifactVersion": 2,
      "currentSourceArtifactDigest": "sha256:new",
      "packet": {
        "sourceRunId": "run-user-story",
        "sourceWorkflowId": "STORY_BREAKDOWN",
        "sourceStageId": "SPRINT_PLAN",
        "sourceArtifactVersion": 1,
        "sourceArtifactDigest": "sha256:old",
        "createdAt": 1710000000000,
        "storyId": "US-001",
        "requirementIds": ["REQ-001"],
        "userStory": "作为测试负责人，我想要输入需求后看到待澄清问题和隐式风险，以便在测试设计前补齐缺失业务规则",
        "acceptanceCriteria": ["输出需求事实清单"],
        "businessRules": ["问题必须标注阻断性、责任方和状态"],
        "nonFunctionalNotes": ["输出内容需要可追溯、可评审"],
        "outOfScope": ["不直接生成用例"],
        "dependencies": ["用户提供需求文本"],
        "openQuestions": ["问题分类口径可在试点中继续校准"]
      }
    }
  ]
}
```

### POST `/api/utils/mermaid/repair` 请求

用于 Mermaid 渲染失败后的工具型修复，不属于主 Agent 产出协议路径。

```json
{
  "brokenCode": "graph TD\n  A-->",
  "errorMessage": "Syntax Error",
  "blockIndex": 0
}
```

### Mermaid repair 响应

```json
{
  "repairedCode": "graph TD\n  A-->B"
}
```

错误时：

```json
{
  "error": "brokenCode 不能为空"
}
```

---

## 健康检查端点汇总

| 服务 | 端点 | 预期响应 |
|------|------|----------|
| Nginx 网关 | `http://localhost/health` | 200 OK |
| Intent-Tester | `http://localhost:5001/health` | `{"status": "ok"}` |
| New Agents Backend | `http://localhost:5002/api/health` | `{"status": "ok", "service": "new-agents-backend"}` |
| MidScene Server | `http://localhost:3001/health` | 200 OK |
