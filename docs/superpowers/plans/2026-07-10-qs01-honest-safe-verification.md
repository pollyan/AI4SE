# QS-01：诚实且不伤数据的验证结果实施计划

对应设计：`docs/superpowers/specs/2026-07-10-qs01-honest-safe-verification-design.md`。

## 文件所有权与边界

本轮可修改 `scripts/test/**`、`.github/workflows/deploy.yml` 中的 verification gate、`tools/intent-tester/backend/app.py`、`tools/intent-tester/tests/**`、必要的根测试、`docs/TESTING.md`、`docs/index.md`、`README.md` 和 owning todo。不得修改 `.env`、默认 Intent 数据库、部署环境、生产 secrets、New Agents runtime 或无关 UI。

## 实施顺序

1. **测试数据库先行（RED）**
   - 新增 factory isolation 测试：初始化前 override 生效、memory engine 一致、file/PostgreSQL URI 在 engine 创建前拒绝、sentinel 不变。
   - 在测试 fixture 中只通过 `create_app(test_config)` 创建 app；禁止 post-init 修改 SQLAlchemy URI。

2. **测试数据库最小实现（GREEN）**
   - 为 Intent `create_app` 增加初始化前 config override。
   - 在 TESTING 路径验证唯一允许的内存数据库 URI，再执行 `db.init_app` 和 `create_all`。
   - 保持生产配置路径不变，fixture teardown 仅操作已验证 engine。

3. **验证 outcome 契约（RED）**
   - 为 runner outcome 定义可测试模型与 JSON 记录格式：`suiteId`、`status`、`collected`、`executed`、`skipped`、`reason`。
   - 覆盖正常 PASS、child failure、zero collection、skip-only、tool error、timeout、smoke required env 缺失；每种非 PASS 均断言父进程非零。

4. **runner/CI 最小实现（GREEN）**
   - 让 `test-local.sh` 使用 outcome 适配器汇总，移除 smoke 的静默成功。
   - 修正 Jest 单数 selector 并去掉 `--passWithNoTests`；为 CI 使用相同的零收集语义。
   - 使 `check-docs.sh` 的 child-tool error 可见且非 PASS，不在本轮重做其跨平台链接解析。

5. **文档与回归**
   - 更新测试策略/入口文档，精确区分 PASS、NOT_RUN、BLOCKED 与外部 smoke 范围。
   - 先跑新增聚焦测试；随后在显式安全 DB 配置下跑 Intent pytest，核查默认本地库未变化；运行 runner/CI 静态契约、关键 lint、`git diff --check`。
   - 将实际结果、未运行外部 judge 与本地库恢复边界写回 owning todo。

## 验证与交付边界

- 聚焦：factory isolation、outcome contract、runner/CI command tests。
- 必要跨层：安全 DB 配置下的 Intent pytest 与正常 proxy suite；不启动真实 provider、浏览器或生产容器。
- CI 等价：检查 `.github/workflows/deploy.yml` 不再允许 proxy 零收集成功，并记录本地对应 command。
- 提交：QS-01 代码、测试、稳定文档、todo 状态和本轮 spec/plan 一次聚焦提交；生成 XML、默认 DB、缓存和外部结果不得暂存。
