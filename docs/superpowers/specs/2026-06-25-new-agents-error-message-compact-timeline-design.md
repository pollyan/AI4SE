# New Agents 错误信息低占用时间线展示设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-subagents.md`、`docs/strategy/goal-mode-ci-verification.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、`docs/CODING_STANDARDS.md`、`docs/DESIGN_PRINCIPLES.md`、`docs/integration-architecture.md`、`docs/component-inventory.md`、`docs/todos/refactor/README.md`。
- 本轮 todo：`docs/todos/refactor/2026-06-25-new-agents-error-message-placement-ux.md`、`docs/todos/refactor/2026-06-25-new-agents-test-strategy-artifact-format-regression.md`、`docs/todos/refactor/2026-06-25-new-agents-artifact-streaming-deep-diagnosis.md`。
- 本轮代码：`tools/new-agents/frontend/src/components/ChatPane.tsx`、`tools/new-agents/frontend/src/services/chatService.ts`、`tools/new-agents/frontend/src/store.ts`、`tools/new-agents/frontend/src/core/types.ts` 及相关测试。
- 当前 `git status --short`：仅有无关生成物 `dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`、`tools/intent-tester/test-results/proxy/junit.xml`，本轮不触碰。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 错误提示低占用时间线展示 | 错误块位置、错误详情占用空间、概要与详情重复、右侧产物可视化诊断 notice 固定在对话顶部、错误不污染 prompt | 用户发起生成 -> 失败或右侧产物渲染异常 -> 在最新消息位置看到短摘要 -> 按需展开详情 -> 重试/设置/定位问题/补充信息 | 只改文案不能解决占用和 prompt 污染；只加折叠不解决时间线和重试动作；只移动 notice 不解决原始错误铺满对话 | `chatService.test.ts`、`ChatPane.test.tsx`、`llm.test.ts`、全量本地自动化 |
| STRATEGY 格式错误真实根因 | 第二阶段测试策略格式错误、外部 judge 质量缺口 | 本地真实运行 -> 捕获 SSE / Markdown / 截图 -> 定位首次错误层级 -> 修复共享 contract | 缺少真实失败 payload，直接改 prompt 或 renderer 会违反系统性调试 | 下一轮真实 payload、renderer/runtime/frontend 回归测试 |
| 右侧产物流式真实模型复核 | 段落级流式确定性修复后的 provider smoke | 真实模型运行 -> 捕获右侧段落增量 -> 确认或记录 provider 限制 | 代码主缺口已确定性修复，剩余依赖外部模型配置 | 本地部署 smoke、SSE 日志、截图序列 |

排序结论：
1. 选择“错误提示低占用时间线展示”，因为用户反馈明确、能独立交付可见体验改进、不依赖外部模型，且可用确定性前端测试完整验证。
2. STRATEGY 格式错误保留为下一轮候选，必须先采集真实失败证据后再修复。
3. 右侧产物流式复核保留为部署 / provider smoke 候选，不与本轮 UI 错误体验混做。

切片准入判断：
- 用户功能包边界：本轮只处理 New Agents 左侧对话中的运行失败提示。保留现有结构化失败重试、provider 设置/检测、停止生成、pending stage transition 行为。
- 用户可感知动作链：用户生成失败 -> 最新对话位置出现低占用错误摘要 -> 用户点击展开查看 code/message/details -> 用户选择重试、打开设置、检测连接或补充信息。
- 相邻缺口合并：合并错误位置、默认折叠、详情入口、prompt 过滤、重试动作保留。
- 过薄风险检查：不是单按钮或单样式调整；它改变错误反馈的状态承接和用户排障闭环。
- 能力增量句：完成后，用户现在可以在最新对话位置看到低占用错误摘要，并按需展开完整诊断信息继续处理失败。

切片厚度门禁：
- 入口：New Agents `ChatPane` 左侧对话。
- 动作：Agent Runtime 或前端解析失败后，用户查看失败反馈并决定下一步。
- 处理：`chatService` 把错误概要和详情写成结构化消息元数据，`ChatPane` 用折叠 UI 渲染。
- 可见结果：默认只显示短摘要和可展开入口，完整错误详情被折叠。
- 状态承接：重试、补充信息、打开模型设置、检测连接保持可用；错误详情不作为下一轮业务 prompt。
- 失败反馈：无法生成时仍显式说明失败，不伪装成功，不隐藏诊断入口。
- 证据：服务测试验证消息元数据，组件测试验证折叠/展开和时间线位置，prompt 测试验证过滤，目标模式全量本地自动化验证。
- 结论：通过。

本轮用户故事：
作为 New Agents 使用者，当生成过程失败时，我可以在最新对话位置看到简短错误摘要，并按需展开完整错误详情，从而在不被大块错误信息打断的情况下继续重试、配置模型或补充信息。

验收条件：
1. Given 生成首帧前失败，When 前端捕获错误，Then 最新 assistant 消息显示短摘要并携带折叠详情。Evidence: `chatService.test.ts`。
2. Given 生成中途失败，When 已有 assistant 消息存在，Then 错误摘要追加到该最新消息而不是产生顶部固定错误块。Evidence: `chatService.test.ts`、`ChatPane.test.tsx`。
3. Given 用户未展开错误详情，When 查看对话流，Then 默认不显示原始 code/message/stack 长文本。Evidence: `ChatPane.test.tsx`。
4. Given 用户点击详情入口，When 错误卡片展开，Then 可查看完整原始错误和必要诊断字段，再次点击可收起。Evidence: `ChatPane.test.tsx`。
5. Given 下一轮继续生成，When 构造 runtime prompt，Then 结构化错误摘要和详情不进入 prompt。Evidence: `llm.test.ts`。

## Superpowers 自问自答

### Explore Project Context

`chatService.ts` 目前用 `formatAssistantErrorContent(...)` 生成 Markdown 文本，并在首帧前失败时创建 assistant 消息、在中途失败时追加到最后一条 assistant 消息。`ChatPane.tsx` 再通过关键短语识别结构化失败或 provider 失败，并渲染较大的 recovery card。provider 错误还会把原始错误附录写入 Markdown，导致主对话里出现长错误块。

`core/llm.ts` 已有过滤逻辑，测试覆盖 `**Error:**`、`*(已停止生成)*` 和 provider 控制反馈不进入 prompt。本轮需要保持这个边界，并补充对新结构化元数据 / 新摘要文案的过滤。

### Visual Companion Decision

本轮是已有工作台内的错误卡片行为调整，不需要单独视觉 companion。设计应沿用当前深色对话面板、lucide 图标、紧凑按钮和现有 recovery action 风格。

### Clarifying Questions

- 用户是谁？使用 New Agents 生成文档、测试策略或其他 artifact 的本地开发 / 演示用户。
- 成功状态是什么？用户看到失败发生在最新时间线位置，默认只占用一小块空间，点击后才看完整错误。
- 需要保留什么？结构化失败的重试本阶段、连续失败后的补充信息、provider 失败的设置 / 检测连接 / 重试。
- 不做什么？不改后端错误 taxonomy，不隐藏错误细节，不把错误伪装成成功，不为 Lisa 或某个 workflow 做专属 UI。
- 如何避免 prompt 污染？错误消息使用结构化 `errorDiagnostic` 元数据，业务 `content` 只保留短摘要；prompt 构造继续过滤控制反馈。

### Approaches

方案 A：继续用 Markdown 文本加 `<details>`。成本低，但错误详情仍会进入消息内容和 prompt 过滤黑名单，且 ReactMarkdown mock / copy 行为难以区分摘要与详情。

方案 B：在 `Message` 上新增 `errorDiagnostic` 元数据，由 `ChatPane` 渲染折叠卡片。成本适中，但能把业务回复、错误摘要和诊断详情分离，是推荐方案。

方案 C：放到全局 toast / floating drawer。占用更小，但会脱离消息时间线，不符合“错误是最新信息”的要求，也会削弱重试和设置动作与失败消息的关联。

推荐方案 B。

### Presented Design

Architecture：保持共享前端状态和 ChatPane 主路径，不新增 agent / workflow 专属 store 或 renderer。`Message` 增加可选 `errorDiagnostic`，旧持久化消息继续兼容。右侧产物可视化诊断继续使用现有 `artifactVisualDiagnostics`，只调整 `ChatPane` 中的展示位置和折叠形态。

Components：`chatService` 负责归因和生成结构化诊断；`ChatPane` 负责紧凑错误卡片、右侧产物诊断 notice、展开状态和 recovery actions；`store` 负责 sanitize / persist 新字段。

Data Flow：`generateResponseStream` 抛错 -> `chatService` 生成 `{ summary, kind, reason, action, rawMessage }` -> 追加或新增 assistant message -> `ChatPane` 在该消息位置渲染低占用卡片 -> 用户展开时显示详情。`ArtifactPane` 发现 Mermaid / StructuredVisual 诊断 -> 写入 `artifactVisualDiagnostics` -> `ChatPane` 在消息流之后展示紧凑产物诊断入口 -> 用户展开详情或定位右侧问题块。

Error Handling：错误仍显式展示，artifact 失败时保持右侧产物不变，部分产物失败时保持 `artifactTruncated`，停止生成仍使用停止反馈。

Testing：先写失败测试，再实现。聚焦测试覆盖服务、组件、prompt 过滤；最终按目标模式运行全量本地自动化和 CI 等价映射。
