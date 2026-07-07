# New Agents DELIVERY Partial Artifact Streaming 设计

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`、`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`。
- 当前工作区：存在大量与本轮无关的删除、文档和生成物变更；本轮只允许写入本 spec、对应 plan、纵切 todo、`artifact_data_renderers.py` 以及 New Agents backend 聚焦测试。

已确认目标来源：

- 来源：`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`。
- 本轮承接：第 2 轮，`TEST_DESIGN/DELIVERY`，Lisa 测试设计交付文档真实 partial streaming 闭环。
- 上一轮状态：第 1 轮 `TEST_DESIGN/CASES` 已完成确定性验证，并记录默认 LLM judge 质量失败不归因于 CASES partial streaming。

改道条件检查：

- 新 P0/P1 或用户新目标：用户新增了 LLM judge 80 分门禁，已写入 playbook；它影响本轮收尾口径，不改变 DELIVERY partial streaming 边界。
- 测试失败或生产阻断：当前已知默认全量命令中的可选 Lisa LLM judge 评分 64，属于最终产物质量风险；本轮若引用 LLM judge，低于 80 必须分析差距并修复或记录外部阻塞。
- 架构、文档或代码事实冲突：无。`AGENTS.md` 要求复用共享 runtime/typed SSE/store；本轮只补共享 artifact_data partial renderer dispatch。
- 工作区冲突：有大量无关脏文件；本轮不回滚、不格式化、不 stage 无关文件。
- 是否需要拆分或合并：否。第 2 轮 todo 明确不得再拆薄，且现有 DELIVERY schema/final renderer 已稳定。

边界复核：

- 本轮纳入：`TEST_DESIGN/DELIVERY` 在 raw JSON streaming 期间，基于已闭合 `artifact_data` 顶层字段逐步生成正式《测试设计文档》Markdown delta。
- 本轮排除：`REQ_REVIEW`、`INCIDENT_REVIEW`、`IDEA_BRAINSTORM`、`VALUE_DISCOVERY` partial streaming；Lisa 最终产物 LLM judge 质量修复只在本轮触发到 DELIVERY 相关问题时处理。
- 厚度门禁：入口是 Lisa DELIVERY 阶段；用户动作是请求最终交付文档；系统处理是共享 Agent Runtime 解析 streaming JSON 并调用 partial renderer；可见结果是右侧 ArtifactPane 逐步出现执行摘要、需求摘要、策略摘要等正式章节；承接是最终 `agent_turn` 仍通过完整 delivery contract 和 coverage-map contract；失败反馈沿用当前 raw JSON retry/contract failure 路径；证据为 partial renderer、runtime streaming、contract、前端消费和必要回归。

结论：继续承接第 2 轮，不恢复完整候选排序型 CGA。

## Brainstorming 自问自答

### Explore Project Context

`TEST_DESIGN/DELIVERY` 已经完成结构化 `artifact_data` 迁移。后端有 `DeliveryArtifactData`、完整 `render_test_design_delivery_markdown()`、`coverage-map` 可视化、contract 测试和 raw JSON final render 测试。缺口不是最终渲染，而是 `render_partial_agent_turn_from_artifact_data()` 没有 DELIVERY 分支，模型 streaming 输出 `delivery_metrics`、`executive_summary` 等字段时，右侧 artifact 仍等到 final JSON 闭合后才一次性出现。

### Visual Companion Decision

本轮不涉及 UI 视觉设计。前端已有 typed SSE 和 ArtifactPane 增量消费测试，本轮只需让后端提前产生正式 artifact delta。

### Clarifying Questions

- 用户是谁？使用 Lisa 完成测试设计交付的测试负责人、产品负责人或评审参与者。
- 用户要完成什么？在 DELIVERY 阶段生成可评审、可签署的测试设计交付文档。
- 成功状态是什么？右侧 ArtifactPane 不再空等最终 JSON，而是随着结构化字段闭合逐步出现正式章节。
- 输入来自哪里？raw JSON streaming 中的 `artifact_data` 顶层字段，字段顺序由 DELIVERY structured output instruction 和现有 schema 决定。
- 约束是什么？不得新增 workflow 专属 runtime、API、store 或 UI 渲染管线；不得用 fake progress 或 synthetic reveal 冒充真实 partial artifact streaming。
- 失败路径是什么？如果 `document_info` 或首个业务字段无效，不输出 partial artifact；如果后续字段无效，保留已验证章节，最终完整校验仍必须失败或重试。
- 下游如何承接？最终 DELIVERY artifact 仍包含 `coverage-map`、开放风险、验收清单、签署确认、变更记录和附录文档信息。
- 不做什么？不改 DELIVERY schema；不改变最终 Markdown 章节顺序；不修非 DELIVERY 的 LLM judge 质量缺口。

### Approaches

方案 A：为 DELIVERY 增加独立 partial renderer，复用现有 section renderer 和 `_build_partial_add_after_patch()`。

- 优点：最小改动，延续 CLARIFY/STRATEGY/CASES 模式；不会改变最终 renderer 和 contract。
- 缺点：继续在大文件中增加一个 stage-specific helper。
- 结论：采用。当前项目已采用这种共享 dispatch + stage data renderer 模式，符合局部一致性。

方案 B：抽象一个通用 schema-driven partial renderer。

- 优点：后续 14 个阶段可能减少重复代码。
- 缺点：需要把每个字段和 section renderer 显式映射，当前阶段会引入额外抽象风险；容易在尚未完成其他 workflow 前过度设计。
- 结论：暂不采用，可在第 7 轮全收口时评估。

方案 C：只在前端对 final artifact 做 reveal。

- 优点：改动少。
- 缺点：不是真实 partial artifact streaming，违背 todo 非目标。
- 结论：拒绝。

### Presented Design

后端在 `render_partial_agent_turn_from_artifact_data()` 增加 `("TEST_DESIGN", "DELIVERY")` 分支，字段顺序为：

1. `executive_summary`
2. `requirement_summary`
3. `strategy_summary_items`
4. `case_summary_items`
5. `coverage_map`
6. `open_risks`
7. `acceptance_checklist`
8. `signoffs`
9. `change_log`
10. `document_info`

partial renderer `render_partial_test_design_delivery_markdown(data)` 必须先校验 `document_info` 存在且合法，但首个可见业务章节从 `executive_summary` 开始，和最终 renderer 一样把 `document_info` 放在最后的附录。这样既能避免文档信息抢占首屏，也保持 final artifact 的章节顺序和现有 contract。

在 runtime 测试中，将 DELIVERY JSON 切成多个 chunk：第一个 chunk 包含 `document_info` 和 `executive_summary`，第二个 chunk 增加 `requirement_summary`，最后输出完整 JSON。断言 final `AgentTurnOutput` 前已经出现多个 `AgentTurnDeltaOutput` artifact markdown，并且 Markdown 章节递增。最终 output 仍以 `# 测试设计文档` 开头并包含 `coverage-map`。

前端消费链路不改代码。本轮复用已有 `llm.ts`、`chatService`、`ArtifactPane.incrementalRender` 测试作为回归证据，证明 backend 产生的 artifact delta 会实时写入 artifact content。

## 验收条件

1. Given `TEST_DESIGN/DELIVERY` raw JSON stream 已闭合 `executive_summary`
   When runtime 解析 partial `artifact_data`
   Then final 前产生正式 `# 测试设计文档` artifact delta，并包含 `## 1. 执行摘要`
   Evidence: 新增 backend runtime 测试。

2. Given partial `artifact_data` 已闭合 `requirement_summary`
   When 调用 partial renderer
   Then Markdown 增加 `## 2. 需求分析摘要`，并生成 `add_after` artifact patch
   Evidence: 新增 artifact renderer 测试。

3. Given 完整 DELIVERY `artifact_data`
   When final renderer 执行
   Then artifact 仍包含 `coverage-map` 并通过 `validate_agent_turn()`
   Evidence: 既有 `test_render_delivery_artifact_data_is_deterministic_and_contract_valid` 继续通过。

4. Given 本轮引用 LLM judge 质量门禁
   When judge 分数低于 80
   Then 不声称质量通过，必须记录差距分析、修复动作或环境阻塞
   Evidence: todo 和收尾说明。
