# Artifact 冲突安全删除自动合并 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend Artifact conflict auto-merge so safe server insertions can be combined with user draft deletions without losing either side's non-conflicting changes.

**Architecture:** Reuse the existing ArtifactPane conflict flow and audit event. Replace the current insertion-only helper with a conservative three-way line merge that treats the original artifact as the base, the conflict artifact as server, and the edit draft as user draft. Keep the UI entry and event type unchanged.

**Tech Stack:** React 19, TypeScript, Zustand store, Vitest, Testing Library.

---

## File Structure

- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - Extend the existing `buildAutoMergedInsertionContent` behavior or replace it with an equivalent conservative helper.
  - Keep `autoMergedConflictContent` and `applyAutoMergedConflictContent` wiring intact.
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
  - Add the RED test for safe deletion + insertion auto-merge.
- Do not modify: backend files, workflow contracts, PDF/DOCX export files, shared todo files. The main Agent will update todo after integration.

## Task 1: Add Failing Component Test

- [ ] **Step 1: Add the RED test**

Add this test near the existing `auto-merges non-overlapping server and draft insertions during an artifact conflict` test in `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`:

```tsx
it('auto-merges server insertions with draft deletions during an artifact conflict', async () => {
    vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
        '产出物已被更新，请刷新后再保存',
        {
            stageId: 'STRATEGY',
            content: '# 测试策略蓝图\n\n背景\n服务端补充\n旧风险\n共同内容\n服务端后置补充',
            versionNumber: 3,
        },
    ));
    useStore.setState({
        workflow: 'TEST_DESIGN',
        stageIndex: 1,
        currentRunId: 'run-123',
        artifactContent: '# 测试策略蓝图\n\n背景\n旧风险\n共同内容',
        stageArtifacts: {
            STRATEGY: '# 测试策略蓝图\n\n背景\n旧风险\n共同内容',
        },
        artifactHistory: [
            {
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: '# 测试策略蓝图\n\n背景\n旧风险\n共同内容',
                stageId: 'STRATEGY',
            },
        ],
        artifactAuditEvents: [],
    });

    render(<ArtifactPane />);
    fireEvent.click(screen.getByTitle('编辑产出物'));
    fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
        target: { value: '# 测试策略蓝图\n\n背景\n用户补充\n共同内容' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
    fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

    expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(
        '# 测试策略蓝图\n\n背景\n服务端补充\n用户补充\n共同内容\n服务端后置补充'
    );
    expect(useStore.getState().artifactAuditEvents).toEqual([
        expect.objectContaining({
            stageId: 'STRATEGY',
            eventType: 'artifact_auto_merge_applied',
            summary: '合并轨迹：自动合并服务端与草稿的非重叠补充',
        }),
    ]);
});
```

- [ ] **Step 2: Run RED**

Run:

```bash
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "auto-merges server insertions with draft deletions"
```

Expected: FAIL because the `自动合并非重叠变更` button is not rendered for a draft deletion scenario.

## Task 2: Implement Conservative Safe Delete Merge

- [ ] **Step 3: Update helper logic**

In `tools/new-agents/frontend/src/components/ArtifactPane.tsx`, replace the body of `collectInsertionSegments` / `buildAutoMergedInsertionContent` with a conservative line mapping that allows draft deletions but requires server to retain every base line in order.

Implementation shape:

```ts
type MergeProjection = {
  insertions: string[][];
  retainedBaseIndexes: Set<number>;
};

const collectMergeProjection = (
  baseLines: string[],
  targetLines: string[],
  options: { allowBaseDeletions: boolean }
): MergeProjection | null => {
  const insertions = Array.from({ length: baseLines.length + 1 }, () => [] as string[]);
  const retainedBaseIndexes = new Set<number>();
  let targetIndex = 0;

  for (let baseIndex = 0; baseIndex < baseLines.length; baseIndex += 1) {
    const nextBaseLineIndex = targetLines.indexOf(baseLines[baseIndex], targetIndex);
    if (nextBaseLineIndex < 0) {
      if (options.allowBaseDeletions) continue;
      return null;
    }
    insertions[baseIndex].push(...targetLines.slice(targetIndex, nextBaseLineIndex));
    retainedBaseIndexes.add(baseIndex);
    targetIndex = nextBaseLineIndex + 1;
  }

  insertions[baseLines.length].push(...targetLines.slice(targetIndex));
  return { insertions, retainedBaseIndexes };
};
```

Then update `buildAutoMergedInsertionContent` to:

```ts
const serverProjection = collectMergeProjection(baseLines, serverLines, { allowBaseDeletions: false });
const draftProjection = collectMergeProjection(baseLines, draftLines, { allowBaseDeletions: true });
if (!serverProjection || !draftProjection) return null;

const mergedLines: string[] = [];
let appliedDraftChange = false;
for (let segmentIndex = 0; segmentIndex < serverProjection.insertions.length; segmentIndex += 1) {
  const serverInsertions = serverProjection.insertions[segmentIndex];
  const draftInsertions = draftProjection.insertions[segmentIndex];
  const mergedInsertions = mergeUniqueInsertions(serverInsertions, draftInsertions);
  if (draftInsertions.some(line => !serverInsertions.includes(line))) {
    appliedDraftChange = true;
  }
  mergedLines.push(...mergedInsertions);

  if (segmentIndex < baseLines.length) {
    if (draftProjection.retainedBaseIndexes.has(segmentIndex)) {
      mergedLines.push(baseLines[segmentIndex]);
    } else {
      appliedDraftChange = true;
    }
  }
}

const mergedContent = mergedLines.join('\n');
if (!appliedDraftChange || mergedContent === serverContent.replace(/\r\n/g, '\n')) return null;
return mergedContent;
```

Preserve current function names where practical to keep the diff narrow.

- [ ] **Step 4: Run GREEN**

Run:

```bash
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "auto-merges server insertions with draft deletions"
```

Expected: PASS.

## Task 3: Regression Checks

- [ ] **Step 5: Run ArtifactPane regression**

Run:

```bash
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
```

Expected: all ArtifactPane tests pass.

- [ ] **Step 6: Self-review**

Check:
- The helper returns `null` when server deletes or rewrites a base line.
- The existing insertion-only auto-merge test still passes.
- No backend/API/workflow contract files changed.
- No edits outside the two allowed frontend files.

## Self-Review

- Spec coverage: Task 1 covers user-visible action and audit trail; Task 2 covers safe server insertion + draft deletion merge; Task 3 covers regression.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: helper names and existing state names match `ArtifactPane.tsx`.
