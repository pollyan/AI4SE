# New Agents 双栏流式、产出物信息层级与真实链路测试待办

- 状态：`ACTIVE / IN_PROGRESS`
- 创建日期：2026-07-16
- 当前待办数：4
- 唯一范围：New Agents 全工作流的对话先行、右侧分段流式一致性、文档元信息轻量化与真实链路功能测试重构
- 历史来源：[`2026-07-10-ai-coding-test-quality-improvement.md`](archive/2026-07-10-ai-coding-test-quality-improvement.md)

## 用户清理决定

2026-07-16 用户先明确要求只保留本文件中的 3 项产品体验待办，旧质量整改序列、P2/P3 条件触发项、旧 E 编号、旧结构化失败治理候选和旧真实模型 smoke 候选均不再作为 backlog。随后用户基于当前测试盘点新增并批准第 4 项：以真实 DeepSeek、真实后端/SSE/持久化和无头 Chromium 为核心的 New Agents 功能测试重构。该项是依据当前目标重新建立的独立待办，不是恢复旧 smoke 候选。历史完成证据保留在 `docs/todos/archive/`，不得从归档文字、旧 checkbox、旧计划或旧分支自动恢复实施；未来若出现新的实际失败，必须按当时事实重新建项。

本文件是当前唯一活跃产品待办入口。用户已在 2026-07-16 启动 Goal Mode，并再次确认必须严格按 `QG-017 → QG-018 → QG-019 → QG-020` 串行执行；当前 QG-017 已完成设计、TDD、正式审查、完成型验证与独立交付，下一入口是 QG-018 ASSESS，QG-019 与 QG-020 不得提前穿插。

## 共享架构边界

- 所有 workflow/stage 继续复用 `/api/agent/runs/stream`、typed SSE、共享 Agent Runtime、服务端 run/artifact/version 持久化、共享 frontend parser/store、`ChatPane` 与 `ArtifactPane`。
- workflow/stage 差异通过 manifest、schema、章节顺序、prompt/template、artifact contract、partial renderer registry 和测试数据表达。
- 禁止增加 Lisa、Alex、workflow 或 stage 专属 endpoint、transport、SSE path、store、持久化或渲染管线。
- 不允许用延迟右侧、最终一次性渲染、占位对话、伪造段落、宽松 schema、silent fallback 或假成功满足体验要求。

## 待办总览

| ID | 优先级 | 待办 | 状态 | 独立验收结果 |
|---|---|---|---|---|
| `QG-017` | P1 | 全工作流左侧有意义对话先于右侧产出物 | `DONE` | 首个非占位自然对话先出现，随后右侧开始真实产出；双栏各自单调更新、互不饥饿 |
| `QG-018` | P1 | 统一 25 个在线阶段的右侧分段流式 | `NOT_STARTED` | 已完整且可校验的业务章节逐段出现，最终与 deterministic renderer 完全一致 |
| `QG-019` | P2 | 文档信息退出首屏重表格 | `NOT_STARTED` | 右侧先展示业务正文，元信息保留但只在尾部轻量附录或共享轻量区出现 |
| `QG-020` | P1 | New Agents 真实链路、无头优先的功能测试重构 | `NOT_STARTED` | PR 运行关键真实链路，Nightly/发布运行全阶段矩阵；验证格式、流式、持久化与阶段流转，不以截图或像素差异作为门禁 |

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
- 设计、厚切片身份与实现计划分别见 [`QG-017 spec`](../superpowers/specs/2026-07-16-qg017-chat-before-artifact-design.md) 和 [`QG-017 plan`](../superpowers/plans/2026-07-16-qg017-chat-before-artifact.md)。聚焦提交由本结果更新所在的 QG-017 commit 承载，交付时以 `git log` 记录其 SHA。

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

## QG-019 — 文档信息退出首屏重表格

### 用户问题

右侧空间有限，产出物标题后经常先出现占据多行的“文档信息”两列表格。Artifact 名称、Workflow、Stage、状态、版本和生成时间等信息多与工作区上下文重复，价值低于正文，却优先消耗首屏和流式生成早期注意力。

### 已知证据

- 至少 `TEST_DESIGN/CLARIFY`、`TEST_DESIGN/DELIVERY`、`VALUE_DISCOVERY/BLUEPRINT` 和四个 `PRD_REVIEW` stage 的 deterministic renderer 会在标题后立即输出元信息表。
- CLARIFY partial renderer 还会把 `document_info` 作为首个有效增量。
- CLARIFY、DELIVERY、BLUEPRINT 的 frontend template 已把同类信息定义为文末“附录”，与 deterministic renderer 的实际顺序不一致。

### 方案边界

默认候选是把纯文档元信息移到文末，以紧凑附录、短键值行或折叠摘要展示。备选是在 `ArtifactPane` 共享布局中提供右下角、页脚或折叠元信息区；只有在窄屏、长文滚动、编辑/预览切换、版本恢复、Markdown/PDF 导出和无障碍访问下均不遮挡正文时才可采用。

`document_info` 仍作为 artifact schema、持久化、版本、handoff 和导出的结构化事实保留。全阶段盘点必须区分纯文档元信息与事件概要、评审结论、执行摘要等业务正文，后者不得因标题相似而降级。

### 验收规则

- 25 个 stage 均完成“纯元信息 / 业务摘要”分类，所有业务正文优先显示。
- `document_info` 不再以首段大型表格出现，也不再成为 `QG-018` 的首个右侧流式增量。
- partial 与 final renderer 的章节顺序一致，结构化数据、持久化、版本恢复、handoff 与导出语义不丢失。
- 每个 workflow 至少一条窄右栏 DOM 证据，覆盖首屏、长文滚动与元信息可发现性；共享前端测试覆盖编辑/预览、版本恢复和导出。

## QG-020 — New Agents 真实链路、无头优先的功能测试重构

### 用户目标与范围

测试保障只聚焦 `tools/new-agents/`，本项不改动、不扩展 `tools/intent-tester/`。用户明确不追求截图回归、像素级比对或精细视觉差异，优先保障以下功能事实：

- 模型输出能够通过当前 workflow/stage 的 `AgentTurnOutput`、`artifact_data`、业务不变量与视觉数据契约校验。
- typed SSE 在真实模型响应下持续产生有效增量，前端能够持续、单调地渲染对话和产出物，而不是只在最终事件一次性出现。
- 完成当前阶段后能够按 manifest 和运行状态正确流转到下一阶段，并保留 run、message、artifact、version、context summary 与 handoff 所需事实。
- 断流、provider 错误、schema 错误和阶段门禁失败必须显式、可诊断，不允许 mock、fallback、重试假通过或伪造成功掩盖失败。

### 已批准的测试模式

采用“开发内环确定性测试 + PR 关键真实链路 + Nightly/发布全量真实矩阵”的分层模式：

1. **开发内环 / 每次相关改动**：运行受影响 stage 的 schema、renderer、partial parser、typed SSE parser/store、DOM 状态和阶段状态机测试。该层不依赖外部模型，目标是秒级或分钟级反馈，并作为 TDD 的 RED/GREEN 证据。
2. **提交前 / PR 门禁**：使用无头 Chromium，启动真实 frontend、backend、数据库和共享 `/api/agent/runs/stream`，调用真实 DeepSeek。选择少量但贯穿 Lisa、Alex 的关键顺序旅程，验证真实 provider token 到 SSE、前端 DOM、持久化和下一阶段的完整链路。
3. **Nightly / 发布门禁**：对 manifest 中 7 个 workflow、25 个在线 stage 运行真实模型格式与流式矩阵；发布门禁再覆盖每个 workflow 的顺序流转旅程。新增 workflow/stage 未进入矩阵时机械失败。

PR 层追求高频、较短反馈；Nightly 与发布层承担广度和真实模型波动观察。真实测试不得用 `page.route` mock `/api/agent/runs/stream`、snapshot、artifact version、handoff 或 packet 等本次旅程涉及的关键 API；mock SSE 只保留给开发内环的故障注入和边界单测。

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
- CI 使用同名 GitHub Actions Secrets。PR 真实门禁仅在受信任分支/事件上运行，外部 fork 不获得密钥；具体 fork 策略在 spec 阶段确定。
- 当前根目录 `.env` 尚未配置上述 DeepSeek 变量。用户后续补充 API Key 后再执行真实调用；缺少凭证不阻塞本待办记录，但阻塞真实证据验收。

### 验收规则

- 提供按 workflow/stage 选择范围的统一命令，开发者能在本地无头运行单 stage、单 workflow、PR 关键集和全量矩阵。
- PR 关键集至少包含一个 Lisa 和一个 Alex 的真实顺序旅程，并覆盖结构化格式、多个流式增量、浏览器渐进 DOM、服务端持久化和至少一次合法阶段推进。
- Nightly 对 25/25 stage 产生真实 provider 证据；发布门禁对 7/7 workflow 产生顺序流转证据，失败报告能定位 workflow、stage、run、事件阶段与错误类型，但不泄露 prompt 中的敏感值或 API Key。
- `QG-017`、`QG-018` 实现后，其核心时序与分段行为必须进入 PR 关键真实链路；`QG-019` 只做 DOM 结构和信息顺序断言，不引入视觉快照。
- CI 与本地命令的选择逻辑、凭证加载和结果语义一致；必跑范围不得静默 skip，偶发 provider 波动必须被单独标记和统计，不得用无限重试稀释真实失败。

## 组合后的用户顺序

前三项组合验收时，用户可见顺序必须是：

1. 左侧出现有意义的自然对话。
2. 右侧出现首个可校验的业务正文段落。
3. 后续正文按章节持续累积并收敛到最终产出物。
4. 低权重文档元信息在尾部或独立轻量区保持可发现、可读取。

## Goal Mode 执行与停止线

本轮已经启动实现，必须按 `QG-017 → QG-018 → QG-019 → QG-020` 逐项完成设计、计划、TDD、正式审查、验证、证据记录和独立交付；前一项未满足完成定义时不得进入下一项。`QG-020` 单独形成测试基础设施重构 spec，并把前三项的真实回归证据纳入分层门禁。不得恢复旧 `QS-05～QS-08`、旧 P2/P3 backlog 或归档 E 编号。
