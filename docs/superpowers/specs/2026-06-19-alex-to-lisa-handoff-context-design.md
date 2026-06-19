# Alex To Lisa Handoff Context Design

## Current State Gap Analysis

- P1 #8 requires a continuous path from Alex value discovery / PRD outputs to Lisa requirement review or test design.
- New Agents already has shared workflow metadata, persisted run snapshots, artifact summaries, and service-side context building.
- There is still no explicit configuration that says which Alex artifact can be handed to which Lisa workflow, and no backend output that prepares the handoff context.

## Chosen Design

Add shared manifest handoff configuration and a read-only backend endpoint:

- Manifest declares `VALUE_DISCOVERY/BLUEPRINT` can hand off to:
  - `TEST_DESIGN/CLARIFY`
  - `REQ_REVIEW/REVIEW`
- Backend validates handoff config against known workflow/stage keys and target agent ownership.
- `GET /api/agent/runs/{runId}/handoffs` reads a persisted Alex run snapshot and returns available handoffs only when the source artifact exists.
- Each handoff includes target workflow/stage, target agent, label, source artifact version, and a bounded prompt/context string that can be used as the first Lisa input.

This is configuration-driven and does not create runtime branches, duplicate SSE paths, or automatically create a Lisa run.

## Requirements

- Handoffs are declared in `workflow_manifest.json`, not hardcoded in route logic.
- Unknown workflow/stage references in handoff config fail tests.
- A run without the required source artifact returns an empty `handoffs` list.
- A non-source workflow returns an empty `handoffs` list, not a fake success handoff.
- Handoff prompt includes the source workflow/stage, target workflow/stage, and source artifact content.

## Non-Goals

- No frontend handoff UI in this slice.
- No automatic creation of a target Lisa run.
- No model-generated transformation or summarization.
- No new Agent Runtime endpoint or SSE branch.

## Verification

- Manifest sync tests validate handoff references.
- Service tests cover available handoffs, missing source artifact, and non-source workflow.
- Endpoint tests cover JSON response.
- Backend full tests and `git diff --check` pass.
