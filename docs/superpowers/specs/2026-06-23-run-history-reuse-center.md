# 历史会话复用中心 Spec

## 背景

New Agents 已有持久化 run、run list、run snapshot restore、artifact version 和 context summary。当前 Header 历史会话入口可以按全部 / 当前 workflow 加载列表、搜索文本并跳转到原 run，但它仍偏“找回会话”，不是“复用已有工作”：

- 列表没有质量状态，用户难以判断哪个 run 可继续。
- 当前 artifact 只有摘要，没有可读预览。
- 用户只能回到原 run，不能安全复制成新 run 后继续。
- run list 不能按质量状态筛选。

## 用户故事

作为 New Agents 工作台用户，当我需要复用历史工作时，我可以在历史中心预览历史 run 的当前产物和质量状态，并选择继续原 run 或复制成新 run，从而安全地恢复或派生已有工作。

## 范围

纳入本轮：

- 后端 run list 增加：
  - `qualityStatus`: 基于当前 artifact summary 和最近运行状态派生的规则型状态。
  - `currentArtifact.preview`: 当前 artifact 的短预览文本。
  - `qualityStatus` 查询过滤。
- 后端新增 run clone 能力：
  - 从来源 run 创建独立 runId。
  - 复制消息、当前 artifact 内容 / artifactData、context summaries。
  - 不复制 artifact comments、section locks、audit events 或 test asset materialization。
- 前端 `runSnapshotService` 增加 strict parser、query 参数和 `cloneRun` 调用。
- Header 历史中心展示质量状态、artifact preview、继续和复制动作，并支持质量筛选。
- 更新活动 todo 与本轮 spec / plan。

不纳入本轮：

- 跨用户分享、收藏、跨 run 对比。
- 全局质量评分模型或 LLM judge。
- 新 runtime、SSE path、agent-specific store 或 renderer。
- 复制协作批注、章节锁、审计事件、测试资产集合。

## 质量状态规则

本轮先做保守规则型状态，避免伪造评分：

- `needs_action`: 当前 artifact 摘要或最后消息包含阻断、待确认、待澄清、缺失、失败、异常、错误等词。
- `ready`: run 状态为 `completed` 或存在当前 artifact summary 且没有上述风险词。
- `in_progress`: 其他可继续 run。

该状态用于历史中心筛选和快速判断，不替代 E08 的完整工作流质量评分。

## 验收条件

1. Given 已有 persisted run，When 查询 `/api/agent/runs`，Then run list item 包含 `qualityStatus` 与 `currentArtifact.preview`。
2. Given 使用 `qualityStatus` 查询参数，When 查询 run list，Then 只返回匹配质量状态的 runs，非法状态返回 400。
3. Given 一个来源 run，When 调用 clone endpoint，Then 返回新 run snapshot；新 run 具备独立 runId、复制后的 messages/artifacts/context summaries，原 run 不变。
4. Given Header 历史中心加载 runs，When 用户选择质量筛选或展开 run，Then 可看到质量状态和 artifact preview。
5. Given 用户点击继续或复制，When 操作成功，Then 前端导航到 `/workspace/:agent/:workflow?runId=<runId>`，继续沿用现有 snapshot restore 路径。

## 风险

- clone 语义容易过度复制。为降低风险，本轮只复制对继续生成必要的 messages、artifacts、context summaries。
- 质量状态是启发式，不应被描述为完整质量评分。
- Header 已承载多种弹窗和操作，本轮只扩展历史中心局部，不重构 Header。

## 验证计划

- `python3 -m pytest tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py -q`
- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/Header.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `git diff --check`
