# New Agents Pre-runtime Config Observability Design

## Current State Gap Analysis

### Fact Sources

- `docs/todos/new-agents-ux-professionalization.md`
- `docs/strategy/goal-mode-playbook.md`
- `tools/new-agents/backend/routes.py`
- `tools/new-agents/backend/route_guards.py`
- `tools/new-agents/backend/api_responses.py`
- `tools/new-agents/backend/run_persistence.py`
- `tools/new-agents/backend/models.py`
- `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Explorer result for default LLM config missing and observability paths.

### Capability Packages

| Package | Raw gaps | User / engineering chain | Why this is not thinner | Evidence |
| --- | --- | --- | --- | --- |
| Pre-runtime config issue observability | Default LLM missing returns before runtime turn metric and is invisible in runtime statistics. | User starts generation -> default LLM guard fails -> system records config issue -> runtime observability shows failed attempt and stage-level model/config diagnosis. | Only adding an error code or frontend badge would not persist the failure; only adding a DB row without summary merge would not be visible to users. | Backend endpoint test for 503 plus observability summary. |
| Full model governance center | Key rotation, provider health, configuration history, environment-specific defaults. | Admin opens settings -> manages providers -> checks health -> audits usage. | This is larger than the current UX todo and risks adding a separate management surface the user deprioritized. | Future dedicated spec. |

### Candidate Gaps

| Candidate | Source | Target | Current | Gap | Value | Risk | Testability | Destination |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pre-runtime config issue observability | P1 model/provider governance todo | Default LLM missing appears in runtime stats without fake run/provider data. | 503 response only; observability remains empty. | No persisted pre-runtime issue. | Users can connect "generation failed" with "model config missing" from the statistics view. | Medium: touches persistence and summary aggregation. | Flask endpoint test. | This slice |
| Full model governance center | P1/P2 governance ideas | Rich provider settings and audit. | Settings modal and connection check exist. | Missing dedicated provider management UX. | Better admin workflows. | High and currently lower priority. | Broad UI/API tests. | Later |
| Frontend recent issue timeline | Runtime observability UX | Recent pre-runtime config issues shown in a dedicated list. | `recentTurns` is turn-only. | No issue timeline field. | More detailed debugging. | Requires frontend contract changes. | Service/Header tests. | Later if needed |

### Selected Milestone

As a New Agents user, when generation fails before the model runtime because the default LLM is not configured, I can still see that failed attempt reflected in runtime statistics at the workflow stage level, so model configuration problems are diagnosable from the same observability surface as provider failures.

### Slice Gate

- Entry: `/api/agent/runs/stream`.
- Action: User sends a valid workflow/stage prompt while default LLM config is missing.
- Processing: Shared guard returns 503 and records a pre-runtime config issue.
- Visible result: `/api/agent/observability` totals and stage summaries include the config issue.
- State continuity: Issue is persisted independently of `AgentRunTurnMetric`, without fake `AgentRun`.
- Failure feedback: Original 503 response shape remains unchanged.
- Evidence: Endpoint test verifies response, persisted summary, empty provider group, and empty recent turns.

## Scope

- Add a dedicated persisted pre-runtime config issue model.
- Add a small persistence API to record default LLM config missing for valid agent runtime requests.
- Merge these issues into observability totals and stage summaries.
- Keep provider grouping and recent turns limited to real runtime turn metrics.
- Update the UX todo progress record.

Out of scope:

- New settings center or provider management page.
- Workflow-specific model config branches.
- Fake run creation for failed pre-runtime attempts.
- Frontend contract changes for a separate recent issue timeline.

## Acceptance Criteria

1. A valid `/api/agent/runs/stream` request with missing default LLM config still returns the existing 503 JSON error.
2. The same request records one pre-runtime config issue with workflow, stage, route, request id, and issue code.
3. `/api/agent/observability` includes that issue in `totals.turns`, `totals.failedTurns`, `totals.providerIssueCount`, and `totals.providerIssueCodes`.
4. The matching `byStage` item includes the same issue in turns, failed turns, raw `errorCodes`, and provider issue fields.
5. `byProvider` remains empty for config-only failures because no real provider was called.
6. `recentTurns` remains empty for config-only failures because no runtime turn was created.
7. Existing runtime turn observability behavior and frontend parsing remain compatible.

## Verification Plan

- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_runs_stream_records_default_llm_missing_observability_issue`
- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_filters_by_workflow_and_stage tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_groups_provider_issue_codes`
- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py`
- `git diff --check`
