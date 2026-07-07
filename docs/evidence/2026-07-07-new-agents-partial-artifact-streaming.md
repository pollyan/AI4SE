# New Agents Partial Artifact Streaming Evidence

## Scope

This evidence record covers the 2026-07-07 target-mode route for real partial artifact streaming across all online New Agents workflows.

Covered stages:

- `TEST_DESIGN/CLARIFY`
- `TEST_DESIGN/STRATEGY`
- `TEST_DESIGN/CASES`
- `TEST_DESIGN/DELIVERY`
- `REQ_REVIEW/REVIEW`
- `REQ_REVIEW/REPORT`
- `INCIDENT_REVIEW/TIMELINE`
- `INCIDENT_REVIEW/ROOT_CAUSE`
- `INCIDENT_REVIEW/IMPROVEMENT`
- `IDEA_BRAINSTORM/DEFINE`
- `IDEA_BRAINSTORM/DIVERGE`
- `IDEA_BRAINSTORM/CONVERGE`
- `IDEA_BRAINSTORM/CONCEPT`
- `VALUE_DISCOVERY/ELEVATOR`
- `VALUE_DISCOVERY/PERSONA`
- `VALUE_DISCOVERY/JOURNEY`
- `VALUE_DISCOVERY/BLUEPRINT`

## Result Summary

- Backend typed SSE, frontend `generateResponseStream()`, `chatService`, Zustand state, and ArtifactPane already supported streaming transport and incremental writes.
- Rounds 1-6 added or verified formal partial artifact rendering for all 17 online stages using the shared Agent Runtime and shared frontend consumption path.
- No workflow-specific runtime, SSE endpoint, store, or bespoke ArtifactPane rendering pipeline was added.
- Round 7 updated stable API and testing documentation so future work can find the contract and verification matrix.
- 2026-07-08 real SSE review found that artifact-data stages still instructed the model to output top-level `chat` before `artifact_data`, which could make the visible artifact appear only near the end of a real model run. The instruction order was changed to `artifact_data` before `chat` for all 17 artifact-data stages.

## 2026-07-08 Real SSE Correction

Trigger:

- User reported that `VALUE_DISCOVERY` and `IDEA_BRAINSTORM` still refreshed the right-side artifact all at once in the local UI.

Root cause:

- The deterministic tests sliced synthetic raw JSON after `artifact_data` members, but real model output followed the prompt's top-level order: `chat` first, then `artifact_data`.
- Because the right-side artifact renderer can only work after `artifact_data` begins, a real run could stream chat deltas for most of the request and only emit artifact deltas near final output.

Fix:

- `tools/new-agents/backend/agent_runtime.py` now rewrites all artifact-data structured output instructions so the top-level JSON order is `artifact_data`, `chat`, `stage_action`, `warnings`.
- `IDEA_BRAINSTORM/DEFINE` instructions now explicitly tell the model that `evidence_items.related_problem` and `problem_user_fit.evidence_or_assumption` must contain `problem_landscape.root_problem`, matching the backend contract.

Pre-fix real SSE evidence on local deployment:

- `VALUE_DISCOVERY/ELEVATOR`: first artifact delta at 17.03s, final at 17.20s, artifact lengths `[3634, 3634, 3634]`.
- `IDEA_BRAINSTORM/DEFINE`: first artifact delta at 16.94s, final at 17.13s, artifact lengths `[2817, 2817, 2817]`.

Post-fix real SSE evidence on local deployment after restarting `ai4se-new-agents-backend`:

- `VALUE_DISCOVERY/ELEVATOR`: first artifact delta at 3.49s, final at 21.13s, artifact lengths began `252 -> 637 -> 926 -> 1316 -> 1588 -> 1857 -> 2754 -> 3041 -> 3146 -> 3240`.
- `IDEA_BRAINSTORM/DEFINE`: first artifact delta at 2.24s, artifact lengths began `388 -> 691 -> 1130 -> 1436 -> 1847 -> 2032 -> 2259 -> 2326`. The sampled real model run then retried and produced another early artifact sequence `375 -> 687 -> 1115 -> 1434 -> 1821 -> 2007 -> 2180 -> 2302`, but ended with `SCHEMA_VALIDATION_FAILED` because the model did not satisfy the DEFINE root-problem coverage contract. This proves the visible artifact delta is now early and incremental for the sampled IDEA run, but that particular external model sample did not prove final contract success.
- A follow-up external model rerun was blocked by approval review because it would export repository workflow prompts and contract instructions to the configured external model endpoint. Further real-provider smoke should only run with explicit user approval.

Additional deterministic verification:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_define_structured_output_instruction_explains_root_problem_coverage -q
```

Result: `18 passed`.

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Result: `318 passed`.

```bash
bash scripts/health/health_check.sh local
```

Result: all local health checks passed after backend restart.

Regression-suite inclusion:

```bash
./scripts/test/test-local.sh new-agents
```

Result: passed. New Agents Frontend: 697 passed. New Agents Backend: 548 passed / 1 deselected. The backend suite includes `test_artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming`, so the artifact-data-first streaming instruction invariant now runs in the standard New Agents regression set.

## Verification Evidence

Focused renderer and runtime tests:

- `TEST_DESIGN/CASES`: renderer RED failed because partial dispatch returned `None`; GREEN passed.
- `TEST_DESIGN/DELIVERY`: renderer RED failed because partial dispatch returned `None`; GREEN passed.
- `REQ_REVIEW/REVIEW` and `REQ_REVIEW/REPORT`: renderer RED failed because partial dispatch returned `None`; GREEN passed.
- `INCIDENT_REVIEW/TIMELINE`, `ROOT_CAUSE`, `IMPROVEMENT`: renderer RED failed because partial dispatch returned `None`; GREEN passed.
- `IDEA_BRAINSTORM/DEFINE`, `DIVERGE`, `CONVERGE`, `CONCEPT`: renderer RED failed because partial dispatch returned `None`; GREEN passed.
- `VALUE_DISCOVERY/ELEVATOR`, `PERSONA`, `JOURNEY`, `BLUEPRINT`: renderer RED failed because partial dispatch returned `None`; GREEN passed.

Final focused commands from round 6:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_define_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_concept_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_elevator_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_persona_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_journey_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_blueprint_artifact_data_before_final_output -q
```

Result: `17 passed`.

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Result: `300 passed`.

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx
```

Result: 3 selected files passed, 140 tests passed.

Full local automation:

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

Result: passed outside sandbox. Key results:

- Intent Tester API: 294 passed.
- Critical Python lint: 0 severe errors.
- MidScene Proxy: 17 passed.
- Common Frontend lint/build: passed.
- New Agents Frontend: 697 passed.
- New Agents Backend: 530 passed / 1 deselected.
- New Agents Browser E2E: 4 passed / 3 skipped / 10 deselected.

## LLM Judge Evidence

During the route, Lisa optional judge returned score 64. That was treated as a quality gate failure and repaired before continuing.

Repair summary:

- Raised shared LLM judge pass line to 80.
- Expanded Lisa mock fixture coverage for cases, test data, edge cases, security, performance, degradation, and observability.
- Added DELIVERY `traceability-matrix` alongside `coverage-map`.
- Synchronized delivery contract / manifest / prompt.

Verification:

```bash
.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py::test_lisa_final_artifact_passes_optional_llm_judge -q
```

Result: 1 passed; the test enforces `score >= 80`.

## Risk Boundary

- This record proves deterministic mock raw JSON streaming, typed SSE parsing, frontend shared stream consumption, final contracts, and full local automation.
- It does not prove every real model run will produce high-quality content. Real model smoke and judge runs still depend on local model configuration, network, quota, and external provider behavior.
- `artifact_patch` is optional optimization metadata. Some valid partial deltas only carry formal `artifact_update.replace.markdown`, especially when a section depends on multiple top-level fields or adds multiple headings at once.
