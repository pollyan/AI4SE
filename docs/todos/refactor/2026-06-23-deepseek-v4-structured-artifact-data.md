# DeepSeek V4 兼容的后端结构化产物数据改造 Todo

> 状态: 活动候选
> 创建日期: 2026-06-23
> 背景: 当前主要使用 DeepSeek V4 Flash。该模型链路适合按 JSON mode 约束“合法 JSON”，但不能把它等同于 OpenAI strict Structured Outputs。长期最稳方案应减少模型直接生成完整 Markdown/Mermaid 的职责。

## 当前进展

- 2026-06-23 已完成首个垂直切片: `TEST_DESIGN/CLARIFY` 支持模型输出 `artifact_data`，后端 Pydantic schema 校验后确定性渲染完整 Markdown/Mermaid artifact，并继续通过现有 `AgentTurnOutput`、artifact contract、typed SSE 和 run artifact persistence 交付。
- 2026-06-23 已完成第二个垂直切片: `TEST_DESIGN/STRATEGY` 支持模型输出 `artifact_data`，后端校验 FMEA 风险、质量目标、测试分层、测试点和资源取舍后，确定性渲染《测试策略蓝图》、Mermaid `quadrantChart`、Mermaid `block-beta` 和 `ai4se-visual` `risk-board`。
- 2026-06-23 已完成第三个垂直切片: `TEST_DESIGN/CASES` 支持模型输出 `artifact_data`，后端校验用例统计、用例分组、覆盖追溯和开放问题后，确定性渲染《测试用例集》和 `ai4se-visual` `traceability-matrix`；renderer 输出继续可被 Lisa 测试资产导出链路解析。
- 2026-06-23 已完成第四个垂直切片: `TEST_DESIGN/DELIVERY` 支持模型输出 `artifact_data`，后端校验交付指标、执行摘要、需求/策略/用例摘要、覆盖地图、开放风险、验收清单、签署和变更记录后，确定性渲染《测试设计文档》和 `ai4se-visual` `coverage-map`。
- 2026-06-23 已完成第五个垂直切片: `REQ_REVIEW/REVIEW` 支持模型输出 `artifact_data`，后端校验评审信息、范围、质量总览、问题统计、分维度问题清单、修订建议和阶段门禁后，确定性渲染《需求评审问题清单》、Mermaid `flowchart` 和 `ai4se-visual` `score-matrix`。
- 2026-06-23 已完成第六个垂直切片: `REQ_REVIEW/REPORT` 支持模型输出 `artifact_data`，后端校验评审结论、问题统计、问题关闭清单、复审条件、签署确认和变更记录后，确定性渲染《需求评审报告》、Mermaid `pie` 和 `ai4se-visual` `priority-board`。
- 2026-06-23 已完成第七个垂直切片: `VALUE_DISCOVERY/ELEVATOR` 支持模型输出 `artifact_data`，后端校验价值流节点引用、价值评分汇总、目标用户场景、痛点证据、差异化、商业可行性、未验证假设和阶段门禁后，确定性渲染《价值定位分析》、Mermaid `flowchart` 和 `ai4se-visual` `score-matrix`。
- 2026-06-23 已完成第八个垂直切片: `VALUE_DISCOVERY/PERSONA` 支持模型输出 `artifact_data`，后端校验画像引用、行为场景、决策链、痛点证据、反画像、用户优先级和阶段门禁后，确定性渲染《用户画像分析》。
- 2026-06-23 已完成第九个垂直切片: `VALUE_DISCOVERY/JOURNEY` 支持模型输出 `artifact_data`，后端校验旅程阶段、痛点优先级、机会评分、产品切入策略和验证实验的跨字段引用后，确定性渲染《用户旅程分析》、Mermaid `journey` 和 `ai4se-visual` `journey-map`。
- 2026-06-23 已完成第十个垂直切片: `VALUE_DISCOVERY/BLUEPRINT` 支持模型输出 `artifact_data`，后端校验需求、验收标准、MVP 范围、主流程、roadmap、风险和 Lisa Handoff 输入的跨字段引用后，确定性渲染《需求蓝图》、Mermaid `mindmap`、Mermaid `flowchart` 和 `ai4se-visual` `roadmap`。
- 2026-06-23 已完成第十一个垂直切片: `INCIDENT_REVIEW/TIMELINE` 支持模型输出 `artifact_data`，后端校验事件概要、影响指标、事实来源、时间线事实引用、事实/推测/待确认分离、参与方和缺失信息后，确定性渲染《故障复盘报告》和 Mermaid `timeline`；timeline 时间标签中的半角冒号由后端转义为全角冒号，避免 Mermaid 解析歧义。
- 2026-06-23 已完成第十二个垂直切片: `INCIDENT_REVIEW/ROOT_CAUSE` 支持模型输出 `artifact_data`，后端校验 5-Why 分析链、根因证据、鱼骨图原因引用、根因结论、排除项、未验证原因和阶段门禁后，确定性渲染《故障复盘报告》的根因分析章节、Mermaid `mindmap` 和 `ai4se-visual` `cause-map`。
- 2026-06-23 已完成第十三个垂直切片: `INCIDENT_REVIEW/IMPROVEMENT` 支持模型输出 `artifact_data`，后端校验报告信息、事件摘要、根因摘要、改进优先级、SMART/CAPA 行动项、根因覆盖、复查计划、遗留风险、经验教训、组织学习、签署确认和阶段门禁后，确定性渲染《故障复盘报告》最终改进章节、Mermaid `pie` 和 `ai4se-visual` `action-board`。
- 2026-06-23 已完成第十四个垂直切片: `IDEA_BRAINSTORM/DEFINE` 支持模型输出 `artifact_data`，后端校验问题假设、目标用户画像、问题域全景、证据与验证状态、问题-用户-场景匹配、约束边界、反向验证和阶段门禁后，确定性渲染《问题域分析》和 Mermaid `mindmap`。
- 2026-06-23 已完成第十五个垂直切片: `IDEA_BRAINSTORM/DIVERGE` 支持模型输出 `artifact_data`，后端校验发散方法、创意全景、创意卡片、创意来源、搁置/排除记录和阶段门禁后，确定性渲染《创意发散》和 Mermaid `mindmap`。
- 2026-06-23 已完成第十六个垂直切片: `IDEA_BRAINSTORM/CONVERGE` 支持模型输出 `artifact_data`，后端校验决策矩阵、ICE 评分、资源约束、敏感性分析、验证实验、合并路径和阶段门禁后，确定性渲染《收敛聚焦》和 Mermaid `quadrantChart`。
- 2026-06-23 已完成第十七个垂直切片: `IDEA_BRAINSTORM/CONCEPT` 支持模型输出 `artifact_data`，后端校验定位声明、核心假设、Lean Canvas、MVP 功能、增长漏斗、Pre-mortem 风险、验证路线、不可做范围、决策记录、下一步行动和阶段门禁后，确定性渲染《产品概念简报》、Mermaid `pie`/`flowchart` 和 `ai4se-visual` `mvp-map`。
- DeepSeek V4 Flash capability 已明确为 `json_object_only`，仍只发送 OpenAI-compatible `response_format={"type":"json_object"}`，并保持 thinking disabled。
- `TEST_DESIGN` 四阶段、`REQ_REVIEW` 两阶段、`VALUE_DISCOVERY` 四阶段、`INCIDENT_REVIEW` 三阶段和 `IDEA_BRAINSTORM` 四阶段已完成结构化产物数据迁移；真实 DeepSeek V4 Flash smoke 仍需要显式凭证、网络和额度，不作为默认本地门禁。
- 2026-06-23 已完成本地 readiness gate: 从 `workflow_manifest.json` 枚举全部 17 个在线 stage，验证每个 stage 都有 `artifact_data` renderer、有效 fixture、artifact contract 通过、structured output instruction 要求 `artifact_data` 且不要求 `artifact_update.markdown`，并用 fake DeepSeek raw JSON stream 验证 `response_format={"type":"json_object"}` 与 thinking disabled。

## 目标

把 New Agents 后端产物链路从“模型直接输出最终 Markdown 文档”改造成“模型输出严格校验的业务数据，后端确定性渲染 Markdown、Mermaid 和 `ai4se-visual`”。

核心目标:

- DeepSeek V4 Flash 兼容: 继续使用 OpenAI-compatible Chat Completions、`response_format={"type":"json_object"}` 和 `thinking` disabled。
- 不依赖供应商 strict JSON Schema: 后端 Pydantic schema、应用级 contract、纠错重试和 deterministic renderer 作为最终可靠边界。
- 不新增 Lisa/Alex 专属运行时: 所有 workflow 继续走共享 `/api/agent/runs/stream`、共享 Agent Runtime、共享 typed SSE、共享 UI。
- 降低“格式不完整”频率: 模型不再负责拼完整 Markdown 标题、表格、Mermaid 代码块和 fenced block，后端 renderer 统一生成这些格式。

## 当前问题

- 现有 raw JSON streaming 已比纯文本标签稳定，但模型仍要把完整 Markdown 文档、Mermaid 和表格塞进 JSON 字符串，容易出现字段缺失、Markdown 结构不完整、Mermaid 格式错误或输出截断。
- DeepSeek V4 Flash 的 JSON mode 只能要求返回合法 JSON，不能保证字段完整、枚举合法、跨字段一致或业务 contract 合格。
- 失败时前端会看到“结构化输出生成失败”，即使 backend 已经做了校验与一次纠错重试，根因仍是模型承担了过多最终交付格式责任。

## 改造方向

### P0: 引入阶段产物数据 schema

为每个 workflow stage 定义 `artifact_data` schema，而不是让模型直接产出最终 Markdown。

建议形态:

- `chat`: 简短面向用户说明。
- `artifact_data`: 当前阶段的业务结构化数据，例如需求边界、风险项、测试点、用例、评分矩阵、用户画像、旅程阶段、创意卡片。
- `stage_action`: 保留现有阶段推进结构。
- `warnings`: 保留截断、证据不足、需要用户补充等运行时信号。

验收标准:

- 后端能拒绝缺字段、空数组、空白字符串、未知字段、枚举越界和跨字段不一致。
- 模型输出里不再要求包含完整 Markdown 文档正文。
- 每个 schema 都能从 `workflow_manifest.json`、stage contract 或独立 registry 中定位到对应 workflow/stage。

### P0: 后端确定性 renderer

新增共享 renderer，把 `artifact_data` 渲染为当前前端可消费的 Markdown Artifact。

renderer 职责:

- 生成固定 H1/H2 结构。
- 生成 Markdown 表格。
- 生成 Mermaid 图代码，使用统一深色可读样式由前端渲染。
- 生成 `ai4se-visual` fenced JSON block。
- 保证必需标题、必需 visual、stage gate 文案稳定存在。

验收标准:

- 同一份 `artifact_data` 每次渲染输出完全一致。
- `validate_agent_turn()` 仍作为最终守门，renderer 输出必须通过现有 artifact contract。
- 前端 typed SSE 协议不需要为首批改造改变。

### P0: DeepSeek V4 JSON mode adapter 收束

把 DeepSeek V4 Flash 作为明确 provider capability tier: `json_object_only`。

要求:

- `deepseek-v4-*` 默认关闭 thinking，保留现有兼容逻辑。
- 请求只发送 DeepSeek 兼容的 `response_format={"type":"json_object"}`。
- 不向 DeepSeek 发送供应商不支持或不稳定的 strict JSON Schema 参数。
- 后端 prompt 明确要求只输出 JSON object，不输出 Markdown fence，不输出解释文字。

验收标准:

- capability resolver 能区分 `json_schema_strict`、`json_object_only`、`plain_text_fallback`。
- DeepSeek V4 Flash 路径命中 `json_object_only`。
- raw output 先过 Pydantic schema，再进入 renderer，不合格则触发有限纠错重试。

### P1: 纠错重试从 Markdown 纠错改为数据纠错

失败反馈应围绕 `artifact_data` schema 和业务 contract，而不是让模型重写整篇 Markdown。

纠错提示应包含:

- 精确 schema/contract 错误。
- 当前 workflow/stage。
- 缺失字段、非法枚举或空内容的具体路径。
- 要求返回完整 JSON object。

验收标准:

- schema validation failure、contract validation failure、renderer validation failure 都进入同一类可观测 retry metric。
- 连续失败后返回明确错误，不伪造 artifact、不静默降级。
- 前端“重试本阶段生成”仍能立即重试当前阶段。

### P1: 分阶段迁移

迁移顺序建议:

1. 已完成: `TEST_DESIGN/CLARIFY` 垂直切片。
2. 已完成: `TEST_DESIGN/STRATEGY` 垂直切片。
3. 已完成: `TEST_DESIGN/CASES` 垂直切片。
4. 已完成: `TEST_DESIGN/DELIVERY` 垂直切片。
5. 已完成: `REQ_REVIEW/REVIEW` 垂直切片。
6. 已完成: `REQ_REVIEW/REPORT` 垂直切片。
7. 已完成: `VALUE_DISCOVERY/ELEVATOR` 垂直切片。
8. 已完成: `VALUE_DISCOVERY/PERSONA` 垂直切片。
9. 已完成: `VALUE_DISCOVERY/JOURNEY` 垂直切片。
10. 已完成: `VALUE_DISCOVERY/BLUEPRINT` 垂直切片。
11. 已完成: `INCIDENT_REVIEW/TIMELINE` 垂直切片。
12. 已完成: `INCIDENT_REVIEW/ROOT_CAUSE` 垂直切片。
13. 已完成: `INCIDENT_REVIEW/IMPROVEMENT` 垂直切片。
14. 已完成: `IDEA_BRAINSTORM/DEFINE` 垂直切片。
15. 已完成: `IDEA_BRAINSTORM/DIVERGE` 垂直切片。
16. 已完成: `IDEA_BRAINSTORM/CONVERGE` 垂直切片。
17. 已完成: `IDEA_BRAINSTORM/CONCEPT` 垂直切片。

每个阶段迁移必须同步:

- backend schema。
- backend renderer。
- artifact contract。
- visual contract。
- prompt 示例。
- backend runtime tests。
- frontend stream / failure card 回归测试，如协议不变则只补必要测试。

## 非目标

- 不引入 LangGraph。
- 不恢复旧 `/api/chat/stream`。
- 不恢复 `<CHAT>/<ARTIFACT>/<ACTION>` 标签协议。
- 不新增 Lisa/Alex 专属 API、store、runtime 或 renderer。
- 不把 DeepSeek V4 Flash 当作 strict Structured Outputs 模型。

## 关键验收

- DeepSeek V4 Flash 下，模型只输出 JSON 数据，后端负责产物格式。
- 至少一个完整 workflow stage 能完成: 用户输入 -> DeepSeek JSON mode -> Pydantic data schema -> backend renderer -> artifact contract -> typed SSE -> 前端展示。
- “格式不完整 / 结构化输出生成失败”不再由 Markdown 标题缺失、Mermaid fence 不完整或表格格式错误高频触发。
- 所有失败都能定位到 schema path、contract rule 或 renderer rule。

## 建议验证命令

- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q`
- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py -q`
- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py -q`
- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`

## 进入实现前需要补的设计问题

- `artifact_data` schema 是按 workflow/stage 手写 Pydantic model，还是先定义通用 block schema 再按 stage 组合。当前本地 readiness gate 已能防止新增在线 stage 遗漏 renderer/fixture/runtime 覆盖，但不改变 schema 设计策略。
- renderer 输出是否继续保存为 Markdown，或同时持久化 `artifact_data` 便于后续重渲染和审计。该问题会触及数据库、snapshot API 和前端审计面，保留为后续独立能力包。
- 真实 DeepSeek V4 Flash smoke gate 是否作为可选验证，还是每个阶段迁移都要求人工触发一次。当前本地 readiness gate 不需要凭证、网络和额度；真实 smoke 仍需显式环境配置后人工或专项 CI 触发。
