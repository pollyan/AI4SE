# QG-022 可信生产发布事务验证记录

- 状态：`PASS`
- 验证对象：QG-022 本地提交 `448b5f0c` 与真实模型流转修复 `ddd4efcd`
- 固定门禁：`./scripts/test/pre-push.sh`
- 生产边界：不执行真实生产发布、不写入真实 production 配置、不推送 GitHub。

## 已实现的可审计契约

| 契约 | 证据位置 | 当前状态 |
| --- | --- | --- |
| SHA 与内容摘要绑定、拒绝 symlink/upload 越界 | `tests/test_release_transaction.py` | PASS |
| 可信 previous、锁、预检先于切换 | `tests/test_release_transaction.py` | PASS |
| image/config/env identity 与 profile-aware rollback | `tests/test_release_transaction.py` | PASS |
| 页面、backend、DB JSON、typed SSE、PostgreSQL 临时读写 readiness | `tests/test_release_transaction.py`、`tools/new-agents/backend/tests/test_readiness_endpoint.py` | PASS |
| immutable release CI handoff、禁止旧 production bypass | `tests/test_ci_deploy_hardening.py` | PASS |
| 本地 production-shaped Docker 与真实模型 release E2E | `scripts/test/pre-push.sh` | PASS（7 workflow / 25 stage / 18 transition） |

## 实际全量门禁证据

- 2026-07-21，在隔离、干净检出中执行 `./scripts/test/pre-push.sh`：preflight、static、deterministic、deployment、real_e2e、finalization 全部 `PASS`。
- `real_e2e` 的最终证据覆盖 7 个 manifest workflow、25 个 stage 与 18 次 transition；真实无头浏览器经 Nginx、New Agents frontend/backend、typed SSE、PostgreSQL 和真实配置的模型运行。
- 全量门禁完成后，临时 Docker Compose project、临时凭据文件和隔离工作区均已清理；没有真实 production 发布、GitHub push 或凭据输出。
- 本轮最初一次真实 E2E 曾失败于中间阶段的模型结构化/流转一致性；修复共享运行时的确定性确认动作与第三次结构化重试后，重新运行固定全量门禁获得上述 PASS。该首失败没有被省略或重新标记为 PASS。
