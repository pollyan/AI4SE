# Lisa Intent Tester Execution Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Lisa asset-center workflow that imports intent-tester drafts, creates intent-tester execution records, refreshes latest execution status, and hands users to the intent-tester execution page for real browser execution.

**Architecture:** Keep New Agents on the shared frontend service/page pattern. Add a small intent-tester execution service that parses the existing `/intent-tester/api/executions` contract, then wire it into `TestAssetsPage` as a per-test-case operation panel without changing backend runtime or intent-tester execution internals.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, existing fetch-based frontend service APIs.

---

## File Map

- Modify `tools/new-agents/frontend/src/core/types.ts`: add intent-tester execution result/record types.
- Create `tools/new-agents/frontend/src/services/intentTesterExecutionService.ts`: create execution record and fetch latest execution record.
- Create `tools/new-agents/frontend/src/services/__tests__/intentTesterExecutionService.test.ts`: parser and fetch contract tests.
- Modify `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`: render per-case intent-tester operation panel and wire import/create/refresh actions.
- Modify `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`: cover the asset-center import, create execution, refresh result, and handoff link flow.
- Modify `docs/todos/new-agents-evolution.md`: record completed capability and remaining boundaries.

### Task 1: Intent Tester Execution Service

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Create: `tools/new-agents/frontend/src/services/intentTesterExecutionService.ts`
- Create: `tools/new-agents/frontend/src/services/__tests__/intentTesterExecutionService.test.ts`

- [ ] **Step 1: Write failing service tests**

Add tests that call `createIntentTesterExecution(42)` and `fetchLatestIntentTesterExecution(42)`. The create test must expect:

```typescript
expect(fetch).toHaveBeenCalledWith('/intent-tester/api/executions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        testcase_id: 42,
        mode: 'headless',
        browser: 'chrome',
        executed_by: 'new-agents',
    }),
});
```

The latest test must expect:

```typescript
expect(fetch).toHaveBeenCalledWith('/intent-tester/api/executions?testcase_id=42&size=1');
```

Malformed create/list responses must reject with explicit invalid response errors.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterExecutionService.test.ts
```

Expected: fail because the service file and functions do not exist.

- [ ] **Step 3: Implement service and types**

Add types:

```typescript
export type IntentTesterExecutionCreateResult = {
    executionId: string;
    status: string;
    testcaseName: string;
    startTime: string;
};

export type IntentTesterExecutionRecord = {
    executionId: string;
    testCaseId: number;
    status: string;
    mode: string;
    browser: string;
    startTime: string | null;
    endTime: string | null;
    duration: number | null;
    errorMessage: string | null;
};
```

Create fetch functions:

```typescript
export const createIntentTesterExecution = async (
    testcaseId: number,
): Promise<IntentTesterExecutionCreateResult> => { /* parse POST response */ };

export const fetchLatestIntentTesterExecution = async (
    testcaseId: number,
): Promise<IntentTesterExecutionRecord | null> => { /* parse first list item */ };
```

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterExecutionService.test.ts
```

Expected: all service tests pass.

### Task 2: Asset Center Intent Tester Operation Panel

**Files:**
- Modify: `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`
- Modify: `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`

- [ ] **Step 1: Write failing page tests**

Add a collection fixture with an `intentTesterDrafts` item matching `TC-001`. Tests must prove:

```typescript
expect(screen.getByText('1 条 intent-tester 草稿')).toBeInTheDocument();
fireEvent.click(screen.getByRole('button', { name: '导入 intent-tester TC-001' }));
await waitFor(() => expect(importIntentTesterDraft).toHaveBeenCalledWith(draft));
expect(screen.getByText('已导入 intent-tester #42')).toBeInTheDocument();
```

Then create execution:

```typescript
fireEvent.click(screen.getByRole('button', { name: '创建执行记录 #42' }));
await waitFor(() => expect(createIntentTesterExecution).toHaveBeenCalledWith(42));
expect(screen.getByText(/最近执行 exec-123 · pending/)).toBeInTheDocument();
```

Then refresh:

```typescript
fireEvent.click(screen.getByRole('button', { name: '刷新执行结果 #42' }));
await waitFor(() => expect(fetchLatestIntentTesterExecution).toHaveBeenCalledWith(42));
expect(screen.getByText(/最近执行 exec-456 · success/)).toBeInTheDocument();
```

The handoff link must be:

```typescript
expect(screen.getByRole('link', { name: '去执行 #42' })).toHaveAttribute(
    'href',
    '/intent-tester/execution?testcase_id=42',
);
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx
```

Expected: fail because the page does not yet import or render intent-tester operations.

- [ ] **Step 3: Implement page state and handlers**

Add state maps keyed by Lisa case ID:

```typescript
const [importedIntentTesterCaseIds, setImportedIntentTesterCaseIds] = useState<Record<string, number>>({});
const [intentTesterExecutions, setIntentTesterExecutions] = useState<Record<string, IntentTesterExecutionRecord>>({});
const [importingIntentTesterCaseId, setImportingIntentTesterCaseId] = useState<string | null>(null);
const [creatingExecutionCaseId, setCreatingExecutionCaseId] = useState<string | null>(null);
const [refreshingExecutionCaseId, setRefreshingExecutionCaseId] = useState<string | null>(null);
```

Add handlers that call `importIntentTesterDraft`, `createIntentTesterExecution`, and `fetchLatestIntentTesterExecution`, update only the matching case state, and show explicit failure messages.

- [ ] **Step 4: Render operation panel**

Inside each test case card:

```tsx
{draft && (
    <div data-testid={`intent-tester-panel-${testCase.id}`}>
        <div>{draft.draftWarnings.length} 条 intent-tester 草稿</div>
        {!importedCaseId ? (
            <button>导入 intent-tester {testCase.id}</button>
        ) : (
            <>
                <div>已导入 intent-tester #{importedCaseId}</div>
                {execution && <div>最近执行 {execution.executionId} · {execution.status}</div>}
                <button>创建执行记录 #{importedCaseId}</button>
                <button>刷新执行结果 #{importedCaseId}</button>
                <a href={`/intent-tester/execution?testcase_id=${importedCaseId}`}>去执行 #{importedCaseId}</a>
            </>
        )}
    </div>
)}
```

- [ ] **Step 5: Run GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx
```

Expected: all page tests pass.

### Task 3: Documentation and Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [ ] **Step 1: Update todo**

Under P1 #7, record:

- Lisa asset center can now import intent-tester drafts, create intent-tester execution records, refresh latest execution status, and hand off to the execution page.
- Remaining work is persisted testcase/execution mapping, true proxy-backed automatic execution, and execution result write-back to New Agents asset versions.

- [ ] **Step 2: Run focused verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterExecutionService.test.ts src/services/__tests__/intentTesterImportService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx
```

Expected: pass.

- [ ] **Step 3: Run lint**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
```

Expected: pass.

- [ ] **Step 4: Run whitespace check**

Run:

```bash
git diff --check
```

Expected: no output.
