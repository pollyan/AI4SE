# Lisa Test Assets Intent Tester Drafts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add intent-tester-compatible import drafts to Lisa test asset exports.

**Architecture:** Extend `test_assets.py` with a deterministic mapper from Lisa `testCases` to intent-tester testcase creation drafts. Keep the endpoint read-only and do not call intent-tester.

**Tech Stack:** Python 3.11, Flask, pytest.

---

## File Structure

- Modify: `tools/new-agents/backend/test_assets.py`
- Modify: `tools/new-agents/backend/tests/test_test_assets.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify docs:
  - `docs/api-contracts.md`
  - `docs/todos/new-agents-evolution.md`

## Task 1: RED Tests

- [ ] Assert service response includes `intentTesterDrafts`.
- [ ] Assert endpoint response includes `intentTesterDrafts`.
- [ ] Run focused tests and confirm failure because field is missing.

## Task 2: GREEN Implementation

- [ ] Add `_build_intent_tester_drafts(test_cases)`.
- [ ] Add priority mapping helper.
- [ ] Include drafts in `export_lisa_test_assets`.
- [ ] Run focused tests.

## Task 3: Verification And Docs

- [ ] Update API contract and todo progress.
- [ ] Run backend full tests.
- [ ] Run `git diff --check`.
