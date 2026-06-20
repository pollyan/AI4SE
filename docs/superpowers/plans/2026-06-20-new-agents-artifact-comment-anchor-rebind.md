# New Agents Artifact 批注锚点重新绑定 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户在批注锚点失效后，可以选中当前正文并把批注重新绑定到新位置。

**Architecture:** 复用现有轻量 `anchorText` 模型，不新增后端字段。前端 store 增加单条批注锚点更新 action，`ArtifactPane` 通过现有 Selection API 读取 artifact 内选区，更新后复用 collaboration sync。

**Tech Stack:** React 19、TypeScript、Zustand、Vitest、Testing Library。

---

## File Structure

- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - 在 `ChatState` / store action 类型中增加 `updateArtifactCommentAnchor`。
- Modify: `tools/new-agents/frontend/src/store.ts`
  - 实现 `updateArtifactCommentAnchor(commentId, anchorText)`。
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`
  - 增加 store 层锚点更新测试。
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - 为失效批注增加 `重新绑定选区` 操作和无选区提示。
  - 重新绑定后复用 `syncArtifactCollaborationState`。
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
  - 增加 RED 测试覆盖重绑、同步、定位恢复和无有效选区。
- Modify: `docs/todos/new-agents-ux-professionalization.md`
  - 记录第五十七块 CGA 完成情况和剩余候选。

## Commit Boundary

- One focused commit: `feat(new-agents): 支持批注锚点重新绑定`
- Commit includes implementation, tests, spec, plan, and todo update.

## Task 1: Store Action TDD

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/store.ts`
- Test: `tools/new-agents/frontend/src/__tests__/store.test.ts`

- [ ] **Step 1: Write failing store test**

Add a test under the store artifact collaboration tests:

```ts
it('updates artifact comment anchor and excerpt', () => {
  useStore.setState({
    workflow: 'TEST_DESIGN',
    stageIndex: 0,
    artifactComments: [
      {
        id: 'comment-1',
        stageId: 'CLARIFY',
        content: '确认登录边界。',
        artifactExcerpt: '旧登录边界',
        anchorText: '旧登录边界',
        createdAt: 1710000000000,
        status: 'open',
        resolvedAt: null,
        replies: [],
      },
    ],
  });

  useStore.getState().updateArtifactCommentAnchor('comment-1', '新的登录边界');

  expect(useStore.getState().artifactComments).toEqual([
    expect.objectContaining({
      id: 'comment-1',
      artifactExcerpt: '新的登录边界',
      anchorText: '新的登录边界',
    }),
  ]);
});
```

- [ ] **Step 2: Run RED store test**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/__tests__/store.test.ts -t "updates artifact comment anchor"
```

Expected: FAIL because `updateArtifactCommentAnchor` does not exist.

- [ ] **Step 3: Add action type**

In `tools/new-agents/frontend/src/core/types.ts`, add this action to the store type near artifact comment actions:

```ts
updateArtifactCommentAnchor: (commentId: string, anchorText: string) => void;
```

- [ ] **Step 4: Implement minimal store action**

In `tools/new-agents/frontend/src/store.ts`, add:

```ts
updateArtifactCommentAnchor: (commentId, anchorText) => set((state) => {
  const normalizedAnchorText = sanitizeOptionalArtifactText(anchorText);
  if (!normalizedAnchorText) return {};

  return {
    artifactComments: state.artifactComments.map((comment) => (
      comment.id === commentId
        ? {
          ...comment,
          artifactExcerpt: normalizedAnchorText,
          anchorText: normalizedAnchorText,
        }
        : comment
    )),
  };
}),
```

- [ ] **Step 5: Run GREEN store test**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/__tests__/store.test.ts -t "updates artifact comment anchor"
```

Expected: PASS.

## Task 2: ArtifactPane Rebind TDD

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Test: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Write failing component test for successful rebind**

Add a test near the existing stale anchor test:

```tsx
it('rebinds stale comment anchor to selected artifact text and syncs it', async () => {
  vi.mocked(updateRunArtifactCollaboration).mockResolvedValue({
    artifactComments: [],
    artifactSectionLocks: [],
  });
  useStore.setState({
    workflow: 'TEST_DESIGN',
    stageIndex: 0,
    currentRunId: 'run-1',
    artifactContent: '# 需求分析文档\n\n新的登录边界需要覆盖 SSO 回调。',
    artifactComments: [
      {
        id: 'comment-1',
        stageId: 'CLARIFY',
        content: '这里需要业务确认登录边界。',
        artifactExcerpt: '旧登录边界',
        anchorText: '旧登录边界',
        createdAt: 1710000000000,
        status: 'open',
        resolvedAt: null,
        replies: [],
      },
    ],
  });

  const { container } = render(<ArtifactPane />);
  const selectedParagraph = screen.getByText('新的登录边界需要覆盖 SSO 回调。');
  const textNode = selectedParagraph.firstChild;
  expect(textNode).toBeTruthy();
  const range = document.createRange();
  range.setStart(textNode as ChildNode, 0);
  range.setEnd(textNode as ChildNode, '新的登录边界'.length);
  const selection = window.getSelection();
  selection?.removeAllRanges();
  selection?.addRange(range);

  clickArtifactToolbarMenuItem('批注');
  fireEvent.click(screen.getByRole('button', { name: '重新绑定选区' }));

  expect(useStore.getState().artifactComments[0]).toEqual(expect.objectContaining({
    artifactExcerpt: '新的登录边界',
    anchorText: '新的登录边界',
  }));
  expect(updateRunArtifactCollaboration).toHaveBeenCalledWith(
    'run-1',
    expect.objectContaining({
      comments: [
        expect.objectContaining({
          id: 'comment-1',
          artifactExcerpt: '新的登录边界',
          anchorText: '新的登录边界',
        }),
      ],
    })
  );

  fireEvent.click(screen.getByRole('button', { name: '定位正文' }));
  const highlight = container.querySelector('[data-artifact-anchor-highlight="true"]');
  expect(highlight?.textContent).toBe('新的登录边界');
});
```

- [ ] **Step 2: Write failing component test for missing selection**

Add:

```tsx
it('does not rebind stale comment anchor without artifact selection', () => {
  useStore.setState({
    workflow: 'TEST_DESIGN',
    stageIndex: 0,
    artifactContent: '# 需求分析文档\n\n新的登录边界需要覆盖 SSO 回调。',
    artifactComments: [
      {
        id: 'comment-1',
        stageId: 'CLARIFY',
        content: '这里需要业务确认登录边界。',
        artifactExcerpt: '旧登录边界',
        anchorText: '旧登录边界',
        createdAt: 1710000000000,
        status: 'open',
        resolvedAt: null,
        replies: [],
      },
    ],
  });

  window.getSelection()?.removeAllRanges();

  render(<ArtifactPane />);
  clickArtifactToolbarMenuItem('批注');
  fireEvent.click(screen.getByRole('button', { name: '重新绑定选区' }));

  expect(screen.getByText('请先在右侧正文中选中新的批注位置。')).toBeTruthy();
  expect(useStore.getState().artifactComments[0]).toEqual(expect.objectContaining({
    artifactExcerpt: '旧登录边界',
    anchorText: '旧登录边界',
  }));
});
```

- [ ] **Step 3: Run RED component tests**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "rebinds stale comment anchor|does not rebind stale comment anchor"
```

Expected: FAIL because `重新绑定选区` is not rendered.

- [ ] **Step 4: Wire store action and local error state**

In `ArtifactPane.tsx`, read the new action:

```ts
const updateArtifactCommentAnchor = useStore((state) => state.updateArtifactCommentAnchor);
```

Add local state:

```ts
const [commentAnchorRebindErrors, setCommentAnchorRebindErrors] = useState<Record<string, string>>({});
```

- [ ] **Step 5: Add rebind handler**

Add near comment handlers:

```ts
const rebindCurrentStageCommentAnchor = (commentId: string) => {
  const anchorText = captureSelectedArtifactText();
  if (!anchorText) {
    setCommentAnchorRebindErrors((errors) => ({
      ...errors,
      [commentId]: '请先在右侧正文中选中新的批注位置。',
    }));
    return;
  }

  updateArtifactCommentAnchor(commentId, anchorText);
  syncArtifactCollaborationState();
  setCommentAnchorRebindErrors((errors) => {
    const nextErrors = { ...errors };
    delete nextErrors[commentId];
    return nextErrors;
  });
};
```

- [ ] **Step 6: Render rebind control for stale comments**

Inside the stale anchor block, add:

```tsx
<button
  type="button"
  onClick={() => rebindCurrentStageCommentAnchor(comment.id)}
  className="mt-2 rounded border border-amber-300/30 px-2 py-1 text-[10px] font-semibold text-amber-100 transition-colors hover:bg-amber-300/10"
>
  重新绑定选区
</button>
{commentAnchorRebindErrors[comment.id] && (
  <div className="mt-1 text-[10px] leading-relaxed text-amber-100">
    {commentAnchorRebindErrors[comment.id]}
  </div>
)}
```

- [ ] **Step 7: Run GREEN component tests**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "rebinds stale comment anchor|does not rebind stale comment anchor"
```

Expected: PASS.

## Task 3: Regression, Todo, and Commit

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: Run focused regression**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "stale anchor|highlights anchored|syncs artifact comments"
npm run test -- --run src/__tests__/store.test.ts -t "artifact comment"
```

Expected: PASS.

- [ ] **Step 2: Run expanded verification**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
npm run lint
npm run build
npm run test
cd ../../..
git diff --check
```

Expected: all commands exit 0. Existing Vite large chunk warning is acceptable.

- [ ] **Step 3: Update todo**

Append under Artifact 协作体验深化:

```markdown
- 2026-06-20：完成第五十七块 CGA「Artifact 批注锚点重新绑定」。
  - 批注锚点失效后，用户可以在当前 artifact 正文中选中新位置，并点击 `重新绑定选区` 更新批注的 `anchorText` 和 `artifactExcerpt`。
  - 重新绑定后 `定位正文` 恢复可用，协作状态继续通过现有 run collaboration snapshot 同步，不新增后端字段。
  - 没有有效 artifact 选区时不会写入错误锚点，会提示 `请先在右侧正文中选中新的批注位置。`。
  - 验证：先运行重绑定相关测试观察到缺少 `重新绑定选区` 失败；实现后运行重绑定聚焦测试、批注锚点回归、store 测试、`ArtifactPane` 全量组件测试、`npm run lint`、`npm run build`、完整前端测试和 `git diff --check`。
  - 剩余：更复杂但可证明安全的三方 merge 解析仍是下一候选。
```

- [ ] **Step 4: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-06-20-new-agents-artifact-comment-anchor-rebind-design.md \
  docs/superpowers/plans/2026-06-20-new-agents-artifact-comment-anchor-rebind.md \
  docs/todos/new-agents-ux-professionalization.md \
  tools/new-agents/frontend/src/core/types.ts \
  tools/new-agents/frontend/src/store.ts \
  tools/new-agents/frontend/src/__tests__/store.test.ts \
  tools/new-agents/frontend/src/components/ArtifactPane.tsx \
  tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 支持批注锚点重新绑定"
```

Expected: one focused commit on `codex/new-agents-comment-anchor-rebind`.

## Self-Review

- Spec coverage: plan covers store action, UI interaction, sync, no-selection feedback, tests, todo and commit.
- Placeholder scan: no unresolved placeholders.
- Type consistency: action name is consistently `updateArtifactCommentAnchor(commentId, anchorText)`.
