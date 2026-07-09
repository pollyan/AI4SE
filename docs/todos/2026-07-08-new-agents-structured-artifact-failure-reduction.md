# New Agents 结构化产出失败治理待办

- 状态：执行中（初版第 0-8 共 9 个切片中，第 8 切片“全工作流失败回归门禁与文档收口”实际过大，已按同级切片口径修正：不再允许内部批次或 8A/8B 字母轮次；过大的工作必须拆成多个明确切片。当前已完成全阶段 fixture registry、字段来源与视觉协议矩阵、raw JSON strict failure closure、manifest visualContract sync、25 个在线 artifact-data 阶段的 `artifactDataContract` manifest 同步、高失败阶段纵切和结构化失败回归门禁；artifactDataContract 同步剩余 0 个阶段；派生字段后端化已新增 `TEST_DESIGN/DELIVERY` 统计字段、`REQ_REVIEW` 问题统计、`INCIDENT_REVIEW/IMPROVEMENT` 行动统计、`IDEA_BRAINSTORM/CONVERGE` ICE 评分 / 排名、`TEST_DESIGN/CASES` / `REQ_REVIEW/REVIEW` 分组内维度派生纵切，以及 `STORY_BREAKDOWN` story sprint 派生纵切；映射一致性已新增 `INCIDENT_REVIEW/IMPROVEMENT` root cause/action 精确映射门禁；视觉协议分层已新增 manifest 顶层 `visualProtocol` 并接入后端 runtime / 前端 system prompt。后续未完成治理仍集中在 4 个能力包：派生字段后端化、ID 收敛、`ai4se-visual` 复杂图扩展、视觉渲染强校验。）
- 创建日期：2026-07-08
- 来源：用户反馈 New Agents 生成右侧产出物时经常出现黄色失败框，要求系统分析反复失败原因，并明确禁止用 fallback 草稿隐藏错误
- 优先级：P0
- 相关模块：`tools/new-agents/`

## 切片口径修正

目标模式只允许一种计划单位：切片。切片是计划、验收、提交和对用户汇报进度的唯一口径，不允许再拆出“内部批次”“子切片”或 `8A/8H` 这类字母后缀轮次。

初版 9 个切片是路线假设，不是不可调整的硬约束。若某个切片过大，必须在计划层面拆成多个同级切片，每个切片都要有独立目标、验收、验证命令、提交和 push 边界；不能把过大的工作塞进一个切片后再用“内部批次”消化。

当前判断：初版 9 个切片不是完全合适。第 0-7 切片边界基本成立；第 8 切片覆盖“所有在线 artifact-data 阶段”的回归门禁、文档矩阵、visualContract sync 和 manifest contract sync，范围过大，后续必须拆为多个同级切片继续推进。已经完成的 `VALUE_DISCOVERY/JOURNEY`、`VALUE_DISCOVERY/BLUEPRINT`、`STORY_BREAKDOWN`、`PRD_REVIEW`、`TEST_DESIGN`、`REQ_REVIEW` 与 `INCIDENT_REVIEW` 剩余阶段同步是当前已完成切片工作的一部分；artifactDataContract manifest sync 已覆盖 25 个在线 artifact-data 阶段，后续如果继续治理，必须按未完成横切能力或纵切风险重新定义同级切片边界。

最新评估：默认按“一个 workflow 一个切片”推进，且一个工作流能在同一验证闭环内收口时，不再拆成多个切片。本次 `PRD_REVIEW` 已作为最后一个 workflow 级 contract sync 切片收口；`artifactDataContract` manifest 同步剩余 0 个切片。后续派生字段后端化、ID 收敛、视觉协议分层等未完成治理不得塞回“内部批次”，必须按独立价值目标重新评估为新的同级切片。

| 工作流级切片 | 覆盖范围 | 拆分理由 |
|---|---|---|
| TEST_DESIGN contract sync | `TEST_DESIGN/CLARIFY`、`TEST_DESIGN/DELIVERY` | 已完成切片；同属测试设计工作流的输入澄清与最终交付，已补齐 manifest contract、prompt 注入、backend/frontend sync tests 和 TESTING 矩阵。 |
| REQ_REVIEW contract sync | `REQ_REVIEW/REVIEW`、`REQ_REVIEW/REPORT` | 本次完成切片；同属需求评审闭环，已补齐问题统计一致性、score / priority 视觉输出和报告闭合的 manifest contract、prompt 注入、backend/frontend sync tests 和 TESTING 矩阵。 |
| INCIDENT_REVIEW 剩余阶段 contract sync | `INCIDENT_REVIEW/TIMELINE`、`INCIDENT_REVIEW/IMPROVEMENT` | 已完成切片；ROOT_CAUSE 此前已完成，剩余两个阶段分别覆盖事实时间线和改进闭环，已补齐 manifest contract、runtime instruction、prompt 注入、backend/frontend sync tests 和 TESTING 矩阵。 |
| Alex 需求蓝图收口 | `VALUE_DISCOVERY/BLUEPRINT` | 已完成切片；这是 Alex 从价值发现走向需求蓝图和后续 AI Coding 输入的关键出口，已补齐 manifest contract、runtime instruction、prompt 注入、backend/frontend sync tests 和 TESTING 矩阵。 |
| STORY_BREAKDOWN contract sync | `STORY_BREAKDOWN/INPUT_ANALYSIS`、`STORY_BREAKDOWN/EPIC_MAPPING`、`STORY_BREAKDOWN/STORY_BACKLOG`、`STORY_BREAKDOWN/SPRINT_PLAN` | 已完成切片；同属从需求蓝图到用户故事、Sprint 切片和 AI Coding 单故事包的完整工作流，已补齐 manifest contract、runtime instruction、frontend prompt/config sync tests、renderer validator 负例和 TESTING 矩阵。 |
| PRD_REVIEW contract sync | `PRD_REVIEW/INVENTORY`、`PRD_REVIEW/QUALITY_AUDIT`、`PRD_REVIEW/COMPLETION_PLAN`、`PRD_REVIEW/REVISION_BLUEPRINT` | 已完成切片；四个阶段共享 PRD 盘点 / 质量发现 / 补全动作 / 修订章节数据形态，已补齐 manifest contract、runtime instruction、frontend prompt/config sync tests、renderer validator 负例和 TESTING 矩阵。 |

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
  - 进展：已完成 `TEST_DESIGN/DELIVERY` 统计字段纵切。`case_summary_items[].case_count` 缺省时由 P0/P1/P2 派生；`delivery_metrics.total_cases` 和 `high_risk_count` 缺省时由用例摘要和开放风险派生；模型显式输出错误统计仍触发 validation failure。`DELIVERY` runtime instruction 示例不再要求模型输出这些派生字段，manifest / frontend prompt 改为说明“缺省后端派生、显式提供必须一致”。
  - 进展：已完成 `REQ_REVIEW/REVIEW` 与 `REQ_REVIEW/REPORT` 问题统计纵切。REVIEW 的 `issue_statistics.p0_count/p1_count/p2_count` 缺省时由 `issue_groups[].issues[].priority` 派生，REPORT 的 `issue_statistics` 缺省时由 `issue_closures[].priority` 派生；显式错误统计仍触发 validation failure。REQ_REVIEW runtime instruction 示例不再要求模型输出派生计数字段，manifest / frontend prompt 改为说明“缺省后端派生、显式提供必须一致”。
  - 进展：已完成 `INCIDENT_REVIEW/IMPROVEMENT` 行动统计纵切。`report_info.action_count` 缺省时由 `improvement_actions` 数量派生，`priority_distribution` 缺省时由 `improvement_actions[].priority` 派生；显式错误统计仍触发 validation failure。IMPROVEMENT runtime instruction 示例不再要求模型输出这些派生统计字段，manifest / frontend prompt 改为说明“缺省后端派生、显式提供必须一致”。
  - 进展：已完成 `IDEA_BRAINSTORM/CONVERGE` ICE 评分纵切。`ice_evaluations[].ice_score` 缺省时由 `impact * confidence / effort` 派生；显式错误评分仍触发 validation failure。CONVERGE runtime instruction 示例不再要求模型输出 `ice_score`，manifest / frontend prompt 改为说明“缺省后端派生、显式提供必须一致”。
  - 进展：已完成 `IDEA_BRAINSTORM/CONVERGE` ICE 排名纵切。`ice_evaluations[].rank` 缺省时由后端按 ICE 得分降序派生；显式错误排名仍触发 validation failure。CONVERGE runtime instruction 示例不再要求模型输出 `rank`，manifest / frontend prompt 改为说明“缺省后端派生、显式提供必须一致”。
  - 进展：已完成已治理派生字段回退审计门禁。新增 `get_derived_artifact_data_field_policies()` 清单和 contract sync 测试，统一校验上述字段必须在 manifest contract 中声明后端派生 / 显式一致性，并且 runtime JSON 示例不得再要求模型输出这些字段。
  - 进展：已完成 `TEST_DESIGN/CASES` 与 `REQ_REVIEW/REVIEW` 分组内维度派生纵切。`case_groups[].cases[].dimension` 缺省时由外层 `case_groups[].dimension` 派生，`issue_groups[].issues[].dimension` 缺省时由外层 `issue_groups[].dimension` 派生；显式不一致维度仍触发 validation failure。CASES / REVIEW runtime instruction 示例不再要求模型输出内层维度，manifest / frontend prompt 改为说明“缺省后端派生、显式提供必须一致”。
  - 进展：已完成 `INCIDENT_REVIEW/IMPROVEMENT` root cause/action 精确映射门禁。`root_cause_coverage[].action_ids` 现在必须精确匹配所有 `root_cause_id` 等于对应 `cause_id` 的 `improvement_actions[].action_id`；显式不一致映射触发 validation failure，manifest / frontend prompt 同步暴露该规则。
  - 进展：已完成 `STORY_BREAKDOWN` story sprint 派生纵切。`user_stories[].sprint` 缺省时由后端按 `sprint_slices[].story_ids` 所属 `sprint_slices[].sprint_id` 派生，显式不一致 sprint 触发 validation failure；单故事 handoff candidate 会读取派生后的 Sprint。STORY 四阶段 runtime instruction 示例不再要求模型输出 `sprint`，manifest / frontend prompt 改为说明“缺省后端派生、显式提供必须一致”。
  - 后续候选：旁路审查未发现 P0 回退，当前派生 / 映射能力包无剩余 P1 候选。旁路审查另识别 `VALUE_DISCOVERY/JOURNEY` pain / opportunity 成对映射为 P2，不建议强行并入当前 P1 收口。

- [ ] 收敛 ID 与引用关系。（第 4-6 轮）
  - 目标：后端生成稳定 ID，或在 renderer/normalizer 中确定性分配 ID；模型不再负责维护容易漂移的跨表引用。
  - 重点阶段：`IDEA_BRAINSTORM/DEFINE` 的 evidence 引用，`IDEA_BRAINSTORM/CONVERGE` 的 idea / rank / recommended idea 引用，`TEST_DESIGN/CASES` 的 requirement / risk / case 覆盖引用。
  - 进展：第 4 轮已完成 `IDEA_BRAINSTORM/DEFINE` 的 root problem / evidence / problem-user-fit ID 引用治理；第 5 轮首个纵切已完成 `IDEA_BRAINSTORM/DIVERGE` 与 `CONVERGE` partial preview 的跨引用门禁，避免流式右侧产物预览已知错误章节；第 6 轮已完成 `TEST_DESIGN/CASES` 的 `automation_candidates.case_id` / `coverage_trace.covered_cases` case_id 引用门禁，以及 `TEST_DESIGN/STRATEGY` 的 `QG/R/TS/TP` 内部 ID 唯一性与引用门禁。更广泛的后端确定性 ID 分配仍未完成。
  - 进展：已补齐 `TEST_DESIGN/CASES automation_candidates.case_id` 后端引用闭环。manifest 已声明自动化候选只能引用已存在 `case_id`，现在 validator 会拒绝未知 case id，与既有 `coverage_trace.covered_cases` 门禁一致。

- [x] 建立 schema / prompt / contract 单源同步机制。（横切，第 3-8 轮）
  - 目标：Pydantic validators、structured output instruction、workflow manifest visual contract、frontend prompt 不再各写一套约束。
  - 验收：新增 contract sync 测试，证明关键不变量在 prompt 和后端 validator 中同时存在。
  - 进展：已完成 `IDEA_BRAINSTORM/CONVERGE` 首个 `artifactDataContract` 同步纵切。CONVERGE 的关键 artifact_data 不变量已进入 `workflow_manifest.json`，后端 structured output instruction 和前端 stage prompt 均从 manifest 生成同步约束，并由 backend / frontend 同步测试保护。
  - 进展：已完成 `TEST_DESIGN/CASES` `artifactDataContract` manifest 同步。CASES 的 `case_statistics` 后端派生、case_id 唯一性、`automation_candidates.case_id` / `coverage_trace.covered_cases` 引用门禁、禁止模型输出 renderer-owned Markdown / `ai4se-visual` 产物等关键约束已进入 manifest，并由 backend instruction sync、runtime instruction 和 frontend prompt tests 保护。该记录完成时 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/CONVERGE` 与 `TEST_DESIGN/CASES` 外，其余 23 个阶段尚未迁移。
  - 进展：已完成 `TEST_DESIGN/STRATEGY` `artifactDataContract` manifest 同步。STRATEGY 的 `risks[].rpn` 后端派生、`QG/R/TS/TP` ID 唯一性、测试点/测试技术/测试分层引用门禁、禁止模型输出 renderer-owned Markdown / Mermaid / risk-board 代码块等关键约束已进入 manifest，并由 backend instruction sync、runtime instruction、renderer validators 和 frontend prompt tests 保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/CONVERGE`、`TEST_DESIGN/CASES` 与 `TEST_DESIGN/STRATEGY` 外，其余 22 个阶段尚未迁移。
  - 进展：已完成 `INCIDENT_REVIEW/ROOT_CAUSE` `artifactDataContract` manifest 同步。ROOT_CAUSE 的 5-Why 深度、原因 ID 唯一性、证据 / 鱼骨 / 根因结论引用门禁、禁止模型输出 renderer-owned Markdown / Mermaid / cause-map JSON 等关键约束已进入 manifest，并由 backend instruction sync 和 frontend manifest prompt tests 保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/CONVERGE`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE` 外，其余 21 个阶段尚未迁移。
  - 进展：已完成 `IDEA_BRAINSTORM/DEFINE` `artifactDataContract` manifest 同步。DEFINE 的 evidence / problem ID 唯一性、problem-user-fit 证据引用、root problem 覆盖、`stage_gate`、禁止模型输出 renderer-owned Markdown / Mermaid / mindmap 代码块等关键约束已进入 manifest，并由 backend instruction sync、frontend manifest 配置和 frontend prompt 注入测试保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/CONVERGE`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE` 外，其余 20 个阶段尚未迁移。
  - 进展：已完成 `IDEA_BRAINSTORM/DIVERGE` `artifactDataContract` manifest 同步。DIVERGE 的 idea/source/parked record ID 唯一性、创意全景与创意来源 idea 引用、`stage_gate`、禁止模型输出 renderer-owned Markdown / Mermaid / mindmap 代码块等关键约束已进入 manifest，并由 backend instruction sync、frontend manifest 配置和 frontend prompt 注入测试保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE` 外，其余 19 个阶段尚未迁移。
  - 进展：已完成 `IDEA_BRAINSTORM/CONCEPT` `artifactDataContract` manifest 同步。CONCEPT 的 core assumption / validation / action ID 唯一性、Lean Canvas 必备格、AARRR 增长漏斗必备 stage、MVP / validation / next action 引用门禁、`stage_gate`、禁止模型输出 renderer-owned Markdown / Mermaid / mvp-map JSON / pie / flowchart 代码块等关键约束已进入 manifest，并由 backend instruction sync、frontend manifest 配置和 frontend prompt 注入测试保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE` 外，其余 18 个阶段尚未迁移。
  - 进展：已完成 `VALUE_DISCOVERY/ELEVATOR` `artifactDataContract` manifest 同步。ELEVATOR 的 value_flow node ID 唯一性、flow link 引用门禁、score 取值范围、`score_summary.total_score` / `average_score` 后端派生或显式一致性、禁止模型输出 renderer-owned Markdown / Mermaid / score-matrix JSON 等关键约束已进入 manifest，并由 backend instruction sync、frontend manifest 配置和 frontend prompt 注入测试保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE` 外，其余 17 个阶段尚未迁移。
  - 进展：已完成 `VALUE_DISCOVERY/PERSONA` `artifactDataContract` manifest 同步。PERSONA 的 `personas[].persona_id` 唯一性、行为场景 / 决策链 / 痛点证据 / 优先级排序 persona 引用门禁、`priority_ranking[].persona_id` 唯一性、禁止模型输出 renderer-owned Markdown / Markdown 表格等关键约束已进入 manifest，并由 backend instruction sync、frontend manifest 配置和 frontend prompt 注入测试保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE` 外，其余 16 个阶段尚未迁移。
  - 进展：已完成 `VALUE_DISCOVERY/JOURNEY` `artifactDataContract` manifest 同步。JOURNEY 的 journey stage / pain / opportunity ID 唯一性、emotion score 取值范围、旅程阶段 / 痛点 / 机会引用门禁、禁止模型输出 renderer-owned Markdown / Mermaid / journey-map JSON 等关键约束已进入 manifest，并由 backend instruction sync、frontend manifest 配置和 frontend prompt 注入测试保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE` 外，其余 15 个阶段尚未迁移。
  - 进展：已完成 `TEST_DESIGN/CLARIFY` 与 `TEST_DESIGN/DELIVERY` `artifactDataContract` manifest 同步。CLARIFY 的必填列表与非空字符串要求、DELIVERY 的用例摘要统计 / 交付指标一致性和覆盖地图 case id 列表要求、禁止模型输出 renderer-owned Markdown / Mermaid / coverage-map JSON 等边界已进入 manifest，并由 backend instruction sync、frontend manifest 配置和 frontend prompt 注入测试保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`TEST_DESIGN/CLARIFY`、`TEST_DESIGN/STRATEGY`、`TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY` 与 `INCIDENT_REVIEW/ROOT_CAUSE` 外，其余 13 个阶段尚未迁移。
  - 进展：已完成 `REQ_REVIEW/REVIEW` 与 `REQ_REVIEW/REPORT` `artifactDataContract` manifest 同步。REVIEW 的问题统计一致性、问题 ID 唯一性、修订建议问题引用、严重度评分范围，REPORT 的问题关闭项 ID 唯一性、问题统计一致性、复审条件问题引用和开放 P0/P1 结论门禁，以及禁止模型输出 renderer-owned Markdown / Mermaid / score-matrix / priority-board JSON 等边界已进入 manifest，并由 backend instruction sync、frontend manifest 配置和 frontend prompt 注入测试保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`TEST_DESIGN/CLARIFY`、`TEST_DESIGN/STRATEGY`、`TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY`、`REQ_REVIEW/REVIEW`、`REQ_REVIEW/REPORT` 与 `INCIDENT_REVIEW/ROOT_CAUSE` 外，其余 11 个阶段尚未迁移。
  - 进展：已完成 `INCIDENT_REVIEW/TIMELINE` 与 `INCIDENT_REVIEW/IMPROVEMENT` `artifactDataContract` manifest 同步。TIMELINE 的必填列表、`timeline_events[].fact_ids` 非空、fact ID 唯一性和事实引用门禁，IMPROVEMENT 的行动数量、优先级分布、action ID、根因覆盖和 action/root_cause 引用门禁，以及禁止模型输出 renderer-owned Markdown / Mermaid / pie / action-board JSON 等边界已进入 manifest，并由 backend instruction sync、frontend manifest 配置和 frontend prompt 注入测试保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`TEST_DESIGN/CLARIFY`、`TEST_DESIGN/STRATEGY`、`TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY`、`REQ_REVIEW/REVIEW`、`REQ_REVIEW/REPORT`、`INCIDENT_REVIEW/TIMELINE`、`INCIDENT_REVIEW/ROOT_CAUSE` 与 `INCIDENT_REVIEW/IMPROVEMENT` 外，其余 9 个阶段尚未迁移。
  - 进展：已完成 `VALUE_DISCOVERY/BLUEPRINT` `artifactDataContract` manifest 同步。BLUEPRINT 的需求 ID 唯一性、验收标准 ID 唯一性、功能 / MVP / 验收 / Lisa handoff 需求引用、Lisa handoff 验收标准引用、主流程节点唯一性和流程 link 引用门禁，以及禁止模型输出 renderer-owned Markdown / Mermaid / roadmap JSON 等边界已进入 manifest，并由 backend instruction sync、runtime instruction、frontend manifest 配置、frontend prompt 注入和 renderer validator 测试保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`VALUE_DISCOVERY/BLUEPRINT`、`TEST_DESIGN/CLARIFY`、`TEST_DESIGN/STRATEGY`、`TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY`、`REQ_REVIEW/REVIEW`、`REQ_REVIEW/REPORT`、`INCIDENT_REVIEW/TIMELINE`、`INCIDENT_REVIEW/ROOT_CAUSE` 与 `INCIDENT_REVIEW/IMPROVEMENT` 外，其余 8 个阶段尚未迁移。
  - 进展：已完成 `STORY_BREAKDOWN/INPUT_ANALYSIS`、`STORY_BREAKDOWN/EPIC_MAPPING`、`STORY_BREAKDOWN/STORY_BACKLOG` 与 `STORY_BREAKDOWN/SPRINT_PLAN` `artifactDataContract` manifest 同步。STORY_BREAKDOWN 的必需字段、契约外字段拒绝、关键嵌套数组非空、Epic / Story / Criterion / Dependency / Sprint ID 唯一性、Epic / Story / Criterion / Dependency / Sprint / Lisa handoff 引用门禁、`story_points >= 1`、`stage_gate` checked，以及禁止模型输出 renderer-owned Markdown / Mermaid / story-map JSON 等边界已进入 manifest，并由 backend instruction sync、runtime instruction、frontend manifest 配置、frontend prompt 注入和 renderer validator 负例测试保护。当前 registry 共 25 个 artifact-data 阶段，除 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`VALUE_DISCOVERY/BLUEPRINT`、`STORY_BREAKDOWN/INPUT_ANALYSIS`、`STORY_BREAKDOWN/EPIC_MAPPING`、`STORY_BREAKDOWN/STORY_BACKLOG`、`STORY_BREAKDOWN/SPRINT_PLAN`、`TEST_DESIGN/CLARIFY`、`TEST_DESIGN/STRATEGY`、`TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY`、`REQ_REVIEW/REVIEW`、`REQ_REVIEW/REPORT`、`INCIDENT_REVIEW/TIMELINE`、`INCIDENT_REVIEW/ROOT_CAUSE` 与 `INCIDENT_REVIEW/IMPROVEMENT` 外，其余 4 个阶段尚未迁移。
  - 进展：已完成 `PRD_REVIEW/INVENTORY`、`PRD_REVIEW/QUALITY_AUDIT`、`PRD_REVIEW/COMPLETION_PLAN` 与 `PRD_REVIEW/REVISION_BLUEPRINT` `artifactDataContract` manifest 同步。PRD_REVIEW 的必需字段、契约外字段拒绝、关键列表非空、finding / action / section ID 唯一性、action finding 引用、acceptance / handoff section 引用、`stage_gate` checked，以及禁止模型输出 renderer-owned Markdown / Mermaid / `ai4se-visual` JSON 等边界已进入 manifest，并由 backend instruction sync、runtime instruction、frontend manifest 配置、frontend prompt 注入和 renderer validator 负例测试保护。当前 registry 共 25 个 artifact-data 阶段，25 个阶段均已完成 `artifactDataContract` manifest sync，剩余待迁移阶段为 0。

- [x] 针对高失败阶段做纵切专项修复。（第 4-6 轮）
  - 优先顺序：`IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/CONVERGE`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY`、`IDEA_BRAINSTORM/DIVERGE`。
  - 目标：每个阶段都有失败复现、根因定位、最小 schema 设计修复和回归测试。
  - 进展：第 4 轮已完成 `IDEA_BRAINSTORM/DEFINE` 的已知 root-problem 覆盖失败模式修复；第 5 轮首个纵切已完成 `DIVERGE` / `CONVERGE` partial preview 与 final validator 关键引用不变量对齐；第 6 轮已完成 `CASES` 的用例统计后端化与 partial case_id 引用门禁，以及 `STRATEGY` 的内部引用门禁。后续已进一步把 CASES 的核心 artifact_data 约束迁入 manifest，并清理前端 prompt 中要求模型手写 Markdown 表格 / `ai4se-visual` block 的旧冲突描述。
  - 进展：已进一步把 `IDEA_BRAINSTORM/DEFINE` 的核心 root-problem / evidence 引用约束迁入 manifest，让原高失败阶段的后端 validator、structured output instruction 和前端 prompt 使用同一配置源。
  - 进展：已进一步把 `IDEA_BRAINSTORM/DIVERGE` 的核心 idea/source 引用约束迁入 manifest，让原高失败阶段的后端 validator、structured output instruction 和前端 prompt 使用同一配置源。

- [x] 增加结构化失败回归门禁。（第 8 轮）
  - 目标：高失败阶段必须有固定 fixture / raw JSON stream / renderer contract 测试，确保不会再次因为已知不变量触发 `SCHEMA_VALIDATION_FAILED`。
  - 验收：纳入 `./scripts/test/test-local.sh new-agents` 或明确的 New Agents backend regression suite。
  - 进展：已建立 `ARTIFACT_DATA_STAGE_FIXTURES` 全阶段测试登记表，当前覆盖全部 `supports_artifact_data_rendering()` 支持的 25 个在线阶段；每个 registry fixture 都必须通过 deterministic renderer 和 `validate_agent_turn()`。`test_agent_runtime.py` 的 artifact-data instruction 顺序矩阵已改为从 registry 派生，避免新增阶段时漏掉 raw JSON visible streaming 门禁。`test_workflow_contract_sync.py` 已反向校验 `workflow_manifest.json` 的 `visualContract` 与后端 required Mermaid / structured visual maps 完全一致。
  - 进展：已在 `docs/TESTING.md` 补齐 25 个在线阶段的模型输出字段 / 后端派生字段 / 视觉协议来源矩阵，明确 validation-only 与 backend-derived 的边界，并记录当前已完成 `artifactDataContract` manifest 同步迁移的阶段为 `IDEA_BRAINSTORM/CONVERGE` 与 `TEST_DESIGN/CASES`。
  - 进展：已新增 `TEST_DESIGN/CASES` 的 backend manifest contract sync、runtime instruction source 和 frontend prompt sync 回归测试；相关 CASES renderer / 引用门禁测试继续通过。
  - 进展：已新增 `TEST_DESIGN/STRATEGY` 的 backend manifest contract sync、runtime instruction source、frontend prompt 单点注入和 renderer validator 回归测试；相关 STRATEGY RPN 派生、ID 唯一性、引用门禁和 stage_gate 测试继续通过。
  - 进展：已移除 raw JSON 截断后的 `artifact_truncated` 伪成功最终输出，恢复最终 JSON 无效时的 `AgentRuntimeSchemaError` strict failure closure；同时把 raw streaming 强门禁明确为“final 前至少一个正式 before-final artifact delta + final contract 通过”，字段级多段 partial renderer 当前仅声明 `TEST_DESIGN/CLARIFY` 已实现，`artifact_patch` 不作为全阶段强门禁。
  - 进展：已新增 `IDEA_BRAINSTORM/DIVERGE` 的 backend manifest contract sync、frontend manifest 配置和 frontend prompt 注入回归测试；相关 DIVERGE renderer / 引用门禁测试继续作为聚焦验证范围。
  - 进展：已新增 `IDEA_BRAINSTORM/CONCEPT` 的 backend manifest contract sync、frontend manifest 配置和 frontend prompt 注入回归测试；相关 CONCEPT renderer / 引用门禁 / raw JSON streaming 测试继续作为聚焦验证范围。
  - 进展：已新增 `VALUE_DISCOVERY/ELEVATOR` 的 backend manifest contract sync、frontend manifest 配置和 frontend prompt 注入回归测试；相关 ELEVATOR score summary 派生、renderer / 引用门禁 / raw JSON streaming 测试继续作为聚焦验证范围。
  - 进展：已新增 `VALUE_DISCOVERY/PERSONA` 的 backend manifest contract sync、frontend manifest 配置和 frontend prompt 注入回归测试；相关 PERSONA persona 引用门禁、renderer 和 raw JSON streaming 测试继续作为聚焦验证范围。
  - 进展：已新增 `VALUE_DISCOVERY/JOURNEY` 的 backend manifest contract sync、frontend manifest 配置和 frontend prompt 注入回归测试；相关 JOURNEY stage / pain / opportunity 引用门禁、visual contract、renderer 和 raw JSON streaming 测试继续作为聚焦验证范围。
  - 进展：已新增 `TEST_DESIGN/CLARIFY` 与 `TEST_DESIGN/DELIVERY` 的 backend manifest contract sync、frontend manifest 配置和 frontend prompt 注入回归测试；相关 CLARIFY / DELIVERY renderer、runtime raw JSON streaming 和视觉 contract 测试继续作为聚焦验证范围。
  - 进展：已新增 `REQ_REVIEW/REVIEW` 与 `REQ_REVIEW/REPORT` 的 backend manifest contract sync、frontend manifest 配置和 frontend prompt 注入回归测试；相关 REVIEW / REPORT renderer、issue statistics consistency、runtime raw JSON streaming 和视觉 contract 测试继续作为聚焦验证范围。

- [x] 建立视觉产物协议分层。（第 7 轮）
  - 目标：明确哪些视觉类型必须走 `ai4se-visual` JSON，哪些 Mermaid 类型允许由后端 deterministic renderer 生成，哪些 DSL 禁止模型直接输出。
  - 初始策略：复杂图和业务图默认走 `ai4se-visual`；Mermaid 只允许作为后端从结构化数据生成的简单图编译目标；不引入 D2、Graphviz 或 PlantUML 作为运行时主协议，除非后续有单独架构批准。
  - 验收：`workflow_manifest.json`、`agent_contracts.py`、structured output instruction 和前端模板对每个在线阶段的视觉协议一致。
  - 进展：已完成共享视觉协议分层切片。`workflow_manifest.json` 顶层新增 `visualProtocol`，声明模型只输出 `artifact_data`、Mermaid 只允许后端 deterministic renderer 生成、复杂业务图优先 `ai4se-visual`，并禁止模型直接输出 Mermaid / D2 / Graphviz DOT / PlantUML 代码块。后端 `format_visual_protocol_instruction()` 和 `build_structured_output_instruction()` 会对所有 artifact-data 阶段注入同一协议；前端 `buildSystemPrompt()` 从同一 manifest 字段注入已脱敏的视觉协议文案，继续避免把 Mermaid 手写要求暴露给模型。

- [ ] 扩展 `ai4se-visual` 类型覆盖复杂图。（第 7 轮）
  - 目标：在现有 `score-matrix`、`coverage-map`、`journey-map` 等表格类视觉之外，补齐 `flow-map`、`timeline-map`、`mindmap`、`sequence-flow`、`distribution-chart` 等数据结构，使复杂图不再依赖模型手写 Mermaid。
  - 约束：每个 visual 类型必须有严格 schema、引用完整性校验、前端渲染组件、导出降级文本和失败诊断。
  - 验收：至少选一个 Mermaid 失败高风险阶段完成纵切迁移，并证明最终 artifact 不含模型手写 Mermaid。
  - 进展：已完成首个复杂图纵切 `INCIDENT_REVIEW/ROOT_CAUSE.cause-map`。该 visual type 已从 `columns/rows` 表格协议迁移为 `nodes/edges`，并覆盖后端 deterministic renderer、后端 contract 校验、前端 parser、前端组件、PDF/DOCX 导出降级和模板同步测试。更广泛的 `flow-map`、`timeline-map`、`mindmap`、`sequence-flow` 等类型仍未迁移。
  - 进展：已补齐 `STORY_BREAKDOWN` 所需 `story-map` 的前端共享 visual 支持。后端和 manifest 已声明并输出矩阵式 `ai4se-visual story-map`，前端 parser、`StructuredVisual`、PDF 导出和 DOCX 导出已纳入同一 `columns/rows` 协议；当前 manifest `requiredStructuredVisuals` 声明的所有类型均可被前端 parser 识别。

- [ ] 建立视觉渲染强校验门禁。（第 7 轮）
  - 目标：正式 artifact 被呈现为成功、持久化和阶段推进前，必须通过 Mermaid / `ai4se-visual` 视觉校验；若运行时校验暂不能放在 backend，则必须先以 CI / renderer fixture / frontend parse 形成可执行门禁，并在运行时失败时显式诊断。
  - Mermaid 校验：允许的 Mermaid block 必须通过 `mermaid.parse` 或等价校验；CI 或回归套件可增加 `mmdc` 渲染 SVG 门禁，覆盖浏览器能 parse 但导出失败的情况。
  - `ai4se-visual` 校验：JSON 必须合法，`type` 必须受支持，columns / rows / nodes / edges / events 等结构必须完整，引用目标必须存在。
  - 验收：新增测试证明视觉校验失败会显式报错，不产生成功 `agent_turn`、不持久化 artifact、不推进 stage。
  - 进展：已完成前端写入前视觉 gate。`llm.ts` 在 final `agent_turn`、合成 artifact reveal 和真实 `agent_delta` partial 写出 chunk 前统一校验 Mermaid 与 `ai4se-visual`；`structuredVisuals.ts` 复用共享 parser 校验所有 fenced `ai4se-visual` block；`chatService.ts` 将结构化视觉校验失败归类为结构化输出生成失败并保持右侧产物不变。后续仍可补 CI / `mmdc` 渲染门禁和更广泛的 backend 运行时 Mermaid parse。
  - 进展：已新增前端门禁测试，反向遍历 `WORKFLOWS[*].stages[*].visualContract.requiredStructuredVisuals` 并验证每一种 required `ai4se-visual` 类型都能被共享 parser 接受，防止 manifest/backend 新增 required 类型但前端无法解析。

- [x] 收紧 Mermaid repair 的架构边界。（第 7 轮）
  - 目标：`/api/utils/mermaid/repair` 和前端 retry 只能作为用户显式触发的修复辅助，不能自动替换正式 artifact、不能绕过 contract、不能让失败状态变成成功。
  - 验收：测试证明 repair 结果必须重新经过 Mermaid parse / artifact contract 校验；repair 失败继续显式展示，不隐藏原始错误。
  - 进展：已完成前端 `retryMermaidGeneration()` parse gate；ArtifactPane 发起 repair 时会把 `workflowId`、`stageId` 和当前完整 artifact 一起提交给共享 `/api/utils/mermaid/repair`，后端替换候选 Mermaid block 后复用 `validate_agent_turn` 做完整 artifact contract 校验。ChatPane 不替换 artifact，只保留 Mermaid parse gate。失败时 service 返回 `null`，父组件不写入 artifact/message，原始错误状态继续保留。

## 目标切片声明

初版按 1 个第 0 切片能力 spike 加 8 个治理切片推进。复盘后确认：第 0-7 切片边界基本成立，原第 8 切片“全工作流失败回归门禁与文档收口”过大，后续必须拆成多个同级切片继续推进。每个切片都必须保留“失败显式报错”的架构边界，不允许通过 fallback 降低用户可见错误。第 0 切片是能力 spike，不改变正式 workflow 主链路；当前已补做第 0 切片静态能力结论，真实 provider smoke 仅在具备 `DEEPSEEK_API_KEY` 和明确外部调用授权时再单独执行。

| 切片 | 目标模式 | 覆盖范围 | 交付边界 |
|---|---|---|---|
| 第 0 切片 | DeepSeek provider 能力 spike | JSON mode 边界、tool calling、strict tool call、streaming tool arguments | 只产出能力结论、最小 fixture 和 provider capability 设计，不改变正式 workflow 主链路；确认 tool calling 是否值得进入后续切片。 |
| 第 1 切片 | 结构化失败诊断透明化 | backend error event、frontend diagnostic card、observability metrics | 用户和工程师能直接看到失败发生在哪个 workflow/stage/field/validator；仍然显式失败，不持久化错误产物。 |
| 第 2 切片 | 严格失败闭环 | raw JSON 截断、空内容、provider 中断、partial delta 最终失败 | 移除 `artifact_truncated` 伪最终输出；partial delta 可用于流式预览，但最终 JSON 无效必须显式失败，不持久化、不推进 stage。 |
| 第 3 切片 | 可计算字段后端化首个纵切 | `VALUE_DISCOVERY/ELEVATOR` 或 `TEST_DESIGN/CASES` 中一组派生字段 | 模型不再输出选定派生字段；后端确定性计算并渲染；相关旧失败模式有回归测试。 |
| 第 4 切片 | IDEA DEFINE 根问题与证据一致性治理 | `IDEA_BRAINSTORM/DEFINE` | root problem、evidence、problem-user-fit 的覆盖关系由更稳定的数据结构或后端确定性关联保证；真实已知失败类型不再复现。 |
| 第 5 切片 | IDEA CONVERGE / DIVERGE 引用一致性治理 | `IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE` | idea id、source id、rank、recommended idea、merge path 等引用关系不再依赖模型自由维护。 |
| 第 6 切片 | TEST_DESIGN CASES / STRATEGY 统计与覆盖治理 | `TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` | 用例统计、覆盖追踪、风险/测试点/用例映射中的派生值和引用关系稳定化。 |
| 第 7 切片 | 视觉产物稳定化专项 | Mermaid、`ai4se-visual`、ArtifactPane、visual contract registry、导出链路 | `ai4se-visual` 成为复杂视觉主协议；Mermaid 只作为后端确定性编译目标；视觉失败显式报错并进入回归门禁。 |
| 第 8 切片及后续同级切片 | 全工作流失败回归门禁与文档收口拆分 | 所有在线 artifact-data 阶段 | 原第 8 切片过大，后续必须按自然业务边界拆成多个同级切片；每个切片独立定义目标、验收、验证、commit 和 push。 |

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

### 2026-07-08 切片记录：artifact_data 全阶段 fixture registry 回归门禁

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

- 本轮不迁移其余阶段的 `artifactDataContract` 到 manifest；该记录完成时 registry 为 25 个阶段，除 `IDEA_BRAINSTORM/CONVERGE` 与 `TEST_DESIGN/CASES` 外仍有 23 个待迁移。
- 本轮不增加 backend Mermaid JS parse 或 `mmdc` 渲染门禁。
- 模型输出字段 / 后端派生字段 / 视觉协议来源的完整全阶段矩阵仍属第 8 轮后续文档收口候选。

### 2026-07-08 切片记录：artifact_data 字段来源与视觉协议矩阵

已完成：

- `docs/TESTING.md` 新增并维护 25 个在线 `artifact_data` 阶段的字段来源矩阵，列出模型负责的语义字段、后端派生 / 归一化字段、视觉来源和现有证据。
- 矩阵明确区分 backend-derived 与 validation-only：`STRATEGY.risks[].rpn`、`CASES.case_statistics`、`VALUE_DISCOVERY/ELEVATOR.score_summary.total_score/average_score` 属于可后端补齐或归一化；`delivery_metrics`、`issue_statistics`、`priority_distribution`、`ice_score`、`acceptance_criteria_count` 等仍是模型输入后的校验，不声明后端补齐。
- 矩阵在该记录完成时明确已完成 `artifactDataContract` manifest 同步迁移的阶段为 `IDEA_BRAINSTORM/CONVERGE` 与 `TEST_DESIGN/CASES`；其余 23 个阶段仍主要由 Pydantic model、renderer tests、runtime instruction 和 artifact contract tests 共同保护。
- 矩阵明确 Mermaid 仍是后端 deterministic renderer 的编译目标，并区分 manifest required visual 与 renderer 额外输出：例如 `IDEA_BRAINSTORM/CONCEPT` 和 `VALUE_DISCOVERY/BLUEPRINT` 仍会额外生成 Mermaid，但 manifest 当前只要求其 `ai4se-visual`。
- 只读 explorer `Jason` 已审查 `workflow_manifest.json`、`agent_runtime.py`、`artifact_data_renderers.py` 和相关 backend tests，返回的事实清单已并入矩阵；本轮未改生产 runtime、schema、manifest、prompt、测试代码或前端运行时。

文档验证：

清理后不再保留指向独立过程 spec / plan 文件的历史文档验证命令；本轮稳定文档和代码路径的验证结果仍保留在上方记录中。

```bash
rg -n "模型负责的 artifact_data|后端派生 / 归一化|视觉来源|字段来源与视觉协议矩阵" docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
```

结果：通过，`docs/TESTING.md` 和本 todo 均包含字段来源与视觉协议矩阵入口；当前 `docs/TESTING.md` 覆盖 25 个在线阶段。

残余风险：

- 本轮只补齐字段来源与视觉协议文档矩阵，不迁移其余阶段的 `artifactDataContract` 到 manifest；该记录完成时仍有 23 个 artifact-data 阶段待迁移。
- 本轮不增加 backend Mermaid JS parse 或 `mmdc` 渲染门禁。
- 矩阵是人工维护的文档事实源，后续 schema / renderer / manifest 变化时仍必须同步更新；fixture registry 和 manifest visualContract sync test 仍是可执行门禁。

### 2026-07-08 切片记录：TEST_DESIGN CASES artifactDataContract 同步

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

- 本轮只迁移 `TEST_DESIGN/CASES`；该记录完成时已完成 `artifactDataContract` manifest 同步迁移的阶段为 `IDEA_BRAINSTORM/CONVERGE` 与 `TEST_DESIGN/CASES`，其余 23 个 artifact-data 阶段仍待后续纵切迁移。
- 本轮不改变 CASES Pydantic schema、renderer、SSE runtime 或 ArtifactPane。
- 本轮不增加 backend Mermaid JS parse 或 `mmdc` 渲染门禁。

### 2026-07-09 切片记录：TEST_DESIGN STRATEGY artifactDataContract 同步

已完成：

- `workflow_manifest.json` 为 `TEST_DESIGN/STRATEGY` 新增 `artifactDataContract`，声明 `risks[].rpn` 由后端根据 S/O/D 计算，`QG/R/TS/TP` ID 必须唯一，测试点、测试技术和测试分层只能引用已定义 ID，`stage_gate` 至少包含一个 checked 项。
- `agent_runtime.py` 的 STRATEGY structured output instruction 改为复用 `format_artifact_data_contract_instruction("TEST_DESIGN", "STRATEGY")`，并从示例 JSON 中移除模型输出 `rpn` 的要求。
- `StrategyRisk` 支持缺省 `rpn` 并由后端派生；若模型显式输出错误 `rpn` 仍触发 validation failure。
- `StrategyArtifactData` 新增内部 ID 唯一性、`QG/R/TS/TP` 引用完整性和 `stage_gate` 校验；STRATEGY fixture 补齐 `TP-002`、`TP-003`，修复历史样例中分层策略引用未定义测试点的问题。
- STRATEGY 前端 prompt 清理要求模型手写 renderer-owned Markdown / Mermaid / risk-board 的旧描述；`buildSystemPrompt` 增加回归测试，确保 manifest contract 只通过统一 `artifact_data` contract 区块注入一次，不再拼入 stage description 造成重复注入。
- 只读 explorer `Hubble` 已审查 STRATEGY contract sync 链路和风险点；本轮采纳其关于“不要让模型输出 rpn”和“避免 frontend prompt 双通道注入”的建议。

RED / GREEN 证据：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_inconsistent_rpn tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_computes_missing_rpn_for_generated_visuals tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_duplicate_strategy_ids tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_unknown_test_point_references tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_unknown_technique_and_layer_references tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_requires_checked_stage_gate tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_strategy_artifact_data_without_model_rpn tools/new-agents/backend/tests/test_agent_runtime.py::test_strategy_structured_output_instruction_uses_manifest_artifact_data_contract -q
```

结果：先按预期暴露缺省 `rpn` 和 STRATEGY 引用校验缺失；修复后通过，`8 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

结果：通过，`73 passed`。

补充清理验证：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_validates_pydantic_ai_output_before_returning_it tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_stream_turn_yields_partial_outputs_and_validates_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_value_elevator_without_model_score_totals tools/new-agents/backend/tests/test_agent_runtime.py::test_value_elevator_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_define_structured_output_instruction_explains_root_problem_coverage -q
```

结果：通过，`5 passed`。

宽回归现状：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

结果：未通过。修复本轮相关和机械 fixture 债后，剩余失败集中在 `test_agent_runtime.py` 的 raw JSON partial streaming 多段预览断言：当前实现只对 `TEST_DESIGN/CLARIFY` 暴露 partial renderer，且多阶段 artifact-data 测试仍期望 2 到 3 个中间 partial / patch。该问题不在本轮 STRATEGY contract 同步范围内，需后续单独决定是恢复多阶段 partial renderer，还是把回归门禁调整为“至少一个可信 partial + final contract 通过”。

残余风险：

- 本轮只迁移 `TEST_DESIGN/STRATEGY`，当前已完成 `artifactDataContract` manifest 同步迁移的阶段为 `IDEA_BRAINSTORM/CONVERGE`、`TEST_DESIGN/CASES` 与 `TEST_DESIGN/STRATEGY`；其余 22 个 artifact-data 阶段仍待后续纵切迁移。
- 本轮不处理 raw JSON partial streaming 多段预览门禁和 `artifact_truncated` 旧路径；这两项应另起纵切，避免混进 STRATEGY contract 同步。
- 本轮不增加 backend Mermaid JS parse 或 `mmdc` 渲染门禁。

### 2026-07-09 切片记录：raw JSON strict failure closure 与 before-final delta 门禁收口

触发原因：

- STRATEGY 宽回归已暴露 `test_agent_runtime.py` 中 raw JSON partial streaming 多段预览断言仍与当前实现不一致。
- 只读 explorer `Volta` 复核后确认：当前 runtime 不应恢复 `artifact_truncated` 伪最终输出；多阶段字段级 partial renderer 与 `artifact_patch` 是未来能力，不是当前全阶段强门禁。

已完成：

- `agent_runtime.py` 删除 JSONDecodeError 后返回 `AgentTurnOutput(warnings=["artifact_truncated"])` 的伪成功路径；已发出的流式 delta 可继续作为预览，但最终 accumulated JSON 无效时必须抛出 `AgentRuntimeSchemaError`。
- `TEST_DESIGN/CASES.case_statistics` 支持缺省输入并由后端根据 `case_groups` 确定性派生；模型显式输出错误统计时仍触发 validation failure。
- `test_agent_runtime.py` 的 raw JSON streaming 门禁调整为：所有 artifact-data 阶段 final 前至少产生一个正式 `artifact_delta.output.artifact_update.replace.markdown`，最终 `AgentTurnOutput` 仍必须通过 contract；不再把全阶段多段字段级 partial 或 `artifact_patch` 当作当前已实现能力。
- structured-output chat 指令统一改为“自然短段落 / 按需短列表”，移除固定 `2 到 4 个短段落或短列表` 模板；artifact contract prompt 同步强调不要固定 bullet 数量，并补充 `artifact_update.markdown` 与 `artifact_data` 优先级关系。
- 后端 contract / endpoint 测试对齐当前 manifest 与 typed runtime：`VALUE_DISCOVERY/BLUEPRINT` handoff 目标包含 `STORY_BREAKDOWN/INPUT_ANALYSIS`，SSE error payload 精确断言 typed diagnostic，`TEST_DESIGN/DELIVERY` 视觉契约按 manifest 保持 `coverage-map`。
- `docs/TESTING.md` 明确字段级 partial renderer 当前仅覆盖 `TEST_DESIGN/CLARIFY`；其他阶段在完整顶层 `artifact_data` 对象可解析后生成 before-final delta。若后续要升级某阶段字段级 partial，必须补对应 partial renderer、子模型校验和聚焦测试。

RED / GREEN 证据：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_fails_final_json_truncation_after_partial_delta -q
```

结果：修复前返回带 `artifact_truncated` warning 的成功最终输出；修复后通过，`1 passed`。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_derives_statistics_when_missing tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_inconsistent_statistics tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_cases_after_case_groups_without_model_statistics -q
```

结果：`3 passed`。

宽回归：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -q
```

结果：`188 passed`。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_runtime.py -q
```

结果：`298 passed`。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py -q
```

结果：`153 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents Frontend `786 passed`；New Agents Backend `755 passed, 4 deselected`。

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 与 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`；非沙箱重跑通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `786 passed`、New Agents Backend `755 passed, 4 deselected`、New Agents Browser E2E `11 passed, 10 deselected`。

残余风险：

- 本轮不实现多阶段字段级 partial renderer，也不恢复 `artifact_patch` 全阶段断言；这属于后续 UX 增强，不影响当前 strict failure closure。
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

### 2026-07-09 切片记录：INCIDENT_REVIEW ROOT_CAUSE artifactDataContract 同步

触发原因：

- 继续盘点结构化失败治理时，`docs/TESTING.md` 与 `workflow_manifest.json` 均显示 25 个 artifact-data 阶段中只有 3 个阶段完成 `artifactDataContract` manifest sync，剩余 22 个阶段仍由 Pydantic model、renderer tests、runtime instruction 和 artifact contract tests 分散保护。
- `INCIDENT_REVIEW/ROOT_CAUSE` 已完成 `cause-map` 复杂视觉纵切，具备既有 renderer、visual contract、frontend parser / component 和导出降级证据，适合作为第 7 轮视觉治理与第 8 轮 contract 单源化之间的独立厚切片。

已修复：

- `INCIDENT_REVIEW/ROOT_CAUSE` 新增 `artifactDataContract` manifest 配置，把 5-Why 深度、`cause_evidence.cause_id` 唯一性、`cause_evidence.related_level` / `fishbone_categories.cause_ids` / `root_cause_conclusions.related_cause_id` 引用约束、根本原因结论要求、`stage_gate` 要求、禁止模型手写 Markdown / Mermaid / `cause-map` JSON，以及后端 renderer 负责输出 `ai4se-visual cause-map` / Mermaid `mindmap` 的边界放入单一配置源。
- 后端 contract sync 测试证明 `format_artifact_data_contract_instruction()` 从 manifest 生成 ROOT_CAUSE 结构化输出约束；前端 workflow 配置测试证明 ROOT_CAUSE 契约已暴露给共享 prompt 注入路径。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 3 个增加到 4 个，剩余待迁移阶段从 22 个减少到 21 个。

验证：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_incident_root_cause_artifact_data_contract_manifest_drives_backend_instruction -q
```

结果：修复前 `1 failed`，失败点为 ROOT_CAUSE `artifactDataContract` 缺失；修复后 `1 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts --run
```

结果：修复前 `1 failed`，失败点为 ROOT_CAUSE `artifactDataContract` 未暴露；修复后 `20 passed`。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_incident_root_cause_artifact_data_is_deterministic_and_contract_valid tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_incident_root_cause_artifact_data_rejects_insufficient_why_depth tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_incident_root_cause_artifact_data_rejects_duplicate_cause_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_incident_root_cause_artifact_data_rejects_unknown_fishbone_cause_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_incident_root_cause_artifact_data_rejects_unknown_conclusion_cause_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_incident_root_cause_artifact_data_requires_root_cause_conclusion -q
```

结果：`26 passed`。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py::test_incident_root_cause_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output -q
```

结果：`2 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：`74 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `787 passed`；New Agents Backend `756 passed, 4 deselected`。

残余风险：

- 本轮只迁移 `INCIDENT_REVIEW/ROOT_CAUSE`；当前已完成 `artifactDataContract` manifest sync 的阶段为 `IDEA_BRAINSTORM/CONVERGE`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE`，其余 21 个 artifact-data 阶段仍待后续纵切迁移。
- 本轮不新增 backend Mermaid JS parse 或 `mmdc` 渲染门禁；Mermaid 仍是后端 deterministic renderer 的编译目标，视觉强校验门禁仍需后续第 7 / 第 8 轮继续收口。

### 2026-07-09 切片记录：IDEA_BRAINSTORM DEFINE artifactDataContract 同步

触发原因：

- 继续盘点结构化失败治理时，`IDEA_BRAINSTORM/DEFINE` 仍是原始高失败阶段之一；第 4 轮已经修复 root-problem 覆盖与 evidence 引用不变量，但这些约束仍未进入 `artifactDataContract` manifest 单源。
- `workflow_manifest.json` 当前 25 个 artifact-data 阶段中已有 4 个完成 manifest sync；DEFINE 具备既有 Pydantic validator、deterministic renderer、runtime raw JSON streaming 和 prompt tests，适合作为第 8 轮后续 contract 单源化厚切片。

已修复：

- `IDEA_BRAINSTORM/DEFINE` 新增 `artifactDataContract` manifest 配置，把 `evidence_items[].evidence_id` 唯一性、`problem_landscape.subproblems[].problem_id` 唯一性、`problem_user_fit.evidence_ids` 引用约束、`problem_landscape.root_problem` 覆盖约束、`stage_gate` checked 要求、禁止模型手写 Markdown / Mermaid / mindmap 代码块，以及后端 renderer 负责输出右侧《问题域分析》和 Mermaid `mindmap` 的边界放入单一配置源。
- 后端 contract sync 测试证明 `format_artifact_data_contract_instruction()` 从 manifest 生成 DEFINE 结构化输出约束；前端 workflow 配置测试证明 DEFINE 契约已暴露；前端 system prompt 测试证明该契约会进入共享 prompt 注入路径，并沿用既有 `Mermaid` -> `图表` 的模型提示降噪逻辑。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 4 个增加到 5 个，剩余待迁移阶段从 21 个减少到 20 个。

验证：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_idea_define_artifact_data_contract_manifest_drives_backend_instruction -q
```

结果：修复前 `1 failed`，失败点为 DEFINE `artifactDataContract` 缺失；修复后 `1 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：修复前 `2 failed`，失败点为 DEFINE `artifactDataContract` 未暴露 / 未进入 system prompt；修复后 `76 passed`。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_idea_define_artifact_data_is_deterministic_and_contract_valid tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_rejects_duplicate_evidence_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_rejects_duplicate_problem_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_rejects_unknown_fit_evidence_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_requires_root_problem_coverage tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_requires_checked_stage_gate -q
```

结果：`27 passed`。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_idea_define_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_define_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_define_structured_output_instruction_explains_root_problem_coverage tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_define_artifact_data_before_final_output -q
```

结果：`4 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `789 passed`；New Agents Backend `757 passed, 4 deselected`。

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 与 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`；非沙箱重跑时确定性套件均通过，但当前环境启用了可选 LLM judge，`test_alex_to_lisa_handoff_passes_optional_llm_judge` 因外部 DeepSeek HTTPS `UNEXPECTED_EOF_WHILE_READING` 失败。

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

结果：非沙箱重跑通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `789 passed`、New Agents Backend `757 passed, 4 deselected`、New Agents Browser E2E `8 passed, 3 skipped, 10 deselected`。

残余风险：

- 本轮只迁移 `IDEA_BRAINSTORM/DEFINE`；当前已完成 `artifactDataContract` manifest sync 的阶段为 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/CONVERGE`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE`，其余 20 个 artifact-data 阶段仍待后续纵切迁移。
- 本轮不新增 backend Mermaid JS parse 或 `mmdc` 渲染门禁；Mermaid `mindmap` 仍由后端 deterministic renderer 生成，并由现有 artifact contract / visual contract 测试保护。

### 2026-07-09 切片记录：IDEA_BRAINSTORM DIVERGE artifactDataContract 同步

触发原因：

- 继续盘点结构化失败治理时，`IDEA_BRAINSTORM/DIVERGE` 仍是原始高失败阶段之一；第 5 轮已经修复 DIVERGE / CONVERGE partial preview 与 final validator 关键引用不变量对齐，但 DIVERGE 的关键约束仍未进入 `artifactDataContract` manifest 单源。
- `workflow_manifest.json` 当前 25 个 artifact-data 阶段中已有 5 个完成 manifest sync；DIVERGE 具备既有 Pydantic validator、deterministic renderer、runtime raw JSON streaming 和 prompt tests，适合作为第 8 轮后续 contract 单源化厚切片。
- 子智能体只读审查确认：DIVERGE 当前没有后端派生字段、没有 `ai4se-visual`，现有 validator 只覆盖 idea/source/parked record ID 唯一性、idea 引用完整性和 stage gate checked 要求；因此本轮不得虚构自动补齐、枚举校验、统计或结构化视觉能力。

已修复：

- `IDEA_BRAINSTORM/DIVERGE` 新增 `artifactDataContract` manifest 配置，把 `idea_cards[].idea_id`、`idea_sources[].source_id`、`parked_or_excluded[].record_id` 唯一性，`idea_landscape.groups[].idea_ids` / `idea_sources[].idea_ids` 引用约束，`stage_gate` checked 要求，禁止模型手写 Markdown / Mermaid / mindmap 代码块，以及后端 renderer 负责输出右侧《创意发散》和 Mermaid `mindmap` 的边界放入单一配置源。
- 后端 contract sync 测试证明 `format_artifact_data_contract_instruction()` 从 manifest 生成 DIVERGE 结构化输出约束；前端 workflow 配置测试证明 DIVERGE 契约已暴露；前端 system prompt 测试证明该契约会进入共享 prompt 注入路径，并沿用既有 `Mermaid` -> `图表` 的模型提示降噪逻辑。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 5 个增加到 6 个，剩余待迁移阶段从 20 个减少到 19 个。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_idea_diverge_artifact_data_contract_manifest_drives_backend_instruction -q
```

结果：修复前 `1 failed`，失败点为 DIVERGE `artifactDataContract` 缺失；修复后 `1 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "IDEA BRAINSTORM DIVERGE"
```

结果：修复前 `1 failed`，失败点为 DIVERGE `artifactDataContract` 未暴露；修复后 `1 passed, 21 skipped`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "IDEA BRAINSTORM DIVERGE"
```

结果：修复前 `1 failed`，失败点为 DIVERGE `artifactDataContract` 未进入 system prompt；修复后 `1 passed, 55 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_diverge_artifact_data_rejects_duplicate_idea_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_diverge_artifact_data_rejects_duplicate_source_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_diverge_artifact_data_rejects_duplicate_parked_record_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_diverge_artifact_data_rejects_unknown_landscape_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_diverge_artifact_data_rejects_unknown_source_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_diverge_artifact_data_requires_checked_stage_gate tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_idea_diverge_artifact_data_is_deterministic_and_contract_valid -q
```

结果：`29 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_idea_diverge_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_diverge_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_diverge_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output -q
```

结果：`4 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：`78 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `791 passed`；New Agents Backend `758 passed, 4 deselected`。

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 与 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`；脚本失败前后已完成 Intent Tester API、严重 lint、Common Frontend、New Agents Frontend / Backend，Browser E2E 因沙箱 Chromium 权限失败。

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

结果：非沙箱重跑通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `791 passed`、New Agents Backend `758 passed, 4 deselected`、New Agents Browser E2E `8 passed, 3 skipped, 10 deselected`。

残余风险：

- 本轮只迁移 `IDEA_BRAINSTORM/DIVERGE`；当前已完成 `artifactDataContract` manifest sync 的阶段为 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE`，其余 19 个 artifact-data 阶段仍待后续纵切迁移。
- 本轮不新增 DIVERGE 后端派生字段、自动 ID 分配、状态枚举校验、backend Mermaid JS parse 或 `mmdc` 渲染门禁；Mermaid `mindmap` 仍由后端 deterministic renderer 生成，并由现有 artifact contract / visual contract 测试保护。

### 2026-07-09 切片记录：IDEA_BRAINSTORM CONCEPT artifactDataContract 同步

触发原因：

- 继续推进第 8 轮 contract 单源化时，`IDEA_BRAINSTORM/DEFINE`、`DIVERGE`、`CONVERGE` 已完成 manifest sync，`CONCEPT` 是 IDEA_BRAINSTORM 工作流中剩余的最后一个 artifact-data 阶段。
- `CONCEPT` 已有 Pydantic validator、deterministic renderer、runtime raw JSON streaming 和 handoff 相关测试，但核心约束仍分散在后端硬编码 instruction、schema validator、renderer tests 与前端 prompt 中。
- 子智能体只读审查确认：CONCEPT 当前没有后端派生 artifact_data 字段；MVP pie 计数仅是 renderer 视觉输出；当前 validator 不校验 `premortem_risks[].risk_id` 唯一性，不校验 MVP level / likelihood 枚举或日期格式，也不自动补齐 Lean Canvas、增长漏斗或业务字段。因此本轮只把现有事实迁入 manifest，不虚构新能力。

已修复：

- `IDEA_BRAINSTORM/CONCEPT` 新增 `artifactDataContract` manifest 配置，把 `core_assumptions[].assumption_id`、`validation_roadmap[].validation_id`、`next_actions[].action_id` 唯一性，Lean Canvas 必备格、AARRR 增长漏斗必备 stage，MVP / validation / next action 引用门禁，`stage_gate` checked 要求，禁止模型手写 Markdown / Mermaid / `mvp-map` JSON / pie / flowchart 代码块，以及后端 renderer 负责输出右侧《产品概念简报》、`ai4se-visual mvp-map`、Mermaid pie 和 Mermaid flowchart 的边界放入单一配置源。
- 后端 contract sync 测试证明 `format_artifact_data_contract_instruction()` 从 manifest 生成 CONCEPT 结构化输出约束；前端 workflow 配置测试证明 CONCEPT 契约已暴露；前端 system prompt 测试证明该契约会进入共享 prompt 注入路径，并沿用既有 `Mermaid` -> `图表` 的模型提示降噪逻辑。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 6 个增加到 7 个，剩余待迁移阶段从 19 个减少到 18 个。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_idea_concept_artifact_data_contract_manifest_drives_backend_instruction -q
```

结果：修复前 `1 failed`，失败点为 CONCEPT `artifactDataContract` 缺失；修复后 `1 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "IDEA BRAINSTORM CONCEPT"
```

结果：修复前 `1 failed`，失败点为 CONCEPT `artifactDataContract` 未暴露；修复后 `1 passed, 22 skipped`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "IDEA BRAINSTORM CONCEPT"
```

结果：修复前 `1 failed`，失败点为 CONCEPT `artifactDataContract` 未进入 system prompt；修复后 `1 passed, 56 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_concept_artifact_data_rejects_duplicate_assumption_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_concept_artifact_data_rejects_duplicate_validation_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_concept_artifact_data_rejects_duplicate_action_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_concept_artifact_data_rejects_missing_lean_canvas_cell tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_concept_artifact_data_rejects_missing_growth_funnel_stage tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_concept_artifact_data_rejects_unknown_mvp_feature_assumption tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_concept_artifact_data_rejects_unknown_validation_assumption tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_concept_artifact_data_rejects_unknown_next_action_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_concept_artifact_data_requires_checked_stage_gate tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_idea_concept_artifact_data_is_deterministic_and_contract_valid -q
```

结果：`33 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_idea_concept_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_concept_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_concept_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_concept_artifact_data_before_final_output -q
```

结果：`4 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：`80 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `793 passed`；New Agents Backend `759 passed, 4 deselected`。

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 与 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`；失败前后 Intent Tester API、严重 lint、Common Frontend、New Agents Frontend / Backend 均已通过。

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

结果：非沙箱重跑通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `793 passed`、New Agents Backend `759 passed, 4 deselected`、New Agents Browser E2E `8 passed, 3 skipped, 10 deselected`。

残余风险：

- 本轮只迁移 `IDEA_BRAINSTORM/CONCEPT`；当前已完成 `artifactDataContract` manifest sync 的阶段为 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE`，其余 18 个 artifact-data 阶段仍待后续纵切迁移。
- 本轮不新增 CONCEPT 后端派生字段、风险 ID 唯一性、MVP level / likelihood 枚举、日期格式校验、自动 ID 分配、backend Mermaid JS parse 或 `mmdc` 渲染门禁；Mermaid pie / flowchart 和 `mvp-map` 仍由后端 deterministic renderer 生成，并由现有 artifact contract / visual contract 测试保护。

### 2026-07-09 切片记录：VALUE_DISCOVERY ELEVATOR artifactDataContract 同步

触发原因：

- `IDEA_BRAINSTORM` 四阶段已完成 manifest sync，继续推进 Alex 需求梳理主链路时，`VALUE_DISCOVERY/ELEVATOR` 是需求蓝图工作流入口，也是已有后端派生 `score_summary` 的阶段。
- `ELEVATOR` 已有 Pydantic validator、deterministic renderer、runtime raw JSON streaming 和 handoff 相关测试，但核心约束仍分散在后端硬编码 instruction、schema validator、renderer tests 与前端 prompt 中。
- 子智能体只读审查确认：ELEVATOR 当前真实业务 validator 只覆盖 `value_flow.nodes[].node_id` 唯一性、`value_flow.links[].from_node/to_node` 引用、`score_matrix[].score` 取值范围，以及 `score_summary.total_score` / `average_score` 的后端派生或显式一致性。本轮不得写成已存在 `pain_id` / `assumption_id` / `score_matrix.dimension` 唯一性、固定评分维度、状态枚举、stage_gate 全 checked、60 秒文案长度校验或“显式 score_summary 会被拒绝”等不存在能力。

已修复：

- `VALUE_DISCOVERY/ELEVATOR` 新增 `artifactDataContract` manifest 配置，把 value flow node ID 唯一性、flow link 引用门禁、score 取值范围、`score_summary.total_score` / `average_score` 后端派生或显式一致性、禁止模型手写 Markdown / Mermaid / `score-matrix` JSON，以及后端 renderer 负责输出右侧《价值定位分析》、Mermaid flowchart 和 `ai4se-visual score-matrix` 的边界放入单一配置源。
- 后端 contract sync 测试证明 `format_artifact_data_contract_instruction()` 从 manifest 生成 ELEVATOR 结构化输出约束；前端 workflow 配置测试证明 ELEVATOR 契约已暴露；前端 system prompt 测试证明该契约会进入共享 prompt 注入路径，并沿用既有 `Mermaid` -> `图表` 的模型提示降噪逻辑。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 7 个增加到 8 个，剩余待迁移阶段从 18 个减少到 17 个。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_value_elevator_artifact_data_contract_manifest_drives_backend_instruction -q
```

结果：修复前 `1 failed`，失败点为 ELEVATOR `artifactDataContract` 缺失；修复后 `1 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "VALUE DISCOVERY ELEVATOR"
```

结果：修复前 `1 failed`，失败点为 ELEVATOR `artifactDataContract` 未暴露；修复后 `1 passed, 23 skipped`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "VALUE DISCOVERY ELEVATOR"
```

结果：修复前 `1 failed`，失败点为 ELEVATOR `artifactDataContract` 未进入 system prompt；修复后 `1 passed, 57 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_value_elevator_artifact_data_rejects_inconsistent_score_summary tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_value_elevator_artifact_data_rejects_unknown_value_flow_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_value_elevator_artifact_data_is_deterministic_and_contract_valid -q
```

结果：`27 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_value_elevator_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_value_elevator_without_model_score_totals tools/new-agents/backend/tests/test_agent_runtime.py::test_value_elevator_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_value_elevator_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_elevator_artifact_data_before_final_output -q
```

结果：`5 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：`82 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `795 passed`；New Agents Backend `760 passed, 4 deselected`。

```bash
./scripts/test/test-local.sh all
```

结果：默认沙箱运行被环境权限限制阻断。已完成 Intent Tester API `294 passed`、flake8 严重错误检查通过、Common Frontend lint/build 通过、New Agents Frontend `795 passed`、New Agents Backend `760 passed, 4 deselected`；MidScene proxy 在沙箱下因 `listen EPERM: operation not permitted 0.0.0.0:3002` 失败，Browser E2E 因 Playwright / Chromium 沙箱权限限制被中断。

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

结果：非沙箱全量验证通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `795 passed`、New Agents Backend `760 passed, 4 deselected`、New Agents Browser E2E `8 passed, 3 skipped, 10 deselected`。

残余风险：

- 本轮只迁移 `VALUE_DISCOVERY/ELEVATOR`；当前已完成 `artifactDataContract` manifest sync 的阶段为 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE`，其余 17 个 artifact-data 阶段仍待后续纵切迁移。
- 本轮不新增 ELEVATOR 后端派生字段之外的自动 ID 分配，不新增 pain / assumption / score dimension 唯一性，不新增状态枚举、stage_gate 全 checked、60 秒演讲长度校验、backend Mermaid JS parse 或 `mmdc` 渲染门禁；Mermaid flowchart 和 `score-matrix` 仍由后端 deterministic renderer 生成，并由现有 artifact contract / visual contract 测试保护。

### 2026-07-09 切片记录：VALUE_DISCOVERY PERSONA artifactDataContract 同步

触发原因：

- `VALUE_DISCOVERY/ELEVATOR` 已完成 manifest sync；继续推进 Alex 需求蓝图梳理链路时，`VALUE_DISCOVERY/PERSONA` 是紧接价值定位之后的用户画像阶段。
- `PERSONA` 已有 Pydantic validator、deterministic renderer 和 runtime raw JSON streaming 测试，但关键 persona 引用约束仍未进入 `artifactDataContract` manifest 单源。
- 子智能体只读审查确认：PERSONA 当前真实业务 validator 只覆盖 `personas[].persona_id` 唯一性，`behavior_scenarios` / `decision_chain` / `pain_evidence` / `priority_ranking` 的 persona 引用，以及 `priority_ranking[].persona_id` 唯一性；PERSONA 没有 Mermaid / `ai4se-visual` required visual，也不做字段派生或归一化。

已修复：

- `VALUE_DISCOVERY/PERSONA` 新增 `artifactDataContract` manifest 配置，把 persona ID 唯一性、行为场景 / 决策链 / 痛点证据 / 优先级排序 persona 引用门禁、优先级排序 persona 去重、禁止模型手写完整 Markdown / Markdown 表格，以及后端 renderer 负责输出右侧《用户画像分析》和相关 Markdown 表格的边界放入单一配置源。
- 后端 contract sync 测试证明 `format_artifact_data_contract_instruction()` 从 manifest 生成 PERSONA 结构化输出约束；前端 workflow 配置测试证明 PERSONA 契约已暴露；前端 system prompt 测试证明该契约会进入共享 prompt 注入路径。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 8 个增加到 9 个，剩余待迁移阶段从 17 个减少到 16 个。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_value_persona_artifact_data_contract_manifest_drives_backend_instruction -q
```

结果：修复前 `1 failed`，失败点为 PERSONA `artifactDataContract` 缺失；修复后 `1 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "VALUE DISCOVERY PERSONA"
```

结果：修复前 `1 failed`，失败点为 PERSONA `artifactDataContract` 未暴露；修复后 `1 passed, 24 skipped`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "VALUE DISCOVERY PERSONA"
```

结果：修复前 `1 failed`，失败点为 PERSONA `artifactDataContract` 未进入 system prompt；修复后 `1 passed, 58 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_value_persona_artifact_data_rejects_unknown_persona_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_value_persona_artifact_data_rejects_duplicate_priority_persona tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_value_persona_artifact_data_is_deterministic_and_contract_valid -q
```

结果：`28 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_value_persona_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_value_persona_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_value_persona_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_persona_artifact_data_before_final_output -q
```

结果：`4 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：`84 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `797 passed`；New Agents Backend `761 passed, 4 deselected`。

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

结果：非沙箱全量验证通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `797 passed`、New Agents Backend `761 passed, 4 deselected`、New Agents Browser E2E `8 passed, 3 skipped, 10 deselected`。

残余风险：

- 本轮只迁移 `VALUE_DISCOVERY/PERSONA`；当前已完成 `artifactDataContract` manifest sync 的阶段为 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE`，其余 16 个 artifact-data 阶段仍待后续纵切迁移。
- 本轮不新增 PERSONA 字段派生、自动 ID 分配、`priority_ranking[].related_pain` 引用校验、`scenario_id` / `pain_id` / `role` 唯一性、枚举强校验、stage_gate checked 要求、使用者 / 决策者 / 付费者三类角色强校验、Mermaid / `ai4se-visual` 输出或 backend Mermaid JS parse / `mmdc` 渲染门禁。

### 2026-07-09 切片记录：VALUE_DISCOVERY JOURNEY artifactDataContract 同步

触发原因：

- `VALUE_DISCOVERY/PERSONA` 已完成 manifest sync；继续推进 Alex 需求蓝图梳理链路时，`VALUE_DISCOVERY/JOURNEY` 是用户画像之后的旅程分析阶段。
- `JOURNEY` 已有 Pydantic validator、deterministic renderer、visual contract 和 runtime raw JSON streaming 测试，但 stage / pain / opportunity 引用约束仍未进入 `artifactDataContract` manifest 单源。
- 本地只读审查确认：JOURNEY 当前真实业务 validator 覆盖 `journey_stages[].stage_id`、`pain_id`、`opportunity_id` 唯一性，`emotion_score` 1-5 字段约束，`pain_priorities.stage_id`、痛点引用和机会引用门禁；JOURNEY 由后端 renderer 输出 Mermaid `journey` 和 `ai4se-visual journey-map`。

已修复：

- `VALUE_DISCOVERY/JOURNEY` 新增 `artifactDataContract` manifest 配置，把 journey stage / pain / opportunity ID 唯一性、emotion score 取值范围、旅程阶段 / 痛点 / 机会引用门禁、禁止模型手写完整 Markdown / Markdown 表格 / Mermaid / `journey-map` JSON，以及后端 renderer 负责输出右侧《用户旅程分析》、Mermaid `journey` 和 `ai4se-visual journey-map` 的边界放入单一配置源。
- 后端 contract sync 测试证明 `format_artifact_data_contract_instruction()` 从 manifest 生成 JOURNEY 结构化输出约束；前端 workflow 配置测试证明 JOURNEY 契约已暴露；前端 system prompt 测试证明该契约会进入共享 prompt 注入路径，并沿用既有 `Mermaid` -> `图表` 的模型提示降噪逻辑。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 9 个增加到 10 个，剩余待迁移阶段从 16 个减少到 15 个。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_value_journey_artifact_data_contract_manifest_drives_backend_instruction -q
```

结果：修复前 `1 failed`，失败点为 JOURNEY `artifactDataContract` 缺失；修复后 `1 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "VALUE DISCOVERY JOURNEY"
```

结果：修复前 `1 failed`，失败点为 JOURNEY `artifactDataContract` 未暴露；修复后 `1 passed, 25 skipped`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "VALUE DISCOVERY JOURNEY"
```

结果：修复前 `1 failed`，失败点为 JOURNEY `artifactDataContract` 未进入 system prompt；修复后 `1 passed, 59 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_value_journey_artifact_data_rejects_unknown_stage_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_value_journey_artifact_data_rejects_unknown_opportunity_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_value_journey_artifact_data_is_deterministic_and_contract_valid -q
```

结果：`29 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_value_journey_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_value_journey_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_value_journey_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_journey_artifact_data_before_final_output -q
```

结果：`4 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：`86 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `799 passed`；New Agents Backend `762 passed, 4 deselected`。

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

结果：非沙箱全量验证通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `799 passed`、New Agents Backend `762 passed, 4 deselected`、New Agents Browser E2E `8 passed, 3 skipped, 10 deselected`。

残余风险：

- 本轮只迁移 `VALUE_DISCOVERY/JOURNEY`；当前已完成 `artifactDataContract` manifest sync 的阶段为 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`TEST_DESIGN/CASES`、`TEST_DESIGN/STRATEGY` 与 `INCIDENT_REVIEW/ROOT_CAUSE`，其余 15 个 artifact-data 阶段仍待后续纵切迁移。
- 本轮不新增 JOURNEY 字段派生、自动 ID 分配、`priority_level` 枚举、RICE / Kano 数值评分计算、实验 owner / status 枚举、stage_gate checked 要求、backend Mermaid JS parse 或 `mmdc` 渲染门禁；Mermaid `journey` 和 `journey-map` 仍由后端 deterministic renderer 生成，并由现有 artifact contract / visual contract 测试保护。

### 2026-07-09 切片记录：TEST_DESIGN artifactDataContract 同步

触发原因：

- 用户明确修正切片口径：默认一个 workflow 一个切片；若工作过大，拆成多个同级切片，不允许内部批次。因此本轮把 `TEST_DESIGN/CLARIFY` 与 `TEST_DESIGN/DELIVERY` 作为同一个 TEST_DESIGN workflow 级切片收口，而不是拆成两个阶段级切片。
- `TEST_DESIGN/STRATEGY` 与 `TEST_DESIGN/CASES` 已完成 manifest sync，测试设计工作流只剩首尾两个 artifact-data 阶段仍未进入 `artifactDataContract` 单源。
- 子智能体只读审查确认：CLARIFY 当前真实 validator 只覆盖 8 个必填列表和非空字符串；后端由 `flow_links` deterministic 生成 Mermaid `flowchart`。DELIVERY 当前真实 validator 覆盖用例摘要统计、交付指标总数 / 高风险数一致性，以及 `coverage_map[].case_ids` 非空；后端由 `coverage_map` 生成 `ai4se-visual coverage-map`。本轮不得虚构自动 ID 分配、跨阶段引用、枚举、日期格式、stage gate checked 强制要求或 backend Mermaid JS parse / `mmdc` 能力。

已修复：

- `TEST_DESIGN/CLARIFY` 新增 `artifactDataContract` manifest 配置，把 required list、非空字符串、禁止模型手写完整 Markdown / Markdown 表格 / Mermaid 代码块，以及后端 renderer 负责输出右侧需求分析文档和 Mermaid `flowchart` 的边界放入单一配置源。
- `TEST_DESIGN/DELIVERY` 新增 `artifactDataContract` manifest 配置，把 `case_summary_items[].case_count` 与 P0/P1/P2 一致性、`delivery_metrics.total_cases`、`delivery_metrics.high_risk_count`、`coverage_map[].case_ids` 非空、禁止模型手写完整 Markdown / Markdown 表格 / Mermaid / `coverage-map` JSON，以及后端 renderer 负责输出右侧测试设计交付包和 `ai4se-visual coverage-map` 的边界放入单一配置源。
- 后端 contract sync 测试证明 `format_artifact_data_contract_instruction()` 从 manifest 生成 CLARIFY / DELIVERY 结构化输出约束；前端 workflow 配置测试证明两个阶段契约已暴露；前端 system prompt 测试证明契约进入共享 prompt 注入路径。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 10 个增加到 12 个，剩余待迁移阶段从 15 个减少到 13 个。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_test_design_clarify_artifact_data_contract_manifest_drives_backend_instruction tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_test_design_delivery_artifact_data_contract_manifest_drives_backend_instruction -q
```

结果：修复前 `2 failed`，失败点为 CLARIFY / DELIVERY `artifactDataContract` 缺失；修复后 `2 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "TEST DESIGN"
```

结果：修复前 `2 failed, 2 passed, 24 skipped`，失败点为 CLARIFY / DELIVERY `artifactDataContract` 未暴露；修复后 `4 passed, 24 skipped`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "TEST DESIGN"
```

结果：修复前 `2 failed, 1 passed, 59 skipped`，失败点为 CLARIFY / DELIVERY `artifactDataContract` 未进入 system prompt；修复后 `3 passed, 59 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_clarify_artifact_data_rejects_blank_required_values tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_clarify_artifact_data_rejects_empty_required_lists tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_clarify_artifact_data_is_deterministic_and_contract_valid tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_delivery_artifact_data_rejects_inconsistent_case_totals tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_delivery_artifact_data_is_deterministic_and_contract_valid -q
```

结果：`33 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_delivery_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_delivery_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_delivery_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output -q
```

结果：`6 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：`90 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `803 passed`；New Agents Backend `764 passed, 4 deselected`。

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 和 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`；非沙箱重跑通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `803 passed`、New Agents Backend `764 passed, 4 deselected`、New Agents Browser E2E `8 passed, 3 skipped, 10 deselected`。

残余风险：

- 本轮只迁移 `TEST_DESIGN/CLARIFY` 与 `TEST_DESIGN/DELIVERY`；当前已完成 `artifactDataContract` manifest sync 的阶段为 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`TEST_DESIGN/CLARIFY`、`TEST_DESIGN/STRATEGY`、`TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY` 与 `INCIDENT_REVIEW/ROOT_CAUSE`，其余 13 个 artifact-data 阶段仍待后续 workflow 级切片迁移。
- 本轮不新增 CLARIFY / DELIVERY 字段派生、自动 ID 分配、跨阶段引用、枚举强校验、日期格式校验、stage_gate checked 要求、字段级 partial renderer、backend Mermaid JS parse 或 `mmdc` 渲染门禁；Mermaid `flowchart` 与 `coverage-map` 仍由后端 deterministic renderer 生成，并由现有 artifact contract / visual contract 测试保护。

### 2026-07-09 切片记录：REQ_REVIEW artifactDataContract 同步

触发原因：

- `TEST_DESIGN` workflow 级切片完成后，按“一个 workflow 一个切片”口径继续推进后续同级切片；`REQ_REVIEW/REVIEW` 与 `REQ_REVIEW/REPORT` 同属需求评审闭环，适合作为一个 workflow 级切片收口。
- `REQ_REVIEW` 已有 Pydantic validator、deterministic renderer、visual contract 和 runtime raw JSON streaming 测试，但关键问题统计 / 引用 / 结论门禁仍未进入 `artifactDataContract` manifest 单源。
- 子智能体只读审查确认：REVIEW 当前真实 validator 覆盖 `quality_overview[].severity_score` 1-5、问题 ID 唯一性、`issue_statistics` 与 `issue_groups` 优先级计数一致、`revision_suggestions.related_issues` 引用完整性；REPORT 当前真实 validator 覆盖问题关闭项 ID 唯一性、`issue_statistics` 与 `issue_closures` 优先级计数一致、`review_conditions.related_issues` 引用完整性，以及开放 P0/P1 时 `review_result` 不能为“通过”。本轮不得虚构枚举、ID 格式、日期格式、stage_gate checked、跨阶段 REVIEW 问题完整继承、字段级 partial renderer 或 backend Mermaid JS parse / `mmdc` 能力。

已修复：

- `REQ_REVIEW/REVIEW` 新增 `artifactDataContract` manifest 配置，把必填列表、严重度评分范围、问题 ID 唯一性、问题统计一致性、修订建议问题引用、禁止模型手写完整 Markdown / Markdown 表格 / Mermaid / `score-matrix` JSON，以及后端 renderer 负责输出右侧需求评审问题清单、Mermaid `flowchart` 和 `ai4se-visual score-matrix` 的边界放入单一配置源。
- `REQ_REVIEW/REPORT` 新增 `artifactDataContract` manifest 配置，把必填列表、问题关闭项 ID 唯一性、问题统计一致性、复审条件问题引用、开放 P0/P1 的结论门禁、禁止模型手写完整 Markdown / Markdown 表格 / Mermaid / `priority-board` JSON，以及后端 renderer 负责输出右侧需求评审报告、Mermaid `pie` 和 `ai4se-visual priority-board` 的边界放入单一配置源。
- 后端 contract sync 测试证明 `format_artifact_data_contract_instruction()` 从 manifest 生成 REVIEW / REPORT 结构化输出约束；前端 workflow 配置测试证明两个阶段契约已暴露；前端 system prompt 测试证明契约进入共享 prompt 注入路径。
- 新增 REVIEW / REPORT validator 负向测试，补齐 duplicate issue、未知引用、严重度越界和开放 P0/P1 不能通过等 manifest 关键约束的直接证据。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 12 个增加到 14 个，剩余待迁移阶段从 13 个减少到 11 个。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_req_review_review_artifact_data_contract_manifest_drives_backend_instruction tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_req_review_report_artifact_data_contract_manifest_drives_backend_instruction -q
```

结果：修复前 `2 failed`，失败点为 REVIEW / REPORT `artifactDataContract` 缺失；修复后 `2 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "REQ REVIEW"
```

结果：修复前 `2 failed, 28 skipped`，失败点为 REVIEW / REPORT `artifactDataContract` 未暴露；修复后 `2 passed, 28 skipped`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "REQ REVIEW"
```

结果：修复前 `2 failed, 62 skipped`，失败点为 REVIEW / REPORT `artifactDataContract` 未进入 system prompt；修复后 `2 passed, 62 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_artifact_data_rejects_inconsistent_issue_statistics tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_artifact_data_rejects_duplicate_issue_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_artifact_data_rejects_unknown_revision_issue_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_artifact_data_rejects_out_of_range_quality_score tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_report_artifact_data_rejects_inconsistent_issue_statistics tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_report_artifact_data_rejects_duplicate_issue_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_report_artifact_data_rejects_unknown_review_condition_issue_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_report_artifact_data_rejects_passing_result_with_open_p0_or_p1 -q
```

结果：`8 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_artifact_data_rejects_inconsistent_issue_statistics tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_artifact_data_rejects_duplicate_issue_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_artifact_data_rejects_unknown_revision_issue_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_artifact_data_rejects_out_of_range_quality_score tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_req_review_artifact_data_is_deterministic_and_contract_valid tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_report_artifact_data_rejects_inconsistent_issue_statistics tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_report_artifact_data_rejects_duplicate_issue_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_report_artifact_data_rejects_unknown_review_condition_issue_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_req_review_report_artifact_data_rejects_passing_result_with_open_p0_or_p1 tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_req_review_report_artifact_data_is_deterministic_and_contract_valid -q
```

结果：`40 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_req_review_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_req_review_report_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_req_review_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_req_review_report_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output -q
```

结果：`6 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：`94 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `807 passed`；New Agents Backend `772 passed, 4 deselected`。

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

结果：非沙箱全量验证通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `807 passed`、New Agents Backend `772 passed, 4 deselected`、New Agents Browser E2E `8 passed, 3 skipped, 10 deselected`。

残余风险：

- 本轮只迁移 `REQ_REVIEW/REVIEW` 与 `REQ_REVIEW/REPORT`；当前已完成 `artifactDataContract` manifest sync 的阶段为 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`TEST_DESIGN/CLARIFY`、`TEST_DESIGN/STRATEGY`、`TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY`、`REQ_REVIEW/REVIEW`、`REQ_REVIEW/REPORT` 与 `INCIDENT_REVIEW/ROOT_CAUSE`，其余 11 个 artifact-data 阶段仍待后续 workflow 级切片迁移。
- 本轮不新增 REQ_REVIEW 字段派生、自动 ID 分配、严格枚举、ID / 日期 / 版本格式、REPORT stage_gate、跨阶段 REVIEW 问题完整继承、字段级 partial renderer、backend Mermaid JS parse 或 `mmdc` 渲染门禁；Mermaid `flowchart` / `pie` 与 `score-matrix` / `priority-board` 仍由后端 deterministic renderer 生成，并由现有 artifact contract / visual contract 测试保护。

### 2026-07-09 切片记录：INCIDENT_REVIEW 剩余阶段 artifactDataContract 同步

触发原因：

- `REQ_REVIEW` workflow 级切片完成后，按“一个 workflow 一个切片”口径继续推进后续同级切片；`INCIDENT_REVIEW/ROOT_CAUSE` 已完成，`TIMELINE` 与 `IMPROVEMENT` 是同一故障复盘闭环中剩余两个 artifact-data 阶段，适合作为一个 workflow 级切片收口。
- `INCIDENT_REVIEW/TIMELINE` 与 `INCIDENT_REVIEW/IMPROVEMENT` 已有 Pydantic validator、deterministic renderer、visual contract 和 runtime raw JSON streaming 测试，但关键事实引用、行动统计和根因覆盖约束仍未进入 `artifactDataContract` manifest 单源。
- 子智能体只读审查确认：TIMELINE 当前真实 validator 只覆盖必填列表、非空标量字符串、`fact_sources[].fact_id` 唯一性、`timeline_events[].fact_ids` 非空和引用完整性；IMPROVEMENT 当前真实 validator 只覆盖行动数量、优先级分布、action ID 唯一性、coverage cause ID 唯一性、coverage/action/root_cause 引用完整性和已覆盖根因必须有 action_ids。本轮不得虚构枚举、日期格式、时间排序、stage_gate checked、跨阶段完整正文保留、字段级 partial renderer、backend Mermaid JS parse 或 `mmdc` 能力。

已修复：

- `INCIDENT_REVIEW/TIMELINE` 新增 `artifactDataContract` manifest 配置，把必填列表、`timeline_events[].fact_ids` 非空、事实 ID 唯一性、时间线事实引用、禁止模型手写完整 Markdown / Markdown 表格 / Mermaid 代码块，以及后端 renderer 负责输出右侧故障复盘事件还原和 Mermaid `timeline` 的边界放入单一配置源。
- `INCIDENT_REVIEW/IMPROVEMENT` 新增 `artifactDataContract` manifest 配置，把必填列表、`report_info.action_count` 与改进行动数量一致性、action ID 唯一性、优先级分布一致性、coverage cause ID 唯一性、coverage action 引用、action root cause 引用、已覆盖根因必须有 action_ids、禁止模型手写完整 Markdown / Markdown 表格 / Mermaid / `pie` / `action-board` JSON，以及后端 renderer 负责输出右侧最终故障复盘报告、Mermaid `pie` 和 `ai4se-visual action-board` 的边界放入单一配置源。
- 后端 `build_structured_output_instruction()` 的 TIMELINE / IMPROVEMENT 常量改为消费 `format_artifact_data_contract_instruction()`，避免 manifest 只存在于 helper 测试而没有进入 runtime prompt。
- 新增 backend/frontend sync 测试：backend manifest instruction、backend runtime instruction、frontend workflow 配置和 frontend system prompt 注入均覆盖 TIMELINE / IMPROVEMENT。
- 新增 `test_incident_improvement_artifact_data_rejects_duplicate_root_cause_coverage_cause_id`，补齐已实现但此前缺少直接测试的 coverage cause ID 唯一性回归。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 14 个增加到 16 个，剩余待迁移阶段从 11 个减少到 9 个。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "incident_timeline_artifact_data_contract or incident_improvement_artifact_data_contract"
```

结果：修复前 `2 failed`，失败点为 TIMELINE / IMPROVEMENT `artifactDataContract` 缺失；修复后 `2 passed`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "INCIDENT REVIEW TIMELINE|INCIDENT REVIEW IMPROVEMENT"
```

结果：修复前 `2 failed, 30 skipped`，失败点为 TIMELINE / IMPROVEMENT `artifactDataContract` 未暴露；修复后 `2 passed, 30 skipped`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "INCIDENT REVIEW TIMELINE|INCIDENT REVIEW IMPROVEMENT"
```

结果：修复前 `2 failed, 64 skipped`，失败点为 TIMELINE / IMPROVEMENT `artifactDataContract` 未进入 system prompt；修复后 `2 passed, 64 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k "incident_timeline_structured_output_instruction or incident_improvement_structured_output_instruction"
```

结果：`2 passed, 186 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k "incident_improvement_artifact_data_rejects_duplicate_root_cause_coverage_cause_id or incident_timeline_artifact_data_rejects or incident_improvement_artifact_data_rejects"
```

结果：`9 passed, 89 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

结果：`32 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k "incident_timeline or incident_root_cause or incident_improvement"
```

结果：`17 passed, 81 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k "incident_timeline or incident_root_cause or incident_improvement"
```

结果：`12 passed, 176 deselected`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：`98 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `811 passed`；New Agents Backend `775 passed, 4 deselected`。

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

结果：默认沙箱失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 和 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`；非沙箱重跑通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `811 passed`、New Agents Backend `775 passed, 4 deselected`、New Agents Browser E2E `8 passed, 3 skipped, 10 deselected`。

残余风险：

- 本轮只迁移 `INCIDENT_REVIEW/TIMELINE` 与 `INCIDENT_REVIEW/IMPROVEMENT`；当前已完成 `artifactDataContract` manifest sync 的阶段为 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`TEST_DESIGN/CLARIFY`、`TEST_DESIGN/STRATEGY`、`TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY`、`REQ_REVIEW/REVIEW`、`REQ_REVIEW/REPORT`、`INCIDENT_REVIEW/TIMELINE`、`INCIDENT_REVIEW/ROOT_CAUSE` 与 `INCIDENT_REVIEW/IMPROVEMENT`，其余 9 个 artifact-data 阶段仍待后续 workflow 级切片迁移。
- 本轮不新增 INCIDENT_REVIEW 字段派生、自动 ID 分配、严格枚举、日期 / 时间格式、时间线排序、stage_gate checked、跨阶段完整正文继承、字段级 partial renderer、backend Mermaid JS parse 或 `mmdc` 渲染门禁；Mermaid `timeline` / `pie` 与 `action-board` 仍由后端 deterministic renderer 生成，并由现有 artifact contract / visual contract 测试保护。

### 2026-07-09 切片记录：VALUE_DISCOVERY/BLUEPRINT artifactDataContract 同步

触发原因：

- `INCIDENT_REVIEW` 剩余阶段切片完成后，按“一个 workflow 一个切片”口径继续推进下一同级切片；`VALUE_DISCOVERY/BLUEPRINT` 是 Alex 从价值发现走向需求蓝图、Story Breakdown 和 Lisa handoff 的关键出口，适合作为单独 workflow 出口切片收口。
- `VALUE_DISCOVERY/BLUEPRINT` 已有 Pydantic validator、deterministic renderer、visual contract、runtime raw JSON streaming 和 handoff 路径测试，但关键 requirement / acceptance / flow 引用约束仍未进入 `artifactDataContract` manifest 单源。
- 子智能体 Euler 只读审查确认：BLUEPRINT 当前真实 validator 只覆盖非空字符串、必填列表、额外字段禁止、需求 ID 唯一、验收标准 ID 唯一、需求引用完整、验收 handoff 引用完整、主流程节点唯一和主流程 link 引用完整；不得虚构 P0/P1/P2 枚举、日期格式、owner/status 枚举、stage_gate checked、roadmap 与 MVP 一致、风险/数据/依赖 handoff 引用、feature/module ID 唯一或 backend Mermaid parse 能力。

已修复：

- `VALUE_DISCOVERY/BLUEPRINT` 新增 `artifactDataContract` manifest 配置，把需求 ID 唯一性、验收标准 ID 唯一性、功能 / MVP / 验收 / Lisa handoff 需求引用、Lisa handoff 验收标准引用、主流程节点唯一性、流程 link 引用、禁止模型手写完整 Markdown / Markdown 表格 / Mermaid / roadmap JSON，以及后端 renderer 负责输出右侧需求蓝图、Mermaid `mindmap`、Mermaid `flowchart` 和 `ai4se-visual roadmap` 的边界放入单一配置源。
- 后端 `build_structured_output_instruction()` 的 BLUEPRINT 常量改为消费 `format_artifact_data_contract_instruction("VALUE_DISCOVERY", "BLUEPRINT")`，避免 runtime prompt 继续维护手写约束。
- 新增 backend/frontend sync 测试：backend manifest instruction、backend runtime instruction、frontend workflow 配置和 frontend system prompt 注入均覆盖 BLUEPRINT。
- 补齐 BLUEPRINT renderer validator 负向测试：重复 `requirement_id`、重复 `acceptance_id`、未知功能 / MVP / handoff 需求引用、未知验收标准 handoff 引用、重复主流程节点 ID、未知主流程节点引用。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 16 个增加到 17 个，剩余待迁移阶段从 9 个减少到 8 个。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "value_blueprint_artifact_data_contract"
```

结果：修复前 `1 failed, 32 deselected`，失败点为 BLUEPRINT `artifactDataContract` 缺失；修复后 `1 passed, 32 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k "value_blueprint_structured_output_instruction"
```

结果：修复前 `1 failed, 187 deselected`，失败点为 BLUEPRINT runtime instruction 未包含 manifest contract instruction；修复后 `1 passed, 187 deselected`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "VALUE DISCOVERY BLUEPRINT"
```

结果：修复前 `1 failed, 32 skipped`，失败点为 BLUEPRINT `artifactDataContract` 未暴露；修复后 `1 passed, 32 skipped`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "VALUE DISCOVERY BLUEPRINT"
```

结果：修复前 `1 failed, 66 skipped`，失败点为 BLUEPRINT `artifactDataContract` 未进入 system prompt；修复后 `1 passed, 66 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k "value_blueprint"
```

结果：`10 passed, 95 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

结果：`33 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k "value_blueprint"
```

结果：`4 passed, 184 deselected`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：`100 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `813 passed`；New Agents Backend `783 passed, 4 deselected`。

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

结果：非沙箱全量验证通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `813 passed`、New Agents Backend `783 passed, 4 deselected`、New Agents Browser E2E `8 passed, 3 skipped, 10 deselected`。

残余风险：

- 本轮只迁移 `VALUE_DISCOVERY/BLUEPRINT`；当前已完成 `artifactDataContract` manifest sync 的阶段为 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`VALUE_DISCOVERY/BLUEPRINT`、`TEST_DESIGN/CLARIFY`、`TEST_DESIGN/STRATEGY`、`TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY`、`REQ_REVIEW/REVIEW`、`REQ_REVIEW/REPORT`、`INCIDENT_REVIEW/TIMELINE`、`INCIDENT_REVIEW/ROOT_CAUSE` 与 `INCIDENT_REVIEW/IMPROVEMENT`，其余 8 个 artifact-data 阶段仍待后续 workflow 级切片迁移。
- 本轮不新增 BLUEPRINT 字段派生、自动 ID 分配、严格枚举、日期格式、owner/status 枚举、stage_gate checked、roadmap 与 MVP 一致性、风险/数据/依赖 handoff 引用、feature/module ID 唯一、字段级 partial renderer、backend Mermaid JS parse 或 `mmdc` 渲染门禁；Mermaid `mindmap` / `flowchart` 与 `roadmap` 仍由后端 deterministic renderer 生成，并由现有 artifact contract / visual contract 测试保护。

### 2026-07-09 切片记录：STORY_BREAKDOWN artifactDataContract 同步

触发原因：

- `VALUE_DISCOVERY/BLUEPRINT` 切片完成后，按“一个 workflow 一个切片”口径继续推进 `STORY_BREAKDOWN`。该工作流是 Alex 从需求蓝图走向用户故事、Sprint 切片和 AI Coding 单故事需求包的关键出口。
- 当前 `STORY_BREAKDOWN` 四阶段已在 runtime 中使用 `artifact_data` 和 deterministic renderer，但 manifest 缺少 `artifactDataContract`，frontend prompt 也没有可注入的结构化契约区块。
- 子智能体只读审查确认：四阶段共享同一个 `StoryBreakdownArtifactData` schema 和同一个 renderer；真实强校验仅包含必需字段、额外字段禁止、直接字符串非空、关键数组非空、ID 唯一性、Epic / Story / Criterion / Dependency / Sprint / Lisa handoff 引用、`story_points >= 1` 与 `stage_gate` checked。不得虚构 priority / status / ready 枚举、P0 必须验收、两轮 Sprint、日期格式或 `user_stories[].sprint` 与 `sprint_slices[].sprint_id` 一致性等未实现规则。

已修复：

- `STORY_BREAKDOWN/INPUT_ANALYSIS`、`EPIC_MAPPING`、`STORY_BACKLOG`、`SPRINT_PLAN` 新增同一组 `artifactDataContract` manifest 配置，覆盖真实 schema / validator 强约束、禁止模型输出 renderer-owned Markdown / Mermaid / story-map JSON，以及后端 renderer 负责输出右侧用户故事拆解包、Mermaid `flowchart` 和 `ai4se-visual story-map`。
- 后端 `_story_breakdown_artifact_data_instruction()` 改为按 stage 注入 `format_artifact_data_contract_instruction("STORY_BREAKDOWN", stage_id)`，保留原 JSON shape 和各阶段 `stage_action`。
- 新增 backend/frontend sync 测试：backend manifest instruction、backend runtime instruction、frontend workflow 配置和 frontend system prompt 注入均覆盖 STORY_BREAKDOWN 四阶段。
- 补齐 STORY_BREAKDOWN renderer validator 负向测试：重复 Epic / Story / Criterion ID、未知 Epic / dependency / sprint / handoff 引用、unchecked stage gate、`story_points < 1` 和额外字段。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 17 个增加到 21 个，剩余待迁移阶段从 8 个减少到 4 个。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k story_breakdown_artifact_data_contract
```

结果：修复前 `1 failed, 33 deselected`，失败点为 `STORY_BREAKDOWN/INPUT_ANALYSIS` 缺少 `artifactDataContract`；修复后 `1 passed, 33 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k story_breakdown_structured_output_instruction
```

结果：修复前 `4 failed, 1 passed, 187 deselected`，失败点为四阶段 runtime instruction 未包含 manifest contract instruction；修复后 `5 passed, 187 deselected`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "STORY BREAKDOWN"
```

结果：修复前 `1 failed, 33 skipped`，失败点为 STORY `artifactDataContract` 未暴露；修复后 `1 passed, 33 skipped`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "STORY BREAKDOWN"
```

结果：修复前 `4 failed, 67 skipped`，失败点为 STORY 四阶段 system prompt 缺少 `【artifact_data 结构化契约】`；修复后 `4 passed, 67 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k story_breakdown
```

结果：`13 passed, 103 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

结果：`34 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k story_breakdown
```

结果：`24 passed, 168 deselected`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：`105 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `818 passed`；New Agents Backend `799 passed, 4 deselected`。

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

结果：沙箱运行失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 和 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`；非沙箱重跑通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `818 passed`、New Agents Backend `799 passed, 4 deselected`、New Agents Browser E2E `8 passed, 3 skipped, 10 deselected`。

残余风险：

- 本轮只迁移 `STORY_BREAKDOWN` 四阶段；当前已完成 `artifactDataContract` manifest sync 的阶段为 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`VALUE_DISCOVERY/BLUEPRINT`、`STORY_BREAKDOWN/INPUT_ANALYSIS`、`STORY_BREAKDOWN/EPIC_MAPPING`、`STORY_BREAKDOWN/STORY_BACKLOG`、`STORY_BREAKDOWN/SPRINT_PLAN`、`TEST_DESIGN/CLARIFY`、`TEST_DESIGN/STRATEGY`、`TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY`、`REQ_REVIEW/REVIEW`、`REQ_REVIEW/REPORT`、`INCIDENT_REVIEW/TIMELINE`、`INCIDENT_REVIEW/ROOT_CAUSE` 与 `INCIDENT_REVIEW/IMPROVEMENT`，其余 4 个 artifact-data 阶段仍待 `PRD_REVIEW` workflow 级切片迁移。
- 本轮不新增 STORY 字段派生、自动 ID 分配、严格枚举、Ready 判定、每个 P0 必须验收、Sprint 名称格式、`user_stories[].sprint` 与 `sprint_slices[].sprint_id` 一致性、字段级 partial renderer、backend Mermaid JS parse 或 `mmdc` 渲染门禁；Mermaid `flowchart` 与 `story-map` 仍由后端 deterministic renderer 生成，并由现有 artifact contract / visual contract 测试保护。

### 2026-07-09 切片记录：PRD_REVIEW artifactDataContract 同步

触发原因：

- `STORY_BREAKDOWN` 切片完成后，按“一个 workflow 一个切片”口径继续推进最后 4 个 artifact-data 阶段；这些阶段全部属于 `PRD_REVIEW`，共享 PRD 盘点、质量发现、补全动作、修订章节、验收标准和 handoff 输入数据形态。
- 当前 `PRD_REVIEW` 四阶段已有 Pydantic validator、deterministic renderer、visual contract 和 raw JSON streaming registry，但 manifest 缺少 `artifactDataContract`，frontend prompt 也没有可注入的结构化契约区块。
- 子智能体只读审查确认：真实强校验仅包含必需字段、额外字段禁止、字符串非空、关键列表非空、`finding_id` / `action_id` / `section_id` 唯一性、action finding 引用、acceptance / handoff section 引用和 `stage_gate` checked。不得虚构 severity / blocking / status / target_workflow 枚举、ready/pass 判定、deadline 或 PRD 专属 Mermaid flowchart 等未实现规则。

已修复：

- `PRD_REVIEW/INVENTORY`、`QUALITY_AUDIT`、`COMPLETION_PLAN`、`REVISION_BLUEPRINT` 新增 `artifactDataContract` manifest 配置，覆盖真实 schema / validator 强约束、禁止模型输出 renderer-owned Markdown / Mermaid / `ai4se-visual` JSON，以及各阶段后端 renderer 负责输出的右侧 PRD artifact 与视觉产物。
- 后端新增 `_prd_review_artifact_data_instruction()`，按 stage 注入 `format_artifact_data_contract_instruction("PRD_REVIEW", stage_id)`，并把 `stage_action` 收紧为精确下一阶段；最后阶段为 `null`。
- 新增 backend/frontend sync 测试：backend manifest instruction、backend runtime instruction、frontend workflow 配置和 frontend system prompt 注入均覆盖 PRD_REVIEW 四阶段。
- 补齐 PRD_REVIEW renderer validator 负向测试：重复 finding / action / section ID 和额外字段拒绝。
- `docs/TESTING.md` 字段来源矩阵同步更新：已迁入 `artifactDataContract` manifest sync 的阶段从 21 个增加到 25 个，剩余待迁移阶段从 4 个减少到 0 个。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k prd_review_artifact_data_contract
```

结果：修复前 `1 failed, 34 deselected`，失败点为 `PRD_REVIEW/INVENTORY` 缺少 `artifactDataContract`；修复后 `1 passed, 34 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k prd_review_structured_output_instruction
```

结果：修复前 `4 failed, 1 passed, 191 deselected`，失败点为四阶段 runtime instruction 未包含 manifest contract instruction；修复后 `9 passed, 191 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k prd_review_structured_output_instruction_targets_exact_next_stage
```

结果：修复前 `4 failed, 196 deselected`，失败点为 PRD_REVIEW runtime instruction 仍使用泛化目标集合；修复后已纳入 `prd_review_structured_output_instruction` 聚焦测试通过。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "PRD REVIEW"
```

结果：修复前 `1 failed, 34 skipped`，失败点为 PRD REVIEW `artifactDataContract` 未暴露；修复后 `1 passed, 34 skipped`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "PRD REVIEW"
```

结果：修复前 `4 failed, 71 skipped`，失败点为 PRD REVIEW 四阶段 system prompt 缺少 `【artifact_data 结构化契约】`；修复后 `4 passed, 71 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k prd_review
```

结果：`11 passed, 109 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

结果：`35 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k prd_review
```

结果：`22 passed, 178 deselected`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：`110 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `823 passed`；New Agents Backend `812 passed, 4 deselected`。

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

结果：非沙箱全量验证通过。关键结果包括 Intent Tester API `294 passed`、flake8 严重错误检查通过、MidScene proxy `17 passed`、Common Frontend lint/build 通过、New Agents Frontend `823 passed`、New Agents Backend `812 passed, 4 deselected`、New Agents Browser E2E `8 passed, 3 skipped, 10 deselected`。

残余风险：

- 本轮只迁移 `PRD_REVIEW` 四阶段；至此 25 个在线 artifact-data 阶段均已完成 `artifactDataContract` manifest sync，剩余待迁移阶段为 0。
- 本轮不新增 PRD 字段派生、自动 ID 分配、严格枚举、ready/pass 判定、deadline 校验、字段级 partial renderer、backend Mermaid JS parse 或 `mmdc` 渲染门禁；Mermaid `mindmap`、`score-matrix`、`action-board` 和 `roadmap` 仍由后端 deterministic renderer 生成，并由现有 artifact contract / visual contract 测试保护。

### 2026-07-09 切片记录：TEST_DESIGN/DELIVERY 派生统计字段后端化

触发原因：

- `artifactDataContract` manifest sync 已全部收口后，未完成治理转入派生字段后端化能力包；不能再把可计算统计继续交给模型维护。
- 子智能体只读审查确认：`TEST_DESIGN/DELIVERY` 当前模型仍被要求输出 `case_summary_items[].case_count`、`delivery_metrics.total_cases` 和 `delivery_metrics.high_risk_count`，后端只做一致性校验，不做缺省派生。
- 本轮只处理 DELIVERY 当前 payload 内可确定计算的字段，不做跨阶段从 `TEST_DESIGN/CASES` 回读逐条用例，也不改变 P0/P1/P2、自动化候选、阻塞环境等语义字段。

已修复：

- `DeliveryCaseSummaryItem.case_count` 缺省时由 `p0_count + p1_count + p2_count` 派生；显式提供但不一致时继续触发 validation failure。
- `DeliveryMetrics.total_cases` 缺省时由 `case_summary_items[].case_count` 总和派生；`high_risk_count` 缺省时由 `open_risks` 中 risk_type 包含“风险”且 `acceptable != "是"` 的开放风险数量派生；显式错误统计仍失败。
- `TEST_DESIGN/DELIVERY` runtime structured output 示例不再要求模型输出 `case_count`、`total_cases`、`high_risk_count`，并改为注入 manifest 生成的 `artifactDataContract` instruction。
- `workflow_manifest.json`、前端 workflow 配置测试和前端 system prompt 测试同步更新为“缺省后端派生、显式提供必须一致”。
- `docs/TESTING.md` 字段来源矩阵同步更新，记录 DELIVERY 交付指标基础信息仍由模型负责，统计汇总由后端确定性派生。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k "delivery_artifact_data_derives_case_count_and_metrics_when_missing or delivery_artifact_data_rejects_inconsistent_high_risk_count_when_present"
```

结果：修复前 `1 failed, 1 passed, 121 deselected`，失败点为 DELIVERY 缺少派生字段时 Pydantic 直接报 required；修复后相关聚焦用例通过。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k "delivery_without_derived_counts or delivery_structured_output_instruction_omits_derived_delivery_counts"
```

结果：修复前 `2 failed, 200 deselected`，失败点为 runtime parse 缺少派生字段失败、structured output instruction 仍要求模型输出派生字段；修复后 `2 passed, 200 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k test_design_delivery_artifact_data_contract
```

结果：修复前 `1 failed, 34 deselected`，失败点为 manifest contract 仍是“模型必须算对”的旧文案；修复后 `1 passed, 34 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k delivery
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k delivery
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：分别通过 `5 passed, 118 deselected`、`9 passed, 193 deselected`、`35 passed`、前端 `110 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `823 passed`；New Agents Backend `817 passed, 4 deselected`。

残余风险：

- 本轮只完成 `TEST_DESIGN/DELIVERY` 当前 payload 内可计算统计字段，不新增跨阶段 CASES 汇总，不后端派生 P0/P1/P2 分布、自动化候选、阻塞环境、交付状态或签署结论。
- 派生字段后端化能力包仍未整体完成；后续需要继续盘点其它 workflow 中仍由模型输出的覆盖统计、排序摘要、ID 派生或可计算汇总。

### 2026-07-09 切片记录：REQ_REVIEW 问题统计后端派生

触发原因：

- `TEST_DESIGN/DELIVERY` 派生统计切片完成后，继续消化同一能力包中的可计算字段；`REQ_REVIEW/REVIEW` 与 `REQ_REVIEW/REPORT` 均仍要求模型输出 P0/P1/P2 问题数量。
- 子智能体只读审查确认：`REQ_REVIEW/REVIEW.issue_statistics.p0_count/p1_count/p2_count` 可由 `issue_groups[].issues[].priority` 计数，`REQ_REVIEW/REPORT.issue_statistics` 可由 `issue_closures[].priority` 计数；二者都只依赖当前 payload，不需要跨阶段读取。
- 本轮按“一个 workflow 一个切片”的口径处理 `REQ_REVIEW` 两阶段；REVIEW 仍保留 `p0_description/p1_description/p2_description` 由模型输出，REPORT 的 `issue_statistics` 可整体缺省。

已修复：

- `ReqReviewIssueStatistics.p0_count/p1_count/p2_count` 缺省时由 `issue_groups[].issues[].priority` 派生；显式提供但不一致时继续 validation failure。
- `ReqReviewReportArtifactData.issue_statistics` 缺省时由 `issue_closures[].priority` 派生；显式提供但不一致时继续 validation failure。
- `REQ_REVIEW` runtime structured output 示例不再要求模型输出派生计数字段，并改为注入 manifest 生成的 `artifactDataContract` instruction。
- `workflow_manifest.json`、前端 workflow 配置测试和前端 system prompt 测试同步更新为“缺省后端派生、显式提供必须一致”。
- `docs/TESTING.md` 字段来源矩阵同步更新，记录 REVIEW 的问题统计描述仍由模型负责，计数由后端派生；REPORT 的 `issue_statistics` 可由后端整体派生。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k "req_review_artifact_data_derives_issue_statistics_counts_when_missing or req_review_report_artifact_data_derives_issue_statistics_when_missing"
```

结果：修复前 `2 failed, 123 deselected`，失败点为缺少 issue statistics 计数字段时 Pydantic 直接报 required；修复后 `2 passed, 123 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k "req_review_without_issue_counts or req_review_report_without_statistics or req_review_structured_output_instruction_omits_issue_count_fields or req_review_report_structured_output_instruction_omits_issue_statistics"
```

结果：修复前 `4 failed, 202 deselected`，失败点为 runtime parse 缺少派生字段失败、structured output instruction 仍要求模型输出派生字段；修复后 `4 passed, 202 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "req_review_review_artifact_data_contract or req_review_report_artifact_data_contract"
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run -t "REQ REVIEW"
```

结果：修复前分别为 `2 failed, 33 deselected` 和前端 `4 failed, 106 skipped`；修复后分别为 `2 passed, 33 deselected` 和前端 `4 passed, 106 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k req_review
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k req_review
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：分别通过 `12 passed, 113 deselected`、`18 passed, 188 deselected`、`35 passed`、前端 `110 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `823 passed`；New Agents Backend `823 passed, 4 deselected`。

残余风险：

- 本轮只处理 `REQ_REVIEW` 当前 payload 内可确定计算的问题统计，不新增跨阶段 REVIEW 到 REPORT 的问题继承，不后端派生评审结论、development gate、needs_recheck 或问题关闭状态。
- 派生字段后端化能力包仍未整体完成；已知后续候选包括 `INCIDENT_REVIEW/IMPROVEMENT` 的 `action_count` / `priority_distribution` 和 `IDEA_BRAINSTORM/CONVERGE` 的 `ice_score`。

### 2026-07-09 切片记录：INCIDENT_REVIEW/IMPROVEMENT 行动统计后端派生

触发原因：

- `REQ_REVIEW` 问题统计切片完成后，继续消化派生字段后端化能力包；`INCIDENT_REVIEW/IMPROVEMENT` 仍要求模型输出改进行动数量和优先级分布。
- 子智能体只读审查确认：`report_info.action_count` 可由 `improvement_actions` 数量派生，`priority_distribution` 可由 `improvement_actions[].priority` 计数；二者都只依赖当前 payload，不需要跨阶段读取。
- 本轮只处理行动统计，不新增根因覆盖自动补齐、日期格式、状态枚举或复查计划推断。

已修复：

- `IncidentImprovementReportInfo.action_count` 缺省时由 `len(improvement_actions)` 派生；显式提供但不一致时继续 validation failure。
- `IncidentImprovementArtifactData.priority_distribution` 缺省时由 `improvement_actions[].priority` 中“紧急 / 重要 / 常规”的数量派生；显式提供但不一致时继续 validation failure。
- `INCIDENT_REVIEW/IMPROVEMENT` runtime structured output 示例不再要求模型输出 `action_count` 或 `priority_distribution`。
- `workflow_manifest.json`、前端 workflow 配置测试和前端 system prompt 测试同步更新为“缺省后端派生、显式提供必须一致”。
- `docs/TESTING.md` 字段来源矩阵同步更新，记录 IMPROVEMENT 的报告基础信息和改进行动由模型负责，行动统计由后端确定性派生。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k incident_improvement_artifact_data_derives_action_statistics_when_missing
```

结果：修复前 `1 failed, 125 deselected`，失败点为缺少 `report_info.action_count` 和 `priority_distribution` 时 Pydantic 直接报 required；修复后 `1 passed, 125 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k "incident_improvement_without_statistics or incident_improvement_structured_output_instruction_omits_statistics"
```

结果：修复前 `2 failed, 206 deselected`，失败点为 runtime parse 缺少派生字段失败、structured output instruction 仍要求模型输出派生字段；修复后 `2 passed, 206 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k incident_improvement_artifact_data_contract
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run -t "INCIDENT REVIEW IMPROVEMENT"
```

结果：修复前分别为 `1 failed, 34 deselected` 和前端 `2 failed, 108 skipped`；修复后分别为 `1 passed, 34 deselected` 和前端 `2 passed, 108 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k incident_improvement
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k incident_improvement
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：分别通过 `9 passed, 117 deselected`、`6 passed, 202 deselected`、`35 passed`、前端 `110 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `823 passed`；New Agents Backend `826 passed, 4 deselected`。

残余风险：

- 本轮只处理 `INCIDENT_REVIEW/IMPROVEMENT` 当前 payload 内可确定计算的行动统计，不后端派生根因覆盖关系、防复发清单、复查计划、遗留风险、签署状态或经验教训。
- 派生字段后端化能力包仍未整体完成；已知后续候选包括 `IDEA_BRAINSTORM/CONVERGE.ice_score`。

### 2026-07-09 切片记录：IDEA_BRAINSTORM/CONVERGE ICE 评分后端派生

触发原因：

- `INCIDENT_REVIEW/IMPROVEMENT` 行动统计切片完成后，继续消化派生字段后端化能力包；`IDEA_BRAINSTORM/CONVERGE` 仍要求模型输出可由当前 payload 确定计算的 `ice_score`。
- 只读审查确认：`ice_score = impact * confidence / effort` 只依赖当前 `ice_evaluations` 单项字段，不需要跨阶段读取；显式错误值仍应作为 validation failure 暴露。
- 本轮只处理 ICE 评分，不新增 idea id / rank / recommended idea / validation experiment / merge path 的后端分配或自动补齐。

已修复：

- `IdeaIceEvaluation.ice_score` 缺省时由 `impact * confidence / effort` 派生；显式提供但不一致时继续 validation failure。
- `IDEA_BRAINSTORM/CONVERGE` runtime structured output 示例不再要求模型输出 `ice_score`。
- `workflow_manifest.json`、前端 workflow 配置测试和前端 system prompt 测试同步更新为“缺省后端派生、显式提供必须一致”。
- `docs/TESTING.md` 字段来源矩阵同步更新，记录 CONVERGE 的决策、ICE 原子评分、资源约束、验证实验和合并路径由模型负责，ICE 评分汇总由后端确定性派生。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k idea_converge_artifact_data_derives_ice_score_when_missing
```

结果：修复前 `1 failed, 126 deselected`，失败点为缺少 `ice_score` 时 Pydantic 直接报 required；修复后 `1 passed, 126 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k "idea_converge_without_ice_score or idea_converge_structured_output_instruction_omits_ice_score"
```

结果：修复前 `2 failed, 208 deselected`，失败点为 runtime parse 缺少派生字段失败、structured output instruction 仍要求模型输出 `ice_score`；修复后 `2 passed, 208 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k idea_converge_artifact_data_contract
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run -t "IDEA BRAINSTORM CONVERGE"
```

结果：修复前分别为 `1 failed, 35 deselected` 和前端 `2 failed, 110 skipped`；修复后分别为 `1 passed, 35 deselected` 和前端 `2 passed, 110 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k idea_converge
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k idea_converge
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：分别通过 `11 passed, 116 deselected`、`7 passed, 203 deselected`、`36 passed`、前端 `112 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `825 passed`；New Agents Backend `830 passed, 4 deselected`。

残余风险：

- 本轮只处理 `IDEA_BRAINSTORM/CONVERGE` 当前 payload 内可确定计算的 ICE 评分，不后端派生 idea id、rank、recommended idea、验证实验引用或合并路径引用。
- 派生字段后端化能力包仍需后续做全量审计，确认是否还有隐藏在当前 payload 内且可确定计算的字段。

### 2026-07-09 切片记录：STORY_BREAKDOWN story-map 前端视觉协议补齐

触发原因：

- 后端 `REQUIRED_ARTIFACT_STRUCTURED_VISUALS` 和 `workflow_manifest.json` 已声明 `STORY_BREAKDOWN/SPRINT_PLAN` 需要 `ai4se-visual story-map`，后端 renderer 也会输出矩阵式 `columns/rows` story-map。
- 前端 `structuredVisuals.ts` 原本只支持 `traceability-matrix`、`score-matrix`、`risk-board`、`action-board`、`journey-map`、`coverage-map`、`priority-board`、`cause-map`、`mvp-map`、`roadmap`，没有 `story-map`，导致正式产物中的 story-map 会被前端视觉校验拒绝。
- 子智能体只读审查确认：当前 manifest required structured visual 集合里除 `story-map` 外没有其他前端 parser 不支持的类型；本轮不扩大到 `flow-map`、`timeline-map`、`mindmap`、`sequence-flow` 等新协议。

已修复：

- `StructuredVisualType` 与 `SUPPORTED_VISUAL_TYPES` 增加 `story-map`，复用已有矩阵式 `columns/rows` 协议。
- `StructuredVisual` 增加 `story-map` 默认标题“用户故事地图”。
- 增加 frontend parser 反向门禁：遍历 `WORKFLOWS[*].stages[*].visualContract.requiredStructuredVisuals`，确保每个 manifest required 类型都能被共享 parser 支持。
- 增加 story-map 的前端渲染、PDF 导出和 DOCX 导出测试，证明预览与导出使用同一 parser，不新增专属 runtime、store、API 或渲染管线。

验证：

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx src/core/__tests__/artifactExport.test.ts src/core/__tests__/docxExport.test.ts --run
```

结果：修复前 `4 failed`，共 5 个断言失败，失败点均为“不支持的结构化可视化类型：story-map”；修复后 `4 passed`，`41 passed`。

```bash
cd tools/new-agents/frontend && npm run test
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q -k "structured_visual or story_map or story_breakdown or visual_contract"
```

结果：分别通过。New Agents Frontend `828 passed`；backend focused visual / contract sync `12 passed, 123 deselected`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `828 passed`；New Agents Backend `830 passed, 4 deselected`。

残余风险：

- 本轮只把已由 backend / manifest required 的 `story-map` 纳入前端共享矩阵 visual 协议，不新增非矩阵复杂图 schema。
- `flow-map`、`timeline-map`、`mindmap`、`sequence-flow`、`distribution-chart` 等复杂视觉类型仍需后续独立切片；backend Mermaid JS parse 或 `mmdc` 渲染门禁也仍未补齐。

### 2026-07-09 切片记录：TEST_DESIGN/CASES 自动化候选 case_id 引用闭环

触发原因：

- 只读审查发现 `workflow_manifest.json` 已声明 `automation_candidates.case_id` 只能引用已存在的 `case_id`，但 `CasesArtifactData` validator 只校验了 `coverage_trace.covered_cases`，没有校验自动化候选引用。
- 这属于 manifest / 后端 validator 的 contract drift，会让模型输出引用不存在用例的自动化候选后仍被后端接受。
- 本轮只补 `automation_candidates.case_id` 的后端引用门禁，不引入全局 ID 生成器，不改 CASES 数据结构，不处理 `CONVERGE` / `STRATEGY` 的更广泛 ID 归一化。

已修复：

- `CasesArtifactData.validate_case_consistency()` 增加 `automation_candidates.case_id` unknown reference 校验。
- 新增负例测试，证明未知自动化候选 `case_id` 会触发 `ValidationError`，错误信息包含 `automation_candidates`。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k cases_artifact_data_rejects_unknown_automation_candidate_case_reference
```

结果：修复前 `1 failed, 127 deselected`，失败点为未知 `automation_candidates.case_id` 未触发 `ValidationError`；修复后 `1 passed, 127 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k cases_artifact_data
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k cases
```

结果：分别通过 `5 passed, 123 deselected` 和 `10 passed, 236 deselected`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `828 passed`；New Agents Backend `831 passed, 4 deselected`。

残余风险：

- 本轮只补齐已写入 manifest 的 CASES 自动化候选引用门禁，不后端生成或重写 `case_id`。
- 更广泛的 ID 收敛仍未完成，尤其是 `IDEA_BRAINSTORM/CONVERGE` 的 idea / rank / recommended idea 链路，以及 `TEST_DESIGN/STRATEGY` 的 `QG/R/TS/TP` 字符串引用归一化。

### 2026-07-09 切片记录：IDEA_BRAINSTORM/CONVERGE ICE 排名后端派生

触发原因：

- `CONVERGE` 的 `ice_score` 已由后端按 `impact * confidence / effort` 派生，但同一 ICE 评估表内的 `rank` 仍由模型输出，后端只校验唯一性。
- 这会把“按 ICE 得分排序”这种确定性产物交给模型维护，导致显式 rank 与 ICE 得分顺序不一致时仍可能通过校验。
- 本轮只处理 ICE 表内 rank 的派生与一致性校验，不后端生成 idea id，不改推荐方案决策矩阵，不改变 validation experiment 或 merge path 引用逻辑。

已修复：

- `IdeaIceEvaluation.rank` 改为可缺省；缺省时由后端按 `ice_score` 降序派生，分数相同保留输入顺序。
- 显式提供 rank 时必须与后端派生顺序一致；重复 rank 或错误排序继续触发 `ValidationError`。
- `IDEA_BRAINSTORM/CONVERGE` runtime structured output 示例不再要求模型输出 `rank`。
- `workflow_manifest.json`、前端 workflow 配置测试和前端 system prompt 测试同步更新为“rank 缺省后端派生、显式提供必须一致”。
- `docs/TESTING.md` 字段来源矩阵同步更新，记录 CONVERGE 的 ICE 原子评分由模型负责，ICE 得分和排名由后端确定性派生。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k "idea_converge_artifact_data_derives_rank_when_missing or idea_converge_artifact_data_rejects_inconsistent_rank_order"
```

结果：修复前 `2 failed, 128 deselected`，失败点为缺少 `rank` 时 Pydantic required、错误 rank 顺序未触发 `ValidationError`；修复后 `2 passed, 128 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k "idea_converge_without_rank or idea_converge_structured_output_instruction_omits_rank"
```

结果：修复前 `2 failed, 210 deselected`，失败点为 runtime parse 缺少 rank 失败、structured output instruction 仍要求模型输出 `rank`；修复后 `2 passed, 210 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k idea_converge_artifact_data_contract
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run -t "IDEA BRAINSTORM CONVERGE"
```

结果：修复前分别为 `1 failed, 35 deselected` 和前端 `2 failed, 110 skipped`；修复后分别为 `1 passed, 35 deselected` 和前端 `2 passed, 110 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k idea_converge
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k idea_converge
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：分别通过 `13 passed, 117 deselected`、`9 passed, 203 deselected`、`36 passed`、前端 `112 passed`。

```bash
./scripts/test/test-local.sh new-agents
```

结果：通过。New Agents Frontend `828 passed`；New Agents Backend `835 passed, 4 deselected`。

残余风险：

- 本轮只派生 ICE 表内 rank，不代表 `IDEA_BRAINSTORM/CONVERGE` 的 idea id、recommended idea、validation experiment 或 merge path 已完成后端生成 / 归一化。
- 若后续产品决策允许用户基于战略因素覆盖 ICE 排名，应新增独立字段表达“人工推荐权重”或“决策覆盖理由”，不能复用 `rank` 混合两种含义。

### 2026-07-09 切片记录：已治理派生字段回退审计门禁

触发原因：

- `TEST_DESIGN/DELIVERY`、`REQ_REVIEW`、`INCIDENT_REVIEW/IMPROVEMENT`、`IDEA_BRAINSTORM/CONVERGE` 等派生字段已完成多个纵切，但缺少一张统一审计清单保护这些字段不被后续 runtime 示例或 manifest 文案回退为“模型必须输出”。
- 单阶段测试能证明局部行为，但不能直接回答“当前已治理派生字段是否整体仍由后端派生、runtime 示例是否没有重新要求模型输出”。
- 本轮作为工程信任闭环，不新增新 workflow，不改变 shared runtime / transport / state / UI，只补后端 contract sync 审计策略与测试。

已修复：

- 新增 `get_derived_artifact_data_field_policies()`，集中记录当前已治理派生字段：`risks[].rpn`、`case_statistics`、`case_summary_items[].case_count`、`delivery_metrics.total_cases`、`delivery_metrics.high_risk_count`、REQ_REVIEW P0/P1/P2 计数、`score_summary.total_score` / `average_score`、`report_info.action_count`、`priority_distribution`、`ice_score`、`rank`。
- 新增 backend contract sync 聚合测试，逐项校验 manifest contract instruction 必须包含后端派生 / 显式一致性片段，同时 runtime structured output JSON 示例不得包含对应 `"field":` 示例 token。
- 子智能体只读旁路审查确认：当前已治理字段未发现 P0 回退；前端配置和 prompt 仍从 manifest 注入派生规则，没有独立要求模型输出上述派生字段。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k derived_artifact_data_fields_are_tracked
```

结果：修复前 `1 failed, 36 deselected`，失败点为缺少统一派生字段策略清单；修复后 `1 passed, 36 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k "derived or artifact_data_contract or structured_output_instruction_omits or without_derived or computes_missing or derives"
```

结果：通过，`46 passed, 333 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
./scripts/test/test-local.sh new-agents
```

结果：通过。backend contract sync `37 passed`；New Agents Frontend `828 passed`；New Agents Backend `836 passed, 4 deselected`。

```bash
./scripts/test/test-local.sh
```

结果：仓库默认全量脚本在本地沙箱下未完全通过。已完成 Intent Tester API `294 passed`、严重 lint 通过、Common Frontend lint / build 通过、New Agents Frontend `828 passed`、New Agents Backend `836 passed, 4 deselected`；MidScene proxy 测试因 `listen EPERM: operation not permitted 0.0.0.0:3002` 失败，New Agents Browser E2E 因 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)` 失败。该失败与本轮 3 个 New Agents contract / todo 文件改动无直接逻辑关联，按环境权限阻塞记录。

残余风险：

- 本轮只防止“已治理统计 / 评分 / 排名派生字段”回退，不代表所有可由 payload 机械推导的字段都已消化。
- 旁路审查新增 4 个 P1 候选：`TEST_DESIGN/CASES` case dimension、`REQ_REVIEW/REVIEW` issue dimension、`INCIDENT_REVIEW/IMPROVEMENT` root cause coverage action mapping、`STORY_BREAKDOWN` story sprint mapping。后续应按同级切片分别评估，不塞回本轮内部批次。

### 2026-07-09 切片记录：分组内维度后端派生与一致性校验

触发原因：

- 上一轮回退审计发现 `TEST_DESIGN/CASES` 的 `CaseGroup.dimension` 与 `TestCaseItem.dimension`、`REQ_REVIEW/REVIEW` 的 `ReqReviewIssueGroup.dimension` 与 `ReqReviewIssueItem.dimension` 属于同一事实重复维护。
- 现状是内层 `dimension` required，模型必须重复输出；同时 validator 只校验 ID / 统计，不校验外层分组维度和内层行维度是否一致，右侧分组标题和行字段可能出现矛盾。
- 子智能体只读旁路审查确认：这两个候选都成立，且 `artifact_data_renderers.py` 中未发现必须并入本切片的第三个同类 group -> item 重复维度候选。

已修复：

- `TEST_DESIGN/CASES`：`TestCaseItem.dimension` 改为可缺省；缺省时由外层 `case_groups[].dimension` 派生，显式提供时必须与外层分组维度一致，否则触发 `ValidationError`。
- `REQ_REVIEW/REVIEW`：`ReqReviewIssueItem.dimension` 改为可缺省；缺省时由外层 `issue_groups[].dimension` 派生，显式提供时必须与外层分组维度一致，否则触发 `ValidationError`。
- CASES / REVIEW runtime structured output 示例不再要求模型输出内层 `dimension`。
- `workflow_manifest.json`、`get_derived_artifact_data_field_policies()`、backend contract sync 测试、frontend workflow 配置测试和 frontend system prompt 测试同步更新为“缺省后端派生、显式提供必须一致”。
- `docs/TESTING.md` 字段来源矩阵同步更新，记录 CASES / REVIEW 的内层维度来源从模型重复维护改为后端派生 / 显式一致性校验。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k "case_dimension or issue_dimension"
```

结果：修复前 `4 failed, 130 deselected`，失败点为缺省内层维度被 Pydantic required 拒绝，显式矛盾维度未触发 `ValidationError`；修复后 `4 passed, 130 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "dimension_examples or derived_artifact_data_fields_are_tracked or req_review_review_artifact_data_contract or cases_artifact_data_contract"
```

结果：修复前 `4 failed, 247 deselected`，失败点为 runtime 示例仍包含内层维度、派生字段策略清单缺少两条维度规则、REQ_REVIEW manifest contract 缺少维度派生说明；修复后 `5 passed, 247 deselected`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

结果：通过，`114 passed`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "cases or req_review or derived"
git diff --check
./scripts/test/test-local.sh new-agents
```

结果：后端聚焦回归 `57 passed, 329 deselected`；`git diff --check` 通过；New Agents Frontend `830 passed`，New Agents Backend `843 passed, 4 deselected`。

残余风险：

- 本轮只治理 CASES / REVIEW 分组内维度重复维护，不后端生成或归一化 `case_id`、`issue_id`，也不改变覆盖追溯、修订建议或自动化候选引用语义。
- `INCIDENT_REVIEW/IMPROVEMENT` root cause coverage `action_ids` 与 `improvement_actions[].root_cause_id` 精确匹配、`STORY_BREAKDOWN` story sprint 与 `sprint_slices[].story_ids` 映射一致性仍是后续 P1 候选。
- 视觉协议分层、复杂 `ai4se-visual` 类型扩展和后端 / CI 视觉渲染强校验仍未在本轮处理。

### 2026-07-09 切片记录：INCIDENT_REVIEW root cause/action 映射一致性

触发原因：

- 上一轮 P1 候选中，`INCIDENT_REVIEW/IMPROVEMENT` 的 `improvement_actions[].root_cause_id` 与 `root_cause_coverage[].action_ids` 属于同一事实的双向表达。
- 当前 validator 只校验 action ID 存在、coverage cause ID 存在、已覆盖时 `action_ids` 非空；未校验“某个 cause 的 `action_ids` 必须精确等于所有 `root_cause_id` 指向该 cause 的 action”。
- 子智能体只读旁路审查确认：Incident 候选成立；`STORY_BREAKDOWN` story sprint/slice 映射也成立，但影响四阶段共享 schema、renderer 和单故事 handoff，建议拆成下一同级切片，不与本轮合并。

已修复：

- `IncidentImprovementArtifactData` 新增 root cause/action 精确映射校验：每个 `root_cause_coverage[].action_ids` 必须等于所有 `improvement_actions[]` 中 `root_cause_id` 等于该 `cause_id` 的 `action_id` 集合。
- 保留既有错误诊断优先级：`coverage_status == “已覆盖”` 且 `action_ids` 为空时，仍先返回 coverage_status 相关错误。
- 新增 renderer contract 负例，覆盖 action 被挂到错误 root cause coverage、coverage 漏列某个 action 两类矛盾。
- `workflow_manifest.json`、backend contract sync、frontend workflow 配置和 frontend system prompt 测试同步新增精确映射规则。
- `docs/TESTING.md` 字段来源矩阵同步更新，记录根因覆盖 action/root_cause 引用和精确映射只校验不派生。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k "wrong_root_cause_coverage or missing_action_from_root_cause_coverage"
```

结果：修复前 `2 failed, 134 deselected`，失败点为错挂 action 和漏列 action 都未触发 `ValidationError`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k "wrong_root_cause_coverage or missing_action_from_root_cause_coverage or incident_improvement_artifact_data"
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_runtime.py -q -k "incident_improvement"
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run -t "INCIDENT REVIEW IMPROVEMENT"
```

结果：修复后分别通过 `11 passed, 125 deselected`、`7 passed, 245 deselected`、前端 `2 passed, 112 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "incident_improvement or incident_review or derived"
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
git diff --check
./scripts/test/test-local.sh new-agents
```

结果：后端聚焦回归 `31 passed, 357 deselected`；前端同步测试 `114 passed`；`git diff --check` 通过；New Agents Frontend `830 passed`，New Agents Backend `845 passed, 4 deselected`。

残余风险：

- 本轮只治理 `INCIDENT_REVIEW/IMPROVEMENT` 的 root cause/action 双向映射，不后端生成 action ID 或 cause ID，也不改 prevention / review / residual risk 的引用规则。
- `STORY_BREAKDOWN` 的 `user_stories[].sprint` 与 `sprint_slices[].story_ids` 映射一致性仍是下一同级 P1 切片；它影响四阶段共享 schema、renderer 和单故事 handoff，不能塞进本轮。
- 旁路审查识别 `VALUE_DISCOVERY/JOURNEY` pain / opportunity 成对映射为 P2 候选，当前不纳入 P1 收口。

### 2026-07-09 切片记录：STORY_BREAKDOWN story sprint 派生与 handoff 一致性

触发原因：

- 旁路审查确认 `STORY_BREAKDOWN` 的 `user_stories[].sprint` 与 `sprint_slices[].story_ids` 会同时表达故事所属 Sprint，当前 validator 只校验 `sprint_slices[].story_ids` 引用已定义 story，不校验 story 自身 sprint 与 sprint slice 是否一致。
- renderer 会同时显示两处信息：Backlog / story-map 使用 `user_stories[].sprint`，Sprint 切片表使用 `sprint_slices[].story_ids`；单故事 handoff candidate / packet 也会读取 `story.sprint`。
- 本轮单独处理 STORY，是因为它覆盖四个共享阶段、renderer 和 handoff packet，影响面明显大于上一轮单阶段 Incident 映射。

已修复：

- `StoryBreakdownUserStory.sprint` 改为可缺省；缺省时由后端按 `sprint_slices[].story_ids` 所属 `sprint_slices[].sprint_id` 派生。
- `StoryBreakdownArtifactData` 新增 sprint 归属校验：每个 story 必须出现在且只能出现在一个 sprint slice 中；显式提供 `user_stories[].sprint` 时必须与 slice 归属一致，否则触发 `ValidationError`。
- 单故事 handoff candidate 使用 `StoryBreakdownArtifactData.model_validate()` 后的派生 sprint，因此持久化 artifact_data 即使缺省 story sprint，也能生成带正确 Sprint 的候选和 packet。
- Story 四阶段 runtime structured output 示例不再要求模型输出 `user_stories[].sprint`。
- `workflow_manifest.json`、`get_derived_artifact_data_field_policies()`、backend contract sync、frontend workflow 配置和 frontend system prompt 测试同步更新为“缺省后端派生、显式提供必须一致”。
- `docs/TESTING.md` 字段来源矩阵同步更新，记录 STORY 四阶段的 story sprint 来源从模型重复维护改为后端派生 / 显式一致性校验。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_story_handoff_packets.py -q -k "story_sprint or derived_from_sprint_slices"
```

结果：修复前 `3 failed, 143 deselected`，失败点为缺省 story sprint 被 Pydantic required 拒绝、显式 sprint 与 sprint slice 矛盾未触发 `ValidationError`、handoff candidate 不能从缺省 sprint 的 artifact_data 派生 Sprint；修复后 `3 passed, 143 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "story_breakdown_structured_output_instruction_omits_story_sprint_examples or story_breakdown_artifact_data_contract or derived_artifact_data_fields"
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run -t "STORY BREAKDOWN"
```

结果：修复前分别为 `5 failed, 251 deselected`、前端 `5 failed, 109 skipped`；修复后分别通过 `6 passed, 250 deselected`、前端 `5 passed, 109 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_story_handoff_packets.py -q -k "story_breakdown or story_handoff or derived"
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts src/services/__tests__/storyHandoffPacketService.test.ts --run
git diff --check
./scripts/test/test-local.sh new-agents
```

结果：后端聚焦回归 `57 passed, 345 deselected`；前端 Story / handoff 同步测试 `118 passed`；`git diff --check` 通过；New Agents Frontend `830 passed`，New Agents Backend `852 passed, 4 deselected`。

残余风险：

- 本轮只治理 `STORY_BREAKDOWN` 的 story sprint / sprint slice 双向映射，不后端生成 `story_id`、`sprint_id`，也不改变 Epic / Criterion / Dependency / Lisa handoff 引用语义。
- `VALUE_DISCOVERY/JOURNEY` pain / opportunity 成对映射仍是 P2 候选；当前没有证据表明它造成高失败或必须并入 P1 派生字段收口。
- 视觉协议分层、复杂 `ai4se-visual` 类型扩展和后端 / CI 视觉渲染强校验仍未在本轮处理。

### 2026-07-09 切片记录：共享视觉产物协议分层

目标承接检查：

- 事实源：已重新读取 `AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/TESTING.md`、本 todo、`workflow_manifest.json`、后端 `agent_contracts.py` / `workflow_manifest.py` / `agent_runtime.py`、前端 `workflowRegistry.ts` / `types.ts` / `buildSystemPrompt.ts` 和相关同步测试。
- 工作区：本轮开始时 `master...origin/master` 干净；本切片只触达 New Agents 共享配置、runtime/prompt 注入、同步测试和文档。
- 改道条件：没有新的 P0/P1 阻断测试失败；Alex handoff 路线已完成，不回开 Lisa/Alex handoff 设计。
- 子智能体：已派发只读 explorer `019f4658-152d-7580-9e97-b921dd41f9e1` 审查视觉协议现状。结论是当前只有阶段级 `visualContract` required lists 和分散 `artifactDataContract.forbiddenOutputs`，没有顶层 `visualProtocol`、没有 unified allowed Mermaid source / forbidden DSL / planned complex visual source；建议本轮只做协议来源与模型禁止输出，不扩大到 renderer 重构。

本轮设计：

- 选择方案：新增 manifest 顶层 `visualProtocol` 作为共享视觉协议源；阶段级 `visualContract` 继续只表达 required Mermaid / required structured visual 的存在性。
- 注入位置：后端 `build_structured_output_instruction()` 对所有 artifact-data 阶段追加 `format_visual_protocol_instruction()`；前端 `buildSystemPrompt()` 从同一 manifest 字段追加视觉协议，并继续把 `Mermaid` 字样脱敏为“图表”，避免模型提示回退到手写 Mermaid。
- 不纳入本轮：不改 `StructuredVisual` 渲染组件，不迁移 `flow-map` / `timeline-map` / `mindmap` / `sequence-flow` 等复杂类型，不新增 backend Mermaid JS parse / `mmdc` 门禁，不把 `rendererOutputs` 与 `visualContract` 精确一致作为本轮强约束。

已修复：

- `workflow_manifest.json` 顶层新增 `visualProtocol`：声明模型只输出 `artifact_data`，禁止 Mermaid / D2 / Graphviz DOT / PlantUML 代码块，Mermaid 只允许由后端 deterministic renderer 生成，复杂业务图优先 `ai4se-visual`，并列出当前类型和后续复杂类型。
- 后端 `workflow_manifest.py` 新增 `get_visual_protocol()` 和 `format_visual_protocol_instruction()`，并校验协议结构与来源字段。
- 后端 `agent_runtime.py` 对 artifact-data 结构化输出说明追加视觉协议；结构化失败 retry prompt 同步禁止 Mermaid / D2 / Graphviz DOT / PlantUML。
- 前端 `types.ts` / `workflowRegistry.ts` 类型化暴露 `visualProtocol`。
- 前端 `buildSystemPrompt.ts` 从 manifest 注入共享视觉协议，所有 artifact-data 阶段共享同一模型输出边界。
- 新增后端 / 前端红绿测试，覆盖 manifest 协议、后端 runtime 注入、前端 manifest 暴露和前端 prompt 注入；测试同时锁定模型不得输出完整 Markdown 文档、Markdown 表格或 `ai4se-visual` JSON 代码块。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k visual_protocol
```

结果：修复前 `1 failed, 38 deselected`，失败点为缺少 `format_visual_protocol_instruction()`；修复后 `1 passed, 38 deselected`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q -k visual_protocol
```

结果：修复前 `1 failed, 218 deselected`，失败点为 artifact-data structured output instruction 未注入视觉协议；修复后 `1 passed, 218 deselected`。

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run -t "visual protocol"
```

结果：修复前 `2 failed, 114 skipped`，失败点为 manifest 缺 `visualProtocol` 且 system prompt 未注入视觉协议；修复后 `2 passed, 114 skipped`。

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_runtime.py -q -k "visual_protocol or artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming or structured_output_instruction_omits or artifact_data_contract"
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
git diff --check
./scripts/test/test-local.sh new-agents
```

结果：后端协议 / artifact-data 聚焦回归 `70 passed, 188 deselected`；前端 manifest / prompt 同步测试 `116 passed`；`git diff --check` 通过；New Agents Frontend `832 passed`，New Agents Backend `854 passed, 4 deselected`。

```bash
./scripts/test/test-local.sh all
```

结果：未形成完整通过结论。已通过部分包括 Intent Tester API `294 passed`、flake8 严重错误检查、Common Frontend lint/build、New Agents Frontend `832 passed`、New Agents Backend `854 passed, 4 deselected`。阻塞点仍是本地全量环境问题：MidScene proxy 在当前沙箱下因 `listen EPERM: operation not permitted 0.0.0.0:3002` 失败；New Agents Browser E2E 在 Playwright / Chromium 检查阶段卡住后被中断。本轮 New Agents 相关验证已用 `./scripts/test/test-local.sh new-agents` 完整覆盖。

残余风险：

- 旁路审查识别 `PRD_REVIEW/COMPLETION_PLAN` 存在 `rendererOutputs` 声明 `roadmap` 但阶段级 `visualContract.requiredStructuredVisuals` 只要求 `action-board` 的不一致信号；本轮不裁决“所有 rendererOutputs 是否必须 required”，后续可并入视觉强校验或协议深化切片。
- 本轮只建立视觉协议来源与模型输出边界，不提供新的复杂 `ai4se-visual` 类型实现。
- 后端 / CI 仍未执行 Mermaid JS parse 或 `mmdc` SVG 渲染门禁，仍属于后续“视觉渲染强校验”能力包。

## 后续厚切片重定义

2026-07-09 用户反馈：当前切片过薄，投入时间较长但进展体感不明显。本轮视觉协议分层提交后停止继续实现，后续先重新定义剩余工作和切片边界。

新的切片原则：

- 不允许“内部批次”。如果一个切片过大，直接拆成多个同级切片；每个切片都必须有独立目标、验收、验证命令、提交和 push 边界。
- 后续切片优先按“用户可见的端到端价值”定义，而不是按单个字段、单个测试或单个配置点定义。
- 默认把剩余工作收敛为更厚的 3 个候选切片，启动前再做一次事实复核和范围确认。

候选厚切片：

| 候选切片 | 覆盖范围 | 交付边界 |
|---|---|---|
| 复杂视觉端到端迁移 | 从一个高风险 Mermaid 场景开始，落地 `timeline-map` / `flow-map` / `mindmap` / `sequence-flow` 等复杂 `ai4se-visual` 类型之一 | schema、后端 deterministic renderer、前端组件 / parser、导出降级、manifest 视觉声明、失败诊断和回归测试一次收口；用户能看到复杂图不再依赖模型手写 Mermaid。 |
| 视觉成功门禁端到端 | Mermaid / `ai4se-visual` 在正式 artifact 成功、持久化和阶段推进前的可执行校验 | 至少形成 CI / renderer fixture / 前端 parse 或 backend 可执行门禁；失败必须显式诊断，不产生成功 `agent_turn`、不持久化 artifact、不推进 stage。 |
| 结构化一致性收口审计 | 派生字段后端化、ID 收敛和引用一致性的剩余候选统一复核 | 明确剩余 P1 是否为 0；若仍有 P1，按 workflow 级或业务闭环级一次收口；P2 只记录 backlog，不继续拆成很薄的小切片。 |

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
