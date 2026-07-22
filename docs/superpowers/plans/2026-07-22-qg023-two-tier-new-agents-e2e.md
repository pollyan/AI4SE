# QG-023：New Agents 双层 E2E 收口实施计划

> 内部实现步骤，不是独立切片、提交或交付。用户已确认本计划的目标架构；整个计划完成后只交付 QG-023 一个工程信任闭环。

## 文件所有权

| 范围 | 责任 |
| --- | --- |
| gate registry 与其单测 | `scripts/test/pre_push.py`、`tests/test_pre_push_gate.py` |
| deterministic live journey 与 observer contracts | `tests/e2e/new_agents_real/test_deterministic_live_stack.py`、`test_live_stack_contracts.py` |
| 本地 / CI 调用 | `scripts/test/test-local.sh`、`.github/workflows/deploy.yml` 与对应 contract tests |
| 分层说明与 active todo | `docs/TESTING.md`、`docs/todos/refactor/**`、本 spec |

## 实施步骤

1. **冻结 gate 语义（RED）**
   - 修改 `tests/test_pre_push_gate.py`，断言 registry 只有 `new-agents-deterministic-e2e`，其命令顺序包含 browser workflow suite 和新的两阶段 live tracer；旧独立 suite ID 不得出现。
   - 对 `test-local.sh` 和 CI 增加源级漂移断言，确保二者调用同一新路径，并继续明确 headless Chromium。
   - 运行这些测试，记录预期失败。

2. **收口真实服务链路 tracer（RED → GREEN）**
   - 新增 `test_deterministic_live_stack.py`，将原两条 journey 合并为一条 `CLARIFY → STRATEGY` 测试：同一 `LiveStack` 完成 forged config 拒绝和两阶段用户旅程的全部交叉边界断言。
   - 先运行新用例获得因文件/实现未完成造成的 RED，再复用既有 fake provider、LiveStack 和 workflow runner adapter 实现最小 GREEN。
   - 删除旧文件中的两条 journey，避免同一服务链路被重复收集。

3. **下沉非 E2E observer/helper 用例**
   - 将余下 16 个顶层测试不改断言地迁入 `test_live_stack_contracts.py`；保留 `pytest.mark.e2e` 仅在实际 Chromium 依赖仍需该环境标记时，suite ownership 归到 evidence level 2 的 contracts。
   - 删除空的旧 `test_live_stack.py`，或仅在有必要的共享 fixture 情况下将共享代码移至非测试 helper；不得留下重复收集路径。
   - 运行新 contract 文件与新 live tracer，确认 collected 数等于迁移前 18 个用例且只有一个 service journey tracer。

4. **收口调用入口与文档**
   - 修改 `fixed_suites()`：唯一 deterministic New Agents E2E suite 运行 browser + live tracer；`new-agents-real-contracts` 纳入 observer contract 文件。
   - 修改 local e2e、CI deterministic job 和 `docs/TESTING.md`；保留 separate pytest process 的 Playwright 生命周期隔离。
   - 从 canonical registry 重新生成 checked-in suite ownership 文件，并用同步测试阻止漂移。

5. **审查与验证**
   - 运行 RED/GREEN 相关 pytest，随后 `tests/e2e/new_agents_browser`、new live tracer、contracts、pre-push/CI contract tests 与相关 frontend/backend tests。
   - 检查 diff，确认没有 secret、用户已有 dirty JUnit 或无关文件；进行本轮正式代码审查，关闭 Critical/Important 问题。
   - 在隔离 clean worktree 对最终 `HEAD` 运行 `./scripts/test/pre-push.sh`；任何 NOT_RUN、BLOCKED、TIMEOUT、FLAKY、零收集或 cleanup failure 都回到实现，不允许以局部结果交付。
   - 更新 active todo 为完成证据并按 Goal Mode 归档，精确 stage 本轮文件并创建聚焦本地 commit；不 push，除非用户明确要求。

## 完成条件

- 两道且仅两道 New Agents E2E 门禁的职责、命令和报告名称一致。
- 浏览器受控坏路径、真实 service-chain 两阶段旅程、真实 DeepSeek release 三类独有覆盖均仍存在。
- pre-push、local、CI、文档和 generated ownership view 不漂移。
- 当前 `HEAD` 固定全量 pre-push PASS，且不触碰用户已有 `tools/intent-tester/test-results/proxy/junit.xml`。
