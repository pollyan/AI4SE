# New Agents Artifact 审阅面板处理闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Artifact 审阅面板从只读摘要升级为可处理的审阅中心。

**Architecture:** 复用现有 `ArtifactPane` 状态和 store action，不新增后端 API。审阅面板内的动作只调用已存在的批注状态、锚点定位/重绑、章节锁定面板、历史视图能力，并在打开其他处理面板时关闭审阅面板，避免浮层叠加。

**Tech Stack:** React 19、TypeScript、Zustand、Vitest、Testing Library。

---

## File Structure

- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - 为审阅面板增加操作按钮和少量事件处理函数。
  - 复用现有 `toggleCurrentStageCommentStatus`、`locateArtifactCommentAnchor`、`rebindCurrentStageCommentAnchor`、`setShowSectionLocks`、`setActiveTab`。
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
  - 扩展 `artifact review panel` 相关测试，先覆盖缺失行为。
- Modify: `docs/todos/new-agents-ux-professionalization.md`
  - 追加本轮进展记录。

## Commit Boundary

一个聚焦 commit：

- `feat(new-agents): 完善 Artifact 审阅处理闭环`

若实现过程中发现必须触达后端协作 API 或新增复杂 merge 逻辑，停止并重做 CGA；本计划不扩大到该范围。

### Task 1: Review Panel Actions RED

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Write failing tests**

Add tests under the existing review panel describe/test area:

```tsx
it('resolves unresolved comments directly from the artifact review panel', async () => {
  renderArtifactPane({
    artifactComments: [
      {
        id: 'comment-open',
        stageId: 'CLARIFY',
        content: '需要确认验证码策略',
        artifactExcerpt: '验证码策略',
        anchorText: '验证码策略',
        createdAt: 1710000000000,
        status: 'open',
        replies: [],
      },
    ],
  });

  openArtifactMoreMenu();
  fireEvent.click(screen.getByRole('menuitem', { name: '审阅' }));
  fireEvent.click(screen.getByRole('button', { name: '标记已解决：需要确认验证码策略' }));

  expect(screen.queryByText('需要确认验证码策略')).toBeNull();
  openArtifactMoreMenu();
  fireEvent.click(screen.getByRole('menuitem', { name: '批注' }));
  expect(screen.getByText('已解决')).not.toBeNull();
});
```

```tsx
it('opens comment handling from stale review anchors', () => {
  renderArtifactPane({
    artifactContent: '# 文档\n\n新的正文',
    artifactComments: [
      {
        id: 'comment-stale',
        stageId: 'CLARIFY',
        content: '旧位置需要处理',
        artifactExcerpt: '旧正文',
        anchorText: '旧正文',
        createdAt: 1710000000000,
        status: 'open',
        replies: [],
      },
    ],
  });

  openArtifactMoreMenu();
  fireEvent.click(screen.getByRole('menuitem', { name: '审阅' }));
  fireEvent.click(screen.getByRole('button', { name: '处理失效锚点：旧位置需要处理' }));

  expect(screen.getByText('产出物批注')).not.toBeNull();
  expect(screen.getByRole('button', { name: '重新绑定选区' })).not.toBeNull();
});
```

```tsx
it('opens section locks and history from the artifact review panel', () => {
  renderArtifactPane({
    artifactHistory: [{ id: 'version-1', content: '# 历史版本', timestamp: 1710000000000 }],
    artifactSectionLocks: [
      {
        id: 'lock-1',
        stageId: 'CLARIFY',
        heading: '## 已确认范围',
        content: '## 已确认范围\n登录',
        createdAt: 1710000000000,
      },
    ],
  });

  openArtifactMoreMenu();
  fireEvent.click(screen.getByRole('menuitem', { name: '审阅' }));
  fireEvent.click(screen.getByRole('button', { name: '管理锁定章节：## 已确认范围' }));
  expect(screen.getByText('章节锁定')).not.toBeNull();

  fireEvent.click(screen.getByTitle('关闭章节锁定'));
  openArtifactMoreMenu();
  fireEvent.click(screen.getByRole('menuitem', { name: '审阅' }));
  fireEvent.click(screen.getByRole('button', { name: '查看最近版本：version-1' }));
  expect(screen.getByRole('button', { name: '版本 version-1' })).not.toBeNull();
});
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "artifact review panel"
```

Expected: FAIL because the review panel does not expose these buttons yet.

### Task 2: Minimal Review Panel Implementation

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Add review action helpers**

Add local helpers near existing comment/lock handlers:

```tsx
const resolveCommentFromReview = (commentId: string) => {
  setArtifactCommentStatus(commentId, 'resolved');
};

const openCommentFromReview = () => {
  setShowReviewPanel(false);
  setShowSectionLocks(false);
  setShowComments(true);
};

const openSectionLocksFromReview = () => {
  setShowReviewPanel(false);
  setShowComments(false);
  setShowSectionLocks(true);
};

const openHistoryFromReview = () => {
  setShowReviewPanel(false);
  openHistory();
};
```

These helper names map to existing state and functions in `ArtifactPane.tsx`: `setArtifactCommentStatus`, `setShowReviewPanel`, `setShowComments`, `setShowSectionLocks`, and `openHistory`.

- [ ] **Step 2: Add review panel buttons**

Within the review panel:

- For open comments:
  - Add `标记已解决：<content>` button calling `resolveCommentFromReview`.
  - For active anchors, add `定位正文：<content>` button calling existing locate helper.
  - For stale anchors, add `处理失效锚点：<content>` button calling `openCommentFromReview`.
- For section locks:
  - Add `管理锁定章节：<heading>` button calling `openSectionLocksFromReview`.
- For latest history version:
  - Add `查看最近版本：<id>` button calling `openHistoryFromReview`.

Keep button text accessible with `aria-label` if visual text must stay compact.

- [ ] **Step 3: Run GREEN**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "artifact review panel"
```

Expected: PASS.

### Task 3: Regression Verification And Todo Record

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: Run focused regressions**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
npm run test -- --run src/__tests__/store.test.ts -t "artifact comment"
```

Expected: PASS.

- [ ] **Step 2: Update todo record**

Append under Todo #7 progress records:

```markdown
- 2026-06-20：完成第五十九块 CGA「Artifact 审阅面板处理闭环」。
  - `更多产物操作 -> 审阅` 不再只是只读摘要；用户可直接标记未解决批注、定位有效锚点、进入失效锚点重绑、打开章节锁定面板或切到历史版本视图。
  - 审阅面板继续复用现有批注、章节锁定、历史版本和审计轨迹状态，不新增后端 API、Lisa/Alex 专属分支或多人实时协同能力。
  - 验证：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "artifact review panel"`；`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`；`npm run test -- --run src/__tests__/store.test.ts -t "artifact comment"`；`npm run lint`；`npm run build`；`npm run test`；`git diff --check`。
  - 剩余：更复杂三方 merge 解析只继续覆盖可证明安全的完整冲突场景；歧义场景保持人工处理。
```

- [ ] **Step 3: Run expanded verification**

Run:

```bash
cd tools/new-agents/frontend
npm run lint
npm run build
npm run test
git diff --check
```

Expected: all pass.

### Task 4: Commit And Push

**Files:**
- All files from this plan.

- [ ] **Step 1: Inspect diff size**

Run:

```bash
git status --short --branch
git diff --stat
```

Expected: only plan/spec, todo, `ArtifactPane.tsx`, and `ArtifactPane.test.tsx` changed.

- [ ] **Step 2: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-06-20-new-agents-artifact-review-action-center-design.md docs/superpowers/plans/2026-06-20-new-agents-artifact-review-action-center.md docs/todos/new-agents-ux-professionalization.md tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 完善 Artifact 审阅处理闭环"
```

Expected: focused commit with no unrelated zip or generated files.

- [ ] **Step 3: Integrate**

Fast-forward merge back to `master` only after validation:

```bash
cd /Users/anhui/Documents/myProgram/AI4SE
git merge --ff-only codex/new-agents-artifact-review-action-center
git push origin master
```

Expected: `master` equals `origin/master`; existing unrelated zip modifications remain uncommitted.
