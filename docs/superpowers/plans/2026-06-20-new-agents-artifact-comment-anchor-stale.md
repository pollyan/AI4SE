# New Agents Artifact Comment Anchor Stale Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户在批注锚点已不再存在于当前产物正文时，能在批注面板和审阅面板看到明确失效提示。

**Architecture:** 只在 `ArtifactPane` 中增加派生状态和展示，不新增后端字段或持久化 schema。状态由当前 `artifactContent` 与批注 `anchorText` 精确匹配计算；可定位批注保留现有 `定位正文` 行为，失效批注显示只读提示。

**Tech Stack:** React 19、TypeScript、Zustand store、Vitest、Testing Library。

---

## File Structure

- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - 增加批注锚点状态 helper。
  - 在批注面板和审阅面板展示失效状态。
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
  - 保留已经写出的 RED 测试 `shows stale anchor status when anchored comment text no longer exists`。
  - 确认定位成功用例不退化。
- Modify: `docs/todos/new-agents-ux-professionalization.md`
  - 记录第五十六块 CGA 完成情况和剩余“重新绑定”候选。

## Commit Boundary

- 一个聚焦 commit：`feat(new-agents): 提示批注锚点失效`
- 预计文件：`ArtifactPane.tsx`、`ArtifactPane.test.tsx`、本 spec、本文 plan、`docs/todos/new-agents-ux-professionalization.md`。
- 当前分支已有一个 RED 测试是在补齐正式 CGA/spec/plan 前写入的偏序遗留；本计划把它纳入 Task 1 的 RED evidence，并要求继续从该测试失败状态向前推进。

### Task 1: Confirm RED Test

**Files:**
- Test: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Verify the existing failing test**

The test already added in this branch is:

```tsx
it('shows stale anchor status when anchored comment text no longer exists', () => {
    useStore.setState({
        workflow: 'TEST_DESIGN',
        stageIndex: 0,
        artifactContent: '# 需求分析文档\n\n登录边界已经被改写。',
        artifactComments: [
            {
                id: 'comment-1',
                stageId: 'CLARIFY',
                content: '这里需要业务确认登录边界。',
                artifactExcerpt: '请重点确认 SSO 回调失败后的登录边界。',
                anchorText: '请重点确认 SSO 回调失败后的登录边界。',
                createdAt: 1710000000000,
                status: 'open',
                resolvedAt: null,
                replies: [],
            },
        ],
    });

    render(<ArtifactPane />);
    clickArtifactToolbarMenuItem('批注');

    expect(screen.getByText('锚点已失效')).toBeTruthy();
    expect(screen.getByText('正文已变化，请重新确认这条批注的位置。')).toBeTruthy();

    fireEvent.click(screen.getByTitle('关闭批注'));
    fireEvent.click(screen.getByRole('button', { name: '更多产物操作' }));
    fireEvent.click(screen.getByRole('menuitem', { name: '审阅' }));

    expect(screen.getByText('锚点已失效')).toBeTruthy();
});
```

- [ ] **Step 2: Run the RED test**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "stale anchor"
```

Expected: FAIL because `锚点已失效` is not rendered.

### Task 2: Add Anchor Status Helper

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Add helper near `locateArtifactCommentAnchor` helpers**

Add this helper in component scope, before rendering:

```ts
const getCommentAnchorStatus = (anchorText: string | null): 'none' | 'active' | 'stale' => {
  const normalizedAnchorText = normalizeCommentAnchorText(anchorText ?? '');
  if (!normalizedAnchorText) return 'none';
  return artifactContent.includes(normalizedAnchorText) ? 'active' : 'stale';
};
```

Rationale: keep the status derived from current artifact content. No store mutation and no server sync.

- [ ] **Step 2: Keep existing locate behavior unchanged**

Do not change:

```ts
const locateArtifactCommentAnchor = (anchorText: string) => {
  const normalizedAnchorText = normalizeCommentAnchorText(anchorText);
  if (!normalizedAnchorText) return;
  setIsEditing(false);
  setViewMode('preview');
  setActiveCommentAnchorText(normalizedAnchorText);
  window.setTimeout(() => {
    const highlight = artifactPreviewRef.current?.querySelector('[data-artifact-anchor-highlight="true"]');
    if (highlight instanceof HTMLElement && typeof highlight.scrollIntoView === 'function') {
      highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, 0);
};
```

This preserves existing successful anchor highlighting.

### Task 3: Render Stale Status in Comments Panel

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Compute status inside `currentStageComments.map`**

Change the map body from:

```tsx
{currentStageComments.map((comment) => (
  <article key={comment.id} className="rounded-lg border border-[#1e293b] bg-[#020617] p-3">
```

to:

```tsx
{currentStageComments.map((comment) => {
  const anchorStatus = getCommentAnchorStatus(comment.anchorText);
  return (
    <article key={comment.id} className="rounded-lg border border-[#1e293b] bg-[#020617] p-3">
```

and close with:

```tsx
    </article>
  );
})}
```

- [ ] **Step 2: Replace the定位正文 conditional**

Replace:

```tsx
{comment.anchorText && (
  <button
    type="button"
    onClick={() => locateArtifactCommentAnchor(comment.anchorText ?? '')}
    className="mt-2 rounded border border-blue-500/30 px-2 py-1 text-[10px] font-semibold text-blue-200 transition-colors hover:bg-blue-500/10"
  >
    定位正文
  </button>
)}
```

with:

```tsx
{anchorStatus === 'active' && comment.anchorText && (
  <button
    type="button"
    onClick={() => locateArtifactCommentAnchor(comment.anchorText ?? '')}
    className="mt-2 rounded border border-blue-500/30 px-2 py-1 text-[10px] font-semibold text-blue-200 transition-colors hover:bg-blue-500/10"
  >
    定位正文
  </button>
)}
{anchorStatus === 'stale' && (
  <div className="mt-2 rounded border border-amber-400/20 bg-amber-400/10 px-2 py-1.5">
    <div className="text-[10px] font-bold text-amber-200">锚点已失效</div>
    <div className="mt-0.5 text-[10px] leading-relaxed text-amber-100/80">
      正文已变化，请重新确认这条批注的位置。
    </div>
  </div>
)}
```

### Task 4: Render Stale Status in Review Panel

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Compute status inside `currentStageOpenComments.map`**

Change:

```tsx
currentStageOpenComments.map((comment) => (
  <article key={comment.id} className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
```

to:

```tsx
currentStageOpenComments.map((comment) => {
  const anchorStatus = getCommentAnchorStatus(comment.anchorText);
  return (
    <article key={comment.id} className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
```

and close with:

```tsx
    </article>
  );
})}
```

- [ ] **Step 2: Add status under excerpt**

After the review panel blockquote:

```tsx
<blockquote className="mt-2 border-l-2 border-amber-300/40 pl-3 text-xs leading-relaxed text-slate-500">
  {comment.artifactExcerpt || '当前产出物'}
</blockquote>
```

add:

```tsx
{anchorStatus === 'stale' && (
  <div className="mt-2 inline-flex rounded border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-[10px] font-bold text-amber-200">
    锚点已失效
  </div>
)}
```

### Task 5: Verify and Document

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: Run focused tests**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "stale anchor"
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "artifact comment|artifact review panel|highlights anchored"
```

Expected: both commands pass.

- [ ] **Step 2: Run ArtifactPane full test**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
```

Expected: all ArtifactPane tests pass.

- [ ] **Step 3: Update todo**

Append one progress record under `Artifact 协作体验深化`:

```markdown
- 2026-06-20：完成第五十六块 CGA「Artifact 批注锚点失效提示」。
  - 批注面板和产物审阅面板现在会对带 `anchorText` 但当前正文已找不到锚点文本的批注显示 `锚点已失效`。
  - 失效提示说明 `正文已变化，请重新确认这条批注的位置。`，避免用户点击定位无反馈。
  - 可定位批注继续保留现有 `定位正文` 高亮行为；无 anchorText 的普通批注不显示失效状态。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "stale anchor"` 观察到缺少提示失败；实现后同命令通过，并运行批注/审阅相关回归、ArtifactPane 全量测试、lint、build、完整前端测试和 `git diff --check`。
  - 剩余：批注锚点重新绑定当前选区仍是后续候选。
```

- [ ] **Step 4: Run final verification**

Run:

```bash
cd tools/new-agents/frontend
npm run lint
npm run build
npm run test
cd ../../..
git diff --check
git status --short --branch
git diff --stat
```

Expected:

- `npm run lint` exits 0.
- `npm run build` exits 0; existing large chunk warning is acceptable.
- `npm run test` exits 0.
- `git diff --check` exits 0.
- `git status --short --branch` only shows this milestone files in the worktree.

- [ ] **Step 5: Commit and push**

Run from the worktree root:

```bash
git add docs/superpowers/specs/2026-06-20-new-agents-artifact-comment-anchor-stale-design.md \
  docs/superpowers/plans/2026-06-20-new-agents-artifact-comment-anchor-stale.md \
  docs/todos/new-agents-ux-professionalization.md \
  tools/new-agents/frontend/src/components/ArtifactPane.tsx \
  tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 提示批注锚点失效"
```

Then fast-forward `master` and push from the main checkout, keeping unrelated zip files unstaged:

```bash
git merge --ff-only codex/new-agents-comment-anchor-status
git push origin master
```

Expected: `origin/master` includes the new commit, while unrelated zip files remain uncommitted in the main checkout.

## Self-Review

- Spec coverage: tasks cover RED test, helper, comments panel, review panel, todo, verification, commit.
- Placeholder scan: no `TODO` or `TBD`; all code steps include exact snippets.
- Type consistency: helper returns `'none' | 'active' | 'stale'`; all render branches use those exact literals.
