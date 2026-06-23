# Workflow Handoff Context Review Design

## Current State Gap

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` lists E07 as a P1 gap: workflow handoff must expose source version, key summary, unconfirmed items, and target workflow input. The current shared handoff path already works at an infrastructure level: manifest handoffs are exported by `workflow_handoffs.py`, the frontend fetches candidates, and `start_workflow_handoff` creates a target run with a first user message. The missing capability is the review surface between those two steps.

Today the user sees a compact handoff button. They cannot inspect which source artifact version will be used, what the upstream artifact says in short form, which items are still unconfirmed, or what Lisa will receive as target workflow input. This makes cross-workflow transfer technically possible but weak as a professional trust loop.

## Milestone

Build a complete workflow handoff context review slice:

- Backend handoff export returns structured review context for each candidate.
- The generated target prompt includes the same structured context before the bounded source artifact.
- The frontend parser treats the new fields as a strict API contract.
- The chat pane renders a review card with source version, summary, unconfirmed items, and target input checklist before the user starts the handoff.
- Starting the handoff still uses the existing shared run persistence, workflow manifest, store transition, and typed Agent Runtime path.

## Requirements

- Keep all handoffs configuration-driven through `workflow_manifest.json`; do not create Lisa, Alex, or DeepSeek specific runtime/API/store branches.
- Preserve existing endpoints:
  - `GET /api/agent/runs/<run_id>/handoffs`
  - `POST /api/agent/runs/<run_id>/handoffs/<handoff_id>/start`
- Add these required handoff fields:
  - `sourceSummary`: a short deterministic summary derived from the source artifact.
  - `unconfirmedItems`: a deterministic list of open or unconfirmed items from the source artifact.
  - `targetInputChecklist`: a deterministic list that explains what the target workflow will receive or must re-check.
- Keep extraction deterministic and local. Do not call an LLM for handoff summaries.
- When no unconfirmed items are found, return an empty `unconfirmedItems` list rather than fabricating concerns.
- The prompt written into the target run must include source version, summary, unconfirmed items, target input checklist, and the bounded source artifact.
- The UI must make the context visible before the user clicks the handoff action.
- Malformed API payloads must fail explicitly in the frontend parser.

## Non-Goals

- No new handoff endpoint or SSE path.
- No new persisted table for handoff review context.
- No model-based summarizer or quality scoring.
- No run history clone/filter work; that remains E06.
- No workflow quality score; that remains E08.

## Acceptance Checks

- Backend tests prove exported handoffs include source summary, unconfirmed items, target checklist, and enriched prompt content.
- Endpoint tests prove the API exposes the review fields.
- Frontend service tests prove strict parsing of the review fields.
- Chat pane tests prove the user can see the context before starting a handoff and the start action still navigates to the target run.
- Store tests continue to prove a handoff starts as a fresh target workflow context.
- Todo docs mark E07 as completed and keep E06/E08/E09 as next candidates.
