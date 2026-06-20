# New Agents Artifact 跨章节段落移动自动合并 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支持安全的跨章节普通段落移动与非冲突章节改写自动合并。

**Architecture:** 只在 `ArtifactPane.tsx` 的前端冲突自动合并逻辑中新增一个专门合并器，放在同章节段落移动合并之后、章节移动合并之前。保持 backend、store、SSE、导出、Markdown renderer 不变；结构化块内部重排继续保守拒绝。

**Tech Stack:** React 19、TypeScript 5、Vitest、Testing Library、Zustand。

---

### Task 1: 跨章节段落移动测试

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: Add RED positive tests**

Add tests near the existing paragraph movement tests:

```ts
it('auto-merges paragraph movement across sections when draft moves one paragraph and server rewrites another section', async () => {
    const baseContent = [
        '# 冲突文档',
        '',
        '## 背景',
        '',
        '登录链路需要覆盖账号密码。',
        '',
        'SSO 回调需要单独确认。',
        '',
        '## 风险',
        '',
        '验证码失败需要降级。',
        '',
        '## 结论',
        '',
        '保持默认方案。',
    ].join('\n');
    const serverContent = baseContent.replace('保持默认方案。', '保持默认方案，并补充灰度观察。');
    const draftContent = [
        '# 冲突文档',
        '',
        '## 背景',
        '',
        '登录链路需要覆盖账号密码。',
        '',
        '## 风险',
        '',
        '验证码失败需要降级。',
        '',
        'SSO 回调需要单独确认。',
        '',
        '## 结论',
        '',
        '保持默认方案。',
    ].join('\n');

    await openConflictDiff(baseContent, serverContent, draftContent);
    fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

    expect(screen.getByLabelText('产出物编辑内容')).toHaveValue([
        '# 冲突文档',
        '',
        '## 背景',
        '',
        '登录链路需要覆盖账号密码。',
        '',
        '## 风险',
        '',
        '验证码失败需要降级。',
        '',
        'SSO 回调需要单独确认。',
        '',
        '## 结论',
        '',
        '保持默认方案，并补充灰度观察。',
    ].join('\n'));
    expect(useStore.getState().artifactAuditEvents).toEqual([
        expect.objectContaining({
            eventType: 'artifact_auto_merge_applied',
            summary: '合并轨迹：自动合并服务端与草稿的非重叠跨章节段落移动',
        }),
    ]);
});
```

Add server-move/draft-rewrite and same-move positive cases with the same fixture style.

- [x] **Step 2: Add RED negative tests**

Add tests whose names include:

```ts
it('does not auto-merge paragraph movement across sections when the moved paragraph is rewritten', async () => { ... });
it('does not auto-merge paragraph movement across sections when paragraph blocks repeat', async () => { ... });
it('does not auto-merge paragraph movement across sections for list items', async () => { ... });
it('does not auto-merge paragraph movement across sections for table rows', async () => { ... });
it('does not auto-merge paragraph movement across sections inside fenced blocks', async () => { ... });
it('does not auto-merge paragraph movement across sections when both sides move different paragraphs', async () => { ... });
```

Each negative test should assert:

```ts
expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
```

- [x] **Step 3: Verify RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "across sections"
```

Expected: the new positive tests fail because no cross-section paragraph move auto merge exists; existing negative cases continue to pass.

### Task 2: Implement cross-section paragraph move merger

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [x] **Step 1: Add narrow cross-section move types and parser**

Add `CrossSectionParagraphMoveChange` near `ParagraphMoveChange`. Add a helper that parses safe paragraph blocks per section while allowing one remaining block:

```ts
type CrossSectionParagraphMoveChange = {
  movedKey: string;
  sourceHeading: string;
  targetHeading: string;
  sectionOrders: Map<string, string[]>;
};
```

- [x] **Step 2: Detect one safe moved paragraph across sections**

Implement `findCrossSectionParagraphMoveChange(baseSections, targetSections)`. It must:

- Require same section shape.
- Reject unsafe blocks, duplicate paragraph keys, additions, deletions, or rewrites.
- Return exactly one paragraph key whose heading changed.

- [x] **Step 3: Build merged content**

Add `buildAutoMergedCrossSectionParagraphMoveResult(baseContent, serverContent, draftContent)` after `buildAutoMergedParagraphMoveResult`. It must:

- Require identical preamble and same section shape.
- Support one-sided move + other-side changes outside source/target.
- Support both sides moving the same paragraph to the same target order.
- Reject edits inside source/target by the non-moving side.
- Return summary `合并轨迹：自动合并服务端与草稿的非重叠跨章节段落移动`.

- [x] **Step 4: Wire into autoMergedConflict order**

Call the new merger after same-section paragraph move and before section move:

```ts
const crossSectionParagraphMoveMerge = buildAutoMergedCrossSectionParagraphMoveResult(...);
if (crossSectionParagraphMoveMerge) return crossSectionParagraphMoveMerge;
```

- [x] **Step 5: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "across sections"
```

Expected: all cross-section tests pass.

### Task 3: Regression and docs

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`
- Modify: `docs/superpowers/plans/2026-06-20-new-agents-cross-section-paragraph-merge.md`

- [x] **Step 1: Update todo progress**

Append under Artifact 协作体验深化:

```markdown
- 2026-06-20：完成第四十六块 CGA「Artifact 跨章节段落移动自动合并」。
  - 保存冲突现在会识别唯一普通段落跨章节移动：当一侧把段落移动到另一个章节，另一侧只改写非源/目标章节时，可继续使用 `自动合并非重叠变更`。
  - 双方把同一普通段落移动到同一目标章节位置时也可自动合并；移动段落被改写、重复段落、列表/表格/fenced block 或双方移动不同段落时继续保守拒绝。
  - 自动合并会记录 `artifact_auto_merge_applied` 活动轨迹，并区分 `非重叠跨章节段落移动`。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "across sections"` 观察到跨章节正例失败；实现后同命令通过，并运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`、`npm run lint`、`npm run build`、`git diff --check`。
  - 剩余：结构化块内部重排和更复杂三方 merge 解析仍可作为后续增强切片。
```

- [x] **Step 2: Run full verification**

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

### Task 4: Commit

**Files:**
- Stage:
  - `docs/todos/new-agents-ux-professionalization.md`
  - `docs/superpowers/specs/2026-06-20-new-agents-cross-section-paragraph-merge-design.md`
  - `docs/superpowers/plans/2026-06-20-new-agents-cross-section-paragraph-merge.md`
  - `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Inspect status**

Run:

```bash
git status --short --branch
git diff --name-only
git ls-files --others --exclude-standard
```

- [ ] **Step 2: Commit**

Run:

```bash
git add docs/todos/new-agents-ux-professionalization.md \
  docs/superpowers/specs/2026-06-20-new-agents-cross-section-paragraph-merge-design.md \
  docs/superpowers/plans/2026-06-20-new-agents-cross-section-paragraph-merge.md \
  tools/new-agents/frontend/src/components/ArtifactPane.tsx \
  tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 支持 Artifact 跨章节段落移动自动合并"
```
