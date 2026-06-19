# Lisa 测试资产操作工作台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Lisa 测试资产中心从展示页升级为可搜索、可筛选、可编辑、可 triage 的操作工作台。

**Architecture:** 只修改前端资产中心页面和对应测试。复用现有 `fetchTestAssetCollection`、`updateTestAssetCase`、`updateTestAssetIssueStatus` 服务，不新增后端 endpoint、store 或运行时分支。

**Tech Stack:** React、React Router、Vitest、Testing Library、TypeScript、现有 `testAssetService`。

---

## File Structure

- Modify `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`: add search/filter state, filtered case rendering, edit form state, issue triage state.
- Modify `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`: add RED tests for search/filter, detail edit, issue triage.
- Modify `docs/todos/new-agents-evolution.md`: record progress and remaining P1 #7 gaps.

## Task 1: Search And Priority Filter

- [ ] **Step 1: Write failing test**

In `TestAssetsPage.test.tsx`, add a test that searches for `失败`, verifies `TC-001` is hidden and `TC-002` remains, then filters to `P0` and verifies only `TC-001` remains after clearing search.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx
```

Expected: FAIL because search and priority filter controls do not exist.

- [ ] **Step 3: Implement search/filter**

Add `caseSearchQuery`, `priorityFilter`, `filteredTestCases`, controls labelled `搜索测试用例` and `优先级过滤`, and render filtered cases. Keep batch selection state intact.

- [ ] **Step 4: Run GREEN**

Run the same page test. Expected: pass.

## Task 2: Full Test Case Detail Editing

- [ ] **Step 1: Write failing test**

Add a test that clicks `编辑 TC-002`, changes `测试点` and `预期结果`, saves, expects `updateTestAssetCase(7, 'TC-002', { ...complete edited patch })`, and verifies `版本 2` plus updated text.

- [ ] **Step 2: Run RED**

Run page test. Expected: FAIL because asset center detail edit controls do not exist.

- [ ] **Step 3: Implement edit form**

Add `editingCaseId`, `caseDraft`, `isSavingCase`, `startEditCase`, `handleSaveCase`, and form fields for all editable `TestAssetCasePatch` fields.

- [ ] **Step 4: Run GREEN**

Run page test. Expected: pass.

## Task 3: Asset Issue Triage

- [ ] **Step 1: Write failing test**

Add a test that clicks `确认问题` for issue `5`, expects `updateTestAssetIssueStatus(7, 5, 'confirmed')`, and verifies status text changes to `已确认`.

- [ ] **Step 2: Run RED**

Run page test. Expected: FAIL because asset center issue triage controls do not exist.

- [ ] **Step 3: Implement issue triage**

Import `updateTestAssetIssueStatus`, add label mapping, issue status update handler, and buttons for `确认问题` / `忽略问题`.

- [ ] **Step 4: Run GREEN**

Run page test. Expected: pass.

## Task 4: Documentation And Verification

- [ ] Update `docs/todos/new-agents-evolution.md` P1 #7.
- [ ] Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx src/services/__tests__/testAssetService.test.ts
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all pass.
