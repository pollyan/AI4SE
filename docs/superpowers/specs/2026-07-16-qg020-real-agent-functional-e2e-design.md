# QG-020 New Agents 真实链路功能测试重构设计

- 日期：2026-07-16
- 状态：已批准，进入实施计划
- Archived owning todo：[`QG-020`](../../todos/archive/2026-07-16-new-agents-streaming-and-artifact-ux.md#qg-020--new-agents-真实链路无头优先的功能测试重构)
- 顺序基线：`QG-017 → QG-018 → QG-019 → QG-020`；前三项已经独立交付，本 spec 只承接最后一项

## 厚切片身份基线

本厚切片是一个工程信任闭环：开发者和 CI 能用同一套无头功能测试入口，分别运行单阶段、单 workflow、本地/受控 `pr` 关键真实旅程、Nightly 全阶段矩阵和发布全 workflow 旅程；自动 PR 门禁只运行无凭证的确定性链路。真实 scope 穿过 React、共享 `/api/agent/runs/stream`、Flask、PydanticAI/DeepSeek、typed SSE、服务端持久化和阶段状态机，并以结构化格式、流式单调性、阶段推进和持久化事实为门禁，不以截图或像素差异为门禁。

这个身份在设计、计划、实现、审查、commit 和交付中保持不变。内部的配置、runner、harness、报告、CI、文档和测试步骤都不是独立切片。

## 1. 当前事实与保护边界

### 1.1 已读取事实

- `AGENTS.md` 与 `docs/strategy/goal-mode-playbook.md` 要求 New Agents 共享一套 runtime、transport、state、UI 和持久化基础设施，并按证据层级区分 deterministic、真实 UI、真实前后端和真实外部模型。
- 当前 backend 有 1 个 `test_agent_real_smoke.py`，只直接调用 `PydanticAgentRuntime` 的 `TEST_DESIGN/CLARIFY`，没有真实 HTTP、浏览器、持久化或阶段推进；缺配置时使用 `pytest.skip`。
- 当前 `tests/e2e/new_agents_browser/` 使用真实无头 Chromium 和真实 React，但 `page.route`/替换 `window.fetch` 提供 mock typed SSE，并 mock snapshot、handoff 和 packet 等接口。
- `scripts/test/test-local.sh` 将确定性 backend、frontend、mock browser E2E 和真实 smoke 分开；真实 smoke 缺凭证时能在 wrapper 层记录 `NOT_RUN` 并非零退出，但测试本身仍可 skip。
- `.github/workflows/deploy.yml` 当前没有真实模型 PR、Nightly 或发布门禁；backend job 也没有显式排除 `slow`。
- `workflow_manifest.json` 当前包含 7 个 workflow、25 个在线 stage；每个 workflow 都有 `agentId`、`slug`、stage 顺序和 stage 名称，足以机械生成测试矩阵。
- frontend 在 `buildSystemPrompt()` 生成完整 stage prompt，并把它通过共享 stream request 发送给 backend；真实浏览器驱动天然使用这条生产路径，无需复制 prompt 构建逻辑。
- Vite dev server 当前没有 `/new-agents/api` 到独立 backend 的代理；mock browser 因为拦截请求而没有暴露这个缺口。
- 根目录 `.env` 当前只有数据库和 Flask 类变量，没有 `NEW_AGENTS_SMOKE_API_KEY`、`NEW_AGENTS_SMOKE_BASE_URL`、`NEW_AGENTS_SMOKE_MODEL`，也没有可安全复用的 DeepSeek/OpenAI 变量。

### 1.2 工作区保护

- 启动 QG-020 时 `master` 与 `origin/master` 同步在 `2a00baa6`。
- `tools/intent-tester/test-results/proxy/junit.xml` 是既有 runner 生成改动，属于其他模块，禁止读取其内容、修改、暂存、提交或借清理回滚。
- 本项只修改 New Agents 测试、测试入口、相关 CI/测试文档和本 todo；不扩展或重构 intent-tester。
- API key 只允许进入 backend/test 进程环境；不得传给 Vite/browser bundle、JSON 报告、pytest failure detail、截图或 Git。

## 2. 用户、目标与输入

### 2.1 用户与场景

- 开发者修改某个 workflow/stage 时，需要在本地用一个统一入口获得快速、功能型的 RED/GREEN 反馈。
- PR 作者先通过无 secret 的确定性无头门禁；Lisa/Alex 真实顺序旅程由开发者本地显式运行，或在代码进入受保护 `master` 后通过受控门禁证明。
- Nightly 需要证明 manifest 的 25/25 stage 都能让真实 DeepSeek 返回合法结构并产生有效流式增量。
- 发布者需要证明 manifest 的 7/7 workflow 都能真实顺序流转、复用 run 并从服务端恢复。
- 维护者需要从失败报告直接定位 workflow、stage、run、SSE 阶段和错误类别，同时确认报告没有密钥。

### 2.2 统一输入

统一入口只暴露五种 scope：

- `inner`：确定性开发内环。
- `stage WORKFLOW STAGE`：一个独立真实 stage probe。
- `workflow WORKFLOW`：一个完整真实顺序旅程。
- `pr`：固定的 Lisa + Alex 关键 workflow 集。
- `nightly`：manifest 派生的 25-stage 独立矩阵。
- `release`：manifest 派生的 7-workflow 顺序旅程。

真实 scope 从根目录 `.env` 或进程环境读取且只接受：

- `NEW_AGENTS_SMOKE_API_KEY`
- `NEW_AGENTS_SMOKE_BASE_URL`
- `NEW_AGENTS_SMOKE_MODEL`

workflow/stage 集合、agent、slug 和顺序只从 `workflow_manifest.json` 派生。测试场景文件只保存合成业务背景和 PR 关键集标记，不复制 stage schema、renderer、prompt、heading 或 transition contract。

## 3. 成功状态、失败路径与非目标

### 3.1 成功状态

一次 stage turn 必须同时满足：

1. 浏览器真实请求共享 `/new-agents/api/agent/runs/stream`，Vite 只做代理，不拦截或伪造响应。
2. SSE 依次出现合法 `run_started`、一个或多个 `agent_delta`、`agent_turn` 和 `[DONE]`；禁止 `error` 终止。
3. `agent_turn` 前至少有一个有意义 chat delta 和两个不同的 partial artifact 状态；chat 先于首个 artifact，chat 与 artifact 分别单调增长。
4. 最终 `AgentTurnOutput` 已通过 backend 的 workflow/stage schema、业务不变量、引用、统计和视觉契约；最终 Markdown 与服务端 artifact snapshot 一致。
5. DOM 观察到 chat 后才出现业务正文，正文有多个独立累积状态；首个业务 section 在 metadata 之前，metadata 如存在只在文尾轻量展示。
6. 服务端 snapshot 包含同一 run 的 user/assistant message、当前 stage artifact、artifact version、结构化 `artifactData` 和可诊断 metric；浏览器刷新后从该 snapshot 恢复。

一次完整 workflow 还必须满足：

1. 每个非末 stage 都返回合法 immediate-next `stage_action`，浏览器显示确认控件。
2. 点击确认后才推进，下一 turn 使用同一个 `runId`，服务端 `currentStageId`、message 序列和各 stage artifact/version 同步更新。
3. 所有在线 stage 各产生一份成功 turn 证据；末 stage 不伪造下一阶段。

### 3.2 失败路径

- 缺少任一真实模型变量：wrapper 先写 `NOT_RUN` outcome，再以非零退出；pytest 不用 `skip` 把缺配置伪装成通过。
- provider 鉴权、限流、网络或服务错误：分类为 `provider`，保留 error code、workflow/stage/run 和事件位置，不输出 SDK 原始 header、key 或完整 prompt。
- 非法 SSE、断流、缺 `[DONE]`、事件逆序：分类为 `transport`。
- `AgentTurnOutput`/`artifact_data`/业务契约失败：分类为 `schema` 或 `renderer`。
- DOM 不单调、chat/artifact 顺序错误、最终态未应用：分类为 `frontend`。
- `runId` 变化、snapshot 缺失、stage 未推进或刷新不能恢复：分类为 `persistence` 或 `transition`。
- runtime 自带的有限 schema retry 通过 `agent_retry` 计数保留；测试 harness 不做无限重跑，也不通过 retry-to-green 抹掉首次失败。

所有失败都让必跑 scope 非零退出。`BLOCKED`、`NOT_RUN`、`TIMEOUT` 和 `FLAKY` 不得记为 `PASS`。

### 3.3 下游承接

- 本地与 CI 共享同一 selection、凭证、headless、报告和退出语义。
- `inner` 继续作为 TDD 主入口；真实 scope 不替代 backend/frontend 的确定性测试。
- manifest 新增 workflow/stage 后，矩阵同步测试必须先失败，直到场景背景和 PR/全量选择规则仍能覆盖它。
- 真实报告可被 CI 上传，但只能上传通过 API key 原值扫描的脱敏 JSON allowlist；不上传整个结果目录，不提交运行产物。

### 3.4 非目标

- 不做 screenshot baseline、视觉快照、像素 diff、录像或失败截图门禁。
- 不把 LLM judge 引入本切片的必跑门禁；已有可选 judge 继续独立记账。
- 不修改 intent-tester/MidScene 测试。
- 不创建 workflow/stage 专属 endpoint、runtime、store、renderer 或 persistence path。
- 不在真实 scope 中用 `page.route`、替换 `window.fetch`、mock snapshot、fake artifact 或 fake success。
- 不承诺真实自然语言逐字稳定，只断言协议、schema、业务契约和可观察状态不变量。

## 4. 方案比较与决定

### 4.1 方案 A：只做 backend 真实模型矩阵

直接对 25 stage 调用 runtime 或 Flask endpoint。成本最低、schema 定位清楚，但无法证明 React parser/store、DOM 流式提交、阶段按钮、refresh 恢复和浏览器同源路径，不能满足 PR 端到端目标。

### 4.2 方案 B：所有 scope 都跑完整浏览器 workflow

所有 stage 都通过从第一阶段开始的完整旅程到达。真实性最高，但单 stage 反馈会被前序阶段成本和波动污染，Nightly 会重复调用相同阶段，失败定位和额度都不理想。

### 4.3 方案 C：共享真实栈 + stage probe/workflow journey 两种场景形态（采用）

用同一个 live-stack harness 启动真实 Vite、Flask、SQLite、无头 Chromium 和 provider adapter：

- 独立 stage probe 通过真实 UI 直接选择目标 stage，适合单 stage 与 Nightly 25-stage 矩阵。
- workflow journey 从第一阶段按确认控件推进到末阶段，适合单 workflow、PR 关键集和 release 7-workflow 矩阵。
- 开发内环给同一 provider seam 接一个本地 OpenAI-compatible deterministic adapter，只验证 live-stack harness、真实 backend/SSE/persistence/browser，不宣称真实模型质量。
- 真实 scope 给同一 seam 接 DeepSeek adapter，且禁止任何关键 API mock。

该方案让调用者只理解 `scope + optional workflow/stage`，内部隐藏进程、端口、数据库、SSE 观察和报告，形成有深度的测试模块；两个真实 adapter 也让 provider seam 不是假想抽象。

用户此前已经明确批准“开发内环确定性 + PR 关键真实链路 + Nightly/发布真实矩阵”的执行策略，因此本设计不再等待常规方案审批。

## 5. 架构与模块接口

### 5.1 统一 runner 模块

`scripts/test/new_agents_functional.py` 是深模块，外部接口只接受 scope、workflow、stage。它负责：

- 解析并校验 manifest selection。
- 安全加载 `.env`，只把 key 注入 backend/live-test 子进程。
- 对缺配置写 `NOT_RUN` outcome 并失败关闭。
- 选择 deterministic 或 real pytest 集合。
- 设置测试进程需要的 selection 环境，不输出 secret。

`scripts/test/new-agents-functional.sh` 只是仓库惯用的 shell adapter，不承载选择逻辑。

### 5.2 Live stack 模块

`tests/e2e/new_agents_real/live_stack.py` 对测试暴露一个 `LiveStack.start(config)`/context manager 接口，内部负责：

- 分配 loopback 端口和临时 SQLite 数据库。
- 启动 Flask backend，并把 smoke 配置映射为 server-managed default LLM config。
- 启动带 backend proxy target 的 Vite。
- 启动无头 Chromium context，显式移除传给 frontend 进程的 secret 变量。
- readiness、超时、子进程日志脱敏和确定性清理。

Vite 的 proxy seam 只在显式 `NEW_AGENTS_BACKEND_URL` 存在时启用，把 `/new-agents/api/*` 重写为 backend `/api/*`；正常生产 build 和现有 mock browser E2E 不改变。

### 5.3 Matrix 与场景模块

`tests/e2e/new_agents_real/matrix.py` 从 manifest 生成 `StageCase` 和 `WorkflowCase`，并机械断言：

- Nightly stage 集等于 25 个在线 stage。
- Release workflow 集等于 7 个 manifest workflow。
- PR 集包含至少一个 Lisa 与一个 Alex，且当前选择 `TEST_DESIGN`、`VALUE_DISCOVERY` 两条完整四阶段旅程。
- `stage`/`workflow` 参数必须存在且匹配。

`real_llm_scenarios.json` 只按 workflow 保存合成业务背景；每个独立 stage probe 复用其 workflow 背景并追加“直接完整完成当前阶段、允许显式假设”的测试指令。新增 workflow 缺场景时同步测试失败。

### 5.4 SSE/DOM 观察模块

浏览器 init script 包装原生 `fetch`，只对真实 stream response 做 `clone()` 旁路读取并解析 typed SSE；原 response、请求、时序和网络路径不改变。观察结果只保存：

- request 的 workflow/stage/requestId（不保存 system prompt/user prompt）。
- event type、相对时间、runId、error code。
- chat/artifact 长度、摘要 hash、partial section/heading 集合。
- final artifact hash。

DOM 通过 `MutationObserver` 记录 chat 与 artifact 的相对提交和文本 hash/长度，不保存截图。网络与 DOM 证据按 requestId 对齐。

### 5.5 断言与脱敏报告模块

`assertions.py` 只接受结构化 trace 和 snapshot，集中执行 SSE、单调性、QG-017/018/019、persistence 和 transition 不变量。失败信息只输出坐标与摘要。

`reporting.py` 把结果写到 Git ignored 的 `test-results/new-agents-real/`，字段包括 scope、workflow、stage、runId、requestId、状态、事件序列、delta 数、retry 数、artifact hash、snapshot/version 数和错误分类。任何 key 名匹配 `api[_-]?key|authorization|secret|token|password` 的值都会被递归替换为 `<redacted>`；报告测试使用 canary secret 证明磁盘内容不含原值。

## 6. 数据流

### 6.1 独立 stage probe

1. runner 解析 `stage` 或 Nightly selection 并检查凭证。
2. live stack 用临时 SQLite 启动 backend/Vite/Chromium。
3. 浏览器打开 manifest 派生 workspace URL，直接选择目标 stage。
4. 测试输入合成背景；frontend 生产代码生成真实 `systemPrompt` 并请求共享 stream endpoint。
5. backend 调用 provider、解析 partial JSON、校验并确定性渲染，持续输出 typed SSE 并持久化最终事实。
6. 旁路 trace 与 DOM observer 记录增量；最终通过 snapshot endpoint 校验持久化与刷新恢复。
7. 生成脱敏 stage evidence；任何不变量失败都令该 case 失败。

### 6.2 完整 workflow journey

1. 浏览器从首 stage 输入合成背景。
2. 每个 turn 通过与 stage probe 相同的真实路径和断言。
3. 非末 stage 必须展示 immediate-next 确认控件；测试点击后 frontend 自动发送下一阶段请求。
4. 每次 `run_started` 必须复用首个 `runId`；snapshot 的 `currentStageId`、messages、artifacts 和 versions 随之增加。
5. 末 stage 完成后刷新带 `runId` 的页面，核对最终服务端恢复。

### 6.3 确定性 live-stack tracer

本地 OpenAI-compatible adapter 顺序返回由现有 backend 合法 fixture 生成、分块发送的 `TEST_DESIGN/CLARIFY → STRATEGY` 两阶段 JSON。它验证真实 HTTP、OpenAI SDK、raw streaming parser、typed SSE、React DOM、SQLite、跨阶段 `runId`/observer 隔离和 refresh 恢复；报告明确标记 evidence level 3，不宣称真实 DeepSeek。

## 7. CI 与执行时机

- 开发/TDD：`inner`；相关 New Agents 改动提交前运行。
- PR：自动门禁只跑 deterministic runner/contracts、Vite proxy 与 live-stack，不收集真实 job，不读取 secret；本地 `pr` 仍可显式跑 `TEST_DESIGN` + `VALUE_DISCOVERY` 完整旅程。
- Nightly：仅 `github.ref_protected == true` 的 `master` schedule 运行 `nightly`，跑 25 个独立 stage probe。
- 发布：仅 `github.ref_protected == true` 的 `master` push 或受审核的 `master` 发布 dispatch 触发 `release`，跑 7 个完整 workflow，并成为 production deploy 的 `needs`。
- 手动：`workflow_dispatch` 必须使用 `master` ref，并经 `new-agents-real-manual` environment required reviewers 审核；任意 feature/PR ref 即使手动触发也不运行真实 job。
- 凭证：三个 `NEW_AGENTS_SMOKE_*` 只作为 `new-agents-real-automatic` 与 `new-agents-real-manual` environment secrets 存在；禁止同名 repository/organization secrets，两个 environment 的 deployment branch 均只允许 `master`。`master` ruleset 必须把 deterministic job 设为 required check；manual environment 必须 required reviewers + prevent self-review 且禁止管理员 bypass。若当前 GitHub 套餐不支持 required reviewers，manual environment 不配置 secrets，只保留受保护 push/schedule 路径。
- CI 只上传通过 allowlist 和 API key 文件名/内容扫描的 `test-results/new-agents-real/*.json`，且真实 scope 必须至少产生一份 evidence；不上传数据库、backend 原始日志、浏览器 storage、截图或整个结果目录。

## 8. 测试设计

### 8.1 TDD 聚焦测试

- runner 参数、manifest 选择、PR Lisa/Alex 覆盖、25/25 与 7/7 集合相等。
- 缺配置返回 `NOT_RUN` 且非零；完整配置不把 key 放入 argv、stdout 或 frontend env。
- Vite proxy 只在 target 存在时启用并正确 rewrite。
- SSE parser 拒绝坏 JSON、缺终止、error 后成功、事件逆序和非单调 chat/artifact。
- report redaction 的 canary secret、嵌套 header/query/message 和错误字符串覆盖。
- deterministic live-stack tracer 证明真实 frontend/backend/SQLite/browser 主路径。

### 8.2 真实模型门禁

- 本地/受控 `pr`：2/2 workflow journey，8 个 stage turn；每个 turn 满足多个真实 partial、DOM 顺序、snapshot、run reuse，至少 6 次合法 transition。该 scope 不自动运行于 PR head。
- Nightly：25/25 stage probe，各产生 provider、SSE、DOM、snapshot 证据。
- Release：7/7 workflow journey，25 个 stage turn和 18 次合法 transition。
- 设计阶段本地缺 key，因此当时只执行 evidence level 1–3，并准确把 evidence level 4 记为 `BLOCKED`/`NOT_RUN`；2026-07-20 收到受控临时凭证后，真实 PR 2/2、Nightly 25/25、Release 7/7 均转为 `PASS` 并关闭 QG-020。

### 8.3 全量与 CI 等价

- New Agents backend `not slow` 全量。
- New Agents frontend 全量、TypeScript lint 和 production build。
- mock browser E2E（显式排除 `real_llm`）与 deterministic live-stack tracer。
- runner/CI workflow 静态契约、关键 Python flake8、Black check、YAML/JSON 解析和 `git diff --check`。
- commit 前运行仓库当前定义的全量本地门禁；无 key 时真实模型门禁保持非 PASS，禁止用低层证据替代。

## 9. 自审结果

- 所有章节均已给出确定决定、责任路径和成功语义，没有占位内容。
- 自动 PR deterministic gate、受控 `pr`、Nightly 与 release 的范围、成本、凭证边界和证据层级互不混淆。
- provider adapter seam 有 deterministic 和 DeepSeek 两个真实 adapter，不是为测试虚构的单实现抽象。
- 场景背景是测试数据；manifest、prompt、schema、renderer、transition 和持久化仍由现有共享事实源负责。
- 真实 key 缺失被明确记录为最终 evidence level 4 的外部阻塞，不会被 skip 或 mock 结果掩盖。
