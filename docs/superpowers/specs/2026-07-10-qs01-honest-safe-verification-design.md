# QS-01：诚实且不伤数据的验证结果设计

## 目标模式评估

- 事实版本：`15a388d3e75895a07f7284041ec52d3897a623a6`
- owning todo：`docs/todos/2026-07-10-ai-coding-test-quality-improvement.md`（当前未跟踪，启动前已有）
- 当前厚切片：`QS-01`
- 承接风险：`QG-001`、`QG-002`

本轮完成完整 CGA，而非沿用旧计划。当前仍存在三个可复现的假绿路径：缺少真实 LLM smoke 配置时 runner 返回 0；Jest 使用 `--passWithNoTests` 时零收集返回 0；`check-docs.sh` 吞掉 BSD `grep -P` 错误后返回 0。Intent Tester 的 fixture 则在 app 已绑定默认或环境数据库后才覆写配置，teardown 的 `drop_all()` 可能清空非测试库。

候选排序如下：

1. **QS-01（推荐）**：使验证 verdict 可信且测试数据库隔离。这是所有后续代码、judge 和 CI 证据的前置工程信任闭环。
2. **QS-02**：收口 Shared Agent Runtime 的持久化与终态协议；它依赖 QS-01 的可信测试执行环境。
3. **QS-06**：当前 77/80 的 judge 失败仍是 P0，不能忽略；但其外部 verdict 依赖 QS-01，且 QS-06 明确依赖 QS-01/QS-02。保留为下一阶段候选，不在本轮调用外部模型。

`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` 顶部声明 P0/P1 已收口，现有新 todo 将其归入 QS-08 的待收口治理；本轮不恢复其中历史实现。旧 `goal-mode-cga-template.md` 已被当前 Playbook 正式退役，故本文件按 Playbook 内置 CGA schema 记录。

## 厚切片门禁

| 门禁 | QS-01 结论 |
| --- | --- |
| 入口 | AI Coding Agent、开发者或 CI 运行本地验证入口。 |
| 动作 | 选择并运行一个验证 gate，或启动 Intent Tester 测试 app。 |
| 处理 | runner 显式区分 PASS/FAIL/NOT_RUN/BLOCKED/TIMEOUT；app factory 在数据库初始化前接收测试配置并验证隔离 URI。 |
| 可见结果 | 机器可读 outcome 与非零退出；测试数据库绑定证据；非测试 URI 被明确拒绝。 |
| 状态承接 | CI/Agent 可消费 outcome，测试 fixture 只清理已验证的内存数据库。 |
| 失败反馈 | 缺配置、零收集、工具错误、子命令失败和不安全数据库 URI 都保留具体原因，不能伪装为绿色。 |
| 证据 | 故障矩阵、Jest 零收集、child-tool failure、factory engine/sentinel 测试和聚焦回归。 |

相邻的 runner 与 test-app 路径共同解除“运行验证会误导或伤害数据”的用户可感知风险，因此同属一个工程信任闭环；不纳入 Intent execution、访问安全、部署、judge 或命令图治理。

## 方案比较与裁决

### 方案 A：只删除几个软失败选项

移除 `--passWithNoTests`、把 smoke 缺配置改为 `return 1`、删除 `|| true`。改动很小，但各 gate 的含义仍分散在 shell 分支中，无法让 CI/Agent 稳定读取状态、收集数和原因。

### 方案 B：结果契约适配层 + 安全 app factory（采用）

为本地 runner 建立可独立测试的 outcome 模型/输出约定，并由 shell 仅负责调用与汇总。每个 gate 输出 suite ID、状态、计数和原因；零收集、skip-only、工具错误、缺配置、超时和 child failure 不能成为 PASS。Intent app factory 接收初始化前的测试 override，测试模式仅接受显式 `sqlite:///:memory:`。

这保留现有 shell 入口和 CI 拓扑，同时把判断逻辑压缩到可测试的边界，是最小可验证方案。

### 方案 C：立即重做全仓命令图和 CI

可一次处理所有本地/CI 差异、cache、UI ownership 和 docs portability，但会吞并 QS-07/QS-08，无法形成 QS-01 的独立交付与回滚边界，因此拒绝。

## 架构与数据流

```text
测试请求
  -> test-local.sh / CI gate adapter
  -> child framework command
  -> outcome contract {suiteId, status, collected, executed, skipped, reason}
  -> JSON summary + process exit

pytest fixture
  -> create_app(test_config)
  -> validate TESTING + memory-only URI
  -> db.init_app / create_all
  -> fixture cleanup on the same verified engine
```

`PASS` 只表示目标测试被收集并执行且满足通过条件。缺少真实 smoke 配置是 `NOT_RUN` 或 `BLOCKED`，可以作为外部资格状态记录，但不得进入“完整验证已通过”的汇总；本轮不把它变成每次 CI 的外部硬依赖。Jest 不再允许零收集通过。文档检查发生工具错误时必须返回非 PASS；BSD/macOS portability 的正确实现仍由 QS-08 owning。

测试 app 的安全边界是：`TESTING=True` 时必须在 `db.init_app()` 前传入精确的内存 SQLite URI；文件 SQLite、PostgreSQL、默认 URI 和环境 URI 都在打开 engine 前拒绝。生产 app 的正常数据库配置不改变。

## 失败路径与非目标

- outcome 写入失败、未知 child 结果、无收集或超时：显式非 PASS 和非零退出，保留首个原因。
- 非隔离测试 URI：factory 抛出可诊断错误，不创建 schema、不清理任何外部数据库。
- 不恢复扫描时已可能受影响的本地数据库；恢复策略由用户另行决定。
- 不修 Intent 执行 identity、XSS/认证、Shared Agent Runtime、发布拓扑、真实 provider judge 或 QS-08 的完整文档可移植性。

## 测试设计与质量门

1. 先以 RED 测试锁定 factory 必须在数据库初始化前应用配置、拒绝 file/PostgreSQL URI，并用 SQLite sentinel 证明拒绝路径不改变外部 schema 或数据。
2. 以 RED 测试锁定 smoke 缺配置、Jest 零收集、模拟 child-tool error/timeout 均不能获得 PASS；正常 child PASS 保持绿色。
3. GREEN 后运行 Intent factory 聚焦测试、runner contract 测试、现有安全的 proxy/Jest 目标和文档一致性检查。
4. 不在修复前运行完整 Intent pytest；修复后只在强制内存 URI/安全 fixture 下运行它，并记录默认 `instance/local.db` 未被打开或修改的证据。
5. 更新 `docs/TESTING.md` 等 owning 文档，明确 smoke 和外部验证的状态边界；验证 `git diff --check`、关键 Python lint 和与 diff 对应的 CI 静态契约。

## 自检

本设计没有 TODO/占位项；QS-01 的 DB 安全与结果真实性均有唯一 owner，外部 smoke 与 judge 的非 PASS 语义没有被改写为 PASS；未承诺 QS-07/QS-08 的命令图、缓存或 portability 工作。
