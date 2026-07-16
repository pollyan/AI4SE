# QG-018 全阶段右侧分段流式设计

## 厚切片身份基线

- **ID / 名称**：`QG-018 — 25 个在线阶段统一分段流式`。
- **完整用户任务**：以 `TEST_DESIGN/CLARIFY` 的真实字段级体验为基准，让 manifest 中 7 个 workflow、25 个在线 stage 都在模型完成并闭合可校验业务结构后，立即把对应章节累积到右侧产出物；最终仍精确收敛到同一 deterministic Markdown，不回退、不闪烁、不伪造成功。
- **顺序基线**：[当前唯一活跃 Todo 的 QG-017 → QG-020 顺序](../../todos/2026-07-16-new-agents-streaming-and-artifact-ux.md#待办总览)。`QG-017` 已由提交 `8d00bb36` 完成并推送，本切片承接 QG-018；QG-019、QG-020 不得穿插。
- **纳入边界**：共享 artifact render plan；25-stage partial 能力与同步门禁；局部 schema、引用和 visual 校验；raw JSON partial → typed SSE → frontend mapper/store → `ArtifactPane` 的累计与回退防护；7-workflow 无头 DOM 分段证据；相关测试与事实文档。
- **排除边界**：不改变文档元信息位置或样式（QG-019）；不接入真实 DeepSeek、真实后端浏览器矩阵或 CI 分层（QG-020）；不修改 Intent Tester；不新增 workflow/stage 专属 endpoint、runtime、SSE、store 或前端 renderer；不恢复历史 Markdown reverse parsing/patch 方案。
- **七项门禁**：入口是任一 New Agents 在线 stage 的一次共享 `/api/agent/runs/stream` 调用；动作是用户发送本阶段输入；处理是 runtime 从同一 attempt 内 append-only 的 provider JSON 中识别已闭合顶层字段，并由共享 render plan 校验、渲染可用章节；可见结果是左侧自然对话后右侧至少三次业务章节更新并最终收敛；状态承接是当前 stage draft 在同一 attempt 内单调更新且成功时只保存一个 final artifact/version；失败反馈是无效 section 被暂扣、回退 replace 被显式拒绝、完整 contract 失败仍走 typed error/`agent_retry`；证据是 25-stage backend 矩阵、typed SSE/mapper/store tests 和 7-workflow headless DOM probe。
- **依赖 / 单一交付**：依赖已完成 QG-017 的 chat-first sequencer。只有本基线全部闭合、正式审查和完成型验证通过后，形成一个 QG-018 聚焦 commit 并推送；render plan、stage adapters、frontend gate、fixtures 和 browser probe 都是内部实现步骤，不是子切片。

## 当前事实与根因

manifest 当前有 7 个 workflow、25 个在线 stage；25 个 stage 都有 `artifactDataContract`、structured-output instruction、完整 Pydantic schema/final renderer 和 fixture。当前缺口不是 final contract，而是 partial seam：

- `agent_runtime.extract_partial_json_object_after_key()` 已能从尚未闭合的外层 JSON 中提取已闭合的 `artifact_data` 顶层 member。
- `render_partial_artifact_data_markdown()` 不是 registry，而是只识别 `TEST_DESIGN/CLARIFY` 的单个硬编码分支；其余 24 个 stage 返回 `None`。
- 其余阶段在完整 `artifact_data` 对象闭合后、最终 `agent_turn` 之前可能出现一次整文档 delta。现有若干名为 `paragraph_level` 的测试只要求一次 before-final 输出，不能证明两个业务章节逐段出现。
- frontend 会逐个消费合法 `replace`，但没有单调性门禁；任何较短但格式合法的 replace 都可覆盖较长草稿。terminal-only 的前端合成渐显也不是真实 provider partial 证据。
- browser fixtures 当前只发一个完整 artifact delta，只证明 QG-017 的 `chat → 首个 artifact`，没有证明两个服务端 delta 到两次独立 DOM 提交。
- 当前完整 schema 还存在两处会直接削弱局部门禁的 manifest 漂移：`TEST_DESIGN/CASES` 未强制 `stage_gate` 至少一项 checked；`INCIDENT_REVIEW/ROOT_CAUSE` 未强制 `why_chain[].level` 唯一和 `stage_gate` 至少一项 checked。QG-018 必须先以 RED 固化并修正，partial 不得比 final contract 更松。

历史代码曾用大段 stage `if/elif` 和 Markdown 标题 reverse parsing 生成 patch；该路线在旧合流中被删除。QG-018 不恢复这种双事实源实现。

## 用户、输入与成功状态

### 用户

Lisa/Alex 工作流的直接使用者，以及依赖 artifact draft、最终版本、handoff 和后续 stage 的调用方。

### 输入

- 已通过 QG-017 chat-first 顺序 seam 的 provider append-only JSON stream。
- `workflow_id`、`current_stage_id` 与当前 manifest stage key。
- `artifact_data` 中已经语法闭合的顶层字段；未闭合字符串、数组、对象不视为可用输入。

### 成功状态

1. 自然对话先出现；QG-017 sequencer 释放后，首个已验证业务 section 显示。
2. 后续 section 在各自依赖字段闭合并通过局部校验后加入同一 Markdown；已经显示的 section 内容不缩短、不消失、不被更改。
3. 缺失或无效 section 不撤回已经有效的 section；不依赖该 section 的后续合法 section可以出现，并按最终文档顺序定位。
4. 每个在线 stage 至少有三个不同业务 section snapshot 并最终收敛；25 个最终 snapshot 与完整 deterministic renderer 字节级一致。
5. 成功结束只持久化一个 final artifact/version；partial 不是历史版本、handoff 或阶段门禁的权威终态。

## 方案比较

### 方案 A：再写 24 个 `_render_partial_*`

表面改动直接，但会复制完整 renderer 的字段顺序、章节组合、引用规则和 visual 生成。新增或调整 stage 时容易只更新一侧，形成静默漂移。拒绝。

### 方案 B：完全依靠 Pydantic introspection，字段闭合就自动显示

接口最小，但顶层字段并不等于展示章节；一个章节可能依赖多个字段、跨 ID 引用、派生统计或可视化。纯 introspection 无法判断业务原子性，可能放行局部 schema 合法但引用/visual 不合法的内容。拒绝。

### 方案 C：完整与 partial 共用 `ArtifactRenderPlan`

采用。它把 19 种实际文档形态、25 个 stage adapter 背后的顺序、依赖、局部校验、section rendering 和 visual 安全封装在一个进程内深模块中。caller 只需知道 stage key 和 raw artifact data；新增 stage 必须通过同一 registry 和同步门禁。

`codebase-design` 对本方案的影响是：seam 放在“结构化业务数据 → 已验证 deterministic artifact”处；schema/section/visual 依赖是进程内纯计算，不引入多余 port 或 adapter。删除这个模块会让复杂度重新散回 25 个 stage、final/partial 两条路径和测试，因此该模块具有足够 depth 与 locality。

## 共享模块与接口

建议新增进程内模块 `artifact_render_plan.py`，外部 interface 只有两个主要入口：

```python
render_complete_artifact_data(stage_key, raw_artifact_data) -> RenderedArtifact
render_available_artifact_data(stage_key, closed_top_level_fields) -> RenderedArtifact | None
```

核心内部类型：

```python
ArtifactRenderPlan(
    model,
    title,
    sections,
)

ArtifactSectionSpec(
    id,
    dependencies,
    render,
    validate_projection=None,
)

RenderedArtifact(
    markdown,
    completed_section_ids,
    normalized_artifact_data=None,
)
```

- `ArtifactRenderPlan` 是一个 stage document shape 的唯一组合事实；完整和 partial 都使用同一 title/section 顺序与 renderer callable。
- `ARTIFACT_DATA_RENDERERS` 升级为 25 个 stage key 到 plan adapter 的单一 registry。Story Breakdown 的 4 个 key复用同一 plan；PRD Review 的 4 个 key各自注册 projection plan，不在 runtime/partial 层增加条件分支。
- 单字段 section 的局部类型从完整 model 的 `model_fields[field].annotation` 创建 `TypeAdapter`，不声明第二套 schema。
- 多字段、引用、统计或派生 section 使用小型 typed projection validator；现有 parent `model_validator` 中可复用的一致性逻辑抽为共享 helper，由 full model 和 partial projection 同时调用，不复制规则。
- `render_complete_artifact_data` 先执行完整 model validation，再通过同一 plan 渲染全部 section，并返回 normalized `artifact_data`。
- `render_available_artifact_data` 只消费已经闭合的字段。缺依赖或局部验证失败的 section 被暂扣；独立 section 继续评估。每个 section Markdown 单独通过 `validate_artifact_visual_blocks()` 后才能加入累计文档。
- title 不能单独构成 artifact delta；至少一个业务 section 合法才返回结果。QG-019 实施前仍保持现有元信息顺序，本切片不借机移动 section。

## 数据流与顺序

```text
provider append-only JSON
  → extract closed artifact_data members
  → render_available_artifact_data(stage_key, fields)
      → typed field/projection validation
      → deterministic section rendering
      → per-section visual validation
      → cumulative Markdown + completed section ids
  → QG-017 NaturalChatFirstDeltaSequencer
  → typed agent_delta replace
  → frontend SSE mapper monotonic replace guard
  → chatService current-stage draft
  → ArtifactPane keyed heading sections
  → complete model/final renderer
  → agent_turn + one durable final version
```

QG-017 前后端都可能在自然 chat 前只保留最新 artifact，因此 QG-018 不要求展示 chat 前产生的每个 provider partial。验收序列从首个权威自然 chat 开始计算。partial delta 不带 `NEXT_STAGE`，最终 `agent_turn` 仍是 stage action 与持久化的唯一权威。

## 单调性与前端防线

后端 provider 文本在同一模型 attempt 内是 append-only，已经闭合的顶层 JSON value 不会改变；plan 因而保证同一 attempt 内的 `section_id` 一旦完成，其 Markdown 内容稳定。新 section 可以追加或插入最终顺序，但不能修改/删除已完成 section。模型校验失败并重试时，typed `agent_retry` 划定新的 attempt；新 attempt 可以从更短的修正版重新累计，并重新执行 natural-chat-first。

frontend 在共享 SSE mapper 增加 artifact replace 单调门禁：

- 相同内容忽略；新内容可以扩展尚在形成的同一 section，或加入新的 heading anchor。
- 旧 heading anchor 必须仍存在，旧 section 内容必须保持相同或只做字符串前缀增长；删除、缩短或改写已完成 section视为显式 stream contract error。
- 该规则只约束一次模型 attempt 内的 `replace` delta；`agent_retry` 会重置 chat/artifact 单调基线，定向编辑的 `artifact_patch`、历史版本恢复和新 stage 切换使用各自现有 contract，不被误拦截。
- terminal-only 合成渐显作为历史兼容保留，但不计入 QG-018 的真实 partial 覆盖。

`ArtifactPane` 继续按稳定 heading anchor memo 渲染；插入一个此前暂扣的 section 时，已有 section key 与内容保持，测试必须证明未变化 section 不被重新渲染。

## 错误处理

- **未闭合 JSON**：不输出，不构造占位 section。
- **字段 schema 无效**：暂扣依赖该字段的 section；已显示 section 保留。完整对象最终仍失败并走既有 provider/schema retry 或 typed error。
- **引用/统计不一致**：projection validator 暂扣相关原子 section；不得用宽松校验或删字段让它通过。
- **Mermaid / `ai4se-visual` 不完整或无效**：相关 section 不发送；不把 visual fallback 或错误文本写入成功 artifact。
- **未知 stage / 缺 plan**：显式失败；同步测试必须在运行前机械发现。
- **frontend replace 回退**：抛出可诊断 stream contract error，旧 artifact 保持；不静默接受、不伪造 final。
- **最终 contract 失败**：不持久化新版本、不推进 stage；partial 可见内容不被当作成功或 handoff 来源。

## 测试设计

### RED/GREEN backend 矩阵

1. 直接集合相等：manifest 在线 stage keys = 带 artifactDataContract 的 keys = plan registry keys = instruction registry keys = fixture keys，必须为 25/25。
2. 对每个 fixture 按 model 顶层字段顺序逐个加入 closed field：至少得到两个 final 前的不同业务 snapshot；`completed_section_ids` 只增不减；每份 visual block 立即合法。
3. `render_available(full_fixture).markdown == render_complete(full_fixture).markdown`，并保持现有 renderer contract/headings/visual 测试绿色。
4. 破坏一个字段、引用和 visual：相关 section 被暂扣，先前有效 section 保留，独立合法 section可继续；完整 render 明确失败。
5. 为 `CASES` 增加全未 checked 的门禁 RED，为 `ROOT_CAUSE` 增加重复 Why level 与全未 checked 门禁 RED；修复后 manifest、full model 与 partial projection 使用同一约束 helper。
6. raw runtime 至少选择 Lisa `TEST_DESIGN/CLARIFY`、Lisa `REQ_REVIEW/REVIEW` 和 Alex `VALUE_DISCOVERY/ELEVATOR` 作为纵向 tracer，证明 chat 后产生 section-1、section-2、final typed delta，且没有 patch/stage action 提前。

### frontend mapper/store

- 表驱动输入 `chat → artifact-1 → artifact-2 → final`，断言 mapper 精确交付三份服务端累计稿而非 terminal synthetic frames。
- 输入回退 replace，断言显式 contract error 且旧稿不被覆盖。
- 用 promise gate 暂停每个 chunk，订阅 store snapshot：`isGenerating=true` 时 artifact-1、artifact-2 依次可见，历史版本仍为 0；成功后只保存 final 一版。
- 保留并增强 ArtifactPane section memo test，覆盖中间插入 section 时已有 section render count 不增加。

### 7-workflow headless DOM probe

新增一个共享、参数化 probe，覆盖首阶段：

- `TEST_DESIGN/CLARIFY`
- `REQ_REVIEW/REVIEW`
- `INCIDENT_REVIEW/TIMELINE`
- `IDEA_BRAINSTORM/DEFINE`
- `VALUE_DISCOVERY/ELEVATOR`
- `STORY_BREAKDOWN/INPUT_ANALYSIS`
- `PRD_REVIEW/INVENTORY`

fixture 使用浏览器内 `ReadableStream` 分时 enqueue typed SSE，仍经过 fetch/SSE parser、mapper、store 和真实 React DOM；不直接写 store、不截图。单个共享 MutationObserver 记录两个业务 marker 与 final marker，要求三者分属独立 DOM commit、section 集合单调、最终文本一致。现有完整 workflow E2E 继续验证 stage 流转，但不能替代本 probe。

## 下游承接与事实同步

- final `artifact_data`、artifact/version、context summary、handoff、story packet 与 stage transition contract 不变。
- QG-019 将只调整同一 plan 的 section 顺序/轻量元信息 presentation，不再维护另一套 partial 顺序；QG-018 必须先提供这个可复用 seam。
- QG-020 将把本切片的 25-stage backend matrix 与 7-workflow DOM 不变量接入真实 DeepSeek 分层门禁；本切片只提供确定性基础。
- 实现完成时更新 `docs/TESTING.md`、`tools/new-agents/CONTEXT.md` 与当前 Todo；不复制 Goal Mode 通用规则。

## 非目标

- 不追求 token/字符逐字动画；粒度是完整、可校验的业务 section。
- 不生成截图基线或像素 diff。
- 不用 Markdown reverse parsing判断后端 section 是否完成。
- 不把 manifest 自然语言 `modelOutputRules` 解析为运行时规则引擎。
- 不把 partial 保存成独立 artifact version，不让 partial 触发 handoff 或阶段推进。
- 不因为 QG-018 顺手改变元信息顺序、标题文案或专业内容结构。

## 设计假设与风险

- 假设 provider 的 raw response 对同一 attempt 是 append-only；若未来 transport 支持在 attempt 内修订历史 token，必须先扩展 stream contract，不能沿用本设计。
- 19 种文档 shape 的 section dependency 配置工作量较大，但它是允许的 code-level mirror；集合相等、full/partial exact convergence 和 25-stage fixture tests 必须机械保护它。
- 局部 projection validator 若遗漏 parent invariant 会造成半成品误放行。正式审查必须逐个核对现有 `model_validator` 与 section dependency；任何无法局部证明的 section 宁可暂扣到依赖齐全，也不能宽松放行。
- 浏览器 `ReadableStream` fixture 证明真实前端解析/状态/DOM，不证明真实网络、backend 或 provider；这些证据明确留给 QG-020，不能在交付说明中升级表述。
