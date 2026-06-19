# New Agents Artifact Section Anchor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Artifact section locks target a concrete repeated heading instance through a persisted `sectionAnchor`.

**Architecture:** Add optional `sectionAnchor` to the shared artifact section lock contract. ArtifactPane generates anchors from heading level, heading title and same-title occurrence; store/service/backend preserve the field; save validation prefers anchor matching and falls back to legacy heading matching for old locks.

**Tech Stack:** React, Zustand, TypeScript, Vitest, Flask, SQLAlchemy, Pytest.

---

### Task 1: Frontend RED For Duplicate Section Locks

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts`

- [ ] **Step 1: Add ArtifactPane duplicate heading test**

Add a test named `locks the second duplicate artifact section without locking the first duplicate heading`.

Scenario:
- Artifact has two `## 验收口径` sections with different body text.
- Open `章节锁定`.
- Click the second section's lock button by accessible name, e.g. `锁定 验收口径 #2`.
- Assert only one lock exists with `sectionAnchor`.
- Edit only the first duplicate section and save.
- Assert the save succeeds and artifact content changes.
- Edit the locked second duplicate section and assert save is blocked.

- [ ] **Step 2: Add store/service RED**

Add tests proving:
- `addArtifactSectionLock` preserves `sectionAnchor` and does not remove a different lock with the same heading but different anchor.
- `parseArtifactSectionLock` reads optional `sectionAnchor` from run snapshot payload.

- [ ] **Step 3: Verify frontend RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts src/services/__tests__/runSnapshotService.test.ts
```

Expected: FAIL because `ArtifactSectionLock` has no `sectionAnchor`, UI labels do not disambiguate duplicate headings, and store dedupes by heading.

### Task 2: Backend RED For Section Anchor Persistence

**Files:**
- Modify: `tools/new-agents/backend/tests/test_run_persistence.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify: `tools/new-agents/backend/tests/test_api.py`

- [ ] **Step 1: Add persistence/API tests**

Update existing collaboration tests to include `"sectionAnchor": "h2:验收口径:2"` in `sectionLocks`, and assert it appears in both direct service response and run snapshot response.

- [ ] **Step 2: Add migration test**

Extend the SQLite upgrade test for pre-existing `agent_artifact_section_locks` table and assert `section_anchor` is added by `init_db`.

- [ ] **Step 3: Verify backend RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_api.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py
```

Expected: FAIL because the model/table snapshot does not include `section_anchor`.

### Task 3: Implement Contract And UI

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/store.ts`
- Modify: `tools/new-agents/frontend/src/services/runSnapshotService.ts`
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Add optional type field**

Add `sectionAnchor: string | null` to `ArtifactSectionLock`, and allow it on `ArtifactSectionLockInput`.

- [ ] **Step 2: Preserve anchors in store/service**

Store sanitization should keep non-empty `sectionAnchor`; dedupe section locks by `stageId + sectionAnchor` when anchor exists, otherwise by legacy `stageId + heading`.

- [ ] **Step 3: Generate anchors in ArtifactPane**

Extend `ArtifactSection` with `anchor` and duplicate display metadata. Generate anchor from heading level/title occurrence, for example `h2:验收口径:2`. Display duplicate labels as `验收口径 #2` when a title repeats.

- [ ] **Step 4: Validate locks by anchor**

Manual save lock validation should first find `nextSection` by `lock.sectionAnchor`; if absent, fall back to `heading`. `getSectionLock` and UI locked state should follow the same rule.

- [ ] **Step 5: Verify frontend GREEN**

Run the frontend test command from Task 1 and confirm all selected tests pass.

### Task 4: Implement Backend Persistence

**Files:**
- Modify: `tools/new-agents/backend/models.py`
- Modify: `tools/new-agents/backend/app.py`
- Modify: `tools/new-agents/backend/run_persistence.py`

- [ ] **Step 1: Add model column and migration**

Add nullable `section_anchor` to `AgentArtifactSectionLock`. Extend `init_db` to add the column to existing `agent_artifact_section_locks` tables.

- [ ] **Step 2: Preserve field in snapshots**

`replace_artifact_collaboration_state` should read optional `sectionAnchor`, save it to `section_anchor`, and `_section_lock_snapshot` should emit `sectionAnchor`.

- [ ] **Step 3: Verify backend GREEN**

Run the backend test command from Task 2 and confirm all selected tests pass.

### Task 5: Todo, Quality Gates And Commit

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`
- Add: `docs/superpowers/specs/2026-06-20-new-agents-artifact-section-anchor-design.md`
- Add: `docs/superpowers/plans/2026-06-20-new-agents-artifact-section-anchor.md`

- [ ] **Step 1: Update todo progress**

Append a progress entry under Artifact 协作体验深化:
- slice name: `Artifact 重复标题章节锚点`
- result: duplicate headings can be locked independently and restored through snapshot.
- verification commands.
- remaining: movement semantic auto-merge and more complex three-way merge.

- [ ] **Step 2: Run final gates**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

- [ ] **Step 3: Commit**

Stage only this slice's files and commit:

```bash
git commit -m "feat(new-agents): 支持产物章节锁精确锚点"
```
