# New Agents Structured Visual Judge Design

## Goal

Extend the optional E2E LLM judge rubric so it can evaluate the new `ai4se-visual` structured visualization protocol instead of only generic charts.

## Scope

This slice updates prompt construction in `tests/e2e/new_agents_browser/llm_judge.py`. It does not call a real judge unless the existing `NEW_AGENTS_E2E_LLM_JUDGE=1` gate is enabled.

## Design

The artifact judge prompt keeps the existing generic visual rubric and adds explicit criteria for structured visuals:

- If an artifact contains `ai4se-visual`, judge whether the JSON type is appropriate for the stage.
- For `traceability-matrix`, judge whether requirements, risks, test points, and cases are traceable and consistent with the prose.
- Ask the judge to include a `dimension_scores` entry for visual quality or structured visualization quality.

The handoff judge remains focused on cross-agent continuity; structured visual quality is already covered through the Lisa testing rubric when judging the target Lisa output.

## Testing

Update `test_llm_judge.py` so the Lisa judge prompt test asserts the prompt mentions `ai4se-visual`, `traceability-matrix`, and a visual quality score dimension.

## Self-Review

- The change is prompt-only and keeps optional real-LLM execution gated.
- It directly closes the remaining P0 #3 judge rubric note.
- It does not require a new runtime path or workflow branch.
