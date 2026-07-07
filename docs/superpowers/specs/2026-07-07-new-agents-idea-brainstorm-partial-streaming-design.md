# New Agents 第 5 轮 IDEA_BRAINSTORM partial artifact streaming 设计

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/strategy/goal-mode-subagents.md`、`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、`tools/new-agents/workflow_manifest.json`、`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`。
- 当前工作区：存在大量与本轮无关的删除和修改；本轮只写入 IDEA partial streaming 相关 spec / plan / todo、`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`。

已确认目标来源：

- 来源：`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`。
- 本轮承接：第 5 轮 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`。
- 上一轮状态：第 1-4 轮已记录完成确定性验证；Lisa judge 64 分质量门已有修复记录，并通过 `score >= 80` 断言。

改道条件检查：

- 新 P0/P1 或用户新目标：无新的替代目标；用户反馈已经转化为 playbook 中质量门和子智能体规则。
- 未关闭质量门或用户明确反馈：Lisa 低分质量门已修复并重跑通过；本轮仍保留“若 judge 启用则必须 >=80”的规则。
- 测试失败或生产阻断：当前没有新的阻断失败证据。
- 架构、文档或代码事实冲突：无；本轮继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、共享前端 store 和 ArtifactPane。
- 工作区冲突：存在大量无关脏文件；本轮限定写入范围，不回滚、不格式化、不 stage 无关文件。
- 是否需要拆分或合并：不拆分。四个 IDEA 阶段属于同一创意脑暴用户链路，final renderer 和 contract 已存在，缺口集中在 partial dispatch 与 runtime 测试。

子智能体 / 旁路审查决策：

- 已派发只读 explorer 复核 IDEA contract、renderer/helper、runtime tests 和拆分风险。
- 已派发只读 explorer 复核未关闭质量门、Lisa judge 80 分记录、前端通用 artifact delta 消费和第 5 轮验证风险。
- 不派发 worker：本轮实现会编辑同一组高冲突 backend renderer 和 tests，串行 TDD 更可控。

结论：继续承接第 5 轮 `IDEA_BRAINSTORM`。

## 自问自答式需求澄清

问题：本轮用户可感知的完整能力是什么？

回答：用户在创意脑暴 workflow 中从问题定义、创意发散、收敛聚焦到产品概念简报时，右侧正式 artifact 不再等完整 `artifact_data` 对象闭合后一次性出现，而是在已完成顶层字段闭合后逐段增长。最终 artifact 仍满足完整 contract、Mermaid 和 `ai4se-visual` 要求。

问题：为什么不拆成四个子轮次？

回答：四个阶段共享同一 backend partial rendering 入口、同一 raw JSON streaming runtime 行为和同一前端 artifact delta 消费链路；现有 final renderer/helper 已完整覆盖四个阶段。单轮触达文件少且验证闭环一致，拆分会重复 spec / plan / 全量验证成本。

问题：前端是否需要 IDEA 专属逻辑？

回答：不需要。前端消费的是通用 typed SSE `agent_delta.output.artifact_update.replace.markdown` 和 `artifact_patch`，不应新增 IDEA 专属 store 或渲染分支。本轮用现有 `llm.ts`、`chatService`、`ArtifactPane.incrementalRender` 回归证明通用消费链路仍成立。

问题：哪些阶段不能保证每个字段都产生单 section patch？

回答：`DIVERGE` 的 `## 发散全景图` 需要 `idea_landscape` 和 `idea_cards` 同时闭合才能把 idea id 映射到标题；`CONVERGE` 的 `## 决策矩阵` 需要 `decision_matrix` 和 `ice_evaluations` 同时闭合才能渲染 Mermaid quadrantChart。它们仍应产生正式 Markdown partial delta，但首个可见增量可能一次加入多个 section，`artifact_patch` 可以为空。

## 方案比较

方案 A：只给四个 IDEA 阶段补 partial renderer 和 dispatch。

- 优点：改动集中，复用 final renderer helper，风险低。
- 缺点：不新增前端 IDEA 专属断言，需要依赖已有通用前端回归证明消费链路。

方案 B：同时新增 IDEA 专属前端测试和 UI 分支。

- 优点：IDEA 前端路径看起来更直接。
- 缺点：违反共享 runtime / store / rendering pipeline 原则，容易把 workflow 差异编码到 UI 分支。

方案 C：先抽象所有 workflow partial renderer DSL。

- 优点：长期可减少重复。
- 缺点：当前目标是纵切消化剩余阶段，抽象会扩大风险并推迟用户可见闭环。

选择方案 A。本轮只补 IDEA 的后端正式 partial renderer、runtime raw JSON streaming 测试和记录；前端保持共享链路并跑通用回归。

## 设计

### Partial renderer 入口

继续使用 `render_partial_agent_turn_from_artifact_data()`。为四个 stage 增加配置：

- `DEFINE`：`problem_statement`、`target_users`、`problem_landscape`、`evidence_items`、`problem_user_fit`、`constraints_boundaries`、`reverse_validation`、`stage_gate`。
- `DIVERGE`：`divergence_method`、`idea_landscape`、`idea_cards`、`idea_sources`、`parked_or_excluded`、`stage_gate`。
- `CONVERGE`：`decision_matrix`、`ice_evaluations`、`resource_constraints`、`sensitivity_analysis`、`validation_experiments`、`merge_paths`、`stage_gate`。
- `CONCEPT`：`positioning_statement`、`core_assumptions`、`lean_canvas`、`mvp_features`、`growth_funnel`、`premortem_risks`、`validation_roadmap`、`out_of_scope`、`decision_records`、`next_actions`、`stage_gate`。

每个 partial renderer 只在最小首段可校验字段出现后返回 Markdown；否则返回 `None`，避免生成占位页、裸 JSON 或未校验内容。

### Helper 复用

所有 partial renderer 复用现有 final renderer helper：

- DEFINE：`_render_idea_problem_statement()`、`_render_idea_target_users()`、`_render_idea_problem_landscape()` 等。
- DIVERGE：`_render_idea_divergence_method()`、`_render_idea_diverge_landscape()`、`_render_idea_cards()` 等。
- CONVERGE：`_render_idea_converge_decision_matrix()`、`_render_idea_ice_evaluations()`、`_render_idea_resource_constraints()` 等。
- CONCEPT：`_render_idea_concept_positioning()`、`_render_idea_concept_core_assumptions()`、`_render_idea_concept_mvp_features()` 等。

Pydantic 子模型用现有 `Idea*` classes 做局部验证；列表字段继续使用 `_validate_partial_list()`。

### Runtime 行为

raw JSON streaming 期间，runtime 仍基于已解析的完整顶层成员尝试 `render_partial_agent_turn_from_artifact_data()`。本轮只改变 IDEA stage 命中分支，不改变 SSE 事件类型、payload schema、persistence、final `agent_turn` 或前端消费逻辑。

### 验收条件

1. Given 模型正在输出 `IDEA_BRAINSTORM/DEFINE` 的 `artifact_data`
   When `problem_statement`、`target_users`、`problem_landscape` 等字段依次闭合
   Then final `agent_turn` 前出现正式《问题域分析》Markdown delta，并保留 mindmap
   Evidence: backend partial renderer test 与 runtime raw JSON streaming test。

2. Given 模型正在输出 `IDEA_BRAINSTORM/DIVERGE`
   When `divergence_method` 先闭合，随后 `idea_landscape` 与 `idea_cards` 闭合
   Then final `agent_turn` 前出现正式《创意发散》Markdown delta，并保留 mindmap
   Evidence: backend partial renderer test 与 runtime raw JSON streaming test。

3. Given 模型正在输出 `IDEA_BRAINSTORM/CONVERGE`
   When `decision_matrix` 与 `ice_evaluations` 都闭合，随后资源约束和验证实验闭合
   Then final `agent_turn` 前出现正式《收敛聚焦》Markdown delta，并保留 quadrantChart
   Evidence: backend partial renderer test 与 runtime raw JSON streaming test。

4. Given 模型正在输出 `IDEA_BRAINSTORM/CONCEPT`
   When 定位、假设、Lean Canvas、MVP 功能等字段依次闭合
   Then final `agent_turn` 前出现正式《产品概念简报》Markdown delta，并保留 `mvp-map`
   Evidence: backend partial renderer test 与 runtime raw JSON streaming test。

5. Given 前端收到通用 typed SSE artifact delta
   When markdown 内容递增或 patch 可用
   Then `artifactContent` 继续实时更新，不需要 IDEA 专属 UI 分支
   Evidence: 现有 frontend `llm.ts`、`chatService`、`ArtifactPane.incrementalRender` 回归。
