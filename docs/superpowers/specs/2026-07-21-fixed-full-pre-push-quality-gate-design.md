# QG-021 固定全量 Pre-push 质量门禁设计

- 日期：2026-07-21
- 状态：已批准；2026-07-21 Goal Mode 实施完成，待最终 `HEAD` 的固定全量门禁
- Owning todo：[`QG-021`](../../todos/2026-07-21-pre-push-full-validation-and-release-safety.md#qg-021--固定全量-pre-push-质量门禁与测试去重)
- 事实审计：[`本地提交 / 推送前验证审计`](../../test_requirements/2026-07-21-pre-push-local-validation-audit.md)
- 顺序基线：`QG-021 → QG-022`；本设计只覆盖第一项

## 厚切片身份基线

本厚切片建立一个固定、失败关闭、可审计的本地 pre-push 工程信任闭环：任何变更在 push 到 GitHub 前，都必须通过同一套全量质量门禁，不允许由 Agent、开发者或 diff 分类器判断“本次可以少跑哪些测试”。开发过程仍可运行聚焦测试获得快速 RED/GREEN，但聚焦结果不能替代 push 前全量结果。

“全量”表示完整覆盖仓库约定的系统不变量和主干用户流程，不表示把现有所有重复测试机械串联。实现必须先为每项不变量确定唯一主要责任层，再合并、下沉或删除重复、无效和低效率测试；去重不得降低覆盖范围。最终由一个统一入口按便宜到昂贵的顺序运行全仓静态门禁、单元/API/模块与契约测试、必要的确定性跨层测试、本地生产形态部署，以及部署栈上的真实 DeepSeek 无头 E2E。

本轮交付边界是“统一门禁、覆盖归属、真实部署 E2E 与失败关闭”全部可用，并用当前 `HEAD` 的新鲜全量证据证明。测试文件盘点、runner 重构、部署栈 target 模式、文档与门禁测试都是内部实现步骤，不得拆成独立完成进度或单独交付。

## 1. 用户决定与设计原则

2026-07-21 用户明确决定：

1. 全量门禁作用于每次 push 到 GitHub 前，而不是每个本地 `git commit`。
2. pre-push 范围固定，不依据 diff、路径或模型影响分析缩减；文档改动也不例外。
3. 效率问题通过测试分层、职责归属和去重解决，不能通过预测影响面后少跑测试解决。
4. 除高效率的单元、API、模块和契约测试外，用户主干链路优先由真实环境、尽量少 mock 的无头 E2E 保障。
5. 重点验证格式、流式、阶段流转、持久化、恢复、鉴权与部署可用性；不建立截图或像素级门禁。
6. 当前三个生产发布阻断风险进入后续 `QG-022`，本轮只为其保留可诊断边界，不在 QG-021 中顺手修复。

## 2. 当前事实与缺口

### 2.1 现有本地入口不是完整全量门禁

- `./scripts/test/test-local.sh all` 已覆盖 Intent Python、Intent critical lint、proxy Jest、Common frontend lint/build、New Agents frontend/backend、mock-browser E2E 和 deterministic LiveStack。
- 默认 `all` 仍漏掉 QG-020 runner/contracts、CI/deploy hardening、outcome parser 和 judge 单测等 root 门禁；New Agents frontend 也没有在该入口内执行 typecheck 与 production build。
- `./scripts/test/new-agents-functional.sh inner` 补 runner/contracts，却重复执行 frontend、backend 和 LiveStack，且不运行完整 mock-browser E2E。
- 两个入口均可能安装依赖或生成 coverage、dist、JUnit 等文件，不能保证从干净 checkout 自举后仍保持工作区无污染。

### 2.2 当前 E2E 证据分散且存在重复

- mock-browser E2E 使用真实 Vite/Chromium，但替换 Agent stream、snapshot、handoff 和 config API，适合精确 UI 状态断言，不证明真实服务链路。
- deterministic LiveStack 使用真实 React/Vite、Flask、SQLite、typed SSE 和 Chromium，但不经过 Docker、Nginx、Gunicorn 或 PostgreSQL。
- real functional runner 使用真实 DeepSeek 和同一 LiveStack，`release` 覆盖 7 个 workflow、25 个 turn 和 18 次阶段推进，但仍不证明生产形态部署。
- Nightly 的 25 个独立 stage probe 与 Release 的 25 个顺序 turn 都有价值，但前者主要用于模型漂移和独立阶段诊断，不应作为 pre-push 的第二份同义全量旅程。

### 2.3 GitHub push 是发布边界

当前 protected `master` push 会运行真实模型 `release`，并在门禁通过后自动部署生产。远端不能成为第一次真实模型、容器或主干链路验证。pre-push 证据必须绑定即将推送的 `HEAD`；测试后任何代码、配置、依赖或生成物变化都会使证据失效。

## 3. 方案比较与决定

### 3.1 方案 A：机械执行所有现有测试

优点是无需先整理测试；缺点是 frontend、backend、LiveStack、workflow journey 和契约测试大量重复，耗时不可控，测试产物污染和失败归因都会恶化。重复数量增加并不等于风险覆盖增加。

### 3.2 方案 B：以真实 E2E 取代大部分低层测试

优点是链路真实；缺点是模型和外部网络存在波动，异常分支、组合边界和故障注入成本过高，失败定位慢。真实 E2E 不适合穷举 schema、鉴权、协议损坏、超时和状态机非法输入。

### 3.3 方案 C：固定全量门禁、分层归属、真实 E2E 收口（采用）

每次 pre-push 固定运行同一套覆盖面。单元/API/模块层穷举技术边界；确定性跨层层证明协议和故障路径；部署后的真实 DeepSeek 无头 E2E 证明完整用户主干。每项不变量只有一个主要责任层，高层只断言跨层结果，不复制低层内部细节。

## 4. 统一 Pre-push 执行模型

统一入口暂定为：

```bash
./scripts/test/pre-push.sh
```

外部只理解“运行当前 `HEAD` 的固定全量门禁”。内部执行顺序固定如下。

### 4.1 Phase 0：环境、身份与工作区前置检查

- 记录 `HEAD`、branch、upstream、Python/Node/npm/Docker/Compose/Chromium 版本。
- 检查仓库虚拟环境、lockfile 对应依赖、Docker daemon、真实模型三个变量和本地部署必需变量。
- 清除可能让确定性测试误调用 judge 的环境变量；真实 key 只进入 backend/test 进程，不进入浏览器、报告或命令输出。
- 记录启动前 dirty/staged ownership；已知无关 dirty 文件不得被读取、修改、暂存或作为失败清理对象。
- 任一必需工具、凭证或 Docker 能力缺失都返回 `BLOCKED` 和非零退出，不降级或跳过。

### 4.2 Phase 1：全仓静态、构建和确定性技术门禁

固定包含：

- 全仓关键 Python lint/format 与 shell/YAML/JSON/Compose 静态检查。
- Common frontend lint 和 production build。
- New Agents frontend typecheck、Vitest 全量和 production build。
- Intent Python 全量及当前 CI coverage threshold、proxy Jest。
- New Agents backend `not slow` 全量。
- root runner/contracts、verification outcome、CI/deploy hardening 和 judge parser 单测。
- 文档一致性、`git diff --check`、secret/staged 文件扫描。

不得使用 `npm install`、系统 Python fallback、测试零收集或“失败后换解释器重跑”为绿色路径。依赖环境不满足时先失败并给出准备命令。

### 4.3 Phase 2：确定性跨层与故障注入

保留真实 frontend/backend/HTTP/SSE/数据库/无头 Chromium 的确定性组合，用可控外部 provider seam 覆盖：

- chat 先于 artifact、段落增量单调、最终收敛。
- typed SSE 事件顺序、断流、非法事件、retry 与错误诊断。
- `runId` 复用、消息与 artifact version 持久化、刷新恢复、合法和非法阶段推进。
- provider/schema/renderer/auth/config/timeout 等需要精确触发的失败路径。

该层使用替身只允许控制真实外部依赖或故障，不允许替换被验收的本仓库 frontend、backend、transport、store、数据库适配和浏览器行为，也不能生成假成功。

### 4.4 Phase 3：本地生产形态部署

用隔离 project name、端口和临时持久化数据执行 production-shaped：

1. Compose render 与必需变量校验。
2. production Dockerfile/image build。
3. PostgreSQL、Gunicorn、生产前端、Nginx 和所需服务启动。
4. readiness 检查所有目标容器、真实上游和页面，而非只验证 Nginx 固定 `200`。
5. 验证 `/new-agents/`、`/new-agents/api/*`、SSE buffering/header、配置鉴权、数据库读写和进程重启恢复。

QG-021 只需建立安全隔离的本地部署验证入口，不在此阶段改造生产 rsync、原子切换或 rollback；这些属于 QG-022。

### 4.5 Phase 4：部署栈上的真实 DeepSeek 无头 E2E

真实 `release` 不再另起 Vite/Flask/SQLite LiveStack 作为 pre-push 发布证据，而是能以 target/base URL 模式访问 Phase 3 已部署的 production-shaped 栈。固定覆盖 manifest 派生的 7/7 workflow 与 25/25 stage，并验证：

- `AgentTurnOutput`、`artifact_data` 和最终 Markdown 合法。
- 每个 turn 都有自然对话与至少两个不同的有效 artifact 增量；DOM 顺序为 chat 后 artifact。
- artifact 业务段落单调增长、元信息不抢首屏、最终 DOM 与服务端 snapshot 一致。
- 仅 immediate-next stage 可推进，7 个 workflow 都复用稳定 `runId` 并完成全部阶段。
- message、artifact、version、structured data、context summary 与 metric 持久化；清空本地缓存并刷新后可恢复。

不做截图、录像或像素比较。真实 provider 内部允许产品代码规定的有限 schema retry，但测试 harness 不做 retry-to-green；同一事实版本结果不一致记为 `FLAKY` 并阻止 push。

### 4.6 Phase 5：证据、清理与 push 裁决

- 每个 phase 输出结构化状态、收集数、执行数、耗时和首个失败；`PASS` 必须实际执行且满足阈值。
- 总报告记录 `HEAD`、suite 版本和 deployment target identity，但不记录 API key、完整 prompt、原始日志、浏览器 storage 或截图。
- 所有运行产物进入 Git ignored 的隔离目录；runner 不覆写 tracked JUnit、dist 或 coverage 文件。
- 清理测试容器、网络、临时 DB 和密钥文件，再次核对工作区相对启动前没有新增污染。
- 只有全部固定 phase 对同一 `HEAD` 为 `PASS` 时才允许 push。`NOT_RUN`、`BLOCKED`、`TIMEOUT`、`FLAKY`、零收集或清理失败都返回非零。

## 5. 测试去重与迁移规则

### 5.1 不变量归属表

在删除测试前，必须为所有现有 suite 建立机械可审计登记：测试 ID/文件、保护的不变量、证据层级、是否 mock、外部依赖、耗时、副作用、主要责任层和唯一价值。每项系统不变量必须有一个主要 owner；其他层只能保留独有的跨层或诊断价值。

### 5.2 KEEP / MOVE / MERGE / DELETE

- `KEEP`：当前层最便宜且最精确地保护唯一风险。
- `MOVE`：断言有效，但位于成本或真实性不合适的层；先在目标层建立等价失败证据再迁移。
- `MERGE`：多个 runner 重复收集同一 suite，统一由 canonical phase 调用一次。
- `DELETE`：完全重复、只验证 mock 自身、永远不失败或已被更强且更便宜证据覆盖；删除前必须用 mutation 或历史缺陷证明替代门禁会失败。

不得预设删减比例或为了达到耗时目标删除独有覆盖。先建立新门禁，再逐批迁移和删除，每批都运行固定全量 pre-push 证明覆盖没有退化。

### 5.3 各层职责

- 单元/API/模块/契约：负责大量输入组合、异常、schema、权限和状态机边界，允许在明确边界替换外部依赖。
- 确定性跨层：负责真实本仓库组件协作、精确时序和故障注入，不承担自然语言质量。
- 真实部署 E2E：只负责完整用户动作、跨层结果和真实 provider/部署事实，不重复内部函数、CSS 或逐字段实现断言。
- Nightly：保留 25 个独立 stage probe，用于模型随时间漂移、单阶段诊断和波动监测；它不是 pre-push Release 的重复硬门禁。

## 6. 性能与稳定性边界

- 固定顺序必须 fail-fast：便宜、确定性层先于 Docker 和真实模型，避免已知低层失败时继续消耗模型额度。
- 目标总耗时为 20–35 分钟，但这是优化目标，不是删减覆盖的理由；各 phase 有显式 timeout 和结构化超时状态。
- 同一 suite 在一次 pre-push 中只执行一次。canonical runner 测试必须能发现重复 test ID、嵌套调用造成的重复收集和意外外部调用。
- 从干净 checkout 运行时，准备失败必须明确可诊断；不得在测试过程中隐式修改依赖锁、全局 Python/npm 环境或 tracked 文件。

## 7. 安全、数据与失败处理

- 真实模型、配置管理员、运行时代理和数据库凭证分别注入最小进程，禁止进入前端 bundle、browser env、测试标题或报告。
- 报告写盘与上传前递归扫描 key/token/password/authorization 等字段和值；发现疑似凭证立即失败并禁止保留报告。
- 本地 production-shaped 栈只绑定 loopback，使用隔离数据库和临时容器命名空间，不连接生产数据库、主机目录或生产凭证。
- 首次失败必须保留；重跑只能用于诊断，不能覆盖原状态。确认代码或测试修复后，必须从 Phase 1 重新运行整套 pre-push。

## 8. 验收条件

QG-021 只有同时满足以下条件才算完成：

1. 一个文档化的 canonical pre-push 命令从干净 checkout 自举并固定运行所有 phase，不使用 diff/path 分类缩减范围。
2. 全仓测试登记能机械证明每个 suite 的唯一调用位置、主要不变量与证据层级；重复 runner 和重复 test ID 被消除。
3. 现有低层、mock-browser、LiveStack 和真实模型测试完成 KEEP/MOVE/MERGE/DELETE 处置，所有删除都有替代证据。
4. 本地 production-shaped Compose 真实 build/up/readiness/restart 成功，覆盖 Nginx、Gunicorn、PostgreSQL、New Agents frontend/backend 与主干 API/SSE。
5. 真实 DeepSeek `release` 在部署栈上完成 7/7 workflow、25/25 stage 和 18 次合法 transition，不使用关键 API mock。
6. 通过 deliberate mutation 证明格式、流式顺序、阶段流转、持久化、Nginx 路由、Docker readiness、缺凭证和重复收集任一损坏都会使门禁失败。
7. 任何非 PASS、模型波动、清理失败或测试后事实变化都阻止 push；报告绑定最终 `HEAD` 且不泄露密钥。
8. 全量运行结束后，工作区相对启动前无新增 tracked/untracked 测试污染；用户已有无关 dirty 文件未被读取、修改、stage 或清理。
9. `AGENTS.md`、Goal Mode Playbook、`docs/TESTING.md`、部署文档、GitHub workflow 与 todo 对统一门禁的执行语义一致。

## 9. 非目标与后续边界

- 本轮不实现产出物 LLM judge/评分门；该话题仍需独立设计，未来可在真实部署 E2E 层增加质量判定并据此精简低价值内容断言。
- 本轮不做 screenshot baseline、像素 diff、录像或人工视觉门禁。
- 本轮不修复生产 rsync/backup、build-before-stop、原子切换和完整线上 readiness；三个已确认阻断风险由 `QG-022` 承接。
- 本轮不按文件类型、分支、提交信息或 Agent 推断跳过测试；任何 push 前范围固定。
