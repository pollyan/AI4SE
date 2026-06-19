# Lisa Test Assets Source Version Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add source artifact version metadata to Lisa test assets export responses.

**Architecture:** Reuse the existing `versionNumber` in run snapshot artifacts and expose it as `sourceArtifactVersion` in `test_assets.py` and the endpoint response.

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

- [ ] Add assertions for `sourceArtifactVersion` in service and endpoint tests.
- [ ] Add service test where CASES artifact is recorded twice and export returns version `2`.
- [ ] Run `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py::test_agent_run_test_assets_endpoint_exports_cases_artifact -q`.
- [ ] Expected: FAIL because `sourceArtifactVersion` is missing.

## Task 2: GREEN Implementation

- [ ] In `export_lisa_test_assets`, include `"sourceArtifactVersion": cases_artifact["versionNumber"]`.
- [ ] Run focused tests and backend full tests.

## Task 3: Docs

- [ ] Update API contract and todo progress.
- [ ] Run `git diff --check`.
