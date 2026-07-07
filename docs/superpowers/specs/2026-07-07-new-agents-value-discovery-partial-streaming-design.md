# New Agents 第 6 轮 VALUE_DISCOVERY partial artifact streaming 设计

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-subagents.md`、`docs/index.md`、`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`、`tools/new-agents/workflow_manifest.json`、`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`。
- 当前工作区：存在大量与本轮无关的删除和修改。本轮只写入 VALUE partial streaming 相关 spec / plan / todo、`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`，以及已经按用户要求更新的 `docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-subagents.md`。

已确认目标来源：

- 来源：`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`。
- 本轮承接：第 6 轮 `VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`VALUE_DISCOVERY/BLUEPRINT`。
- 上一轮状态：第 1-5 轮已完成确定性验证；Lisa judge 64 分质量门已修复，相关 pytest 断言现在强制 `score >= 80` 并通过。

改道条件检查：

- 新 P0/P1 或用户新目标：用户指出 playbook 规则需要补强以避免再次遗漏 judge 低分和子智能体审查。该反馈已经先处理，主 playbook、CGA 模板和子智能体附录已补充运行中反馈中断、judge 差距分析和默认子智能体触发规则。
- 未关闭质量门或用户明确反馈：没有新的未关闭质量门。Lisa 低分已关闭；本轮未启用新的 VALUE LLM judge，若后续引用 judge，默认通过线仍为 80 分。
- LLM judge / E2E / 审查状态：第 6 轮当前只做确定性 raw JSON streaming、renderer、contract 和前端共享消费回归；不声称真实模型质量分。
- 运行中断处理：用户关于 playbook 的反馈已被纳入当前轮改道处理，未继续沿原实现计划推进。
- 测试失败或生产阻断：没有新的阻断失败证据。
- 架构、文档或代码事实冲突：无。VALUE final renderer、manifest 和 contract 已存在；缺口集中在 partial renderer dispatch 和 runtime streaming 测试。
- 工作区冲突：存在大量无关脏文件；本轮限定写入范围，不回滚、不格式化、不 stage 无关文件。
- 是否需要拆分或合并：不拆分。四个 VALUE 阶段属于 Alex 价值发现到 Lisa handoff 的同一用户链路，缺口集中在同一 partial rendering 入口和两组 backend tests。

子智能体 / 旁路审查决策：

- 已派发只读 explorer Hypatia 复核 VALUE contract、field order、final renderer/helper、runtime tests、依赖字段和拆分风险。
- Hypatia 结论：四阶段可作为同一第 6 轮完成；主要切入点是 `render_partial_agent_turn_from_artifact_data()` 缺 `VALUE_DISCOVERY` 分支；`ELEVATOR` 的 `score_matrix + score_summary`、`PERSONA` 的 `personas` 映射、`JOURNEY` 的 summary 顺序、`BLUEPRINT` 的 `document_info` 与成对字段会影响 patch 形态，但不阻断正式 artifact delta。
- 不派发 worker：本轮实现集中编辑同一 backend renderer 与同一组测试文件，多个 worker 会增加写入冲突。

结论：继续承接第 6 轮 `VALUE_DISCOVERY`。

## 自问自答式需求澄清

问题：本轮用户可感知的完整能力是什么？

回答：用户在 Alex 价值发现 workflow 中做价值定位、用户画像、用户旅程和需求蓝图时，右侧正式 artifact 不再等待完整 `artifact_data` 闭合后一次性出现，而是在已闭合顶层字段可校验后逐步增长。最终需求蓝图仍保留 Lisa handoff 所需内容。

问题：为什么不拆成四个子轮次？

回答：四个阶段共享 `render_partial_agent_turn_from_artifact_data()`、raw JSON streaming runtime、typed SSE 和前端 ArtifactPane 消费链路。最终 renderer 和 contract 已经存在，新增内容集中在同一个 backend 文件和两个测试文件。拆分会重复承接检查、spec、plan 和全量验证成本。

问题：前端是否需要 VALUE 专属逻辑？

回答：不需要。前端消费的是共享 typed SSE `agent_delta.output.artifact_update.replace.markdown` 和 `artifact_patch`。本轮保持前端无 workflow 专属分支，并用现有 `llm.ts`、`chatService`、`ArtifactPane.incrementalRender` 回归证明通用消费链路。

问题：哪些字段依赖会影响 partial patch？

回答：`ELEVATOR` 的评分矩阵需要 `score_matrix` 与 `score_summary` 成对渲染；`PERSONA` 的行为、决策、痛点和排序章节需要 `personas` 做名称映射；`JOURNEY` 的 `journey_summary` 在字段顺序靠前但 final renderer 放在后段；`BLUEPRINT` 的 H1 依赖 `document_info.product_name`，核心需求需要 `feature_modules + requirements` 成对渲染。这些场景允许某些增量只有 replace markdown、没有单 section `add_after` patch。

## 方案比较

方案 A：只补 VALUE partial renderer、dispatch 和 backend streaming tests。

- 优点：改动集中，复用 final renderer helper，不新增运行时或前端分支，符合共享架构原则。
- 缺点：部分字段依赖导致不是每个顶层字段都能产生单独 patch，需要测试明确边界。

方案 B：为 VALUE 新增前端或 workflow 专属 streaming 分支。

- 优点：可以为 Alex 场景写更直接的 UI 断言。
- 缺点：违反 New Agents 共享 runtime、transport、state 和 UI 基础设施原则，会把 workflow 差异写进 UI 管线。

方案 C：先抽象一套通用 partial renderer 配置 DSL，再迁移所有已完成 workflow。

- 优点：长期可能减少重复。
- 缺点：会扩大本轮风险，触碰已验证的 13 个阶段，不适合作为第 6 轮纵切目标。

选择方案 A。本轮只补 VALUE 四阶段的后端正式 partial renderer、runtime raw JSON streaming 测试和记录；前端保持共享链路。

## 设计

### Partial renderer 入口

继续使用 `render_partial_agent_turn_from_artifact_data()`。为四个 stage 增加配置：

- `ELEVATOR`：`document_info`、`positioning_summary`、`value_flow`、`target_scenarios`、`pain_evidence`、`differentiators`、`business_feasibility`、`score_matrix`、`score_summary`、`assumptions`、`elevator_pitch`、`stage_gate`。
- `PERSONA`：`document_info`、`persona_summary`、`personas`、`behavior_scenarios`、`decision_chain`、`pain_evidence`、`anti_personas`、`priority_ranking`、`stage_gate`。
- `JOURNEY`：`document_info`、`journey_summary`、`journey_stages`、`pain_priorities`、`opportunity_scores`、`entry_strategy`、`validation_experiments`、`stage_gate`。
- `BLUEPRINT`：`document_info`、`product_overview`、`target_users`、`feature_modules`、`requirements`、`main_flow`、`success_metrics`、`mvp_plan`、`non_functional_requirements`、`acceptance_criteria`、`roadmap`、`risks`、`lisa_handoff_inputs`、`stage_gate`。

每个 renderer 只在最小可校验字段闭合后返回 Markdown；不完整字段返回 `None`，避免进度页、裸 JSON 或未经校验的半成品。

### Helper 复用

所有 partial renderer 复用现有 final renderer helper：

- `ELEVATOR`：`_render_value_positioning_summary()`、`_render_value_flow()`、`_render_target_scenarios()`、`_render_pain_evidence()`、`_render_differentiators()`、`_render_business_feasibility()`、`_render_value_score_matrix()`、`_render_value_assumptions()`、`_render_elevator_pitch()`、`_render_value_stage_gate()`。
- `PERSONA`：`_render_persona_summary()`、`_render_persona_profiles()`、`_render_persona_behavior_scenarios()`、`_render_persona_decision_chain()`、`_render_persona_pain_evidence()`、`_render_anti_personas()`、`_render_persona_priority_ranking()`、`_render_value_stage_gate()`。
- `JOURNEY`：`_render_journey_map()`、`_render_journey_map_visual()`、`_render_journey_stage_details()`、`_render_journey_pain_priorities()`、`_render_journey_opportunity_scores()`、`_render_journey_entry_strategy()`、`_render_journey_validation_experiments()`、`_render_journey_summary()`、`_render_value_stage_gate()`。
- `BLUEPRINT`：`_render_blueprint_product_overview()`、`_render_blueprint_target_users()`、`_render_blueprint_requirements()`、`_render_blueprint_main_flow()`、`_render_blueprint_success_metrics()`、`_render_blueprint_mvp_plan()`、`_render_blueprint_non_functional_requirements()`、`_render_blueprint_acceptance_criteria()`、`_render_blueprint_roadmap()`、`_render_blueprint_risks()`、`_render_blueprint_lisa_handoff_inputs()`、`_render_blueprint_stage_gate()`、`_render_blueprint_document_info()`。

Pydantic 子模型继续做局部验证；列表字段继续使用 `_validate_partial_list()`。

### Runtime 行为

raw JSON streaming 期间，runtime 已会基于已解析的完整顶层成员尝试 `render_partial_agent_turn_from_artifact_data()`。本轮只增加 VALUE stage 命中分支，不改变 SSE event 类型、payload schema、持久化、final `agent_turn` 或前端消费逻辑。

### 验收条件

1. Given 模型正在输出 `VALUE_DISCOVERY/ELEVATOR`
   When `positioning_summary`、`value_flow`、`target_scenarios`、`score_matrix + score_summary` 等字段闭合
   Then final `agent_turn` 前出现正式《价值定位分析》Markdown delta，并保留 Mermaid `flowchart` 与 `score-matrix`
   Evidence: backend partial renderer test 与 runtime raw JSON streaming test。

2. Given 模型正在输出 `VALUE_DISCOVERY/PERSONA`
   When `persona_summary`、`personas`、`behavior_scenarios`、`decision_chain` 等字段闭合
   Then final `agent_turn` 前出现正式《用户画像分析》Markdown delta，并保留画像、行为场景和决策链章节
   Evidence: backend partial renderer test 与 runtime raw JSON streaming test。

3. Given 模型正在输出 `VALUE_DISCOVERY/JOURNEY`
   When `journey_stages`、`pain_priorities`、`opportunity_scores` 等字段闭合
   Then final `agent_turn` 前出现正式《用户旅程分析》Markdown delta，并保留 Mermaid `journey` 与 `journey-map`
   Evidence: backend partial renderer test 与 runtime raw JSON streaming test。

4. Given 模型正在输出 `VALUE_DISCOVERY/BLUEPRINT`
   When `document_info + product_overview`、`target_users`、`feature_modules + requirements`、`main_flow`、`roadmap` 等字段闭合
   Then final `agent_turn` 前出现正式《需求蓝图》Markdown delta，并保留 Lisa handoff 输入和 `roadmap`
   Evidence: backend partial renderer test 与 runtime raw JSON streaming test。

5. Given 前端收到通用 typed SSE artifact delta
   When markdown 内容递增或 patch 可用
   Then `artifactContent` 继续实时更新，不需要 VALUE 专属 UI 分支
   Evidence: 现有 frontend `llm.ts`、`chatService`、`ArtifactPane.incrementalRender` 回归。
