# Workflow 质量治理闭环 Spec

## 背景

New Agents 已具备多 workflow、多阶段产物、Artifact 审阅诊断、运行统计和 Lisa 测试资产质量闭环。当前 Artifact 审阅诊断能检查“当前阶段”的 required headings、Mermaid、structured visual、阶段门禁、运行时可视化警告和开放问题，但用户仍缺少一个跨阶段质量治理入口：整个 workflow 哪些阶段已经可推进，哪些阶段因为缺产物、缺 contract evidence、可视化警告或待确认事项而阻断，以及用户下一步应该定位到哪个阶段处理。

本切片消化 E08 “工作流质量评分”的规则型治理闭环。它把现有当前阶段诊断升级为 workflow-level quality cockpit：每个 stage 都有质量分、状态、证据明细、待处理项和下一步建议；面板同时给出全局待处理队列和阶段定位动作。用户可以从一个审阅入口完成“看到阻断 -> 判断优先级 -> 定位阶段 -> 继续修订”的完整链路。该能力复用现有 `stageArtifacts`、当前 artifact、runtime visual diagnostics、workflow manifest、`setStageIndex()` 和 ArtifactPane 审阅入口，不新增 agent 专属 runtime、API path、store 或 renderer。

## 用户故事

作为 New Agents 多阶段 workflow 用户，当我审阅当前 artifact 时，我可以看到整个 workflow 各阶段的质量评分、证据强度和待处理项，并能直接定位到需要处理的阶段，从而完成一次可执行的 workflow 质量复审。

## 范围

纳入本轮：

- 新增前端纯规则质量聚合模块，基于现有 `buildArtifactQualityDiagnostics()` 计算每个 workflow stage 的质量分。
- 每个 stage 输出：
  - `stageIndex` / `stageId` / `stageName`：用于 UI 定位和可读展示。
  - `score`: 0-100 分。
  - `status`: `not-started | blocked | attention | ready`。
  - `label`: 用户可读状态。
  - `evidenceItems`: contract、visual、stage gate、runtime visual、open questions 等证据明细。
  - `pendingItems`: 待处理项，包括缺失产物、失败项、警告项、阻断开放问题。
  - `nextAction`: 下一步建议。
- Workflow summary 输出：
  - 平均分。
  - ready / attention / blocked / not-started 阶段数。
  - 全局待处理队列，按 blocker、attention、not-started 优先级排序。
  - `nextFocusStageIndex`，指向当前最需要处理的阶段。
- ArtifactPane 审阅面板展示 workflow quality cockpit：总体平均分、阻断/关注/可推进阶段数量、每阶段分数、全局待处理队列和阶段定位按钮。
- 阶段定位按钮调用现有 `setStageIndex()`，承接现有 `stageArtifacts` 和 `artifactContent` 同步逻辑。定位后仍可继续使用当前 Artifact 审阅诊断、批注、锁定章节和历史版本。
- 当前阶段现有“审阅诊断”和“缺失信息清单”继续保留，作为当前阶段细节。
- 更新 `docs/todos/`、spec 和 plan。

不纳入本轮：

- LLM judge 或真实模型质量评分。
- 后端持久化质量分。分数从已持久化 artifact/stage state 派生，随 run snapshot 自然恢复。
- 跨 run 质量趋势。该能力可后续结合 observability/quality scoring 做趋势化。
- 自动修复或章节级重生成。E05 单独成厚切片。

## 评分口径

规则型评分先聚焦当前已有证据，避免引入不可验证的主观模型判断。

基础分为 100。扣分规则：

- stage 尚无 artifact：分数 0，状态 `not-started`。
- 每个 `fail` 诊断项扣 20 分。
- 每个 `warn` 诊断项扣 8 分。
- 每个阻断开放问题扣 18 分。
- 每个非阻断开放问题扣 8 分。
- 分数下限 0，上限 100。

状态规则：

- 无 artifact：`not-started`。
- 存在 fail 诊断或阻断开放问题：`blocked`。
- 存在 warn 诊断或非阻断开放问题：`attention`。
- 其他：`ready`。

该规则不是最终质量模型，而是一个确定性 first pass。后续 E08 趋势化或 LLM judge 可以在不破坏 UI contract 的情况下扩展。

## UI / 交互设计

ArtifactPane 审阅面板新增一个“工作流质量治理”区块，位于现有当前阶段“审阅诊断”之前。

区块包含：

- 总览：平均分、可推进阶段数、需关注阶段数、阻断阶段数。
- 阶段列表：每个 stage 显示 stage 名称、score、status label、证据数量和待处理数量。
- 当前阶段高亮：当前 stage 使用更明确的边框/背景。
- 全局待处理队列：展示排序后的前 4 个待处理项，包含来源 stage、严重级别、问题标题和 next action。
- 阶段定位动作：每个非当前 stage 都有“定位阶段”按钮；点击后调用 `setStageIndex(stageIndex)`，让用户立刻进入该 stage 的 artifact。
- 待处理摘要：每个 stage 最多展示前 2 个 pending item，避免面板过长。
- 空状态：没有 artifact 的阶段显示“待生成”，并给出“先生成该阶段产物”的 next action。

不新增复杂导航控件，不新增专属路由。阶段定位复用现有 stage 切换能力，确保已保存的 `stageArtifacts` 和当前 `artifactContent` 一致。

## 验收条件

1. Given workflow 中某 stage 没有 artifact
   When 构建 workflow quality summary
   Then 该 stage score 为 0，status 为 `not-started`，pending item 提示先生成该阶段产物。

2. Given 某 stage 缺 required headings/visual 或存在 runtime visual warning
   When 构建 workflow quality summary
   Then 该 stage score 降低，status 为 `blocked` 或 `attention`，evidenceItems 和 pendingItems 包含对应诊断来源。

3. Given 某 stage artifact 满足 contract、visual 和 stage gate 且没有开放问题
   When 构建 workflow quality summary
   Then 该 stage status 为 `ready`，score 为 100。

4. Given 用户打开 ArtifactPane 审阅面板
   When workflow 中同时存在 ready、attention、blocked/not-started stage
   Then UI 展示“工作流质量治理”、平均分、阶段分数、状态、全局待处理队列和待处理项，并保留当前阶段“审阅诊断”细节。

5. Given 用户在质量治理区点击某个非当前 stage 的“定位阶段”
   When 该 stage 已有 `stageArtifacts` 内容
   Then store 的 `stageIndex` 和 `artifactContent` 切换到目标 stage，当前审阅入口可以继续使用。

6. Given 用户刷新后从 persisted workspace state 恢复
   When `stageArtifacts` 和当前 `artifactContent` 被恢复
   Then workflow quality summary 可从现有状态重新派生，不依赖新增持久化字段。

7. Given 本轮完成
   When 查看 `docs/todos/refactor/`
   Then E08 记录本轮规则型质量治理闭环已消化，跨 run 趋势/LLM judge 保留为后续候选。

## 风险与约束

- 不把规则型评分包装成 LLM 质量判断；文案必须体现它来自当前 artifact contract、visual 和开放问题证据。
- 不新增持久化字段，避免 schema 迁移和同步风险；状态恢复依赖现有 `stageArtifacts`/`artifactContent`。
- 不新增 workflow/agent 专属逻辑。评分必须对所有在线 workflow 使用同一规则。
- 不遮蔽现有 Artifact 审阅诊断；本轮是跨阶段总览加当前阶段细节承接。
- 阶段定位不做自动修复，也不绕过现有 stage 生成/切换逻辑。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/workflowQuality.test.ts src/core/__tests__/artifactReview.test.ts src/core/__tests__/workspaceState.test.ts src/components/__tests__/ArtifactPane.test.tsx`
- `cd tools/new-agents/frontend && npm run build`
- `git diff --check`
