# New Agents INCIDENT_REVIEW Partial Artifact Streaming Design

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、`docs/CODING_STANDARDS.md`、`docs/DESIGN_PRINCIPLES.md`、`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`、`tools/new-agents/workflow_manifest.json`、`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/agent_runtime.py`、`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`。
- 当前工作区：存在大量无关删除、归档目录变更、压缩包和文档变更；本轮只允许写入本 spec、本轮 plan、纵切 todo、`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py` 和 `tools/new-agents/backend/tests/test_agent_runtime.py`。

已确认目标来源：

- 来源：`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md` 已声明 7 轮纵切目标。
- 本轮承接：第 4 轮，`INCIDENT_REVIEW/TIMELINE`、`INCIDENT_REVIEW/ROOT_CAUSE`、`INCIDENT_REVIEW/IMPROVEMENT`，用户故事为“故障复盘 workflow 真实 partial streaming 闭环”。
- 上一轮状态：第 1-3 轮已完成确定性验证；Lisa judge 64 分质量门失败已修复，并通过 `score >= 80` 的可选 judge 测试。

改道条件检查：

- 新 P0/P1 或用户新目标：无。用户目标仍是持续消化 partial artifact streaming 纵切 todo。
- 测试失败或生产阻断：无新的失败证据；上一轮全量确定性回归通过。
- 架构、文档或代码事实冲突：无。`AGENTS.md` 要求复用共享 runtime/transport/state/UI；本轮只增加共享 partial renderer dispatch，不新增 workflow 专属链路。
- 工作区冲突：有大量无关脏文件，但本轮写入范围可隔离，不需要回滚或覆盖。
- 是否需要拆分或合并：不拆分。三个 INCIDENT_REVIEW 阶段属于同一个“故障复盘”用户动作链，当前已有 final renderer 和测试 fixture，预计可在一个目标轮次内完成；拆成 4a/4b/4c 会让用户首次感知的完整故障复盘流式能力被割裂。

边界复核：

- 本轮纳入：TIMELINE 事件还原、ROOT_CAUSE 根因分析、IMPROVEMENT 改进报告三个阶段的正式 partial artifact delta；后端 raw JSON streaming final 前的多段输出；最终 contract、Mermaid 和 ai4se-visual 保持；前端 typed SSE 消费回归；todo 记录。
- 本轮排除：第 5-7 轮 IDEA_BRAINSTORM、VALUE_DISCOVERY 和全量契约收口；真实模型 smoke 和新 LLM judge 不作为本轮必需门禁，除非环境和模型配置明确可用。
- 厚度门禁：入口是用户选择故障复盘 workflow；动作是输入故障经过并推进事件还原、根因分析、改进报告；处理是共享 Agent Runtime 在 `artifact_data` 顶层字段闭合后渲染正式 Markdown delta；可见结果是右侧 ArtifactPane 逐步出现时间线、5-Why/鱼骨图、行动看板；状态承接仍由 final `agent_turn` 和现有持久化处理；失败反馈由现有 Pydantic/contract 校验显式报错；证据为 partial renderer、runtime streaming、contract 和前端 stream 回归。

结论：继续承接第 4 轮，不升级完整 CGA。

## Superpowers Brainstorming 自问自答

### Explore Project Context

`INCIDENT_REVIEW` 已是在线 workflow，manifest、后端 stage 列表、prompt、artifact contract 和 final renderer 都存在。当前缺口不是“能不能生成故障复盘报告”，而是 raw JSON streaming 期间右侧 artifact 仍等完整 `artifact_data` 对象闭合后才正式更新。`TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY` 和 `REQ_REVIEW` 已建立共享实现模式：在 `render_partial_agent_turn_from_artifact_data()` 中按 workflow/stage 配置字段顺序，调用 partial renderer 渲染已闭合字段，并生成可选 `artifact_patch.add_after`。本轮应沿用该模式。

当前需求范围不需要视觉 companion。它不改变页面布局或交互控件，核心是后端正式 Markdown delta 的生成时机和契约保持。

### Clarifying Questions

- 用户是谁？使用 New Agents 的故障复盘用户，需要在模型生成过程中尽早看到右侧正式复盘内容。
- 用户要完成什么？从事件还原到根因分析再到改进报告，看到时间线、事实来源、5-Why、鱼骨图、改进行动和复查计划逐步成形。
- 成功状态是什么？每个阶段在 final `agent_turn` 前至少出现多个正式 artifact delta；最终 artifact 仍通过当前完整 contract。
- 输入来源是什么？模型按 structured output instruction 流式输出 JSON，后端只能基于已闭合 `artifact_data` 顶层字段渲染。
- 约束是什么？不能输出进度页、裸 JSON、字段名调试信息；不能新增 Incident 专属 runtime、SSE endpoint、store 或 UI pipeline；不能降低 final Pydantic/contract 校验。
- 失败路径是什么？局部字段未闭合或局部字段不合法时，不生成该字段及其后续章节；最终对象仍由完整模型和 contract 显式失败。
- 下游承接是什么？最终 `agent_turn` 仍进入现有 artifact version 持久化、stage action、Mermaid/ai4se-visual contract 和前端 ArtifactPane。
- 不做什么？不追求逐 token 打字机效果，不为真实模型输出质量新增 judge，不调整 prompt/manifest/final contract。

### Approaches

1. 推荐方案：新增三个 INCIDENT_REVIEW partial renderer，复用共享 dispatch、`_build_partial_add_after_patch()`、现有 final renderer helper 和现有 test fixture。优点是和前 1-3 轮一致，改动集中，风险低；缺点是 `IMPROVEMENT` 中容器标题会让部分增量无法形成单章节 patch，但仍可产生正式 replace delta。
2. 方案二：把 final renderer 拆成可组合 section registry，再由 full/partial 共用 declarative section 表。优点是长期减少重复；缺点是会重构大文件，触达范围超过本轮目标，不适合作为纵切实现轮。
3. 方案三：前端继续 synthetic reveal 最终 artifact。优点是改动小；缺点是不是真实 partial artifact streaming，违背 todo 非目标。

选择方案一。

### Presented Design

架构：继续复用共享 Agent Runtime raw JSON streaming 解析、typed SSE、`AgentTurnOutput.artifact_update.replace`、`artifact_patch.add_after` 和前端现有消费链路。新增逻辑只在 `artifact_data_renderers.py` 的 partial dispatch 和三个 partial renderer 内完成。

组件：

- `render_partial_incident_review_timeline_markdown(data)`：从 `incident_summary` 开始，依次渲染影响量化、事实来源、事件时间线、事实/推测隔离、事实摘要、参与人员、信息缺口章节、阶段门禁。
- `render_partial_incident_review_root_cause_markdown(data)`：从 `analysis_context` 开始，依次渲染 5-Why cause-map、根因证据、鱼骨 mindmap、根因结论、排除项、未验证原因、阶段门禁。
- `render_partial_incident_review_improvement_markdown(data)`：从报告信息开始，依次渲染事件还原摘要、根因摘要、改进措施分区、优先级 pie、action-board、根因覆盖、防复发、复查、残余风险、经验教训、组织学习、签署和阶段门禁。

数据流：raw JSON stream 每次解析到一个闭合 `artifact_data` 顶层字段时，runtime 调用 partial renderer。partial renderer 只渲染连续可验证字段，返回正式 Markdown；dispatch 根据字段顺序生成 `AgentTurnOutput`。最终完整 JSON 仍走 `render_agent_turn_from_artifact_data()` 和 `validate_agent_turn()`。

错误处理：partial renderer 对缺失首字段返回 `None`；对后续字段校验失败返回已成功渲染的前序章节，不输出错误占位。最终完整输出继续显式失败，不新增 fallback。

测试：先写 renderer RED tests 证明当前 dispatch 返回 `None`；再实现 partial renderers；升级三个 runtime tests，拆分 final JSON，让 final 前产生多段 artifact delta；最后跑已完成 partial runtime 回归、backend focused regression 和前端 stream 回归。

## 验收条件

1. Given `INCIDENT_REVIEW/TIMELINE` 的 raw JSON 逐字段流式输出，When `incident_summary`、`impact_metrics`、`fact_sources`、`timeline_events` 等字段陆续闭合，Then final 前出现正式《故障复盘报告》partial artifact delta，且包含 Mermaid timeline。
2. Given `INCIDENT_REVIEW/ROOT_CAUSE` 的 raw JSON 逐字段流式输出，When `analysis_context`、`why_chain`、`cause_evidence`、`fishbone_categories` 等字段陆续闭合，Then final 前出现正式根因分析 delta，且包含 `cause-map` 和 mindmap。
3. Given `INCIDENT_REVIEW/IMPROVEMENT` 的 raw JSON 逐字段流式输出，When `report_info`、`timeline_summary`、`root_cause_summary`、`priority_distribution`、`improvement_actions` 等字段陆续闭合，Then final 前出现正式改进报告 delta，且包含 pie 和 `action-board`。
4. Final `agent_turn` 仍通过 `validate_agent_turn()`、workflow manifest sync、Mermaid / structured visual contract 和现有前端 stream consumption regression。
5. 本轮 todo 记录 spec、plan、验证命令、LLM judge 状态和残余风险。
