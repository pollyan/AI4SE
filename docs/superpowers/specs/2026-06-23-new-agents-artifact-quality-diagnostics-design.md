# New Agents Artifact 质量诊断面板设计

## 背景

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 E03 标为 P0：用户需要在当前产物中直接看到产物是否满足 workflow/stage artifact contract、visual contract、阶段门禁和专业字段要求。现有前端只在 Mermaid 或 `ai4se-visual` 渲染失败时记录 `artifactVisualDiagnostics`，不能回答“这份产物整体是否符合当前阶段合同”。

## 目标

在共享 New Agents ArtifactPane 的“产物审阅”侧栏中增加质量诊断区，让所有 workflow 复用同一套 manifest-derived 诊断逻辑。诊断必须覆盖：

- artifact contract 中的 Markdown 标题要求。
- artifact contract 中非标题类专业字段或表格列要求。
- visual contract 中的 Mermaid 图表类型要求。
- visual contract 中的 `ai4se-visual` 结构化可视化类型要求。
- 阶段门禁章节是否存在，以及是否包含 checkbox 决策项。
- 当前阶段已有 Mermaid / structured visual 渲染诊断错误。

## 非目标

- 不新增 Lisa、Alex、DeepSeek 或未来 agent 专属 runtime、API path、store 或 renderer。
- 不做自动修复或 LLM 重新生成。
- 不持久化新的质量诊断数据；诊断从当前 artifact 内容和现有 runtime state 派生。
- 不改变 backend typed SSE、run/artifact persistence 或 artifact contract source of truth。

## 用户体验

用户打开 ArtifactPane 的“更多产物操作 -> 审阅”后，侧栏顶部先显示“质量诊断”：

- 三个计数：通过、需处理、提醒。
- 当产物为空时，显示当前阶段暂无可诊断内容。
- 当存在缺口时，按合同项展示“缺少标题”“缺少专业字段”“缺少图表”“缺少阶段门禁决策项”“可视化渲染失败”等诊断。
- 可视化渲染失败项继续复用现有 `focusArtifactVisualDiagnostic` 行为，点击后切回预览并定位到对应图表块。

## 架构

新增前端纯函数模块 `tools/new-agents/frontend/src/core/artifactQuality.ts`。它接收当前 `WorkflowStage`、artifact Markdown 内容和当前阶段 visual diagnostics，返回稳定的 `ArtifactQualitySummary`：

- `status`: `empty | pass | warning | fail`
- `passedCount`
- `failedCount`
- `warningCount`
- `items`: 每个合同项的类别、状态、标题、说明和可选 visual diagnostic id

`WorkflowStage` 类型显式加入 `artifactContract` 和 `visualContract`，字段继续由现有 `workflow_manifest.json` 注入。ArtifactPane 不复制 manifest 规则，只调用诊断函数并渲染结果。

## 诊断规则

- `artifactContract.requiredHeadings` 中以 `#` 开头的条目作为 Markdown 标题检查，忽略首尾空白，要求正文中有完全相同的标题行。
- 其他 `requiredHeadings` 条目作为专业字段/表格列关键字检查，要求正文包含该字符串。
- `visualContract.requiredMermaidDiagrams` 要求存在相应 Mermaid fence，图表首个非空行以对应 diagram keyword 开头。
- `visualContract.requiredStructuredVisuals` 要求存在 `ai4se-visual` fence，并且 JSON 顶层 `type` 等于要求值。
- 标题或字段缺失为 `fail`。
- Mermaid/structured visual 缺失为 `fail`。
- 阶段门禁标题存在但章节内没有 `- [ ]` 或 `- [x]` 决策项为 `warning`。
- 当前阶段已有 visual diagnostic 时，每条渲染/解析错误为 `fail`，并保留可定位 action。

## 验收

- ArtifactPane 审阅面板展示质量诊断计数和缺口列表。
- `TEST_DESIGN/CLARIFY` 缺少合同标题、专业字段、Mermaid 图、阶段门禁 checkbox 时能显示对应诊断。
- 合同满足时显示通过计数，无误报缺口。
- 已存在 visual diagnostic 时，质量诊断区显示渲染失败，并能复用原定位行为。
- 后端 artifact contract registry 基线保持通过。

