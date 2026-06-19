# New Agents Artifact Section Rewrite Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-merge safe non-overlapping Markdown section rewrites during Artifact save conflicts.

**Architecture:** Extend the existing ArtifactPane conflict merge helper. Keep the current conflict UI and audit event model, but let `autoMergedConflictContent` choose either the existing insertion/deletion merge or a new conservative section-rewrite merge.

**Tech Stack:** React, TypeScript, Vitest, existing Zustand store and ArtifactPane tests.

---

### Task 1: RED Test For Section Rewrite Auto Merge

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Write the failing test**

Add a test near the existing auto-merge conflict tests:

```ts
it('auto-merges non-overlapping section rewrites during an artifact conflict', async () => {
    vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
        '产出物已被更新，请刷新后再保存',
        {
            stageId: 'STRATEGY',
            content: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '服务端风险策略：优先覆盖支付链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            versionNumber: 3,
        },
    ));
    useStore.setState({
        workflow: 'TEST_DESIGN',
        stageIndex: 1,
        currentRunId: 'run-123',
        artifactContent: [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '旧风险策略',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n'),
        stageArtifacts: {
            STRATEGY: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
        },
        artifactHistory: [
            {
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
                stageId: 'STRATEGY',
            },
        ],
        artifactAuditEvents: [],
    });

    render(<ArtifactPane />);
    fireEvent.click(screen.getByTitle('编辑产出物'));
    fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
        target: {
            value: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '用户验收口径：增加异常回滚检查',
            ].join('\n'),
        },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
    fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

    expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
        '# 测试策略蓝图',
        '',
        '## 风险策略',
        '服务端风险策略：优先覆盖支付链路',
        '',
        '## 验收口径',
        '用户验收口径：增加异常回滚检查',
    ].join('\n'));
    expect(useStore.getState().artifactAuditEvents).toEqual([
        expect.objectContaining({
            stageId: 'STRATEGY',
            eventType: 'artifact_auto_merge_applied',
            summary: '合并轨迹：自动合并服务端与草稿的非重叠章节改写',
        }),
    ]);
});
```

- [ ] **Step 2: Verify RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "auto-merges non-overlapping section rewrites"
```

Expected: fail because the existing auto-merge helper only handles insertions and safe deletions.

### Task 2: Section Rewrite Merge Helper

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Add merge result type**

Represent auto-merge output as:

```ts
type AutoMergedConflictResult = {
  content: string;
  summary: string;
};
```

- [ ] **Step 2: Preserve existing insertion merge**

Wrap the existing `buildAutoMergedInsertionContent` result:

```ts
const buildAutoMergedInsertionResult = (...) => {
  const content = buildAutoMergedInsertionContent(...);
  return content
    ? { content, summary: '合并轨迹：自动合并服务端与草稿的非重叠补充' }
    : null;
};
```

- [ ] **Step 3: Add conservative section parser**

Parse only unique Markdown headings:

- heading line matches `#{1,6} text`
- no duplicate heading text
- server and draft must have the same heading order as base
- pre-heading content must be unchanged

- [ ] **Step 4: Build section rewrite merge**

For each base section:

- If server changed and draft changed the same section differently, return `null`.
- If only server changed, use server section.
- If only draft changed, use draft section.
- If neither changed, use base section.
- Require at least one draft section change and merged content different from server content.

- [ ] **Step 5: Wire into `autoMergedConflictContent`**

Try existing insertion/deletion merge first, then section rewrite merge:

```ts
const autoMergedConflict = buildAutoMergedInsertionResult(...)
  ?? buildAutoMergedSectionRewriteResult(...);
```

Update `applyAutoMergedConflictContent` to use `autoMergedConflict.content` and `autoMergedConflict.summary`.

- [ ] **Step 6: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "auto-merges non-overlapping section rewrites"
```

Expected: pass.

### Task 3: Regression, Docs, Commit

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: Run focused regression**

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
npm run lint
npm run build
```

- [ ] **Step 2: Update todo progress**

Append a progress entry documenting section rewrite auto-merge and verification.

- [ ] **Step 3: Check whitespace**

```bash
git diff --check
```

- [ ] **Step 4: Commit**

```bash
git add docs/todos/new-agents-ux-professionalization.md docs/superpowers/specs/2026-06-20-new-agents-artifact-section-rewrite-merge-design.md docs/superpowers/plans/2026-06-20-new-agents-artifact-section-rewrite-merge.md tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 支持章节改写冲突自动合并"
```
