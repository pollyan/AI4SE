# New Agents Alex Upstream Start Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans when delegating. This plan is executed in the main workspace because the touched files share handoff contracts and tests.

**Goal:** Let Alex users start `VALUE_DISCOVERY` from either a new topic or a persisted `IDEA_BRAINSTORM/CONCEPT` product concept brief, while preserving existing Lisa handoff behavior and the shared Agent Runtime architecture.

**Architecture:** Reuse the existing manifest-driven handoff service. Add a target-side candidate query over persisted run/artifact data, extend handoff metadata with source trace fields, keep `/api/agent/runs/{runId}/handoffs/{handoffId}/start` as the single target-run creation path, and add a ChatPane empty-state selector for `VALUE_DISCOVERY`.

**Tech Stack:** Flask, SQLAlchemy, pytest, React, TypeScript, Zustand, Vitest, Testing Library.

## Global Constraints

- Do not add Alex-, Lisa-, workflow-, or stage-specific runtime, transport, store, or rendering pipelines.
- Do not alter Lisa source-side handoff URLs or behavior except for backward-compatible metadata additions.
- Do not create fallback drafts, hidden success, production mocks, or fake run state.
- Do not introduce user/permission concepts; the current system has no user model.
- Do not implement `USER_STORY_BREAKDOWN`, story packet persistence, or AI Coding workflow consumption in this round.
- Preserve existing `WorkflowHandoff` compatibility for source-side handoff responses.
- Limit writes to this feature's spec/plan, New Agents handoff backend/frontend code and tests, workflow manifest, API/TESTING docs, and Alex todo execution record.

---

## File Map

- Modify: `tools/new-agents/workflow_manifest.json`
  Add `IDEA_BRAINSTORM/CONCEPT -> VALUE_DISCOVERY/ELEVATOR` handoff; update `VALUE_DISCOVERY` visible name/listing copy.
- Modify: `tools/new-agents/backend/workflow_handoffs.py`
  Add target-side candidate export, source trace metadata, digest/summary helpers, and prompt trace metadata.
- Modify: `tools/new-agents/backend/routes.py`
  Add `GET /api/agent/workflow-handoff-candidates`.
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`
  Cover Alex internal handoff, target candidate query, prompt trace metadata, and Lisa regression.
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
  Cover target candidate endpoint happy path, empty path, and invalid target stage.
- Modify: `tools/new-agents/frontend/src/core/types.ts`
  Extend `WorkflowHandoff` with optional source trace fields.
- Modify: `tools/new-agents/frontend/src/services/workflowHandoffService.ts`
  Add target candidate fetch and metadata parsing.
- Modify: `tools/new-agents/frontend/src/services/__tests__/workflowHandoffService.test.ts`
  Cover target candidate parsing and malformed metadata failures.
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
  Add `VALUE_DISCOVERY` empty-state startup selector and target candidate application flow.
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`
  Cover selector, no-candidate state, candidate selection, and existing Lisa source-side action.
- Existing coverage: `tools/new-agents/frontend/src/__tests__/store.test.ts`
  Cover Alex internal handoff application with `targetRunId`.
- Modify docs: `docs/api-contracts.md`, `docs/TESTING.md`, `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`.

---

### Task 1: Backend Handoff Manifest and Target Candidate Service

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/backend/workflow_handoffs.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`

**Interfaces:**
- Produces: manifest handoff `idea-brainstorm-concept-to-value-discovery`.
- Produces: `export_target_workflow_handoffs(target_workflow_id, target_stage_id=None)`.
- Extends: `WorkflowHandoff` payload with optional `sourceRunId`, `sourceArtifactDigest`, `sourceArtifactSummary`.

- [x] **Step 1: Write failing tests for Alex internal source-side handoff**

Add tests that create an `IDEA_BRAINSTORM` run with a `CONCEPT` artifact and assert `export_run_handoffs(run.id)` returns one candidate targeting `VALUE_DISCOVERY/ELEVATOR/alex`, with label `从产品概念简报继续梳理需求蓝图`.

- [x] **Step 2: Write failing tests for target-side candidate query**

Add tests for `export_target_workflow_handoffs("VALUE_DISCOVERY", "ELEVATOR")`:

- returns source run id, source workflow/stage, artifact version, digest, summary, target workflow/stage/agent, and prompt;
- excludes runs without `CONCEPT` artifact;
- returns `[]` for workflows with no inbound configured handoff.

- [x] **Step 3: Write failing prompt trace test**

Assert `start_workflow_handoff(source_run.id, "idea-brainstorm-concept-to-value-discovery")` creates a target run whose first message includes source run id, source artifact version, source digest, `IDEA_BRAINSTORM/CONCEPT`, and `VALUE_DISCOVERY/ELEVATOR`.

- [x] **Step 4: Implement manifest and service**

Add manifest handoff and implement:

- target-side manifest filtering;
- persisted source artifact lookup via `AgentRun`, `AgentArtifact`, `AgentArtifactVersion`;
- SHA-256 digest helper;
- summary helper using context summary when available, otherwise bounded content snippet;
- backward-compatible `_build_handoff` with optional source run metadata;
- prompt trace metadata block.

- [x] **Step 5: Run focused backend service tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_handoffs.py -q
```

Expected: all handoff service tests pass, including existing Lisa regression.

---

### Task 2: Backend Target Candidate API

**Files:**
- Modify: `tools/new-agents/backend/routes.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify: `docs/api-contracts.md`

**Interfaces:**
- Produces: `GET /api/agent/workflow-handoff-candidates?targetWorkflowId=...&targetStageId=...`.
- Returns: `{ targetWorkflowId, targetStageId, handoffs }`.

- [x] **Step 1: Write failing API tests**

Add tests using Flask test client:

- happy path returns Alex target candidates for `VALUE_DISCOVERY/ELEVATOR`;
- no persisted source artifact returns empty `handoffs`;
- unknown workflow or mismatched target stage returns JSON 400.

- [x] **Step 2: Implement route**

In `routes.py`, read query parameters, require `targetWorkflowId`, allow optional `targetStageId`, call `export_target_workflow_handoffs`, and map validation `ValueError` to 400 JSON.

- [x] **Step 3: Update API docs**

Document the new endpoint and add optional metadata fields to existing run handoff response.

- [x] **Step 4: Run focused backend API tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_agent_endpoint.py -q
```

---

### Task 3: Frontend Service and Store Contract

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/workflowHandoffService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/workflowHandoffService.test.ts`
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`

**Interfaces:**
- Produces: `fetchTargetWorkflowHandoffCandidates(targetWorkflowId, targetStageId?)`.
- Extends: `WorkflowHandoff` optional source trace fields.

- [x] **Step 1: Write failing service tests**

Add tests proving target candidate fetch calls `/new-agents/api/agent/workflow-handoff-candidates?...`, parses source metadata, and fails explicitly on malformed `sourceRunId` or digest fields.

- [x] **Step 2: Confirm store handoff application coverage**

Existing `applyWorkflowHandoff` coverage already validates generic target workflow/stage/agent state reset. The new ChatPane target-side test asserts the Alex internal handoff path applies a `VALUE_DISCOVERY/ELEVATOR` target run with `targetRunId`, so no separate store-only production change was needed.

- [x] **Step 3: Implement service/types**

Extend parsing and add target candidate fetch. Keep existing source-side functions behavior unchanged.

- [x] **Step 4: Run focused frontend service tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/workflowHandoffService.test.ts
```

---

### Task 4: ChatPane Target Startup Selector

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`

**Interfaces:**
- Consumes: `fetchTargetWorkflowHandoffCandidates`.
- Uses: existing `startWorkflowHandoff(sourceRunId, handoffId)` and `applyWorkflowHandoff`.

- [x] **Step 1: Write failing ChatPane tests**

Add tests:

- empty `VALUE_DISCOVERY/ELEVATOR` loads and displays startup selector with “开启新话题” and candidate “从产品概念简报继续梳理需求蓝图”;
- selecting candidate calls `startWorkflowHandoff(sourceRunId, handoffId)`, applies target run, and navigates to `/workspace/alex/value-discovery?runId=...`;
- no candidates displays “暂无可继承的产品概念简报，可以直接开启新话题” and does not block starter prompts;
- existing source-side Lisa handoff tests still pass.

- [x] **Step 2: Implement UI state and actions**

Add target handoff state, loading/error/no-candidate handling, dismiss/new-topic action, and candidate apply handler. Keep source-side current-run handoff banner intact.

- [x] **Step 3: Run focused ChatPane tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ChatPane.test.tsx
```

---

### Task 5: Naming, Docs, Todo Record, and Verification

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `docs/api-contracts.md`
- Modify: `docs/TESTING.md`
- Modify: `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`
- Modify: this plan checklist after each completed task.

- [x] **Step 1: Validate naming and manifest sync**

Ensure `VALUE_DISCOVERY` visible name/listing/empty-state copy says “需求蓝图梳理” while internal ID/slug remain unchanged.

- [x] **Step 2: Update testing docs**

Record target-side handoff candidate API, frontend startup selector, and Lisa regression testing responsibilities.

- [x] **Step 3: Update Alex todo execution record**

Mark 第 1 轮 completed only after tests pass. Record commands and results.

- [x] **Step 4: Run focused full New Agents checks**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts
```

```bash
cd tools/new-agents/frontend && npm run lint
```

- [x] **Step 5: Run New Agents local automation or document exception**

Default:

```bash
./scripts/test/test-local.sh new-agents
```

If skipped or blocked, document reason and residual risk in todo and final response.

- [x] **Step 6: Final review**

Run:

```bash
git diff --check
```

Confirm no unrelated dirty files were modified by this round and Lisa handoff remains covered.
