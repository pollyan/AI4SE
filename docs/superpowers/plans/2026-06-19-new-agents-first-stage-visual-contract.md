# New Agents First Stage Visual Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every online workflow first stage has a contract-enforced professional visualization.

**Architecture:** Extend the existing shared artifact contract dictionaries and structured visual parser. Use Mermaid for flow/mindmap/timeline cases and `ai4se-visual` `score-matrix` for stable scoring matrices. Keep rendering in the shared `StructuredVisual` component.

**Tech Stack:** Python contract validation, TypeScript prompt/templates, React structured visual renderer, Pytest, Vitest.

---

### Task 1: Contract Coverage Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`

- [ ] Add a failing backend test that every first stage in `WORKFLOW_STAGES` appears in either `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` or `REQUIRED_ARTIFACT_STRUCTURED_VISUALS`.
- [ ] Add failing expectations for `score-matrix` prompt/template sync.
- [ ] Run `python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py`.

### Task 2: Structured Visual Parser And Renderer

**Files:**
- Modify: `tools/new-agents/frontend/src/core/structuredVisuals.ts`
- Modify: `tools/new-agents/frontend/src/components/StructuredVisual.tsx`
- Modify: `tools/new-agents/frontend/src/core/__tests__/structuredVisuals.test.ts`
- Modify: `tools/new-agents/frontend/src/components/__tests__/StructuredVisual.test.tsx`

- [ ] Add failing tests for `score-matrix`.
- [ ] Reuse the existing `columns` / `rows` JSON shape for `score-matrix`.
- [ ] Render `score-matrix` through the same shared table component with a type label.
- [ ] Run `npm run test -- --run src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx`.

### Task 3: Contract And Prompt Implementation

**Files:**
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/frontend/src/core/prompts/test_design/clarify.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/req_review/review.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/idea_brainstorm/define.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/value_discovery/elevator.ts`

- [ ] Add required Mermaid contract for `TEST_DESIGN/CLARIFY` and `IDEA_BRAINSTORM/DEFINE`.
- [ ] Add required structured visual contract for `REQ_REVIEW/REVIEW` and `VALUE_DISCOVERY/ELEVATOR`.
- [ ] Add `score-matrix` schema prompt.
- [ ] Update frontend templates with valid Mermaid / `ai4se-visual` examples.
- [ ] Run backend and frontend focused tests.

### Task 4: Todo Record And Verification

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] Record P0 #3 progress and remaining follow-up for non-first-stage visual audit.
- [ ] Run `npm run build`, focused Pytest/Vitest, and `git diff --check`.
