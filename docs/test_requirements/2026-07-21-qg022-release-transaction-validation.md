# QG-022 可信生产发布事务验证记录

- 状态：`PENDING_FINAL_GATE`
- 验证对象：待创建的 QG-022 本地提交
- 固定门禁：`./scripts/test/pre-push.sh`
- 生产边界：不执行真实生产发布、不写入真实 production 配置、不推送 GitHub。

## 已实现的可审计契约

| 契约 | 证据位置 | 当前状态 |
| --- | --- | --- |
| SHA 与内容摘要绑定、拒绝 symlink/upload 越界 | `tests/test_release_transaction.py` | 定向 PASS；等待全量门禁 |
| 可信 previous、锁、预检先于切换 | `tests/test_release_transaction.py` | 定向 PASS；等待全量门禁 |
| image/config/env identity 与 profile-aware rollback | `tests/test_release_transaction.py` | 定向 PASS；等待全量门禁 |
| 页面、backend、DB JSON、typed SSE、PostgreSQL 临时读写 readiness | `tests/test_release_transaction.py`、`tools/new-agents/backend/tests/test_readiness_endpoint.py` | 定向 PASS；等待全量门禁 |
| immutable release CI handoff、禁止旧 production bypass | `tests/test_ci_deploy_hardening.py` | 定向 PASS；等待全量门禁 |
| 本地 production-shaped Docker 与真实模型 release E2E | `scripts/test/pre-push.sh` | 待执行 |

## 完成条件

只有在隔离、干净检出中对最终提交运行固定全量门禁并全部 PASS 后，才可将本记录、活动待办和 Goal Mode 状态标为完成。该门禁的实际 HEAD、时间、phase 结果和清理状态将在通过后填写；失败不会被本记录覆盖。
