# New Agents Structured Visual Contract Design

## Goal

Make the new `ai4se-visual` frontend protocol enforceable by the backend artifact contract for the first natural stage: `TEST_DESIGN/CASES`.

## Scope

This slice requires `TEST_DESIGN/CASES` artifacts to include a fenced `ai4se-visual` JSON block with `type: "traceability-matrix"`. The JSON block should represent requirement, risk, test point, and test case traceability data that the frontend can render through `StructuredVisual`.

This slice does not add LLM judge scoring changes and does not require every workflow to use structured visuals yet.

## Contract

`TEST_DESIGN/CASES` must include a block like:

````markdown
```ai4se-visual
{
  "type": "traceability-matrix",
  "title": "需求-风险-测试点-用例追溯矩阵",
  "columns": ["需求", "风险", "测试点", "用例", "覆盖状态"],
  "rows": [
    {
      "需求": "REQ-1",
      "风险": "RISK-1",
      "测试点": "TP-1",
      "用例": "TC-1",
      "覆盖状态": "已覆盖"
    }
  ]
}
```
````

Backend validation accepts only fenced code blocks whose language is exactly `ai4se-visual`. The block content must be valid JSON object data, have `type: "traceability-matrix"`, include a non-empty `columns` string array, and include a `rows` object array.

## Architecture

- Add `REQUIRED_ARTIFACT_STRUCTURED_VISUALS` to `agent_contracts.py`, parallel to `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS`.
- Add `extract_structured_visual_blocks()` and validation helpers near the existing Mermaid code-block helpers.
- Extend `validate_artifact_template()` so missing required structured visuals produce the same high-level error family as missing Mermaid visuals: `missing required artifact visualizations`.
- Extend `build_artifact_contract_prompt()` to inject concise `ai4se-visual` instructions only for stages configured in the new contract map.

## Testing

- Contract prompt test proves `TEST_DESIGN/CASES` includes `ai4se-visual` and `traceability-matrix` instructions.
- Validation test proves `TEST_DESIGN/CASES` without the block is rejected.
- Validation test proves a valid fenced block is accepted through the existing complete-template parameterized test.

## Self-Review

- The design reuses the shared artifact contract path.
- The first required structured visual is scoped to the stage where traceability naturally belongs.
- Invalid visuals fail explicitly instead of being ignored.
- Judge rubric work is intentionally left as a separate follow-up.
