# QG-022 目标承接检查

- 日期：2026-07-21
- Goal Mode 状态：`BOOTSTRAP → ASSESS → MILESTONE`
- 结论：`CONTINUE QG-022`
- 顺序基线：[历史待办 QG-021 → QG-022](../../todos/archive/2026-07-21-pre-push-full-validation-and-release-safety.md)
- 厚切片身份基线：[QG-022 设计](../specs/2026-07-21-qg022-trusted-production-release-design.md#厚切片身份基线)

## 1. 已确认顺序与上一轮证据

用户已确认按 `QG-021 → QG-022` 顺序消化活动待办，且授权在当前仓库内自主完成设计、实现、验证和本地提交，但未授权 push 或真实生产发布。`QG-021` 已完成：隔离检出的 canonical `./scripts/test/pre-push.sh` 对 7/7 workflow、25/25 stage、18 次阶段推进及全部固定质量门给出 PASS；临时 Docker project、凭据文件和工作区已清理。该结论记录在活动待办与 [QG-021 验证记录](../../test_requirements/2026-07-21-qg021-validation-record.md)。

`QG-022` 是唯一下一入口。它不是 QG-021 的补丁：它改变的是 GitHub 到单主机生产环境的 release transaction、回滚身份和线上 readiness 信任边界。

## 2. 当前事实、工作区与风险

重新读取了 `AGENTS.md`、Goal Mode Playbook、活动待办、`.github/workflows/deploy.yml`、`scripts/ci/deploy.sh`、`scripts/health/health_check.sh`、`docker-compose.prod.yml`、`nginx/nginx.conf`、New Agents backend routes，以及 QG-021 production-shaped deployment tests。

- 当前分支为 `master`，QG-021 的本地提交尚未 push。用户已有的 `tools/intent-tester/test-results/proxy/junit.xml` 修改仍与本轮无关；不读取、修改、暂存、清理或纳入提交。
- workflow 以固定 `/opt/intent-test-framework-upload-tmp` 接收包，随后在远端先执行 `rsync -a --delete ... /opt/intent-test-framework/`；因此旧 live source 已被覆盖，之后 `deploy.sh` 创建的 backup 不能代表上一 release。
- `deploy.sh production` 在 Docker build 前执行 Compose `down`，并按宽泛名称模式删除容器和 network；构建、拉取或启动失败会先造成停机，且与并发发布相互破坏。
- release 没有 SHA/内容摘要/image-id/config 摘要组成的 immutable identity；rollback 只 rsync 文件并 `up -d`，不验证旧镜像、配置或服务身份。
- `health_check.sh` 依赖静态 `/health`、硬编码容器名和浅 `/new-agents/api/health`；页面清单没有 `/new-agents/`，也没有数据库经 New Agents、网关 upstream、SSE transport、失败回滚后的复验。

三个 P0 风险均是 QG-022 已确认范围，没有发现应改变用户顺序的新风险。首次 adoption 的既有 live 目录没有可验证 release identity；把它伪装为可回滚版本会违反目标，因此 migration 必须 fail-closed 并要求运营者先提供可信基线。

## 3. 厚切片与七项门禁

本轮是一个工程信任厚切片：开发者从 protected GitHub SHA 触发生产发布，候选 release 在不影响当前服务时完成身份校验、构建与预检；受 lock 保护的切换后，系统对真实 gateway、New Agents 页面、DB 和 SSE readiness 作出判定；任何失败以已冻结的上一 release identity 恢复，并机械核验恢复。它不能按“备份”“构建”“健康检查”拆成多个完成项，因为它们共同决定一次发布是否可信。

1. **入口**：`deploy-to-production` 的受保护 `master` SHA 或受控手动 release。
2. **动作**：上传带 SHA/内容摘要的候选包，由远端 release transaction 执行 prepare、activate、verify 或 rollback。
3. **处理**：不可变 release 目录、私有 release env、image/config identity、文件锁和唯一 Compose project 统一承接。
4. **可见结果**：事务写出不含凭据的 release state，GitHub job 只报告 SHA、phase 和安全原因；active `current` 指针与运行 image 均可检查。
5. **状态承接**：只有 readiness 全部 PASS 才把 candidate 记为 active；失败把 `current`、Compose 工作目录、image/config identity 一并恢复到 previous。
6. **失败反馈**：无可信 previous、manifest 不匹配、并发锁、构建/预检/切换/readiness/rollback 任一失败均非成功，且不得广泛删除资源。
7. **证据**：事务单元/故障 mutation、workflow/compose 静态合同、New Agents readiness endpoint 与本地 Docker release simulation；最终由固定全量 pre-push 验证。

纳入：release identity、staging、lock、build-before-switch、activation/rollback、readiness、GitHub 交接与部署文档。排除：真实线上执行、零停机双栈/流量分割、数据库 schema migration framework、LLM 产出物 judge 和改变 Agent 工作流。

## 4. 方案比较与选择

| 方案 | 优点 | 不足 | 结论 |
| --- | --- | --- | --- |
| 在现有 live rsync / `deploy.sh` 上增加更早 backup | 修改小 | 仍原地覆盖、无法证明 image/config 身份，仍会先停服 | 不采用 |
| 完整 blue/green 双 Compose stack | 可降低切换停机 | 需要独立端口、数据库写入策略、Nginx traffic switch 和 migration 协议，超出单主机当前拓扑 | 不采用 |
| 不可变 release 目录 + 单 Compose 受控切换 | 先构建预检、previous identity 可验证、失败精确恢复、可逐步迁移 | 切换时仍有短暂受控重建，首次 adoption 需可信基线 | 采用 |

## 5. 协作与审查决策

本轮的 release transaction、Compose contract、GitHub workflow、后端 readiness 和故障测试共享一个安全契约，不能由多个 writer 并行修改。当前执行环境的协作模式禁止主动派发子智能体；因此记录为“子智能体环境降级”，由主 Agent 串行完成设计、TDD、diff 复核和最终审查。允许路径限定为生产部署、New Agents readiness、相应测试与文档；禁止触碰用户的 JUnit 文件。

## 6. 承接结论

进入 `DESIGN`。推荐方案以不可变 SHA release 目录和 manifest 为唯一 identity，拒绝把未知旧 live 目录伪装成可恢复 release；候选 build/preflight 在切换前完成，切换与 rollback 由同一事务和 lock 管理，readiness 从 gateway 到 DB/SSE 形成可执行证据。
