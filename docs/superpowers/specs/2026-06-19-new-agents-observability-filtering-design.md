# New Agents Observability Filtering Design

## Goal

Add workflow and stage filters to Agent Runtime observability so users can inspect failures and latency for a focused workflow/stage instead of only seeing global recent turns.

## Scope

- Backend `GET /api/agent/observability` accepts optional `workflowId` and `stageId`.
- Frontend observability service passes these query parameters.
- Header runtime statistics modal exposes workflow and stage selects and reloads the summary when filters are applied.
- No alerting, auto-refresh, provider deep categorization, real token billing, or real contract retry counting in this slice.

## Behavior

If `workflowId` is provided, the backend limits totals, stage/provider aggregation, and recent turns to that workflow. If `stageId` is also provided, the backend limits data to that stage. A `stageId` without a `workflowId`, an unknown workflow, or a stage that does not belong to the workflow returns a JSON error instead of silently ignoring the filter.

The frontend modal defaults to all workflows/stages. Users can choose a workflow, then an optional stage from that workflow, and click `应用筛选`. The modal reloads via `fetchObservabilitySummary({ limit: 20, workflowId, stageId })`.

## Testing

- Backend endpoint test covers filtered summary and invalid stage/workflow combinations.
- Frontend service test covers URL query serialization.
- Header component test covers selecting workflow/stage and applying the filter.
