# 本地提交 / 推送前验证审计

> 日期：2026-07-21
> 审计对象：当前仓库事实与 QG-020 聚焦提交 `a78c944a`
> 范围：只读审计；不修改 runner、CI、产品代码或测试结果
> 事实源：仓库当前 `AGENTS.md`、Goal Mode Playbook、测试 / 部署文档、workflow、runner、Compose、package / pytest 配置及相关测试

## 用户后续决策（当前执行口径）

本审计完成后，用户于 2026-07-21 明确决定：每次 push 到 GitHub 前运行相同的固定全量门禁，不依据 diff、路径或 Agent 影响分析缩减范围。开发过程仍可使用聚焦测试，但效率优化只能通过测试分层、职责归属和去重实现。

因此，本文关于“按 diff 触发附加门禁”的内容只用于解释现有风险、测试归属和去重候选，不再作为允许跳过 pre-push suite 的政策。当前设计以 [`QG-021 spec`](../superpowers/specs/2026-07-21-fixed-full-pre-push-quality-gate-design.md) 为准；对应能力包已进入 [`历史待办`](../todos/archive/2026-07-21-pre-push-full-validation-and-release-safety.md)。

## 结论摘要

本仓库现有命令不能直接充当可靠的单一全量门禁；需要先按以下证据层级重构为固定 pre-push 入口：

1. **开发内环**：每次行为修改先跑最快的确定性聚焦测试，保留 RED / GREEN；它证明目标行为，不证明整仓或部署。
2. **完成型 commit 前**：代码厚切片必须跑当前全量本地门禁；纯文档变更可以只跑文档一致性检查并说明为什么未跑代码测试。仓库将 `./scripts/test/test-local.sh` 定义为本地验证入口，但该脚本**不是严格 CI 等价**，必须按 diff 补齐其漏项。
3. **push 前**：固定全量入口必须绑定将要推送的当前 `HEAD`，覆盖全部 CI、真实模型和部署风险；不能用 diff 映射缩减执行范围。
4. **真实模型与 Docker**：不在每个开发小步运行，但属于每次 pre-push 的固定后层门禁。真实模型证明 provider 行为；临时 LiveStack 证明真实 React / Vite / Flask / SQLite / Chromium 链路；完整 Docker 部署才可能证明镜像、Nginx、PostgreSQL、Compose 和进程启动。这三者不能互相替代。

上述分层直接来自 Playbook 的“先聚焦、再组合、动态 CI 等价、完成型 commit 前全量、外部证据独立记账”规则；`NOT_RUN`、`BLOCKED`、`TIMEOUT`、`FLAKY` 或零收集都不是 `PASS`。[Goal Mode Playbook：风险递进与结果语义](../strategy/goal-mode-playbook.md#L291-L333)

当前 QG-020 对 New Agents 的功能链路提供了很强的 evidence level 1–4 证据，但 `a78c944a` 同时改动了 workflow、Compose、Nginx 和生产部署配置，仓库记录中没有可定位的完整 Compose 启动、生产形态 smoke、健康检查负向验证或回滚演练。因此：

- 可以认可 QG-020 的 **New Agents 功能测试体系与真实模型矩阵**成果；
- 不能把这些结果表述成 **生产 Docker / 发布事务已经验证**；
- 若同类部署面 diff 尚未完成安全、隔离的 Docker 验证，不应把直接 push 到受保护 `master` 当作第一次集成测试，因为该 push 会触发真实 `release` 并自动部署生产。

## 1. 事实源与裁决规则

本审计按以下优先级裁决冲突：

1. `AGENTS.md` 与 Goal Mode Playbook 是硬约束；
2. 当前 workflow、runner、package scripts、测试和 Compose 高于旧说明；
3. `docs/TESTING.md`、`docs/deployment-guide.md` 提供稳定领域说明；
4. QG-020 spec / plan / archive 只用于核对其目标和执行记录，不用于覆盖当前可执行事实。

这与 Playbook 明确的事实源顺序一致。[Goal Mode Playbook：事实源优先级](../strategy/goal-mode-playbook.md#L17-L27)

仓库级约束还要求：New Agents 改动按边界覆盖 backend contract/runtime/SSE/persistence、frontend stream/state/rendering，以及 manifest / contract 同步；真实模型 smoke 需要显式配置。[AGENTS.md：New Agents 分层覆盖](../../AGENTS.md#L16-L28) [AGENTS.md：测试要求](../../AGENTS.md#L46-L52)

## 2. commit 前与 push 前应分别做什么

### 2.1 每次 commit 前的硬底线

对所有变更都应执行：

```bash
git status --short
git diff --check
git diff --cached --check
git diff --cached --name-status
```

目的不是“测试业务”，而是确认 ownership、空白错误、意外删除、生成物和 staged 集。Playbook 要求精确区分用户已有 staged 项与本轮 staged 项，结果文件、缓存和无关 dirty 文件不得进入提交。[Goal Mode Playbook：staging / commit / push](../strategy/goal-mode-playbook.md#L361-L367)

随后按变更先跑最快的确定性聚焦验证。行为变更必须先有 RED，再做最小实现并取得 GREEN；纯文档变更用文档一致性检查替代代码测试。[Goal Mode Playbook：实现纪律](../strategy/goal-mode-playbook.md#L275-L277)

完成型代码 commit 还必须在最终代码和文档落定后跑当前全量门禁。仓库显式列出 `./scripts/test/test-local.sh` 作为本地 validation suite，[AGENTS.md：本地命令](../../AGENTS.md#L30-L38)；Playbook 则明确全量验证不能替代聚焦验证，也不能推迟到远端 CI。[Goal Mode Playbook：commit 前全量](../strategy/goal-mode-playbook.md#L293-L305)

建议的完成型基线是：

```bash
./scripts/test/test-local.sh
flake8 --select=E9,F63,F7,F82 .
git diff --check
```

但必须结合第 4 节补齐 `test-local.sh all` 没有覆盖或没有严格等价覆盖的门禁。不能只看到脚本退出 0 就写“CI 等价通过”。

纯文档 commit 可以不跑代码全量，但至少要确认路径 / 链接、当前规则不与代码和稳定文档冲突、没有未解释占位，并通过 `git diff --check`；这正是 Playbook 定义的文档例外。[Goal Mode Playbook：文档一致性](../strategy/goal-mode-playbook.md#L300-L307)

### 2.2 每次 push 前的硬底线

push 前应重新确认：

```bash
git status --short
git log --oneline --decorate @{upstream}..HEAD
```

并形成最小 CI 等价记录：远端风险面 / job、本地实际命令、状态、未覆盖原因、证据位置和 push 决定。Playbook 对每次 commit 或 push 都要求该映射，并明确不能只用局部测试覆盖共享 API、SSE、持久化、manifest、主路径、生成物或部署改动。[Goal Mode Playbook：CI 等价](../strategy/goal-mode-playbook.md#L335-L341)

如果以下条件同时成立，可以避免重复跑同一批确定性测试：

- 测试完成后代码、配置、依赖锁、生成物和 staged 内容未变；
- 测试证据明确对应即将 push 的 `HEAD`；
- commit 前已经完成第 4 节所需的全部 diff-triggered 门禁；
- 目标分支没有新增真实模型或部署门禁。

任何事实变化都会使相应证据失效；验证记录本应绑定当前事实版本并列出实际命令、范围、状态和缺口。[Goal Mode Playbook：验证记录](../strategy/goal-mode-playbook.md#L343-L350)

## 3. 目标分支决定 push 风险

当前 workflow 只在 `main` / `master` 的 push、以其为 base 的 PR、schedule 和手动 dispatch 上触发，而且没有 path filter；因此 docs-only 与代码变更在远端触发面上没有区别。[deploy.yml：触发器](../../.github/workflows/deploy.yml#L1-L20)

| push / 合并目标 | 当前远端行为 | 本地 push 前合理要求 |
|---|---|---|
| feature branch，尚无 PR | 当前 workflow 不因该 branch push 自动运行 | 至少完成聚焦与受影响模块；不要因为“远端不会跑”而跳过完成型 commit 门禁 |
| PR → `main` / `master` | 运行无 secret 的 backend、frontends、critical lint、proxy 和 New Agents deterministic functional jobs；真实模型 job 不收集 | 跑受影响模块和与 PR jobs 最接近的确定性组合；New Agents 共享链路 diff 至少跑 `inner`，必要时跑 browser E2E |
| 受保护 `master` push | 在上述门禁之外运行真实模型 `release`；production deploy 依赖全部门禁并自动执行 | 必须把它视为发布：补齐真实模型 release 等价或明确阻塞，并对部署面 diff 完成 Docker / health 验证；不能把远端生产发布当首个 smoke |
| protected `master` schedule | 真实模型 `nightly`，即 25 个独立 stage probe | 日常开发不必重复；manifest、全 stage contract 或 provider-wide 改动应在发布前按需运行 |
| manual dispatch | 只允许 protected `master`；production deploy 还要求 `real_scope=release` | 记录人工审批、scope 与证据；不能从 feature / PR ref 取真实凭证 |

真实 job 的条件、环境和 120 分钟 timeout 见 [deploy.yml：真实模型 job](../../.github/workflows/deploy.yml#L176-L239)；push 被硬映射为 `release`，production deploy 又 `needs` 全部七个门禁，见 [deploy.yml：deploy 依赖与条件](../../.github/workflows/deploy.yml#L349-L356)。

## 4. 当前本地 runner 与 CI 的真实差异

### 4.1 `test-local.sh all` 实际覆盖

默认 `all` 顺序运行：Intent Python、Intent critical lint、proxy Jest、Common frontend lint / build、New Agents frontend tests、New Agents backend `not slow`、mock browser E2E 和 deterministic LiveStack。[test-local.sh：all 分派](../../scripts/test/test-local.sh#L343-L397)

它是有价值的全仓聚合入口，但不是严格 CI 等价：

| 差异 | 本地 `all` | 当前 CI | 处理 |
|---|---|---|---|
| Intent coverage | 生成 coverage，但没有 `--cov-fail-under=50` | threshold 50 是硬门禁 | Intent / shared Python diff 必须补跑 CI selector与阈值 |
| New Agents frontend | `npm run test` | `npm run lint` 后 `npm run test` | New Agents frontend diff 补 `npm run lint`；生产构建面再补 `npm run build` |
| QG-020 runner / contract | 默认 `all` 不显式收集 root `tests/test_new_agents_functional_runner.py` 与 `tests/e2e/new_agents_real/test_contracts.py` | deterministic job 显式收集 | New Agents runner、scope、CI、secret 或 LiveStack diff 必须补跑 |
| root deploy / outcome tests | `tests/test_ci_deploy_hardening.py`、`tests/test_verification_outcomes.py` 不在 `all` | 当前 CI 也未持续收集它们 | workflow、Compose、deploy、health 或 gate parser diff 必须直接补跑；这是现存持续门禁缺口 |
| Browser E2E | 多跑真实 Vite + mock API browser，以及 deterministic LiveStack | CI deterministic job只显式跑 runner/contracts、LiveStack 和 Vite proxy test | 这是本地额外的 UI 证据，不应被删减成 CI job 的同义词 |
| 真实模型 | 默认 `all` 明确不跑；只有 `smoke` 子命令调用单 stage | protected master 运行 `nightly` / `release` | 按第 6 节独立记账 |

对应命令差异可以直接核对 [test-local.sh：Intent selector](../../scripts/test/test-local.sh#L58-L92)、[test-local.sh：New Agents frontend / backend](../../scripts/test/test-local.sh#L167-L228)、[test-local.sh：browser / LiveStack](../../scripts/test/test-local.sh#L230-L290) 与 [deploy.yml：backend 与 frontend jobs](../../.github/workflows/deploy.yml#L26-L128)。

`test-local.sh proxy` 还会因 Jest reporter 覆写 `tools/intent-tester/test-results/proxy/junit.xml`；该文件是测试结果，不应被误 stage，已有 dirty 内容也不得回滚或覆盖。[Intent Jest reporter](../../tools/intent-tester/jest.config.js#L68-L93)

### 4.2 `new-agents-functional.sh inner` 实际覆盖

`inner` 依次运行：

1. runner + deterministic contracts；
2. `test_live_stack.py`；
3. `test-local.sh new-agents`，即 New Agents frontend 全量 Vitest和 backend `not slow`。

这是代码中真实编排，不等于“所有 New Agents 验证”。它不运行 mock browser workflow E2E，也不运行 frontend lint / build、root deploy hardening 或 outcome tests。[new_agents_functional.py：inner 编排](../../scripts/test/new_agents_functional.py#L198-L233)

因此普通 New Agents 完成型变更的合理组合是：

```bash
./scripts/test/new-agents-functional.sh inner
(cd tools/new-agents/frontend && npm run lint && npm run build)
```

触及 UI 主路径、stream 顺序、workflow/stage、handoff、artifact DOM 或恢复行为时，再加：

```bash
./scripts/test/test-local.sh e2e
```

前端 / 后端更窄的共享流式聚焦命令已经由稳定测试文档给出，可用于 TDD，不能替代上述完成型组合。[docs/TESTING.md：共享流式聚焦测试](../TESTING.md#L207-L222)

### 4.3 建议的 CI 等价补充命令

以下命令不要求每个 diff 全部重复，而是按第 5 节选择：

```bash
# gate parser / CI / deploy 静态契约
python3 -m pytest -o addopts='' \
  tests/test_verification_outcomes.py \
  tests/test_ci_deploy_hardening.py \
  tests/test_new_agents_functional_runner.py \
  tests/e2e/new_agents_real/test_contracts.py -q

# Intent CI coverage 等价核心
PYTHONPATH="$PWD:$PWD/tools/intent-tester" \
  python3 -m pytest tools/intent-tester/tests/ -v \
  --cov=tools/intent-tester/backend --cov-report=term --cov-fail-under=50

# Common frontend
(cd tools/frontend && npm run lint && npm run build)

# New Agents frontend
(cd tools/new-agents/frontend && npm run lint && npm run test)

# Proxy
(cd tools/intent-tester && npm run test:proxy)
```

CI 的确切 selectors 以 workflow 为准：[backend jobs](../../.github/workflows/deploy.yml#L39-L70)、[frontend jobs](../../.github/workflows/deploy.yml#L75-L128)、[deterministic functional job](../../.github/workflows/deploy.yml#L130-L171)、[critical lint / proxy jobs](../../.github/workflows/deploy.yml#L276-L344)。

## 5. 按 diff 触发的门禁矩阵

| diff / 风险面 | commit 前聚焦 | 完成型 commit / push 前扩大 | 外部或部署证据 |
|---|---|---|---|
| 纯文档 | `scripts/test/check-docs.sh` 能覆盖的稳定文档 + 手工核对本次链接；`git diff --check` | 不跑代码测试需写明原因；执行规则变更要与 runner / workflow 对照 | 无 |
| Python 纯逻辑 / 单 API | 对应 pytest 文件 / node id | owning module 全量；critical flake8 | 无 |
| Intent backend / DB / security | 对应 API / service / security tests | Intent 全量 + coverage threshold 50；涉及 proxy 再跑 Jest | access、Origin/CSRF、CSP、DOM 或 ticket 变更需按稳定文档扩展到 real HTTP / Chromium；规则见 [docs/TESTING.md](../TESTING.md#L66-L76) |
| Common frontend | `npm run lint` | `npm run build` | 变更入口 / 路由时需在部署栈健康验证页面 |
| New Agents frontend 单组件 | 对应 Vitest | frontend lint + tests + build | 用户主路径 / stream /恢复触发 browser E2E |
| New Agents backend contract/runtime/SSE/persistence | 对应 backend tests | `inner`；共享链路再跑 browser E2E | provider / prompt / workflow 质量变化触发 targeted real scope |
| `workflow_manifest.json`、stage、renderer、prompt / template | sync / contract / renderer 聚焦测试 | backend + frontend + `inner` + browser E2E；验证所有配置镜像同步 | affected `stage` / `workflow`；跨 Agent / 全矩阵变化可升级 `pr`、`nightly`、`release` |
| gate parser、runner、pytest / package scripts | 对应 runner / outcome tests | root gate tests + 精确 CI selector | 无；缺配置必须保留非 PASS |
| `.github/workflows/deploy.yml`、Compose、Nginx、Dockerfile、deploy / health scripts | YAML / shell / Compose render + deployment hardening tests | image build；实际 Compose up；完整 health；记录未覆盖的 prod 差异 | 受保护 master 前需要 production-shaped smoke / rollback rehearsal；当前仓库尚无安全完整入口 |
| dependency / lockfile / Docker build context | owning module tests | `npm ci` / clean Python env + frontend builds + Docker full rebuild | 外部 registry 不可用时记 `BLOCKED`，不能用旧缓存冒充 |

该矩阵不会改变“完成型代码 commit 前全量”规则；它用于决定全量入口之外还需补哪些跨层、真实模型和部署证据。

## 6. 确定性、真实模型与 LLM judge

### 6.1 证据层级

仓库稳定文档把 New Agents 证据分为：

- deterministic LiveStack：真实 frontend / backend / SSE / SQLite / browser，但 provider 是本地确定性 OpenAI-compatible adapter，属于 evidence level 3；
- real functional scope：相同栈接真实 DeepSeek，属于 evidence level 4；
- optional LLM judge：单独评估产物语义质量，默认阈值为 `score >= 80`，未启用时不能声称有真实质量评分。

见 [docs/TESTING.md：真实链路层级](../TESTING.md#L349-L358) 与 [docs/TESTING.md：judge 阈值](../TESTING.md#L416-L428)。

### 6.2 真实模型 scope 的合理频率

| scope | 证明什么 | 合理触发 |
|---|---|---|
| `stage WORKFLOW STAGE` | 一个受影响 stage 的真实 provider / SSE / DOM / snapshot | 单 stage prompt、schema、renderer 或 provider 修复 |
| `workflow WORKFLOW` | 一个完整 workflow 的 run reuse、阶段流转和恢复 | workflow 专属 prompt / handoff / stage sequence 变化 |
| `pr` | Lisa `TEST_DESIGN` + Alex `VALUE_DISCOVERY` 两条关键连续旅程 | 共享 runtime、SSE、persistence、frontend parser/store 或跨 Agent 变化；不会在 PR head 自动运行 |
| `nightly` | manifest 派生的 25 个独立 stage | 全 stage contract、模型兼容或 manifest 广泛变化；通常由 schedule 承担 |
| `release` | manifest 派生的 7 个完整 workflow、25 turns、18 transitions | 受保护 master 发布；production deploy 的前置门禁 |

scope 选择由 manifest 派生，[matrix.py：scope selection](../../tests/e2e/new_agents_real/matrix.py#L68-L129)；执行时机和规模见 [QG-020 spec](../superpowers/specs/2026-07-16-qg020-real-agent-functional-e2e-design.md#L212-L238)。缺少三个 `NEW_AGENTS_SMOKE_*` 变量时 runner 返回 `NOT_RUN` 并非零退出，不会 skip 成绿色。[new_agents_functional.py：配置失败关闭](../../scripts/test/new_agents_functional.py#L89-L155)

真实模型不应每次开发小步都跑：QG-020 的实际记录为 `pr` 230.40 秒、`nightly` 724.85 秒、`release` 757.32 秒，且会消耗外部额度。[QG-020 archive：实际耗时](../todos/archive/2026-07-16-new-agents-streaming-and-artifact-ux.md#L138-L148) 但直接发布到 protected `master` 时，远端就是 `release`，因此本地缺少凭证不能被描述成“已完成发布等价”；应改走受保护流程或记录阻塞，而不是让生产 push 成为第一次真实验证。

确定性 browser 运行还应显式清除 / 禁用 `NEW_AGENTS_E2E_LLM_JUDGE`。browser workflow 中的 optional judge 用例只按环境变量 skip，并未标为 `real_llm`；父环境意外启用时，`-m "e2e and not real_llm"` 仍可能产生真实 judge 调用。[Lisa optional judge](../../tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py#L139-L145) [Alex optional judge](../../tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py#L140-L166)

## 7. 临时 LiveStack 与完整 Docker 部署的边界

### 7.1 LiveStack 能证明什么

`LiveStack` 在临时目录创建 SQLite，启动 `flask run`、Vite dev server 和 headless Chromium，使用动态 loopback 端口；它没有启动 Docker、Gunicorn、Nginx 或 PostgreSQL。[live_stack.py：临时栈生命周期](../../tests/e2e/new_agents_real/live_stack.py#L171-L279)

当前 deterministic 端到端 tracer 的产品旅程集中在 `TEST_DESIGN/CLARIFY`，以及同一 run 的前两个 stage；它不是 7 workflow 的 deterministic production stack matrix。[test_live_stack.py：CLARIFY tracer](../../tests/e2e/new_agents_real/test_live_stack.py#L1145-L1213) [test_live_stack.py：两阶段 tracer](../../tests/e2e/new_agents_real/test_live_stack.py#L1216-L1257)

mock browser E2E 又是另一层：它启动真实 Vite / Chromium，但通过 `page.route` 替换 Agent stream、config、snapshot 和 handoff API，因此只证明真实 UI 对 mock typed SSE 的行为。[browser conftest：API route mocks](../../tests/e2e/new_agents_browser/conftest.py#L507-L530)

### 7.2 完整 Docker 验证能补什么

`./scripts/dev/deploy-dev.sh` 会构建三个前端 / Node 项目和 proxy artifact，随后构建并启动 `docker-compose.dev.yml`、重启 Nginx，再调用 health script；它覆盖 LiveStack 没覆盖的镜像、Compose service DNS、Nginx、PostgreSQL 和容器启动。[deploy-dev.sh：build 与 Compose up](../../scripts/dev/deploy-dev.sh#L57-L120) [deploy-dev.sh：health](../../scripts/dev/deploy-dev.sh#L122-L161)

建议按 diff 选择：

```bash
# Compose / route / env 小改，且前端产物未变
./scripts/dev/deploy-dev.sh --skip-frontend

# 应用、frontend、Nginx 或跨服务主路径变化
./scripts/dev/deploy-dev.sh

# Dockerfile、requirements、lockfile、base image 或 cache identity 变化
./scripts/dev/deploy-dev.sh full
```

该脚本会创建 `.env`（若缺失）、安装依赖、改写 dist / proxy 产物并改变本机 Docker / 数据卷状态，所以不应作为每次小 commit 的内环；运行前后都要检查 `git status` 和本地数据 ownership。[deploy-dev.sh：环境与生成副作用](../../scripts/dev/deploy-dev.sh#L15-L29) [deploy-dev.sh：构建产物](../../scripts/dev/deploy-dev.sh#L57-L98)

即使 dev stack + health 通过，也不能声称 production-shaped release 已通过：dev Compose 使用源码 / dist bind mount和 development 配置，[docker-compose.dev.yml](../../docker-compose.dev.yml#L26-L132)；production Compose 使用不同环境约束、镜像构建和资源配置，[docker-compose.prod.yml](../../docker-compose.prod.yml#L25-L153)。当前仓库没有一个安全、隔离、自动化的 production Compose + Nginx + PostgreSQL + rollback rehearsal runner；既有质量审计也把该缺口保留给 `QS-05 / QG-006 / QG-008`。[既有审计：release / production-shaped 缺口](../todos/archive/2026-07-10-ai-coding-test-quality-improvement.md#L211-L230)

## 8. 当前 deployment / health 证据的限制

当前 health script 会检查部分容器、PostgreSQL readiness、若干 Intent 页面和四个 API，但：

- 容器清单没有 `new-agents` frontend，也没有启用 execution profile 时的 proxy；
- 页面清单没有 `/new-agents/`；
- New Agents 只检查 backend `/new-agents/api/health`；
- Nginx `/health` 是固定 `200`，不能证明上游可用。

证据分别见 [health_check.sh：容器清单](../../scripts/health/health_check.sh#L43-L67)、[health_check.sh：页面清单](../../scripts/health/health_check.sh#L145-L200)、[health_check.sh：API 清单](../../scripts/health/health_check.sh#L203-L258) 和 [nginx.conf：静态 health](../../nginx/nginx.conf#L125-L130)。因此 health 通过只能算浅 readiness，不能替代浏览器主路径、DB 读写、SSE 或恢复验证。

生产 workflow 还会先以 `rsync --delete` 替换 live 目录，再调用生产部署脚本。[deploy.yml：远端替换与部署](../../.github/workflows/deploy.yml#L383-L452) [deploy.yml：服务器端同步](../../.github/workflows/deploy.yml#L478-L492) 当前 deploy script 随后才创建 backup、停止并广泛清理容器 / 网络、生产无缓存 build，再 up；health 失败路径才尝试 restore。[deploy.sh：backup 与 stop](../../scripts/ci/deploy.sh#L172-L221) [deploy.sh：health 与 rollback](../../scripts/ci/deploy.sh#L245-L299) 这意味着本地 / staging 的完整部署和失败注入具有独立价值，不能依赖“生产失败会自动安全回滚”的假设。

另外，workflow 的遗留 migration 分支查找 `intent-test-db-prod` 并调用 `scripts/migrate_langfuse_to_local.sh`，[deploy.yml：migration 分支](../../.github/workflows/deploy.yml#L617-L670)；当前 production Compose 的 DB 容器名是 `ai4se-db-prod`。[docker-compose.prod.yml：PostgreSQL](../../docker-compose.prod.yml#L1-L23) 对触发旧 Langfuse 容器条件的环境，这一分支必须在发布前单独验证，而不能由普通 happy-path health 推断。

## 9. 失败、缺配置与重跑处理

统一按以下规则处理：

| 结果 | commit / push 决定 |
|---|---|
| `PASS` | 只有目标测试实际收集、执行且满足阈值时成立 |
| `FAIL` | 停止；保留首个真实错误，修复后先跑聚焦，再扩大到受影响组合和全量 |
| `NOT_RUN` / 零收集 / skip-only | 不是通过；修 selector、依赖或配置。若是必需真实门禁，停止发布 |
| `BLOCKED` | 记录缺少的权限、凭证、网络、服务、owner 和恢复条件；低层测试不能替代 |
| `TIMEOUT` | 记录预先边界和停止阶段，先诊断资源 / deadlock / scope，不能无限加时后写 PASS |
| `FLAKY` | 保留首次失败；同一事实版本结果不一致就是独立阻断，不得 retry-to-green |

仓库的 `verification_outcomes.py` 已机械要求 `PASS` 必须 collected / executed 大于 0，所有非 PASS 都返回非零；无法解析测试摘要也会成为 `NOT_RUN`。[verification_outcomes.py：状态与 PASS 条件](../../scripts/test/verification_outcomes.py#L15-L55) [verification_outcomes.py：零执行与解析失败](../../scripts/test/verification_outcomes.py#L197-L245)

如果远端 CI 失败，必须把远端 job、命令、事实版本和首个错误带回本地复现；不得把 GitHub Actions 当首次验证渠道，也不得用一次重跑绿色覆盖首次失败。[Goal Mode Playbook：远端失败闭环](../strategy/goal-mode-playbook.md#L335-L341)

## 10. QG-020 / `a78c944a` 验证审计

### 10.1 已有的强证据

QG-020 记录了以下完成结果：

- runner / contracts `107 passed`；
- deterministic LiveStack `18 passed`；
- New Agents frontend `63 files / 947 passed`；
- New Agents backend `1247 passed`；
- TypeScript lint、production build、Black、关键 flake8、Shell / YAML / JSON / Compose 和 `git diff --check` 通过；
- 真实模型 `pr` 2/2、`nightly` 25/25、`release` 7/7；
- Code / Security 独立复审零遗留。

这些结果可定位于 [QG-020 完成记录](../todos/archive/2026-07-16-new-agents-streaming-and-artifact-ux.md#L138-L148)，且与 QG-020 计划定义的 runner、LiveStack、真实 scope 和 CI 分层目标一致。[QG-020 plan：目标与边界](../superpowers/plans/2026-07-16-qg020-real-agent-functional-e2e.md#L1-L21)

因此，本审计不否定 QG-020 对 typed SSE、浏览器、SQLite persistence、阶段流转、真实 provider、scope fail-closed 和 secret isolation 的成果。

### 10.2 尚未闭合或不可审计的缺口

| 缺口 | 影响 | 判定 |
|---|---|---|
| 没有完整 Docker / production-shaped 启动证据 | QG-020 LiveStack 不经过 Docker、Gunicorn、Nginx、PostgreSQL；但提交改了 Compose、Nginx、deployment workflow / secrets | **明确缺口**；不影响功能 runner 结论，但禁止升级成部署验证 |
| 完成记录未给出完整 Compose up / health / failure / rollback 实际命令和证据位置 | “Compose 通过”更像静态 parse / render；无法证明容器或发布事务 | **审计性缺口**；Playbook 要求实际命令、范围、状态、当前事实版本与证据位置 |
| root deploy hardening 与 gate outcome tests 不在默认 `all`，也不在当前 CI | QG-020 新增 / 修改的 deploy、secret、scope、fail-closed 契约没有统一持续入口 | **持续门禁缺口**；每次相关 diff 需直接补跑 |
| `test-local.sh all` 不是严格 CI 等价 | coverage threshold、New Agents lint，以及 root tests 的选择不同 | **已知 runner 缺口**；必须按第 4 节补齐 |
| health 不覆盖 New Agents frontend、完整 stream / DB / recovery | 部署可能在浅 health 绿色时仍有用户主路径故障 | **部署 readiness 缺口** |
| 真实 evidence 记录未绑定 GitHub run / artifact 或 `a78c944a` 的可核验 evidence path | 仓库内只有数量和耗时摘要，无法从单一记录验证原始 sanitized JSON 所属 SHA | **证据可追溯缺口**；不把摘要改写成“未运行”，但后续应记录 run / SHA / artifact identity |
| QG-020 修改了 prompt / manifest / renderer 等质量相关面，但完成摘要没有 judge 记录 | 若这些 diff 被判定影响 workflow 质量，`AGENTS.md` 要求相关 judge evidence；否则可注明不适用 | **条件性缺口**；需由实际 diff 风险判定，不能把真实 functional runner 当 judge |

QG-020 plan 自身把 `./scripts/test/test-local.sh`、frontend lint / build、backend 全量、关键 flake8 / Black、YAML / JSON 与 staged ownership 列为完成型门禁，但没有列出 Docker deployment smoke。[QG-020 plan：完成型全量](../superpowers/plans/2026-07-16-qg020-real-agent-functional-e2e.md#L404-L434) 这解释了为什么功能测试目标可以完成，同时生产部署风险仍应作为独立 owner 保留。

### 10.3 若在 `a78c944a` push 前重新做一次合理验证

按照该 commit 的实际风险面，最小但完整的证据包应为：

1. QG-020 已记录的 runner/contracts、LiveStack、frontend lint/test/build、backend `not slow`、browser E2E、真实 `pr`；
2. 因共享 runtime、persistence、SSE、manifest 和多 workflow 改动，保留一次 `nightly` 25 stage 与 `release` 7 workflow 作为该厚切片的一次性验收，而非要求以后每个无关 commit 都重复；
3. `tests/test_verification_outcomes.py`、`tests/test_ci_deploy_hardening.py` 与精确 workflow selectors；
4. dev Compose 实际 build / up +完整 health；由于 frontend、backend、Nginx 和 Compose 都改动，不能使用 stale dist 或只 render YAML；
5. production Compose render / image build，以及隔离环境里的 Nginx / PostgreSQL / stream / config-auth smoke；
6. 至少一次部署失败与 rollback identity rehearsal。当前仓库没有安全的一键入口时，应如实记 `NOT_RUN` / `BLOCKED` 和 residual risk，不能写“部署已验证”；
7. 最终 `git status` / staged ownership，明确排除 `tools/intent-tester/test-results/proxy/junit.xml` 与 `test-results/new-agents-real/*.json`。

## 11. 开发者成本与推荐频率

| 层级 | 成本 / 副作用 | 推荐频率 |
|---|---|---|
| 聚焦 unit / contract / component | 最快、确定性、无外部额度 | 每次行为小步 |
| module full + lint / build | 中等；可能安装依赖、生成 coverage / dist | 完成型 commit；对应模块 diff |
| `test-local.sh all` | 高；跨 Python / Node / Chromium，可能安装依赖并改写 JUnit / coverage | 每个完成型代码厚切片；纯文档例外 |
| mock browser / deterministic LiveStack | 高；启动 Vite / Flask / Chromium /临时 DB，无 provider 额度 | UI / stream / persistence / workflow 主路径 diff；共享链路完成型 commit |
| real `stage` / `workflow` / `pr` | 外部网络、凭证和额度；QG-020 `pr` 实测约 230 秒 | provider / prompt / shared runtime 风险触发 |
| `nightly` / `release` | 最高；QG-020 实测各约 12 分钟 | schedule、发布或广泛 contract 变化，不作为每次 TDD 内环 |
| Docker dev / full rebuild | 高，改变本地容器 / 数据卷 / dist；full 禁用缓存 | deployment seam、Dockerfile / dependency / gateway / cross-service 变化 |
| production-shaped / rollback rehearsal | 最高，必须隔离并保护状态 | 任何发布事务、Compose prod、Nginx、health、migration、secret wiring 改动；发布前至少一次 |

`test-local.sh` 会在若干路径主动安装 Python / Node / Playwright 依赖，[test-local.sh：依赖安装](../../scripts/test/test-local.sh#L61-L75) [test-local.sh：Playwright 安装](../../scripts/test/test-local.sh#L233-L250)；workflow 的 deterministic / real jobs分别设置 30 / 120 分钟 timeout，[deploy.yml](../../.github/workflows/deploy.yml#L130-L184)。因此最佳优化是保存绑定 SHA 的证据、避免无事实变化的重复运行，并按风险触发昂贵层，而不是降低必需层级或把 skip 当绿色。

## 12. 最终建议

当前最合理的团队约定可以压缩为一句话：

> **每个行为小步跑聚焦确定性测试；每个完成型代码 commit 跑全量本地门禁并补齐 diff 对应的 CI 差异；push 前只复用明确绑定当前 HEAD 的新鲜证据，并补真实模型 / Docker / 发布风险；任何非 PASS 不得升级表述。**

在当前 workflow 未加入 path selection、root hardening 持续门禁和 production-shaped smoke 之前，直接 push protected `master` 的成本和风险都很高。更安全的日常路径是 feature branch + PR deterministic gates；只有发布候选在真实 `release`、部署面验证和残余风险记录齐全时进入 `master` 自动部署。
