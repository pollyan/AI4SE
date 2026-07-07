# New Agents REQ_REVIEW Partial Artifact Streaming 设计

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`、`tools/new-agents/backend/agent_runtime.py`、`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`。
- 当前工作区：存在大量与本轮无关的删除、文档和生成物变更；本轮只允许写入本 spec、对应 plan、纵切 todo、`artifact_data_renderers.py` 以及 New Agents backend 聚焦测试。

已确认目标来源：

- 来源：`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`。
- 本轮承接：第 3 轮，`REQ_REVIEW/REVIEW` 与 `REQ_REVIEW/REPORT`，需求评审 workflow 真实 partial streaming 闭环。
- 上一轮状态：第 1-2 轮 `TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY` 已完成确定性验证。

改道条件检查：

- 新 P0/P1 或用户新目标：无新的目标变更。playbook 已要求 LLM judge 启用时最低 80 分。
- 测试失败或生产阻断：已知默认启用可选 Lisa LLM judge 时评分 64，属于质量门禁风险；本轮不声称 judge 质量通过，除非实际重跑并达到 80。
- 架构、文档或代码事实冲突：无。REQ_REVIEW 两阶段已经通过 shared raw JSON runtime、artifact_data schema、final renderer 和 contract 测试，缺口是 partial renderer dispatch 仍未覆盖这两个阶段。
- 工作区冲突：有大量无关脏文件；本轮不回滚、不格式化、不 stage 无关文件。
- 是否需要拆分或合并：否。todo 第 3 轮明确把 REVIEW 和 REPORT 作为一个需求评审 workflow 用户故事，二者共享问题清单到评审报告的用户链路。

边界复核：

- 本轮纳入：`REQ_REVIEW/REVIEW` 和 `REQ_REVIEW/REPORT` 在 raw JSON streaming 期间，基于已闭合 `artifact_data` 顶层字段逐步生成正式 Markdown artifact delta。
- 本轮排除：故障复盘、创意脑暴、价值发现 workflow；非 REQ_REVIEW 的 LLM judge 质量修复。
- 厚度门禁：入口是用户发起需求评审或评审报告；动作是 Lisa 输出问题清单 / 评审报告；系统处理是共享 Agent Runtime 解析 streaming JSON 并调用 partial renderer；可见结果是右侧 ArtifactPane 逐步出现评审范围、质量总览、问题统计、评审结论、评审信息、优先级看板等正式章节；承接是最终 `agent_turn` 仍通过完整 REQ_REVIEW contract；失败反馈沿用当前 raw JSON retry 和 contract failure 路径；证据为 partial renderer、runtime streaming、contract 和前端消费回归。

结论：继续承接第 3 轮，不恢复完整候选排序型 CGA。

## Brainstorming 自问自答

### Explore Project Context

`REQ_REVIEW/REVIEW` 和 `REQ_REVIEW/REPORT` 已有结构化输出 instruction、Pydantic schema、final renderer 和 raw JSON final render 测试。现有 final renderer 负责渲染 `score-matrix`、Mermaid flowchart、priority-board 和评审签署内容。缺口是 `render_partial_agent_turn_from_artifact_data()` 只覆盖 `TEST_DESIGN` 四个阶段，REQ_REVIEW 的 artifact delta 仍等完整 JSON 闭合后才出现。

### Visual Companion Decision

本轮不涉及 UI 视觉设计。前端已有 typed SSE 和 ArtifactPane 增量消费回归，本轮重点是后端提前产生正式 artifact delta。

### Clarifying Questions

- 用户是谁？使用 Lisa 对需求进行质量评审的产品、研发、测试和评审负责人。
- 用户要完成什么？先看到需求评审问题清单，再形成可签署的需求评审报告。
- 成功状态是什么？REVIEW 和 REPORT 两阶段右侧 artifact 随结构化字段闭合逐步出现，不再等最终 JSON 才一次性渲染。
- 输入来自哪里？raw JSON streaming 中的 `artifact_data` 顶层字段，字段顺序由 `agent_runtime.py` 中 REQ_REVIEW structured output instruction 定义。
- 约束是什么？不新增 workflow 专属 runtime、endpoint、store 或 UI 渲染管线；不使用 fake progress 或 synthetic reveal。
- 失败路径是什么？首个可见字段无效时不输出 partial；后续字段无效时只保留已验证章节；最终完整校验仍必须失败或重试。
- 下游如何承接？最终 REVIEW 仍能请求进入 REPORT；最终 REPORT 仍包含 priority-board、复审条件、签署确认和变更记录。
- 不做什么？不修改 REQ_REVIEW schema 和 final Markdown contract；不修非本轮引起的 LLM judge 质量缺口。

### Approaches

方案 A：为 REVIEW 和 REPORT 各加一个 partial renderer，复用现有 section renderer 和 `_build_partial_add_after_patch()`。

- 优点：与 TEST_DESIGN 已完成四阶段一致，改动最小，最终 renderer 不变。
- 缺点：大文件中继续增加 stage-specific helper。
- 结论：采用。当前仓库架构已经以共享 dispatch + stage renderer 表达 workflow 差异。

方案 B：把所有 artifact renderer 抽象成 declarative field-to-section table。

- 优点：后续轮次可能减少重复代码。
- 缺点：会影响多个 workflow，容易把第 3 轮扩大成跨工作流重构。
- 结论：暂不采用，留到第 7 轮全阶段收口评估。

方案 C：只改前端显示策略。

- 优点：短期改动少。
- 缺点：不是真实 partial artifact streaming，违背 todo 非目标。
- 结论：拒绝。

## 设计

`REQ_REVIEW/REVIEW` partial renderer 可见字段顺序：

1. `scope_items`
2. `quality_overview`
3. `issue_statistics`
4. `issue_groups`
5. `revision_suggestions`
6. `stage_gate`

`review_info` 必须存在并合法，但只在 `stage_gate` 之后作为 `## 附录：评审信息` 输出，保持 final renderer 顺序。`quality_overview` 会同时产生质量总览和静态质量结构图；`issue_statistics` 会产生问题统计和 `score-matrix`。

`REQ_REVIEW/REPORT` partial renderer 可见字段顺序：

1. `conclusion`
2. `review_info`
3. `issue_statistics`
4. `issue_closures`
5. `review_conditions`
6. `signoffs`
7. `change_log`

REPORT 首屏从 `## 评审结论` 开始，随后出现评审信息、问题统计、优先级看板、问题关闭清单、复审条件、签署确认和变更记录。最终 artifact contract 不变。

## 验收条件

1. Given `REQ_REVIEW/REVIEW` raw JSON stream 已闭合 `scope_items`
   When runtime 解析 partial `artifact_data`
   Then final 前产生正式 `# 需求评审问题清单` artifact delta，并包含 `## 评审范围与不评审范围`
   Evidence: 新增 backend runtime 测试。

2. Given `REQ_REVIEW/REVIEW` partial 数据已闭合 `issue_statistics`
   When 调用 partial renderer
   Then Markdown 增加 `## 问题统计` 和 `score-matrix`，并尽量生成 `add_after` patch
   Evidence: 新增 renderer 测试。

3. Given `REQ_REVIEW/REPORT` raw JSON stream 已闭合 `conclusion`
   When runtime 解析 partial `artifact_data`
   Then final 前产生正式 `# 需求评审报告` artifact delta，并包含 `## 评审结论`
   Evidence: 新增 backend runtime 测试。

4. Given 完整 REQ_REVIEW `artifact_data`
   When final renderer 执行
   Then REVIEW 和 REPORT 仍通过 `validate_agent_turn()`，并保留 `score-matrix` 和 `priority-board`
   Evidence: 既有 contract 测试继续通过。

5. Given 本轮引用 LLM judge 质量门禁
   When judge 分数低于 80
   Then 不声称质量通过，必须记录差距分析、修复动作或环境阻塞
   Evidence: todo 和收尾说明。
