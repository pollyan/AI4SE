# New Agents 智能体框架深化阶段 1-2 路线图

> 状态: 正式路线图
> 创建日期: 2026-06-25
> 收束日期: 2026-06-25
> 背景: 当前 New Agents 已经使用 Pydantic AI 作为结构化 Agent Runtime 的一部分，但上下文压缩、工具调用、运行恢复、框架能力收口和质量观测仍主要由项目自研逻辑承担。下一步不应切换到 LangGraph、AutoGen 或 CrewAI 这类全量替换式框架，而应在保留共享 `/api/agent/runs/stream`、typed SSE、workflow manifest、artifact contract、run persistence 和共享 UI 的前提下，分阶段深化 Pydantic AI 内核能力。

## 收束记录

该文件已从 `docs/todos/refactor/` 活跃候选升格为 `docs/plans/` 正式路线图。后续执行时，不从本文件直接进入编码；应选择其中一个 Story，按 `docs/strategy/goal-mode-playbook.md` 单独生成 Current State Gap Analysis、spec、plan 和验证记录。

## 核心判断

New Agents 不是“尚未引入智能体框架”的空白系统。当前后端已经依赖 `pydantic-ai-slim[openai]==1.104.0`，并通过 `tools/new-agents/backend/agent_runtime.py` 承载结构化输出、contract retry、raw JSON streaming、DeepSeek V4 JSON mode 兼容和 typed SSE 交付。

接下来两阶段的目标不是重写 Agent Runtime，而是把现有框架使用从“薄包装”升级为“可扩展内核”:

- 阶段 1: Pydantic AI runtime kernel 收口。让模型调用、输出校验、provider capability、retry、streaming、metrics 和错误分类有清晰边界。
- 阶段 2: 上下文压缩与工具调用试点。基于阶段 1 的内核边界，加入结构化上下文策略、受控工具调用、审批/审计和首批 workflow 试点。

## 不变架构约束

- 继续复用共享 `/api/agent/runs/stream`，不新增 Lisa、Alex 或未来 agent 专属 SSE/API path。
- 继续使用 typed SSE 事件作为前端唯一主流式协议。
- workflow 差异继续通过 `workflow_manifest.json`、`agentId`、stage prompt/template、artifact contract、visual contract 和 handoff 配置表达。
- 前端继续复用共享 store、ChatPane、ArtifactPane、Header 和 workflow 配置层，不新增 agent-specific state store 或 renderer。
- 所有失败必须显式暴露，不能用 mock、伪造 artifact、隐藏 fallback 或假成功响应掩盖能力缺口。
- 工具调用、记忆写入和上下文摘要都必须可审计、可测试、可关闭。

## 用户故事拆分原则

这些故事按“技术用户故事”组织，每个故事都应能独立形成 design / plan / implementation，并带来一个可观察的架构能力提升。故事不会拆成过小的函数级任务；每个故事都应覆盖一个完整的技术边界、测试面和验收面。

建议拆分数量:

- 阶段 1: 5 个技术用户故事。
- 阶段 2: 5 个技术用户故事。

每个故事进入实现前都应单独补 Current State Gap Analysis、spec、TDD plan 和验证命令。

## Superpowers 执行要求

每一个 Story 后续都必须作为独立工作项走完一套完整 superpowers 流程，不能从本 todo 直接进入编码。

每个 Story 的标准流转:

1. 使用 `brainstorming` 重新进入该 Story 的 Current State Gap Analysis，确认当前代码事实、约束、风险和成功标准。
2. 形成该 Story 独立 design/spec，并保存到 `docs/superpowers/specs/YYYY-MM-DD-<story-topic>-design.md`。
3. spec 自检通过后，默认由 Agent 按 `docs/strategy/goal-mode-playbook.md` 的目标模式授权做自问自答式裁决，并在 spec 中记录取舍；只有涉及架构变更、外部权限、凭证、用户明确要求等待确认或无法自行裁决时，才停下来请求用户确认。
4. 使用 `writing-plans` 为该 Story 编写独立实施计划，保存到 `docs/superpowers/plans/YYYY-MM-DD-<story-topic>.md`。
5. 执行时使用 `subagent-driven-development` 或 `executing-plans`，按计划任务推进，并保持 TDD、频繁验证和 review checkpoint。
6. 完成前使用 `verification-before-completion`，用该 Story plan 中声明的 backend/frontend/e2e 命令验证。
7. 如 Story 涉及较大 runtime、上下文或工具调用边界变更，完成后使用 `requesting-code-review` 做一次独立审查，再进入下一 Story。

每个 Story 的 spec 和 plan 都必须明确记录:

- 当前状态差距。
- 不变架构约束。
- 涉及文件和模块边界。
- TDD 验证路径。
- typed SSE、artifact contract、run persistence、共享 UI 是否受影响。
- 本 Story 不做什么。

一个 Story 未完成上述流程前，不应合并到下一 Story 执行；确需并行时，必须说明无共享写入冲突，并分别保留独立 spec、plan 和验证记录。

---

## 阶段 1: Pydantic AI Runtime Kernel 收口

目标: 在不改变外部 API/SSE/UI contract 的前提下，把 `agent_runtime.py` 中混合的模型适配、结构化输出、streaming、contract retry、provider capability 和 metrics 责任拆成可扩展 runtime kernel。阶段 1 完成后，后续新增工具调用、上下文压缩和 durable execution 不应继续堆进一个大文件。

### Story 1.1: Runtime Kernel 边界重构

**技术用户故事**

作为 New Agents 平台维护者，我希望 Agent Runtime 的入口、模型适配、输出解析、contract 校验和 streaming 编排拥有清晰边界，这样后续新增工具调用或上下文压缩时，不需要继续修改一个承担过多职责的 `agent_runtime.py`。

**技术独立价值**

该故事的价值是建立 runtime 内核边界。它不改变用户可见行为，但能降低后续阶段每个能力的改动面，避免工具、记忆、provider capability、retry 和 SSE 编排互相耦合。

**建议范围**

- 拆分或收口以下职责:
  - Pydantic Agent 构建。
  - provider/model capability 解析。
  - raw JSON streaming adapter。
  - structured output instruction registry。
  - final output parser。
  - contract validator bridge。
- 保留 `stream_services.py` 对 runtime 的调用形态，避免 API 层感知内部拆分。
- 保留现有 `AgentTurnOutput`、`AgentTurnDeltaOutput`、`AgentRuntimeSchemaError`、`AgentRuntimeModelError` 对外语义。

**影响文件候选**

- `tools/new-agents/backend/agent_runtime.py`
- `tools/new-agents/backend/llm_client.py`
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/backend/tests/test_agent_runtime.py`
- `tools/new-agents/backend/tests/test_stream_services.py`

**验收标准**

- 现有 typed SSE 成功路径不变。
- DeepSeek V4 raw JSON streaming 兼容路径不变。
- contract validation failure 仍能触发有限 retry 或明确失败。
- runtime 单元测试可以分别覆盖 provider capability、output parsing、streaming delta 和 contract validator。
- 不新增任何 workflow/agent 专属 runtime 分支。

**非目标**

- 不引入 LangGraph。
- 不改变 frontend SSE parser。
- 不改变 artifact_data schema 或 renderer 行为。

### Story 1.2: Provider Capability Registry

**技术用户故事**

作为平台维护者，我希望每个模型供应商和模型族的能力被显式登记，而不是散落在 runtime 条件判断中，这样 OpenAI、DeepSeek、DashScope、SiliconFlow 或未来 OpenAI-compatible provider 的 structured output、thinking、streaming 和 retry 策略都能被一致处理。

**技术独立价值**

该故事解决 provider 适配扩散问题。它让模型能力成为可测试配置，而不是隐藏在调用代码中的 if/else。

**建议范围**

- 建立 provider/model capability 数据结构。
- 至少覆盖:
  - `json_object_only`
  - `json_schema_strict` 预留
  - `plain_text_fallback` 预留但默认不静默启用
  - thinking control
  - retry count
  - response_format
  - extra_body
- `deepseek-v4-*` 明确命中 `json_object_only` 和 thinking disabled。
- unknown provider 必须有诊断清晰的默认策略，不能假装支持 strict schema。

**影响文件候选**

- `tools/new-agents/backend/agent_runtime.py`
- `tools/new-agents/backend/config_service.py`
- `tools/new-agents/backend/tests/test_agent_runtime.py`
- `tools/new-agents/backend/tests/test_config_service.py`

**验收标准**

- provider capability 有独立单元测试。
- DeepSeek V4、OpenAI 默认模型、未知 OpenAI-compatible base_url 都有明确预期。
- capability 决策能进入 runtime metrics 或错误诊断上下文。
- 不向不支持的供应商发送 strict JSON Schema 参数。

**非目标**

- 不新增供应商 UI。
- 不要求真实 provider smoke 进入默认门禁。

### Story 1.3: Runtime Error Taxonomy 与用户可诊断错误

**技术用户故事**

作为维护者和使用者，我希望 runtime 失败能稳定归类为 schema、contract、provider auth、provider rate limit、provider HTTP、context、tool 等错误类型，这样前端、运行统计和排障文档可以给出明确行动，而不是统一显示“结构化输出生成失败”。

**技术独立价值**

该故事让失败成为产品化信号。它可以独立提升可运维性，并为第二阶段工具调用失败、上下文压缩失败建立通用错误承载方式。

**建议范围**

- 定义 runtime error code taxonomy。
- 将 PydanticAI schema error、OpenAI SDK auth/rate-limit/API error、contract validation error、JSON parse error 映射到稳定 code。
- SSE error event 保持现有 schema，但 code/message 更稳定。
- 运行指标记录 error_code、contract_retry_count、provider、model、workflow、stage。
- 前端错误文案仍保持共享，不为 Lisa/Alex 分叉。

**影响文件候选**

- `tools/new-agents/backend/stream_services.py`
- `tools/new-agents/backend/agent_runtime.py`
- `tools/new-agents/backend/sse_schemas.py`
- `tools/new-agents/backend/run_persistence.py`
- `tools/new-agents/backend/tests/test_stream_services.py`
- `tools/new-agents/frontend/src/core/llm.ts`
- `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`

**验收标准**

- 每类 runtime failure 都有稳定 error code。
- 前端能保留 typed SSE error 解析，不破坏现有错误卡片。
- observability 能按 error_code 聚合失败。
- schema/contract/provider 错误不会互相混淆。

**非目标**

- 不做自动修复。
- 不改变用户配置 API。

### Story 1.4: Runtime Metrics 与 Trace Hook 收口

**技术用户故事**

作为平台维护者，我希望每一轮 Agent Runtime 调用都能记录统一指标和可选 trace hook，这样后续无论使用 Pydantic Logfire、OpenTelemetry、LangSmith 还是自建观测，都不需要改动业务 workflow 代码。

**技术独立价值**

该故事建立观测插口。它先把 metrics/trace 的边界打稳，不要求立即绑定某个 SaaS 或外部平台。

**建议范围**

- 抽象 runtime metric collector 或 hook。
- 保留现有 `agent_run_turn_metrics` 作为项目内事实源。
- 增加可选 trace metadata:
  - run_id
  - workflow_id
  - stage_id
  - model/provider
  - capability tier
  - retry count
  - input/output size
  - error code
- 默认不向外部观测平台发送敏感 prompt 或 artifact 全文。

**影响文件候选**

- `tools/new-agents/backend/stream_services.py`
- `tools/new-agents/backend/run_persistence.py`
- `tools/new-agents/backend/models.py`
- `tools/new-agents/backend/tests/test_run_persistence.py`
- `tools/new-agents/backend/tests/test_stream_services.py`

**验收标准**

- 成功、schema failure、provider failure、contract retry exhausted 都有一致 metric。
- metric hook 不要求 Flask app context，便于单元测试。
- 外部 trace 适配点存在，但默认关闭。
- 不记录 API Key。

**非目标**

- 不上线外部观测平台。
- 不做完整 trace UI。

### Story 1.5: Runtime Contract Regression Fixture

**技术用户故事**

作为维护者，我希望每次调整 runtime kernel 时，都能用固定 contract fixture 验证 typed SSE、artifact contract、context warning、error event 和 partial delta 没有回归，这样重构不会依赖真实模型或人工浏览器验收。

**技术独立价值**

该故事提供阶段 1 的回归安全网。它让后续 runtime 内部重构可控，也能支撑阶段 2 的工具/上下文试点。

**建议范围**

- 扩展或整理 `tools/new-agents/contract-fixtures/agent-runtime-events.json`。
- 增加 fixture-driven backend tests。
- 增加 frontend parser fixture tests。
- 覆盖:
  - `run_started` with runId/warnings
  - partial `agent_delta`
  - final `agent_turn`
  - structured error
  - context_truncated warning
- fixture 不包含真实密钥、真实用户隐私或大段 artifact 正文。

**影响文件候选**

- `tools/new-agents/contract-fixtures/agent-runtime-events.json`
- `tools/new-agents/backend/tests/test_sse_encoder.py`
- `tools/new-agents/backend/tests/test_stream_services.py`
- `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`

**验收标准**

- 后端和前端共享同一类 typed event fixture。
- runtime 重构后，fixture tests 能证明协议未变。
- fixture 能覆盖 warning/error/final 三类关键路径。

**非目标**

- 不替代真实 LLM smoke。
- 不把 fixture 当生产 fallback。

---

## 阶段 2: 上下文压缩与工具调用试点

目标: 在阶段 1 runtime kernel 稳定后，引入两个最有价值的框架能力: 结构化上下文压缩和受控工具调用。阶段 2 应选择少量 workflow 做垂直试点，证明能力闭环后再扩散到全部 Lisa/Alex workflow。

### Story 2.1: 结构化上下文策略与压缩摘要

**技术用户故事**

作为长会话使用者，我希望系统在上下文接近窗口上限时，不只是按字符截断历史，而是保留用户补充、关键决策、阶段结论、artifact 摘要和锁定章节等结构化上下文，这样后续轮次能延续专业判断而不是遗忘关键约束。

**技术独立价值**

该故事直接解决超长上下文问题，是第二阶段最重要的能力。它把现有 `context_builder.py` 从 bounded concatenation 升级为可配置 context policy。

**建议范围**

- 定义 context policy:
  - 当前用户输入必须保留。
  - locked artifact sections 必须保留或明确失败。
  - manual decision summary 优先级高于普通历史消息。
  - artifact summary 优先于完整旧 artifact。
  - 低价值聊天历史可截断。
- 建立 context budget 分层:
  - reserved chars for current prompt
  - reserved chars for locked sections
  - reserved chars for summaries
  - remaining chars for recent messages
- 保留 `context_truncated` warning，但 message 更明确。

**影响文件候选**

- `tools/new-agents/backend/context_builder.py`
- `tools/new-agents/backend/context_summary_format.py`
- `tools/new-agents/backend/run_persistence.py`
- `tools/new-agents/backend/tests/test_context_builder.py`
- `tools/new-agents/backend/tests/test_stream_services.py`

**验收标准**

- 超长历史下，当前输入、关键决策、阶段结论和锁定章节按优先级保留。
- 截断行为可预测、可测试。
- run_started warnings 能提示上下文压缩或截断。
- 不把控制错误消息注入模型上下文。

**非目标**

- 不引入向量记忆。
- 不做跨 run 长期个性化记忆。

### Story 2.2: Context Summary 生成与写入门禁

**技术用户故事**

作为平台维护者，我希望上下文摘要不是任意写入长期记忆，而是经过 schema、来源、类型和覆盖范围校验后再写入，这样可以降低记忆污染、摘要冲突和错误信息长期影响后续 workflow 的风险。

**技术独立价值**

该故事建立 memory write-path 的安全边界。它比直接引入向量记忆更适合当前系统，因为 New Agents 的产物和阶段天然结构化。

**建议范围**

- 明确 summary types:
  - user supplement
  - stage conclusion
  - decision
  - current artifact summary
  - handoff summary
- 每条 summary 必须有:
  - source_type
  - source_stage_id
  - summary_type
  - content
  - generated_by
  - validation status
- 对模型生成摘要使用 Pydantic schema 校验。
- 对人工编辑摘要保留审计记录。
- 如果摘要生成失败，不伪造成功；当前 turn 仍可基于未压缩上下文继续或明确失败。

**影响文件候选**

- `tools/new-agents/backend/context_summary_format.py`
- `tools/new-agents/backend/run_persistence.py`
- `tools/new-agents/backend/routes.py`
- `tools/new-agents/backend/tests/test_run_persistence.py`
- `tools/new-agents/backend/tests/test_context_builder.py`

**验收标准**

- summary 写入有明确 schema 和来源字段。
- summary 更新可审计。
- 无效 summary 不会进入 runtime prompt。
- 用户手动决策摘要优先级高于模型自动摘要。

**非目标**

- 不做 embedding retrieval。
- 不做自动跨项目记忆复用。

### Story 2.3: Pydantic AI Tool Registry 与只读工具试点

**技术用户故事**

作为 workflow 设计者，我希望可以通过共享 tool registry 给 Agent Runtime 暴露受控工具，而不是在 workflow prompt 中让模型假装知道系统状态，这样 Lisa/Alex 后续可以读取 run snapshot、artifact diagnostics、workflow metadata 或测试资产摘要等真实数据。

**技术独立价值**

该故事引入工具调用能力，但选择低风险只读工具作为首批试点。它能验证 Pydantic AI tool 集成、typed output、错误处理和审计链路，而不会引入写操作风险。

**建议范围**

- 建立共享 tool registry。
- 工具声明包含:
  - tool_id
  - description
  - input schema
  - output schema
  - permission level
  - workflow/stage availability
  - audit policy
- 首批只读工具候选:
  - read_run_snapshot_summary
  - read_current_artifact_diagnostics
  - read_workflow_stage_contract
  - read_test_asset_quality_summary
- 工具输出必须是结构化 JSON，不直接拼 Markdown artifact。

**影响文件候选**

- `tools/new-agents/backend/agent_runtime.py`
- `tools/new-agents/backend/run_persistence.py`
- `tools/new-agents/backend/workflow_contract_registry.py`
- `tools/new-agents/backend/test_assets.py`
- `tools/new-agents/backend/tests/test_agent_runtime.py`
- `tools/new-agents/backend/tests/test_agent_contracts.py`

**验收标准**

- 工具可以按 workflow/stage 开关。
- 工具输入输出都有 Pydantic 校验。
- 工具失败映射到稳定 runtime error 或 tool warning。
- 工具调用记录进入 metric/audit，不暴露 API Key。
- 不引入写工具。

**非目标**

- 不做外部系统写入。
- 不给模型 shell、浏览器或数据库任意查询能力。

### Story 2.4: 工具调用审批、审计与前端展示边界

**技术用户故事**

作为产品和平台维护者，我希望工具调用在进入高风险能力前先有审批、审计和 UI 边界，这样未来新增写操作工具或外部集成时，不会绕过用户确认和安全控制。

**技术独立价值**

该故事为工具体系建立 governance。即使阶段 2 只上线只读工具，也要先定义审批和审计协议，避免后续工具扩展变成不受控能力。

**建议范围**

- 定义 tool permission levels:
  - readonly_auto
  - readonly_sensitive_confirm
  - write_requires_confirm
  - external_side_effect_forbidden_by_default
- 定义 tool audit event:
  - run_id
  - workflow_id
  - stage_id
  - tool_id
  - input hash 或脱敏摘要
  - output hash 或脱敏摘要
  - status
  - approval state
- 前端首批只需要展示“本轮使用了哪些只读工具”的只读 trace，不必做完整审批 UI。
- 如果工具需要审批但 UI 尚未支持，runtime 必须拒绝而不是自动执行。

**影响文件候选**

- `tools/new-agents/backend/models.py`
- `tools/new-agents/backend/run_persistence.py`
- `tools/new-agents/backend/sse_schemas.py`
- `tools/new-agents/backend/stream_services.py`
- `tools/new-agents/frontend/src/core/llm.ts`
- `tools/new-agents/frontend/src/components/ChatPane.tsx`

**验收标准**

- 只读工具调用可被记录和回放。
- 未授权工具不会执行。
- 需要审批的工具在无审批 UI 时明确失败。
- 前端不会把 tool trace 当 artifact 正文写入。

**非目标**

- 不实现写工具审批全流程。
- 不实现外部系统 OAuth。

### Story 2.5: 首个 Workflow 垂直试点与质量回归

**技术用户故事**

作为平台维护者，我希望选择一个 workflow 完成“上下文压缩 + 只读工具调用 + contract 输出 + typed SSE + 持久化回放”的完整垂直试点，这样可以验证第二阶段能力确实能服务真实工作流，而不是只停留在 runtime 单元测试。

**技术独立价值**

该故事把阶段 2 的平台能力落到一个可验收 workflow 上。它不是新增业务功能，而是证明新 runtime 能力可以穿透后端、SSE、前端和持久化。

**建议试点选择**

优先选择 `REQ_REVIEW` 或 `TEST_DESIGN/CLARIFY -> STRATEGY`:

- `REQ_REVIEW` 适合验证需求上下文摘要、质量诊断工具和报告阶段继承。
- `TEST_DESIGN` 适合验证 artifact summary、测试资产质量摘要和阶段推进后的上下文延续。

**建议范围**

- 选定一个 workflow/stage pair。
- 构造长历史 run，触发 context compression。
- 允许一个只读工具在该 stage 可用。
- final output 仍必须通过现有 artifact contract。
- run snapshot 恢复后能看到摘要、工具调用 trace 和最终 artifact。

**影响文件候选**

- `tools/new-agents/workflow_manifest.json`
- `tools/new-agents/backend/agent_runtime.py`
- `tools/new-agents/backend/context_builder.py`
- `tools/new-agents/backend/run_persistence.py`
- `tools/new-agents/backend/tests/test_agent_runtime.py`
- `tools/new-agents/backend/tests/test_context_builder.py`
- `tools/new-agents/backend/tests/test_agent_endpoint.py`
- `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`

**验收标准**

- 一个真实 workflow stage 使用新 context policy 生成合法 artifact。
- 至少一次只读工具调用被记录。
- typed SSE parser 无需分叉。
- run snapshot 能恢复摘要和工具 trace。
- LLM judge 或 mock e2e evidence 能证明输出质量没有明显退化。

**非目标**

- 不一次性推广到所有 17 个阶段。
- 不新增新的 Lisa/Alex workflow。

---

## 阶段间依赖

建议执行顺序:

1. Story 1.5 先建立 regression fixture，或至少和 Story 1.1 并行完成。
2. Story 1.1 完成 runtime 边界后，再做 Story 1.2 provider capability registry。
3. Story 1.3 和 Story 1.4 可在 1.1 后并行推进。
4. 阶段 2 必须等 Story 1.1、1.2、1.3 至少完成后再开始。
5. Story 2.1 和 2.2 应先于工具试点，因为工具结果也会进入上下文和审计。
6. Story 2.3 和 2.4 可以一起设计，但实现上先做只读工具 registry，再补审批/审计边界。
7. Story 2.5 必须最后做，作为阶段 2 的端到端验收切片。

## 总体验收标准

阶段 1 完成后:

- runtime 内部职责拆分清晰。
- provider capability 可测试。
- runtime error code 稳定。
- metrics/trace hook 有统一入口。
- typed SSE regression fixture 能保护 API/前端协议。
- 所有现有 workflow 仍通过共享 Agent Runtime 运行。

阶段 2 完成后:

- 长上下文场景不再只依赖字符截断。
- context summary 写入有来源、类型、schema 和审计边界。
- 至少一类只读工具可被 Pydantic AI Runtime 调用。
- 工具调用有权限、审计和失败处理。
- 至少一个 workflow 完成端到端垂直试点。
- 不引入 agent-specific runtime、API、store 或 renderer。

## 建议验证矩阵

Backend:

- `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_runtime.py -q`
- `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py -q`
- `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py -q`
- `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py -q`
- `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q`

Frontend:

- `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts`
- `cd tools/new-agents/frontend && npm run lint`

E2E / evidence:

- 使用 mock typed SSE 覆盖上下文 warning、tool trace、final artifact。
- 对选定试点 workflow 运行一次 LLM judge 或真实模型 smoke，真实模型验证需要显式凭证、网络和额度。

## 暂不纳入本轮

- LangGraph 全量替换。
- OpenAI Agents SDK 全量替换。
- AutoGen/CrewAI 多 agent conversation runtime。
- 长期向量记忆或跨项目个性化记忆。
- 写操作工具、shell/browser/database 任意工具。
- 外部系统写入，例如 Jira、禅道、飞书、Slack。
- 新增业务 workflow。

## 待决策问题

- 阶段 1 是否先做 fixture 安全网，还是先拆 runtime kernel 再补 fixture。
- provider capability registry 是否使用纯 Python registry，还是同步从配置文件生成。
- context summary 自动生成是否由主 Agent 同轮完成，还是由独立 summarizer 在 turn 后异步完成。
- 工具调用 trace 是否需要扩展 typed SSE schema，还是先只进入 run snapshot / observability。
- 阶段 2 垂直试点优先选 `REQ_REVIEW` 还是 `TEST_DESIGN`。
