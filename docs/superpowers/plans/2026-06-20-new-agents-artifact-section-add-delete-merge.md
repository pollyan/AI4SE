# New Agents Artifact 章节新增删除自动合并 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Artifact 保存冲突在安全的 Markdown 章节新增/删除场景下提供 `自动合并非重叠变更`，减少用户逐行处理非冲突章节集合变化的成本。

**Architecture:** 继续复用 `ArtifactPane.tsx` 内现有冲突卡片、三方 Markdown 解析、编辑草稿和活动轨迹机制。新增一个保守的 section add/delete auto-merge helper，注册在章节改写和章节移动之后、行级插入之前；所有不确定情况降级到现有人工冲突处理。

**Tech Stack:** React 19、TypeScript 5、Zustand、Vitest、Testing Library。

---

### Task 1: 章节新增/删除自动合并测试

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: Add RED tests near the existing section rewrite/movement tests**

Add four tests inside `describe('ArtifactPane Component', () => { ... })`, near the existing `section movement` tests:

```tsx
it('auto-merges non-overlapping section add/delete when draft adds a section', async () => {
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
        artifactHistory: [{
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
        }],
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
                '旧验收口径',
                '',
                '## 覆盖策略',
                '用户新增覆盖策略：补充退款链路',
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
        '旧验收口径',
        '',
        '## 覆盖策略',
        '用户新增覆盖策略：补充退款链路',
    ].join('\n'));
    expect(useStore.getState().artifactAuditEvents).toEqual([
        expect.objectContaining({
            stageId: 'STRATEGY',
            eventType: 'artifact_auto_merge_applied',
            summary: '合并轨迹：自动合并服务端与草稿的非重叠章节增删',
        }),
    ]);
});

it('auto-merges non-overlapping section add/delete when draft deletes an unchanged section', async () => {
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
        artifactHistory: [{
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
        }],
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
        '## 验收口径',
        '旧验收口径',
    ].join('\n'));
});

it('does not auto-merge section add/delete when draft deletes a server-changed section', async () => {
    vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
        '产出物已被更新，请刷新后再保存',
        {
            stageId: 'STRATEGY',
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
                '服务端交付计划：增加上线回滚窗口',
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
        artifactHistory: [{
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
        }],
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
                '旧验收口径',
            ].join('\n'),
        },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

    await screen.findByRole('button', { name: '对比服务端版本' });
    expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
});

it('does not auto-merge section add/delete when the change looks like a section rename', async () => {
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
        artifactHistory: [{
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
        }],
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
                '## 质量口径',
                '旧验收口径',
            ].join('\n'),
        },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

    await screen.findByRole('button', { name: '对比服务端版本' });
    expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
});
```

For the two negative tests, copy the full state setup style from nearby tests instead of adding shared test fixtures.

- [x] **Step 2: Verify RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section add/delete"
```

Expected: at least the positive tests fail because `自动合并非重叠变更` is not found.

### Task 2: 章节新增/删除自动合并实现

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [x] **Step 1: Add small helpers near existing section helpers**

Add helper after `buildSectionMap`:

```ts
const getSectionHeadingSet = (sections: ParsedMarkdownSections): Set<string> => (
  new Set(getSectionOrder(sections))
);
```

- [x] **Step 2: Implement conservative add/delete merge**

Add `buildAutoMergedSectionAddDeleteResult` after `buildAutoMergedSectionMoveResult`:

```ts
const buildAutoMergedSectionAddDeleteResult = (
  baseContent: string,
  serverContent: string,
  draftContent: string
): AutoMergedConflictResult | null => {
  const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
  const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
  const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
  if (!baseSections || !serverSections || !draftSections) return null;
  if (
    !areLineGroupsEqual(baseSections.preambleLines, serverSections.preambleLines)
    || !areLineGroupsEqual(baseSections.preambleLines, draftSections.preambleLines)
  ) {
    return null;
  }

  const baseSectionMap = buildSectionMap(baseSections);
  const serverSectionMap = buildSectionMap(serverSections);
  const draftSectionMap = buildSectionMap(draftSections);
  const baseHeadingSet = getSectionHeadingSet(baseSections);
  const serverHeadingSet = getSectionHeadingSet(serverSections);
  const draftHeadingSet = getSectionHeadingSet(draftSections);
  const serverAddedHeadings = getSectionOrder(serverSections).filter(heading => !baseHeadingSet.has(heading));
  const draftAddedHeadings = getSectionOrder(draftSections).filter(heading => !baseHeadingSet.has(heading));
  const serverDeletedHeadings = getSectionOrder(baseSections).filter(heading => !serverHeadingSet.has(heading));
  const draftDeletedHeadings = getSectionOrder(baseSections).filter(heading => !draftHeadingSet.has(heading));

  if (
    (serverAddedHeadings.length > 0 && serverDeletedHeadings.length > 0)
    || (draftAddedHeadings.length > 0 && draftDeletedHeadings.length > 0)
  ) {
    return null;
  }
  if (
    serverAddedHeadings.length === 0
    && serverDeletedHeadings.length === 0
    && draftAddedHeadings.length === 0
    && draftDeletedHeadings.length === 0
  ) {
    return null;
  }

  let hasServerChange = serverAddedHeadings.length > 0 || serverDeletedHeadings.length > 0;
  const mergedSectionLines: string[][] = [];

  for (const section of serverSections.sections) {
    const heading = section.heading;
    const serverSectionLines = serverSectionMap.get(heading);
    const draftSectionLines = draftSectionMap.get(heading);
    if (!serverSectionLines) return null;

    if (!baseHeadingSet.has(heading)) {
      if (draftSectionLines && !areLineGroupsEqual(serverSectionLines, draftSectionLines)) {
        return null;
      }
      mergedSectionLines.push(serverSectionLines);
      continue;
    }

    const baseSectionLines = baseSectionMap.get(heading);
    if (!baseSectionLines) return null;
    const serverChanged = !areLineGroupsEqual(baseSectionLines, serverSectionLines);
    if (draftDeletedHeadings.includes(heading)) {
      if (serverChanged) return null;
      continue;
    }

    if (!draftSectionLines) return null;
    const draftChanged = !areLineGroupsEqual(baseSectionLines, draftSectionLines);
    if (
      serverChanged
      && draftChanged
      && !areLineGroupsEqual(serverSectionLines, draftSectionLines)
    ) {
      return null;
    }

    if (draftChanged) {
      mergedSectionLines.push(draftSectionLines);
    } else if (serverChanged) {
      hasServerChange = true;
      mergedSectionLines.push(serverSectionLines);
    } else {
      mergedSectionLines.push(baseSectionLines);
    }
  }

  for (const heading of serverDeletedHeadings) {
    const baseSectionLines = baseSectionMap.get(heading);
    const draftSectionLines = draftSectionMap.get(heading);
    if (!baseSectionLines) return null;
    if (draftSectionLines && !areLineGroupsEqual(baseSectionLines, draftSectionLines)) {
      return null;
    }
  }

  for (const heading of draftAddedHeadings) {
    if (serverHeadingSet.has(heading)) continue;
    const draftSectionLines = draftSectionMap.get(heading);
    if (!draftSectionLines) return null;
    mergedSectionLines.push(draftSectionLines);
  }

  if (!hasServerChange) return null;

  const mergedContent = [
    ...baseSections.preambleLines,
    ...mergedSectionLines.flat(),
  ].join('\n');
  if (mergedContent === serverContent.replace(/\r\n/g, '\n')) return null;

  return {
    content: mergedContent,
    summary: '合并轨迹：自动合并服务端与草稿的非重叠章节增删',
  };
};
```

If the exact implementation needs adjustment to satisfy all tests, keep these invariants:
- no repeated headings because `parseMarkdownSectionsForAutoMerge` already rejects them;
- server-side and draft-side section add/delete are both supported when they are non-overlapping and conservative;
- no auto-merge when draft deletes a server-changed section;
- no auto-merge when server deletes a draft-changed section;
- no auto-merge when both sides add the same new heading with different content;
- no auto-merge when draft replaced a base heading with a new heading while not preserving all unchanged base headings.

- [x] **Step 3: Register the helper**

Update `autoMergedConflict`:

```ts
? buildAutoMergedSectionRewriteResult(artifactContent, conflictArtifact.content, editDraft)
  ?? buildAutoMergedSectionMoveResult(artifactContent, conflictArtifact.content, editDraft)
  ?? buildAutoMergedSectionAddDeleteResult(artifactContent, conflictArtifact.content, editDraft)
  ?? buildAutoMergedInsertionResult(artifactContent, conflictArtifact.content, editDraft)
```

- [x] **Step 4: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section add/delete"
```

Expected: the new section add/delete tests pass.

### Task 3: 文档记录与验证

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`
- Modify: `docs/superpowers/plans/2026-06-20-new-agents-artifact-section-add-delete-merge.md`

- [x] **Step 1: Update todo progress**

Append after the fourth十二块 CGA record:

```markdown
- 2026-06-20：完成第四十三块 CGA「Artifact 章节新增删除自动合并」。
  - 保存冲突现在会在现有非重叠插入、安全删除、章节改写和章节移动之外，识别双向保守的章节集合变化：服务端或草稿任一侧新增完整章节、删除对方未改写的旧章节，或双方新增不同标题章节时，可继续使用 `自动合并非重叠变更`。
  - 点击后编辑草稿会按服务端章节顺序为基准保留服务端新增/删除和非冲突改写，并把 draft-only 新增章节追加到末尾，同时记录 `artifact_auto_merge_applied` 活动轨迹，summary 区分 `非重叠章节增删`。
  - 章节重命名、重复标题、服务端删除了草稿改写章节、草稿删除了服务端改写章节、双方改写同一章节且内容不同、双方新增同名章节且内容不同等歧义场景不显示自动合并入口，继续交给人工冲突处理。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section add/delete"` 观察到 server-side 章节新增/删除正例失败；实现后同命令通过，并运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`、`npm run lint`、`npm run build`、`git diff --check`。
  - 剩余：章节重命名、段落级移动和更复杂三方 merge 解析仍可作为后续增强切片。
```

### Review Fix: 双向保守章节集合变化

- [x] **Step 1: Add server-side section add/delete and same-heading add conflict tests**

新增覆盖：
- server 新增章节 + draft 改写其他旧章节；
- server 删除未被 draft 改写的旧章节 + draft 改写其他旧章节；
- 双方新增不同标题章节；
- 双方新增同一新标题但内容不同。

- [x] **Step 2: Verify RED**

运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section add/delete"`，观察到 3 个新增正例失败；其中 server 新增章节用例还暴露了 line-level insertion helper 先截获导致 summary 仍为 `非重叠补充`。

- [x] **Step 3: Extend section add/delete merge**

修正为以服务端章节顺序为基准，支持 server-side 和 draft-side 的非重叠章节新增/删除，draft-only 新增章节追加到末尾，并将章节 add/delete helper 排在 line-level insertion helper 前面。

- [x] **Step 4: Run full verification after review fix**

### Review Fix: 阻断 unsafe 章节集合变化 fall-through

- [x] **Step 1: Add fall-through regression tests**

新增两个 reviewer 指出的回归：
- 双方新增同名紧凑章节且内容不同，不得被行级 insertion fallback 自动合并。
- server 新增章节、draft 重命名另一个旧章节，不得被行级 insertion fallback 自动合并。

- [x] **Step 2: Verify RED**

运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section add/delete"`，观察到两个新增回归失败，均因为仍显示 `自动合并非重叠变更`。

- [x] **Step 3: Add section-set-change veto before insertion fallback**

新增 `hasMarkdownSectionSetChangeForAutoMerge`，当三方都能解析为唯一 Markdown 章节且章节集合发生变化时，只有 section add/delete helper 返回安全合并结果才允许自动合并；否则返回 `null`，不再继续落到 line-level insertion helper。

- [x] **Step 4: Verify GREEN and full regression**

运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section add/delete"` 10/10 通过；随后运行完整 `ArtifactPane` 测试、lint、build 和 `git diff --check`。

- [x] **Step 2: Mark plan checkboxes complete as steps finish**

Update this plan's checkboxes from `[ ]` to `[x]` only after the corresponding action is actually completed.

- [x] **Step 3: Run full verification**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
npm run lint
npm run build
cd ../../..
git diff --check
```

Expected: all commands exit 0.

### Task 4: Commit boundary

**Files:**
- Stage only:
  - `docs/todos/new-agents-ux-professionalization.md`
  - `docs/superpowers/specs/2026-06-20-new-agents-artifact-section-add-delete-merge-design.md`
  - `docs/superpowers/plans/2026-06-20-new-agents-artifact-section-add-delete-merge.md`
  - `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Inspect status and staged files**

Run:

```bash
git status --short --branch
git diff --name-only
git ls-files --others --exclude-standard
```

Expected: only the files listed above are modified or untracked.

- [ ] **Step 2: Commit after verification**

Run:

```bash
git add docs/todos/new-agents-ux-professionalization.md \
  docs/superpowers/specs/2026-06-20-new-agents-artifact-section-add-delete-merge-design.md \
  docs/superpowers/plans/2026-06-20-new-agents-artifact-section-add-delete-merge.md \
  tools/new-agents/frontend/src/components/ArtifactPane.tsx \
  tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 支持 Artifact 章节增删自动合并"
```
