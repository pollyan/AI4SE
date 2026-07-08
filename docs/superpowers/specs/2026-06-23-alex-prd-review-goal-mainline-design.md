# Alex PRD 质量评审与补全 Workflow 主线落地设计

## 背景

当前主线 `tools/new-agents/` 已具备共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、run/artifact persistence 和共享 UI。Alex 在线能力包含创意发散与价值发现，但主线尚未提供面向产品经理的 PRD 质量评审与补全 workflow。`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 `PRD_REVIEW` 列为 P0 Alex 专业化切片，要求从产品完整性角度输出缺口清单、补全建议、质量门禁和修订版 PRD 大纲。

本轮目标是在当前主线落地完整、可运行、可验证的 Alex `PRD_REVIEW` workflow。它必须继续复用共享 Agent Runtime，不新增 Alex 专属 runtime、API path、store 或 renderer。

## Superpowers 头脑风暴记录

本节按 Superpowers `brainstorming` skill 的问题链执行。目标模式的自动执行授权将用户确认节点改为 Agent 基于当前仓库事实的自问自答裁决；该裁决不替代后续 TDD、验证和收尾证据。

### Explore Project Context

问：当前代码、文档、测试和 git 状态说明了什么？
答：`AGENTS.md` 和目标模式 playbook 要求 `tools/new-agents/` 继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run/artifact 模型和共享 UI，不允许新增 Alex 专属 runtime、API path、store 或 renderer。`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 `PRD_REVIEW` 列为 P0，要求从产品经理视角评审 PRD 的业务目标、用户价值、范围边界、指标、依赖、非功能需求和验收标准。当前主线已有 Alex `IDEA_BRAINSTORM` 与 `VALUE_DISCOVERY`，但缺少面向 PRD 产品完整性的在线 workflow。主工作区存在既有未提交改动，因此本轮在隔离 worktree `codex/alex-prd-review-goal-mainline` 中推进，并已 rebase 到当前 `master` 的最新 playbook 规则。

问：这个需求是否过大，需要拆成多个独立子项目？
答：不需要拆成多个 Superpowers 轮次。`PRD_REVIEW` 是单一用户入口、单一角色意图和单一 artifact 输出链路：用户输入 PRD，Alex 输出产品完整性评审与修订蓝图。它内部包含 manifest、prompt、contract、renderer、runtime 和前端 registry 多个实现面，但这些都是同一 workflow 能被用户使用的必要接线。如果拆薄成“只加 prompt”“只加 backend contract”或“只加 frontend slug”，都会形成不可用半成品。

问：有哪些相邻缺口需要同轮并入？
答：必须并入 workflow manifest、Alex workflow listing/slug、四个 stage prompt/template、backend workflow stages、artifact required headings、visual contract、`artifact_data` schema、deterministic renderer、runtime parser、前后端同步测试和 todo 记录。它们共同构成“用户能选择、能运行、能看到 contract-valid artifact、失败能显式报错、后续能追溯”的完整能力包。

### Visual Companion Decision

问：本轮是否需要浏览器视觉辅助来做 mockup、布局或视觉方案比较？
答：不需要。本轮新增的是配置化 workflow、prompt/template、后端 contract 和 deterministic artifact renderer；用户可见入口沿用现有 Alex workflow listing 和 Workspace 双栏 UI，不改布局、不新增复杂视觉交互。可视化 contract 只要求 renderer 输出现有 Mermaid / `ai4se-visual` block，适合用 contract tests 验证，不需要浏览器 mockup。

### Clarifying Questions

问：这个能力包真正服务的用户是谁？
答：产品经理、业务分析师、需求负责人，以及需要在研发或测试评审前提高 PRD 完整性的团队成员。

问：用户要完成的真实任务是什么？
答：用户已有 PRD 草稿，但不确定它是否能支撑研发、测试、上线评审和业务决策；他们要把 PRD 中的目标、价值、范围、需求、指标、依赖、非功能和验收缺口找出来，并转成可执行补全计划。

问：成功状态是什么？
答：Alex `PRD_REVIEW` 作为在线 workflow 出现在 Alex 工作流入口；用户触发后，四个阶段能通过共享 `/api/agent/runs/stream` 生成 PRD 输入盘点、质量评审、补全建议和修订蓝图；最终 artifact 满足 required headings、visual contract 和 stage action contract。

问：输入来源是什么？
答：用户直接粘贴 PRD 草稿、产品需求说明、需求蓝图或相关业务上下文。未来可以从 `VALUE_DISCOVERY/BLUEPRINT` 或历史 run handoff 输入承接，但本轮不新增新的 handoff UI 或外部文档导入。

问：PRD Review 与 Lisa `REQ_REVIEW` 的边界是什么？
答：Alex `PRD_REVIEW` 负责产品完整性和业务决策质量，覆盖业务目标、用户价值、范围边界、用户旅程、功能需求、异常路径、非功能、指标、依赖风险和验收标准。Lisa `REQ_REVIEW` 负责可测试性、测试风险、歧义、边界和复审条件。PRD Review 可以输出 Lisa 需求评审输入，但不替代 Lisa。

问：失败路径应如何处理？
答：沿用共享 runtime 的显式失败路径。模型输出必须先通过 `artifact_data` schema、renderer、`validate_agent_turn()` 和 workflow contract；缺字段、空数组、空白字符串、非法引用、visual 缺失或 stage gate 不满足时触发有限纠错重试，连续失败后返回结构化错误，不伪造 artifact，不静默降级。

问：哪些内容本轮明确不做？
答：不做 Jira/禅道等外部项目管理工具写入；不做 Lisa `REQ_REVIEW` 的评分深化；不做通用 artifact 质量诊断面板；不做 Story Breakdown；不做真实 DeepSeek V4 网络 smoke；不新增 Alex 专属 runtime、API、store 或 renderer。

问：本轮验证怎样覆盖 CI 风险？
答：后端用 workflow contract sync、contract registry、runtime parser、artifact renderer 和 agent contract tests 覆盖 manifest/backend/runtime/renderer 同步；前端用 workflow config 和 prompt 构造测试覆盖 slug、stage、template registry；再用 `py_compile`、frontend lint 和 `git diff --check` 覆盖语法、lint 和格式风险。真实模型 smoke 需要外部凭证、网络和额度，不作为本轮默认门禁。

### Approaches

方案 A：最小配置化 workflow 接线，只新增 manifest、frontend registry 和 prompt，让模型继续直接输出 Markdown。
取舍：实现最少，但与 DeepSeek V4 结构化产物方向冲突，仍让模型承担完整 Markdown/Mermaid 格式责任，容易出现格式不完整；后端 contract 对业务数据没有强约束。结论：不选。

方案 B：完整共享 runtime workflow，新增 manifest、frontend prompt/template、backend contract、`artifact_data` schema、deterministic renderer 和同步测试。
取舍：改动面更宽，但完全符合 New Agents 架构约束和 DeepSeek V4 兼容方向；用户得到完整 workflow，后续也能复用 renderer/contract 证据。结论：推荐并采用。

方案 C：先做 PRD Review 质量诊断面板或评分 helper，再以后接入 workflow。
取舍：看似降低风险，但用户不能从 Alex 入口完成 PRD 评审；也会把评分规则悬空在没有 workflow 输入输出的状态。结论：不选，评分/诊断应作为 workflow artifact 的一部分或后续独立质量面板能力包。

### Presented Design

Architecture：通过 `workflow_manifest.json` 声明 `PRD_REVIEW`、`agentId: alex`、`slug: prd-review`、四个 stages、artifact/visual contract、starter prompts 和 onboarding。前端 `WORKFLOWS` 与 prompt registry 从 manifest/模板接线；后端 `agent_contracts.py`、`agent_runtime.py`、`artifact_data_renderers.py` 使用共享 contract、runtime parser 和 deterministic renderer 承接。没有新的 API path、store、runtime 或 renderer pipeline。

Components：`workflow_manifest.json` 负责 workflow 定义；`frontend/src/core/workflows.ts` 和 `types.ts` 暴露 workflow id、slug、stage 和 prompt template；`frontend/src/core/prompts/prd_review/*.ts` 定义四阶段系统提示；`backend/agent_contracts.py` 保存 stage/headings/visual contract；`backend/artifact_data_renderers.py` 定义 PRD Review 数据 schema 与 Markdown/Mermaid/`ai4se-visual` renderer；`backend/agent_runtime.py` 分发 `artifact_data` 渲染；测试覆盖前后端同步。

Data flow：用户选择 Alex `prd-review` 并输入 PRD -> 前端按 workflow stage 构建 prompt -> 共享 `/api/agent/runs/stream` 调用模型 -> 模型返回 JSON object，包括 `chat`、`artifact_data`、`stage_action`、`warnings` -> 后端用 Pydantic schema 校验数据 -> deterministic renderer 生成 artifact markdown 与 visual blocks -> `validate_agent_turn()` 检查 headings/visual/stage_action -> typed SSE 推送 -> run/artifact persistence 保存并供前端展示。

Error handling：schema validation、contract validation、renderer validation 和 stage_action validation 都必须显式失败；runtime 可以进行有限纠错重试，但不得伪造 artifact 或使用 hidden fallback。前端继续展示共享 runtime 的结构化错误和重试入口，不新增 workflow 专属异常路径。

Testing：先补前端 workflow config 和后端 contract sync/runtime/renderer RED tests，再实现接线；GREEN 后运行后端 contract/runtime/renderer 组合测试、前端 workflow/prompt 测试、Python compile、frontend lint、`git diff --check`。这些测试证明 `PRD_REVIEW` 不是孤立配置，而是共享 runtime 可执行、可校验、可持久化的 workflow。

## 用户故事

作为产品经理或业务分析师，当我已有一份 PRD 草稿但担心目标、范围、需求、指标、依赖或验收标准不完整时，我可以在 Alex 工作区选择“PRD 质量评审”，提交 PRD 内容后获得分阶段评审、补全建议和修订蓝图，从而把 PRD 修订到可进入研发/测试评审的状态。

## Workflow 设计

新增 workflow:

- `workflowId`: `PRD_REVIEW`
- `slug`: `prd-review`
- `agentId`: `alex`
- 用户入口：Alex workflow listing 自动来自 manifest，链接 `/workspace/alex/prd-review`
- 共享 transport：继续使用 `/api/agent/runs/stream`

阶段设计：

1. `INVENTORY`：PRD 输入盘点。识别文档版本、目标用户、业务目标、范围、功能模块、约束、缺失信息和评审边界。
2. `QUALITY_AUDIT`：质量评审。按业务目标、用户价值、范围边界、用户旅程、功能需求、异常路径、非功能需求、指标、依赖风险和验收标准输出质量评分矩阵和缺口清单。
3. `COMPLETION_PLAN`：补全建议。把缺口转化为可执行补全项，明确优先级、owner、阻断性、补充材料和 Lisa 可测试性 handoff 输入。
4. `REVISION_BLUEPRINT`：修订蓝图。输出修订版 PRD 大纲、章节改写建议、验收标准补全、风险依赖和阶段门禁。

## Artifact Contract

最终阶段必须包含：

- `# PRD 修订蓝图`
- `## 1. 修订摘要`
- `## 2. 业务目标与用户价值补全`
- `## 3. 范围边界与功能需求补全`
- `## 4. 非功能需求与验收标准补全`
- `## 5. 风险、依赖与开放问题`
- `## 6. 修订版 PRD 大纲`
- `## 7. Lisa 需求评审输入`
- `## 8. 阶段门禁`

Visual contract 使用现有 Mermaid 与 `ai4se-visual`，不新增 renderer pipeline：

- `INVENTORY`: Mermaid `mindmap`
- `QUALITY_AUDIT`: `ai4se-visual` `score-matrix`
- `COMPLETION_PLAN`: `ai4se-visual` `priority-board`
- `REVISION_BLUEPRINT`: Mermaid `flowchart` 与 `ai4se-visual` `roadmap`

## 数据与运行时边界

- 新增 `artifact_data` schema 和 deterministic renderer，归入共享 `artifact_data_renderers.py`。
- `agent_runtime.py` 只通过 workflow/stage 分发表达差异，不新增专属 runtime。
- `agent_contracts.py` 保持 manifest 同步，新增 required headings / visual contract。
- 前端 prompt/template 通过 `STAGE_CONTENT_BY_TEMPLATE_ID` 注入，不绕过 workflow manifest。
- frontend types 只扩展 workflow id 联合类型，不新增独立 store。

## 验收条件

1. Given 主线缺少 `PRD_REVIEW`
   When 运行新增前后端配置同步测试
   Then 测试先失败，显示 manifest / workflow registry / backend contract 不包含 `PRD_REVIEW`
   Evidence: RED 测试输出。

2. Given 用户进入 Alex 工作流选择
   When 读取 frontend `WORKFLOWS` 和 agent listing
   Then `PRD_REVIEW` 以 `prd-review` 在线 workflow 出现，链接为 `/workspace/alex/prd-review`
   Evidence: frontend workflow config tests。

3. Given backend 收到 `PRD_REVIEW/REVISION_BLUEPRINT` 的合法 `artifact_data`
   When runtime parse agent output
   Then deterministic renderer 输出 contract-valid artifact，包含必需 headings、visual 和 stage action
   Evidence: backend runtime / renderer / contract tests。

4. Given manifest、backend contract 和 frontend prompt/template 任一面缺失
   When 运行同步测试
   Then 测试失败并指出缺失 workflow/stage/prompt/contract
   Evidence: workflow contract sync / prompt tests。

5. Given 本轮完成
   When 查看 `docs/todos/refactor/`
   Then E14 被标记为已消化或完成记录可追溯，DeepSeek V4 证据门禁保留为下一轮优先候选
   Evidence: todo 文档 diff。

## 风险与控制

- 新 workflow 接线面多，容易 manifest、frontend prompt 和 backend contract 不同步。通过同步测试覆盖 workflow id、stage id、prompt template id、artifact headings 和 visual contract。
- PRD Review 与 Lisa `REQ_REVIEW` 职责可能重叠。prompt 和 artifact 明确 Alex 负责产品完整性；可测试性问题只作为 Lisa handoff 输入。
- 复用既有隔离 worktree 可能带入过期基线。已将 `codex/alex-prd-review-goal-mainline` rebase 到当前 `master`，并重新执行本轮 spec 自审、验证和提交检查。
- 真实模型输出质量无法由本地 mock 完全证明。本轮证明 runtime/contract/renderer 可接收合法结构化数据并显式拒绝不合法数据；真实 DeepSeek V4 smoke 进入下一轮能力包。

## 本轮不做

- 不新增 Alex 专属 runtime、API、store、renderer。
- 不修改 intent-tester。
- 不新增外部项目管理工具写入。
- 不做通用 artifact 质量评分面板。
- 不运行需要外部凭证、网络或额度的真实模型 smoke。
