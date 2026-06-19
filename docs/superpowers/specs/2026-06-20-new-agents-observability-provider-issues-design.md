# New Agents Observability Provider Issues Design

## Problem

Provider and model configuration failures are now recoverable from ChatPane, but the runtime statistics view still exposes only raw error codes. Users cannot quickly tell whether failures are caused by model/provider availability versus artifact contract or Mermaid issues.

## Scope

Add provider issue visibility to the existing runtime observability path:

- Classify model/provider related error codes in backend observability summaries.
- Expose provider issue counts and provider issue code counts in totals, stage summaries, and provider summaries.
- Parse the new fields on the frontend with strict validation.
- Surface provider issue alerts and badges in the existing Header observability modal.

This does not add a new settings center, new runtime endpoint, workflow-specific logic, or provider-specific configuration branches.

## Provider Issue Definition

For this slice, provider issues are runtime turn failures whose persisted error code indicates model/provider availability.

Current `stream_services.py` persists provider/model-side runtime failures as:

- `LLM_ERROR`

Missing default LLM configuration is handled before a runtime turn metric is created, so it is not counted in this observability slice. Finer codes such as auth/rate-limit/network can be introduced later by changing stream error taxonomy and SSE contracts.

Existing contract and visualization errors remain visible through raw `errorCodes`, but should not be counted as provider issues.

## UX Contract

When provider issues exist, the runtime observability modal should show:

- A clear alert titled `模型/供应商异常集中`.
- A total card or diagnostic line with provider issue count.
- Stage/provider cards with `模型/供应商问题 xN` badges when relevant.

The existing success-rate, stage, provider, and recent-turn views remain intact.
