# New Agents 结构化产出失败治理待办

- 状态：执行中（第 0 轮 DeepSeek tool calls 静态能力 spike 已完成；第 1、2 轮已完成；第 3 轮首个 `VALUE_DISCOVERY/ELEVATOR` 派生字段纵切已完成；第 4 轮 `IDEA_BRAINSTORM/DEFINE` 证据引用纵切已完成）
- 创建日期：2026-07-08
- 来源：用户反馈 New Agents 生成右侧产出物时经常出现黄色失败框，要求系统分析反复失败原因，并明确禁止用 fallback 草稿隐藏错误
- 优先级：P0
- 相关模块：`tools/new-agents/`

## 背景与当前证据

本地 `/api/agent/observability?limit=100` 观测结果显示：

- 共 81 次 turn，失败 9 次，整体成功率 88.89%。
- 失败中 8 次为 `SCHEMA_VALIDATION_FAILED`，1 次为 `LLM_ERROR`。
- `deepseek` provider 下 78 次 turn 中 8 次失败，失败全是 `SCHEMA_VALIDATION_FAILED`。
- 失败高发阶段集中在：
  - `IDEA_BRAINSTORM/DEFINE`：13 次 turn，3 次 `SCHEMA_VALIDATION_FAILED`。
  - `IDEA_BRAINSTORM/DIVERGE`：3 次 turn，1 次 `SCHEMA_VALIDATION_FAILED`。
  - `IDEA_BRAINSTORM/CONVERGE`：1 次 turn，1 次 `SCHEMA_VALIDATION_FAILED`。
  - `TEST_DESIGN/CASES`：4 次 turn，2 次 `SCHEMA_VALIDATION_FAILED`。
  - `TEST_DESIGN/STRATEGY`：21 次 turn，1 次 `SCHEMA_VALIDATION_FAILED`。
- `VALUE_DISCOVERY/ELEVATOR` 当前本地记录 4 次 turn 全部成功，但它仍存在可计算字段由模型输出的结构性风险，例如 `score_summary.total_score` 和 `average_score`。

当前判断：反复失败的直接原因主要是大模型输出结构化 `artifact_data` 时无法稳定满足后端 Pydantic schema 与业务不变量。根因不应简单归咎于模型不稳定，而应继续收敛为产品架构问题：我们把过多需要精确一致的派生字段、ID 引用、跨字段一致性和统计汇总交给模型生成。

## DeepSeek V4 Flash 适配结论

当前 New Agents 使用 DeepSeek V4 Flash 时，本地 runtime 只启用了 `json_object_only` 能力：`response_format={"type":"json_object"}`，并在 `deepseek-v4-*` 下关闭 thinking。该能力只能帮助模型输出合法 JSON，不能保证满足 Pydantic schema、业务不变量、跨字段引用或统计一致性。因此，治理主线不能押在 JSON mode 本身，而应优先减少模型需要精确维护的结构复杂度。

可直接采用的举措：

- 后端确定性生成派生字段。模型只输出语义事实和原子判断，`total_score`、`average_score`、`case_count`、P0/P1/P2 汇总、`high_risk_count`、覆盖统计、RPN、排序摘要等由后端计算。
- 后端确定性分配或归一化 ID。模型不再负责维护跨表 ID、source id、rank id、requirement/risk/case 引用链；renderer 或 normalizer 负责生成稳定 ID，并在最终 contract 校验前拒绝无法归一化的数据。
- typed error taxonomy 与脱敏诊断持久化。失败继续显式暴露，但错误信息应能定位到 workflow、stage、field path、validator、attempt 和 provider。
- schema / prompt / contract 单源同步。把 Pydantic schema、structured output instruction、workflow manifest visual contract、frontend prompt 中重复书写的关键约束收敛到可测试的同步机制。
- 高失败阶段纵切治理。优先处理 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/CONVERGE`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY`、`IDEA_BRAINSTORM/DIVERGE`。

可做能力 spike、但不能作为当前主线的举措：

- DeepSeek Function Calling / Tool Calls。DeepSeek 支持工具调用，但当前 `llm_client.py` 只消费 `delta.content`，没有接入 `tools`、`tool_choice`、`delta.tool_calls` 或 tool argument streaming。若采用，应设计为 `submit_artifact_data(...)` 这类语义数据提交工具，而不是让模型调用 `render_artifact(...)`。
- DeepSeek strict tool call。strict mode 是可研究增强项，但它是 beta 能力，需要独立 provider capability 开关，并且 JSON Schema 子集有限：object 的字段必须全部 required、`additionalProperties=false`，且不支持 `minLength`、`maxLength`、`minItems`、`maxItems` 等约束。它不能替代后端 Pydantic validators、业务校验和 deterministic renderer。

不适合作为 DeepSeek V4 Flash 主方案的举措：

- 直接照搬 OpenAI `response_format=json_schema` / `strict=true` structured outputs。DeepSeek 当前 Chat Completion `response_format` 只适配 `text` 和 `json_object`，不能按 OpenAI strict JSON Schema 响应格式直接接入。
- 把右侧产出物渲染本身交给模型工具调用。渲染必须继续由后端 deterministic renderer 负责，模型最多提交结构化业务数据。

## 视觉产物稳定化结论

最新调研结论：Mermaid、D2、Graphviz DOT、PlantUML 这类文本图 DSL 都适合作为工具链编译目标，但不适合作为 LLM 直接输出的主协议。更稳定的路线是：模型输出结构化业务图数据，后端确定性编译，渲染前做强校验。也就是说，`ai4se-visual` 应升级为复杂视觉产物的主协议，Mermaid 只作为少数简单图的后端生成结果或导出目标。

当前项目已有基础：

- 前端 `Mermaid.tsx` 已使用 `mermaid.parse` 做语法校验，并有图表诊断 UI。
- 前端 `StructuredVisual.tsx` / `structuredVisuals.ts` 已支持 `ai4se-visual` 的稳定 JSON 渲染，但当前类型以表格/矩阵类为主。
- 后端 `artifact_data_renderers.py` 已能从 `artifact_data` 确定性输出 Mermaid 和 `ai4se-visual`，方向正确。
- 后端存在 `/api/utils/mermaid/repair`，但它只能作为显式人工修复入口，不能作为自动 fallback 或静默成功路径。

视觉产物治理主张：

- 复杂图优先结构化。`flow-map`、`timeline-map`、`mindmap`、`sequence-flow`、`journey-map`、`coverage-map`、`score-matrix`、`roadmap` 等应由 `ai4se-visual` JSON 表达，前端组件直接消费数据渲染。
- Mermaid 降级为编译目标。只有简单 `pie`、简单 `flowchart`、简单 `timeline`、简单 `mindmap` 可由后端 deterministic renderer 从结构化数据生成 Mermaid；模型不得直接手写 Mermaid。
- 渲染前必须强校验。正式 artifact 被呈现为成功、持久化或推进阶段前，应至少通过 Pydantic / JSON schema、引用完整性校验、Mermaid parse 或等价 `mmdc` / fixture 渲染门禁；具体校验落点在视觉专项中确定，不能假定 Python backend 当前已具备 `mermaid.parse` 运行环境。
- 视觉失败必须显式失败。Mermaid 解析失败、`ai4se-visual` JSON 无效、引用缺失、渲染失败都不能被旧图、草稿、自动修复或缓存内容掩盖。

## 严格原则

- 严禁 fallback 草稿、静默成功、伪造成功、生产 mock 或隐藏失败。
- 结构化产出最终校验失败时必须继续显式报错，不得持久化为正式 artifact，不得推进 stage，不得生成看起来成功的右侧产物。
- 可增加诊断信息、观测信息和自动化证据，但不能降低 contract 严格性来绕过失败。
- 所有治理必须继续复用共享 Agent Runtime、typed SSE、run persistence、workflow manifest、共享 frontend store 和 ArtifactPane；不得新增 Lisa、Alex 或单 workflow 专属 runtime / API / store / 渲染管线。
- 视觉产物治理必须复用共享 artifact renderer、Mermaid component、StructuredVisual component 和 visual contract registry；不得为单 workflow 新增独立图表渲染管线。

## 已识别优化点

下列优化点分为横切能力、纵切阶段治理和回归门禁三类。若条目之间看起来覆盖相同问题，以“横切能力提供机制，纵切阶段消化具体 workflow 风险，回归门禁防止回退”为准，不按重复事项分别验收。

- [x] 做 DeepSeek tool calling 能力 spike。（第 0 轮）
  - 目标：验证 `submit_artifact_data(...)` 工具调用是否能在 DeepSeek V4 Flash 下稳定产出 tool arguments，并评估它对当前 partial artifact streaming 的影响。
  - 范围：只做共享 provider capability、tool-call stream parsing、最小单阶段 fixture，不接入正式 workflow 主链路。
  - 验收：形成明确结论：是否支持 streaming tool arguments、是否需要 `/beta` base URL、strict schema 子集能覆盖哪些字段、失败时是否仍然能 typed error 显式暴露。
  - 结论：本轮完成静态 provider capability spike，不启用正式 tool calls 主链路。DeepSeek 官方支持 tool calls，strict mode 需要 `/beta` base URL；strict schema 子集不能完整覆盖当前 `artifact_data` contract，不能替代 Pydantic validators。官方 streaming chunk schema 未明确展示 `delta.tool_calls` / streaming tool arguments；本地 `llm_client.py` 也只消费 `delta.content`，没有 `tools`、`tool_choice` 或 tool argument parser。当前环境缺少 `DEEPSEEK_API_KEY`，因此未做真实 provider smoke，不声明 DeepSeek V4 Flash 已稳定支持 streaming tool arguments。后续若要启用，必须单独增加 shared provider capability registry、mock stream fixture、toy `submit_artifact_data` live smoke 和 typed error 路径。

- [x] 移除 raw JSON 截断后的伪最终输出路径。（第 2 轮）
  - 当前风险：`agent_runtime.py` 在 JSON 截断且已经发过 partial delta 时，会返回带 `warnings=["artifact_truncated"]` 的 `AgentTurnOutput`，这会把不完整产物包装成一次最终输出。
  - 目标：JSON decode 失败、长度截断、空内容或 provider 中断必须显式失败，不能持久化为正式 artifact，不能推进 stage，不能让右侧产物呈现为成功结果。
  - 验收：增加回归测试证明 partial delta 可以在流式过程中出现，但最终 JSON 无效时必须产生错误事件和失败 metric，而不是 `agent_turn` 成功帧。

- [x] 将错误诊断从字符串匹配升级为 typed error taxonomy，并接入前端诊断展示。（第 1 轮）
  - 目标：后端错误事件返回 `phase`、`workflowId`、`stageId`、`fieldPath`、`validator`、`retryable`、`publicReason`；前端优先使用 typed diagnostic 生成错误卡片和观测摘要。
  - 约束：错误仍然必须暴露给用户，不能被 UI 吃掉或降级成成功状态。

- [x] 持久化结构化失败的脱敏诊断。（第 1 轮）
  - 目标：`agent_run_turn_metrics` 或相邻观测表记录 validation path、错误类别、attempt、模型、provider、stage 和最后一次失败原因。
  - 约束：不得记录 API key、完整用户私密输入或完整模型输出。

- [ ] 把可计算字段从模型输出中移除，改为后端确定性生成。（第 3 轮；首个 `VALUE_DISCOVERY/ELEVATOR` 评分汇总纵切已完成）
  - 候选字段：`total_score`、`average_score`、`case_count`、P0/P1/P2 汇总、`high_risk_count`、覆盖统计、RPN 等派生值。
  - 目标：模型只输出语义内容和原子事实，后端负责确定性计算、排序和汇总。

- [ ] 收敛 ID 与引用关系。（第 4-6 轮）
  - 目标：后端生成稳定 ID，或在 renderer/normalizer 中确定性分配 ID；模型不再负责维护容易漂移的跨表引用。
  - 重点阶段：`IDEA_BRAINSTORM/DEFINE` 的 evidence 引用，`IDEA_BRAINSTORM/CONVERGE` 的 idea / rank / recommended idea 引用，`TEST_DESIGN/CASES` 的 requirement / risk / case 覆盖引用。
  - 进展：第 4 轮已完成 `IDEA_BRAINSTORM/DEFINE` 的 root problem / evidence / problem-user-fit ID 引用治理；`CONVERGE` 和 `TEST_DESIGN/CASES` 仍未完成。

- [ ] 建立 schema / prompt / contract 单源同步机制。（横切，第 3-8 轮）
  - 目标：Pydantic validators、structured output instruction、workflow manifest visual contract、frontend prompt 不再各写一套约束。
  - 验收：新增 contract sync 测试，证明关键不变量在 prompt 和后端 validator 中同时存在。

- [ ] 针对高失败阶段做纵切专项修复。（第 4-6 轮）
  - 优先顺序：`IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/CONVERGE`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY`、`IDEA_BRAINSTORM/DIVERGE`。
  - 目标：每个阶段都有失败复现、根因定位、最小 schema 设计修复和回归测试。
  - 进展：第 4 轮已完成 `IDEA_BRAINSTORM/DEFINE` 的已知 root-problem 覆盖失败模式修复；后续仍需处理 `CONVERGE`、`CASES`、`STRATEGY`、`DIVERGE`。

- [ ] 增加结构化失败回归门禁。（第 8 轮）
  - 目标：高失败阶段必须有固定 fixture / raw JSON stream / renderer contract 测试，确保不会再次因为已知不变量触发 `SCHEMA_VALIDATION_FAILED`。
  - 验收：纳入 `./scripts/test/test-local.sh new-agents` 或明确的 New Agents backend regression suite。

- [ ] 建立视觉产物协议分层。（第 7 轮）
  - 目标：明确哪些视觉类型必须走 `ai4se-visual` JSON，哪些 Mermaid 类型允许由后端 deterministic renderer 生成，哪些 DSL 禁止模型直接输出。
  - 初始策略：复杂图和业务图默认走 `ai4se-visual`；Mermaid 只允许作为后端从结构化数据生成的简单图编译目标；不引入 D2、Graphviz 或 PlantUML 作为运行时主协议，除非后续有单独架构批准。
  - 验收：`workflow_manifest.json`、`agent_contracts.py`、structured output instruction 和前端模板对每个在线阶段的视觉协议一致。

- [ ] 扩展 `ai4se-visual` 类型覆盖复杂图。（第 7 轮）
  - 目标：在现有 `score-matrix`、`coverage-map`、`journey-map` 等表格类视觉之外，补齐 `flow-map`、`timeline-map`、`mindmap`、`sequence-flow`、`distribution-chart` 等数据结构，使复杂图不再依赖模型手写 Mermaid。
  - 约束：每个 visual 类型必须有严格 schema、引用完整性校验、前端渲染组件、导出降级文本和失败诊断。
  - 验收：至少选一个 Mermaid 失败高风险阶段完成纵切迁移，并证明最终 artifact 不含模型手写 Mermaid。

- [ ] 建立视觉渲染强校验门禁。（第 7 轮）
  - 目标：正式 artifact 被呈现为成功、持久化和阶段推进前，必须通过 Mermaid / `ai4se-visual` 视觉校验；若运行时校验暂不能放在 backend，则必须先以 CI / renderer fixture / frontend parse 形成可执行门禁，并在运行时失败时显式诊断。
  - Mermaid 校验：允许的 Mermaid block 必须通过 `mermaid.parse` 或等价校验；CI 或回归套件可增加 `mmdc` 渲染 SVG 门禁，覆盖浏览器能 parse 但导出失败的情况。
  - `ai4se-visual` 校验：JSON 必须合法，`type` 必须受支持，columns / rows / nodes / edges / events 等结构必须完整，引用目标必须存在。
  - 验收：新增测试证明视觉校验失败会显式报错，不产生成功 `agent_turn`、不持久化 artifact、不推进 stage。

- [ ] 收紧 Mermaid repair 的架构边界。（第 7 轮）
  - 目标：`/api/utils/mermaid/repair` 和前端 retry 只能作为用户显式触发的修复辅助，不能自动替换正式 artifact、不能绕过 contract、不能让失败状态变成成功。
  - 验收：测试证明 repair 结果必须重新经过 Mermaid parse / artifact contract 校验；repair 失败继续显式展示，不隐藏原始错误。

## 目标轮数声明

基线按 1 个第 0 轮能力 spike 加 8 个目标模式治理轮次推进。每轮都必须保留“失败显式报错”的架构边界，不允许通过 fallback 降低用户可见错误。第 0 轮是能力 spike，不改变正式 workflow 主链路；当前已补做第 0 轮静态能力结论，真实 provider smoke 仅在具备 `DEEPSEEK_API_KEY` 和明确外部调用授权时再单独执行。

| 轮次 | 目标模式 | 覆盖范围 | 交付边界 |
|---|---|---|---|
| 第 0 轮 | DeepSeek provider 能力 spike | JSON mode 边界、tool calling、strict tool call、streaming tool arguments | 只产出能力结论、最小 fixture 和 provider capability 设计，不改变正式 workflow 主链路；确认 tool calling 是否值得进入后续轮次。 |
| 第 1 轮 | 结构化失败诊断透明化 | backend error event、frontend diagnostic card、observability metrics | 用户和工程师能直接看到失败发生在哪个 workflow/stage/field/validator；仍然显式失败，不持久化错误产物。 |
| 第 2 轮 | 严格失败闭环 | raw JSON 截断、空内容、provider 中断、partial delta 最终失败 | 移除 `artifact_truncated` 伪最终输出；partial delta 可用于流式预览，但最终 JSON 无效必须显式失败，不持久化、不推进 stage。 |
| 第 3 轮 | 可计算字段后端化首个纵切 | `VALUE_DISCOVERY/ELEVATOR` 或 `TEST_DESIGN/CASES` 中一组派生字段 | 模型不再输出选定派生字段；后端确定性计算并渲染；相关旧失败模式有回归测试。 |
| 第 4 轮 | IDEA DEFINE 根问题与证据一致性治理 | `IDEA_BRAINSTORM/DEFINE` | root problem、evidence、problem-user-fit 的覆盖关系由更稳定的数据结构或后端确定性关联保证；真实已知失败类型不再复现。 |
| 第 5 轮 | IDEA CONVERGE / DIVERGE 引用一致性治理 | `IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE` | idea id、source id、rank、recommended idea、merge path 等引用关系不再依赖模型自由维护。 |
| 第 6 轮 | TEST_DESIGN CASES / STRATEGY 统计与覆盖治理 | `TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` | 用例统计、覆盖追踪、风险/测试点/用例映射中的派生值和引用关系稳定化。 |
| 第 7 轮 | 视觉产物稳定化专项 | Mermaid、`ai4se-visual`、ArtifactPane、visual contract registry、导出链路 | `ai4se-visual` 成为复杂视觉主协议；Mermaid 只作为后端确定性编译目标；视觉失败显式报错并进入回归门禁。 |
| 第 8 轮 | 全工作流失败回归门禁与文档收口 | 所有在线 artifact-data 阶段 | 新增或更新测试矩阵、TESTING 文档、观测说明；明确哪些字段由模型输出、哪些字段由后端生成，哪些视觉由结构化协议驱动。 |

## 目标模式执行记录

### 2026-07-08 第 1 轮：结构化失败诊断透明化

已完成共享 Agent Runtime 错误诊断链路：

- 后端 `ErrorEvent` 新增可选 `diagnostic`，包含 `phase`、`workflowId`、`stageId`、`fieldPath`、`validator`、`retryable`、`publicReason`。
- `stream_services.py` 为结构化输出、contract、request、runtime、provider 失败生成同一套脱敏 diagnostic，并同时写入 SSE error 和 turn metric。
- `agent_run_turn_metrics` 新增脱敏 diagnostic 字段，`GET /api/agent/observability` 的 `recentTurns[].diagnostic` 可返回失败阶段、字段路径、validator、公开原因和是否可重试。
- 前端 `core/llm.ts` 解析 SSE error diagnostic 并抛出 typed runtime error；`chatService.ts` 优先使用 typed diagnostic 生成错误卡片；`ChatPane.tsx` 展开详情可见 workflow/stage、field path、validator 和重试建议；`Header.tsx` 运行统计最近 turn 展示诊断摘要。
- API 与测试文档已记录 SSE error diagnostic、observability diagnostic 和前端/后端回归测试口径。

已验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_sse_encoder.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_run_persistence.py -q
```

结果：`56 passed`

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx
```

结果：`207 passed`

补充验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

结果：`172 passed`

```bash
cd tools/new-agents/frontend && npm run lint
```

结果：TypeScript `tsc --noEmit` 通过。

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents 前端 `701 passed`；New Agents 后端 `553 passed, 1 deselected`。运行中出现既有 React `act(...)` warning，但未导致测试失败。

### 2026-07-08 第 2 轮：严格失败闭环

已完成 raw JSON streaming 截断失败治理：

- `agent_runtime.py` 已移除 JSON 截断后构造 `AgentTurnOutput(warnings=["artifact_truncated"])` 的伪最终输出路径。
- raw JSON streaming 期间仍允许已闭合 `artifact_data` 字段生成正式 partial artifact delta，用于右侧流式预览。
- 最终 accumulated JSON 无效、未闭合或被截断时，runtime 抛出 `AgentRuntimeSchemaError`；`stream_services.py` 输出 `SCHEMA_VALIDATION_FAILED` typed error，并记录失败 metric。
- 已新增回归测试证明 partial artifact delta 可以先出现，但最终无效 JSON 不会产生 `agent_turn` 成功帧，不会 append assistant message，不会 record artifact version。
- 第 2 轮设计与执行计划已记录在：
  - `docs/superpowers/specs/2026-07-08-new-agents-strict-structured-failure-closure-design.md`
  - `docs/superpowers/plans/2026-07-08-new-agents-strict-structured-failure-closure.md`

RED 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_fails_final_json_truncation_after_partial_delta -q
```

结果：修复前失败，失败原因为旧实现没有抛出 `AgentRuntimeSchemaError`。

已验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_fails_final_json_truncation_after_partial_delta tools/new-agents/backend/tests/test_stream_services.py::test_stream_agent_run_events_errors_after_partial_delta_without_persisting_artifact -q
```

结果：`2 passed`

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q
```

结果：`109 passed`

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

结果：`229 passed`

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents 前端 `706 passed`；New Agents 后端 `562 passed, 1 deselected`。运行中出现既有 React `ArtifactPane.test.tsx` `act(...)` warning，但未导致测试失败。

### 2026-07-08 第 3 轮首个纵切：VALUE_DISCOVERY/ELEVATOR 评分汇总后端化

已完成首个可计算字段后端化纵切：

- `ValueScoreSummary.total_score` 和 `average_score` 改为可选输入；模型缺省时由后端根据 `score_matrix[].score` 确定性计算。
- 显式错误的 `score_summary.total_score` 或 `score_summary.average_score` 仍触发 `ValidationError`，不生成假成功 artifact。
- `VALUE_DISCOVERY/ELEVATOR` structured output instruction 示例不再要求模型输出总分和平均分，只要求输出 `score_summary.judgement`。
- partial renderer 复用同一套评分汇总 normalizer，raw JSON streaming 期间只要 `score_matrix` 与 `score_summary.judgement` 闭合即可输出正式评分章节。
- 本轮设计与执行计划已记录在：
  - `docs/superpowers/specs/2026-07-08-new-agents-value-elevator-derived-score-summary-design.md`
  - `docs/superpowers/plans/2026-07-08-new-agents-value-elevator-derived-score-summary.md`

RED 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_value_elevator_artifact_data_computes_missing_score_summary_fields tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_value_elevator_artifact_data_computes_score_summary_fields tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_value_elevator_without_model_score_totals tools/new-agents/backend/tests/test_agent_runtime.py::test_value_elevator_structured_output_instruction_requests_artifact_data_not_markdown -q
```

结果：`4 failed`，失败点为 `score_summary.total_score` / `average_score` 仍是 required、partial renderer 未输出评分章节、prompt 仍包含旧示例。

GREEN 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_value_elevator_artifact_data_computes_missing_score_summary_fields tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_value_elevator_artifact_data_computes_score_summary_fields tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_value_elevator_without_model_score_totals tools/new-agents/backend/tests/test_agent_runtime.py::test_value_elevator_structured_output_instruction_requests_artifact_data_not_markdown -q
```

结果：`4 passed`

聚焦回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

结果：`348 passed`

New Agents 验证：

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents 前端 `718 passed`；New Agents 后端 `601 passed, 1 deselected`。运行中出现既有 React `ArtifactPane.test.tsx` `act(...)` warning，但未导致测试失败。

全量验证：

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 和 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`；非沙箱重跑通过，关键结果包括 Intent Tester API `294 passed`、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `718 passed`、New Agents Backend `601 passed, 1 deselected`、New Agents Browser E2E `11 passed, 10 deselected`。

残余风险：

- 本轮只完成 `VALUE_DISCOVERY/ELEVATOR` 的评分汇总后端化，`TEST_DESIGN/CASES` 的用例统计、DELIVERY 的汇总和后续 ID / 引用一致性仍按第 4-8 轮推进。
- 本轮没有启用真实外部模型 smoke 或 LLM judge；该改动由确定性 schema / renderer / runtime / E2E 回归覆盖，不证明 DeepSeek 真实样本成功率已经提升到某个数值。

### 2026-07-08 第 4 轮：IDEA_BRAINSTORM/DEFINE 证据引用稳定化

已完成 `IDEA_BRAINSTORM/DEFINE` 根问题与证据一致性治理：

- `IdeaProblemLandscape` 新增 `root_problem_id`，`IdeaEvidenceItem` 新增 `related_problem_ids`，模型不再需要把 `root_problem` 原样复制到 evidence 或 problem-user-fit 文本中。
- 后端 validator 改为校验稳定 ID 引用图：root problem id 不能与 subproblem id 重复；evidence 只能引用 root 或已存在 subproblem；至少一条 evidence 必须支撑 root；problem-user-fit 必须引用支撑 root 的 evidence。
- 未知 problem id、缺少 root coverage、problem-user-fit 未引用 root evidence、未知 evidence id、重复 ID 和无 checked stage gate 仍显式 `ValidationError`，不生成假成功 artifact。
- DEFINE Markdown deterministic renderer 在问题域表中展示 root problem 行，并在证据表中展示“关联问题 ID”；partial renderer 在 evidence 引用未知 problem id 时停在上一段，不预览已知错误的证据章节。
- `IDEA_DEFINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` 已同步 `root_problem_id` / `related_problem_ids`，删除“原样包含 `problem_landscape.root_problem`”的脆弱要求。
- 本轮设计与执行计划已记录在：
  - `docs/superpowers/specs/2026-07-08-new-agents-idea-define-evidence-reference-design.md`
  - `docs/superpowers/plans/2026-07-08-new-agents-idea-define-evidence-reference.md`

RED 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_accepts_id_based_root_problem_coverage_without_exact_text_copy tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_rejects_unknown_related_problem_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_requires_root_problem_id_coverage tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_define_structured_output_instruction_explains_root_problem_coverage -q
```

结果：`4 failed`，失败点为 `root_problem_id` / `related_problem_ids` 尚不是 schema 或 prompt 的一部分。

补充 RED 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_define_artifact_data_skips_evidence_with_unknown_problem_reference -q
```

结果：`1 failed`，失败点为 partial renderer 会把未知 `related_problem_ids` 的证据表预览出来。

GREEN 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_accepts_id_based_root_problem_coverage_without_exact_text_copy tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_rejects_unknown_related_problem_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_requires_root_problem_id_coverage tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_define_structured_output_instruction_explains_root_problem_coverage -q
```

结果：`4 passed`

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_define_artifact_data_skips_evidence_with_unknown_problem_reference -q
```

结果：`1 passed`

DEFINE 聚焦回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_rejects_duplicate_evidence_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_rejects_duplicate_problem_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_rejects_unknown_fit_evidence_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_accepts_id_based_root_problem_coverage_without_exact_text_copy tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_rejects_unknown_related_problem_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_requires_root_problem_id_coverage tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_requires_fit_to_reference_root_problem_evidence tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_requires_checked_stage_gate tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_define_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_define_artifact_data_skips_evidence_with_unknown_problem_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_idea_define_artifact_data_is_deterministic_and_contract_valid tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_define_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_define_structured_output_instruction_explains_root_problem_coverage tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_define_artifact_data_before_final_output -q
```

结果：`14 passed`

聚焦后端回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

结果：`352 passed`

New Agents 验证：

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents 前端 `718 passed`；New Agents 后端 `605 passed, 1 deselected`。运行中出现既有 React `ArtifactPane.test.tsx` `act(...)` warning，但未导致测试失败。

全量验证：

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002`、Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`，并且曾卡在 `python -m playwright install chromium`；非沙箱重跑通过，关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `718 passed`、New Agents Backend `605 passed, 1 deselected`、New Agents Browser E2E `11 passed, 10 deselected`。

残余风险：

- 本轮只完成 `IDEA_BRAINSTORM/DEFINE` 的证据引用稳定化，不代表 `IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/DIVERGE`、`TEST_DESIGN/CASES` 或 `TEST_DESIGN/STRATEGY` 的引用/统计风险已解决。
- 本轮未启用真实外部模型 smoke 或 LLM judge；确定性测试证明脆弱 contract 已被 ID 引用替代，但不证明 DeepSeek 真实样本成功率已经提升到某个数值。
- 第 0 轮 DeepSeek tool calls 静态能力 spike 已补做；真实 provider smoke 因缺少 `DEEPSEEK_API_KEY` 未执行，后续若要启用 tool calls 仍需单独完成 toy schema live smoke 和 stream parser 验证。

### 2026-07-08 补做第 0 轮：DeepSeek tool calls 静态能力 spike

已完成 DeepSeek provider 能力边界澄清：

- 官方 Tool Calls 文档显示 DeepSeek 支持 OpenAI SDK 兼容的 `tools` 调用；strict tool calls 属于 beta 能力，需要 `/beta` base URL，并要求 function 开启 `strict=true`。
- 官方 Chat Completion 文档显示 `response_format.type` 只支持 `text` 和 `json_object`，不能直接照搬 OpenAI strict JSON Schema `response_format`。
- strict schema 子集不能完整覆盖当前 New Agents `artifact_data` contract：object 字段必须全部 required 且 `additionalProperties=false`，并且不支持 `minLength`、`maxLength`、`minItems`、`maxItems` 等约束；因此它不能替代 Pydantic validator、业务不变量和 deterministic renderer。
- 官方 streaming chunk 示例和 schema 未明确展示 `delta.tool_calls` 或 streaming tool arguments；只看到 stream delta 文本增量和 `finish_reason=tool_calls`。缺少真实 `DEEPSEEK_API_KEY`，本轮不声明 DeepSeek V4 Flash 已稳定支持 streaming tool arguments。
- 当前本地 `llm_client.py` 只消费 `delta.content`，且 `stream_chat_completion_content()` 不传 `tools` / `tool_choice`；`agent_runtime.py` 对 `deepseek-v4-*` 仍应保持 `json_object_only` 能力。
- 本轮结论：不把 tool calls 接入正式 workflow 主链路。若未来启用，必须先实现 shared provider capability registry、独立 tool-call stream event parser、mock fixture、toy live smoke 和 typed error 显式失败路径。
- 本轮设计与执行计划已记录在：
  - `docs/superpowers/specs/2026-07-08-new-agents-deepseek-tool-calling-capability-spike-design.md`
  - `docs/superpowers/plans/2026-07-08-new-agents-deepseek-tool-calling-capability-spike.md`

已验证：

```bash
curl -L -A Mozilla https://api-docs.deepseek.com/guides/tool_calls | rg -n "strict|Strict|Beta|tools|tool_choice|tool_calls|/beta|required|additionalProperties|minLength|maxLength|minItems|maxItems|Unsupported"
```

结果：确认官方 Tool Calls 页面、strict beta `/beta` 要求、object required / `additionalProperties=false` 约束，以及 string / array 的部分 unsupported 参数。

```bash
curl -L -A Mozilla https://api-docs.deepseek.com/api/create-chat-completion | rg -n "tools|tool_choice|tool_calls|response_format|json_object|chat.completion.chunk|finish_reason|delta|stream"
```

结果：确认 Chat Completion 文档中 `response_format` 为 `text` / `json_object`，stream chunk 示例为文本 delta，`finish_reason` 包含 `tool_calls`。

```bash
curl -L -A Mozilla https://api-docs.deepseek.com/guides/json_mode | rg -n "response_format|json_object|JSON|stream|must|Output"
```

结果：确认 JSON Output 使用 `response_format={'type':'json_object'}`，仍要求 prompt 明确要求 JSON，并提示空内容 / 截断风险。

```bash
if [ -n "$DEEPSEEK_API_KEY" ]; then echo present; else echo missing; fi
```

结果：`missing`，未调用外部模型端点。

残余风险：

- 本轮是官方文档 + 本地静态代码事实 spike，不是 live provider smoke；不证明真实 DeepSeek streaming tool arguments 可用或稳定。
- 当前治理主线仍应优先推进派生字段后端化、ID / 引用关系收敛、schema / prompt / contract 同步和高失败阶段纵切治理。

## 每轮验收口径

- 必须先写或更新失败测试，复现目标失败类别。
- 必须证明失败仍然显式暴露，不允许改成草稿成功、隐藏错误或跳过校验。
- 必须证明 JSON 截断、空内容、provider 中断和 schema/contract 校验失败不会产生最终成功帧。
- 必须证明最终 artifact 仍通过完整 schema、artifact contract、Mermaid / ai4se-visual contract 和相关下游解析。
- 必须证明复杂视觉产物不要求模型手写 Mermaid；若最终 artifact 包含 Mermaid，必须能追溯到后端 deterministic renderer，并通过 `mermaid.parse` 或等价渲染门禁。
- 必须证明 `ai4se-visual` block 在前端预览、PDF/DOCX 导出、run snapshot 恢复中都使用同一结构化解析逻辑，不得各自实现不一致 schema。
- 涉及 DeepSeek provider 能力时，必须明确当前走的是 `json_object_only`、tool calling、strict tool call 还是普通 PydanticAI structured output，不能把不同能力混写成一个“结构化输出”结论。
- 涉及 frontend 诊断时，必须有 chat service / diagnostic card 测试证明错误详情可见。
- 涉及真实模型 smoke 时，必须记录是否会向外部模型端点发送 workflow prompt、contract 或用户输入；如需外部调用，必须取得用户明确批准。

## 非目标

- 不通过降低 schema 严格性来提升成功率。
- 不使用未通过最终校验的 partial artifact、草稿、缓存旧 artifact 或 synthetic reveal 冒充成功；流式 delta 可以作为预览，但不能作为最终成功结果持久化或推进阶段。
- 不把 Mermaid repair、旧图缓存、前端 sanitizer 或导出降级文本当成成功路径。
- 不让模型直接输出 D2、Graphviz DOT、PlantUML 或其他图 DSL 来替代结构化视觉协议。
- 不因为模型失败而自动推进阶段。
- 不引入 workflow 专属 runtime、SSE endpoint、store 或渲染管线。
