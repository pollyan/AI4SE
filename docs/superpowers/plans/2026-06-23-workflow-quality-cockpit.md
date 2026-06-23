# Workflow 质量治理闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 ArtifactPane 审阅入口中提供 workflow-level 质量治理闭环，让用户看到每个 stage 的质量分、证据明细、全局待处理队列，并能直接定位到需要处理的阶段。

**Architecture:** 新增前端纯函数模块 `workflowQuality.ts`，复用现有 `buildArtifactQualityDiagnostics()` 和 `WORKFLOWS`/manifest 信息，从 `stageArtifacts`、当前 artifact 和 runtime visual diagnostics 派生质量 summary、全局 pending queue 和 `nextFocusStageIndex`。ArtifactPane 渲染该 summary，并通过现有 `setStageIndex()` 完成阶段定位；不新增 store、API、runtime 或持久化模型。

**Tech Stack:** React 19 + TypeScript + Vitest；现有 Zustand store；现有 ArtifactPane 审阅 UI。

---

## File Structure

- Create: `tools/new-agents/frontend/src/core/workflowQuality.ts`
  - 负责 stage artifact 选择、score/status 计算、evidence/pending item 派生、workflow-level totals、全局 pending queue 和下一定位阶段。
- Create: `tools/new-agents/frontend/src/core/__tests__/workflowQuality.test.ts`
  - 覆盖 not-started、blocked、attention、ready、aggregate totals、pending queue 排序和状态恢复派生。
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - 调用 `buildWorkflowQualitySummary()`，在审阅面板中新增“工作流质量治理”区块，并为非当前 stage 提供定位按钮。
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
  - 覆盖 cockpit UI 展示 stage score/status/pending queue，并验证点击定位按钮后 `stageIndex` / `artifactContent` 承接到目标 stage；现有当前阶段审阅诊断仍可见。
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - 更新 E08 消化记录。
- Modify: `docs/todos/refactor/README.md`
  - 更新当前入口和下一轮候选。

## Task 1: Pure workflow quality governance summary

**Files:**
- Create: `tools/new-agents/frontend/src/core/__tests__/workflowQuality.test.ts`
- Create: `tools/new-agents/frontend/src/core/workflowQuality.ts`

- [ ] **Step 1: Write failing pure tests**

Add tests that call `buildWorkflowQualitySummary()` with:

1. `TEST_DESIGN` stage artifacts where `STRATEGY` is valid and `CLARIFY` is incomplete.
2. A missing `CASES` stage artifact.
3. A runtime visual diagnostic warning for `DELIVERY`.
4. A persisted-state style input where only `stageArtifacts` and current `artifactContent` are available.

Assert:

- `STRATEGY` is `ready`, score `100`.
- `CLARIFY` is `blocked`, has heading/visual pending items.
- `CASES` is `not-started`, score `0`.
- `DELIVERY` is `attention` when runtime visual diagnostics are warnings without fail diagnostics.
- `pendingQueue` sorts blockers before attention before not-started.
- `nextFocusStageIndex` points to the first blocked stage.
- Recomputing from existing `stageArtifacts` produces the same summary without persisted quality fields.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/workflowQuality.test.ts
```

Expected: fail because `workflowQuality.ts` does not exist.

- [ ] **Step 3: Implement minimal pure module**

Implement:

- `WorkflowStageQualityStatus`
- `WorkflowQualityPendingSeverity`
- `WorkflowQualityPendingItem`
- `WorkflowQualityEvidenceItem`
- `WorkflowStageQualitySummary`
- `WorkflowQualitySummary`
- `buildWorkflowQualitySummary(input)`

Rules:

- Missing artifact -> score 0, status `not-started`.
- Score starts at 100.
- Fail item -20.
- Warn item -8.
- Blocking open question -18.
- Non-blocking open question -8.
- `blocked` if any fail or blocking open question.
- `attention` if any warn or non-blocking open question.
- `ready` otherwise.
- `pendingQueue` flattens all stage pending items and sorts `blocker`, then `attention`, then `not-started`, preserving workflow stage order within the same severity.
- `nextFocusStageIndex` is the first stage in `pendingQueue`, or `null` when all stages are ready.

- [ ] **Step 4: Run GREEN**

Run the same npm test command. Expected: pass.

## Task 2: ArtifactPane quality governance UI

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Write failing UI test**

Add a test that:

- Sets `workflow: TEST_DESIGN`, `stageIndex: 1`.
- Sets `stageArtifacts.STRATEGY` to a valid artifact, `stageArtifacts.CLARIFY` to an incomplete artifact, and leaves `CASES` missing.
- Opens the review panel.
- Asserts “工作流质量治理”, “平均分”, `需求澄清`, `策略制定`, `全局待处理`, `可推进`, `需处理`/`待生成`, and pending text are visible.
- Asserts existing “审阅诊断” is still visible.
- Clicks “定位阶段：需求澄清”.
- Asserts `useStore.getState().stageIndex === 0` and `artifactContent` is the `CLARIFY` artifact.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
```

Expected: fail because ArtifactPane does not render workflow quality governance UI or stage locator actions.

- [ ] **Step 3: Implement UI section**

In `ArtifactPane.tsx`:

- Import `buildWorkflowQualitySummary`.
- Read `stageArtifacts` and `setStageIndex` from store.
- Build summary from `workflow`, `currentStageId`, `artifactContent`, `stageArtifacts`, and `artifactVisualDiagnostics`.
- Render a compact “工作流质量治理” section before current-stage diagnostics.
- Show totals and stage cards.
- Show top global pending queue items.
- Highlight current stage.
- Show up to two pending items per stage.
- Render `定位阶段：${stage.stageName}` buttons for non-current stages that call `setStageIndex(stage.stageIndex)`.

- [ ] **Step 4: Run GREEN**

Run the same ArtifactPane test command. Expected: pass.

## Task 3: Docs and verification

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/README.md`

- [ ] **Step 1: Update todo records**

Mark E08 current rule-based cockpit slice as consumed. Keep cross-run quality trends, LLM judge evidence, E05 section regeneration, and E12 dry-run/scaffold as future candidates.

- [ ] **Step 2: Run target frontend tests**

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/workflowQuality.test.ts src/core/__tests__/artifactReview.test.ts src/core/__tests__/workspaceState.test.ts src/components/__tests__/ArtifactPane.test.tsx
```

- [ ] **Step 3: Run frontend build**

```bash
cd tools/new-agents/frontend && npm run build
```

- [ ] **Step 4: Run diff checks**

```bash
git diff --check
git diff --cached --check
```

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-06-23-workflow-quality-cockpit-design.md docs/superpowers/plans/2026-06-23-workflow-quality-cockpit.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md tools/new-agents/frontend/src/core/workflowQuality.ts tools/new-agents/frontend/src/core/__tests__/workflowQuality.test.ts tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 增加工作流质量治理闭环"
```
