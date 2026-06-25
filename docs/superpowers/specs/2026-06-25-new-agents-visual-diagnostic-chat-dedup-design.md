# New Agents 可视化诊断左侧重复提示收束设计

## Current State Gap Analysis

### 事实源快照

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、剩余活跃 `docs/todos/*.md`、`tools/new-agents/frontend/src/components/ChatPane.tsx`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、对应组件测试。
- 当前工作区：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`、`tools/intent-tester/test-results/proxy/junit.xml` 是既有脏文件，本轮不触碰、不 stage。
- 本轮允许写入：`tools/new-agents/frontend/src/components/ChatPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`、必要的 `ArtifactPane` 测试、本 spec、配套 plan 和对应 todo 记录。

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 左侧重复可视化诊断提示收束 | `docs/todos/2026-06-25-new-agents-artifact-visual-diagnostic-duplicate-notice.md`；`ChatPane` 当前渲染 `右侧产物有可视化需要处理` 大卡片 | 用户遇到右侧图表/结构化可视化错误 -> 右侧 Artifact 保留诊断入口和定位锚点 -> 左侧对话不重复大卡片 | 只删 UI 不加测试会回归；只改测试不删卡片无法解决截图问题 | `ChatPane` 不渲染重复卡片测试；`ArtifactPane` 诊断入口/定位锚点测试 |
| 产出物去表格化审计 | 格式审计 todo | 右侧文档阅读更自然，表格只用于追溯和比较 | 跨 renderer、prompt 和导出，适合后续较大能力包 | renderer/prompt/导出测试 |
| 本轮 Diff 标识 | diff 标识 todo | 用户审阅新增/删除变化但不污染 Markdown | 需要 UI 状态和复制/导出保护 | diff/ArtifactPane 测试 |
| 左侧自然聊天可读性 | chat 可读性 todo | 自然短段落与按需列表并存 | 涉及 prompt 和 Markdown 渲染 | prompt/ChatPane 测试 |

### 排序结论

本轮选择“左侧重复可视化诊断提示收束”。它直接对应用户截图反馈，风险低，且能在共享前端组件内形成完整闭环。其他三个待办保留为后续能力包。

### 切片厚度门禁

- 入口：New Agents 工作区左侧 ChatPane 和右侧 ArtifactPane。
- 动作：用户生成的 Artifact 中存在 Mermaid 或 `ai4se-visual` 诊断。
- 处理：右侧 ArtifactPane 记录诊断、展示诊断入口、支持定位；左侧 ChatPane 不再重复渲染大卡片。
- 可见结果：左侧对话区不再出现 `右侧产物有可视化需要处理`，右侧仍显示具体诊断并可定位问题块。
- 状态承接：不改变 `artifactVisualDiagnostics` store、focus request、Agent Runtime SSE、错误 taxonomy 或重试逻辑。
- 失败反馈：真实可视化错误仍在右侧暴露，不伪造渲染成功。
- 证据：组件测试覆盖左侧不渲染重复卡片和右侧诊断锚点仍存在。
- 结论：通过。

## Superpowers 自问自答

### Explore Project Context

`ChatPane.tsx` 当前订阅 `artifactVisualDiagnostics`，根据当前 stage 取 `currentArtifactVisualDiagnostic`，在消息列表后额外渲染一张 amber 提示卡。该卡包含标题、固定正文、详情展开和“查看问题位置”。用户反馈的重复提示正是这块 UI。

`ArtifactPane.tsx` 已在 Mermaid 和 structured visual 渲染块外添加 `data-artifact-visual-diagnostic-id`，记录 `artifactVisualDiagnostics`，并在 focus request 到来时滚动和高亮对应块。右侧现有测试已经覆盖 invalid visual 记录诊断、focus 后定位和 read-only history 不附加诊断锚点。

### Visual Companion Decision

本轮不是重新设计错误展示，而是删除重复入口并保留右侧既有诊断能力，不需要视觉 companion。

### Clarifying Questions

- 用户是谁：在 New Agents 工作区审阅右侧 Artifact 的用户。
- 用户要完成什么：知道右侧可视化有问题并定位处理，但不被左侧重复大卡片打断阅读。
- 成功状态是什么：左侧不出现重复标题/正文/按钮；右侧仍能显示诊断详情和定位锚点。
- 输入来源是什么：ArtifactPane 对 Mermaid 或 `ai4se-visual` 的渲染/校验失败。
- 失败路径是什么：如果右侧诊断仍存在，错误不隐藏；如果诊断属于其他 stage，左侧也不显示。
- 不做什么：不改后端错误 code、不改 SSE、不删除右侧诊断、不新增 Lisa 专属分支。

### Approaches

1. 推荐：完全移除 ChatPane 的 artifact visual diagnostic 大卡片。优点是直接消除重复，代码更简单，右侧仍是单一处理入口；缺点是左侧不再提供快捷 focus 按钮，但用户反馈明确认为左侧重复。
2. 不选：把左侧卡片改成更小的状态 chip。它仍会重复同一错误信息，且 todo 要求右侧已有入口时左侧不再重复。
3. 不选：隐藏右侧诊断只保留左侧入口。这会把问题定位能力从实际出错块旁边移走，降低诊断效率。

### Presented Design

`ChatPane.tsx` 删除对 `artifactVisualDiagnostics` 和 `focusArtifactVisualDiagnostic` 的订阅，移除 `currentArtifactVisualDiagnostic`、`isVisualDiagnosticExpanded` state 和底部诊断卡渲染。这样左侧消息流只负责聊天、普通错误恢复和阶段确认，不再承载右侧 Artifact 视觉诊断入口。

`ArtifactPane.tsx` 不改运行时行为。右侧继续负责记录当前阶段 visual diagnostic、展示具体错误、挂载定位锚点，并响应 focus request。由于左侧不再触发 focus request，本轮测试重点转为证明右侧诊断锚点仍存在且诊断记录仍写入 store。

## 验收条件

1. Given 当前阶段存在 `artifactVisualDiagnostics`，When 渲染 `ChatPane`，Then 左侧不出现 `右侧产物有可视化需要处理`、`查看诊断详情` 或 `查看问题位置`。
2. Given 另一阶段存在 `artifactVisualDiagnostics`，When 渲染 `ChatPane`，Then 左侧仍不显示任何 artifact visual diagnostic 卡片。
3. Given 当前 Artifact 中有非法 `ai4se-visual`，When 渲染 `ArtifactPane`，Then 右侧仍显示 `结构化可视化格式错误`，store 中仍记录当前 stage diagnostic。
4. Given 当前 Artifact 中有 Mermaid 诊断且 focus request 存在，When 渲染 `ArtifactPane`，Then 对应块仍带有 `data-artifact-visual-diagnostic-id` 和 focused 标记。

## 非目标

- 不改变后端错误 code taxonomy。
- 不隐藏右侧产物中的真实可视化错误。
- 不伪造可视化渲染成功。
- 不为 Lisa 创建专属错误展示逻辑。
