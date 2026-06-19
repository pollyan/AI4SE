# New Agents Observability Alerts Design

## Context

`docs/todos/new-agents-evolution.md` #12 still lists alerting as a missing observability capability. The current Header runtime statistics modal already shows totals, workflow/stage filtering, provider aggregation, recent turns, and auto-refresh. Users can inspect raw numbers, but there is no focused callout when the current window contains failures or a low-success-rate hotspot.

## Goal

Add lightweight derived alerts to the existing runtime statistics modal using only the current `ObservabilitySummary` payload.

## Scope

- Derive alerts on the frontend from `totals`, `byStage`, and `byProvider`.
- Show an alert section in the existing Header runtime statistics modal when alerts exist.
- Keep the existing observability API unchanged.
- Keep thresholds deterministic and conservative:
  - show a total failure alert when `totals.failedTurns > 0`;
  - show the lowest-success stage alert when a stage has failures and `successRate < 80`;
  - show the lowest-success provider alert when a provider has failures and `successRate < 80`.

## Non-Goals

- No persistent alert records.
- No notification delivery.
- No backend threshold configuration.
- No alert acknowledgement workflow.

## Design

Create `tools/new-agents/frontend/src/core/observabilityAlerts.ts` with a pure `buildObservabilityAlerts(summary)` function. It returns stable alert view models with `id`, `title`, and `detail`. The helper keeps alert selection deterministic by sorting candidate stage/provider summaries by success rate ascending and failure count descending.

`Header.tsx` imports the helper, derives `observabilityAlerts` from the current summary, and renders a `运行告警` section above metric cards only when alerts exist. The modal continues to render all raw statistics below the alerts.

## Testing

- Add unit tests for `buildObservabilityAlerts` covering total failure, lowest-success stage, lowest-success provider, and no-alert healthy data.
- Add a Header component test proving the runtime statistics modal renders the derived alert section from the existing mocked summary.

## Acceptance

- Failed runtime windows surface a concise alert before raw metric cards.
- Healthy windows do not render the alert section.
- No backend route or response schema changes are required.
