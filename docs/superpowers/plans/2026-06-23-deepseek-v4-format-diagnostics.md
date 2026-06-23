# DeepSeek V4 Format Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared Agent Runtime diagnostic loop for DeepSeek V4 formatted-output failures.

**Architecture:** Extend `tools/new-agents/backend/agent_runtime.py` with a lightweight diagnostic exception and retry prompt context. Keep raw JSON streaming, `artifact_data` renderers, typed SSE, run persistence, and workflow manifest unchanged.

**Tech Stack:** Python 3.11, Pydantic, pytest.

---

## File Structure

- Modify: `tools/new-agents/backend/agent_runtime.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Modify: `docs/todos/refactor/README.md`

## Task 1: RED - Diagnostic Classification Tests

- [x] Add `test_raw_json_streaming_final_failure_classifies_json_decode_error`.
- [x] Add `test_raw_json_streaming_final_failure_classifies_artifact_data_schema_error`.
- [x] Add `test_raw_json_streaming_final_failure_classifies_missing_artifact_data_renderer`.
- [x] Add `test_raw_json_streaming_final_failure_classifies_artifact_contract_error`.
- [x] Add `test_artifact_data_retry_prompt_includes_diagnostic_context`.
- [x] Run focused tests and confirm failures are caused by missing diagnostic classification.

## Task 2: GREEN - Shared Diagnostic Runtime

- [x] Add `FormattedOutputDiagnosticError` with `kind`, `workflow_id`, `stage_id`, `message`, and `path`.
- [x] Add helpers to build diagnostic errors from `JSONDecodeError`, `ValidationError`, renderer `ValueError`, and `ContractValidationError`.
- [x] Update raw JSON streaming final parse / validation loops to preserve retry behavior and raise diagnostic error after final attempt.
- [x] Update `build_raw_json_retry_prompt()` to include diagnostic kind/context while keeping artifact_data instructions.
- [x] Run focused runtime tests until green.

## Task 3: Docs And Verification

- [x] Update DeepSeek todo with the formatted-output diagnostic milestone.
- [x] Update refactor README next-candidate wording if needed.
- [x] Run DeepSeek readiness tests.
- [x] Run focused agent runtime tests.
- [x] Run `py_compile` for `agent_runtime.py`.
- [x] Run `git diff --check`.
- [x] Commit the verified milestone.

## Expected Commit Boundary

One commit: `fix(new-agents): 增强 DeepSeek 格式化输出失败诊断`
