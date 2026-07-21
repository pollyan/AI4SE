# QG-021 目标承接检查

- 日期：2026-07-21
- Goal Mode 状态：`ASSESS → MILESTONE`
- 结论：`CONTINUE QG-021`
- 顺序基线：[活动待办 QG-021 → QG-022](../../todos/2026-07-21-pre-push-full-validation-and-release-safety.md)
- 厚切片身份基线：[QG-021 设计](../specs/2026-07-21-fixed-full-pre-push-quality-gate-design.md#厚切片身份基线)

## 1. 已确认目标与上一轮证据

用户已明确要求按活动待办顺序消化两个能力包，并拒绝按 diff、路径或 Agent 影响分析缩小 push 前验证范围。`QG-021` 是当前唯一入口；`QG-022` 的生产发布事务与 readiness 风险不得提前混入本轮实现。

`2bcfe5d4` 已提交 QG-021 的设计、现状审计、活动待办和入口索引。设计确认固定全量门禁、去重、隔离的 production-shaped 本地部署与部署栈真实 DeepSeek 无头 E2E 是同一个工程信任闭环，不把 runner、Compose 或 E2E 单独记为切片或交付。

## 2. 当前事实、工作区与质量门

本轮重新读取了 `AGENTS.md`、Goal Mode Playbook、活动待办、QG-021 spec、`docs/TESTING.md`、`scripts/test/test-local.sh`、`scripts/test/new_agents_functional.py`、`scripts/test/verification_outcomes.py`、`.github/workflows/deploy.yml`、`docker-compose.prod.yml`、`nginx/nginx.conf` 和真实模型 E2E runner。

- 当前分支为 `master`，相对 `origin/master` 领先 `2bcfe5d4`；该提交是本轮设计基线，尚未 push。
- 用户已有的 `tools/intent-tester/test-results/proxy/junit.xml` 修改与本轮无关。它不被读取、修改、暂存、清理或纳入任何提交。
- `test-local.sh all` 不是完整 pre-push 入口：它遗漏 CI 的 Intent coverage threshold、New Agents frontend lint/build、root runner/contract/deploy hardening 等，同时与 `new-agents-functional.sh inner` 重复前端、后端和 LiveStack。
- 真实 `release` 当前启动临时 Flask/Vite/SQLite LiveStack；它尚不验证 Docker、Gunicorn、Nginx、PostgreSQL、production build 或 Compose readiness。
- protected `master` push 仍会先后触发真实 release 与生产部署，因此远端不能作为首次真实部署/模型主链路验证。

这些缺口与 QG-021 设计一致，没有新事实要求改变已确认顺序或切片边界。

## 3. 风险、依赖与验收重核

`QG-021` 继续覆盖：一个 fail-closed canonical pre-push 命令、固定全仓技术与确定性跨层门禁、每项测试的唯一责任层、隔离 production-shaped Compose、部署栈上真实 DeepSeek 的 `release` 7 workflow/25 stage E2E、同一 `HEAD` 的脱敏证据与无污染清理。

依赖为本地 Docker/Compose、Node、Python、Chromium、`.env` 中已配置的真实模型参数和隔离的 loopback 端口/卷。缺失依赖、零收集、模型波动、超时、清理失败或事实变化都必须保持非 `PASS` 并阻止 push。

三个已确认的生产发布阻断风险（备份/回滚身份、先停服务再构建、线上 readiness 浅）仍然属于 `QG-022`。本轮只建立隔离的本地 production-shaped 验证与可诊断失败边界，不改变线上 rsync、切换、rollback 或生产部署流程。

## 4. 七项厚切片门禁

1. **入口**：开发者在任意 `git push` 前运行一个固定的本地命令。
2. **动作**：命令对当前 `HEAD` 执行完整、不可按 diff 缩减的验证。
3. **处理**：按唯一归属调度低层、跨层、Docker/Compose 和真实模型测试，收集每层结果。
4. **可见结果**：输出可读的 phase 结果和机器可读、脱敏的 evidence；只有全部 `PASS` 才给出可 push 判定。
5. **状态承接**：evidence 绑定 `HEAD` 与部署 target identity；任何代码、配置、依赖或测试产物变化使其失效。
6. **失败反馈**：依赖缺失、零收集、超时、波动、清理失败与断言失败都以非零、可定位原因停止，不降级成绿色。
7. **证据**：测试登记、runner 单测/故障 mutation、Compose build/up/readiness/restart、部署栈 release E2E 与最终全量运行共同覆盖。

相邻缺口共同构成同一调用方动作链，不能拆成多个完成项；QG-022 是独立的线上发布事务风险面，保留为下一厚切片。

## 5. 协作与旁路审查

本轮已使用三个只读并行审查结果，且均未写入用户 dirty 路径：

- `ci_deploy_audit`：核对 CI、部署与 production-shaped 缺口；结论被 QG-022 三个风险和 QG-021 本地部署边界吸收。
- `runner_coverage_audit`：核对 `all`/`inner` 的遗漏与重复，并确认真实 scope 矩阵。
- `prepush_research_doc`：产出已随 `2bcfe5d4` 提交的现状审计。

后续实现不派发 writer：canonical runner、共享测试入口和 Compose 相关文件高度耦合，且当前工作区存在必须保护的用户 JUnit 修改。主 Agent 负责集成、TDD、最终审查和全量证据；必要的只读审查在厚切片最终 diff 落定后按 Playbook 执行。

## 6. 承接结论

不存在新的 P0/P1、外部阻塞或顺序冲突。继续承接 `QG-021`，进入 `MILESTONE` 后以既有设计基线写一份只覆盖该厚切片的 implementation plan。计划中的 RED/GREEN 步骤均为内部实现步骤，不改变 `QG-021 → QG-022` 的能力包顺序，也不形成独立交付。
