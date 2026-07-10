# New Agents 智能体架构收口待办

- 状态：活跃。切片 1 至 4 已完成；第 5、6 切片按前置条件顺序候选，其中切片 5 为下一轮目标模式候选。
- 创建日期：2026-07-10
- 优先级：P1 架构收口 + P2 模块边界治理
- 来源：2026-07-10 `tools/new-agents/` 只读架构审计
- 相关模块：`tools/new-agents/`；不包含 `tools/intent-tester/` 的架构调整。

## 目标

在不重写共享 Agent Runtime 的前提下，收口 New Agents 的结构化契约、workflow 配置镜像、服务端 run 状态归属和大模块边界。完成后，新增或修改 agent/workflow 时必须继续复用同一套 runtime、typed SSE、run persistence、frontend store 和 artifact rendering 链路，且漏配会被测试明确阻止。

## 审计事实与固定边界

- `workflow_manifest.json` 已被前后端读取，但 `WorkflowType`、prompt mapping、backend contract map、renderer registry 与部分 runtime instruction 仍有手工镜像。
- 正式 artifact version 已持久化 `artifactData`，但 Lisa CASES 测试资产仍从 Markdown 反解析。
- 前端仍会在缺少 typed `stage_action` 时从 chat 文案推断下一阶段动作。
- `ArtifactPane.tsx`、`artifact_data_renderers.py`、`agent_runtime.py` 和 frontend store 的职责面偏宽，但当前 shared Runtime/SSE/persistence 主链路有效。
- 不新增 Lisa、Alex 或未来 agent/workflow 专用 runtime、SSE/API 路径、store、持久化路径或渲染管线。
- 不改变 `/api/agent/runs/stream` 的公开路径或 typed SSE event 名称；错误必须继续显式失败，不得用生产 fallback、mock 或 fake success 掩盖问题。
- `tools/intent-tester/` 仅作为 Lisa 测试资产的下游集成边界，不纳入本待办的重构范围，除非某个切片得到新的直接耦合证据。

## 目标模式执行规则

- 切片是唯一计划、验收、提交和汇报单位；不创建“内部批次”、`4A/4B` 或无独立验收的子轮次。
- 每轮只推进一个未完成切片。开始前按 `docs/strategy/goal-mode-playbook.md` 做 CGA；CGA 若发现新的 P0/P1 冲突，可以调整后续顺序并在本文件记录原因。
- 每个切片先写或强化失败测试，再做最小实现；完成后记录实际修改文件、验证命令、结果、遗留风险和下一切片入口。
- 若某个切片经 CGA 证明过大，拆成两个或更多新的同级厚切片，每个新切片必须具备独立用户/工程信任闭环、验收、验证和提交边界。
- 本文件是长期 todo，不替代某轮的 spec 或 implementation plan；不在 `docs/strategy/` 创建本次重构过程文档。

## 切片路线

### 切片 1：结构化权威链路闭环（已完成，2026-07-10）

- [x] **目标**：下游机器消费与阶段推进只接受结构化、可持久化的权威输入。
- **范围**：`backend/test_assets.py`、`backend/test_asset_parsing.py`、`backend/tests/test_test_assets.py`、`backend/tests/test_test_asset_parsing.py`、`frontend/src/core/llm.ts`、`frontend/src/core/__tests__/llm.test.ts`。
- **完成状态**：新的 `TEST_DESIGN/CASES` 测试资产从持久化 `artifactData` 构建；历史 Markdown-only run 仅走显式、可诊断的兼容路径；chat 文案本身不能产生 `NEXT_STAGE`，只有有效 typed `stage_action` 能产生阶段推进动作。
- **验收**：结构化数据、历史兼容和缺失数据三类资产导出测试均有明确结果；SSE parser 测试证明 chat 文案不再是状态机输入；现有 typed SSE 主链路保持不变。
- **建议验证**：`test_test_assets.py`、`test_test_asset_parsing.py`、`frontend/src/core/__tests__/llm.test.ts`。
- **后续入口**：只有在结构化输入与阶段状态均不再绕开契约后，进入切片 2。
- **执行证据**：CASES 测试资产在 `artifactData` 存在时直接转换为既有资产 payload；只有 `artifactData is None` 的历史 artifact 使用 `legacy_markdown`，损坏的结构化数据显式失败而不降级。前端移除了 chat 正则推进，保留 typed `stage_action` 的既有目标阶段校验。
- **验证**：RED 阶段后端 4 项断言与前端 1 项断言按预期失败；GREEN 后定向 backend 35 passed、frontend 79 passed；扩展 backend 116 passed；`./scripts/test/test-local.sh new-agents` 通过，frontend 851 passed、backend 889 passed（4 个 slow deselected）；Python 致命错误 flake8 通过，`git diff --check` 通过。
- **已知质量门**：`npm run lint` 在本切片前后都失败于未触碰的 `StructuredVisual.tsx`、`artifactExport.ts` 和 `docxExport.ts` 对 `NodeEdgeStructuredVisual` 的 `columns/rows` 访问；保留为切片 6 的独立现状，不把它混入本切片。

### 切片 2：Workflow contract 机械同步闭环（已完成，2026-07-10）

- [x] **目标**：把新增 workflow/stage 所需的手工同步面变成可机械验证的 registry 边界。
- **范围**：`workflow_manifest.json`、`backend/workflow_manifest.py`、`backend/agent_contracts.py`、`backend/agent_runtime.py`、`backend/artifact_data_renderers.py`、`frontend/src/core/types.ts`、`frontend/src/core/workflowRegistry.ts`、`frontend/src/core/workflows.ts` 与同步测试。
- **完成状态**：workflow/stage、prompt/template id、artifact/visual contract、runtime instruction、renderer registration、regression sample 和 handoff 引用的遗漏或错配会在测试中失败；Pydantic schema 与 renderer 实现仍保留在代码中，不强行迁入 JSON。
- **验收**：manifest 仍是声明式元数据入口；纯声明字段优先从 manifest 派生；其余代码镜像都有直接 drift test；新增 workflow 的最小完整注册有单一、可读的验证入口。
- **建议验证**：`test_workflow_contract_sync.py`、`test_workflow_contract_registry.py`、`test_artifact_data_renderers.py`、`test_agent_runtime.py`、前端 `workflows.test.ts`。
- **后续入口**：机械同步护栏可靠后，才调整运行时恢复与 UI handoff 归属。
- **执行证据**：`agent_contracts.py` 的 stage、artifact heading、Mermaid 和 structured visual 公共 map 现在直接调用 `workflow_contract_registry`，保留原公共名称和既有消费者；Pydantic schema、H1 特例、renderer schema prompt 仍在代码。前端 `WorkflowType` 从 JSON manifest 类型派生，`buildSystemPrompt()` 以当前 stage 的 `artifactDataContract` 决定结构化模式，移除了手工 workflow/stage 集合。
- **防漂移验证**：新增后端 AST guard，要求四个 map 各有且仅有一个模块级 registry 调用赋值；新增前端 source guard，要求 workflow type 与 artifact-data mode 均从 manifest 派生。RED 阶段 backend 1 项、frontend 2 项按预期失败；实现中的残留 visual map 覆盖被“单一赋值” guard 捕获后移除。
- **验证**：扩展 backend contract/runtime/renderer suite 为 427 passed；前端定向为 118 passed；`./scripts/test/test-local.sh new-agents` 通过，frontend 853 passed、backend 890 passed（4 个 slow deselected）。
- **已知质量门**：`npm run lint` 仍只失败于未触碰的 `StructuredVisual.tsx`、`artifactExport.ts`、`docxExport.ts` 对 `NodeEdgeStructuredVisual` 的 `columns/rows` 访问，保留给切片 6，不在本切片混修。

### 切片 3：服务端 run 与前端状态归属闭环（已完成，2026-07-10）

- [x] **目标**：明确服务型 run 的服务端 snapshot 是执行历史权威来源，localStorage 只承担 UI cache 与未提交草稿。
- **范围**：`frontend/src/store.ts`、`frontend/src/services/runSnapshotService.ts`、`frontend/src/services/chatService.ts`、`frontend/src/components/ChatPane.tsx`、相关 store/chat/handoff 测试。
- **完成状态**：URL 或显式 `runId` 恢复能覆盖陈旧本地会话数据；artifact version、handoff 与 Story packet 不会从 local-only 内容生成；目标 workflow 的 handoff 可用性优先由 manifest 配置决定，而不是继续增加 workflow 条件分支。
- **验收**：恢复、切换 workflow/stage、继续对话与 handoff 的状态行为有前端回归测试；服务端 snapshot API 和持久化数据模型不变。
- **建议验证**：`store.test.ts`、`chatService`/workflow handoff tests、`ChatPane.test.tsx`、`test_run_persistence.py`、`test_workflow_handoffs.py`。
- **后续入口**：状态职责清晰后，进入 backend renderer/runtime 的文件边界治理。
- **执行证据**：`localStorage` hydration 检测到历史 `currentRunId` 时会清除聊天、产物、版本和协作状态，并停止恢复该 run id；后续服务型 run 持久化时只保留 workflow UI 选择。`Workspace` 对 URL `runId` 不再因内存中同名 run 而跳过 `fetchRunSnapshot()`，因此 server snapshot 会覆盖陈旧本地状态。
- **验证**：RED 阶段 store hydration 和同 runId URL 恢复各失败 1 项；GREEN 后定向 Vitest 58 passed；`./scripts/test/test-local.sh new-agents` 通过，frontend 854 passed、backend 890 passed（4 个 slow deselected）。
- **已知质量门**：`npm run lint` 的既有 `StructuredVisual.tsx`、`artifactExport.ts`、`docxExport.ts` union narrowing 错误未在本切片触碰，继续留给切片 6。

### 切片 4：后端 artifact renderer 与 instruction registry 模块化（已完成，2026-07-10）

- [x] **目标**：降低新增 workflow 对巨型 renderer 与 structured instruction 文件的改动冲突面。
- **范围**：`backend/artifact_data_renderers.py`、`backend/agent_runtime.py`、必要的 workflow 子模块、renderer/runtime tests。
- **完成状态**：按 workflow 或稳定领域边界拆分 artifact-data schema、renderer 与 instruction 示例；对外继续只暴露共享 renderer registry 和 Agent Runtime builder。
- **验收**：所有在线 stage 的 renderer key、runtime instruction、contract validation 与 deterministic visual 输出保持兼容；不新增任何 agent/workflow 专用 runtime。
- **建议验证**：`test_artifact_data_renderers.py`、`test_agent_runtime.py`、`test_agent_contracts.py`、`test_stream_services.py`。
- **后续入口**：后端 registry API 稳定后，进入 Artifact 工作台的 UI 模块化。
- **执行证据**：新增 `artifact_data_renderer_base.py` 承载共享严格模型，`artifact_data_value_schema.py` 承载 Value Discovery 四个 stage 的 schema 和 cross-reference validation，`artifact_data_renderer_value.py` 承载对应的确定性 Markdown/visual helper；主 renderer 显式重导出既有模型名并保留单一 `ARTIFACT_DATA_RENDERERS` registry。新增 `artifact_data_instruction_registry.py` 承载所有 stage 的结构化输出说明，`agent_runtime.py` 仅消费它并保留 Agent Runtime、stream delta 和 retry API。
- **防漂移验证**：新增源码结构测试，要求 Value renderer helper 与四个 Value artifact-data schema 各自只存在于专用模块；此前主 renderer 中 900 余行 Value/Blueprint/common helper 的第二份定义已删除，避免后定义静默覆盖前定义。
- **验证**：RED 阶段 renderer 和 instruction registry 模块边界各失败 1 项；GREEN 后 renderer/runtime/contract/stream 定向 suite 为 505 passed，致命错误 flake8 通过；`./scripts/test/test-local.sh new-agents` 通过，frontend 854 passed、backend 893 passed（4 个 slow deselected）。
- **已知质量门**：`npm run lint` 的既有 `StructuredVisual.tsx`、`artifactExport.ts`、`docxExport.ts` union narrowing 错误未在本切片触碰，继续留给切片 6。

### 切片 5：Artifact 工作台编辑与协作边界闭环

- [ ] **目标**：从 `ArtifactPane.tsx` 分离编辑、历史、冲突合并、评论和 section lock 的职责，同时保持现有交互与持久化协议。
- **范围**：`frontend/src/components/ArtifactPane.tsx`、对应 hooks/components、artifact collaboration/history services、`ArtifactPane` 与 store tests。
- **完成状态**：ArtifactPane 只承担工作台组合与公共状态连接；编辑、merge、评论、锁定和历史逻辑拥有独立可测试模块；API、artifact version 格式和用户行为不变。
- **验收**：冲突识别、自动/人工合并、评论锚点、section lock、版本恢复均有回归证据；不把工作流差异写成新的专用编辑管线。
- **建议验证**：`ArtifactPane.test.tsx`、artifact incremental render tests、`store.test.ts`、相关 backend persistence tests。
- **后续入口**：编辑协作稳定后，独立收口渲染与 Story packet UI 边界。

### 切片 6：Artifact 渲染、视觉诊断与 Story packet 边界闭环

- [ ] **目标**：从 ArtifactPane 分离 Markdown/visual rendering、visual diagnostics 与 Story packet 领域 UI，保持共享视觉组件和结构化 handoff 契约。
- **范围**：`frontend/src/components/ArtifactPane.tsx`、`StructuredVisual.tsx`、`Mermaid.tsx`、Story handoff packet services/tests、必要的 backend packet tests。
- **完成状态**：通用 Markdown、Mermaid、StructuredVisual 渲染继续共享；`STORY_BREAKDOWN/SPRINT_PLAN` 的 packet 是显式领域入口，不污染通用渲染管线；视觉失败继续以诊断状态显式呈现。
- **验收**：Mermaid/structured visual、visual diagnostics、Story packet 生成/复制/stale 判定均保持测试覆盖；packet 继续只消费持久化 `artifactData`。
- **建议验证**：`Mermaid.test.tsx`、`StructuredVisual.test.tsx`、`ArtifactPane.test.tsx`、`test_story_handoff_packets.py`。
- **收口条件**：完成后重新进行只读架构审计，决定是否需要将数据库启动期 schema 变更迁入显式 migration 机制；该事项在没有新证据前保持 P3，不提前实现。

## 非目标

- 不为 Lisa、Alex 或未来 agent 复制 runtime、transport、state、API 或 rendering infrastructure。
- 不重写 `/api/agent/runs/stream`、typed SSE schema、run persistence 或 artifact version 数据模型。
- 不把 prompt 全文或 Pydantic schema 强行塞入 `workflow_manifest.json`。
- 不从历史 `docs/todos/archive/` 的 phase 文档恢复旧任务；只以本文件及每轮 CGA 的当前代码证据为准。

## 执行记录

- 2026-07-10：根据 New Agents 架构审计创建。当前没有已执行切片；下一轮从切片 1 开始做 CGA。
- 2026-07-10：完成切片 1。新增结构化 CASES 资产转换与来源标记，移除 chat 文案阶段推断；未改变 API 路径、typed SSE event、run persistence schema 或 `tools/intent-tester/`。下一轮从切片 2 做目标承接检查。
- 2026-07-10：完成切片 2。声明性 workflow contract map、前端 workflow type 和 artifact-data prompt mode 均由 manifest 派生；新增单一赋值与 source guard，未改变 runtime、SSE、persistence 或 `tools/intent-tester/`。下一轮从切片 3 做服务端 run 与前端状态归属的 CGA。
- 2026-07-10：完成切片 3。服务型 run 不再从 `localStorage` 恢复会话、产物或 run id；URL `runId` 始终以服务端 snapshot 恢复。下一轮从切片 4 做 backend renderer/runtime 模块化的 CGA。
- 2026-07-10：完成切片 4。Value Discovery 的 artifact-data schema 与确定性 renderer 已从主文件拆出，stage instruction registry 已从 Runtime 拆出；共享 renderer registry、Agent Runtime、typed SSE 和持久化调用面保持兼容。下一轮从切片 5 做 Artifact 工作台编辑与协作边界的 CGA。
