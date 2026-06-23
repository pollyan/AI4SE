# New Agents Artifact 质量诊断面板设计

## 背景

DeepSeek V4 格式化输出主线已经完成，在线 workflow stage 统一走 `artifact_data -> backend renderer -> artifact contract -> typed SSE -> frontend artifact`。当前后端 contract 和 renderer 已能阻断格式缺失，但用户在右侧产物视图中仍缺一个统一入口来判断当前 artifact 是否满足本 stage 的标题、可视化、阶段门禁和专业字段要求。

现有前端已有 Mermaid / `ai4se-visual` 渲染失败诊断，但它只覆盖具体可视化块的运行时错误，不等同于 artifact 质量总览。本轮把这些局部诊断纳入一个共享 Artifact 质量诊断面板，不新增 Lisa、Alex、DeepSeek 专属 runtime、API、store 或 renderer。

## 用户故事

作为 New Agents 用户，我在 Lisa 或 Alex 任一 workflow 的当前 stage 查看右侧产出物时，可以直接看到这份 artifact 的质量诊断状态：哪些 contract 已通过，哪些标题、可视化、阶段门禁或专业字段缺失，哪些 visual block 有运行时警告。这样我可以决定继续交付、补充输入、重试当前阶段或审阅产物。

## 范围

本轮进入范围：

- 新增前端共享纯函数，基于当前 `workflow`、`stageId`、artifact Markdown 文本和现有 visual diagnostics 生成质量诊断。
- 诊断覆盖四类质量项：required headings、required Mermaid / structured visual、stage gate / handoff / checklist 等专业字段、runtime visual diagnostics。
- 在 `ArtifactPane` 当前 artifact 视图中展示诊断摘要和分组结果。
- 质量诊断只派生自当前内容和现有 workflow 配置，不新增持久化模型。
- 更新 E03 todo 状态，记录本轮消化边界。

本轮不进入范围：

- 不做 LLM judge 评分或自动质量分。
- 不做自动修复全文、章节重生成或 prompt 改写。
- 不新增 backend diagnostic endpoint。
- 不改变 typed SSE、Agent Runtime、artifact_data renderer、run persistence 或 artifact contract。
- 不把历史 run 质量筛选纳入本轮。

## 设计

### 诊断核心

新增 `tools/new-agents/frontend/src/core/artifactQuality.ts`。它负责：

- 从 `WORKFLOWS` 中定位当前 workflow/stage。
- 建立每个 stage 的基础质量需求：
  - 当前阶段名称或 artifact H1 / H2 相关标题。
  - Mermaid fence 或 `ai4se-visual` fence。
  - 阶段门禁、验收、风险、开放问题、handoff 等专业字段关键词。
- 对当前 Markdown 文本执行大小写无关的包含性检查。
- 合并当前 stage 的 `ArtifactVisualDiagnostic[]`，把运行时 visual 错误作为 warning。
- 输出稳定结构：整体状态、通过/警告/失败计数、分组诊断项。

### UI 展示

`ArtifactPane` 在预览模式和有 artifact 内容时展示轻量质量面板：

- 顶部显示“产物质量诊断”和整体状态。
- 展示通过、警告、失败计数。
- 分组列出 Contract、可视化、专业门禁、运行时诊断。
- 失败项给出明确缺失内容；warning 指向现有 visual diagnostic 说明。
- read-only history preview 不记录新的 visual diagnostic，也不改变现有 visual focus 行为。

### Contract 边界

本轮质量面板不是后端 contract 的替代品。后端仍是最终守门，前端面板只是用户可见诊断。任何生成失败仍由现有 typed SSE error / structured output failure 路径处理。

## 验收条件

- 当 artifact 包含 required heading、Mermaid、`ai4se-visual` 和阶段门禁关键词时，诊断摘要显示通过。
- 当 artifact 缺少 required heading 或 required visual 时，诊断摘要显示失败并列出缺失项。
- 当当前 stage 有 visual runtime diagnostic 时，诊断摘要显示 warning，并保留已有点击定位 visual diagnostic 的行为。
- `ArtifactPane` 只在当前 artifact 视图展示质量面板，空 artifact 不展示误导性结果。
- 前端测试覆盖纯函数诊断和 ArtifactPane 集成展示。
- `npm run lint` 通过。

## 风险与缓解

- 风险：前端关键词诊断可能与后端 contract 不完全等价。缓解：文案明确这是“质量诊断”，后端 contract 仍是最终守门；本轮只覆盖用户可理解的稳定 contract 信号。
- 风险：ArtifactPane 文件较大，继续加逻辑会加重维护成本。缓解：诊断计算放在 `core/artifactQuality.ts`，ArtifactPane 只做展示。
- 风险：不同 workflow 的专业字段差异大。缓解：先以通用 stage gate / risk / open questions / handoff / checklist 等关键词覆盖，不引入独立 workflow runtime 分支。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactQuality.test.ts src/components/__tests__/ArtifactPane.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `git diff --check`
