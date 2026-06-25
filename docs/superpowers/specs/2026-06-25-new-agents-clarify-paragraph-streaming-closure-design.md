# New Agents 需求澄清段落级流式收束设计

## Current State Gap Analysis

### 事实源快照

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、`docs/CODING_STANDARDS.md`、`docs/DESIGN_PRINCIPLES.md`、活跃 `docs/todos/*.md`、当前 `git status` 和 New Agents 未提交 diff。
- 当前工作区：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`、`tools/intent-tester/test-results/proxy/junit.xml` 是既有脏文件，本轮不触碰、不 stage。
- 本轮允许写入：`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`、必要的 `tools/new-agents/frontend/src/services/**` 回归测试文件、本 spec、配套 plan 和相关 todo 记录。
- 按需未展开：`docs/plans/tech-debt.md` 等非 New Agents Artifact 主题计划。

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 需求澄清段落级流式收束 | 当前未提交的 `TEST_DESIGN/CLARIFY` partial renderer 与 runtime 测试；`docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md` 的局部变更感知方向 | 用户进入 Lisa 需求澄清阶段并发起生成，后端在 `artifact_data` 顶层字段闭合时渲染正式章节，右侧在 final 前显示已完成章节，最终完整产物仍通过 contract validation | 只补 renderer 会缺少 runtime 证据；只补测试会留下未收束 dirty diff；扩展到全 workflow patch 协议会跨越当前半成品边界 | 后端 raw JSON streaming 测试、前端 service 回归测试、`git diff --check` |
| 产出物去表格化审计 | `docs/todos/2026-06-25-new-agents-artifact-format-over-tabularization-audit.md` | 用户阅读右侧 Artifact，摘要/附件/文档信息使用自然段落或列表，结构化追溯表格保留 | 需要跨 renderer、prompt、导出和浏览器验收，不能混入当前 dirty diff | renderer/prompt/导出测试和浏览器截图 |
| 本轮变更 Diff 标识 | `docs/todos/2026-06-25-new-agents-artifact-change-diff-highlighting.md` | 用户审阅右侧 Artifact 更新时可切换显示新增/删除痕迹，复制和导出仍为干净内容 | 需要 UI 状态、diff 策略、结构化块保护和复制/导出回归一起交付 | `artifactDiff` 与 `ArtifactPane` 测试 |
| 左侧自然聊天可读性 | `docs/todos/2026-06-25-new-agents-natural-chat-readability.md` | 用户读取 assistant 回复时，简单场景自然短段落，复杂场景按需列表和重点突出 | 仅 prompt 或仅 UI 都不能形成完整可读性闭环 | prompt 测试、`ChatPane` Markdown 渲染测试 |
| 可视化诊断重复提示抑制 | `docs/todos/2026-06-25-new-agents-artifact-visual-diagnostic-duplicate-notice.md` | 右侧已保留可视化诊断入口时，左侧不再重复显示大卡片 | 可独立交付，但与当前 partial streaming dirty diff 无依赖 | `ChatPane` / `ArtifactPane` 组件测试 |

### 排序结论

1. 本轮选择“需求澄清段落级流式收束”。它已经有未提交实现痕迹，若继续其他待办会把半成品和新能力混在一个提交中，破坏目标模式的用户故事边界。
2. 去表格化审计、本轮 diff 标识、自然聊天可读性、重复诊断提示和完整 patch/changed_sections 协议保留为后续候选。

### 切片准入判断

- 用户功能包边界：Lisa `TEST_DESIGN/CLARIFY` 的正式 Artifact 段落级流式显示闭环；包含后端 partial renderer、runtime delta 证据和前端阶段续写 prompt 回归；排除全 workflow patch 协议和全量去表格化审计。
- 用户可感知动作链：进入 Lisa 需求澄清 -> 发起生成 -> 系统收到结构化 `artifact_data` 的已闭合顶层字段 -> 右侧显示已完成正式章节 -> final 到达后完整文档收敛。
- 相邻缺口合并：把当前未提交的 `chatService` 阶段续写稳定提示词回归纳入验证，避免阶段确认后新阶段生成行为被本轮收束破坏。
- 过薄风险检查：本轮不是单 helper、单字段或单测试；它收束右侧生成主路径中的一个可见阶段能力，并消除当前 dirty diff 的工程信任风险。
- 能力增量句：完成后，用户现在可以在 Lisa 需求澄清阶段看到右侧需求分析文档按正式章节逐段生成，而不是等最终输出一次性出现。

### 切片厚度门禁

- 入口：`/new-agents/workspace/lisa/test-design` 的需求澄清阶段。
- 动作：用户发送需求材料并触发 Lisa 生成需求分析文档。
- 处理：共享 `/api/agent/runs/stream` raw JSON streaming 路径提取已完成 `artifact_data` 顶层字段，后端 deterministic renderer 渲染已完成正式章节。
- 可见结果：右侧 Artifact 在 final 前出现 `# 需求分析文档` 和已完成章节。
- 状态承接：最终 `agent_turn` 仍写入完整 artifact 内容；复制、导出、历史版本和后续 prompt 继续使用干净最终 Markdown。
- 失败反馈：半截字段、半截数组或不合法局部数据不生成假进度页；保留此前已验证章节或等待最终完整输出。
- 证据：后端 runtime 测试覆盖局部字段递增，前端 service 测试覆盖阶段续写 prompt，`git diff --check` 确认补丁干净。
- 结论：通过。

## Superpowers 自问自答

### Explore Project Context

New Agents 的主链路必须复用共享 Agent Runtime、typed SSE、Zustand store 和 ArtifactPane。`docs/ARCHITECTURE.md` 与 `docs/api-contracts.md` 明确 `/api/agent/runs/stream` 返回 typed SSE，`artifact_update.type="replace"` 承载正式 Markdown，不能用调试占位页冒充右侧产物。

现有后端已经有 `extract_completed_json_object_members(...)` 和 `render_partial_agent_turn_from_artifact_data(...)`。当前未提交 diff 把 partial renderer 从 `TEST_DESIGN/STRATEGY` 扩展到 `TEST_DESIGN/CLARIFY`，但还需要确认测试边界、前端回归和文档记录都与目标模式一致。

### Visual Companion Decision

本轮是运行时和契约收束，不涉及新视觉布局选择。右侧逐段显示已有 ArtifactPane 承载，不需要浏览器 mockup 或视觉 companion。

### Clarifying Questions

- 用户是谁：使用 Lisa 测试设计 workflow 的用户。
- 用户要完成什么：在需求澄清阶段生成需求分析文档，并在生成过程中确认右侧产物正在按正式章节形成。
- 成功状态是什么：final 前至少出现两帧递增的正式需求分析 Markdown；最终输出仍是完整文档。
- 输入来源是什么：模型 raw JSON stream 中 `artifact_data` 的已闭合顶层字段，例如 `requirement_facts`、`system_boundaries`。
- 失败路径是什么：局部字段未闭合或局部数据不合法时不生成半截 Markdown、不生成调试占位；等待更多字段或最终完整对象。
- 不做什么：不新增 workflow 专属 SSE/API path、store 或 UI renderer；不把完整 patch/changed_sections 协议塞进本轮。

### Approaches

1. 推荐：收束当前 partial renderer 扩展，让 `TEST_DESIGN/CLARIFY` 复用已有 completed-member extractor 和 deterministic section renderer。优点是最小化架构风险，直接保护当前 dirty diff；缺点是只覆盖需求澄清阶段，不等于完整 patch 协议。
2. 不选：立刻实现 `artifact_patch` / `changed_sections` 协议。它更接近长期增量渲染目标，但会跨后端 schema、前端 store、ArtifactPane、协作功能和导出路径，风险高且会吞掉当前半成品边界。
3. 不选：只用前端 synthetic reveal 模拟逐段出现。它无法证明真实模型 streaming 期间已有正式 artifact delta，且会掩盖后端结构化输出的局部可渲染能力缺口。

### Presented Design

后端保持现有共享 partial JSON member extractor：只提取已经形成完整 JSON value 的 `artifact_data` 顶层字段，不猜测半截字符串、半截数组或半截对象。

`artifact_data_renderers.py` 为 `TEST_DESIGN/CLARIFY` 增加局部 renderer。它要求 `document_info` 和 `requirement_facts` 至少可验证，随后按现有完整 renderer 的章节顺序追加 `system_boundaries`、`business_rules`、`flow_links`、`clarification_questions`、`quality_requirements`、`downstream_inputs` 和 `stage_gate`。每段局部数据先通过对应 Pydantic 子模型校验；失败时返回已验证章节，而不是抛出到 SSE 层或伪造成功。

前端不新增渲染路径。本轮只保留并验证阶段确认后的内部续写使用稳定提示词 `请继续生成当前阶段产出物`，用户确认文本只作为历史消息保存，避免把“已确认进入策略制定”误当作新阶段产物生成指令。

## 验收条件

1. Given `TEST_DESIGN/CLARIFY` raw JSON stream 已输出完整 `requirement_facts` 但 `artifact_data` 对象尚未闭合，When 后端处理当前累计文本，Then final 前发出包含 `# 需求分析文档` 和 `## 1. 需求事实清单` 的 `agent_delta.artifact_update.replace`，且不包含 `## 2. 被测系统与边界`。
2. Given 后续 `system_boundaries` 完整闭合，When 后端继续处理流，Then 下一帧 artifact Markdown 递增包含 `## 2. 被测系统与边界`，且仍不包含未闭合的 `## 3. 业务规则与数据状态`。
3. Given 最终完整 `agent_turn` 到达，When 前端收敛输出，Then 右侧 artifact 包含后续完整章节，并继续由完整 renderer / contract validation 保护。
4. Given 用户确认进入下一阶段，When `handleConfirmStageTransition()` 触发内部续写，Then chat history 保留用户确认消息，而发送给模型的续写 prompt 是稳定的 `请继续生成当前阶段产出物`。
5. Given 本轮完成，When stage / commit，Then 不包含既有 intent-tester zip 和 junit 脏文件。

## 非目标

- 不实现全 workflow `artifact_patch` / `changed_sections` 协议。
- 不处理去表格化审计、diff 标识、自然聊天可读性或重复诊断提示。
- 不调用真实外部模型作为默认门禁。
- 不新增 Lisa 专属 runtime、transport、state store、SSE/API path 或 bespoke renderer pipeline。
