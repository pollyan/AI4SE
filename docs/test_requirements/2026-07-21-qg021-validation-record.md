# QG-021 固定全量 Pre-push 验证记录

- 验证对象：运行命令时的当前 Git `HEAD`。
- 唯一命令：`./scripts/test/pre-push.sh`（Git hook 同样只调用该命令）。
- 证据目录：Git ignored 的 `test-results/pre-push/<HEAD>/summary.json` 与受控的 `real-e2e/` 脱敏报告。

## 通过判定

提交只有在该 `HEAD` 的 summary 中所有固定 phase 都为 `PASS` 时才可推送：`preflight`、`static`、`deterministic`、`deployment`、`real_e2e`、`finalization`。任何 `FAIL`、`BLOCKED`、`NOT_RUN`、`TIMEOUT` 或 `FLAKY` 均禁止推送；重跑不能覆盖首次失败，而应作为新的诊断证据。

## 真实环境要求

验证会创建随机命名、仅 loopback 可访问的 production-shaped Compose 栈，检查 New Agents 页面、后端健康接口和 PostgreSQL，并在部署的栈上执行真实模型 `release`：manifest 派生的 7/7 workflow、25/25 stage 和 18 次阶段推进。临时 Docker project、volume、network、私有环境文件和系统临时子工作区必须在 `finalization` 前清理。

报告不得包含 API key、provider URL、管理员或代理凭据、完整 prompt、浏览器 storage、截图或原始子进程日志。固定 runner 将 child build/JUnit/coverage 放入系统临时目录，只有脱敏的最终 evidence 留在上述 Git ignored 目录。
