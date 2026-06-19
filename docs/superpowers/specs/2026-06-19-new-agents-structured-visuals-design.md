# New Agents Structured Visuals Design

## Goal

Introduce the first shared structured visualization protocol for artifact Markdown so workflows can output structured data blocks and the frontend can render them through reusable components instead of relying on model-written HTML.

## Scope

This slice adds frontend support for a fenced code block language named `ai4se-visual`. The first supported visual type is `traceability-matrix`, covering requirement, risk, test case, owner, or status style tables used by Lisa and other workflows.

The slice does not add backend contract enforcement yet. Mermaid contract validation remains unchanged. Invalid structured visual blocks render an explicit error panel in preview mode instead of crashing the artifact pane or silently falling back to raw HTML.

## Protocol

Artifact Markdown may include:

````markdown
```ai4se-visual
{
  "type": "traceability-matrix",
  "title": "需求-风险-用例追溯矩阵",
  "columns": ["需求", "风险", "用例", "覆盖状态"],
  "rows": [
    {
      "需求": "REQ-1",
      "风险": "RISK-1",
      "用例": "TC-1",
      "覆盖状态": "已覆盖"
    }
  ]
}
```
````

The parser accepts only JSON objects with:

- `type`: exactly `traceability-matrix`.
- `title`: optional non-empty string.
- `columns`: one or more non-empty strings.
- `rows`: array of objects keyed by column names. Missing cell values render as empty strings.

## Architecture

- `tools/new-agents/frontend/src/core/structuredVisuals.ts` owns parsing and validation. It has no React dependency.
- `tools/new-agents/frontend/src/components/StructuredVisual.tsx` owns rendering. It receives raw code, calls the parser, renders a table for valid matrices, and renders an explicit error state for invalid blocks.
- `tools/new-agents/frontend/src/components/markdownCodeRenderer.tsx` adds an optional structured visual renderer hook next to the existing Mermaid hook.
- `tools/new-agents/frontend/src/components/ArtifactPane.tsx` wires `ai4se-visual` to `StructuredVisual` for both live preview and history preview.

## Testing

- Parser tests cover valid matrix parsing and invalid JSON/schema failures.
- Component tests cover accessible table rendering and invalid block error rendering.
- ArtifactPane tests cover `ai4se-visual` Markdown rendering through the shared code renderer.

## Alternatives Considered

- Reuse raw Markdown tables only: lowest implementation cost, but it does not create a reusable protocol for richer visuals.
- Let models output HTML: flexible, but brittle and hard to validate or style consistently.
- Add backend contract enforcement immediately: useful later, but too broad for this focused todo slice.

## Self-Review

- No backend behavior changes are required for this slice.
- The language name and schema are explicit.
- Invalid state is visible and diagnosable.
- The scope is small enough to verify with focused frontend tests.
