# QG-023：New Agents 双层 E2E 收口

- 状态：`DONE`（2026-07-22，待归档）
- 优先级：P1（push 前工程信任）
- 来源：用户确认“最精简且兼顾质量保障”的两套 E2E，并要求立即执行。
- Owning spec：[双层 E2E 收口设计](../../superpowers/specs/2026-07-22-qg023-two-tier-new-agents-e2e-design.md)
- 实施计划：[QG-023 implementation plan](../../superpowers/plans/2026-07-22-qg023-two-tier-new-agents-e2e.md)

## 目标态

New Agents 只有两道 E2E 门禁：

1. **确定性功能 E2E**：保留真实无头浏览器可见的流式、渲染、handoff 与阶段行为；并包含一个真实 React/Vite、Flask、SQLite、typed SSE、Chromium 和 deterministic provider 的两阶段 tracer。
2. **真实模型 Release E2E**：继续在本地 production-shaped 部署栈上使用已配置的 DeepSeek，覆盖 manifest 派生的全部 7 个 workflow、25 个 stage 和 18 次合法 transition。

此前 `test_live_stack.py` 中仅验证 observer、日志脱敏、SSE 诊断等确定性契约的用例下沉为契约测试；它们不再被误计为第三套 E2E，但不得删除或改成 mock 本仓库运行时。

## 不变量与边界

- 不减少 `chat → artifact` 首帧顺序、分段流式、artifact 单调性、持久化恢复、跨 workflow handoff / Story packet、配置鉴权或错误脱敏覆盖。
- 不用真实模型替代故障注入；`artifact-first`、retry、非法/损坏 SSE、active-tail rewrite 等可控坏路径仍由确定性测试保护。
- 不用 mock 替代要验收的 React、Flask、typed SSE、服务端持久化或 Chromium；deterministic provider 仅是外部模型边界的受控替身。
- 不新增 workflow/agent 专属 runtime、endpoint、state store 或渲染管线；不建立截图、像素 diff 或假成功路径。
- 每次 push 前仍只能运行 `./scripts/test/pre-push.sh` 的固定全量门禁；聚焦命令只服务开发反馈，不能取代它。

## 完成证据

- 聚焦 RED/GREEN 与迁移验证：`tests/test_new_agents_deterministic_e2e.py`、`tests/test_new_agents_functional_runner.py`、`tests/test_pre_push_gate.py`、`test_live_stack_contracts.py`、`test_deterministic_live_stack.py` 共 95 项通过。
- 规格与规范独立复审均已完成；发现的本地 contracts 漏跑、aggregate 统计失真与文档路径漂移全部关闭。
- 对提交 `164527c58cea6a866afa81d54327daf6709416e3` 在隔离 clean worktree 执行 `./scripts/test/pre-push.sh`，所有 phase 为 `PASS`：Intent API 510、proxy 40、New Agents frontend 949、backend 1253、level-2 contracts 86、统一 deterministic E2E 23；production-shaped deployment 通过；真实 DeepSeek Release 证据覆盖 7 workflows、25 stages、18 transitions；finalization 通过。
- 用户已有 `tools/intent-tester/test-results/proxy/junit.xml` 脏文件未读取、未修改、未暂存或提交。固定门禁首次在主 worktree 因该文件正确失败关闭，后续只在 clean worktree 验证。

## 本轮厚切片与顺序

本轮只有一个厚切片：把现有三处 New Agents E2E 证据按职责收口为两道可审计门禁，并使本地开发入口、CI、测试文档和固定 pre-push registry 同步。内部迁移、重命名和 runner 调整不是独立待办或交付。

完成证据：新 registry 只有一个确定性 New Agents E2E suite 和一个真实 Release suite；两阶段 live tracer 证明真实服务链路；下沉的 observer 契约仍独立执行；CI/本地命令/文档一致；最终 `HEAD` 的固定全量 pre-push 通过。
