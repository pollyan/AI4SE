# Alex 需求到单故事需求包证据收口设计

## 目标承接检查

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`、`docs/TESTING.md`、`docs/api-contracts.md`。
- 已读取代码与测试：`tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py`、`tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py`、`tests/e2e/new_agents_browser/conftest.py`、`tests/e2e/new_agents_browser/workflow_runner.py`、`tools/new-agents/backend/tests/test_workflow_handoffs.py`、`tools/new-agents/backend/tests/test_story_handoff_packets.py`、`tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`。
- 当前工作区：第 4 轮已提交并推送到 `0c2612fb`；仍存在大量与本路线无关的删除、文档和生成物变更，本轮只允许写入第 5 轮证据相关 E2E、文档和 todo。

已确认目标来源：
- 来源：Alex 路线 todo 第 5 轮。
- 本轮承接：证明 `需求蓝图 -> 用户故事拆解 -> 单故事 handoff packet` 主路径可用，并把 Lisa 既有 handoff 回归纳入收口证据。
- 前置状态：第 1-4 轮已分别完成目标侧 handoff、用户故事拆解工作流、结构化故事契约和单故事 packet 持久化。

改道条件检查：
- 用户反馈：Playbook 已有独立价值点 commit / push 规则，第 4 轮已按该规则提交并推送。
- 新 P0/P1：没有比第 5 轮更高优先级且同向的未关闭失败。
- 未关闭质量门：第 4 轮提权全量本地自动化通过；本轮仍需在最终变更后重跑聚焦 E2E、New Agents suite 和全量本地自动化。
- 架构约束：不新增真实 AI Coding workflow，不改 Lisa 契约，不创建 Alex 专属 runtime/store/transport。
- 子智能体 / 旁路审查：多智能体工具要求用户显式授权才可 spawn，本轮不分发子智能体，改用聚焦 E2E + 全量验证作为收口证据。

边界：
- 纳入：浏览器 E2E 串起 `VALUE_DISCOVERY/BLUEPRINT` 出站 handoff 到 `USER_STORY_BREAKDOWN/SCOPE`，继续完成四阶段用户故事拆解，并生成/复制单故事需求包。
- 纳入：E2E mock 保留 `VALUE_DISCOVERY/BLUEPRINT -> Lisa` handoff，证明新增 Alex 链路不会挤掉 Lisa 出站按钮。
- 纳入：todo、TESTING 文档记录最终证据和第 5 轮完成状态。
- 排除：真实 AI Coding workflow、实现计划消费协议、workflow 级 handoff 一等持久化表、LLM judge 新 rubric。

结论：继续承接第 5 轮证据收口。

## Superpowers 自问自答记录

### 用户可感知链路

用户从 Alex 的“需求蓝图梳理”开始，得到需求蓝图后，不需要复制 Markdown，而是在同一界面点击“从需求蓝图继续拆用户故事”。系统创建用户故事拆解目标 run，恢复上游蓝图上下文，继续四阶段拆成故事卡，最后对 ready story 生成单故事需求包。

### 缺口

当前已有三类证据：
- `test_alex_value_discovery_workflow.py` 覆盖需求蓝图和 Lisa handoff。
- `test_alex_user_story_breakdown_workflow.py` 覆盖用户故事拆解和 packet。
- 后端 / 前端单测覆盖 target-side handoff 和 story packet。

缺少的是同一个浏览器路径把 `VALUE_DISCOVERY/BLUEPRINT` 的 Alex handoff 按钮、目标 run snapshot、用户故事拆解阶段推进和 packet 生成连在一起。

### 方案

1. 推荐：新增一个浏览器 E2E 文件，复用已有 value discovery 和 user story scenario helper，在 E2E mock 里补 `value-discovery-blueprint-to-user-story-breakdown` 的出站 handoff、start response 和目标 run snapshot。优点是证据贴近用户路径，改动集中在测试和记录。
2. 只在 todo 里引用已有独立测试。优点是无代码改动；缺点是不能证明 handoff 后同一用户路径可继续生成 packet。
3. 新增后端集成测试模拟全部链路。优点是快；缺点是不覆盖真实浏览器跳转、workspace restore 和 ArtifactPane 复制。

选择方案 1。

## 验收

- 浏览器 E2E 从“需求蓝图梳理”完成到点击“从需求蓝图继续拆用户故事”。
- 跳转到 `/workspace/alex/user-story-breakdown?runId=mock-run-user_story_breakdown-handoff`。
- 目标 workspace 的初始消息包含上游需求蓝图上下文。
- 用户故事拆解四阶段完成后可生成并复制 `US-001` 单故事需求包。
- 复制内容包含 `storyId` 和 `acceptanceCriteria`，不包含 `implementationPlan`、`filePaths` 或 `testCommands`。
- 同一 mock 中仍保留“交给 Lisa 做测试设计”按钮，现有 Lisa handoff E2E 继续通过。
