# Refactor Todo

`docs/todos/` 当前没有活动待办。2026-07-22 的 New Agents 双层 E2E 收口已完成并归档为 [`QG-023 历史记录`](../archive/2026-07-22-new-agents-two-tier-e2e-consolidation.md)；2026-07-21 的固定全量 pre-push 与生产发布安全工作也已归档为 [`历史记录`](../archive/2026-07-21-pre-push-full-validation-and-release-safety.md)。此前取消的 P2/P3、条件触发、旧真实模型 smoke、旧 E 编号和历史集成候选继续只保留事实证据，不得自动恢复实施。

## 当前状态

当前没有执行入口；需要新增工作时必须从 Goal Mode `BOOTSTRAP` 重新审计活动待办、失败证据与用户最新目标。

最近完成并归档的能力包为 [`2026-07-16-new-agents-streaming-and-artifact-ux.md`](../archive/2026-07-16-new-agents-streaming-and-artifact-ux.md)，包含：

1. `QG-017`：全工作流左侧有意义对话先于右侧产出物。
2. `QG-018`：统一 25 个在线阶段的右侧分段流式。
3. `QG-019`：文档信息退出首屏重表格。
4. `QG-020`：New Agents 真实链路、无头优先的功能测试重构；PR 跑关键真实旅程，Nightly/发布跑全阶段矩阵。

四项状态均为 `DONE`。不得与归档 Todo、旧 checkbox、旧分支或旧计划混合续跑。

## 共享架构约束

- `tools/new-agents/` 继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、服务端 run/artifact/version 持久化和共享 UI。
- Lisa、Alex 和未来 Agent 的差异通过 `agentId`、workflow/stage 配置、prompt/template、artifact/visual contract 和 handoff 配置表达。
- 未经明确架构变更批准，不新增 agent/workflow/stage 专属 runtime、transport、state store、SSE/API path 或渲染管线。
- 不使用 mock、fallback、伪造数据或假成功掩盖错误。

## 已归档

- [`2026-07-22-new-agents-two-tier-e2e-consolidation.md`](../archive/2026-07-22-new-agents-two-tier-e2e-consolidation.md)：`QG-023` 完成；确定性功能 E2E 与真实模型 Release E2E 双层收口，固定全量 pre-push 通过。
- [`2026-07-16-new-agents-streaming-and-artifact-ux.md`](../archive/2026-07-16-new-agents-streaming-and-artifact-ux.md)：`QG-017～QG-020` 全部完成；真实 PR/Nightly/Release 门禁闭合。
- [`2026-07-10-ai-coding-test-quality-improvement.md`](../archive/2026-07-10-ai-coding-test-quality-improvement.md)：`QS-01～QS-04` 完成证据；其余旧整改序列已取消，3 个 New Agents 待办已迁出。
- [`2026-07-08-new-agents-structured-artifact-failure-reduction.md`](../archive/2026-07-08-new-agents-structured-artifact-failure-reduction.md)：结构化产出失败治理完成记录；旧 P2 候选已取消。
- [`2026-06-23-deepseek-v4-structured-artifact-data.md`](../archive/2026-06-23-deepseek-v4-structured-artifact-data.md)：DeepSeek 结构化产物历史证据；真实 smoke 候选已取消。
- [`2026-06-23-new-agents-enhancement-diagnostic.md`](../archive/2026-06-23-new-agents-enhancement-diagnostic.md)：旧 E 编号能力包完成记录；增强候选已取消。
- [`2026-06-24-goal-mode-milestone-ledger.md`](../archive/2026-06-24-goal-mode-milestone-ledger.md)：历史 milestone 与集成证据。
- `docs/todos/archive/` 下其他文件均为历史记录，不是当前执行入口。
