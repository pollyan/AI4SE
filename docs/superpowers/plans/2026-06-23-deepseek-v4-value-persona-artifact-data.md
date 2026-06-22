# DeepSeek V4 Value Persona Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `VALUE_DISCOVERY/PERSONA` use DeepSeek-compatible `artifact_data` with backend validation and deterministic artifact rendering.

**Architecture:** Reuse the existing shared Agent Runtime and artifact data renderer registry. Add one stage-specific Pydantic schema and renderer, then wire `VALUE_DISCOVERY/PERSONA` into the same structured output instruction, retry, raw JSON parse, typed SSE, and contract validation paths already used by previous DeepSeek artifact_data stages.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing `AgentTurnOutput` and `validate_agent_turn()` contracts.

---

## File Map

- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: add fixture and RED tests for `ValueDiscoveryPersonaArtifactData`, deterministic rendering, contract validity, unknown persona references, and duplicate priority ranking.
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: add RED tests for parse, structured output instruction, retry prompt, and raw JSON stream rendering for `VALUE_DISCOVERY/PERSONA`.
- Modify `tools/new-agents/backend/artifact_data_renderers.py`: add schema classes, dispatch branch, renderer, and helper functions for the persona artifact.
- Modify `tools/new-agents/backend/agent_runtime.py`: add `VALUE_PERSONA_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`, support tuple, and instruction dispatch.
- Modify `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: record the completed `VALUE_DISCOVERY/PERSONA` slice and narrow remaining work.

## Task 1: Renderer RED Tests

- [ ] Add `ValueDiscoveryPersonaArtifactData` to the `artifact_data_renderers` import block in `tools/new-agents/backend/tests/test_artifact_data_renderers.py`.
- [ ] Add a valid `VALID_VALUE_PERSONA_ARTIFACT_DATA` fixture with one core persona, behavior scenario, decision chain, pain evidence, anti-persona, priority ranking, and stage gate.
- [ ] Add `test_value_persona_artifact_data_rejects_unknown_persona_reference()`, mutating `behavior_scenarios[0].persona_id` to `USER-404` and expecting `ValidationError` matching `references unknown persona ids`.
- [ ] Add `test_value_persona_artifact_data_rejects_duplicate_priority_persona()`, appending a second ranking for the same `persona_id` and expecting `ValidationError` matching `priority_ranking contains duplicate persona_id`.
- [ ] Add `test_render_value_persona_artifact_data_is_deterministic_and_contract_valid()`, rendering two identical outputs and asserting `# 用户画像分析`, `### 画像 1`, `#### 基础特征`, `#### 行为特征`, `## 决策链`, `## 用户优先级排序`, and `stage_action.target_stage_id == "JOURNEY"`.
- [ ] Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: FAIL because `ValueDiscoveryPersonaArtifactData` is not implemented.

## Task 2: Runtime RED Tests

- [ ] Add `VALID_VALUE_PERSONA_ARTIFACT_DATA` to the import block in `tools/new-agents/backend/tests/test_agent_runtime.py`.
- [ ] Add `test_parse_agent_turn_output_text_renders_value_persona_artifact_data()`, calling `parse_agent_turn_output_text(... workflow_id="VALUE_DISCOVERY", current_stage_id="PERSONA")` and asserting rendered artifact starts with `# 用户画像分析` and requests `JOURNEY`.
- [ ] Add `test_value_persona_structured_output_instruction_requests_artifact_data_not_markdown()`, asserting the instruction contains `artifact_data`, `personas`, `decision_chain`, `priority_ranking`, `"target_stage_id": "JOURNEY"`, and excludes `artifact_update`.
- [ ] Add `test_value_persona_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite()`, asserting retry prompt contains `artifact_data`, the validation error path, and not `artifact_update.type 必须为 replace`.
- [ ] Add raw stream test `test_runtime_raw_json_stream_turn_renders_value_persona_artifact_data_before_final_output()` using the DeepSeek raw streaming pattern and asserting final output is renderer Markdown.
- [ ] Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -q
```

Expected: FAIL because `VALUE_DISCOVERY/PERSONA` is not in artifact_data support registry.

## Task 3: Implement Schema And Renderer

- [ ] In `tools/new-agents/backend/artifact_data_renderers.py`, add schema classes:
  - `PersonaSummary`
  - `PersonaFeature`
  - `PersonaBehaviorFeature`
  - `PersonaProfile`
  - `PersonaBehaviorScenario`
  - `PersonaDecisionRole`
  - `PersonaPainEvidence`
  - `AntiPersona`
  - `PersonaPriorityRanking`
  - `ValueDiscoveryPersonaArtifactData`
- [ ] Add model validation in `ValueDiscoveryPersonaArtifactData`:

```python
persona_ids = {persona.persona_id for persona in self.personas}
if len(persona_ids) != len(self.personas):
    raise ValueError("personas contains duplicate persona_id")

references = [
    *(item.persona_id for item in self.behavior_scenarios),
    *(item.persona_id for item in self.decision_chain),
    *(item.persona_id for item in self.pain_evidence),
    *(item.persona_id for item in self.priority_ranking),
]
unknown = sorted({persona_id for persona_id in references if persona_id not in persona_ids})
if unknown:
    raise ValueError("persona references unknown persona ids: " + ", ".join(unknown))

ranked_ids = [item.persona_id for item in self.priority_ranking]
if len(set(ranked_ids)) != len(ranked_ids):
    raise ValueError("priority_ranking contains duplicate persona_id")
```

- [ ] Add dispatch branch for `("VALUE_DISCOVERY", "PERSONA")` in `render_agent_turn_from_artifact_data()`.
- [ ] Add `render_value_discovery_persona_markdown()` with sections in exact contract order.
- [ ] Use existing `_markdown_table()` and `_render_value_stage_gate()` patterns; do not add new rendering infrastructure.
- [ ] Run renderer tests until green.

## Task 4: Implement Runtime Wiring

- [ ] In `tools/new-agents/backend/agent_runtime.py`, add `VALUE_PERSONA_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` requiring JSON field order `chat`, `artifact_data`, `stage_action`, `warnings`.
- [ ] Include `document_info`, `persona_summary`, `personas`, `behavior_scenarios`, `decision_chain`, `pain_evidence`, `anti_personas`, `priority_ranking`, `stage_gate` in the instruction shape.
- [ ] Require `stage_action` target `JOURNEY`.
- [ ] Explicitly prohibit complete Markdown documents and Markdown tables.
- [ ] Add `("VALUE_DISCOVERY", "PERSONA")` to `supports_artifact_data_rendering()`.
- [ ] Add instruction dispatch for `VALUE_DISCOVERY/PERSONA`.
- [ ] Run runtime tests until green.

## Task 5: Documentation, Formatting, Verification, Commit

- [ ] Update `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` with an eighth completed slice for `VALUE_DISCOVERY/PERSONA`.
- [ ] Update remaining work to `VALUE_DISCOVERY/JOURNEY/BLUEPRINT` plus `IDEA_BRAINSTORM` and `INCIDENT_REVIEW`.
- [ ] Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/black tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py -q
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py
git diff --check
```

- [ ] Stage only this milestone's files and commit:

```bash
git add docs/superpowers/specs/2026-06-23-deepseek-v4-value-persona-artifact-data-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-value-persona-artifact-data.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
git commit -m "feat: 支持 DeepSeek 用户画像结构化产物数据"
```
