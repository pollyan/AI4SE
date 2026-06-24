# Workflow Quality Governance Design

## 背景

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 把 E03「Artifact 质量诊断面板」列为 P0，把 E08「工作流质量评分」列为 P1。二者属于同一审阅动作链：用户拿到当前阶段 artifact 后，需要判断产物是否满足 workflow/stage 的交付门槛、哪里缺证据、下一步该处理什么。

当前 `ArtifactPane` 已有「产物审阅」抽屉，能汇总未解决批注、章节锁定、协作轨迹和最近版本，但没有统一展示 artifact contract、可视化、stage gate 和专业字段质量。现有 visual diagnostic 只在 Mermaid 或 structured visual 渲染失败时提示，不能回答整体质量是否可交付。

## Superpowers 头脑风暴结论

- 问：这个能力包真正服务的用户意图是什么？
  答：让 PM、测试专家或研发负责人在 artifact 审阅入口判断当前产物是否可信、缺什么证据、下一步该补什么。
- 问：是否需要视觉辅助？
  答：不需要单独视觉 companion。本轮沿用现有 `ArtifactPane` 审阅抽屉，重点是质量规则、数据流和验收证据。
- 问：哪些相邻缺口必须并入？
  答：E03 的 headings / visual / stage gate 诊断和 E08 的 stage quality score 必须同轮并入。只有诊断没有分数，用户难以排序处理；只有分数没有证据，用户无法信任结果。
- 问：本轮不做什么？
  答：不做 E09 runtime observability 趋势和 provider retry drilldown；不做 E05 章节级重生成；不做 LLM judge。它们分别属于运行排障、编辑修订和模型评审证据闭环。
- 问：推荐方案是什么？
  答：采用前端确定性质量模型。新增纯函数模块从 workflow/stage/artifact/visual diagnostics 派生质量摘要，`ArtifactPane` 只负责展示。该方案本地可测、不会新增 API 或 agent 专属 runtime。

## 用户故事

作为 New Agents 的 artifact 审阅用户，当我打开当前阶段产物的「审阅」抽屉时，我可以看到质量总分、通过/警告/失败项、证据明细和待处理项，从而决定产物是否可交付、是否需要补充输入或继续修订。

## 范围

本轮包含：

- 新增 `tools/new-agents/frontend/src/core/workflowQuality.ts`，提供无副作用质量摘要构建函数。
- 新增 `tools/new-agents/frontend/src/core/__tests__/workflowQuality.test.ts`，覆盖核心质量规则。
- 扩展 `tools/new-agents/frontend/src/components/ArtifactPane.tsx` 的「产物审阅」抽屉，展示质量总览、检查项和待处理项。
- 扩展 `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`，验证用户入口和可见质量治理结果。
- 更新本 todo，记录 E03/E08 合并消化状态。

本轮不包含：

- 不新增后端 diagnostic endpoint。
- 不改 `/api/agent/runs/stream`、typed SSE、run persistence 或 artifact persistence。
- 不新增 Lisa、Alex 或未来 agent 专属 runtime、store、API path 或 renderer。
- 不引入 LLM judge 或真实模型 smoke。

## 设计

### 质量模型

新增 `buildWorkflowQualitySummary(input)`：

- `workflow`: 当前 workflow 定义。
- `stageId`: 当前 stage id。
- `artifactMarkdown`: 当前 artifact 内容。
- `visualDiagnostics`: 当前 store 中的 visual diagnostics。

输出：

- `score`: 0 到 100 的整数。
- `status`: `pass | warning | fail`。
- `passedCount`、`warningCount`、`failedCount`。
- `checks`: 逐项检查结果，每项包含 id、label、status、evidence、impact。
- `actionItems`: 从失败和警告项派生的用户待处理建议。

首批确定性规则：

- Artifact 内容必须非空。
- 当前 stage 的 required headings 必须在 Markdown 中出现。
- 当前 stage 声明 Mermaid visual contract 时，artifact 必须包含 Mermaid fenced block。
- 当前 stage 声明 structured visual contract 时，artifact 必须包含 `ai4se-visual` fenced block。
- Artifact 必须包含阶段门禁或类似 gate/checklist 章节。
- 当前 stage 的 visual diagnostics 会降低质量状态，并转成待处理项。

### UI 呈现

`ArtifactPane` 复用已有「审阅」抽屉，在批注、锁定章节和最近轨迹之前展示「质量治理」区：

- 顶部显示质量分和状态文案。
- 显示通过、警告、失败数量。
- 展示最多若干条关键检查项，包含证据与影响。
- 展示待处理项；无待处理项时明确说明当前没有阻断项。

该区域只消费纯函数结果，不在组件中复制规则。

### 错误处理

- 当前 stage 不存在时，质量模型返回失败项，提示 stage context 缺失。
- Artifact 为空时返回失败项，提示无法审阅。
- 缺 heading、visual 或 stage gate 时返回失败或警告，不静默通过。
- Visual diagnostic 只影响当前 stage；其他 stage 的 diagnostic 不污染当前审阅。

## 验收条件

1. Given 当前 stage artifact 包含 required headings、Mermaid/structured visual 和 stage gate  
   When 构建质量摘要  
   Then 返回高分 `pass`，且检查项包含通过证据。  
   Evidence: `workflowQuality.test.ts`

2. Given 当前 artifact 缺 required heading 或 visual  
   When 构建质量摘要  
   Then 返回 `fail` 或 `warning`，并生成明确待处理项。  
   Evidence: `workflowQuality.test.ts`

3. Given 当前 stage 有 visual diagnostic  
   When 打开「产物审阅」  
   Then 审阅抽屉展示质量警告和待处理项。  
   Evidence: `ArtifactPane.test.tsx`

4. Given 用户在 `ArtifactPane` 点击「更多产物操作 -> 审阅」  
   When 当前 artifact 有质量缺口  
   Then UI 显示质量分、失败/警告统计和可读问题说明。  
   Evidence: `ArtifactPane.test.tsx`

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/workflowQuality.test.ts src/components/__tests__/ArtifactPane.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `git diff --check`

## 风险

- 规则型质量分不能替代 LLM judge 的语义评审；本轮只建立确定性本地质量门禁。
- `ArtifactPane.tsx` 已较大，本轮只接线展示，不做无关拆分。
- Frontend worktree 可能缺 `node_modules`，验证时需要复用主仓库已有依赖或报告环境原因。
