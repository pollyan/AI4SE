# Partial Streaming Contract Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the New Agents partial artifact streaming route by updating stable API/testing documentation and archiving evidence for all 17 online stages.

**Architecture:** No runtime code changes. Document the existing shared typed SSE contract, partial renderer behavior, `artifact_patch` metadata, testing matrix, and judge quality gate.

**Tech Stack:** Markdown documentation, existing pytest/Vitest evidence, target-mode documentation checks.

---

## Scope

Modify:

- `docs/api-contracts.md`
- `docs/TESTING.md`
- `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`

Create:

- `docs/superpowers/specs/2026-07-07-new-agents-partial-streaming-contract-evidence-design.md`
- `docs/superpowers/plans/2026-07-07-new-agents-partial-streaming-contract-evidence.md`

Do not modify runtime code, frontend code, workflow manifest, generated bundles, or unrelated dirty files.

## Task 1: Update API Contract

**Files:**

- Modify: `docs/api-contracts.md`

- [ ] **Step 1: Add `agent_delta` SSE example**

In the `/api/agent/runs/stream` SSE section, show `run_started`, at least one `agent_delta`, final `agent_turn`, and `[DONE]`.

- [ ] **Step 2: Document partial artifact contract**

Add bullets for:

- `agent_delta.output.chat` carries incremental left-side text.
- `agent_delta.output.artifact_update.type="replace"` carries a formal partial or final Markdown artifact.
- `agent_delta.output.artifact_patch.operation="add_after"` is optional metadata for locating one newly appended section.
- `artifact_patch` requires `artifact_update.type="replace"`.
- Missing patch does not mean streaming failed when a field adds multiple headings or depends on multiple top-level fields.

## Task 2: Update Testing Strategy

**Files:**

- Modify: `docs/TESTING.md`

- [ ] **Step 1: Add partial streaming matrix**

Add a subsection under New Agents runtime or audit checklist with rows for all 17 online stages:

- `TEST_DESIGN/CLARIFY`
- `TEST_DESIGN/STRATEGY`
- `TEST_DESIGN/CASES`
- `TEST_DESIGN/DELIVERY`
- `REQ_REVIEW/REVIEW`
- `REQ_REVIEW/REPORT`
- `INCIDENT_REVIEW/TIMELINE`
- `INCIDENT_REVIEW/ROOT_CAUSE`
- `INCIDENT_REVIEW/IMPROVEMENT`
- `IDEA_BRAINSTORM/DEFINE`
- `IDEA_BRAINSTORM/DIVERGE`
- `IDEA_BRAINSTORM/CONVERGE`
- `IDEA_BRAINSTORM/CONCEPT`
- `VALUE_DISCOVERY/ELEVATOR`
- `VALUE_DISCOVERY/PERSONA`
- `VALUE_DISCOVERY/JOURNEY`
- `VALUE_DISCOVERY/BLUEPRINT`

- [ ] **Step 2: Add verification commands**

Document the 17-stage runtime test command, focused backend suite, and frontend shared stream regression.

- [ ] **Step 3: Add LLM judge threshold**

Document that optional LLM judge pass line is 80, and scores below 80 require gap analysis and repair before continuing.

## Task 3: Update Todo Final Record

**Files:**

- Modify: `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`

- [ ] **Step 1: Add第 7 轮记录**

Record API contract update, testing matrix update, subagent review, documentation checks, LLM judge state, and remaining risk.

- [ ] **Step 2: Mark route completed**

Set route status to implementation and documentation收口完成, while noting real model smoke still depends on local model config, network, and quota.

## Task 4: Verify Documentation

**Files:**

- Verify documentation and touched files.

- [ ] **Step 1: Run diff check**

Run:

```bash
git diff --check -- docs/api-contracts.md docs/TESTING.md docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md docs/superpowers/specs/2026-07-07-new-agents-partial-streaming-contract-evidence-design.md docs/superpowers/plans/2026-07-07-new-agents-partial-streaming-contract-evidence.md
```

Expected: no output.

- [ ] **Step 2: Run placeholder scan**

Run:

```bash
rg -n "T[B]D|implement[ ]later|<填[入]|待[补]" docs/api-contracts.md docs/TESTING.md docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md docs/superpowers/specs/2026-07-07-new-agents-partial-streaming-contract-evidence-design.md docs/superpowers/plans/2026-07-07-new-agents-partial-streaming-contract-evidence.md
```

Expected: no output.

## Code Test Decision

This round is documentation-only. The code evidence it archives is the already-run第 6 轮 verification: 17 partial runtime tests passed, backend focused suite 300 passed, frontend shared stream regression 140 passed, and full local automation passed with LLM judge disabled.
