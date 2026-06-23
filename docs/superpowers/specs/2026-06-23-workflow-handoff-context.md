# Workflow Handoff 上下文强化 Spec

## 背景

New Agents 已有配置化 workflow handoff: Alex 的 `VALUE_DISCOVERY/BLUEPRINT` 与 `STORY_BREAKDOWN/SPRINT_PLAN` 可以通过共享后端 handoff export/start、前端 `workflowHandoffService`、`ChatPane` 和 `applyWorkflowHandoff` 接力到 Lisa 的 `TEST_DESIGN` 或 `REQ_REVIEW`。

当前 handoff 只暴露来源阶段、目标阶段、来源 artifact version 和原始 artifact prompt。用户在启动接力前看不到关键摘要、未确认项和目标输入用途；Lisa 新 run 的首条消息也缺少明确的 handoff 上下文框架。

## 用户故事

作为 New Agents 工作台用户，当我已经让 Alex 生成需求蓝图或用户故事拆解后，我可以在接力 Lisa 前看到来源版本、关键摘要、未确认项和目标用途，并把这些上下文写入 Lisa 新 run，从而让跨智能体接力可判断、可追踪、可继续。

## 范围

纳入本轮：

- 后端 handoff export 增加共享字段：
  - `sourceArtifactSummary`: 来源 artifact 的确定性关键摘要。
  - `unresolvedItems`: 来源 artifact 中待确认、待澄清、风险或待补充条目的确定性列表。
  - `targetInputSummary`: 说明目标 workflow/stage 如何使用该 handoff 输入。
- 后端 handoff prompt 使用上述字段，并继续包含有界来源 artifact 内容。
- 前端 `WorkflowHandoff` 类型与 strict parser 同步新增字段。
- `ChatPane` handoff 卡片展示来源版本、摘要、未确认项和目标用途。
- start handoff 创建的 target run 第一条 user message 使用增强后的 prompt。
- 更新活动 todo，记录 E07 消化结果。

不纳入本轮：

- 新增 handoff 类型或 agent-specific runtime/API/store/renderer。
- Run 历史复制、历史质量筛选、跨 run 对比。
- LLM judge 评分、全局质量分、prompt/template 版本管理。
- 改动共享 typed SSE 或 Agent Runtime 执行路径。

## 验收条件

1. Given 一个包含来源 artifact 的 Alex persisted run，When 调用 handoff export，Then 每个候选包含来源版本、关键摘要、未确认项、目标输入说明和包含这些上下文的 prompt。
2. Given 来源 artifact 含有待确认、待澄清、风险或待补充内容，When 后端构建 handoff，Then `unresolvedItems` 至少包含可读条目，并在 prompt 中显式列出。
3. Given ChatPane 加载到 handoff candidates，When 用户查看接力卡片，Then 卡片展示来源版本、摘要、未确认项数量/内容和目标用途。
4. Given 用户启动 handoff，When 后端创建 target run，Then target run 的第一条 user message 等于增强后的 handoff prompt，前端仍通过共享 `applyWorkflowHandoff` 切换到目标 workflow。

## 风险

- Markdown artifact 格式来自确定性 renderer，但不同 workflow 标题不完全一致；摘要和未确认项提取必须保守、可诊断、不可伪造。
- 前端 strict parser 变更会使旧 handoff payload 测试失败；这是预期 contract 收紧，需要同步后端和测试。
- ChatPane 已承载多种卡片，新增展示需保持紧凑，避免影响消息主流程。

## 验证计划

- `python3 -m pytest tools/new-agents/backend/tests/test_workflow_handoffs.py -q`
- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `git diff --check`
