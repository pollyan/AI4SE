# New Agents Artifact Section Move Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-merge safe whole-section movement conflicts in Artifact manual edit conflicts.

**Architecture:** Extend the existing `ArtifactPane.tsx` auto-merge chain. Keep insertion, safe deletion, and non-overlapping section rewrite behavior intact. Add a conservative Markdown-section movement merge result that only activates when headings are unique, section sets are unchanged, and no section is edited differently by both server and draft.

**Tech Stack:** React, Zustand, Vitest, Testing Library.

---

## Commit Boundary

This slice should produce one focused commit after main-thread verification:

```bash
git add docs/todos/new-agents-ux-professionalization.md \
  docs/superpowers/plans/2026-06-20-new-agents-artifact-section-move-merge.md \
  docs/superpowers/specs/2026-06-20-new-agents-artifact-section-move-merge-design.md \
  tools/new-agents/frontend/src/components/ArtifactPane.tsx \
  tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 支持 Artifact 章节移动自动合并"
```

The worker must not commit or push. The main agent will review, verify, commit, merge to `master`, and push.

### Task 1: RED Tests For Section Movement Auto-Merge

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: Add success-path test**

Add a test near the existing auto-merge tests:

```ts
it('auto-merges non-overlapping section movement during an artifact conflict', async () => {
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
                '',
                '## 交付计划',
                '旧交付计划',
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
            '',
            '## 交付计划',
            '旧交付计划',
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
                '',
                '## 交付计划',
                '旧交付计划',
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
                    '',
                    '## 交付计划',
                    '旧交付计划',
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
                '## 交付计划',
                '旧交付计划',
                '',
                '## 验收口径',
                '旧验收口径',
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
        '## 交付计划',
        '旧交付计划',
        '',
        '## 验收口径',
        '旧验收口径',
    ].join('\n'));
    expect(useStore.getState().artifactAuditEvents).toEqual([
        expect.objectContaining({
            stageId: 'STRATEGY',
            eventType: 'artifact_auto_merge_applied',
            summary: '合并轨迹：自动合并服务端与草稿的非重叠章节移动',
        }),
    ]);
});
```

- [x] **Step 2: Add same-section conflict negative test**

Add a test where Server and Draft both change `## 风险策略` differently while Draft also moves another section. Assert `screen.queryByRole('button', { name: '自动合并非重叠变更' })` is `null`.

- [x] **Step 3: Add repeated-heading negative test**

Add a test where Base contains duplicate `## 风险策略` headings and Draft moves one block. Assert the auto-merge button is absent.

- [x] **Step 4: Verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section movement"
```

Expected: the success-path test fails because auto-merge is not offered for section movement yet.

### Task 2: Implement Conservative Section Movement Merge

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [x] **Step 1: Add section helpers**

Near `buildAutoMergedSectionRewriteResult`, add helpers that reuse `ParsedMarkdownSections`:

```ts
const getSectionOrder = (sections: ParsedMarkdownSections): string[] => (
  sections.sections.map(section => section.heading)
);

const haveSameSectionSet = (...): boolean => { ... };
const areSectionOrdersEqual = (...): boolean => { ... };
const buildSectionMap = (...): Map<string, string[]> => { ... };
```

Implementation constraints:
- Compare headings exactly as currently parsed, including `#` level.
- Require identical preamble lines.
- Require identical heading sets across base/server/draft.
- Keep using the existing duplicate heading rejection in `parseMarkdownSectionsForAutoMerge`.

- [x] **Step 2: Add movement result**

Implement:

```ts
const buildAutoMergedSectionMoveResult = (
  baseContent: string,
  serverContent: string,
  draftContent: string
): AutoMergedConflictResult | null => { ... };
```

Algorithm:
1. Parse base/server/draft with `parseMarkdownSectionsForAutoMerge`; return null if any fails.
2. Return null if preambles differ or heading sets differ.
3. Compute `baseOrder`, `serverOrder`, `draftOrder`.
4. Determine movement order:
   - If draft order differs from base, use draft order.
   - Else if server order differs from base, use server order.
   - Else return null because existing section rewrite merge should handle non-move edits.
   - If both server and draft order differ from base and differ from each other, return null.
5. For each heading in movement order:
   - Compare server section lines to base section lines.
   - Compare draft section lines to base section lines.
   - If both changed and not equal, return null.
   - Else choose draft lines if draft changed, else server lines if server changed, else base lines.
6. Require at least one non-order content change from server or draft, or at least one movement; otherwise return null.
7. Return merged content with summary `合并轨迹：自动合并服务端与草稿的非重叠章节移动`.

- [x] **Step 3: Register movement merge after section rewrite**

Update:

```ts
const autoMergedConflict = useMemo(
  () => conflictArtifact
    ? buildAutoMergedInsertionResult(...)
      ?? buildAutoMergedSectionRewriteResult(...)
    : null,
  [...]
);
```

to:

```ts
      ?? buildAutoMergedSectionRewriteResult(...)
      ?? buildAutoMergedSectionMoveResult(...)
```

Ordering matters: keep existing rewrite behavior unchanged for same-order non-overlapping rewrites.

- [x] **Step 4: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section movement"
```

Expected: PASS.

### Task 3: Todo Record And Quality Gates

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`
- Add: `docs/superpowers/specs/2026-06-20-new-agents-artifact-section-move-merge-design.md`
- Add: `docs/superpowers/plans/2026-06-20-new-agents-artifact-section-move-merge.md`

- [x] **Step 1: Update todo progress**

Append under Artifact 协作体验深化:

```markdown
- 2026-06-20：完成第四十二块 CGA「Artifact 唯一章节移动自动合并」。
  - 保存冲突现在会在插入、安全删除和非重叠章节改写之外，识别唯一 Markdown 标题章节的整体移动：当用户只调整章节顺序，服务端只改写其他章节时，可继续使用 `自动合并非重叠变更`。
  - 点击后编辑草稿会采用安全移动顺序，并保留服务端非冲突章节改写和用户非冲突章节改写；自动合并会记录 `artifact_auto_merge_applied` 活动轨迹，并区分 `非重叠章节移动`。
  - 重复标题、章节集合变化、双方移动为不同顺序或双方改写同一章节时不显示自动合并入口，继续交给人工冲突处理。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section movement"` 观察到缺少自动合并入口失败；实现后同命令通过，并运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`、`npm run lint`、`npm run build`、`git diff --check`。
  - 剩余：段落级移动、章节新增/删除/重命名的三方 merge、更复杂冲突解析仍可作为后续增强切片。
```

- [x] **Step 2: Run final gates**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

- [x] **Step 3: Leave uncommitted for main-thread review**

Do not commit. Report changed files, RED/GREEN commands, final verification, and residual risks.
