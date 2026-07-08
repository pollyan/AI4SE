# Alex Single Story Handoff Packet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 用户可以从 Alex 用户故事拆解的 ready story 生成、保存、读取、复制一个单故事需求包。

**Architecture:** 后端从 `USER_STORY_BREAKDOWN/HANDOFF` 当前 artifact version 的 `artifact_data` 生成 packet，并保存为一等持久化记录；前端 ArtifactPane 通过 typed service 查询候选、创建 packet、展示 stale 状态和复制内容。所有能力复用共享 New Agents Flask API、SQLAlchemy、Zustand store 和 ArtifactPane，不新增 Alex 专属 runtime。

**Tech Stack:** Python 3.11、Flask、SQLAlchemy、Pydantic、pytest、TypeScript 5、React 19、Vitest、Testing Library、Playwright mock E2E。

---

## File Structure

- Create: `tools/new-agents/backend/story_handoff_packets.py`，封装候选读取、packet 生成、持久化、stale 计算和 payload 序列化。
- Modify: `tools/new-agents/backend/models.py`，新增 `AgentStoryHandoffPacket`。
- Modify: `tools/new-agents/backend/app.py`，为已有数据库补建 packet 表。
- Modify: `tools/new-agents/backend/routes.py`，新增候选、列表和创建 API。
- Test: `tools/new-agents/backend/tests/test_story_handoff_packets.py`，覆盖 service 和 API 主路径/失败路径。
- Modify: `tools/new-agents/frontend/src/core/types.ts`，新增 story handoff packet 类型，允许 snapshot artifact 带 `artifactData`。
- Create: `tools/new-agents/frontend/src/services/storyHandoffPacketService.ts`。
- Test: `tools/new-agents/frontend/src/services/__tests__/storyHandoffPacketService.test.ts`。
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`，新增单故事需求包操作区。
- Test: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`。
- Modify: `tests/e2e/new_agents_browser/conftest.py` 和 `tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py`，补 mock packet 生成路径。
- Modify: `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`、`docs/api-contracts.md`、`docs/TESTING.md`，记录第 4 轮交付和验证口径。

## Tasks

### Task 1: Backend RED tests for packet service and API

**Files:**
- Create: `tools/new-agents/backend/tests/test_story_handoff_packets.py`

- [x] Add fixtures that create a `USER_STORY_BREAKDOWN` run and record a `HANDOFF` artifact version with `VALID_USER_STORY_HANDOFF_ARTIFACT_DATA`.
- [x] Add `test_story_handoff_candidates_return_ready_stories_from_artifact_data`.
- [x] Add `test_create_story_handoff_packet_persists_requirement_only_payload`.
- [x] Add `test_story_handoff_packets_mark_stale_after_source_artifact_changes`.
- [x] Add failure tests for missing artifact data, unknown story id, and invalid stage.
- [x] Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_story_handoff_packets.py -q
```

Expected: fail because `story_handoff_packets` module and API routes do not exist.

### Task 2: Backend model, migration, service and routes

**Files:**
- Modify: `tools/new-agents/backend/models.py`
- Modify: `tools/new-agents/backend/app.py`
- Create: `tools/new-agents/backend/story_handoff_packets.py`
- Modify: `tools/new-agents/backend/routes.py`

- [x] Add `AgentStoryHandoffPacket` with run relationship, source trace columns, `packet_json`, and `created_at_ms`.
- [x] Add `_ensure_story_handoff_packet_table()` in `app.py` and call it from `init_db`.
- [x] Implement `list_story_handoff_candidates`, `create_story_handoff_packet`, and `list_story_handoff_packets`.
- [x] Reuse `UserStoryHandoffArtifactData.model_validate` for strict artifact_data validation.
- [x] Reject packet generation unless source run workflow is `USER_STORY_BREAKDOWN` and source stage is `HANDOFF`.
- [x] Generate `sourceArtifactDigest` from current Markdown content with SHA-256 so stale detection is stable.
- [x] Ensure packet payload contains only requirement/trace fields and explicitly excludes implementation fields.
- [x] Add three API routes under `/agent/runs/<run_id>/story-handoff-*`.
- [x] Run the RED test again.

Expected: pass.

### Task 3: Frontend service RED tests

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Create: `tools/new-agents/frontend/src/services/__tests__/storyHandoffPacketService.test.ts`

- [x] Add type tests through service behavior for candidate and packet parsing.
- [x] Test invalid response rejection.
- [x] Test POST body sends `{ stageId, storyId }`.
- [x] Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/storyHandoffPacketService.test.ts
```

Expected: fail because the service does not exist.

### Task 4: Frontend service and snapshot artifactData parser

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/runSnapshotService.ts`
- Create: `tools/new-agents/frontend/src/services/storyHandoffPacketService.ts`

- [x] Add `StoryHandoffCandidate`, `StoryHandoffPacket`, and `StoryHandoffPacketListItem` types.
- [x] Add optional `artifactData?: unknown` to `AgentRunSnapshotArtifact` and preserve it in `parseArtifact`.
- [x] Implement `fetchStoryHandoffCandidates`, `fetchStoryHandoffPackets`, and `createStoryHandoffPacket`.
- [x] Run the service test.

Expected: pass.

### Task 5: ArtifactPane RED tests for user action and stale warning

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] Mock `storyHandoffPacketService`.
- [x] Add a test where `workflow=USER_STORY_BREAKDOWN`, `stageIndex=3`, `currentRunId` exists, candidates load, user clicks “生成需求包”, and packet summary appears.
- [x] Add a stale packet test that expects “源需求已更新”.
- [x] Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.test.tsx
```

Expected: fail because ArtifactPane has no packet panel.

### Task 6: ArtifactPane packet panel

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] Import packet service and `Copy` icon.
- [x] Add local state for candidates, packets, loading, error and copy status.
- [x] Fetch candidates/packets only for `USER_STORY_BREAKDOWN/HANDOFF` with a persisted `currentRunId`.
- [x] Render a compact “单故事需求包” panel above artifact body or inside the current side action area without nesting cards.
- [x] Generate packet on candidate button click and refresh packet list.
- [x] Copy formatted packet JSON with `navigator.clipboard.writeText`; show visible success/error state.
- [x] Run ArtifactPane tests.

Expected: pass, with existing React `act(...)` warnings only if already present.

### Task 7: Browser mock E2E packet path

**Files:**
- Modify: `tests/e2e/new_agents_browser/conftest.py`
- Modify: `tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py`

- [x] Add mock handlers for story handoff candidates and packet creation/list.
- [x] Add or extend a browser test proving the user can generate a packet from the HANDOFF stage and see/copy its summary.
- [x] Run:

```bash
.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py -q
```

Expected: pass.

### Task 8: Documentation and todo status

**Files:**
- Modify: `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`
- Modify: `docs/api-contracts.md`
- Modify: `docs/TESTING.md`

- [x] Mark 第 4 轮 as completed with changed files and verification evidence.
- [x] Document the three packet API endpoints and payload shape.
- [x] Add New Agents test coverage note for single story handoff packets.

### Task 9: Verification, commit and push checkpoint

**Files:** no source edits unless verification finds failures.

- [x] Run backend focused tests:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_story_handoff_packets.py tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_run_persistence.py -q
```

- [x] Run frontend focused tests:

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/storyHandoffPacketService.test.ts src/components/__tests__/ArtifactPane.test.tsx src/services/__tests__/runSnapshotService.test.ts
```

- [x] Run New Agents suite:

```bash
./scripts/test/test-local.sh new-agents
```

- [x] Run full local automation before commit:

```bash
./scripts/test/test-local.sh all
```

- [x] If full automation is blocked by sandbox permissions again, rerun with approved escalation if available; otherwise record exact blocker in todo and final response.
- [x] Stage only files touched by this plan.
- [x] Commit with a focused Chinese message.
- [x] Push current branch to GitHub unless remote or verification is blocked.

## Self Review

Spec coverage:
- Persistent packet, API read, no implementation-task leakage, stale detection, frontend display/copy, Lisa non-regression and documentation are covered by Tasks 1-9.

Placeholder scan:
- No unresolved placeholders remain.

Type consistency:
- Backend API and frontend service use the same story/camelCase field names; source trace fields match the todo acceptance list.
