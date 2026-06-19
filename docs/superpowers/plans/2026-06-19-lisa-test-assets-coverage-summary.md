# Lisa Test Assets Coverage Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic coverage summary metrics to Lisa test assets exports.

**Architecture:** Reuse parsed `testCases` and `coverageTrace` in `test_assets.py`; compute summary metrics before returning the export payload. No persistence or frontend changes.

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

- [ ] Add service assertions for `coverageSummary`.
- [ ] Add endpoint assertion for `coverageSummary`.
- [ ] Run `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py::test_agent_run_test_assets_endpoint_exports_cases_artifact -q`.
- [ ] Expected: FAIL because `coverageSummary` is missing.

## Task 2: GREEN Implementation

- [ ] Add `_build_coverage_summary(test_cases, coverage_trace)`.
- [ ] Include summary in `export_lisa_test_assets`.
- [ ] Run focused tests.

## Task 3: Verification And Docs

- [ ] Update API contract and todo progress.
- [ ] Run backend full tests.
- [ ] Run `git diff --check`.
