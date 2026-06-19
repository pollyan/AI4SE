# New Agents Structured Visual Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce the first backend `ai4se-visual` contract for `TEST_DESIGN/CASES` artifacts.

**Architecture:** Add structured visual requirements beside the existing Mermaid contract map, parse fenced `ai4se-visual` blocks independently from heading checks, and inject concise stage-specific prompt text through `build_artifact_contract_prompt`.

**Tech Stack:** Python 3.11, Pydantic, Pytest.

---

### Task 1: Contract Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`

- [x] **Step 1: Write failing prompt and validation tests**

Add tests that expect `build_artifact_contract_prompt("TEST_DESIGN", "CASES")` to mention `ai4se-visual` and `traceability-matrix`, and expect `validate_agent_turn()` to reject a complete CASES artifact that lacks the structured visual block.

- [x] **Step 2: Run tests to verify RED**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -k 'structured_visual or accepts_complete_required_artifact_template' -q`

Expected: fail because no structured visual contract exists yet.

### Task 2: Backend Contract Implementation

**Files:**
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`

- [x] **Step 1: Add structured visual requirement map**

Add `REQUIRED_ARTIFACT_STRUCTURED_VISUALS = {("TEST_DESIGN", "CASES"): ["traceability-matrix"]}` and import it in tests where needed.

- [x] **Step 2: Parse and validate fenced visual blocks**

Add helpers to extract exact-language `ai4se-visual` fenced blocks, parse JSON, and check `type`, non-empty `columns`, and `rows`.

- [x] **Step 3: Include a valid visual block in complete-template test data**

Update `_complete_markdown_for_stage()` so configured structured visual stages include a minimal valid `ai4se-visual` block.

- [x] **Step 4: Inject prompt requirements**

Extend `build_artifact_contract_prompt()` so configured stages instruct the model to include fenced `ai4se-visual` JSON and avoid hand-written HTML.

- [x] **Step 5: Run tests to verify GREEN**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -q`

Expected: all agent contract tests pass.

### Task 3: Todo Record And Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [x] **Step 1: Update progress record**

Append a dated P0 #3 note that `TEST_DESIGN/CASES` now has backend `ai4se-visual` contract and prompt injection, while judge rubric remains open.

- [x] **Step 2: Run focused backend tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -q`

Expected: all contract tests pass.

- [x] **Step 3: Run diff whitespace verification**

Run: `git diff --check`

Expected: no whitespace errors.
