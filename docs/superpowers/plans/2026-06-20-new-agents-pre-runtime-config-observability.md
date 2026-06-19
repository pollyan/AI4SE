# New Agents Pre-runtime Config Observability Plan

## Goal

Make default LLM configuration failures visible in runtime observability without creating fake agent runs or fake provider failures.

## Steps

1. Add a failing endpoint test for missing default LLM config being reflected in `/api/agent/observability`.
2. Add a dedicated pre-runtime config issue persistence model and recording helper.
3. Record default LLM missing issues from the shared `/api/agent/runs/stream` guard path after request validation.
4. Merge pre-runtime config issues into observability totals and stage summaries while leaving provider groups and recent turns as real turn-metric views.
5. Update the UX professionalization todo progress.
6. Run focused backend tests, expanded backend endpoint tests, and `git diff --check`.
7. Commit and push this slice.

## Verification

- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_runs_stream_records_default_llm_missing_observability_issue`
- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_filters_by_workflow_and_stage tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_groups_provider_issue_codes`
- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py`
- `git diff --check`
