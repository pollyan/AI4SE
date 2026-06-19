# Lisa 资产中心列表管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Lisa 测试资产中心支持测试用例排序、分页和 URL 持久化筛选条件。

**Architecture:** 只修改前端资产中心页面，在 `TestAssetsPage.tsx` 内用 URL query 作为列表视图状态来源，并派生过滤、排序、分页后的当前页用例。现有后端资产 API、测试资产编辑 API、风险生命周期 API 和 intent-tester 导入链路保持不变。

**Tech Stack:** React + TypeScript + React Router `useSearchParams` + Vitest + Testing Library。

---

## Files

- Modify: `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`
- Modify: `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`
- Modify: `docs/todos/new-agents-evolution.md`

## Task 1: URL State And Filter Restoration Tests

- [x] Step 1: Add a larger `TEST_ASSET_COLLECTION` fixture in `TestAssetsPage.test.tsx` with at least 7 cases covering P0, P1, P2, different risk names and titles.
- [x] Step 2: Add a failing test named `restores list controls from the URL query` that renders `/test-assets/7?q=失败&priority=P1&sort=risk&direction=desc&pageSize=5&page=1`, waits for the page, then asserts:
  - `搜索测试用例` input value is `失败`
  - `优先级过滤` value is `P1`
  - `排序字段` value is `risk`
  - `排序方向` value is `desc`
  - `每页数量` value is `5`
  - `test-asset-case-TC-002` is visible
  - unrelated cases such as `test-asset-case-TC-001` are not visible
- [x] Step 3: Run `cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx -t "restores list controls"` and confirm it fails because sort/page controls do not exist.

## Task 2: Query Parsing And List Derivation

- [x] Step 1: In `TestAssetsPage.tsx`, import `useSearchParams` from `react-router-dom`.
- [x] Step 2: Add constants `SORT_FIELDS = ['id', 'priority', 'title', 'risk']`, `SORT_DIRECTIONS = ['asc', 'desc']`, `PAGE_SIZES = [5, 10, 20]`, `DEFAULT_SORT_FIELD = 'id'`, `DEFAULT_SORT_DIRECTION = 'asc'`, and `DEFAULT_PAGE_SIZE = 10`.
- [x] Step 3: Add helper functions in `TestAssetsPage.tsx`:
  - `parseSearchParams(params)` returns `{ query, priority, sort, direction, page, pageSize }`
  - `buildSearchParams(state)` returns `URLSearchParams` with only non-default values
  - `priorityRank(priority)` returns `0` for P0, `1` for P1, `2` for P2, `3` for unknown values
  - `compareCases(left, right, sortField)` compares the selected field
  - `clampPage(page, totalPages)` keeps page between 1 and total pages
- [x] Step 4: Replace local `caseSearchQuery` and `priorityFilter` state initialization with parsed URL state, while preserving the same controlled inputs.
- [x] Step 5: Add derived values:
  - `sortedFilteredTestCases`
  - `totalPages`
  - `currentPage`
  - `paginatedTestCases`
  - `pageStart`
  - `pageEnd`
- [x] Step 6: Re-run the URL restoration test and confirm it still fails only on missing UI or display assertions.

## Task 3: Controls, URL Sync, And Pagination UI

- [x] Step 1: Add `updateListQuery(nextPatch, options)` in `TestAssetsPage.tsx`; it merges current URL state, resets `page` to 1 for search/filter/sort/direction/pageSize changes, writes query params via `setSearchParams(buildSearchParams(nextState), { replace: true })`, and keeps `page` when explicitly changing page.
- [x] Step 2: Wire `搜索测试用例` input to `updateListQuery({ query: value })`.
- [x] Step 3: Wire `优先级过滤` select to `updateListQuery({ priority: value })`.
- [x] Step 4: Add labels and controls:
  - `排序字段` select with `id`, `priority`, `title`, `risk`
  - `排序方向` select with `asc`, `desc`
  - `每页数量` select with `5`, `10`, `20`
- [x] Step 5: Replace `filteredTestCases.map(...)` with `paginatedTestCases.map(...)`.
- [x] Step 6: Update count text to `显示 {pageStart}-{pageEnd} / 过滤后 {sortedFilteredTestCases.length} 条 / 总计 {collection.testCases.length} 条`.
- [x] Step 7: Add `上一页` and `下一页` buttons that call `updateListQuery({ page: currentPage - 1 }, { keepPage: true })` and `updateListQuery({ page: currentPage + 1 }, { keepPage: true })`.
- [x] Step 8: Change `allCasesSelected` and `toggleAllCases` so selection operates on `paginatedTestCases`, not all filtered cases.
- [x] Step 9: Add an empty state when `sortedFilteredTestCases.length === 0`.
- [x] Step 10: Re-run the URL restoration test and confirm pass.

## Task 4: Pagination Behavior And Batch Scope Tests

- [x] Step 1: Add a regression test named `paginates sorted test cases and persists page changes in the URL`.
  - Render `/test-assets/7?pageSize=5&sort=id`.
  - Assert page 1 shows `TC-001` and not `TC-006`.
  - Click `下一页`.
  - Assert page 2 shows `TC-006`.
  - Assert `window.location.search` contains `page=2`.
- [x] Step 2: Add a regression test named `selects all only on the current page`.
  - Render `/test-assets/7?pageSize=5`.
  - Click `选择全部`.
  - Click `更新选中用例`.
  - Assert `updateTestAssetCase` is called exactly 5 times and never with `TC-006`.
- [x] Step 3: Run `cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx -t "paginates|selects all only"` and confirm both pagination regressions pass after the URL state implementation.
- [x] Step 4: Implement any remaining pagination or selection fixes.
- [x] Step 5: Re-run the targeted tests and confirm pass.

## Task 5: Documentation And Verification

- [x] Step 1: Update P1 #7 in `docs/todos/new-agents-evolution.md` to record asset center list management completion and update the remaining work sentence.
- [x] Step 2: Run `cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx`.
- [x] Step 3: Run `cd tools/new-agents/frontend && npm run lint`.
- [x] Step 4: Run `git diff --check`.
- [x] Step 5: Report changes, verification, residual risk and next thick-slice candidates. Do not commit unless explicitly asked.
