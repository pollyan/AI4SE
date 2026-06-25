# New Agents 可视化诊断左侧重复提示收束 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 当右侧 ArtifactPane 已经记录并展示可视化诊断入口时，左侧 ChatPane 不再渲染重复的大块提示卡。

**Architecture:** 继续复用共享 `artifactVisualDiagnostics` store 和 ArtifactPane 诊断锚点。ChatPane 不再订阅或渲染 artifact visual diagnostic；右侧 ArtifactPane 仍负责诊断详情、定位和高亮。

**Tech Stack:** React 19, TypeScript 5.x, Zustand, Vitest, Testing Library.

---

### Task 1: Red Tests

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`

- [x] **Step 1: Replace current-stage notice expectation**

Change the existing current-stage diagnostic test to expect no left-side visual diagnostic card:

```ts
expect(screen.queryByText('右侧产物有可视化需要处理')).toBeNull();
expect(screen.queryByRole('button', { name: '查看诊断详情' })).toBeNull();
expect(screen.queryByRole('button', { name: '查看问题位置' })).toBeNull();
expect(screen.getByText('右侧产物已更新。')).toBeDefined();
```

- [x] **Step 2: Remove tests that depend on the deleted card**

Delete or rewrite tests whose only purpose is proving the left-side card ordering or focus button behavior. Keep the existing test that diagnostics from another stage are not shown, but make its expectation generic: no visual diagnostic card appears in ChatPane.

- [x] **Step 3: Run the focused ChatPane test**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ChatPane.test.tsx
```

Expected: FAIL because ChatPane still renders the current-stage card.

Result: FAIL as expected before implementation, because `右侧产物有可视化需要处理` was still rendered.

### Task 2: Remove ChatPane Duplicate UI

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`

- [x] **Step 1: Remove unused diagnostic subscriptions**

Remove `artifactVisualDiagnostics` and `focusArtifactVisualDiagnostic` selectors from ChatPane.

- [x] **Step 2: Remove local state and derived current diagnostic**

Remove `currentArtifactVisualDiagnostic` and `isVisualDiagnosticExpanded`.

- [x] **Step 3: Remove the bottom visual diagnostic card**

Delete the JSX block that renders `右侧产物有可视化需要处理`, `查看诊断详情`, and `查看问题位置`.

- [x] **Step 4: Clean unused imports**

Remove icons that become unused only because of this card, while preserving icons used by other ChatPane UI.

### Task 3: Verify Right-Side Diagnostic Path

**Files:**
- Existing: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: Run focused ArtifactPane diagnostic tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.test.tsx -t "diagnostic"
```

Expected: PASS. This proves right-side visual diagnostic recording and focus anchors remain intact.

Result: PASS, 5 tests.

- [x] **Step 2: Run ChatPane focused tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ChatPane.test.tsx
```

Expected: PASS.

Result: PASS, 33 tests.

- [x] **Step 3: Run New Agents frontend type check**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
```

Expected: PASS.

Result: PASS.

### Task 4: Todo Record and Commit

**Files:**
- Move/update: `docs/todos/2026-06-25-new-agents-artifact-visual-diagnostic-duplicate-notice.md`
- Create/update: `docs/todos/archive/2026-06-25-new-agents-artifact-visual-diagnostic-duplicate-notice.md`
- Create: this spec and plan.

- [x] **Step 1: Archive the completed todo**

Move the todo to `docs/todos/archive/2026-06-25-new-agents-artifact-visual-diagnostic-duplicate-notice.md`, change status to `已完成`, and add a verification note with the commands run.

Result: Archived with status `已完成` and verification notes.

- [x] **Step 2: Run diff and doc checks**

Run:

```bash
git diff --check
python3 - <<'PY'
from pathlib import Path

tokens = ["TO" + "DO", "TB" + "D", "待" + "补充", "PLACE" + "HOLDER", "未" + "定"]
paths = [
    Path("docs/superpowers/specs/2026-06-25-new-agents-visual-diagnostic-chat-dedup-design.md"),
    Path("docs/superpowers/plans/2026-06-25-new-agents-visual-diagnostic-chat-dedup.md"),
    Path("docs/todos/archive/2026-06-25-new-agents-artifact-visual-diagnostic-duplicate-notice.md"),
]
for path in paths:
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        if token in text:
            raise SystemExit(f"{path}: contains placeholder token {token}")
PY
```

Expected: PASS.

Result: Document placeholder check passed. Repository-wide `git diff --check` is currently blocked by pre-existing unrelated `tools/intent-tester/test-results/proxy/junit.xml` trailing whitespace from the dirty intent-tester generated file; targeted diff check for this story's files passed.

- [ ] **Step 3: Stage only this story**

Stage:

```bash
git add \
  tools/new-agents/frontend/src/components/ChatPane.tsx \
  tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx \
  docs/superpowers/specs/2026-06-25-new-agents-visual-diagnostic-chat-dedup-design.md \
  docs/superpowers/plans/2026-06-25-new-agents-visual-diagnostic-chat-dedup.md \
  docs/todos/archive/2026-06-25-new-agents-artifact-visual-diagnostic-duplicate-notice.md
```

Do not stage unrelated intent-tester generated files or remaining active todo files.

- [ ] **Step 4: Commit**

Run:

```bash
git commit -m "fix: 去除左侧重复可视化诊断提示"
```
