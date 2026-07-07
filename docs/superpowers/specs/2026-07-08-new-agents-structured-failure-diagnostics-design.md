# New Agents 结构化失败诊断透明化设计

- 日期：2026-07-08
- 状态：目标模式第 1 轮设计
- 来源：`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- 本轮用户故事：当结构化产出生成失败时，用户可以看到具体、可操作的失败诊断，并确认右侧产物没有被错误覆盖；工程侧可以在运行统计中追踪同一失败类别。

## Current State Gap Analysis 摘要

本轮已读取 `AGENTS.md`、目标模式 playbook、CGA 模板、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、当前 `docs/todos/` 和 New Agents 错误链路代码。

当前真正未处理的 P0 待办是两条：

- 结构化产出失败治理：状态为待执行。
- Alex 需求蓝图到用户故事 handoff：状态为待启动。

Partial artifact streaming 纵切路线和策略图表 schema 强化均已记录为完成，不进入本轮实现。

排序结论：先做结构化失败诊断透明化。原因是它直接处理用户看到黄色失败框但不知道原因的问题，也会降低后续 Alex 新工作流和 handoff 链路的排错成本。

## Superpowers Brainstorming 自问自答

### Explore Project Context

New Agents 当前通过共享 `/api/agent/runs/stream` typed SSE 主链路生成所有 Agent 输出。后端 `stream_services.py` 已能把 `ContractValidationError`、Pydantic `ValidationError`、`AgentRuntimeSchemaError`、供应商错误等映射为 `ErrorEvent(code, message)`，并通过 `agent_run_turn_metrics` 记录 `error_code`、耗时、provider、stage 和 retry count。

前端 `core/llm.ts` 解析 SSE `error` 后抛出 `code: message` 文本，`chatService.ts` 再用字符串匹配判断是 structured/provider/generic 错误，`ChatPane.tsx` 显示基础诊断卡。这个链路能显式失败，但诊断维度不足：没有 `phase`、`fieldPath`、`validator`、`publicReason`、`retryable`，运行统计也无法保留这些信息。

当前数据库初始化使用 `db.create_all()` 加少量启动时补列函数，没有 Alembic 迁移体系。本轮如果扩展 metric 字段，应沿用现有轻量补列模式，并保持已有表数据兼容。

### Visual Companion Decision

本轮不是视觉设计问题。现有 ChatPane 已有诊断卡样式，目标是把后端 typed 诊断数据接进去，而不是重新设计 UI 布局，因此不使用 visual companion。

### Clarifying Questions

1. 用户真正要解决什么？
   用户不希望黄色失败框只告诉“生成失败”，而是要知道失败发生在哪个工作流、哪个阶段、哪个字段或校验规则，以及应该重试、补充信息还是检查模型配置。

2. 是否允许 fallback 草稿？
   不允许。结构化校验失败仍必须显式失败，不持久化正式 artifact，不推进 stage，不用旧 artifact 或草稿冒充成功。

3. 是否要记录完整模型输出？
   不记录。本轮只记录脱敏诊断字段，不记录 API key、完整用户输入、完整模型输出或完整 prompt。

4. 是否要一次修复所有 schema 失败根因？
   不在本轮。第 1 轮只把失败透明化；后续轮次再做可计算字段后端化、ID 关系收敛和高失败阶段纵切修复。

5. 是否要破坏现有 SSE error 兼容性？
   不破坏。`code` 和 `message` 继续存在，新增 `diagnostic` 为可选对象。旧前端仍能读取 `code/message`。

6. 是否要引入 Lisa 或 Alex 专属错误链路？
   不引入。所有 workflow 继续共享 Agent Runtime、SSE schema、persistence、frontend parser 和 ChatPane。

### Approaches

推荐方案：在 SSE `error` 事件中增加可选 `diagnostic` 对象，并把同一诊断字段写入 `agent_run_turn_metrics`。

- 优点：一次覆盖用户当次失败和工程后续排查；保持 `code/message` 兼容；符合当前共享 runtime 架构。
- 缺点：需要同时改后端 schema、stream service、persistence、observability、前端 parser 和 UI 测试。

备选方案 A：只在前端继续解析错误字符串。

- 优点：改动小。
- 缺点：无法可靠拿到 field path 和 validator；后端观测仍不可追踪；会继续扩大字符串匹配债务。

备选方案 B：先修复高失败阶段 schema。

- 优点：可以直接降低某些阶段失败率。
- 缺点：没有先建立诊断闭环，后续每个阶段都难以证明失败根因；不符合 todo 第 1 轮顺序。

结论：采用推荐方案。

## 设计目标

本轮完成后：

- SSE `error` 事件仍显式失败，并增加可选 `diagnostic`。
- 结构化失败诊断至少包含 `phase`、`workflowId`、`stageId`、`fieldPath`、`validator`、`retryable`、`publicReason`。
- 前端错误卡展示阶段、字段路径、校验器、建议动作和原始错误摘要。
- `agent_run_turn_metrics` 记录脱敏诊断字段，`/api/agent/observability` 返回 recent turn 的诊断摘要。
- 右侧 artifact 不因失败被更新，stage 不推进。

## 非目标

- 不降低任何 schema、contract、Mermaid 或 structured visual 校验严格性。
- 不生成 fallback 草稿、旧 artifact 成功状态或 synthetic success。
- 不记录完整模型输出、完整用户输入、API key 或完整 prompt。
- 不处理第 2 轮之后的派生字段后端化、ID 收敛和具体高失败阶段 schema 修复。
- 不修改 Alex handoff 或 Lisa handoff 路径。

## 后端设计

### Diagnostic Model

新增共享诊断结构，建议放在 `sse_schemas.py`，由 `ErrorEvent` 可选引用：

```text
ErrorDiagnostic
- phase: request_validation | structured_output | contract_validation | provider | runtime | unknown
- workflowId: string
- stageId: string
- fieldPath: string
- validator: string
- retryable: boolean
- publicReason: string
```

字段约束：

- 所有字符串非空。
- `fieldPath` 无法定位时使用稳定兜底值，例如 `artifact_data`、`artifact_contract` 或 `runtime`，避免返回空字段。
- `publicReason` 是用户可见的短说明，不包含完整模型输出。
- `message` 保留现有详细错误文本，前端默认折叠显示。

### Diagnostic Builder

在 `stream_services.py` 增加诊断构建函数：

- Pydantic `ValidationError`：取第一条 `errors()`，`fieldPath` 由 `loc` 拼接，`validator` 使用 `type`，`phase=structured_output`。
- `AgentRuntimeSchemaError` / PydanticAI schema retry exhausted：`fieldPath=artifact_data`，`validator=pydantic_ai_output_retry` 或 `structured_output`，`phase=structured_output`。
- `ContractValidationError`：`fieldPath=artifact_contract`，`validator=workflow_contract`，`phase=contract_validation`。
- `RequestValidationError` / `ValueError`：`phase=request_validation`，`fieldPath=request`，`validator=request_schema`。
- `AgentRuntimeModelError`、OpenAI SDK `AuthenticationError`、`RateLimitError`、`APIError`：`phase=provider`，`fieldPath=provider`，`validator` 按鉴权、限流或 provider error 分类。
- `retryable`：schema retry exhausted、供应商限流、临时 API error 通常为 true；鉴权、请求参数、contract validation 通常为 false。具体实现可保守标记，不能把 false failure 当成功。

### Metric Persistence

扩展 `AgentRunTurnMetric` 可选字段：

- `diagnostic_phase`
- `diagnostic_field_path`
- `diagnostic_validator`
- `diagnostic_public_reason`
- `diagnostic_retryable`

沿用 `app.py` 中现有 `_ensure_*_columns()` 方式，新增 `_ensure_turn_metric_diagnostic_columns()`，为已有本地数据库补列。新字段只记录脱敏摘要，不记录完整错误文本。

`record_turn_metric()` 接收可选 `diagnostic`，成功 turn 不写诊断，错误 turn 写入诊断摘要。

### Observability Response

`get_runtime_observability_summary()` 的 `recentTurns[]` 增加：

```text
diagnostic: null | {
  phase,
  fieldPath,
  validator,
  publicReason,
  retryable
}
```

聚合层暂不新增复杂分组，避免本轮范围膨胀。后续如果需要按 fieldPath 或 validator 排名，可以在第 6 轮全工作流回归门禁里补。

## 前端设计

### SSE Parser

`core/llm.ts` 的 `AgentRuntimeEvent` 增加 error diagnostic 类型，解析时校验：

- `diagnostic` 缺失时保持现有行为。
- `diagnostic` 存在时必须是对象，字段类型正确，字符串非空。
- parse 后抛出的 Error 需要保留 typed diagnostic。推荐新增自定义 `AgentRuntimeError extends Error`，携带 `code`、`message` 和 `diagnostic`，避免继续从字符串反解析。

### Chat Service

`chatService.ts` 的 `formatAssistantErrorFeedback()` 优先读取 typed diagnostic：

- `phase=structured_output` 或 `contract_validation` 时，`kind=structured`。
- `phase=provider` 时，`kind=provider`。
- 其他为 `generic`。

`MessageErrorDiagnostic` 扩展字段：

- `phase`
- `workflowId`
- `stageId`
- `fieldPath`
- `validator`
- `retryable`

现有 `summary`、`reason`、`action`、`rawMessage`、`code` 保留。`summary` 优先使用 `publicReason`，并继续说明“右侧产出物已保持不变”。

### Chat Pane

诊断卡在展开详情时新增展示：

- 工作流 / 阶段
- 字段路径
- 校验器
- 是否建议重试

已有“重试本阶段生成”“补充信息后再试”“打开模型设置”等按钮保留。是否显示按钮仍由错误类型决定，不因为新增字段改变主路径。

### Observability Frontend

`observabilityService.ts` 和相关类型扩展 `recentTurns[].diagnostic`。Header 运行统计中 recent turn 可以显示诊断摘要；如果 UI 空间有限，至少在 recent turn 行显示 `fieldPath` 和 `validator`，详细 `publicReason` 可作为标题或小字展示。

## 数据流

```text
模型/运行时异常
  -> stream_services 归类 diagnostic
  -> ErrorEvent(code, message, diagnostic)
  -> record_turn_metric(error, error_code, diagnostic)
  -> frontend llm.ts 解析 typed error
  -> chatService 转成 MessageErrorDiagnostic
  -> ChatPane 诊断卡展示
  -> observability recentTurns 返回同一诊断摘要
```

## 错误处理边界

- 任何诊断构建失败都不能掩盖原始错误；应回退为 `phase=unknown` 的诊断，并保留原 `code/message`。
- SSE `error` 事件一旦发出，前端必须停止当前生成流程，不能继续等待 final `agent_turn`。
- 如果失败发生在已有 partial artifact delta 之后，现有行为继续标记 artifact truncated；本轮不改变该边界。
- 错误不会写入 assistant message 作为模型后续上下文；现有 `isAssistantControlFeedback()` 继续过滤错误反馈。

## 测试策略

后端：

- `sse_schemas` 测试：`ErrorEvent` 接受合法 diagnostic，拒绝空字段和非法 phase。
- `stream_services` 测试：模拟 Pydantic `ValidationError`，SSE error 包含 workflow/stage/fieldPath/validator/publicReason/retryable，且没有 `agent_turn`。
- `stream_services` 测试：模拟 `AgentRuntimeModelError`，diagnostic phase 为 provider，前端可识别为 provider failure。
- `run_persistence` 测试：错误 metric 持久化诊断字段，observability recent turn 返回诊断摘要。

前端：

- `llm.test.ts`：SSE error diagnostic 被解析并随 Error 传递，不再只能依赖 `code: message` 字符串。
- `chatService` 测试：typed structured diagnostic 生成 structured error card，保留 rawMessage 且不更新 artifact。
- `ChatPane.test.tsx`：展开详情可看到工作流 / 阶段、字段路径、校验器、重试建议。
- `observabilityService` 或 Header 测试：recent turn diagnostic 能被解析和展示。

回归：

- 现有 `code/message` only error fixture 仍通过，保证兼容旧后端或旧测试。
- 相关 New Agents backend/frontend 聚焦测试通过。

## 文档更新

实现完成后同步：

- `docs/api-contracts.md`：补充 SSE `error.diagnostic` schema。
- `docs/TESTING.md`：补充结构化失败诊断透明化回归口径。
- `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`：记录第 1 轮状态、spec、plan、验证和残余风险。

## 验收条件

1. Given 模型输出触发 Pydantic schema validation error
   When `/api/agent/runs/stream` 返回 SSE
   Then `error` 事件包含 `diagnostic.phase=structured_output`、当前 workflow/stage、字段路径、validator、publicReason 和 retryable；没有成功 artifact 被持久化。
   Evidence: 后端 stream service 测试。

2. Given 前端收到带 diagnostic 的 SSE error
   When 生成流程失败
   Then ChatPane 显示结构化错误卡，展开后能看到工作流 / 阶段、字段路径、校验器和原始错误摘要，右侧 artifact 保持不变。
   Evidence: `llm.ts`、`chatService`、`ChatPane` 测试。

3. Given 一个失败 turn 已记录 metric
   When 调用 `/api/agent/observability`
   Then recent turn 返回同一诊断摘要，且不包含完整模型输出或密钥。
   Evidence: persistence / observability 测试。

4. Given 旧格式 SSE error 只包含 `code/message`
   When 前端解析
   Then 仍按现有逻辑显示错误卡，不报格式错误。
   Evidence: 前端兼容测试。
