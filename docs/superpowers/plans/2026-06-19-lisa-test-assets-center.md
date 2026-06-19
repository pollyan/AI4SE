# Lisa 测试资产中心 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Lisa 测试资产从 Header 弹层中的辅助视图升级为可导航资产中心，并补齐部分选择批量优先级编辑。

**Architecture:** 复用现有测试资产后端集合 contract 和前端 `TestAssetCollection` 类型。新增前端 GET 服务、页面路由和资产中心页面；批量更新继续调用现有单条用例 PATCH，不新增后端批量 endpoint 或独立 store。

**Tech Stack:** React、React Router、Vitest、Testing Library、TypeScript、现有 `testAssetService`。

---

## File Structure

- Modify `tools/new-agents/frontend/src/services/testAssetService.ts`: add `fetchTestAssetCollection(collectionId)` and reuse `parseCollection`.
- Modify `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`: cover GET collection success and invalid id failure.
- Create `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`: load collection by route param, render asset center, support selected-case batch priority updates.
- Create `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`: cover loading, error state, selected batch update.
- Modify `tools/new-agents/frontend/src/App.tsx`: register `/test-assets/:collectionId`.
- Modify `tools/new-agents/frontend/src/components/Header.tsx`: add “打开资产中心” action after materialize succeeds.
- Modify `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`: cover Header navigation entry.
- Modify `docs/todos/new-agents-evolution.md`: record progress and remaining gaps.

## Task 1: Test Asset Collection GET Service

- [ ] **Step 1: Write the failing service test**

Add a test in `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`:

```ts
it('fetches a materialized test asset collection by id', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(
        JSON.stringify(COLLECTION_PAYLOAD),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
    ));

    const collection = await fetchTestAssetCollection(7);

    expect(fetch).toHaveBeenCalledWith('/new-agents/api/agent/test-assets/7');
    expect(collection.id).toBe(7);
    expect(collection.runId).toBe('run-123');
});
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts
```

Expected: FAIL because `fetchTestAssetCollection` is not exported.

- [ ] **Step 3: Implement the service**

Add `fetchTestAssetCollection(collectionId: number): Promise<TestAssetCollection>` in `testAssetService.ts`. It validates positive integer ids, calls `/new-agents/api/agent/test-assets/${collectionId}`, fails explicitly on non-OK, and parses through `parseCollection`.

- [ ] **Step 4: Run GREEN**

Run the same service test. Expected: all service tests pass.

## Task 2: Asset Center Page

- [ ] **Step 1: Write failing page tests**

Create `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx` with mocked `fetchTestAssetCollection` and `updateTestAssetCase`.

Required tests:

- Loads `/test-assets/7`, calls `fetchTestAssetCollection(7)`, and displays “Lisa 测试资产中心”, coverage, cases, asset issues, risk matrix, and test points.
- Shows “无法加载测试资产集合” for invalid collection id or service failure.
- Selects only `TC-002`, changes batch priority to `P0`, clicks “更新选中用例”, calls `updateTestAssetCase(7, 'TC-002', { title: '用户登录失败提示错误', priority: 'P0' })`, and updates visible priority/version for `TC-002`.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx
```

Expected: FAIL because `TestAssetsPage` does not exist.

- [ ] **Step 3: Implement the page**

Create `TestAssetsPage.tsx` using `useParams` for `collectionId`, local state for loading/error/collection/selected case ids/batch priority/saving/success message, and existing `updateTestAssetCase`.

- [ ] **Step 4: Run GREEN**

Run the page test. Expected: all page tests pass.

## Task 3: Route And Header Entry

- [ ] **Step 1: Write failing Header navigation test**

Add a test in `Header.test.tsx`: materialize returns collection id `7`; after opening “测试资产”, clicking “打开资产中心” calls `navigate('/test-assets/7')`.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx
```

Expected: FAIL because the button does not exist.

- [ ] **Step 3: Implement route and Header entry**

Register `<Route path="/test-assets/:collectionId" element={<TestAssetsPage />} />` in `App.tsx`. Add the Header button only when `testAssetCollection` is loaded.

- [ ] **Step 4: Run GREEN**

Run Header and page tests. Expected: all pass.

## Task 4: Documentation And Verification

- [ ] Update `docs/todos/new-agents-evolution.md` P1 #7 with the asset center progress and remaining gaps.
- [ ] Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx src/components/__tests__/Header.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all pass.
