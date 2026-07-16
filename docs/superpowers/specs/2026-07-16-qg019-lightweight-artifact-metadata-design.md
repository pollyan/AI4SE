# QG-019 产出物元信息文末轻量化设计

## 状态与事实基线

- 日期：2026-07-16
- 当前分支 / 基线：`master` / `cb2fb87e`
- 顺序来源：[`New Agents 双栏流式、产出物信息层级与真实链路测试待办`](../../todos/2026-07-16-new-agents-streaming-and-artifact-ux.md) 中的 `QG-017 → QG-018 → QG-019 → QG-020`
- 当前工作区保护边界：`tools/intent-tester/test-results/proxy/junit.xml` 是测试 runner 生成且不属于本切片的未提交文件，禁止修改、回滚或暂存；QG-020 不进入本切片。
- 已读取事实源：`AGENTS.md`、目标模式 Playbook、活跃 todo、`workflow_manifest.json`、25-stage `ARTIFACT_DATA_RENDERERS`、`ArtifactRenderPlan`、结构化 schema、Markdown renderer、frontend prompt/template、`ArtifactPane`、历史版本/导出路径及现有 backend/frontend/browser 测试。
- 当前质量门：QG-018 已经正式审查、全量验证并以 `cb2fb87e` 推送；没有新的 P0/P1、远端失败或外部阻塞。真实模型凭证不是本切片依赖。

## 目标承接检查

用户已经确认 QG-019 的顺序、边界和验收，QG-018 的完成证据与远端提交均可定位。当前代码仍证明该问题存在：6 个 render-plan shape 把 metadata 标为独立 section，其中 CLARIFY、DELIVERY、VALUE/BLUEPRINT 与四个 PRD stage 会把大型信息表放在正文前部；REVIEW、REPORT、IMPROVEMENT 的 metadata section 又混入不可降级的业务摘要。既定顺序和厚切片仍成立，因此继续承接 QG-019，不升级完整 CGA，也不改道 QG-020。

Playbook 要求跨 workflow 契约和真实 UI 证据可并行时实际分发。本切片在设计期派发两个只读旁路审计：25-stage 元信息分类审计与 frontend/导出影响审计；主 Agent 保留方案、实现、diff、验证和交付责任。

## 厚切片身份基线

- **ID / 名称**：QG-019 / 产出物元信息退出首屏重表格。
- **完整用户任务**：用户在任一 New Agents workflow 生成或恢复产出物时，右栏首屏先看到业务正文；纯文档元信息如仍需展示，只在文末以紧凑、可发现的文本附注出现，而需求摘要、评审结论、事件严重度等业务内容仍留在正文层级。
- **纳入边界**：25 个在线 stage 的 metadata 分类；共享 render-plan 顺序不变量；混合 section 的业务/元信息拆分；compact footer renderer；partial/final 同序收敛；窄右栏 DOM、编辑/预览、历史恢复、Markdown/DOCX 导出证据；相关 prompt/template 与事实文档同步。
- **排除边界**：不改 artifact schema、typed SSE、持久化结构、版本语义、handoff contract、工作流阶段、右下角悬浮 UI、折叠面板、截图/像素回归和 QG-020 真实模型基础设施。
- **依赖**：沿用 QG-018 的 `ArtifactSectionSpec.role` 与共享 `ArtifactRenderPlan`；结构化 `artifact_data` 始终是持久事实。
- **入口**：用户进入任一 workflow workspace，生成、恢复或导出当前 stage 的产出物。
- **动作**：用户阅读右栏业务正文，并在需要时滚动到文末查看文档元信息、编辑/预览、恢复历史版本或导出。
- **处理**：backend 按 section role 将业务内容稳定排在 metadata 前；混合对象通过两个投影保留业务字段；纯元信息由共享紧凑 renderer 输出；frontend 继续消费同一 Markdown 和持久化版本。
- **可见结果**：首个右侧增量和最终首屏均为业务正文；可见元信息位于末尾、不是表格且可读取；所有现有数据和下游语义不丢失。
- **状态承接**：final Markdown、`artifact_data`、artifact version、恢复内容与导出内容保持同一顺序；不创建第二份 metadata 状态。
- **失败反馈**：未知 role、metadata 先于 business、混合业务字段遗漏、partial/final 漂移或导出丢失由确定性测试显式失败；不以 silent reorder fallback 掩盖错误配置。
- **证据**：25/25 stage 机械分类与 final/partial 顺序测试；代表性混合字段测试；7/7 workflow 窄栏 DOM；编辑/恢复/Markdown/DOCX 保真测试；相关全量 runner、正式 Spec/Standards 审查。
- **单一交付边界**：上述用户可见信息层级、结构化保留和消费方证据必须在一个聚焦 commit 中同时成立；内部 RED/GREEN 步骤不是独立切片或交付点。

## 用户、输入与成功状态

主要用户是使用 Lisa/Alex 阅读产出物的产品、研发和测试人员。输入是 provider 逐步补全并最终通过 stage schema 的 `artifact_data`，以及服务端恢复的历史 Markdown。成功状态满足：

1. 标题之后第一个完成 section 必须是业务正文，metadata-only partial 不产生右栏增量。
2. 已显示业务 section 按 QG-018 规则单调累积；metadata 即使先到，也只会在有业务正文后出现在当前文档末尾。
3. final Markdown 的所有 business section 先于 metadata section；可见 metadata 是一条或少量紧凑文本，不使用两列表格。
4. 需求概述、评审结论、交付状态、严重等级、行动数量、产品方向等业务内容不得被错误塞进低权重 footer。
5. 结构化字段、持久化、版本恢复、handoff 和 Markdown/DOCX 导出不丢失。

## 25-stage 分类

分类以当前 manifest 和 render-plan registry 为准，不新增并行 source of truth：测试从 registry 读取 stage key，再验证 role 与输出不变量。

| Workflow / stage | 当前可见元信息 | 目标分类 |
| --- | --- | --- |
| `TEST_DESIGN/CLARIFY` | `document_info` 大表 | 纯元信息，compact footer |
| `TEST_DESIGN/STRATEGY`、`CASES` | `document_info` 仅保留在结构化数据 | 增加文末 compact footer，统一可发现性 |
| `TEST_DESIGN/DELIVERY` | `document_info + delivery_metrics` 混合大表 | 项目、交付状态、用例/风险数量为业务概览；artifact/workflow/stage/status/version/generated_at 为 footer |
| `REQ_REVIEW/REVIEW` | `review_info` 混合表 | 需求名称、需求概述、结论倾向为业务上下文；artifact 名称、评审时间为 footer |
| `REQ_REVIEW/REPORT` | 结论后 `review_info` 表 | 需求名称、评审输入、参与方为业务上下文；artifact 名称、评审时间为 footer |
| `INCIDENT_REVIEW/TIMELINE`、`ROOT_CAUSE` | 无纯文档元信息 section | 无 footer，不把事件概要/分析上下文误分类 |
| `INCIDENT_REVIEW/IMPROVEMENT` | `report_info` 混合表 | 故障、严重度、行动数、复查日期、关闭状态为业务概览；版本和生成时间为 footer |
| `IDEA_BRAINSTORM/*`（4 stages） | 无纯文档元信息 section | 无 footer，问题/创意/决策摘要均为业务正文 |
| `VALUE_DISCOVERY/ELEVATOR`、`PERSONA`、`JOURNEY` | `document_info` 未独立渲染；前两者还把 Artifact 名称混入业务摘要 | 移除摘要中的 Artifact 名称，并增加文末 compact footer |
| `VALUE_DISCOVERY/BLUEPRINT` | `document_info` 大表 | 产品方向为业务概览；版本、日期、artifact 名称、蓝图状态为 footer；产品名继续用于标题 |
| `STORY_BREAKDOWN/*`（4 stages） | `document_info` 仅保留在结构化数据 | 共用 plan 增加文末 compact footer |
| `PRD_REVIEW/*`（4 stages） | `document_info` 大表 | 纯元信息，compact footer |

合计 25 个在线 stage：19 个 stage 显示 compact footer，6 个 stage 没有可附加的纯文档元信息。25 个 stage 注册对应 22 个独立 plan 对象和 19 个独立 artifact schema shape；测试按 registry stage key 计数，避免把共享 plan 或共享 model 误当成 stage。

## 方案比较与决定

### 方案 A：只把现有表格挪到文末

改动最小，但 DELIVERY、REVIEW、REPORT、IMPROVEMENT 和 BLUEPRINT 的现有 section 混入业务字段；整体后移会让重要摘要降级，表格仍然占用大量文末空间，也无法机械阻止未来 metadata 回到前部。不采用。

### 方案 B：共享 role 排序 + 混合 section 拆分 + compact footer（采用）

`ArtifactRenderPlan` 以已声明的 `role` 生成唯一 canonical section order：所有 `business` 保持配置相对顺序，所有 `metadata` 保持配置相对顺序并形成尾部 suffix。混合模型使用业务 renderer 与 metadata renderer 两个只读投影，不改 schema。共享 helper 保留既有元信息标题锚点，在标题下渲染一行紧凑文本，不生成表格或字面分隔符。该方案同时解决首屏、信息权重、partial/final 一致性、历史 section lock 兼容和未来 stage 漂移，且不引入第二状态源。

### 方案 C：ArtifactPane 右下角悬浮/折叠 metadata 区

可更强地从正文分离，但需要新的 frontend 状态、窄屏遮挡与可访问性处理，还要定义编辑、版本恢复、Markdown/DOCX 导出时如何合并，风险和维护面明显更大。用户允许文末方案，因此本切片不采用；以后若真实可用性证据证明 footer 仍干扰阅读，再作为独立候选评估。

## 架构与组件

### `ArtifactRenderPlan`

- 新增受校验的 canonical section order，role 只允许 `business | metadata`；重复 section id 或未知 role 必须显式失败。
- `render_available()` 与 `render_complete()` 必须遍历同一 canonical order，`completed_section_ids` 与 Markdown 顺序一致。
- metadata-only 输入仍返回 `None`；一旦业务 section 有效，当前已完成 metadata 只作为 suffix 附加，不影响业务 section 的局部有效性。

### renderer 与 schema

- 在共享 renderer base 提供 compact metadata helper，负责校验 H1-H3 标题、转义普通 Markdown/HTML 行内值并拒绝空键值；各 workflow 只声明既有标题、字段标签和值，不复制布局。
- 不修改 Pydantic schema，也不移动或删除 `document_info/review_info/report_info/delivery_metrics` 字段。
- 对五类混合 section 创建业务投影与 metadata 投影；投影依赖仍使用 QG-018 的字段级类型和业务不变量校验。
- 对已有 `document_info` 但过去未显示的 9 个 stage 增加同一行 footer；额外占用被限制为一个标题和一个文本行，换取全 workflow 的可发现性与一致分类。

### frontend 与下游

- `ArtifactPane`、store、typed SSE、历史版本和 persistence 不需要新的生产分支；最终 Markdown 是唯一可见顺序。
- preview/code/edit/history 均消费同一字符串；metadata 标题形成独立稳定 preview chunk，现有标题保持 section lock anchor；Markdown 下载保持字节级内容，DOCX parser 把 compact footer 当普通标题和段落保留。
- browser 只验证 DOM 顺序、首屏、滚动到底部后的可发现性和内容保真，不使用截图或像素差异。

## 数据流

1. provider 继续输出原 schema 的 `artifact_data`。
2. partial parser 将当前完整顶层字段交给 stage 对应 `ArtifactRenderPlan`。
3. plan 校验字段与投影，按 canonical role order 渲染已完成业务 section；已完成 metadata 仅附加到末尾。
4. typed SSE 继续发送 replace Markdown；frontend 按 QG-018 的单调规则更新右栏。
5. final 完整 model validation 后使用同一 plan 输出 exact Markdown，服务端记录原始结构化数据与最终版本。
6. 恢复、编辑、handoff 和导出继续读取既有持久事实；没有 reverse parsing 或 metadata 旁路存储。

## 错误处理与风险

- 未知 role、重复 section id、无 business section 的 plan：配置错误，测试和构造时失败，不默认当 business。
- compact footer 中的换行、`|`、强调符或 HTML：共享 helper 统一生成安全实体，禁止注入新的表格、标题或内联样式；preview 按 Markdown 实体显示原文，DOCX/PDF 在剥离 Markdown 后统一解码，原结构化值与导出可见文本不变。
- 混合字段错误分类：专项测试精确断言业务词出现在正文 section、纯元信息只出现在 footer。
- partial 字段尚未完整：维持 QG-018 的 section 隔离；不生成占位 footer。
- 历史 artifact 已包含旧表格：不迁移或改写历史版本；新生成/新保存版本使用新顺序，历史恢复忠实显示当时内容。既有 `文档信息/评审信息/报告信息` 标题和级别保持，已锁定 section 不会因找不到 anchor 被重复追加。
- Markdown heading contract：compact footer 保留独立标题以维持流式 preview chunk 稳定和历史 lock anchor；它的 `role="metadata"` 而非标题文字决定展示层级。prompt/template 的尾部信息示例同步为同一轻量格式。

## 测试设计

### RED / deterministic backend

- 为 `ArtifactRenderPlan` 增加未知 role、重复 id、canonical business→metadata、metadata-only gate、partial/final exact order 测试。
- 参数化 25/25 stage fixtures：registry 与 manifest 同步；完成输出的 role 序列只能是 business prefix + metadata suffix；第一个可见 section 是 business；19 个 stage 的 metadata section 都是 compact 非表格，6 个 stage 不伪造 metadata；全部结构化字段仍存在于 normalized artifact data。
- 为 DELIVERY、REQ REVIEW/REPORT、INCIDENT IMPROVEMENT、VALUE BLUEPRINT 精确断言混合业务字段与 footer 字段的归属和相对位置。

### frontend / browser

- 真实 React `ArtifactPane` 在窄右栏中对 7/7 workflow 各运行一条 mock typed SSE：首屏业务 marker 在 metadata marker 之前；长文可滚动；6 个含纯元信息的代表 workflow 滚到底部后可读取 compact footer；Idea workflow 不伪造 footer且不出现大型“文档信息”表。
- preview 与 code/edit 看到同一顺序；历史版本预览/恢复不重排；Markdown 下载内容一致；DOCX 生成包包含 footer 文本且位于业务文本之后。
- 不新增截图基线，不对像素或精确坐标做门禁。

### 回归与完成型验证

- backend renderer/runtime/stream/persistence 聚焦集与 backend 全量。
- frontend ArtifactPane、stream、history、export 聚焦集，随后 frontend 全量、lint、build。
- 新增 browser 用例、browser 全量、`./scripts/test/test-local.sh new-agents` 与全仓 runner。
- 关键 Python flake8、`git diff --check`；正式 Spec/Standards 审查关闭所有 Critical/Important。

## 实现与审查闭环

- 25 个 stage 的最终分类为 19 个 visible compact footer、6 个无纯元信息 footer；业务正文、metadata suffix、partial/final convergence 和 normalized artifact data 均由共享 plan 参数化验证。
- mixed section 的业务字段与元信息字段已分别投影，且 `document_info` 声明的 workflow/stage 必须匹配 runtime identity；Story 指令写入真实当前 stage，不再依赖测试夹具掩盖身份错误。
- preview/code/edit、section lock、历史恢复、Markdown、DOCX、PDF 和 7-workflow 1024×800 headless browser consumer 证据均已闭合；安全实体在 Markdown 显示和导出文本中无损往返。
- manifest required headings 与 renderer 静态 headings 使用 25-stage 双向精确 tracer，19 个相关 prompt/template version 统一为 `2026.07.16.1`。Spec 与 Standards 审查最终均为 PASS，无 Critical、Important 或 Minor 遗留。
- 最终证据：backend `1092 passed, 1 skipped`；frontend `62 files / 928 passed`，lint/build 通过；browser `32 passed, 3 skipped`；New Agents runner 与使用仓库 Python 3.11 PATH 的全仓 runner 均通过；flake8、Black check、`git diff --check` 通过。

## 下游承接与非目标

QG-019 完成并独立推送后，唯一下一入口是 QG-020 ASSESS。QG-020 会把前三项行为纳入真实 DeepSeek/真实 backend/SSE/persistence/headless Chromium 分层门禁；本切片不提前建立真实模型 runner，也不把 mock browser 证据描述为真实模型证据。
