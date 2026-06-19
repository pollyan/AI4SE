# New Agents E2E 可视化质量证据硬化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make New Agents E2E evidence prove professional visual quality, not just artifact headings.

**Architecture:** Add deterministic visual marker assertions to browser workflow scenarios, and make optional LLM judge parsing enforce a visualization-quality dimension and threshold. Keep LLM judge optional and do not change backend contracts.

**Tech Stack:** Python 3.12, pytest, Playwright sync API, existing New Agents E2E mock runtime.

---

## File Structure

- Modify: `tests/e2e/new_agents_browser/llm_judge.py`
  - Add visualization dimension detection and threshold assertion.
- Modify: `tests/e2e/new_agents_browser/test_llm_judge.py`
  - Add RED tests for missing visualization dimension and low visualization score.
- Modify: `tests/e2e/new_agents_browser/workflow_runner.py`
  - Add `visual_markers` to `StageExpectation` and assert them against artifact pane.
- Modify: `tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py`
  - Add Lisa stage visual markers.
- Modify: `tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py`
  - Add Alex stage visual markers.
- Modify: `tests/e2e/new_agents_browser/sse_mock.py`
  - Add deterministic Mermaid / `ai4se-visual` blocks for Lisa/Alex E2E artifacts.
  - Add Alex->Lisa handoff-specific Lisa artifacts so optional LLM judge can evaluate professional continuity.
- Modify: `docs/todos/new-agents-ux-professionalization.md`
  - Record progress and remaining gaps.

## Task 1: Judge Parser RED/GREEN

- [x] Add failing tests in `test_llm_judge.py`:
  - `test_parse_judge_result_rejects_missing_visualization_dimension`
  - `test_assert_visualization_quality_dimension_rejects_low_score`
  - handoff prompt must include `可视化质量`
- [x] Run `.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_llm_judge.py` and confirm failure.
- [x] Implement visualization dimension lookup in `llm_judge.py`.
- [x] Re-run the same command and confirm pass.

## Task 2: E2E Visual Marker RED/GREEN

- [x] Add `visual_markers: tuple[str, ...] = ()` to `StageExpectation`.
- [x] Make `run_complete_workflow` assert these markers after existing heading checks.
- [x] Add Lisa/Alex stage markers for Mermaid and `ai4se-visual` keywords.
- [x] Run `.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py` and confirm failure before mock artifacts include markers.
- [x] Update `sse_mock.py` so the mocked artifacts emit the expected Mermaid / `ai4se-visual` blocks.
- [x] Update Alex->Lisa handoff mock artifacts to inherit Alex's AI 测试设计助手蓝图 instead of reusing the generic 登录支付 sample.
- [x] Re-run the same command and confirm pass.

## Task 3: Documentation And Verification

- [x] Update `docs/todos/new-agents-ux-professionalization.md`.
- [x] Run `git diff --check`.
- [x] Run focused pytest commands above.
- [ ] Stage only this milestone files, commit, and push.

## Self-Review

- Spec coverage: judge parser, artifact quality assertion, browser marker evidence and todo recording are covered.
- Placeholder scan: no placeholders.
- Type consistency: `visual_markers` mirrors existing `artifact_headings` tuple pattern.
