# New Agents Visual Diagnostic Focus Design

## Problem

ChatPane can already tell users that the current artifact has a Mermaid or `ai4se-visual` rendering problem. The message still asks users to manually inspect the right artifact pane, which is weak when the artifact is long or the failed block is below the fold.

## Scope

Add a shared focus path from the left visual diagnostic notice to the right artifact block:

- Store the requested visual diagnostic focus id in shared workspace state.
- ChatPane shows a `查看问题位置` action when a current-stage visual diagnostic exists.
- ArtifactPane marks Mermaid and `ai4se-visual` blocks with stable diagnostic ids.
- ArtifactPane switches to preview mode and scrolls the matching block into view when focus is requested.
- The focused block gets a temporary visual outline so users can see what was located.

This slice does not add a new renderer, workflow branch, agent branch, or browser-global event bus.

## UX Contract

When the left notice says `右侧产物有可视化需要处理`, the user can click `查看问题位置`. The right artifact pane should then:

- show preview mode if it was in code/edit mode,
- scroll the corresponding visual block into view,
- highlight the block,
- keep existing retry/failure actions intact.

If the block no longer exists, the action should be harmless.

## Architecture Notes

- Reuse `artifactVisualDiagnostics` ids already generated as `<kind>:<stageId>:<blockIndex>`.
- Add generic store action `focusArtifactVisualDiagnostic`.
- Keep block anchors generic by diagnostic id and avoid Lisa/Alex/workflow-specific code.
