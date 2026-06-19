# New Agents Observability Auto Refresh Design

## Context

`docs/todos/new-agents-evolution.md` #12 already has runtime metric collection, a read-only observability endpoint, a Header runtime statistics modal, workflow/stage filters, and provider aggregation. The remaining gap in this slice is that users must close/reopen or manually reapply filters to see new runtime turns while watching an active session.

## Goal

Add a focused auto-refresh control to the existing Header runtime statistics modal so users can keep the current observability view live without changing backend contracts.

## Scope

- Add an auto-refresh toggle inside the existing runtime statistics modal.
- When enabled, refresh every 30 seconds.
- Reuse the current workflow/stage filter state on each automatic refresh.
- Stop refreshing when the toggle is disabled or the modal is closed.
- Keep the existing `GET /api/agent/observability` service and response schema unchanged.

## Non-Goals

- No alert rules or notifications.
- No backend polling endpoint changes.
- No live SSE observability stream.
- No token or retry collection changes.

## Design

`Header.tsx` keeps a local `isObservabilityAutoRefreshEnabled` boolean. A `useEffect` watches the modal open state, auto-refresh state, and current filter values. When the modal is open and auto-refresh is enabled, it creates one interval that calls the existing `loadObservabilitySummary` with the active workflow/stage filters. The effect cleanup clears the interval when filters change, the modal closes, or the component unmounts.

The UI adds a compact checkbox label near the existing filter form. The wording is state-oriented rather than instructional: `自动刷新`. The existing loading and error states are reused.

## Testing

Add a Header component test using fake timers:

- Open the runtime statistics modal.
- Select `TEST_DESIGN` / `CLARIFY`.
- Enable `自动刷新`.
- Advance timers by 30 seconds.
- Assert `fetchObservabilitySummary` was called with `{ limit: 20, workflowId: 'TEST_DESIGN', stageId: 'CLARIFY' }`.
- Close the modal, advance timers again, and assert no additional request is made.

## Acceptance

- Auto-refresh keeps the selected workflow/stage filter.
- Closing the modal clears the interval.
- Existing manual open, filtering, and error behavior remains covered by current tests.
