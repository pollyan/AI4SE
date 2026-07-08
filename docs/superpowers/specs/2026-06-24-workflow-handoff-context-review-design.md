# Workflow Handoff 上下文审阅闭环设计

## Superpowers Brainstorming 自问自答

### Explore Project Context

问: 当前仓库事实说明了什么？

答: `tools/new-agents/` 已经有共享 Agent Runtime、typed SSE、run persistence、artifact persistence、workflow manifest 和共享前端 store。`VALUE_DISCOVERY/BLUEPRINT` 已能通过 manifest 配置 handoff 到 Lisa 的 `TEST_DESIGN/CLARIFY` 和 `REQ_REVIEW/REVIEW`。当前 `workflow_handoffs.py` 只把来源阶段、目标阶段和原始 artifact 拼成 prompt，前端 `ChatPane` 只展示按钮 label。用户能启动下游 workflow，但不能在启动前审阅来源版本、关键摘要、未确认项和目标输入是否足够。

问: 这个需求是否过大，需要拆分吗？

答: 不需要拆分。它只围绕同一个用户动作链: 从 Alex 需求蓝图交给 Lisa 继续工作。后端上下文提取、API 返回、前端展示、store 承接和测试证据属于同一能力包，拆开会导致用户仍不能完整判断 handoff 是否可靠。

问: 当前有哪些约束？

答: 必须复用共享 runtime、manifest handoff 配置、artifact persistence、typed API response 和共享 UI；不能新增 Lisa/Alex 专属 API path、store 或 renderer。主工作区有既有未提交改动，所以本轮在隔离 worktree `codex/workflow-handoff-context-goal-mainline` 实施。

### Visual Companion Decision

问: 是否需要视觉辅助或浏览器 mock？

答: 不需要。UI 改动是现有 ChatPane handoff action 卡片的信息密度增强，不涉及全新布局选择、视觉风格探索或复杂交互原型。用组件测试验证可见文本和按钮行为即可。

### Clarifying Questions

问: 用户是谁？

答: 使用 New Agents 工作台的产品/测试协作用户。他们先用 Alex 生成需求蓝图，再希望交给 Lisa 做需求评审或测试设计。

问: 用户要完成什么真实任务？

答: 在启动 Lisa workflow 前，判断 Alex 产物是否适合作为下游输入，并让 Lisa 带着明确的来源版本、关键需求、验收标准、风险和未确认项继续工作。

问: 成功状态是什么？

答: Handoff action 不再只是一个按钮。用户能看到来源版本、关键摘要、未确认项、目标输入检查项；点击后目标 run 的首条用户消息也包含这些上下文，Lisa 能基于同一信息继续生成目标 artifact。

问: 输入从哪里来？

答: 从 persisted run snapshot 中的 source stage artifact 来。首批只处理 manifest 已配置的 `VALUE_DISCOVERY/BLUEPRINT` handoff，不新增新的 handoff 来源。

问: 失败路径如何处理？

答: 如果没有 source artifact，仍不导出 handoff。若 handoff payload 缺失结构化上下文字段，前端 service 明确失败，不做隐藏 fallback。若 source artifact 无法提取未确认项，返回空数组并在 prompt 中说明“无”。若 artifact 太长，继续使用现有截断策略。

问: 下游如何承接？

答: `start_workflow_handoff()` 创建目标 run，并把增强后的 prompt 作为目标 run 第一条 user message 持久化。前端 `applyWorkflowHandoff()` 继续重置到目标 workflow/stage，并保留目标 run id。

问: 本轮不做什么？

答: 不做 run 历史复制/筛选，不做全局质量评分，不做 DeepSeek 真实 smoke，不新增其他 workflow handoff，不做新的 runtime 或 renderer。

### Approaches

方案 A: 后端构建结构化 handoff context，API 返回字段，前端直接展示并用同一 prompt 启动目标 run。
优点: 契约集中在后端，前端保持渲染职责；目标 run 和 UI 使用同一上下文，避免展示与实际 prompt 不一致。
缺点: 后端需要从 Markdown artifact 中做轻量提取，规则要保守。

方案 B: 后端只返回 raw artifact，前端解析摘要和未确认项。
优点: 后端改动少。
缺点: 解析逻辑进入 UI 层，难以保证目标 run prompt 与前端展示一致，也增加前端 markdown 解析负担。

方案 C: 新增专门 handoff diagnostic endpoint。
优点: 可以独立扩展复杂诊断。
缺点: 对当前问题过重，引入额外 API 面，偏离 manifest 驱动的现有 handoff 模型。

推荐方案: 选择方案 A。它保持共享 API/运行时不变，只增强现有 handoff response 契约和 prompt 构造，能一次性完成用户可见审阅与下游承接闭环。

### Presented Design

Architecture: `workflow_handoffs.py` 在构建 handoff candidate 时生成 `sourceSummary`、`unconfirmedItems` 和 `targetInputChecklist`。这些字段与现有 `prompt` 一起通过 `/api/agent/runs/<runId>/handoffs` 和 `/start` 返回。

Components: 后端新增轻量 Markdown 提取函数，前端 `WorkflowHandoff` 类型和 `workflowHandoffService` parser 强制校验新字段，`ChatPane` 在跨智能体接力卡片内展示来源版本、摘要、未确认项和检查项，store 继续把增强 prompt 作为目标 workflow 初始消息。

Data flow: source run snapshot -> source artifact -> structured handoff context -> API response -> ChatPane review card -> start handoff -> target run first message -> store route to Lisa workflow。

Error handling: 缺 source artifact 时不提供 handoff；未知 template 仍抛错； malformed API payload 前端显式失败；无法提取未确认项时使用空数组而不是伪造问题；artifact 截断继续显示截断提示。

Testing: 先补后端 RED 测试证明 handoff response/prompt 必须包含结构化上下文；补前端 service/parser、ChatPane 可见展示和 store 承接测试；实现最小代码后运行后端 handoff/API 测试、前端 handoff 相关 Vitest、lint 和 `git diff --check`。

## 用户故事

作为使用 Alex 和 Lisa 协作的用户，我希望在把 Alex 的需求蓝图交给 Lisa 前，能审阅一份清晰的 handoff 上下文，这样我可以确认来源版本、关键需求、验收标准、风险和未确认项都被带到目标 workflow，而不是让 Lisa 基于一段不透明的长文继续工作。

## 范围

本轮包含:

- `VALUE_DISCOVERY/BLUEPRINT` 到 Lisa 目标 workflow 的结构化 handoff context。
- 后端 handoff response 和 start response 同步返回结构化字段。
- 目标 run 初始 user prompt 包含来源版本、关键摘要、未确认项和目标输入检查项。
- 前端 handoff service 严格解析新字段。
- ChatPane handoff 卡片展示可审阅上下文。
- Store 应用 handoff 时保留增强 prompt。
- 后端、前端和文档/todo 记录。

本轮不包含:

- 新增 Alex/Lisa 专属 runtime、API path、store 或 renderer。
- 新增其他 source workflow 的 handoff。
- 历史 run 复制、收藏、筛选或跨 run 对比。
- 全局质量评分趋势。
- 真实 DeepSeek V4 Flash smoke。

## 验收条件

1. 当 source run 存在 `VALUE_DISCOVERY/BLUEPRINT` artifact 时，handoff candidate 返回 `sourceSummary`、`unconfirmedItems`、`targetInputChecklist`、`sourceArtifactVersion` 和增强 prompt。
2. 增强 prompt 至少包含来源版本、关键摘要、未确认项、目标工作流输入和源产物内容。
3. `start_workflow_handoff()` 创建目标 run 后，目标 run 第一条 user message 等于增强 prompt。
4. 前端 service 对缺少结构化上下文字段的 handoff payload 显式报错。
5. ChatPane 在 handoff action 卡片中展示来源版本、摘要、未确认项和目标检查项，点击后仍导航到目标 Lisa workflow。
6. Store 应用 handoff 后清空旧上下文，进入目标 workflow/stage，并保留增强 prompt 作为新 chat 第一条消息。
7. 不改变共享 `/api/agent/runs/stream` typed SSE，不新增 agent-specific runtime。

## 风险与取舍

- Markdown 提取只能做保守摘要，不能替代完整语义理解；因此 prompt 仍携带 bounded source artifact。
- 未确认项提取以状态关键词为主，可能漏掉隐含风险；本轮目标是“显式携带可见未确认项”，不是完整质量评分。
- ChatPane 信息增多可能增加视觉密度；本轮只展示精简摘要和最多若干条列表，避免把完整 artifact 放进 action card。
- API response 契约变严会要求现有测试 fixture 同步更新，这是有意为之，避免前端吞掉不完整 handoff。

## 验证计划

- 后端聚焦: `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_agent_endpoint.py -q`
- 前端聚焦: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts`
- 前端静态检查: `cd tools/new-agents/frontend && npm run lint`
- Diff hygiene: `git diff --check`

真实模型 smoke 不作为本轮默认门禁，因为本轮改动不调用模型，也不改变 provider adapter。
