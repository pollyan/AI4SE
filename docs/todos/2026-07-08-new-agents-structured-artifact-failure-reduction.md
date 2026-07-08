# New Agents 结构化产出失败治理待办

- 状态：执行中（第 0 轮 DeepSeek tool calls 静态能力 spike 已完成；第 1、2 轮已完成；第 3 轮首个 `VALUE_DISCOVERY/ELEVATOR` 派生字段纵切已完成；第 4 轮 `IDEA_BRAINSTORM/DEFINE` 证据引用纵切已完成；第 5 轮首个 `IDEA_BRAINSTORM/DIVERGE` 与 `CONVERGE` partial 引用门禁纵切已完成；第 6 轮 `TEST_DESIGN/CASES` 与 `TEST_DESIGN/STRATEGY` 纵切已完成；`IDEA_BRAINSTORM/CONVERGE` artifactDataContract 同步纵切已完成；第 7 轮首个 `INCIDENT_REVIEW/ROOT_CAUSE` `cause-map` 结构化视觉纵切已完成；Mermaid repair parse + artifact contract 双门禁已完成；前端正式 / partial artifact `ai4se-visual` 写入前校验已完成并全量验证通过；第 8A 轮 `artifact_data` 全阶段 fixture registry 回归门禁已完成并全量验证通过；第 8B 轮 `artifact_data` 字段来源与视觉协议矩阵已完成；第 8C 轮 `TEST_DESIGN/CASES` artifactDataContract manifest 同步已完成）
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
  - 进展：第 6 轮首个纵切已完成 `TEST_DESIGN/CASES.case_statistics` 后端派生。缺省统计由后端根据 `case_groups` 计算，显式错误统计仍触发 validation failure。

- [ ] 收敛 ID 与引用关系。（第 4-6 轮）
  - 目标：后端生成稳定 ID，或在 renderer/normalizer 中确定性分配 ID；模型不再负责维护容易漂移的跨表引用。
  - 重点阶段：`IDEA_BRAINSTORM/DEFINE` 的 evidence 引用，`IDEA_BRAINSTORM/CONVERGE` 的 idea / rank / recommended idea 引用，`TEST_DESIGN/CASES` 的 requirement / risk / case 覆盖引用。
  - 进展：第 4 轮已完成 `IDEA_BRAINSTORM/DEFINE` 的 root problem / evidence / problem-user-fit ID 引用治理；第 5 轮首个纵切已完成 `IDEA_BRAINSTORM/DIVERGE` 与 `CONVERGE` partial preview 的跨引用门禁，避免流式右侧产物预览已知错误章节；第 6 轮已完成 `TEST_DESIGN/CASES` 的 `automation_candidates.case_id` / `coverage_trace.covered_cases` case_id 引用门禁，以及 `TEST_DESIGN/STRATEGY` 的 `QG/R/TS/TP` 内部 ID 唯一性与引用门禁。更广泛的后端确定性 ID 分配仍未完成。

- [ ] 建立 schema / prompt / contract 单源同步机制。（横切，第 3-8 轮）
  - 目标：Pydantic validators、structured output instruction、workflow manifest visual contract、frontend prompt 不再各写一套约束。
  - 验收：新增 contract sync 测试，证明关键不变量在 prompt 和后端 validator 中同时存在。
  - 进展：已完成 `IDEA_BRAINSTORM/CONVERGE` 首个 `artifactDataContract` 同步纵切。CONVERGE 的关键 artifact_data 不变量已进入 `workflow_manifest.json`，后端 structured output instruction 和前端 stage prompt 均从 manifest 生成同步约束，并由 backend / frontend 同步测试保护。
  - 进展：第 8C 轮已完成 `TEST_DESIGN/CASES` `artifactDataContract` manifest 同步。CASES 的 `case_statistics` 后端派生、case_id 唯一性、`automation_candidates.case_id` / `coverage_trace.covered_cases` 引用门禁、禁止模型输出 renderer-owned Markdown / `ai4se-visual` 产物等关键约束已进入 manifest，并由 backend instruction sync、runtime instruction 和 frontend prompt tests 保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/CONVERGE` 与 `TEST_DESIGN/CASES` 外，其余 23 个阶段尚未迁移。

- [ ] 针对高失败阶段做纵切专项修复。（第 4-6 轮）
  - 优先顺序：`IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/CONVERGE`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY`、`IDEA_BRAINSTORM/DIVERGE`。
  - 目标：每个阶段都有失败复现、根因定位、最小 schema 设计修复和回归测试。
  - 进展：第 4 轮已完成 `IDEA_BRAINSTORM/DEFINE` 的已知 root-problem 覆盖失败模式修复；第 5 轮首个纵切已完成 `DIVERGE` / `CONVERGE` partial preview 与 final validator 关键引用不变量对齐；第 6 轮已完成 `CASES` 的用例统计后端化与 partial case_id 引用门禁，以及 `STRATEGY` 的内部引用门禁。第 8C 轮进一步把 CASES 的核心 artifact_data 约束迁入 manifest，并清理前端 prompt 中要求模型手写 Markdown 表格 / `ai4se-visual` block 的旧冲突描述。

- [ ] 增加结构化失败回归门禁。（第 8 轮）
  - 目标：高失败阶段必须有固定 fixture / raw JSON stream / renderer contract 测试，确保不会再次因为已知不变量触发 `SCHEMA_VALIDATION_FAILED`。
  - 验收：纳入 `./scripts/test/test-local.sh new-agents` 或明确的 New Agents backend regression suite。
  - 进展：第 8A 轮已建立 `ARTIFACT_DATA_STAGE_FIXTURES` 全阶段测试登记表，当前覆盖全部 `supports_artifact_data_rendering()` 支持的 25 个在线阶段；每个 registry fixture 都必须通过 deterministic renderer 和 `validate_agent_turn()`。`test_agent_runtime.py` 的 artifact-data instruction 顺序矩阵已改为从 registry 派生，避免新增阶段时漏掉 raw JSON visible streaming 门禁。`test_workflow_contract_sync.py` 已反向校验 `workflow_manifest.json` 的 `visualContract` 与后端 required Mermaid / structured visual maps 完全一致。
  - 进展：第 8B 轮已在 `docs/TESTING.md` 补齐 25 个在线阶段的模型输出字段 / 后端派生字段 / 视觉协议来源矩阵，明确 validation-only 与 backend-derived 的边界，并记录当前已完成 `artifactDataContract` manifest 同步迁移的阶段为 `IDEA_BRAINSTORM/CONVERGE` 与 `TEST_DESIGN/CASES`。
  - 进展：第 8C 轮已新增 `TEST_DESIGN/CASES` 的 backend manifest contract sync、runtime instruction source 和 frontend prompt sync 回归测试；相关 CASES renderer / 引用门禁测试继续通过。

- [ ] 建立视觉产物协议分层。（第 7 轮）
  - 目标：明确哪些视觉类型必须走 `ai4se-visual` JSON，哪些 Mermaid 类型允许由后端 deterministic renderer 生成，哪些 DSL 禁止模型直接输出。
  - 初始策略：复杂图和业务图默认走 `ai4se-visual`；Mermaid 只允许作为后端从结构化数据生成的简单图编译目标；不引入 D2、Graphviz 或 PlantUML 作为运行时主协议，除非后续有单独架构批准。
  - 验收：`workflow_manifest.json`、`agent_contracts.py`、structured output instruction 和前端模板对每个在线阶段的视觉协议一致。

- [ ] 扩展 `ai4se-visual` 类型覆盖复杂图。（第 7 轮）
  - 目标：在现有 `score-matrix`、`coverage-map`、`journey-map` 等表格类视觉之外，补齐 `flow-map`、`timeline-map`、`mindmap`、`sequence-flow`、`distribution-chart` 等数据结构，使复杂图不再依赖模型手写 Mermaid。
  - 约束：每个 visual 类型必须有严格 schema、引用完整性校验、前端渲染组件、导出降级文本和失败诊断。
  - 验收：至少选一个 Mermaid 失败高风险阶段完成纵切迁移，并证明最终 artifact 不含模型手写 Mermaid。
  - 进展：已完成首个复杂图纵切 `INCIDENT_REVIEW/ROOT_CAUSE.cause-map`。该 visual type 已从 `columns/rows` 表格协议迁移为 `nodes/edges`，并覆盖后端 deterministic renderer、后端 contract 校验、前端 parser、前端组件、PDF/DOCX 导出降级和模板同步测试。更广泛的 `flow-map`、`timeline-map`、`mindmap`、`sequence-flow` 等类型仍未迁移。

- [ ] 建立视觉渲染强校验门禁。（第 7 轮）
  - 目标：正式 artifact 被呈现为成功、持久化和阶段推进前，必须通过 Mermaid / `ai4se-visual` 视觉校验；若运行时校验暂不能放在 backend，则必须先以 CI / renderer fixture / frontend parse 形成可执行门禁，并在运行时失败时显式诊断。
  - Mermaid 校验：允许的 Mermaid block 必须通过 `mermaid.parse` 或等价校验；CI 或回归套件可增加 `mmdc` 渲染 SVG 门禁，覆盖浏览器能 parse 但导出失败的情况。
  - `ai4se-visual` 校验：JSON 必须合法，`type` 必须受支持，columns / rows / nodes / edges / events 等结构必须完整，引用目标必须存在。
  - 验收：新增测试证明视觉校验失败会显式报错，不产生成功 `agent_turn`、不持久化 artifact、不推进 stage。
  - 进展：已完成前端写入前视觉 gate。`llm.ts` 在 final `agent_turn`、合成 artifact reveal 和真实 `agent_delta` partial 写出 chunk 前统一校验 Mermaid 与 `ai4se-visual`；`structuredVisuals.ts` 复用共享 parser 校验所有 fenced `ai4se-visual` block；`chatService.ts` 将结构化视觉校验失败归类为结构化输出生成失败并保持右侧产物不变。后续仍可补 CI / `mmdc` 渲染门禁和更广泛的 backend 运行时 Mermaid parse。

- [x] 收紧 Mermaid repair 的架构边界。（第 7 轮）
  - 目标：`/api/utils/mermaid/repair` 和前端 retry 只能作为用户显式触发的修复辅助，不能自动替换正式 artifact、不能绕过 contract、不能让失败状态变成成功。
  - 验收：测试证明 repair 结果必须重新经过 Mermaid parse / artifact contract 校验；repair 失败继续显式展示，不隐藏原始错误。
  - 进展：已完成前端 `retryMermaidGeneration()` parse gate；ArtifactPane 发起 repair 时会把 `workflowId`、`stageId` 和当前完整 artifact 一起提交给共享 `/api/utils/mermaid/repair`，后端替换候选 Mermaid block 后复用 `validate_agent_turn` 做完整 artifact contract 校验。ChatPane 不替换 artifact，只保留 Mermaid parse gate。失败时 service 返回 `null`，父组件不写入 artifact/message，原始错误状态继续保留。

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
- 本轮设计与执行要点已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。

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
- 本轮设计与执行要点已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
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
- 本轮设计与执行要点已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
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
- 本轮设计与执行要点已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
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

### 2026-07-08 第 5 轮首个纵切：IDEA DIVERGE / CONVERGE partial 引用门禁

已完成 `IDEA_BRAINSTORM/DIVERGE` 与 `IDEA_BRAINSTORM/CONVERGE` partial artifact preview 的引用一致性治理：

- 抽取 DIVERGE final validator 的 idea card、landscape、source、parked record 校验 helper，并在 partial renderer 中复用。
- 抽取 CONVERGE final validator 的 ICE evaluation、decision matrix、recommended idea、validation experiment、merge path 校验 helper，并在 partial renderer 中复用。
- DIVERGE partial 在 `idea_sources.idea_ids` 引用未知 idea 时停在“创意卡片库”，不再预览“创意来源与假设”。
- CONVERGE partial 在 `recommended_idea_id` 未知或 ICE score 不一致时直接不生成 partial；在 validation experiment 或 merge path 引用未知 idea 时停在上一段可信章节。
- 最终 artifact schema 和 validator 严格性不降低，错误仍通过 final validation 显式暴露。
- 本轮设计与执行要点已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
RED 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_diverge_artifact_data_skips_sources_with_unknown_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_rejects_unknown_recommended_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_rejects_invalid_ice_score tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_skips_validation_experiments_with_unknown_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_skips_merge_paths_with_unknown_idea_reference -q
```

结果：`5 failed`，失败点均为旧 partial renderer 会预览未知引用或错误 ICE score 对应的章节。

GREEN 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_diverge_artifact_data_skips_sources_with_unknown_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_rejects_unknown_recommended_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_rejects_invalid_ice_score tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_skips_validation_experiments_with_unknown_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_skips_merge_paths_with_unknown_idea_reference -q
```

结果：`5 passed`

IDEA 聚焦回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_diverge_artifact_data_rejects_duplicate_idea_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_diverge_artifact_data_rejects_unknown_source_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_diverge_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_diverge_artifact_data_skips_sources_with_unknown_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_converge_artifact_data_rejects_invalid_ice_score tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_converge_artifact_data_rejects_unknown_recommended_idea tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_converge_artifact_data_rejects_unknown_validation_experiment_idea tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_converge_artifact_data_rejects_unknown_merge_path_idea tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_rejects_unknown_recommended_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_rejects_invalid_ice_score tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_skips_validation_experiments_with_unknown_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_skips_merge_paths_with_unknown_idea_reference tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output -q
```

结果：`15 passed`

聚焦后端回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

结果：`357 passed`

New Agents 验证：

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents 前端 `718 passed`；New Agents 后端 `610 passed, 1 deselected`。运行中出现既有 React `ArtifactPane.test.tsx` `act(...)` warning，但未导致测试失败。

全量验证：

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002`、Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`，并且曾卡在 `python -m playwright install chromium`；非沙箱重跑通过，关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `718 passed`、New Agents Backend `610 passed, 1 deselected`、New Agents Browser E2E `11 passed, 10 deselected`。

残余风险：

- 本轮只处理 DIVERGE / CONVERGE partial preview 与 final validator 的关键引用不变量对齐，不代表 `TEST_DESIGN/CASES` 的 requirement / risk / case 覆盖引用已经治理。
- 本轮没有改变 prompt / schema / contract 单源同步机制；CONVERGE prompt 是否充分表达这些不变量仍按后续横切项处理。

### 2026-07-08 第 6 轮首个纵切：TEST_DESIGN CASES 统计后端化与 case_id 引用门禁

已完成 `TEST_DESIGN/CASES` 的用例统计后端化与 case_id 引用门禁：

- `CasesArtifactData.case_statistics` 改为可选输入；模型缺省时由后端根据 `case_groups[].cases[].priority` 派生 `total`、`p0_count`、`p1_count`、`p2_count`。
- 如果模型仍输出显式错误的 `case_statistics`，后端继续触发 `ValidationError`，不会静默覆盖成成功。
- `automation_candidates.case_id` 与 `coverage_trace.covered_cases` 纳入同一 case_id 引用门禁，未知 `case_id` 在 final validation 中显式失败。
- CASES partial renderer 不再把 `case_statistics` 当作首个流式章节；只有 `design_bases + case_groups` 到齐后才输出后端派生统计、设计依据和用例清单。
- CASES partial renderer 在自动化候选或覆盖追溯引用未知用例时停在上一段可信章节，不预览最终 validator 会拒绝的章节。
- `CASES_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` 与前端 CASES prompt 已同步：模型不需要输出用例统计数量，后端根据用例清单计算。
- 本轮设计与执行要点已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
RED 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_derives_statistics_when_missing tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_automation_candidate_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_derives_statistics_from_case_groups tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_skips_automation_candidates_with_unknown_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_skips_coverage_trace_with_unknown_case_reference tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_omits_derived_statistics tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_cases_after_case_groups_without_model_statistics -q
```

结果：`7 failed`，失败点分别为旧 schema 要求 `case_statistics` 必填、旧 validator 不拒绝未知 `automation_candidates.case_id`、旧 partial renderer 不能在缺省统计时从 `case_groups` 派生统计、旧 prompt 仍要求输出 `"case_statistics"`、旧 raw streaming 在缺省统计时 final validation 失败。

GREEN 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_derives_statistics_when_missing tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_automation_candidate_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_derives_statistics_from_case_groups tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_skips_automation_candidates_with_unknown_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_skips_coverage_trace_with_unknown_case_reference tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_omits_derived_statistics tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_cases_after_case_groups_without_model_statistics -q
```

结果：`7 passed`

CASES 聚焦回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_inconsistent_statistics tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_coverage_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_cases_artifact_data_is_contract_valid_and_asset_parseable tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data -q
```

结果：`8 passed`

后端共享回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

结果：`364 passed`

New Agents 验证：

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents Frontend `718 passed`；New Agents Backend `617 passed, 1 deselected`。运行中出现既有 React `ArtifactPane.test.tsx` `act(...)` warning，但未导致测试失败。

全量验证：

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002`、Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`，并且曾卡在 `python -m playwright install chromium`；非沙箱重跑中，Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `718 passed`、New Agents Backend `617 passed, 1 deselected`，但 Browser E2E 在 `test_lisa_final_artifact_passes_optional_llm_judge` 的 fixture setup 阶段出现一次 `page.goto(http://127.0.0.1:64656/new-agents/)` 超时，发生在测试体内 skip 逻辑之前。

Browser E2E 复跑：

```bash
.venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q
```

结果：`11 passed, 10 deselected`

残余风险：

- 本轮不做跨阶段 `STRATEGY.test_points` 到 `CASES.test_point` 的强 ID 校验；当前 `CASES.test_point` 是自由文本，不是结构化 `point_id`，需要后续单独改上游数据形态。
- 本轮不改 Lisa 测试资产解析、测试资产编辑 API 或 Header 测试资产面板。
- `test_data_environments.related_cases` 仍是自由文本，未纳入结构化 case_id 引用门禁。

### 2026-07-08 第 6 轮第二个纵切：TEST_DESIGN STRATEGY 内部引用门禁

已完成 `TEST_DESIGN/STRATEGY` 的 `QG/R/TS/TP` 内部引用门禁：

- `StrategyArtifactData` 增加 after validator，校验 `quality_goals.goal_id`、`risks.risk_id`、`test_techniques.technique_id`、`test_points.point_id` 不重复。
- `test_points.quality_goal`、`test_points.risk`、`test_points.technique` 必须引用同一 artifact_data 中已存在的 `QG/R/TS`。
- `test_techniques.target`、`test_techniques.applies_to`、`test_layers.related` 必须引用同一 artifact_data 中已存在的 `QG/R/TP`。
- STRATEGY partial renderer 不再单独提前展示测试技术或测试分层；章节 4-6 必须等 `test_techniques + test_layers + test_points` 到齐并通过引用校验后一起展示。
- 当章节 4-6 出现未知引用时，partial renderer 停在上一段可信章节，不预览最终 validator 会拒绝的内容。
- STRATEGY 后端 structured output instruction 与前端 prompt 已同步：模型必须复用当前策略蓝图中已经定义的 `QG/R/TS/TP` ID。
- 现有 STRATEGY 测试 fixture 已补齐 `TP-002`、`TP-003`，修复历史 fixture 中分层策略引用未定义测试点的问题。
- 本轮设计与执行要点已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
RED 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_duplicate_strategy_ids tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_unknown_test_point_references tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_unknown_technique_and_layer_references tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_strategy_artifact_data_waits_for_references_before_sections_four_to_six tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_strategy_artifact_data_skips_sections_four_to_six_with_unknown_reference tools/new-agents/backend/tests/test_agent_runtime.py::test_strategy_structured_output_instruction_requests_internal_id_references tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_waits_for_strategy_references_before_sections_four_to_six -q
```

结果：`6 failed, 1 passed`，失败点分别为旧 validator 不拒绝重复 / 未知引用、旧 partial renderer 提前展示章节 4-5、旧 prompt 缺少内部引用规则。raw streaming 用例在旧实现下已通过，因为旧流式分块只观察到了最终完整状态。

GREEN 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_duplicate_strategy_ids tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_unknown_test_point_references tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_unknown_technique_and_layer_references tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_strategy_artifact_data_waits_for_references_before_sections_four_to_six tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_strategy_artifact_data_skips_sections_four_to_six_with_unknown_reference tools/new-agents/backend/tests/test_agent_runtime.py::test_strategy_structured_output_instruction_requests_internal_id_references tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_waits_for_strategy_references_before_sections_four_to_six -q
```

结果：`7 passed`

STRATEGY 聚焦回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_inconsistent_rpn tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_computes_missing_rpn_for_generated_visuals tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_mermaid_labels_are_normalized_for_special_characters tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_strategy_artifact_data_is_deterministic_and_contract_valid tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_strategy_artifact_data_without_model_rpn tools/new-agents/backend/tests/test_agent_runtime.py::test_strategy_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_strategy_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_strategy_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data -q
```

结果：`10 passed`

后端共享回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

结果：`371 passed`

New Agents 验证：

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents Frontend `718 passed`；New Agents Backend `624 passed, 1 deselected`。运行中仍出现既有 React `ArtifactPane.test.tsx` `act(...)` warning，但未导致测试失败。

全量验证：

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 与 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`，属于端口 / 浏览器权限环境限制。

非沙箱第一次重跑中，Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `718 passed`、New Agents Backend `624 passed, 1 deselected`，但 Browser E2E 的 `test_alex_final_artifact_passes_optional_llm_judge` 得分 `75`，低于目标模式默认通过线 `80`。

补充质量门修复：

- `tests/e2e/new_agents_browser/sse_mock.py` 的 Alex `VALUE_DISCOVERY/BLUEPRINT` mock 需求蓝图补充分析方法与边界、优先级取舍依据、交付后复盘闭环、交互验收条件和交付后复盘覆盖率指标。
- `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md` 已记录这次 Alex 需求蓝图 LLM Judge 证据补强。

复验：

```bash
.venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py::test_alex_final_artifact_passes_optional_llm_judge -q
```

结果：`1 passed`

非沙箱第二次全量重跑：

```bash
./scripts/test/test-local.sh all
```

结果：通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `718 passed`、New Agents Backend `624 passed, 1 deselected`、New Agents Browser E2E `11 passed, 10 deselected`。

残余风险：

- 本轮只校验 STRATEGY artifact_data 内部的 `QG/R/TS/TP` 引用，不校验 `quality_goals.source`、`risks.source` 到 CLARIFY 阶段的事实 / 规则 / 链路 ID。
- 本轮不改变 `TEST_DESIGN/CASES.test_point` 仍为自由文本的上游消费形态；跨阶段 `STRATEGY.test_points` 到 `CASES` 的强 ID 链路仍需后续单独治理。
- 本轮不做后端确定性 ID 分配，只拒绝模型输出中的重复 ID 和未知引用。

### 2026-07-08 第 6 轮补充横切：IDEA_BRAINSTORM CONVERGE artifactDataContract 同步

已完成 `IDEA_BRAINSTORM/CONVERGE` 的首个 schema / prompt / contract 单源同步纵切：

- `workflow_manifest.json` 的 CONVERGE stage 新增 `artifactDataContract`，声明模型必须遵守的 artifact_data 关键不变量、禁止直接输出的产物形态，以及后端负责确定性渲染的产物。
- 后端 `workflow_manifest.py` 新增 stage 查询、artifactDataContract 读取和 instruction formatter。
- 后端 `IDEA_CONVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` 复用 manifest formatter，不再手写同一组 CONVERGE 约束句。
- 前端 `workflowRegistry.ts` 扩展 manifest stage 类型，`workflows.ts` 在构建 `WORKFLOWS` 时把同一份 manifest contract guidance 追加到 stage description。
- Pydantic validator、partial renderer、raw JSON streaming、typed SSE、run persistence、frontend store 和 ArtifactPane 均未新增 CONVERGE 专属分支。

RED 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_converge_artifact_data_contract_manifest_drives_backend_instruction tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_converge_structured_output_instruction_uses_manifest_artifact_data_contract -q
```

结果：后端选中测试在 collection 阶段失败，因为 `workflow_manifest` 尚未导出 `format_artifact_data_contract_instruction`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "appends manifest artifact data contract guidance"
```

结果：前端选中测试失败，因为 CONVERGE description 尚未包含 `【artifact_data 契约同步约束】`。

GREEN 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_converge_artifact_data_contract_manifest_drives_backend_instruction tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_converge_structured_output_instruction_uses_manifest_artifact_data_contract -q
```

结果：`2 passed`

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "appends manifest artifact data contract guidance"
```

结果：`1 passed`

聚焦后端回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_converge_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_converge_structured_output_instruction_uses_manifest_artifact_data_contract tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_rejects_unknown_recommended_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_rejects_invalid_ice_score tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_skips_validation_experiments_with_unknown_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_skips_merge_paths_with_unknown_idea_reference -q
```

结果：`19 passed`

聚焦前端回归：

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts
```

结果：`16 passed`

New Agents 验证：

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents Frontend `719 passed`；New Agents Backend `626 passed, 1 deselected`。运行中仍出现既有 React `ArtifactPane.test.tsx` `act(...)` warning，但未导致测试失败。

全量验证：

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 与 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`，属于端口 / 浏览器权限环境限制。非沙箱重跑通过，退出码 `0`；关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `719 passed`、New Agents Backend `626 passed, 1 deselected`、New Agents Browser E2E `11 passed, 10 deselected`。

残余风险：

- 本轮只迁移 CONVERGE 的 artifactDataContract，不代表所有 artifact_data stage 已完成 schema / prompt / contract 单源同步。
- manifest 中的 contract 是模型提示和同步测试的配置源，不能替代 Pydantic validators；后端 validators 仍是最终门禁。
- 本轮不处理第 7 轮视觉协议稳定化，不改变 Mermaid / `ai4se-visual` 的运行时校验策略。

### 2026-07-08 第 7 轮首个纵切：INCIDENT_REVIEW ROOT_CAUSE cause-map 结构化视觉

已完成 `INCIDENT_REVIEW/ROOT_CAUSE` 的 `cause-map` 节点 / 边结构化视觉纵切：

- 后端 `_render_incident_why_chain()` 继续从结构化 `artifact_data.why_chain` 确定性生成视觉数据，但 `cause-map` block 已从 `columns/rows` 改为 `nodes/edges`。
- 后端 `agent_contracts.py` 对 `cause-map` 使用节点 / 边 contract 校验，拒绝缺失节点引用；其他 `ai4se-visual` 类型继续沿用矩阵 `columns/rows` 校验。
- 前端 `parseStructuredVisual()` 支持 `matrix` 与 `node-edge` 两种 shape，`StructuredVisual` 对 `cause-map` 渲染为非表格节点链路视图。
- PDF / DOCX 导出层按 `visual.kind` 分流，`cause-map` 导出为可读节点和连接文本，不再假设所有结构化视觉都有 `columns/rows`。
- `ROOT_CAUSE_TEMPLATE` 和后端模板同步测试已改为要求 `cause-map` 使用 `nodes/edges` 协议。
- 本轮设计与执行要点已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
RED 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_incident_root_cause_artifact_data_builds_formal_incremental_markdown_and_patch -q
```

结果：旧 renderer 仍输出 `columns/rows`，新增 `nodes/edges` 断言失败。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx -t "cause-map|ROOT_CAUSE"
```

结果：旧 parser 要求 `cause-map` 使用 `columns/rows`，新增节点 / 边解析和模板协议测试失败。

GREEN 与聚焦回归：

```bash
npm run lint
```

结果：`tsc --noEmit` 通过。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_incident_root_cause_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_incident_root_cause_artifact_data_is_deterministic_and_contract_valid tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_incident_root_cause_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_incident_root_cause_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_frontend_templates_include_required_structured_visual_contract_examples -q
```

结果：`99 passed`

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx src/components/__tests__/ArtifactPane.test.tsx src/core/__tests__/artifactExport.test.ts src/core/__tests__/docxExport.test.ts
```

结果：`182 passed`。运行中仍出现既有 React `ArtifactPane.test.tsx` `act(...)` warning，但未导致测试失败。

New Agents 验证：

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents Frontend `724 passed`；New Agents Backend `627 passed, 1 deselected`。运行中仍出现既有 React `ArtifactPane.test.tsx` `act(...)` warning，但未导致测试失败。

全量验证：

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 与 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`，属于端口 / 浏览器权限环境限制。

非沙箱重跑：

```bash
/bin/zsh -lc './scripts/test/test-local.sh all > /private/tmp/ai4se-cause-map-full-all.log 2>&1; rc=$?; tail -120 /private/tmp/ai4se-cause-map-full-all.log; echo EXIT_STATUS:$rc; exit $rc'
```

结果：通过，退出码 `0`。关键结果包括 Intent Tester API `294 passed`、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `724 passed`、New Agents Backend `627 passed, 1 deselected`、New Agents Browser E2E `11 passed, 10 deselected`。

残余风险：

- 本轮只迁移 `cause-map` 一个复杂视觉类型，不代表 `flow-map`、`timeline-map`、`mindmap`、`sequence-flow` 等复杂图协议已经完成。
- ROOT_CAUSE 的鱼骨图 Mermaid mindmap 本轮仍保留为后端 deterministic renderer 输出；未迁移为新的结构化 `mindmap` visual。
- 本轮建立的是前后端 contract / renderer / 导出回归门禁；正式 artifact 持久化前的运行时视觉 parse 门禁仍需后续第 7 轮继续收紧。

### 2026-07-08 第 7 轮补充：ROOT_CAUSE cause-map contract prompt 同步

已关闭上一轮后发现的 `cause-map` contract prompt 矛盾：后端 `build_artifact_contract_prompt()` 现在要求 `nodes/edges` 节点 / 边协议，不再提示旧 `columns/rows` 表格示例。

RED 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py::test_build_artifact_contract_prompt_requires_cause_map_node_edge_contract -q
```

结果：失败符合预期。旧 prompt 不包含 `"nodes"`，因为 `STRUCTURED_VISUAL_SCHEMA_PROMPTS["cause-map"]` 仍使用 `columns/rows` 示例。

GREEN 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py::test_build_artifact_contract_prompt_requires_cause_map_node_edge_contract -q
```

结果：`1 passed`

聚焦后端契约回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_contract_registry.py -q
```

结果：`109 passed`

New Agents 验证：

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents Frontend `724 passed`；New Agents Backend `628 passed, 1 deselected`。运行中仍出现既有 React `ArtifactPane.test.tsx` `act(...)` warning，但未导致测试失败。

提交前全量验证与验证阻塞处理：

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 与 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`，属于端口 / 浏览器权限限制。

非沙箱全量重跑先后暴露 New Agents Browser E2E setup 阶段 `Page.goto` / `Page.reload` 默认 `load` 等待超时；同一 E2E 套件单独非沙箱运行通过，证明应用工作流可跑通，失败集中在 fixture 等待条件。已同步修复 `tests/e2e/new_agents_browser/conftest.py`：打开 New Agents 首页时等待 `domcontentloaded`，再等待 `选择你的 AI 助手` 标题出现，不再把浏览器 `load` 事件作为 React 首页可交互证据。

```bash
/bin/zsh -lc './scripts/test/test-local.sh e2e > /private/tmp/ai4se-e2e-domcontentloaded.log 2>&1; rc=$?; tail -120 /private/tmp/ai4se-e2e-domcontentloaded.log; echo EXIT_STATUS:$rc; exit $rc'
```

结果：通过，退出码 `0`；New Agents Browser E2E `11 passed, 10 deselected`。

```bash
/bin/zsh -lc './scripts/test/test-local.sh all > /private/tmp/ai4se-cause-map-contract-prompt-full-all-after-e2e-fix.log 2>&1; rc=$?; tail -160 /private/tmp/ai4se-cause-map-contract-prompt-full-all-after-e2e-fix.log; echo EXIT_STATUS:$rc; exit $rc'
```

结果：通过，退出码 `0`。关键结果包括 Intent Tester API `294 passed`、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `724 passed`、New Agents Backend `628 passed, 1 deselected`、New Agents Browser E2E `11 passed, 10 deselected`。

残余风险：

- 本轮只同步 `cause-map` 的 backend artifact contract prompt，不改变其他结构化视觉类型的 schema prompt。
- 本轮不迁移 ROOT_CAUSE 的 Mermaid mindmap，也不实现运行时 Mermaid parse 门禁。

### 2026-07-08 第 7 轮补充：Mermaid repair parse 与 artifact contract 双门禁

已完成：

- 前端 `retryMermaidGeneration()` 在接收 repair endpoint 返回后，会先用现有 Mermaid sanitizer 规范化代码，再调用 `mermaid.parse(..., { suppressErrors: false })`；parse 异常、空代码或 parse 返回 `false` 都返回 `null`，调用方不会替换 Markdown。
- `ArtifactPane` 发起 Mermaid retry 时会传入当前 `workflowId`、`stageId` 和完整 `artifactContent`；`ChatPane` 不传 artifact context，只保留 Mermaid parse gate。
- 后端 `MermaidRepairRequest` 支持可选 artifact contract context，并要求 `workflowId`、`stageId`、`currentArtifact` 和 `blockIndex` 成组出现；workflow/stage 不匹配会显式 400。
- `/api/utils/mermaid/repair` 在有 artifact context 时，会将修复后的 Mermaid code 替换进候选完整 artifact，并复用共享 `AgentTurnOutput` / `validate_agent_turn` 校验当前 workflow/stage 的 artifact contract。contract 失败返回 JSON error，不返回可写入的 `repairedCode`。
- 本轮继续复用共享 repair endpoint、ArtifactPane、Mermaid component 和 backend contract；未新增 Lisa/Alex/workflow 专属 runtime、API、store 或渲染管线。
- 只读 explorer `Tesla` 已审查 repair 调用路径，确认仅前端 parse 不足以覆盖 artifact contract，本轮已据此补齐后端 contract gate。

RED 验证：

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/mermaidRetryService.test.ts
```

结果：修复前 `4 failed, 1 passed`。失败证明 service 没有调用 `mermaid.parse`、没有发送 artifact context，并会返回仍无法 parse 的 repaired code。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_request_schemas.py::test_parse_mermaid_repair_request_accepts_artifact_contract_context tools/new-agents/backend/tests/test_request_schemas.py::test_parse_mermaid_repair_request_requires_complete_artifact_contract_context tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py::test_mermaid_repair_validates_candidate_artifact_contract tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py::test_mermaid_repair_rejects_candidate_when_artifact_contract_fails -q
```

结果：修复前 `5 failed, 1 passed`。失败证明 schema 忽略 artifact context，endpoint 未拦截破坏 contract 的 repair 结果。

GREEN 与聚焦回归：

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/mermaidRetryService.test.ts
```

结果：`5 passed`

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_request_schemas.py::test_parse_mermaid_repair_request_accepts_artifact_contract_context tools/new-agents/backend/tests/test_request_schemas.py::test_parse_mermaid_repair_request_requires_complete_artifact_contract_context tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py::test_mermaid_repair_validates_candidate_artifact_contract tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py::test_mermaid_repair_rejects_candidate_when_artifact_contract_fails -q
```

结果：`6 passed`

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "passes workflow, stage and current artifact context"
```

结果：`1 passed, 149 skipped`

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/mermaidRetryService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/ArtifactPane.test.tsx src/core/__tests__/llm.test.ts
```

结果：`272 passed`。运行中仍出现既有 React `ArtifactPane.test.tsx` `act(...)` warning，但未导致测试失败。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_request_schemas.py tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

结果：`131 passed`

New Agents 批量验证：

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents Frontend `728 passed`；New Agents Backend `634 passed, 1 deselected`。运行中仍出现既有 React `ArtifactPane.test.tsx` `act(...)` warning，但未导致测试失败。

全量验证：

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 与 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`，属于端口 / 浏览器权限限制；脚本被中断前已完成 Intent Tester API、代码质量、Common Frontend、New Agents Frontend / Backend，Browser E2E 因 Chromium 权限失败。

非沙箱重跑：

```bash
/bin/zsh -lc './scripts/test/test-local.sh all > /private/tmp/ai4se-mermaid-repair-full-all.log 2>&1; rc=$?; tail -160 /private/tmp/ai4se-mermaid-repair-full-all.log; echo EXIT_STATUS:$rc; exit $rc'
```

结果：通过，退出码 `0`。关键结果包括 Intent Tester API `294 passed`、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `728 passed`、New Agents Backend `634 passed, 1 deselected`、New Agents Browser E2E `11 passed, 10 deselected`。

残余风险：

- 本轮只收紧用户显式触发的 Mermaid repair 边界，不迁移其他复杂视觉类型到 `ai4se-visual`。
- Backend 仍不执行 Mermaid JS parse；parse gate 由前端 Mermaid runtime 承担，artifact contract gate 由后端承担。
- 更广泛的正式 artifact 视觉运行时门禁和 CI / `mmdc` 渲染门禁仍属于第 7 轮后续视觉稳定化候选。

### 2026-07-08 第 7 轮补充：artifact `ai4se-visual` 写入前校验

已完成：

- `structuredVisuals.ts` 新增 `extractStructuredVisualBlocks()` 与 `validateStructuredVisualBlocks()`，提取 Markdown 中所有 fenced `ai4se-visual` block，并复用 `parseStructuredVisual()` 校验 JSON、受支持类型、矩阵 `columns/rows`、`cause-map` `nodes/edges` 与边引用。
- `llm.ts` 将 artifact 视觉校验收敛为 `validateArtifactVisualBlocks()`，final `agent_turn`、有 `agent_delta` 后的 artifact reveal 和真实 `agent_delta` partial 都会在 yield chunk 前校验 `ai4se-visual` 与 Mermaid。
- `chatService.ts` 已将 `Artifact structured visual validation failed` 归类为结构化输出生成失败。失败时左侧显示恢复消息，右侧产物保持不变；无效 partial 不会写入 ArtifactPane / store。
- E2E SSE mock 中历史遗留的数组行 `rows: [[...]]` 已改为当前 `ai4se-visual` 矩阵协议要求的列名对象行 `rows: [{"列名": "..."}]`，避免强校验启用后被测试数据中的弱契约阻断。
- 本轮继续复用共享 typed Agent Runtime、`llm.ts`、`chatService`、Zustand store、ArtifactPane 和 `StructuredVisual` parser；未新增 Lisa/Alex/workflow 专属 runtime、API、store 或渲染管线。
- 只读 explorer `Sagan` 已审查前端路径，确认旧实现只在渲染 / 导出时解析 `ai4se-visual`，没有写入前 gate；本轮已据此补齐 final 与 partial 写入前校验。

RED 验证：

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/structuredVisuals.test.ts
```

结果：修复前 `4 failed, 14 passed`。失败证明 `extractStructuredVisualBlocks()` / `validateStructuredVisualBlocks()` 尚不存在。

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts -t "ai4se-visual"
```

结果：修复前 `2 failed, 77 skipped`。失败证明 final `agent_turn` 和真实 `agent_delta` partial 都会把无效 `ai4se-visual` 作为 artifact chunk yield。

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/chatService.test.ts -t "artifact validation fails"
```

结果：修复前 `1 failed, 3 passed, 61 skipped`。失败证明 `Artifact structured visual validation failed` 尚未归类为结构化输出失败。

GREEN 与聚焦回归：

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/structuredVisuals.test.ts
```

结果：`19 passed`

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts -t "ai4se-visual"
```

结果：`2 passed, 77 skipped`

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/chatService.test.ts -t "artifact validation fails"
```

结果：`4 passed, 61 skipped`

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/structuredVisuals.test.ts src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/StructuredVisual.test.tsx src/core/__tests__/artifactExport.test.ts src/core/__tests__/docxExport.test.ts
```

结果：`182 passed`

```bash
cd tools/new-agents/frontend && npm run lint
```

结果：TypeScript `tsc --noEmit` 通过。

浏览器 E2E 回归：

```bash
.venv/bin/python -m pytest tests/e2e/new_agents_browser -q
```

结果：`21 passed`。本轮曾先在全量验证中暴露 7 个浏览器 E2E 失败，失败根因是 E2E mock 中部分 `ai4se-visual` `rows` 使用数组行，启用写入前强校验后被正确拒绝；修正 mock 为列名对象行后完整浏览器 E2E 通过。

全量验证：

```bash
/bin/zsh -lc './scripts/test/test-local.sh all > /private/tmp/ai4se-visual-validation-full-all-rerun.log 2>&1; rc=$?; tail -180 /private/tmp/ai4se-visual-validation-full-all-rerun.log; echo EXIT_STATUS:$rc; exit $rc'
```

结果：通过，退出码 `0`。关键结果包括 MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `736 passed`、New Agents Backend `634 passed, 1 deselected`、New Agents Browser E2E `11 passed, 10 deselected`。

残余风险：

- 本轮补齐前端写入前 `ai4se-visual` gate，不改变后端 `validate_agent_turn()` 的正式 contract。
- Backend 仍不执行 Mermaid JS parse；Mermaid parse gate 仍由前端 Mermaid runtime 承担。
- `mmdc` / 浏览器渲染级 CI 门禁仍属于后续第 7 / 第 8 轮候选，不在本切片内声明完成。

### 2026-07-08 第 8A 轮：artifact_data 全阶段 fixture registry 回归门禁

已完成：

- `test_artifact_data_renderers.py` 新增 `ARTIFACT_DATA_STAGE_FIXTURES`，当前覆盖所有 `supports_artifact_data_rendering()` 支持的 25 个在线 workflow/stage；每个 fixture 都必须能通过 deterministic renderer 和 `validate_agent_turn()`。
- `test_agent_runtime.py` 的 `ARTIFACT_DATA_STREAMING_STAGES` 从 fixture registry 派生，避免手写 21 阶段矩阵和 runtime 支持范围漂移。
- `test_workflow_contract_sync.py` 新增 manifest `visualContract` 反向同步测试，要求 `workflow_manifest.json` 中的 `requiredMermaidDiagrams` / `requiredStructuredVisuals` 与后端 required visual maps 完全一致。
- `docs/TESTING.md` 记录第 8 轮全工作流回归门禁入口，明确 fixture registry、runtime instruction matrix 和 visual contract sync 的覆盖边界。
- 只读 explorer `Dirac` 已审查当前门禁缺口，确认本切片应优先收口全阶段 fixture registry、自派生 runtime matrix 和 manifest visualContract reverse sync。

RED 验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_covers_runtime_supported_stages tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_renders_contract_valid_outputs -q
```

结果：修复前 collection 失败，退出码 `4`，失败原因为 `NameError: name 'ARTIFACT_DATA_STAGE_FIXTURES' is not defined`，证明 registry 尚未建立。

GREEN 与聚焦回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_covers_runtime_supported_stages tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_renders_contract_valid_outputs -q
```

结果：`22 passed`

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming -q
```

结果：`21 passed`

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_shared_workflow_manifest_visual_contract_matches_backend_required_visuals -q
```

结果：`1 passed`

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_covers_runtime_supported_stages tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_renders_contract_valid_outputs tools/new-agents/backend/tests/test_agent_runtime.py::test_artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_shared_workflow_manifest_visual_contract_matches_backend_required_visuals -q
```

结果：`44 passed`

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

结果：`375 passed`

批量与全量验证：

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `736 passed`，New Agents Backend `657 passed, 1 deselected`。

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 与 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`，属于端口 / 浏览器权限限制；脚本被中断前已完成 Intent Tester API、代码质量、Common Frontend、New Agents Frontend / Backend，Browser E2E 因 Chromium 权限失败。

```bash
/bin/zsh -lc './scripts/test/test-local.sh all > /private/tmp/ai4se-artifact-data-registry-full-all.log 2>&1; rc=$?; tail -180 /private/tmp/ai4se-artifact-data-registry-full-all.log; echo EXIT_STATUS:$rc; exit $rc'
```

结果：非沙箱全量通过，退出码 `0`。关键结果包括 Intent Tester API `294 passed`、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `736 passed`、New Agents Backend `657 passed, 1 deselected`、New Agents Browser E2E `11 passed, 10 deselected`。

残余风险：

- 本轮不迁移其余阶段的 `artifactDataContract` 到 manifest；当前 registry 为 25 个阶段，除 `IDEA_BRAINSTORM/CONVERGE` 与 `TEST_DESIGN/CASES` 外仍有 23 个待迁移。
- 本轮不增加 backend Mermaid JS parse 或 `mmdc` 渲染门禁。
- 模型输出字段 / 后端派生字段 / 视觉协议来源的完整全阶段矩阵仍属第 8 轮后续文档收口候选。

### 2026-07-08 第 8B 轮：artifact_data 字段来源与视觉协议矩阵

已完成：

- `docs/TESTING.md` 新增并维护 25 个在线 `artifact_data` 阶段的字段来源矩阵，列出模型负责的语义字段、后端派生 / 归一化字段、视觉来源和现有证据。
- 矩阵明确区分 backend-derived 与 validation-only：`STRATEGY.risks[].rpn`、`CASES.case_statistics`、`VALUE_DISCOVERY/ELEVATOR.score_summary.total_score/average_score` 属于可后端补齐或归一化；`delivery_metrics`、`issue_statistics`、`priority_distribution`、`ice_score`、`acceptance_criteria_count` 等仍是模型输入后的校验，不声明后端补齐。
- 矩阵明确当前已完成 `artifactDataContract` manifest 同步迁移的阶段为 `IDEA_BRAINSTORM/CONVERGE` 与 `TEST_DESIGN/CASES`；其余 23 个阶段仍主要由 Pydantic model、renderer tests、runtime instruction 和 artifact contract tests 共同保护。
- 矩阵明确 Mermaid 仍是后端 deterministic renderer 的编译目标，并区分 manifest required visual 与 renderer 额外输出：例如 `IDEA_BRAINSTORM/CONCEPT` 和 `VALUE_DISCOVERY/BLUEPRINT` 仍会额外生成 Mermaid，但 manifest 当前只要求其 `ai4se-visual`。
- 只读 explorer `Jason` 已审查 `workflow_manifest.json`、`agent_runtime.py`、`artifact_data_renderers.py` 和相关 backend tests，返回的事实清单已并入矩阵；本轮未改生产 runtime、schema、manifest、prompt、测试代码或前端运行时。

文档验证：

清理后不再保留指向独立过程 spec / plan 文件的历史文档验证命令；本轮稳定文档和代码路径的验证结果仍保留在上方记录中。

```bash
rg -n "模型负责的 artifact_data|后端派生 / 归一化|视觉来源|第 8B" docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
```

结果：通过，`docs/TESTING.md` 和本 todo 均包含第 8B 矩阵入口；当前 `docs/TESTING.md` 覆盖 25 个在线阶段。

残余风险：

- 本轮只补齐字段来源与视觉协议文档矩阵，不迁移其余阶段的 `artifactDataContract` 到 manifest；当前仍有 23 个 artifact-data 阶段待迁移。
- 本轮不增加 backend Mermaid JS parse 或 `mmdc` 渲染门禁。
- 矩阵是人工维护的文档事实源，后续 schema / renderer / manifest 变化时仍必须同步更新；第 8A 的 fixture registry 和 manifest visualContract sync test 仍是可执行门禁。

### 2026-07-08 第 8C 轮：TEST_DESIGN CASES artifactDataContract 同步

已完成：

- `workflow_manifest.json` 为 `TEST_DESIGN/CASES` 新增 `artifactDataContract`，声明 `case_statistics` 由后端根据 `case_groups` 计算、`case_groups[].cases[].case_id` 必须唯一、`automation_candidates.case_id` 和 `coverage_trace.covered_cases` 只能引用已存在 case id、`stage_gate` 至少包含一个 checked 项。
- `agent_runtime.py` 的 CASES structured output instruction 改为复用 `format_artifact_data_contract_instruction("TEST_DESIGN", "CASES")`，避免 runtime 文案和 manifest 漂移。
- CASES 前端 prompt 清理了要求模型手写 Markdown 覆盖追溯表和 `ai4se-visual` fenced block 的旧描述，改为要求模型提供结构化覆盖关系，由后端确定性渲染右侧测试用例集和 `ai4se-visual traceability-matrix`。
- 新增 backend / frontend 回归测试，覆盖 CASES manifest contract 驱动 backend instruction、runtime instruction 来源、frontend prompt 同步，以及禁止 prompt 回退到 renderer-owned 视觉产物手写要求。
- 只读 explorer `Euler` 已审查 CONVERGE 现有 contract sync 链路和 CASES 最小迁移清单；本轮采纳其关于 `case_groups[].cases[].case_id` 唯一性的建议。

RED 证据：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_cases_artifact_data_contract_manifest_drives_backend_instruction tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_uses_manifest_artifact_data_contract -q
```

结果：按预期失败，`test_cases_artifact_data_contract_manifest_drives_backend_instruction` 失败在 `contract is not None`，`test_cases_structured_output_instruction_uses_manifest_artifact_data_contract` 失败在 instruction 不包含 manifest formatter 输出。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "TEST DESIGN CASES"
```

结果：按预期失败，CASES prompt description 不包含 `【artifact_data 契约同步约束】`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "renderer-owned visuals"
```

结果：按预期失败，CASES prompt description 仍包含要求模型手写 Markdown 表格和 `ai4se-visual` fenced block 的旧描述。

GREEN 证据：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_cases_artifact_data_contract_manifest_drives_backend_instruction tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_omits_derived_statistics tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_uses_manifest_artifact_data_contract -q
```

结果：通过，`3 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "TEST DESIGN CASES|renderer-owned visuals"
```

结果：通过，`2 passed | 16 skipped`。

相关回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_omits_derived_statistics tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_uses_manifest_artifact_data_contract tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_derives_statistics_when_missing tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_inconsistent_statistics tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_automation_candidate_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_coverage_case_reference -q
```

结果：通过，`20 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts
```

结果：通过，`18 passed`。

集成 / 全量验证：

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `47 passed` / `738 passed`；New Agents Backend `659 passed, 1 deselected`。

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 与 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`，属于端口 / 浏览器权限限制；脚本失败前已完成 Intent Tester API、代码质量、Common Frontend、New Agents Frontend / Backend。

```bash
./scripts/test/test-local.sh all
```

结果：非沙箱重跑通过。Intent Tester API `294 passed`；MidScene proxy `17 passed`；Common Frontend lint/build 通过；New Agents Frontend `47 passed` / `738 passed`；New Agents Backend `659 passed, 1 deselected`；New Agents Browser E2E `11 passed, 10 deselected`；汇总未发现失败。

残余风险：

- 本轮只迁移 `TEST_DESIGN/CASES`，当前已完成 `artifactDataContract` manifest 同步迁移的阶段为 `IDEA_BRAINSTORM/CONVERGE` 与 `TEST_DESIGN/CASES`；其余 23 个 artifact-data 阶段仍待后续纵切迁移。
- 本轮不改变 CASES Pydantic schema、renderer、SSE runtime 或 ArtifactPane。
- 本轮不增加 backend Mermaid JS parse 或 `mmdc` 渲染门禁。

### 2026-07-09 补充质量门修复：artifact_data 输出顺序与 ArtifactPane section memo

触发原因：

- 目标模式继续盘点当前 `docs/todos` 时，结构化失败治理仍是 P0 活跃项；Alex handoff 主线已完成，不应重新恢复为活跃主线。
- 前端全量 Vitest 暴露 `ArtifactPane.incrementalRender.test.tsx` 失败：ArtifactPane 预览仍整篇渲染 Markdown，未变章节会在其他章节变化时重新渲染。
- 后端质量门 `test_artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming` 失败：25 个 artifact-data 阶段的模型指令仍要求先输出 `chat`，再输出 `artifact_data`，会削弱右侧真实流式预览。

已修复：

- `ArtifactPane` 预览态按 Markdown 标题章节拆成 memoized section render chunk；单章节内容不变时不会重新调用 `ReactMarkdown`，同时继续用全局 Mermaid / `ai4se-visual` block 起始索引保持视觉诊断锚点稳定。
- 前端类型补齐 `AgentRunSnapshotArtifact.artifactData` 和 observability recent turn `diagnostic`；`observabilityService` 严格解析可选 diagnostic，`ChatPane` handoff fixture 补齐 `unconfirmedItems` 与 `targetInputChecklist`。
- 后端 `build_structured_output_instruction()` 对 artifact-data 阶段统一归一化输出顺序，确保提示词和 JSON 示例都要求 `artifact_data` 在 `chat` 前面；非 artifact-data 文本输出指令不受影响。

验证：

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.incrementalRender.test.tsx
```

结果：修复前 `1 failed`；修复后 `1 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.incrementalRender.test.tsx src/components/__tests__/ArtifactPane.test.tsx src/core/__tests__/artifactSections.test.ts src/components/__tests__/StructuredVisual.test.tsx
```

结果：`157 passed`。

```bash
cd tools/new-agents/frontend && npm run test
```

结果：`51 passed` / `782 passed`；仍有既有 React `act(...)` warning，未导致失败。

```bash
cd tools/new-agents/frontend && npm run lint
```

结果：TypeScript `tsc --noEmit` 通过。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming -q
```

结果：修复前 `25 failed`；修复后 `25 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py tools/new-agents/backend/tests/test_workflow_dry_run.py -q
```

结果：`81 passed`。

扩大验证现状：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_stream_services.py -q
```

结果：`40 failed, 182 passed`。失败集中在历史 contract fixture / 派生字段测试预期 / typed diagnostic 预期滞后等既有后端回归缺口；本轮已修复的 artifact-data 输出顺序质量门包含在该套件中并已单独通过。后续目标模式应把这些后端红灯纳入结构化失败治理的下一批 P0 改道候选，而不是继续新增 workflow 能力。

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
