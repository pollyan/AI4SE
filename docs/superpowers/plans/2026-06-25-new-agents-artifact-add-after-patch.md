# New Agents Artifact add_after Patch Implementation Plan

> **For agentic workers:** Use executing-plans. Track each checkbox as the slice progresses.

**Goal:** Extend the shared artifact patch path so backend partial artifact_data streams can emit a useful append-section patch and the frontend can apply it safely.

## Task 1: Frontend Patch Application

Files:
- `tools/new-agents/frontend/src/core/types.ts`
- `tools/new-agents/frontend/src/core/artifactSections.ts`
- `tools/new-agents/frontend/src/core/__tests__/artifactSections.test.ts`
- `tools/new-agents/frontend/src/core/llm.ts`
- `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`

- [x] Add failing tests for applying `add_after` after an existing section and rejecting missing `afterSectionAnchor`.
- [x] Update patch types and `applyArtifactSectionPatch(...)`.
- [x] Update typed SSE patch validation to accept `add_after`.
- [x] Run focused frontend tests.

## Task 2: Backend Patch Contract

Files:
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/backend/sse_schemas.py`
- `tools/new-agents/backend/stage_readiness.py`
- `tools/new-agents/backend/tests/test_sse_encoder.py`
- `tools/new-agents/backend/tests/test_stream_services.py`

- [x] Add failing tests for backend `artifact_patch` schema, alias serialization, and stream preservation.
- [x] Add `ArtifactPatch` Pydantic model and optional patch fields to turn/delta output.
- [x] Preserve patch through stage readiness and stream delta conversion.
- [x] Run focused backend schema/stream tests.

## Task 3: Backend Partial Renderer Patch Generation

Files:
- `tools/new-agents/backend/artifact_data_renderers.py`
- `tools/new-agents/backend/agent_runtime.py`
- `tools/new-agents/backend/tests/test_agent_runtime.py`

- [x] Add failing raw JSON stream test asserting CLARIFY second partial frame carries `add_after`.
- [x] Generate `add_after` only when current partial markdown equals previous partial markdown plus exactly one new markdown section.
- [x] Keep full markdown fallback unchanged for unsupported or multi-section additions.
- [x] Run focused backend runtime tests.

## Task 4: Verification and Todo Update

Files:
- `docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md`

- [x] Run frontend focused tests and lint.
- [x] Run backend focused tests.
- [x] Update the active todo with scope, remaining work, and verification evidence.
- [x] Diff check, stage only this slice, commit.
