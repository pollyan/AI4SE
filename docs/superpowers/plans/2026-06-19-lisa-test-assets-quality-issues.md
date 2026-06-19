# Lisa Test Assets Quality Issues Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface non-fatal quality issues in Lisa test asset exports.

**Architecture:** Add `_build_asset_issues(test_cases, coverage_trace)` in `test_assets.py`; include `assetIssues` in the export response. Keep parsing failures as `ValueError`.

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

- [ ] Assert clean exports return `assetIssues: []`.
- [ ] Add a service test for unknown coverage case and orphan test case.
- [ ] Assert endpoint response includes `assetIssues`.
- [ ] Run focused tests and confirm failure because field is missing.

## Task 2: GREEN Implementation

- [ ] Implement issue builder.
- [ ] Include issues in export payload.
- [ ] Run focused tests.

## Task 3: Verification And Docs

- [ ] Update API contract and todo.
- [ ] Run backend full tests.
- [ ] Run `git diff --check`.
