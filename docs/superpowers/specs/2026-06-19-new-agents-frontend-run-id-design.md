# New Agents Frontend Run ID Design

## Current State Gap Analysis

- Backend `/api/agent/runs/stream` now creates or reuses server-side runs and returns `run_started.runId`.
- Frontend `generateResponseStream` currently ignores `run_started` metadata and never sends `runId`, so every turn still creates a new server run.
- Existing frontend workspace state remains in Zustand + localStorage. Full server-side restore/list/detail APIs do not exist yet, so this slice should not remove localStorage.

## Chosen Design

- Add `currentRunId: string | null` to the existing Zustand workspace state.
- Persist `currentRunId` with the current workspace state so a page reload can continue appending to the same server run.
- Clear `currentRunId` when the user switches workflow or clears history, because the current server run belongs to a specific workflow history.
- Include `runId` in `/new-agents/api/agent/runs/stream` request bodies only when `currentRunId` is present.
- When a `run_started` event includes `runId`, write it back to the store before yielding the normal "正在生成..." chunk.
- Do not expose run IDs in the visible UI in this slice.

## Requirements

- First request without `currentRunId` omits `runId` from the JSON body and stores `run_started.runId`.
- Later requests include the stored `runId`.
- `clearHistory()` and `setWorkflow()` reset `currentRunId`.
- Persisted workspace state sanitizes `currentRunId`; invalid values are dropped.
- Existing streaming behavior and chunk shape remain unchanged.

## Non-Goals

- No run list or resume page.
- No artifact diff UI from server versions.
- No migration away from localStorage.
- No cross-device sharing.

## Verification

- Store tests cover reset and persisted merge behavior.
- `llm.ts` tests cover request body omission/inclusion and `run_started.runId` storage.
- Existing frontend llm/store tests remain green.
