# New Agents 双栏流式、产出物信息层级与真实链路测试待办

- 状态：`ARCHIVED / DONE`
- 创建日期：2026-07-16
- 归档日期：2026-07-20
- 完成情况：4/4；当前活跃待办数：0
- 唯一范围：New Agents 全工作流的对话先行、右侧分段流式一致性、文档元信息轻量化与真实链路功能测试重构
- 历史来源：[`2026-07-10-ai-coding-test-quality-improvement.md`](2026-07-10-ai-coding-test-quality-improvement.md)

## 用户清理决定

2026-07-16 用户先明确要求只保留本文件中的 3 项产品体验待办，旧质量整改序列、P2/P3 条件触发项、旧 E 编号、旧结构化失败治理候选和旧真实模型 smoke 候选均不再作为 backlog。随后用户基于当前测试盘点新增并批准第 4 项：以真实 DeepSeek、真实后端/SSE/持久化和无头 Chromium 为核心的 New Agents 功能测试重构。该项是依据当前目标重新建立的独立待办，不是恢复旧 smoke 候选。历史完成证据保留在 `docs/todos/archive/`，不得从归档文字、旧 checkbox、旧计划或旧分支自动恢复实施；未来若出现新的实际失败，必须按当时事实重新建项。

本文件曾是唯一活跃产品待办入口。Goal Mode 已严格按 `QG-017 → QG-018 → QG-019 → QG-020` 串行完成：前三项分别由 `8d00bb36`、`cb2fb87e`、`2a00baa6` 独立交付并推送，QG-020 由本归档结果所在的聚焦提交交付。四项全部闭合后，本文件退出活跃入口；未来新问题必须按当时事实重新建项。

## 共享架构边界

- 所有 workflow/stage 继续复用 `/api/agent/runs/stream`、typed SSE、共享 Agent Runtime、服务端 run/artifact/version 持久化、共享 frontend parser/store、`ChatPane` 与 `ArtifactPane`。
- workflow/stage 差异通过 manifest、schema、章节顺序、prompt/template、artifact contract、partial renderer registry 和测试数据表达。
- 禁止增加 Lisa、Alex、workflow 或 stage 专属 endpoint、transport、SSE path、store、持久化或渲染管线。
- 不允许用延迟右侧、最终一次性渲染、占位对话、伪造段落、宽松 schema、silent fallback 或假成功满足体验要求。

## 待办总览

| ID | 优先级 | 待办 | 状态 | 独立验收结果 |
|---|---|---|---|---|
| `QG-017` | P1 | 全工作流左侧有意义对话先于右侧产出物 | `DONE` | 首个非占位自然对话先出现，随后右侧开始真实产出；双栏各自单调更新、互不饥饿 |
| `QG-018` | P1 | 统一 25 个在线阶段的右侧分段流式 | `DONE` | 已完整且可校验的业务章节逐段出现，最终与 deterministic renderer 完全一致 |
| `QG-019` | P2 | 文档信息退出首屏重表格 | `DONE` | 25/25 阶段先展示业务正文；19 个阶段在文末单行展示元信息，6 个阶段不伪造元信息 |
| `QG-020` | P1 | New Agents 真实链路、无头优先的功能测试重构 | `DONE` | 真实 PR 2/2、Nightly 25/25、Release 7/7 全部通过；确定性内环、无头浏览器、安全边界、CI 分层与文档契约共同闭合 |

## QG-017 — 全工作流左侧有意义对话先于右侧产出物

### 用户问题

测试设计/测试用例生成工作流第一阶段会先在右侧流式展示产出物，左侧自然对话直到右侧接近或完成后才出现。通用“正在生成”占位或纯执行状态不算有意义对话。

### 已知证据

- artifact-data 阶段要求 `artifact_data` 先于 `chat`，partial parser 因而可能先产生 `chat=None`、但带可渲染 artifact 的 `agent_delta`。
- frontend 对同一 chunk 会先写 chat 再写 artifact，目前没有证据表明根因是 React 提交顺序；需要从 provider raw JSON、runtime parser、typed SSE、frontend state 到 DOM 完成时序诊断。

### 验收规则

- 所有当前与未来 workflow/stage 的首个非占位、与本轮分析直接相关的自然对话，必须先于右侧首个可见 artifact 增量。
- 右侧开始后仍按 `QG-018` 逐段流式，不得通过人为延迟或最终批量显示伪造顺序。
- chat 与 artifact 均单调更新；慢 token、artifact-first provider 输出、断流和最终收敛时任一栏都不会长期饥饿。
- 至少覆盖一个 Lisa、一个 Alex 的真实 typed SSE → parser/store → `ChatPane`/`ArtifactPane` DOM 时序证据。

### 完成结果与证据（2026-07-16）

- 共享 backend `NaturalChatFirstDeltaSequencer` 在 partial、final、durable replay 与 terminal error 路径统一执行自然对话先行；artifact-first provider 输出先缓存，错误终止会显式丢弃缓存，未增加 workflow/stage 专属分支。
- frontend 对 artifact-first、混合帧与 terminal-only 帧做防御性拆分；正常 chat-only → artifact-only 事件不增加渲染 barrier，stage action 在 artifact 状态应用后承接。
- Python 与 TypeScript 共同拒绝固定生成话术、等价前缀和不足 12 字符的 partial chat，并由 workflow contract sync test 防止镜像漂移。
- Lisa 与 Alex 共用 browser runner 的 DOM 时序观察器，均证明 `chat → artifact`；mock typed SSE 仍保留真实 `run_started / agent_delta / agent_turn / DONE` 语义，不复制生产占位规则。
- 正式 Spec/Standards 审查发现的 6 个 Important 问题已全部修复并复审关闭：占位前缀、计划横切、浏览器规则重复、过短 partial 解锁、正常事件误加 barrier、错误前未清空缓存。
- 完成型证据：backend 全量 `944 passed, 1 skipped`；frontend `60 files / 888 passed`，TypeScript lint 与 production build 通过；browser 全量 `18 passed, 3 skipped`；`./scripts/test/test-local.sh new-agents` 通过；最终全仓 `./scripts/test/test-local.sh` 通过（Intent 510、MidScene 40、New Agents frontend 888/backend 941/browser 8，另 3 个按 runner 配置跳过）；关键 Python flake8 与 `git diff --check` 通过。
- 全仓验证的前两次尝试分别因错误系统 Python 与不完整 PATH 而不具备 CI 等价性；修正环境后的较早一次运行在未改动的 Intent CSP 用例遇到数据库清理干扰。该用例随后单测、完整 Intent 510/510 与最终全仓新鲜运行均通过；没有修改 Intent 业务或测试代码，也不把早期失败改写为通过证据。
- 设计、厚切片身份与实现计划分别见 [`QG-017 spec`](../../superpowers/specs/2026-07-16-qg017-chat-before-artifact-design.md) 和 [`QG-017 plan`](../../superpowers/plans/2026-07-16-qg017-chat-before-artifact.md)。聚焦提交为 `8d00bb36`。

## QG-018 — 统一全阶段右侧分段流式

### 用户基准

以 `TEST_DESIGN/CLARIFY` 当前右侧行为为基准：模型已经完整输出且通过局部类型校验的顶层结构，应立即由后端确定性渲染为章节；后续结构完成后继续累积到同一文档。

### 静态盘点

| Workflow | 在线阶段数 | 已有 partial renderer | 待统一阶段数 |
|---|---:|---:|---:|
| `TEST_DESIGN` | 4 | 1（`CLARIFY`） | 3 |
| `REQ_REVIEW` | 2 | 0 | 2 |
| `INCIDENT_REVIEW` | 3 | 0 | 3 |
| `IDEA_BRAINSTORM` | 4 | 0 | 4 |
| `VALUE_DISCOVERY` | 4 | 0 | 4 |
| `STORY_BREAKDOWN` | 4 | 0 | 4 |
| `PRD_REVIEW` | 4 | 0 | 4 |
| **合计** | **25** | **1** | **24** |

当前 `render_partial_artifact_data_markdown()` 只为 `TEST_DESIGN/CLARIFY` 注册 partial renderer，其余 24 个阶段返回 `None`。这是共享 partial renderer 注册/能力矩阵缺口，不是单个 React 组件或 prompt 的局部问题。

### 验收规则

- manifest 中 25/25 个在线 stage 都有机械可验证的 partial-rendering 能力；新增 stage 未注册时测试失败。
- 已完成且通过局部 schema、引用与视觉契约校验的章节立即显示；未完整表格、Mermaid、`ai4se-visual`、ID 关系或引用不得伪造成成功。
- 已显示内容不回退、闪烁、重复或丢失；其他无效章节不阻塞已经有效的章节。
- 每个 stage 的 fixture 至少证明两个业务结构块分步出现，并精确收敛到 final deterministic Markdown。
- 每个 workflow 至少有一条 typed SSE → frontend state → DOM 的用户可见分段流式证据。

### 完成结果与证据（2026-07-16）

- 新增共享 `ArtifactRenderPlan`，让 partial 与 final 复用同一章节顺序、局部类型校验、引用/统计/视觉契约和 deterministic renderer；25/25 个在线 stage 全部机械注册，未增加 workflow/stage 专属 runtime、endpoint、store 或渲染管线。
- partial 只公布已经完整且独立有效的业务章节：元信息不能单独触发首个增量，无效章节被隔离，已显示章节保持单调；final 会重走同一投影校验并与完整 Pydantic schema 的 deterministic Markdown 精确收敛。
- typed SSE 增加 `agent_retry`：每次 provider 重试显式重置本次尝试的 backend sequencer 与 frontend 单调状态，同时保留跨尝试 token/retry 观测，避免合法重试被误判为内容回退。
- backend 以每 stage 至少 3 个业务快照覆盖 25/25 stage，并覆盖 23 组跨引用无效输入、派生字段、visual 隔离和 final exact convergence；frontend 以 7/7 workflow 覆盖三个渐进 DOM 状态、历史版本只在 final 落一版及稳定章节不重渲染。
- 无头 Chromium 在真实 React 页面内使用分时 `ReadableStream` typed SSE，7/7 workflow 均观察到 `chat → artifact-1 → artifact-2 → final`，精确核对三次 marker 累积、最终 DOM、workflow/stage 请求以及单次 stream 调用；全量 browser 结果为 `25 passed, 3 skipped`。
- Spec 与 Standards 两轮独立正式审查均为 PASS，无 Critical、Important 或 Minor 遗留。完成型验证：backend 完整集 `1024 passed, 1 skipped`；frontend `61 files / 898 passed`，lint 与 production build 通过；QG-018 聚焦 backend `513 passed`；`./scripts/test/test-local.sh new-agents` 通过；最终全仓 `./scripts/test/test-local.sh` 通过（Intent 510、MidScene 40、New Agents frontend 898/backend 1021/browser 15，另 3 个按 runner 配置跳过、10 个不在 runner 默认范围）；关键 flake8、`git diff --check` 通过。
- 全仓入口首次在受限沙箱内运行时，10 个本地端口用例和 2 个 Chromium 用例分别被 `Operation not permitted` 与 macOS Mach port 权限阻断；没有断言失败。保留该环境阻断证据后，在具备本地端口/浏览器权限的环境中重新执行同一完整命令并全部通过。
- 设计与纵向实现计划分别见 [`QG-018 spec`](../../superpowers/specs/2026-07-16-qg018-all-stage-paragraph-streaming-design.md) 和 [`QG-018 plan`](../../superpowers/plans/2026-07-16-qg018-all-stage-paragraph-streaming.md)。聚焦提交为 `cb2fb87e`。

## QG-019 — 文档信息退出首屏重表格

### 用户问题

右侧空间有限，产出物标题后经常先出现占据多行的“文档信息”两列表格。Artifact 名称、Workflow、Stage、状态、版本和生成时间等信息多与工作区上下文重复，价值低于正文，却优先消耗首屏和流式生成早期注意力。

### 已知证据

- 至少 `TEST_DESIGN/CLARIFY`、`TEST_DESIGN/DELIVERY`、`VALUE_DISCOVERY/BLUEPRINT` 和四个 `PRD_REVIEW` stage 的 deterministic renderer 会在标题后立即输出元信息表。
- QG-018 已阻止 metadata-only partial 独立产生右栏增量；当前剩余问题是首个业务 section 到达后，render plan 仍会把已完成的 `document_info` 排在同一 Markdown 的业务正文前面。
- CLARIFY、DELIVERY、BLUEPRINT 的 frontend template 已把同类信息定义为文末“附录”，与 deterministic renderer 的实际顺序不一致。

### 方案边界

默认候选是把纯文档元信息移到文末，以紧凑附录、短键值行或折叠摘要展示。备选是在 `ArtifactPane` 共享布局中提供右下角、页脚或折叠元信息区；只有在窄屏、长文滚动、编辑/预览切换、版本恢复、Markdown/PDF 导出和无障碍访问下均不遮挡正文时才可采用。

`document_info` 仍作为 artifact schema、持久化、版本、handoff 和导出的结构化事实保留。全阶段盘点必须区分纯文档元信息与事件概要、评审结论、执行摘要等业务正文，后者不得因标题相似而降级。

### 验收规则

- 25 个 stage 均完成“纯元信息 / 业务摘要”分类，所有业务正文优先显示。
- `document_info` 不再以首段大型表格出现，也不再成为 `QG-018` 的首个右侧流式增量。
- partial 与 final renderer 的章节顺序一致，结构化数据、持久化、版本恢复、handoff 与导出语义不丢失。
- 每个 workflow 至少一条窄右栏 DOM 证据，覆盖首屏、长文滚动与元信息可发现性；共享前端测试覆盖编辑/预览、版本恢复和导出。

### 完成结果与证据（2026-07-16）

- 共享 `ArtifactRenderPlan` 对 `business | metadata` 建立唯一 canonical 顺序并拒绝重复 section、未知 role 与无业务 section；partial/final 共用该顺序，metadata-only 输入不会成为首个右栏增量。
- 25/25 stage 完成机械分类：19 个 stage 使用文末 compact metadata footer，6 个 stage 没有纯文档元信息且不伪造 footer。DELIVERY、REQ REVIEW/REPORT、INCIDENT IMPROVEMENT 与 VALUE BLUEPRINT 的混合信息已拆成业务摘要和纯元信息投影。
- compact footer 保留结构化 `artifact_data`，不使用表格或水平分隔线；特殊 Markdown/HTML 字符用安全实体编码，preview、Markdown、DOCX 与 PDF 均保持可见原文。Story/PRD/Test 的 `document_info.workflow/stage` 会与运行时身份精确校验。
- manifest 的 19 个相关 stage 已同步 required headings 和 `2026.07.16.1` prompt/template 版本；25-stage 双向精确 heading tracer 同时阻止 manifest 漏标题、renderer 漏声明及近似子串假通过。
- frontend 覆盖 preview/code/edit、section lock、历史恢复、Markdown 字节、DOCX/PDF 顺序与实体保真；1024×800 无头 Chromium 的 7/7 workflow 专项证明业务正文首屏可见、footer 文末可发现且无 metadata 表格，完整 browser 为 `32 passed, 3 skipped`。
- Spec 与 Standards 正式审查最终均为 PASS，Critical / Important / Minor 全部清零；审查员额外用 `## PRD 输入` 与 `## 文档信息附录` 两个 mutation 证明双向精确漂移测试会失败关闭。
- 完成型证据：backend 全量 `1092 passed, 1 skipped`；frontend `62 files / 928 passed`，TypeScript lint 与 production build 通过；`./scripts/test/test-local.sh new-agents` 通过（frontend 928、backend 1089，另 4 个按 runner 选择规则不执行）；最终全仓 runner 通过（Intent 510、MidScene 40、common frontend lint/build、New Agents frontend 928/backend 1089/browser 22，另 3 skipped、10 deselected）；关键 flake8、Black check 与 `git diff --check` 通过。
- 全仓 runner 首次使用系统 Python 3.14 时因该解释器缺少 pip/pytest/flake8 而无法形成有效验证；改用仓库 Python 3.11 虚拟环境 PATH 后，同一完整入口通过。无关 runner 生成文件 `tools/intent-tester/test-results/proxy/junit.xml` 始终不进入 QG-019 提交。
- 设计与实施计划分别见 [`QG-019 spec`](../../superpowers/specs/2026-07-16-qg019-lightweight-artifact-metadata-design.md) 和 [`QG-019 plan`](../../superpowers/plans/2026-07-16-qg019-lightweight-artifact-metadata.md)。聚焦提交为 `2a00baa6`。

## QG-020 — New Agents 真实链路、无头优先的功能测试重构

### 完成状态（2026-07-20，`DONE`）

- 设计与实现计划见 [`QG-020 spec`](../../superpowers/specs/2026-07-16-qg020-real-agent-functional-e2e-design.md) 和 [`QG-020 plan`](../../superpowers/plans/2026-07-16-qg020-real-agent-functional-e2e.md)。统一 runner、manifest/scenario 派生矩阵、Vite→Flask proxy、临时 SQLite、无头 Chromium、旁路 typed SSE/DOM 摘要、跨阶段 snapshot/metrics、刷新恢复、类型化脱敏报告和 CI 事件映射均已落位。
- 分层执行模式按批准方案完成：开发内环确定性、受控 `pr` 的 Lisa/Alex 关键真实链路、Nightly 的 25-stage 独立矩阵、Release 的 7-workflow 连续旅程；自动 PR 继续只跑无 secret deterministic gate。
- QG-017/018/019 的核心行为进入同一真实链路断言：有意义对话先于产出物、产出物按有效业务段落单调累积、纯文档元信息不占首屏；同时验证 typed SSE、合法阶段流转、runId 复用、服务端持久化与刷新恢复。
- 最终确定性内环：runner/contracts `107 passed`、真实 frontend/backend/persistence 的无头 LiveStack `18 passed`、frontend `63 files / 947 passed`、backend `1247 passed`。TypeScript lint、production build、Black、关键 flake8、Shell/YAML/JSON/Compose 和 `git diff --check` 全部通过。
- 最终真实模型门禁严格按顺序执行并全绿：PR `2/2 passed in 230.40s`；Nightly `25/25 passed in 724.85s`；Release `7/7 passed in 757.32s`。此前缺凭证时的 `NOT_RUN` 与 Release 初次失败均作为历史诊断事实保留，不能替代或稀释本次新鲜完整通过。
- 最终独立复审：Code Critical / Important / Minor = `0 / 0 / 0`；Security High / Medium / Low = `0 / 0 / 0`。配置管理、运行时代理和模型三类密钥强制两两独立；生产浏览器只读，安全诊断端点不可覆盖 provider target；开发匿名配置默认关闭且只发布 loopback；供应商异常、日志和报告均执行脱敏与失败关闭。
- 真实模型变量只注入受控临时 shell，门禁结束后已清除；未写入源码、报告、测试结果或提交。无关生成文件 `tools/intent-tester/test-results/proxy/junit.xml` 和 `test-results/new-agents-real/*.json` 不属于本项提交且保持未暂存。

### 用户目标与范围

测试保障只聚焦 `tools/new-agents/`，本项不改动、不扩展 `tools/intent-tester/`。用户明确不追求截图回归、像素级比对或精细视觉差异，优先保障以下功能事实：

- 模型输出能够通过当前 workflow/stage 的 `AgentTurnOutput`、`artifact_data`、业务不变量与视觉数据契约校验。
- typed SSE 在真实模型响应下持续产生有效增量，前端能够持续、单调地渲染对话和产出物，而不是只在最终事件一次性出现。
- 完成当前阶段后能够按 manifest 和运行状态正确流转到下一阶段，并保留 run、message、artifact、version、context summary 与 handoff 所需事实。
- 断流、provider 错误、schema 错误和阶段门禁失败必须显式、可诊断，不允许 mock、fallback、重试假通过或伪造成功掩盖失败。

### 已批准的测试模式

采用“开发内环确定性测试 + 本地/受控关键真实链路 + Nightly/发布全量真实矩阵”的分层模式：

1. **开发内环 / 每次相关改动**：运行受影响 stage 的 schema、renderer、partial parser、typed SSE parser/store、DOM 状态和阶段状态机测试。该层不依赖外部模型，目标是秒级或分钟级反馈，并作为 TDD 的 RED/GREEN 证据。
2. **提交前 / PR 门禁**：本地可显式使用无头 Chromium、真实 frontend/backend/数据库、共享 `/api/agent/runs/stream` 和真实 DeepSeek 跑 Lisa/Alex 关键顺序旅程；自动 PR 不读取 secret，只跑同一 harness 的 deterministic 功能门禁。真实证据在代码进入受保护 `master` 后由 push/schedule/reviewed dispatch 闭环。
3. **Nightly / 发布门禁**：对 manifest 中 7 个 workflow、25 个在线 stage 运行真实模型格式与流式矩阵；发布门禁再覆盖每个 workflow 的顺序流转旅程。新增 workflow/stage 未进入矩阵时机械失败。

自动 PR 层追求高频、较短且无凭证的反馈；本地受控运行、Nightly 与发布层承担真实模型波动观察。真实测试不得用 `page.route` mock `/api/agent/runs/stream`、snapshot、artifact version、handoff 或 packet 等本次旅程涉及的关键 API；mock SSE 只保留给开发内环的故障注入和边界单测。

### 断言模型

真实模型输出具有非确定性，因此不对完整自然语言文本做逐字快照。门禁使用功能与语义不变量：

- HTTP/SSE 协议有效，事件类型、顺序、`runId` 复用和终止语义符合共享 contract。
- 一次流式 turn 在最终 `agent_turn` 前产生可观测的有效增量；chat、partial artifact 和最终 artifact 的内容均单调收敛，不回退、不重复、不丢失。
- `artifact_data` 通过对应 Pydantic schema、引用完整性、统计一致性和 Mermaid/`ai4se-visual` contract；最终 Markdown 与 deterministic renderer 一致。
- 浏览器只断言用户可见 DOM 内容、阶段状态、操作可用性与网络/持久化结果，不生成截图基线，也不做像素差异比较。
- 当前阶段完成后，下一阶段入口、上下文继承和服务端记录同时成立；刷新或恢复后仍以服务端事实为准。
- 失败按 provider、transport、schema、renderer、frontend 或 transition 分类输出诊断；必跑门禁缺凭证或未执行时记为 `NOT_RUN` 并失败关闭，不得算作通过。

### DeepSeek 凭证边界

- 本地凭证统一从 Git 已忽略的根目录 `.env` 安全加载，首选 `NEW_AGENTS_SMOKE_API_KEY`、`NEW_AGENTS_SMOKE_BASE_URL`、`NEW_AGENTS_SMOKE_MODEL`；API Key 只能进入 backend/test process，不得注入浏览器 bundle、测试报告、日志或失败截图。
- CI 不向任何 PR 事件注入真实模型凭证，`master` ruleset 必须把 deterministic job 设为 required check。三个同名 secrets 只配置在 `new-agents-real-automatic` 和 `new-agents-real-manual` environments，两者 deployment branch 只允许 `master`，workflow 同时要求 `github.ref_protected == true`；manual environment 还需 required reviewers、prevent self-review 并禁止管理员 bypass。不得保留同名 repository/organization secrets；若当前 GitHub 套餐不支持 required reviewers，manual environment 不配置 secrets，只保留受保护 push/schedule 路径。
- CI 只上传经 allowlist 和 API key 原值扫描的脱敏 JSON 文件，不上传整个结果目录或原始日志/数据库/浏览器状态。
- 实施中曾因根目录 `.env` 未配置上述变量而准确记录 `NOT_RUN`；随后用户通过受控临时 shell 提供真实模型变量，完成全部真实门禁后立即清除。凭证从未进入 Git、浏览器环境或持久测试证据。

### 验收规则

- 提供按 workflow/stage 选择范围的统一命令，开发者能在本地无头运行单 stage、单 workflow、PR 关键集和全量矩阵。
- 本地/受控 `pr` 关键集至少包含一个 Lisa 和一个 Alex 的真实顺序旅程，并覆盖结构化格式、多个流式增量、浏览器渐进 DOM、服务端持久化和至少一次合法阶段推进；自动 PR 不因未运行真实 scope 而获得虚假 PASS，其证据类型明确记为 deterministic。
- Nightly 对 25/25 stage 产生真实 provider 证据；发布门禁对 7/7 workflow 产生顺序流转证据，失败报告能定位 workflow、stage、run、事件阶段与错误类型，但不泄露 prompt 中的敏感值或 API Key。
- `QG-017`、`QG-018` 实现后，其核心时序与分段行为必须进入 PR 关键真实链路；`QG-019` 只做 DOM 结构和信息顺序断言，不引入视觉快照。
- CI 受保护真实 job 与本地真实命令的 scope 选择、凭证加载和结果语义一致；自动 PR 明确记录为无 secret deterministic 证据。必跑范围不得静默 skip，偶发 provider 波动必须被单独标记和统计，不得用无限重试稀释真实失败。

## 组合后的用户顺序

前三项组合验收时，用户可见顺序必须是：

1. 左侧出现有意义的自然对话。
2. 右侧出现首个可校验的业务正文段落。
3. 后续正文按章节持续累积并收敛到最终产出物。
4. 低权重文档元信息在尾部或独立轻量区保持可发现、可读取。

## Goal Mode 执行与停止线

本轮已按 `QG-017 → QG-018 → QG-019 → QG-020` 完成设计、计划、TDD、正式审查、验证、证据记录和独立交付；没有越过前项门禁。`QG-020` 以独立测试基础设施重构 spec 收口，并把前三项的真实回归证据纳入分层门禁。旧 `QS-05～QS-08`、旧 P2/P3 backlog 或归档 E 编号继续保持取消状态，不得从本归档恢复。
