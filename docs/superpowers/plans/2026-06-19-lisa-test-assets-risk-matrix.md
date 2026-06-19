# Lisa Test Assets Risk Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a derived risk matrix to Lisa test asset exports.

**Architecture:** Compute `riskMatrix` in `test_assets.py` from parsed `testCases` and `coverageTrace`. Keep the API read-only and avoid new persistence in this slice.

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

- [ ] Assert service response includes `riskMatrix`.
- [ ] Assert endpoint response includes `riskMatrix`.
- [ ] Run focused tests and confirm failure because field is missing.

## Task 2: GREEN Implementation

- [ ] Add `_build_risk_matrix(test_cases, coverage_trace)`.
- [ ] Include `riskMatrix` in `export_lisa_test_assets`.
- [ ] Run focused tests.

## Task 3: Verification And Docs

- [ ] Update API contract and todo progress.
- [ ] Run backend full tests.
- [ ] Run `git diff --check`.
