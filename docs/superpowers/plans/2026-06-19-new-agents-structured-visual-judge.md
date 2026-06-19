# New Agents Structured Visual Judge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach the optional E2E LLM judge prompt to evaluate `ai4se-visual` structured visual quality.

**Architecture:** Update only the judge prompt text and its deterministic tests. Keep the existing real-LLM judge environment gate unchanged.

**Tech Stack:** Python 3.11, Pytest.

---

### Task 1: Judge Prompt Test

**Files:**
- Modify: `tests/e2e/new_agents_browser/test_llm_judge.py`

- [x] **Step 1: Write failing test assertions**

Add assertions to the Lisa rubric test that expect `ai4se-visual`, `traceability-matrix`, and `可视化质量` in the prompt.

- [x] **Step 2: Run the judge prompt test to verify RED**

Run: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py::test_build_judge_prompt_uses_lisa_testing_rubric -q`

Expected: fail because the current prompt only contains generic visual criteria.

### Task 2: Judge Prompt Implementation

**Files:**
- Modify: `tests/e2e/new_agents_browser/llm_judge.py`

- [x] **Step 1: Add structured visual rubric bullets**

Extend the `可视化维度` section in `build_judge_prompt()` with explicit `ai4se-visual` and `traceability-matrix` quality criteria and ask for a visual quality score dimension.

- [x] **Step 2: Run judge prompt tests to verify GREEN**

Run: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py -q`

Expected: all judge prompt tests pass.

### Task 3: Todo Record And Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [x] **Step 1: Update P0 #3 progress**

Append a dated note that optional E2E LLM judge prompt now evaluates `ai4se-visual` / `traceability-matrix` quality.

- [x] **Step 2: Run focused verification**

Run: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py -q`

Expected: all judge prompt tests pass.

- [x] **Step 3: Run diff whitespace verification**

Run: `git diff --check`

Expected: no whitespace errors.
