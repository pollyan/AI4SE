# New Agents 演进 Todo

本文记录 `tools/new-agents/` 的长期演进 backlog。目标模式启动时应读取本文，并在完成主目标之外持续消化高优先级 todo。

## 使用规则

- `P0`：影响后续能力评估、专业可信度、主链路质量或目标模式选题的优先事项。
- `P1`：直接提升 Lisa / Alex 业务价值或平台扩展能力的事项。
- `P2`：体验、生态和增强型能力，等待 P0/P1 稳定后推进。
- 每次目标模式完成相关工作后，应更新对应条目的状态、证据和后续拆分。
- 这些 todo 不是一次性执行计划；进入实现前仍需按 `docs/strategy/goal-mode-playbook.md` 做 Current State Gap Analysis、spec、plan 和验证。
- todo 可以记录细分缺口，但进入目标模式时必须先聚合成用户可感知能力包或有独立价值的工程信任闭环；不要把单端点、单按钮、单字段、单测试或 0.x% 进度微切片直接作为 CGA milestone。
- 当一个 todo 下剩余事项都是技术子项时，CGA 必须先回答它们共同服务的用户动作链是什么；若无法形成“用户现在可以……”的能力增量，应暂缓并归入更大的能力包。
- 从本文选择下一轮 CGA 时，先按用户动作链聚合剩余缺口，再比较能力包优先级；不得因为某个子项容易实现，就把它单独包装成 milestone。
- 如果一个剩余子项只是完整能力链的前半段，且后半段没有明确技术阻断，应同轮合并；如果同轮合并会跨越不相关场景或显著扩大破坏面，必须把该子项记录为更大能力包的组成部分并改选其他可交付能力。
- 目标模式汇报进度时按剩余能力包估算，不按 todo 子弹、文件、字段、端点或测试数量估算；如果下一片只能带来极小百分比变化，优先重新聚合切片范围。

## P0 高优先级

### 1. 建立专业大模型 E2E 评判体系

**目标**：把浏览器级工作流测试中的可选 LLM judge 演进成衡量 New Agents 能力的核心评估手段。评判不只看最终 artifact，还要覆盖完整交互过程、专业方法使用、用户引导质量和信息重点表达。

**待办**：

- 扩展 `tests/e2e/new_agents_browser/` 的评判输入，从“最终产物文本”扩展为“完整会话轨迹 + 阶段切换 + 每阶段产物 + 最终产物”。
- 设计 Lisa 测试专家视角评判 rubric：需求澄清、风险识别、测试策略、测试用例、覆盖追溯、边界条件、异常路径、非功能需求、可执行性。
- 设计 Alex 业务分析师视角评判 rubric：问题定义、用户画像、用户旅程、价值主张、需求拆解、优先级、验收标准、业务闭环。
- 设计交互体验评判 rubric：对话引导是否清晰、是否主动说明使用的方法、是否突出关键风险/结论、是否避免大段重复 artifact、是否能帮助用户做确认和补充。
- 设计可视化评判 rubric：图表是否存在、是否适合当前阶段、是否能帮助快速理解重点、是否与正文一致、是否可渲染。
- 输出严格 JSON verdict，至少包含 `pass`、`score`、`dimension_scores`、`issues`、`evidence`、`recommendations`。
- 保持默认 E2E 确定性测试不依赖模型；LLM judge 继续通过显式环境变量启用。
- 将评判结果纳入后续目标模式收尾证据：当改动影响工作流、prompt、artifact 或 UI 引导时，应说明是否运行了 judge，未运行则说明原因。

**验收证据**：

- 浏览器 E2E 能收集并传入完整工作流轨迹。
- judge 能按 Lisa / Alex 两类专业角色输出分维度评分。
- 至少覆盖 Lisa `test-design` 和 Alex `value-discovery` 两条完整流程。

**进展记录**：

- 2026-06-19: 浏览器 E2E runner 已从只返回最终 artifact 字符串升级为返回结构化 `WorkflowRunResult`，包含 `final_artifact`、`stage_artifacts`、`conversation_events` 和 `stage_transitions`。Lisa `test-design` 与 Alex `value-discovery` 确定性 E2E 已断言完整阶段 artifact、用户/助手会话事件和阶段确认事件。
- 2026-06-19: 可选 LLM judge prompt 已改为消费完整工作流轨迹，包含完整会话轨迹、阶段切换、每阶段产物和最终产物；真实模型调用仍由 `NEW_AGENTS_E2E_LLM_JUDGE=1` 显式启用。
- 验证: `NEW_AGENTS_E2E_LLM_JUDGE=0 python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py -q`，3 passed / 2 skipped。
- 2026-06-19: 可选 LLM judge verdict 已从 `pass/score/issues` 扩展为严格 JSON，包含 `pass`、`score`、`dimension_scores`、`issues`、`evidence` 和 `recommendations`；解析器会拒绝缺字段、非法总分和非法维度分数。
- 2026-06-19: judge prompt 已按 Lisa / Alex 分别注入测试专家维度和业务分析师维度，并追加通用交互体验维度与可视化维度。真实模型调用仍保持显式启用。
- 验证: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py -q`，6 passed。
- 验证: `NEW_AGENTS_E2E_LLM_JUDGE=0 python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py -q`，2 passed / 2 skipped。

### 2. 系统性审视并升级所有工作流产出物

**目标**：从专业测试人员和专业业务分析人员视角重新审视每个 workflow 的 artifact 是否合理、完整、可执行、可复用。

**待办**：

- 为 Lisa 工作流建立专业 artifact 标准：测试设计、需求评审、故障复盘分别定义必备章节、专业方法、质量门槛和可视化要求。
- 为 Alex 工作流建立专业 artifact 标准：创意头脑风暴、价值发现，以及后续 PRD / 用户故事方向分别定义方法论、结构和判断标准。
- 对现有 `WORKFLOWS`、阶段 prompt、template、后端 artifact heading contract 做逐项差距分析。
- 明确哪些内容属于 prompt，哪些属于 artifact contract，哪些应由前端可视化组件承担，避免只靠提示词维持质量。
- 给每个阶段补“专业方法显性表达”：让左侧对话明确说明本轮使用了什么分析方法、为什么用、得到什么关键结论。

**验收证据**：

- 每个在线 workflow 都有专业产物审计结论。
- 每个阶段都有明确的方法论、产物结构和质量校验点。
- 评判体系能检测“方法论缺失”和“产物空洞”。

**进展记录**：

- 2026-06-19: 已新增 `docs/plans/2026-06-19-new-agents-artifact-audit.md`，基于前端 `WORKFLOWS` 和后端 `REQUIRED_ARTIFACT_HEADINGS` 完成 5 个在线 workflow 的 artifact 专业审计基线，覆盖专业目标、当前 contract 摘要、主要差距和推荐后续切片。
- 2026-06-19: 审计建议后续优先推进 `REQ_REVIEW/REVIEW` 问题清单字段收紧、`TEST_DESIGN/CASES` 用例字段收紧、`VALUE_DISCOVERY/JOURNEY` 用户旅程结构化、`INCIDENT_REVIEW/IMPROVEMENT` 行动项字段收紧和 `IDEA_BRAINSTORM/CONVERGE` 评分口径收紧。
- 2026-06-19: 已完成 `REQ_REVIEW/REVIEW` 问题清单字段收紧，后端 contract 现在要求 `问题描述`、`优先级`、`所属需求章节`、`影响范围`、`证据/依据`、`建议`、`责任方/确认人`，前端 prompt/template 已同步。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -k 'req_review' -q`，5 passed / 63 deselected。
- 2026-06-19: 已完成 `TEST_DESIGN/CASES` 用例字段收紧，后端 contract 现在要求 `ID`、`用例标题`、`优先级`、`测试维度`、`关联测试点`、`关联风险`、`前置条件`、`操作步骤`、`测试数据`、`预期结果`，前端 prompt/template 已同步。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -k 'test_design' -q`，8 passed / 61 deselected。
- 2026-06-19: 已完成 `VALUE_DISCOVERY/JOURNEY` 用户旅程字段收紧，后端 contract 现在要求 `旅程阶段`、`触点渠道`、`用户任务`、`情绪评分`、`关键痛点`、`现有方案不足`、`机会假设`、`成功指标`，前端 prompt/template 已同步。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -k 'value_discovery' -q`，9 passed / 61 deselected。
- 2026-06-19: 已完成 `INCIDENT_REVIEW/IMPROVEMENT` 改进行动字段收紧，后端 contract 现在要求 `ID`、`改进措施`、`类型`、`对应根因`、`建议负责人`、`完成期限`、`验证方式`、`验收标准`、`优先级`、`当前状态`、`追踪机制`，前端 prompt/template 已同步。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -k 'incident_review' -q`，7 passed / 64 deselected。
- 2026-06-19: 已完成 `IDEA_BRAINSTORM/CONVERGE` 评分口径字段收紧，后端 contract 现在要求 `评分口径`、`影响力`、`信心`、`实现难度`、`ICE得分`、`淘汰理由`、`推荐方案`、`下一步验证`、`合并逻辑`，前端 prompt/template 已同步。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -k 'idea_brainstorm' -q`，9 passed / 63 deselected。

### 3. 建立产出物可视化增强规范

**目标**：让用户不只阅读枯燥 Markdown 报告，而是能通过图表、矩阵、时间线、看板、评分卡快速理解重点。

**待办**：

- 恢复并制度化 Mermaid 使用：为每个 workflow/stage 定义推荐图形，如风险矩阵、测试金字塔、测试点拓扑、时间线、5-Why 链路、用户旅程、路线图。
- 评估 Mermaid 之外的可视化块：例如风险热力图、需求-风险-用例追溯矩阵、用户旅程组件、评分卡、行动项看板。
- 设计结构化可视化协议，避免模型直接手写复杂 HTML；优先让模型输出结构化数据，前端用共享组件渲染。
- 将可视化要求纳入 artifact contract 和 LLM judge rubric。
- 保持所有可视化走共享渲染管线，不为 Lisa / Alex 建立独立渲染分支。

**验收证据**：

- 每个核心工作流至少有一个阶段具备稳定可视化输出。
- 可视化内容能被 E2E 或组件测试验证。
- LLM judge 能评价可视化是否提升理解，而不只是是否出现图表。

**进展记录**：

- 2026-06-19: 已新增后端 Mermaid 可视化契约 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS`，首轮覆盖 `TEST_DESIGN/STRATEGY`、`REQ_REVIEW/REPORT`、`INCIDENT_REVIEW/TIMELINE`、`INCIDENT_REVIEW/ROOT_CAUSE`、`INCIDENT_REVIEW/IMPROVEMENT`、`IDEA_BRAINSTORM/CONVERGE`、`VALUE_DISCOVERY/JOURNEY`，保证每个在线 workflow 至少一个关键阶段必须输出适配的 Mermaid 图。
- 2026-06-19: artifact contract prompt 会按阶段注入必需 Mermaid 图类型；后端校验独立解析 fenced Mermaid code block，不复用标题 substring 校验，避免代码块内标题伪造和可视化漏检相互干扰。
- 2026-06-19: 已新增首个 Mermaid 之外的结构化可视化协议 `ai4se-visual`，前端支持模型输出 JSON `traceability-matrix` 并通过共享 `StructuredVisual` 组件渲染为可访问追溯矩阵；无效 JSON/schema 会在预览区显示明确错误，不再要求模型手写复杂 HTML。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/markdownCodeRenderer.test.tsx`，22 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 2026-06-19: `ai4se-visual` 已接入后端 artifact contract 首个阶段，`TEST_DESIGN/CASES` 现在必须包含 fenced `ai4se-visual` JSON 且 `type=traceability-matrix`，contract prompt 会按阶段注入结构化可视化要求并明确不要手写复杂 HTML。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -q`，77 passed。
- 2026-06-19: 可选 E2E LLM judge prompt 已补充结构化可视化评分口径，明确评估 `ai4se-visual` JSON 是否适合当前阶段、`traceability-matrix` 是否能追溯需求/风险/测试点/用例并与正文一致，并要求 `dimension_scores` 包含“可视化质量”或等价维度。
- 验证: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py -q`，7 passed。

## P1 中优先级

### 4. 共享 workflow manifest

**目标**：将 workflow、stage、persona、artifact contract、listing、slug、可视化要求收敛为共享配置源，降低前后端漂移风险。

**待办**：

- 设计 manifest schema。
- 从 manifest 生成或加载前端 `WORKFLOWS` 与后端 `WORKFLOW_STAGES` / artifact contract。
- 保留现有 `test_workflow_contract_sync.py` 作为迁移护栏。

**进展记录**：

- 2026-06-19: 已新增 `tools/new-agents/workflow_manifest.json` 作为在线 workflow 首轮共享元数据源，覆盖 workflow id、agentId、slug、名称、描述、listing、stage id/name 和 onboarding；prompt/template 仍保留在 TypeScript 模块中，避免一次性迁移运行时提示词。
- 2026-06-19: 前端 `WORKFLOWS` 已改为由共享 manifest 元数据 + stage prompt/template 映射组装，`WORKFLOW_SLUGS`、`SLUG_TO_WORKFLOW` 和在线 workflow card 继续从 `WORKFLOWS` 派生。
- 2026-06-19: 后端 `test_workflow_contract_sync.py` 已从正则解析 `workflows.ts` 升级为读取共享 manifest，校验 manifest stage 顺序与 `WORKFLOW_STAGES` 一致，并校验 manifest stage keys 与 `REQUIRED_ARTIFACT_HEADINGS` 一致。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_workflow_contract_sync.py -q`，2 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts`，12 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。

### 5. 服务端会话与产物持久化

**目标**：从浏览器 localStorage 过渡到服务端 run/session/artifact/version 持久化，支持恢复、审计、分享和评判数据采集。

**待办**：

- 设计 `agent_runs`、`agent_messages`、`agent_artifacts`、`artifact_versions` 数据模型。
- 保持 typed SSE 主链路不分叉。
- 为 LLM judge 提供可复用的会话轨迹来源。

**进展记录**：

- 2026-06-19: 已完成服务端持久化第一片，新增通用 `AgentRun`、`AgentMessage`、`AgentArtifact`、`AgentArtifactVersion` SQLAlchemy 模型，对应 `agent_runs`、`agent_messages`、`agent_artifacts`、`agent_artifact_versions` 表；新增 `run_persistence.py` repository，支持创建 run、追加有序消息、按 run/stage 追加 artifact version、读取 snapshot，并复用 `WORKFLOW_STAGES` 拒绝非法 workflow/stage。
- 2026-06-19: 当前切片未迁移前端 `localStorage`；后续仍需恢复 API、前端状态迁移和 judge 数据读取。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py -q`，8 passed。
- 2026-06-19: 已将服务端持久化接入现有 `/api/agent/runs/stream` typed SSE 主链路，没有新增分叉 endpoint；请求可选 `runId`，无 `runId` 时创建 run，有 `runId` 时复用并校验 workflow/agent，`run_started` 返回 `runId`，成功轮次会记录 user message、最终 assistant chat 和当前阶段 artifact version。
- 2026-06-19: `stream_services.py` 通过可选 persistence adapter 接入持久化，纯服务测试仍可不依赖 Flask/数据库；路由层注入真实 `AgentRunPersistence`，workflow 到 agent 的归属从共享 `workflow_manifest.json` 读取。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_request_schemas.py tests/test_sse_encoder.py tests/test_stream_services.py tests/test_agent_endpoint.py tests/test_run_persistence.py -q`，64 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，213 passed / 1 skipped。
- 2026-06-19: 前端已新增 `currentRunId` workspace state，首轮请求不携带 `runId`，收到 `run_started.runId` 后写入 store，后续同一工作流会把 `runId` 带回 `/new-agents/api/agent/runs/stream` 以复用服务端 run；`clearHistory()` 和 `setWorkflow()` 会清空当前 runId，避免跨工作流串写。
- 2026-06-19: 当前仍未提供服务端恢复/list/detail API，也未从服务端 snapshot 重建前端工作台；localStorage 仍保存本地工作台状态。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts src/core/__tests__/llm.test.ts`，88 passed。
- 2026-06-19: 已新增只读 `GET /api/agent/runs/{runId}` snapshot API，返回 `run`、有序 `messages` 和当前 `artifacts`，可作为后续前端恢复、审计、分享和 LLM judge 数据采集来源；未知 run 返回 JSON 404。
- 2026-06-19: 当前仍未提供 run list、分享权限模型、前端恢复 UI 或从 snapshot 自动重建工作台。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q`，12 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，215 passed / 1 skipped。
- 2026-06-19: 前端已新增服务端 snapshot 恢复基础层，`fetchRunSnapshot(runId)` 可读取并校验 `GET /api/agent/runs/{runId}` 响应，异常协议会显式失败；workspace store 新增 `restoreRunSnapshot()`，可按 snapshot 重建 workflow、stage、chat history、当前 artifact、stage artifacts、artifact history 和 `currentRunId`，并拒绝 agent/stage 与 workflow 不匹配的 snapshot。
- 2026-06-19: 当前仍未提供 run list、分享权限模型、恢复 UI 或自动从 URL/query 参数恢复工作台；localStorage 仍保存当前 workspace 状态。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts src/services/__tests__/runSnapshotService.test.ts src/services/__tests__/workflowHandoffService.test.ts src/core/__tests__/llm.test.ts`，98 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 2026-06-19: Workspace 已接入 `?runId=` 自动恢复入口，进入 `/workspace/:agentId/:workflowId?runId=<id>` 时会读取服务端 snapshot 并恢复工作台；若 snapshot 所属 workflow 与当前 URL 不一致，会 `replace` 到 snapshot 对应的 agent/workflow URL。恢复失败时保留当前本地 workspace，不伪造成功。
- 2026-06-19: 当前仍未提供 run list、分享权限模型或专门的恢复 UI；URL 恢复依赖调用方已持有 runId。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/Workspace.test.tsx src/__tests__/store.test.ts src/services/__tests__/runSnapshotService.test.ts src/core/__tests__/llm.test.ts`，103 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 2026-06-19: 后端已新增只读 `GET /api/agent/runs` run list 基础 API，默认返回最近 20 条 persisted runs，支持 `workflowId` 和 `limit` 查询；列表项包含 run 元信息、最后一条消息和当前 artifact 摘要，不返回完整 artifact 内容。未知 workflowId 返回显式 400。
- 2026-06-19: 当前仍未提供前端 run list UI、分享权限模型或用户级访问控制；该 endpoint 只作为本地恢复/审计基础能力。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py::test_agent_runs_list_endpoint_returns_recent_runs_with_summaries tests/test_agent_endpoint.py::test_agent_runs_list_endpoint_filters_by_workflow_id tests/test_agent_endpoint.py::test_agent_runs_list_endpoint_rejects_unknown_workflow_id -q`，3 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py tests/test_run_persistence.py tests/test_context_builder.py -q`，39 passed。
- 验证: `git diff --check`，passed。
- 2026-06-19: 前端已新增最小历史会话入口，Header 中的“历史会话”会调用 `fetchRunList({ limit: 20 })` 展示最近 run 摘要；点击条目会导航到对应 `/workspace/:agentId/:workflowSlug?runId=<id>`，复用 Workspace 的 snapshot 自动恢复链路。
- 2026-06-19: 当前仍未提供完整恢复中心、分页/搜索、分享权限模型或用户级访问控制；历史会话入口面向本地开发/演示恢复。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/Header.test.tsx src/pages/__tests__/Workspace.test.tsx src/__tests__/store.test.ts`，45 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 2026-06-19: 历史会话弹层已补充“全部 / 当前工作流”过滤，当前工作流模式会调用 `fetchRunList({ workflowId, limit: 20 })`，避免 Lisa/Alex 多 workflow run 混在一起时难以定位当前工作流历史。
- 2026-06-19: `GET /api/agent/runs` 已补充 `offset`、`query`、`total`、`hasMore` 和 `nextOffset`，支持按 workflow 过滤后的分页，并可搜索 run 元数据、消息内容和当前 artifact 摘要。
- 2026-06-19: 历史会话弹层已补充搜索框、结果计数和“加载更多”，搜索会重置当前结果，加载更多会沿用当前 scope/query 追加下一页。
- 2026-06-19: 当前仍未提供完整恢复中心、分享权限模型或用户级访问控制。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx src/services/__tests__/runSnapshotService.test.ts src/pages/__tests__/Workspace.test.tsx src/__tests__/store.test.ts`，48 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q`，20 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/Header.test.tsx`，12 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py tests/test_run_persistence.py tests/test_context_builder.py -q`，41 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。

### 6. 上下文管理与摘要机制

**目标**：替代前端简单拼接历史和截断前序产物的方式，建立服务端 context builder。

**待办**：

- 分层保存用户补充、阶段关键结论、产物摘要和决策。
- 明确截断策略和可见告警。
- 让模型能基于摘要稳定跨阶段推进。

**进展记录**：

- 2026-06-19: 已完成服务端 context builder 第一片，新增 `context_builder.py`，基于持久化 run 的有序 messages 构造 bounded runtime prompt；无历史时保持当前输入不变，有历史时按 `[用户]` / `[助手]` 标签注入，过滤助手错误/停止等控制反馈，超过预算时丢弃最旧消息并加入截断说明。
- 2026-06-19: `stream_services.py` 已通过 persistence adapter 在调用 runtime 前生成服务端上下文 prompt；前端 `llm.ts` 在已有 `currentRunId` 时不再把本地 `chatHistory` 拼入请求，只发送当前用户输入和附件内容，避免前后端重复注入历史。
- 2026-06-19: 当前仍未实现持久化摘要表、前序 artifact 服务端摘要、前端可见截断告警或基于 snapshot 的工作台恢复。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py tests/test_stream_services.py -q`，17 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts`，64 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，220 passed / 1 skipped。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/__tests__/store.test.ts`，89 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 2026-06-19: 已补充服务端上下文截断的可见告警链路，`context_builder.py` 在裁剪较早 messages 时返回 `context_truncated` warning，`stream_services.py` 通过 `run_started.warnings` 暴露给前端，`llm.ts` 将其映射为左侧对话首帧提示；该状态与右侧 artifact 截断 banner 分离。
- 2026-06-19: 当前仍未实现持久化摘要表、前序 artifact 服务端摘要或基于 snapshot 的工作台恢复。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py tests/test_stream_services.py tests/test_sse_encoder.py -q`，26 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts`，65 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，222 passed / 1 skipped。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/__tests__/store.test.ts`，90 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 2026-06-19: 已补充前序 artifact 服务端摘要，`context_builder.py` 会读取 run snapshot 中的 current artifacts，以 `[已保存阶段产物摘要]` / `[阶段产物: <stageId>]` 形式将 bounded Markdown 摘要注入 runtime prompt；单个 artifact 过长时会在摘要内标明截断，整体 prompt 仍复用 `context_truncated` warning 策略。
- 2026-06-19: 当前仍未实现持久化摘要表、结构化决策/阶段结论表或基于 snapshot 的工作台恢复。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py -q`，8 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py tests/test_stream_services.py tests/test_sse_encoder.py -q`，29 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，225 passed / 1 skipped。
- 验证: `git diff --check`，passed。
- 2026-06-19: 已新增 `agent_context_summaries` 持久化表和确定性 artifact summary formatter；`record_artifact_version` 会 upsert 当前阶段 artifact summary，`get_run_snapshot` 返回 `contextSummaries`，`context_builder.py` 优先使用持久化 summary，旧数据缺 summary 时回退 current artifact。
- 2026-06-19: 当前仍未实现用户补充、阶段关键结论、决策的结构化摘要，也未实现基于 snapshot 的工作台恢复。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py -q`，12 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py -q`，9 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py tests/test_context_builder.py tests/test_stream_services.py tests/test_agent_endpoint.py -q`，47 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，228 passed / 1 skipped。
- 验证: `git diff --check`，passed。
- 2026-06-19: 已补充分层结构化摘要，`append_run_message` 会按当前 stage 聚合用户补充为 `user_supplement`，`record_artifact_version` 会同步维护 `stage_conclusion` 和 `decision` 摘要；这些摘要继续复用 `agent_context_summaries`，没有新增 agent/workflow 专属存储分支。
- 2026-06-19: `context_builder.py` 已将用户补充、阶段结论、关键决策作为独立上下文块注入 runtime prompt，再叠加当前 artifact summary 和有序消息历史，支持模型基于摘要稳定跨阶段推进。
- 2026-06-19: 前端已新增上下文摘要可见与本地校准入口，Header 的“上下文摘要”会展示 snapshot 恢复出的 `contextSummaries`，按摘要类型和来源阶段显示，并允许在当前工作台内编辑保存展示内容；本轮不写回服务端，避免把本地校准误认为持久摘要。
- 2026-06-19: 上下文摘要校准已升级为服务端持久写回，后端新增 `PATCH /api/agent/runs/{runId}/context-summaries`，基于 `sourceType/sourceStageId/summaryType` 只更新已有摘要；前端“上下文摘要”保存会调用该接口，并用服务端返回内容更新当前工作台，因此后续 snapshot 恢复和 context builder 会使用校准后的摘要。
- 2026-06-19: 已新增独立关键决策录入，后端 `POST /api/agent/runs/{runId}/context-summaries/decisions` 会把当前阶段人工决策 upsert 为 `artifact/decision` 摘要；前端“上下文摘要”弹层提供“关键决策录入” textarea，保存成功后把服务端返回的 decision summary 合入当前工作台，后续 snapshot 和 context builder 可消费该决策。
- 2026-06-19: 当前仍未提供用户级摘要写回权限控制；人工校准/人工决策摘要也尚未与后续自动 artifact 摘要覆盖做锁定/优先级区分。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py -q`，20 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q`，32 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts`，39 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`，21 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py tests/test_agent_endpoint.py tests/test_context_builder.py -q`，62 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts src/components/__tests__/Header.test.tsx`，60 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py -q`，17 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q`，30 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/Header.test.tsx`，26 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py tests/test_agent_endpoint.py tests/test_context_builder.py -q`，57 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/Header.test.tsx src/__tests__/store.test.ts`，57 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts src/components/__tests__/Header.test.tsx`，51 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py -q`，14 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py -q`，10 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py tests/test_context_builder.py tests/test_stream_services.py tests/test_agent_endpoint.py -q`，58 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts src/pages/__tests__/Workspace.test.tsx`，41 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，249 passed / 1 skipped。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。

### 7. Lisa 测试资产闭环

**目标**：让 Lisa 从报告生成升级为测试资产管理助手。

**待办**：

- 测试点库、用例版本、需求覆盖追溯、风险矩阵和评审问题闭环。
- 支持导出给 intent-tester 或其他测试管理工具，但短期不改 intent-tester 主链路。

**进展记录**：

- 2026-06-19: 已完成 Lisa 测试资产导出基础层，新增 `test_assets.py` 从 `TEST_DESIGN/CASES` artifact 解析结构化 `testCases` 和 `coverageTrace`，并通过 `GET /api/agent/runs/{runId}/test-assets` 提供只读导出；缺少 CASES artifact 或非 TEST_DESIGN run 会显式返回错误，不返回空成功。
- 2026-06-19: 当前仍未实现独立测试点库、用例版本管理、风险矩阵实体、资产编辑 UI 或 intent-tester 导入/执行接力。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -q`，3 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py::test_agent_run_test_assets_endpoint_exports_cases_artifact tests/test_agent_endpoint.py::test_agent_run_test_assets_endpoint_returns_404_without_cases_artifact tests/test_test_assets.py -q`，5 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py tests/test_run_persistence.py -q`，29 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，233 passed / 1 skipped。
- 验证: `git diff --check`，passed。
- 2026-06-19: Lisa 测试资产导出已补充 `sourceArtifactVersion`，导出结果可追溯到当前 CASES artifact version；同一 run/stage 多次更新测试用例集后，导出会指向最新 version。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py::test_agent_run_test_assets_endpoint_exports_cases_artifact -q`，5 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，234 passed / 1 skipped。
- 验证: `git diff --check`，passed。
- 2026-06-19: Lisa 测试资产导出已补充 `coverageSummary`，基于 `coverageTrace` 计算总测试点、已覆盖/部分覆盖/未覆盖数量、总体覆盖率和按优先级覆盖率，支持快速判断测试点覆盖闭环质量。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py::test_agent_run_test_assets_endpoint_exports_cases_artifact -q`，5 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，234 passed / 1 skipped。
- 验证: `git diff --check`，passed。
- 2026-06-19: Lisa 测试资产导出已补充非阻断 `assetIssues`，可识别覆盖追溯引用不存在的测试用例、测试用例未被任何测试点引用等资产质量问题；缺少 CASES artifact 或表格不可解析仍保持显式失败。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py::test_agent_run_test_assets_endpoint_exports_cases_artifact -q`，6 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，235 passed / 1 skipped。
- 验证: `git diff --check`，passed。
- 2026-06-19: Lisa 测试资产导出已补充派生 `riskMatrix`，按风险聚合关联测试用例、测试点、优先级、测试维度和覆盖状态；当前仍未实体化风险库或风险生命周期管理。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py::test_agent_run_test_assets_endpoint_exports_cases_artifact -q`，6 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，235 passed / 1 skipped。
- 验证: `git diff --check`，passed。
- 2026-06-19: Lisa 测试资产导出已补充 `intentTesterDrafts`，将每条结构化用例映射为 intent-tester `/api/testcases` 创建 payload 草稿，包含名称、描述、分类、优先级、标签和有效 step action；该草稿只读导出，不自动写入 intent-tester，导入前仍需人工校准 URL、定位语义和可执行步骤。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py::test_agent_run_test_assets_endpoint_exports_cases_artifact -q`，6 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，235 passed / 1 skipped。
- 验证: `git diff --check`，passed。
- 2026-06-19: Lisa 测试资产已新增服务端实体化能力，`POST /api/agent/runs/{runId}/test-assets/materialize` 会把当前 `TEST_DESIGN/CASES` artifact 解析为可读取的资产集，沉淀测试用例、用例版本、测试点覆盖、风险矩阵和资产质量问题；同一 run 的资产集会随最新 CASES artifact version 刷新。
- 2026-06-19: 已新增 `GET /api/agent/test-assets/{collectionId}` 和 `PATCH /api/agent/test-assets/{collectionId}/test-cases/{caseId}`，支持读取实体化资产集并以追加版本方式更新单条测试用例，避免覆盖历史版本。
- 2026-06-19: 前端已新增 Lisa 测试资产入口，`TEST_DESIGN` 且存在服务端 `currentRunId` 时，Header 的“测试资产”会实体化当前 CASES artifact，展示覆盖率、用例列表和来源版本，并支持编辑单条用例标题/优先级；保存后通过 `PATCH /api/agent/test-assets/{collectionId}/test-cases/{caseId}` 追加新版本。
- 2026-06-19: 前端已新增单条 intent-tester 草稿导入，测试资产弹层会为存在 `intentTesterDrafts.sourceCaseId` 匹配的用例展示“导入 TC-xxx”；点击后通过 `/intent-tester/api/testcases` 创建 intent-tester 用例，并在成功后显示新用例 ID。当前保持人工触发，避免草稿未校准 URL/定位语义时自动污染用例库。
- 2026-06-19: 前端已新增手动批量导入 intent-tester 草稿，测试资产弹层可一次导入当前集合中尚未导入的 `intentTesterDrafts`，并在用例卡片上显示创建后的 intent-tester ID；该能力仍需用户显式点击，不会在实体化时自动写入。
- 2026-06-19: 前端已新增导入后执行接力入口，已导入的用例会显示“去执行 #id”链接到 `/intent-tester/execution?testcase_id=<id>`，由 intent-tester 执行页接管后续运行；New Agents 不直接调用执行 API。
- 2026-06-19: 前端已新增资产质量问题只读展示，测试资产弹层会显示 `assetIssues` 数量、问题消息、关联用例和测试点。
- 2026-06-19: 测试资产弹层已新增资产问题 triage 交互，问题默认 `待处理`，可标记为 `已确认` 或 `忽略`，并实时更新待处理计数；后续持久化切片已升级为服务端状态。
- 2026-06-19: 资产问题状态已补充服务端持久化，实体化 `assetIssues` 现在包含 `id/status`，后端新增 `PATCH /api/agent/test-assets/{collectionId}/issues/{issueId}` 支持 `pending/confirmed/ignored` 状态更新；前端测试资产弹层会通过该接口更新状态并保留服务端返回结果。
- 2026-06-19: 前端已新增风险矩阵只读展示，测试资产弹层会显示 `riskMatrix` 中的风险、关联用例、测试点、优先级和覆盖状态；当前不新增独立风险库或风险生命周期编辑。
- 2026-06-19: 前端已新增测试点覆盖明细只读展示，测试资产弹层会显示 `testPoints` 中的测试点、覆盖状态、优先级、关联风险和覆盖用例；当前不新增独立测试点库或测试点编辑。
- 2026-06-19: 测试资产弹层已新增批量优先级编辑，可将当前集合全部测试用例按 P0/P1/P2 批量更新；实现复用现有单条用例 PATCH 并保留用例版本追加机制，不新增后端批量 endpoint。
- 2026-06-19: 已新增 Lisa 测试资产中心基础页，Header 测试资产弹层可进入 `/test-assets/{collectionId}`；资产中心通过 `GET /api/agent/test-assets/{collectionId}` 读取实体化集合，展示覆盖概览、用例、资产问题、风险矩阵和测试点覆盖，并支持选择部分用例后批量更新优先级。
- 2026-06-19: Lisa 测试资产中心已升级为操作工作台，支持按关键词搜索用例、按 P0/P1/P2 过滤、编辑单条用例完整字段，并可在资产中心内确认或忽略资产问题；实现继续复用现有单条用例 PATCH 和资产问题状态 PATCH。
- 2026-06-19: Lisa 测试资产中心已新增测试点独立校准闭环，后端 `PATCH /api/agent/test-assets/{collectionId}/test-points/{testPoint}` 可保存测试点优先级、关联风险、覆盖状态和覆盖用例，并在保存后重建风险矩阵；前端资产中心可编辑测试点并重新读取完整集合，使覆盖概览、测试点明细和风险矩阵同步刷新。
- 2026-06-19: Lisa 测试资产中心已新增风险生命周期管理，后端 `PATCH /api/agent/test-assets/{collectionId}/risks/{risk}` 可保存风险处置状态、责任人和备注；测试点校准或资产刷新重建风险矩阵时会按同名风险保留 lifecycle，前端资产中心可编辑风险并即时展示最新处置信息。
- 2026-06-19: Lisa 测试资产中心已新增列表管理能力，测试用例列表支持搜索、优先级过滤、排序字段、排序方向、页大小和分页；这些视图状态会写入 URL query，刷新或分享链接后可恢复同一资产视图，且“选择全部”只作用于当前页可见用例。
- 2026-06-19: Lisa 测试资产中心已新增稳定风险库管理能力，风险矩阵现在暴露 collection 内稳定风险 ID 和手工风险标记；后端重建风险矩阵改为 upsert，保留同名风险的 ID、处置状态、责任人和备注；资产中心支持新增手工风险、按 ID 重命名风险并同步当前测试点 / 当前用例版本、删除无关联风险，删除有关联风险会显式失败。
- 2026-06-19: Lisa 测试资产中心已新增 intent-tester 执行接力与状态追踪能力，用例卡片可展示匹配草稿、单条导入 intent-tester、创建 intent-tester 执行记录、刷新最近执行状态，并保留 `/intent-tester/execution?testcase_id=<id>` 跳转，由 intent-tester 执行页和本地 MidScene proxy 接管真实浏览器执行。
- 2026-06-19: Lisa 测试资产中心已新增 intent-tester 映射持久化，后端通过 collection/source case 唯一映射保存 intent-tester testcase ID、名称和最近 execution 摘要；资产集合详情会返回 `intentTesterMappings`，资产中心刷新后可恢复“已导入 #id”和最近执行状态；重新 materialize 时保留仍存在源用例的映射并清理已消失源用例的映射。
- 2026-06-19: Lisa 测试资产中心已新增 intent-tester 执行结果快照承接，前端可从 `/intent-tester/api/executions/{executionId}` 读取步骤详情，后端将步骤总数、通过 / 失败数、失败步骤、错误信息和截图路径压缩保存到 source case mapping；资产中心刷新后可恢复执行结果摘要、失败步骤和截图数量。
- 2026-06-19: 当前仍未实现代理可用时的真实自动浏览器执行、执行结果转 New Agents 测试资产版本状态 / 报告策略；后续 CGA 应继续按跨系统“自动执行-资产版本承接”能力包推进，不拆成单 endpoint 或单按钮微切片。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`，70 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterExecutionService.test.ts src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx src/components/__tests__/Header.test.tsx`，65 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`，68 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`，55 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterExecutionService.test.ts src/services/__tests__/intentTesterImportService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`，22 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`，62 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`，28 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx`，11 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`，52 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`，17 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`，23 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`，47 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`，14 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx src/services/__tests__/intentTesterImportService.test.ts src/services/__tests__/testAssetService.test.ts`，28 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx src/pages/__tests__/TestAssetsPage.test.tsx src/services/__tests__/testAssetService.test.ts`，31 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx src/services/__tests__/testAssetService.test.ts src/components/__tests__/Header.test.tsx`，34 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx src/services/__tests__/intentTesterImportService.test.ts src/services/__tests__/testAssetService.test.ts`，20 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -q`，8 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py::test_agent_run_test_assets_materialize_endpoint_persists_collection tests/test_agent_endpoint.py::test_agent_test_assets_case_update_endpoint_creates_new_version -q`，2 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`，19 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`，38 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/components/__tests__/Header.test.tsx`，23 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py tests/test_run_persistence.py -q`，44 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，254 passed / 1 skipped。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/components/__tests__/Header.test.tsx`，11 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/components/__tests__/Header.test.tsx src/pages/__tests__/Workspace.test.tsx src/__tests__/store.test.ts`，47 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterImportService.test.ts src/services/__tests__/testAssetService.test.ts src/components/__tests__/Header.test.tsx`，16 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterImportService.test.ts src/services/__tests__/testAssetService.test.ts src/components/__tests__/Header.test.tsx src/pages/__tests__/Workspace.test.tsx src/__tests__/store.test.ts`，52 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。

### 8. Alex 到 Lisa 的跨智能体接力

**目标**：形成从价值发现 / PRD / 用户故事到需求评审 / 测试设计的连续流程。

**待办**：

- 先以 workflow 配置表达接力，不新增 agent-specific runtime。
- 明确 Alex 产物如何作为 Lisa 前序上下文。
- 用 E2E 和 judge 验证跨角色专业连续性。

**进展记录**：

- 2026-06-19: 已完成 Alex 到 Lisa 接力第一片，`workflow_manifest.json` 顶层 `handoffs` 声明 `VALUE_DISCOVERY/BLUEPRINT` 可接力到 Lisa `TEST_DESIGN/CLARIFY` 和 `REQ_REVIEW/REVIEW`；`workflow_handoffs.py` 基于 persisted run snapshot 生成只读 handoff context，`GET /api/agent/runs/{runId}/handoffs` 返回候选目标和可作为 Lisa 首轮输入的 prompt。
- 2026-06-19: 该第一片当时尚未自动创建目标 Lisa run，也未包含前端 handoff UI、跨角色 E2E 或 LLM judge 专项验证；后续切片已补齐这些能力。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_workflow_contract_sync.py tests/test_workflow_handoffs.py tests/test_agent_endpoint.py::test_agent_run_handoffs_endpoint_exports_configured_targets -q`，8 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，241 passed / 1 skipped。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts`，12 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 2026-06-19: 前端已新增 handoff 数据层第一片，`fetchWorkflowHandoffs(runId)` 可从 persisted Alex run 拉取候选接力并显式拒绝异常协议；workspace store 新增 `applyWorkflowHandoff()`，可切到目标 Lisa workflow/stage、注入 handoff prompt 作为首轮上下文，并清空旧 `currentRunId`，继续复用共享 Agent Runtime。
- 2026-06-19: 该数据层切片当时尚未包含 handoff UI 入口、自动创建目标 Lisa run、跨角色 E2E 或 LLM judge 专项验证；后续切片已补齐这些能力。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts src/services/__tests__/workflowHandoffService.test.ts`，29 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 2026-06-19: 已新增 ChatPane handoff UI 入口：当前 run 存在候选接力时，左侧对话区展示“跨智能体接力”操作条；点击候选后会应用 handoff prompt、切换到目标 Lisa workflow/stage、清空源 runId，并同步导航到目标 workspace URL，避免被旧路由切回源 workflow。
- 2026-06-19: 该 UI 切片当时尚未包含自动创建目标 Lisa run、跨角色 E2E 或 LLM judge 专项验证；后续切片已补齐这些能力。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ChatPane.test.tsx`，19 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx`，48 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 2026-06-19: 已补充 Alex 到 Lisa 接力浏览器 E2E，mock Agent Runtime 现在会发出 `run_started.runId`，并模拟 `/api/agent/runs/{runId}/handoffs`；测试覆盖 Alex 价值发现完成后显示 handoff 操作、点击进入 Lisa 测试设计 URL，并保留 Alex 蓝图作为 Lisa 首轮上下文。
- 2026-06-19: E2E 暴露并修复了一个路由同步竞态：handoff 刚写入 store 后，Workspace route effect 可能用旧 workflow 闭包再次 `setWorkflow()` 清空接力上下文；现在 effect 会读取 Zustand 当前即时状态再决定是否重置。
- 2026-06-19: 该 E2E 切片当时尚未包含自动创建目标 Lisa run 或 LLM judge 专项验证；后续切片已补齐这些能力。
- 验证: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py::test_alex_value_discovery_can_handoff_to_lisa_test_design -q`，1 passed。
- 验证: `NEW_AGENTS_E2E_LLM_JUDGE=0 python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py -q`，3 passed / 2 skipped。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx src/pages/__tests__/Workspace.test.tsx`，53 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 2026-06-19: 已补充 handoff 自动创建目标 run，`POST /api/agent/runs/{runId}/handoffs/{handoffId}/start` 会基于 manifest 候选创建目标 Lisa run，并把 handoff prompt 作为目标 run 的第一条用户上下文保存，目标 run 可继续复用 snapshot 恢复和 Agent Runtime。
- 2026-06-19: 前端 handoff 点击流程已改为先调用 `startWorkflowHandoff()`，再带着 `targetRunId` 切换 store 并导航到 `/workspace/:agent/:workflow?runId=<targetRunId>`，不再把接力停留在纯本地上下文。
- 2026-06-19: 自动创建目标 run 后，真实 LLM judge 仍由显式环境变量控制；可选专项验证入口已在后续切片补齐。
- 2026-06-19: Alex -> Lisa handoff 已补充可选 LLM judge 专项验证入口，`test_alex_to_lisa_handoff_passes_optional_llm_judge` 在 `NEW_AGENTS_E2E_LLM_JUDGE=1` 时完成 Alex run -> handoff -> Lisa run，并调用 `assert_llm_judges_handoff_quality` 验证跨角色交接质量；默认确定性套件仍不依赖模型。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_workflow_handoffs.py tests/test_agent_endpoint.py::test_agent_run_handoff_start_endpoint_creates_target_run -q`，6 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts`，51 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_workflow_contract_sync.py tests/test_workflow_handoffs.py tests/test_agent_endpoint.py tests/test_run_persistence.py -q`，46 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts src/pages/__tests__/Workspace.test.tsx`，58 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，257 passed / 1 skipped。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。
- 2026-06-19: 已补充跨智能体 handoff LLM judge 专项提示词，`build_handoff_judge_prompt()` 会同时纳入 Alex 源会话/源产物和 Lisa 目标会话/目标产物，并以源产物继承、角色专业性转换、上下文完整性、追溯连续性、风险延续、执行落地和体验连续性作为评分维度。
- 2026-06-19: 已新增 `assert_llm_judges_handoff_quality()` 和可选真实 judge 用例 `test_alex_to_lisa_handoff_passes_optional_llm_judge`；默认仍由 `NEW_AGENTS_E2E_LLM_JUDGE=1` 控制，未开启时跳过，避免本地/CI 无模型配置时误失败。
- 2026-06-19: E2E mock 已同步 handoff `/start` 和目标 run snapshot，浏览器用例现在验证 handoff 后 URL 带目标 `runId`，覆盖自动创建目标 run 后的恢复路径。
- 验证: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py -q`，7 passed。
- 验证: `NEW_AGENTS_E2E_LLM_JUDGE=0 python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py::test_alex_value_discovery_can_handoff_to_lisa_test_design -q`，1 passed。
- 验证: `NEW_AGENTS_E2E_LLM_JUDGE=0 python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py -q`，3 passed / 3 skipped。
- 验证: `cd tools/new-agents/backend && python3 -m pytest -q`，257 passed / 1 skipped。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts src/pages/__tests__/Workspace.test.tsx`，58 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。

### 9. 规则与架构文档持续校准机制

**目标**：让 `AGENTS.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、`docs/DESIGN_PRINCIPLES.md`、`docs/component-inventory.md` 等规则和架构文档持续反映当前代码，而不是长期滞后于实现。

**待办**：

- 基于当前代码、测试、Docker 配置、New Agents 运行时和工作流配置，做一次批量文档校准审计。
- 更新已经过期的架构、API、测试、组件和 Agent 工作规则描述，特别是 New Agents typed Agent Runtime、共享工作流基础设施、LLM judge、`docs/todos/` 和 goal mode 读取规则。
- 建立目标模式文档同步检查清单：当改动影响架构、API、测试门禁、工作流契约、Agent 规则、部署方式或长期 todo 时，必须判断并更新对应文档。
- 在 `docs/strategy/goal-mode-playbook.md` 中强化文档校准原则：目标模式每轮收尾不仅更新 spec/plan，也要更新稳定事实源；发现过期文档时应写入 todo 或直接修正。
- 为批量校准保留明确证据：列出校准过的文件、对应代码事实、未校准原因和后续候选。

**验收证据**：

- 完成一次当前代码状态驱动的文档批量校准。
- 目标模式 playbook 明确要求在相关变更后同步稳定规则/架构文档。
- 后续目标模式可以从 `docs/todos/` 或 playbook 中发现并持续消化文档过期问题。

**进展记录**：

- 2026-06-19: 已完成 New Agents 稳定文档首轮校准，覆盖 `AGENTS.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md` 和 `docs/component-inventory.md`，同步 typed Agent Runtime、共享 `workflow_manifest.json`、artifact/Mermaid contract、LLM judge trace/verdict 和 ChatPane Markdown 可读性职责。
- 2026-06-19: 本轮未做全仓自动生成文档重扫，也未改 `docs/index.md` 的 BMAD 自动生成内容；后续若运行文档生成器，应保留本轮稳定事实。

### 10. 左侧对话 Markdown 可读性恢复

**目标**：让左侧对话在 assistant 回复变长、内容更丰富时，仍保持基础 Markdown 可读性，而不是退化成缺少层级和格式的纯文本。

**背景**：

- 2026-06-19 用户反馈：当前左侧对话内容略长后格式表现较差，看起来没有原来的 Markdown 格式。
- 当前阶段推进体验“凑合还能接受”，暂不把“进入下一阶段体验 / 流程优化”作为活动待办；除非后续出现明确误导、阻断或高频操作成本，再重新纳入 CGA 候选。

**待办**：

- 审计 `ChatPane` 当前 assistant 消息渲染路径，确认 Markdown 格式丢失发生在流式 chunk 拼接、message content 存储、ReactMarkdown 渲染配置还是 CSS 样式层。
- 恢复左侧对话的基础 Markdown 表达能力：段落、列表、粗体、行内代码、代码块、链接和必要的换行层级。
- 保持 chat / artifact 职责分离：左侧对话只展示摘要、方法、关键结论和引导，不重新承载完整 artifact 正文。
- 复用现有 Markdown / Mermaid 渲染工具，不为 ChatPane 新增独立解析管线。
- 补充组件或服务层测试，覆盖较长 assistant Markdown 回复的渲染结构和职责边界。

**验收证据**：

- 左侧 assistant 消息中的 Markdown 列表、强调、代码和段落在 UI 中可读。
- 长回复不破坏 ChatPane 布局、阶段确认卡片和重试按钮。
- 测试能防止完整 artifact Markdown 被重新塞回左侧聊天。

**进展记录**：

- 2026-06-19: 已恢复 `ChatPane` 左侧消息基础 Markdown 样式，覆盖紧凑标题、无序/有序列表、列表项、强调、斜体、链接、引用、分割线、行内代码和代码块；继续复用 `ReactMarkdown`、`remarkGfm`、`preprocessMarkdown` 和 `createMarkdownCodeRenderer`，没有新增独立解析管线。
- 2026-06-19: 已修复共享 `markdownCodeRenderer` 对 ReactMarkdown v10 行内代码缺少 `inline` prop 的兼容问题，语言为空且不含换行的 code 节点会按行内代码渲染；ChatPane 同时解除默认外层 `pre` 包装，避免代码块样式落在内层而外层空壳影响布局。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ChatPane.test.tsx src/components/__tests__/ChatPane.markdown.test.tsx src/components/__tests__/markdownCodeRenderer.test.tsx`，22 passed。

## P2 后续增强

### 11. Artifact 协作体验

- 局部重写。
- 章节锁定。
- 版本 diff。
- 批注。
- 接受 / 拒绝变更。
- Word / PDF / Markdown 多格式导出。

**进展记录**：

- 2026-06-19: 已补充 artifact 历史版本 diff 第一片，历史版本弹层新增“预览 / 差异”切换；差异模式将选中的历史版本与当前产出物做行级对比，用新增/删除/未变更样式辅助审阅版本变化。
- 2026-06-19: 新增 `artifactDiff.ts` 行级 LCS diff 工具，供后续接受/拒绝变更、批注或局部重写复用。
- 2026-06-19: Artifact 历史版本弹层已新增“恢复此版本”，用户可把当前前端工作区产出物恢复到选中的历史版本；恢复前的当前内容会先追加为当前 stage 的本地历史版本，避免误操作后无法回退。
- 2026-06-19: ArtifactPane 下载按钮已改为导出菜单，保留 Markdown 下载，并新增 Word 兼容 `.doc` 导出；Word 导出使用转义后的 HTML 文档承载当前 artifact 文本，不引入新依赖。
- 2026-06-19: ArtifactPane 导出菜单已新增 PDF 下载，前端无新依赖生成最小有效 `%PDF-1.4` 单页文本 PDF，并以 `<workflow>_artifact.pdf` 下载。
- 2026-06-19: 当前恢复动作仍是前端工作区状态更新，未新增服务端 artifact update API；Word 导出是兼容 `.doc` 的文本型 HTML，不是富文本 DOCX；PDF 导出是纯文本最小 PDF，不包含 Markdown 富排版、Mermaid 渲染或分页；仍未实现章节锁定、批注、逐行接受/拒绝变更。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactDiff.test.ts src/components/__tests__/ArtifactPane.test.tsx`，10 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactDiff.test.ts src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/markdownCodeRenderer.test.tsx src/__tests__/store.test.ts src/pages/__tests__/Workspace.test.tsx`，50 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`，10 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/core/__tests__/artifactDiff.test.ts src/components/__tests__/markdownCodeRenderer.test.tsx src/__tests__/store.test.ts src/pages/__tests__/Workspace.test.tsx`，51 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`，11 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/core/__tests__/artifactDiff.test.ts src/components/__tests__/markdownCodeRenderer.test.tsx src/__tests__/store.test.ts src/pages/__tests__/Workspace.test.tsx`，52 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/core/__tests__/artifactDiff.test.ts`，13 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `git diff --check`，passed。

### 12. 运行时可观测性

- 记录 run id、workflow、stage、模型、耗时、错误码、contract retry 次数、token 估算。
- 提供基本统计视图，帮助发现高失败率阶段和低质量输出。

**进展**

- 2026-06-19: 已新增 `agent_run_turn_metrics` 持久化表，并在共享 `/api/agent/runs/stream` typed Agent Runtime 链路记录每轮 turn metric，覆盖 run、workflow、stage、模型、成功/失败状态、错误码、耗时、输入/输出字符数、token 估算和 contract retry 次数占位。
- 2026-06-19: 已新增只读 `GET /api/agent/observability` 基础统计 API，返回整体 totals、按 workflow/stage 聚合的失败率与错误码分布，以及最近 turn 明细，便于先定位高失败率阶段。
- 2026-06-19: 前端已新增只读“运行统计”视图，Header 会调用 `fetchObservabilitySummary({ limit: 20 })` 展示总轮次、成功率、失败轮次、估算 token、按阶段/供应商聚合和最近 turn；API 或协议异常会显示错误状态，不伪造空成功。
- 2026-06-19: `GET /api/agent/observability` 已新增 `workflowId` / `stageId` 筛选，Header 运行统计弹层可选择工作流和阶段后重新加载统计，便于定位单个 workflow/stage 的失败率、供应商分布和最近 turn。
- 2026-06-19: Header 运行统计弹层已新增 `自动刷新` 开关，开启后每 30 秒复用当前 workflow/stage 筛选重新读取统计，关闭弹层时清理定时器，避免后台继续轮询。
- 2026-06-19: Header 运行统计弹层已新增轻量 `运行告警` 区块，基于现有 totals、stage 和 provider 聚合派生失败运行、低成功率阶段和低成功率供应商提示，不改变后端 observability API。
- 2026-06-19: Agent Runtime metric 已开始采集真实结构化/契约重试耗尽次数；当 PydanticAI schema error 暴露 `Exceeded maximum output retries (N)` 时，`stream_services.py` 会解析 `N` 并写入 `agent_run_turn_metrics.contract_retry_count`。
- 2026-06-19: raw OpenAI-compatible streaming 已开始采集 provider 返回的真实 `usage.total_tokens`；`llm_client.py` 在 usage 回调存在时请求 `stream_options.include_usage`，`PydanticAgentRuntime.last_token_usage` 保存该值，`stream_services.py` 记录 metric 时优先使用真实 token，缺失时回退原字符估算。
- 2026-06-19: 当前未拆分 prompt/completion token 字段，也未为不返回 streaming usage 的 provider 强行推断真实 token；本轮先完成基础可见性闭环。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py::test_stream_agent_run_events_records_turn_through_persistence_adapter tests/test_stream_services.py::test_stream_agent_run_events_records_error_turn_metric -q`，2 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary -q`，1 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py tests/test_agent_endpoint.py tests/test_run_persistence.py -q`，53 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx`，13 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary tests/test_agent_endpoint.py::test_agent_observability_endpoint_filters_by_workflow_and_stage tests/test_agent_endpoint.py::test_agent_observability_endpoint_rejects_stage_without_workflow -q`，3 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx`，20 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx src/pages/__tests__/Workspace.test.tsx src/__tests__/store.test.ts`，49 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary -q`，1 passed。
- 验证: `git diff --check`，passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`，17 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx`，21 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/observabilityAlerts.test.ts`，2 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`，18 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/observabilityAlerts.test.ts src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx`，24 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py::test_stream_agent_run_events_records_schema_retry_count_from_runtime_error tests/test_stream_services.py::test_stream_agent_run_events_records_turn_through_persistence_adapter tests/test_stream_services.py::test_stream_agent_run_events_records_error_turn_metric -q`，3 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary -q`，17 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_llm_client.py tests/test_agent_runtime.py::test_raw_streaming_runtime_records_stream_usage tests/test_stream_services.py::test_stream_agent_run_events_records_real_token_usage_when_runtime_exposes_it tests/test_stream_services.py::test_stream_agent_run_events_records_turn_through_persistence_adapter -q`，7 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_llm_client.py tests/test_agent_runtime.py tests/test_stream_services.py tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary -q`，40 passed。

### 13. 模型配置与供应商治理

- 默认 LLM 配置管理 UI。
- 密钥轮换。
- 模型可用性检测。
- 供应商错误归因。
- 按环境启用不同模型。

**进展**

- 2026-06-19: 已完成供应商错误归因第一片，Agent Runtime turn metric 现在会从默认 LLM `base_url` 推断 provider 并持久化；`GET /api/agent/observability` 已新增 `byProvider` 聚合和 recent turn provider 字段，用于区分阶段契约失败与供应商/模型侧失败集中在哪个 provider。
- 2026-06-19: 已新增默认 LLM 配置管理 UI 与 `POST /api/config`，支持创建/更新默认 `baseUrl`、`model`、`description`，并通过“新 API Key”输入完成密钥轮换；后端响应和前端状态均不回显已有 API Key，已有配置留空密钥时保留当前密钥。
- 2026-06-19: 已新增模型可用性检测，`POST /api/config/check` 会使用当前默认配置做最小模型调用，返回 `ok`、模型、Base URL 和诊断消息；设置弹层提供“检测连接”入口，供应商失败以业务态展示，不回显 API Key。
- 2026-06-19: 已补充按环境选择默认模型配置 key，默认仍为 `default`，部署环境可通过 `NEW_AGENTS_DEFAULT_LLM_CONFIG_KEY` 指向不同 `llm_config.config_key`；`GET /api/config`、`POST /api/config`、`POST /api/config/check` 和 Agent Runtime guard 都复用该选择，不新增运行时分支。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py::test_stream_agent_run_events_records_turn_through_persistence_adapter tests/test_stream_services.py::test_stream_agent_run_events_records_error_turn_metric -q`，2 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary -q`，1 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py tests/test_agent_endpoint.py tests/test_run_persistence.py -q`，53 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_api.py::test_post_config_creates_default_config_without_exposing_api_key tests/test_api.py::test_post_config_updates_default_config_and_preserves_key_when_omitted tests/test_api.py::test_post_config_requires_api_key_when_creating_default_config -q`，3 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_api.py tests/test_request_schemas.py tests/test_routes_blueprint.py tests/test_route_guards.py -q`，39 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/SettingsModal.test.tsx src/pages/__tests__/Workspace.test.tsx`，15 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_api.py::test_post_config_check_requires_default_config tests/test_api.py::test_post_config_check_returns_model_availability_result tests/test_config_service.py -q`，4 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/SettingsModal.test.tsx`，9 passed。
- 验证: `cd tools/new-agents/backend && python3 -m pytest tests/test_api.py::test_get_config_uses_environment_selected_config_key tests/test_api.py::test_post_config_updates_environment_selected_config_key tests/test_api.py::test_init_db_seeds_environment_selected_config_key -q`，3 passed。
