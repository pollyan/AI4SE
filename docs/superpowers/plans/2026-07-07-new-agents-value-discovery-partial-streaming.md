# VALUE_DISCOVERY Partial Artifact Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable real partial artifact streaming for `VALUE_DISCOVERY/ELEVATOR`, `PERSONA`, `JOURNEY`, and `BLUEPRINT`.

**Architecture:** Reuse the shared raw JSON Agent Runtime, typed SSE output, artifact delta handling, final renderer helpers, and shared frontend ArtifactPane. The only runtime behavior change is adding VALUE stage branches to `render_partial_agent_turn_from_artifact_data()`.

**Tech Stack:** Python 3.11, Pydantic models, pytest, React/Vitest shared SSE regression.

---

## Scope

Modify:

- `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- `tools/new-agents/backend/tests/test_agent_runtime.py`
- `tools/new-agents/backend/artifact_data_renderers.py`
- `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`

Create:

- `docs/superpowers/specs/2026-07-07-new-agents-value-discovery-partial-streaming-design.md`
- `docs/superpowers/plans/2026-07-07-new-agents-value-discovery-partial-streaming.md`

Do not modify frontend runtime, frontend store, workflow-specific API paths, shared transport, unrelated dirty files, or existing generated bundles.

## Subagent Record

Hypatia completed a read-only review and found no blocker to implementing all four VALUE stages in one round. The review identified field dependencies that affect patch shape but not formal `artifact_update.replace.markdown` streaming. No worker is assigned because the write set is concentrated in one renderer file and two test files.

## Task 1: Add RED Partial Renderer Tests

**Files:**

- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`

- [ ] **Step 1: Add four failing tests**

Add tests near the existing partial renderer tests:

```python
def test_render_partial_value_elevator_artifact_data_builds_formal_incremental_markdown_and_patch():
    summary_payload = {
        "chat": "我正在生成价值定位分析。",
        "artifact_data": {
            "document_info": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["document_info"],
            "positioning_summary": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["positioning_summary"],
        },
        "stage_action": None,
        "warnings": [],
    }

    summary_output = render_partial_agent_turn_from_artifact_data(
        summary_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert summary_output is not None
    assert summary_output.artifact_update.markdown.startswith("# 价值定位分析")
    assert "## 定位摘要" in summary_output.artifact_update.markdown
    assert "## 价值结构图" not in summary_output.artifact_update.markdown
    assert summary_output.artifact_patch is None

    flow_payload = {
        **summary_payload,
        "artifact_data": {
            **summary_payload["artifact_data"],
            "value_flow": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["value_flow"],
        },
    }
    flow_output = render_partial_agent_turn_from_artifact_data(
        flow_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert flow_output is not None
    assert "## 价值结构图" in flow_output.artifact_update.markdown
    assert "flowchart TD" in flow_output.artifact_update.markdown
    assert "## 目标用户与场景" not in flow_output.artifact_update.markdown
    assert flow_output.artifact_patch is not None
    assert flow_output.artifact_patch.operation == "add_after"
```

```python
def test_render_partial_value_persona_artifact_data_builds_formal_incremental_markdown_and_patch():
    summary_payload = {
        "chat": "我正在生成用户画像分析。",
        "artifact_data": {
            "document_info": VALID_VALUE_PERSONA_ARTIFACT_DATA["document_info"],
            "persona_summary": VALID_VALUE_PERSONA_ARTIFACT_DATA["persona_summary"],
        },
        "stage_action": None,
        "warnings": [],
    }

    summary_output = render_partial_agent_turn_from_artifact_data(
        summary_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="PERSONA",
    )

    assert summary_output is not None
    assert summary_output.artifact_update.markdown.startswith("# 用户画像分析")
    assert "## 画像摘要" in summary_output.artifact_update.markdown
    assert "## 主要用户画像" not in summary_output.artifact_update.markdown

    personas_payload = {
        **summary_payload,
        "artifact_data": {
            **summary_payload["artifact_data"],
            "personas": VALID_VALUE_PERSONA_ARTIFACT_DATA["personas"],
        },
    }
    personas_output = render_partial_agent_turn_from_artifact_data(
        personas_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="PERSONA",
    )

    assert personas_output is not None
    assert "## 主要用户画像" in personas_output.artifact_update.markdown
    assert "### 画像 1" in personas_output.artifact_update.markdown
    assert "## 行为与场景" not in personas_output.artifact_update.markdown
    assert personas_output.artifact_patch is not None
```

```python
def test_render_partial_value_journey_artifact_data_builds_formal_incremental_markdown_and_patch():
    stages_payload = {
        "chat": "我正在生成用户旅程分析。",
        "artifact_data": {
            "document_info": VALID_VALUE_JOURNEY_ARTIFACT_DATA["document_info"],
            "journey_stages": VALID_VALUE_JOURNEY_ARTIFACT_DATA["journey_stages"],
        },
        "stage_action": None,
        "warnings": [],
    }

    stages_output = render_partial_agent_turn_from_artifact_data(
        stages_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="JOURNEY",
    )

    assert stages_output is not None
    assert stages_output.artifact_update.markdown.startswith("# 用户旅程分析")
    assert "## 用户旅程地图" in stages_output.artifact_update.markdown
    assert "journey\n    title 核心用户旅程" in stages_output.artifact_update.markdown
    assert '"type": "journey-map"' in stages_output.artifact_update.markdown
    assert "## 痛点优先级排序" not in stages_output.artifact_update.markdown

    pain_payload = {
        **stages_payload,
        "artifact_data": {
            **stages_payload["artifact_data"],
            "pain_priorities": VALID_VALUE_JOURNEY_ARTIFACT_DATA["pain_priorities"],
        },
    }
    pain_output = render_partial_agent_turn_from_artifact_data(
        pain_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="JOURNEY",
    )

    assert pain_output is not None
    assert "## 痛点优先级排序" in pain_output.artifact_update.markdown
    assert "高优先级痛点" in pain_output.artifact_update.markdown
```

```python
def test_render_partial_value_blueprint_artifact_data_builds_formal_incremental_markdown_and_patch():
    overview_payload = {
        "chat": "我正在生成需求蓝图。",
        "artifact_data": {
            "document_info": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA["document_info"],
            "product_overview": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA["product_overview"],
        },
        "stage_action": None,
        "warnings": [],
    }

    overview_output = render_partial_agent_turn_from_artifact_data(
        overview_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    )

    assert overview_output is not None
    assert overview_output.artifact_update.markdown.startswith(
        "# AI4SE 测试设计助手 需求蓝图"
    )
    assert "## 1. 产品概述" in overview_output.artifact_update.markdown
    assert "## 2. 目标用户（摘要）" not in overview_output.artifact_update.markdown

    users_payload = {
        **overview_payload,
        "artifact_data": {
            **overview_payload["artifact_data"],
            "target_users": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA["target_users"],
        },
    }
    users_output = render_partial_agent_turn_from_artifact_data(
        users_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    )

    assert users_output is not None
    assert "## 2. 目标用户（摘要）" in users_output.artifact_update.markdown
    assert "## 3. 核心需求" not in users_output.artifact_update.markdown
    assert users_output.artifact_patch is not None
```

- [ ] **Step 2: Run RED command**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_value_elevator_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_value_persona_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_value_journey_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_value_blueprint_artifact_data_builds_formal_incremental_markdown_and_patch -q
```

Expected: four failures because `render_partial_agent_turn_from_artifact_data()` currently returns `None` for `VALUE_DISCOVERY`.

## Task 2: Implement VALUE Partial Renderers

**Files:**

- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] **Step 1: Add VALUE dispatch branches**

Add four `elif` branches before the final `else: return None` in `render_partial_agent_turn_from_artifact_data()`:

```python
elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "ELEVATOR"):
    field_order = [
        "document_info",
        "positioning_summary",
        "value_flow",
        "target_scenarios",
        "pain_evidence",
        "differentiators",
        "business_feasibility",
        "score_matrix",
        "score_summary",
        "assumptions",
        "elevator_pitch",
        "stage_gate",
    ]
    renderer = render_partial_value_discovery_elevator_markdown
    markdown = render_partial_value_discovery_elevator_markdown(payload["artifact_data"])
```

Repeat the same structure for `PERSONA`, `JOURNEY`, and `BLUEPRINT` with the exact field orders listed in the spec.

- [ ] **Step 2: Add `render_partial_value_discovery_elevator_markdown()`**

Implement by appending sections in final renderer order. Validate each present field with existing models:

```python
def render_partial_value_discovery_elevator_markdown(data: dict[str, Any]) -> str | None:
    sections = ["# 价值定位分析"]
    if "positioning_summary" in data:
        sections.append(
            _render_value_positioning_summary(
                PositioningSummary.model_validate(data["positioning_summary"])
            )
        )
    if "value_flow" in data:
        sections.append(_render_value_flow(ValueFlow.model_validate(data["value_flow"])))
    if "target_scenarios" in data:
        sections.append(
            _render_target_scenarios(
                _validate_partial_list(data["target_scenarios"], TargetScenario)
            )
        )
    if "pain_evidence" in data:
        sections.append(
            _render_pain_evidence(
                _validate_partial_list(data["pain_evidence"], PainEvidence)
            )
        )
    if "differentiators" in data:
        sections.append(
            _render_differentiators(
                _validate_partial_list(data["differentiators"], Differentiator)
            )
        )
    if "business_feasibility" in data:
        sections.append(
            _render_business_feasibility(
                _validate_partial_list(data["business_feasibility"], BusinessFeasibility)
            )
        )
    if "score_matrix" in data and "score_summary" in data:
        sections.append(
            _render_value_score_matrix(
                _validate_partial_list(data["score_matrix"], ValueScore),
                ValueScoreSummary.model_validate(data["score_summary"]),
            )
        )
    if "assumptions" in data:
        sections.append(
            _render_value_assumptions(
                _validate_partial_list(data["assumptions"], ValueAssumption)
            )
        )
    if "elevator_pitch" in data:
        sections.append(_render_elevator_pitch(str(data["elevator_pitch"])))
    if "stage_gate" in data:
        sections.append(
            _render_value_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    return _join_partial_sections(sections)
```

- [ ] **Step 3: Add the other three partial renderers**

Use final renderer order and existing helper dependencies:

- `PERSONA`: render behavior, decision, pain, and ranking only when `personas` is present.
- `JOURNEY`: render map, visual, and stage details from `journey_stages`; render pain priorities only with `journey_stages`; render summary near the end to match final order.
- `BLUEPRINT`: render H1 only when `document_info` is present; render product overview as first visible body; render requirements only when both `feature_modules` and `requirements` are present.

Catch `(TypeError, ValueError, ValidationError, KeyError)` and return `None`, matching existing partial renderer error behavior.

- [ ] **Step 4: Run renderer GREEN command**

Run the same command from Task 1 Step 2.

Expected: `4 passed`.

## Task 3: Upgrade Runtime Streaming Tests

**Files:**

- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [ ] **Step 1: Change VALUE runtime tests to stream JSON prefixes**

For each existing VALUE test, replace the single `yield final_json` fake stream with prefix chunks. Use the existing local helper pattern:

```python
def prefix_after_artifact_data_member(member_name: str) -> str:
    needle = f'"{member_name}":'
    member_start = final_json.index(needle)
    cursor = member_start + len(needle)
    depth = 0
    in_string = False
    escaped = False
    while cursor < len(final_json):
        char = final_json[cursor]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        elif char == "," and depth == 0:
            return final_json[:cursor]
        cursor += 1
    return final_json
```

Recommended chunk points:

- `ELEVATOR`: `positioning_summary`, `value_flow`, `target_scenarios`, `score_summary`.
- `PERSONA`: `persona_summary`, `personas`, `decision_chain`.
- `JOURNEY`: `journey_stages`, `pain_priorities`, `opportunity_scores`.
- `BLUEPRINT`: `product_overview`, `target_users`, `requirements`, `main_flow`.

- [ ] **Step 2: Assert partial outputs before final output**

For each VALUE test, collect:

```python
artifact_outputs = [
    output
    for output in outputs[:-1]
    if isinstance(output, AgentTurnDeltaOutput)
    and output.artifact_update is not None
    and output.artifact_update.markdown is not None
]
```

Assert at least two partial artifact deltas and stage-specific section progression. The final output assertions must remain.

- [ ] **Step 3: Run VALUE runtime tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_elevator_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_persona_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_journey_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_blueprint_artifact_data_before_final_output -q
```

Expected after Task 2 implementation: `4 passed`.

## Task 4: Run Focused Regressions

**Files:**

- Verify: backend and frontend shared stream tests.

- [ ] **Step 1: Run all partial runtime tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_define_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_concept_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_elevator_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_persona_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_journey_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_blueprint_artifact_data_before_final_output -q
```

Expected: `17 passed`.

- [ ] **Step 2: Run backend focused suite**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Run frontend shared stream regression**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx
```

Expected: three selected test files pass.

## Task 5: Update Records and Full Verification

**Files:**

- Modify: `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`

- [ ] **Step 1: Update todo state**

Record:

- 第 6 轮完成 status after verification.
- VALUE four stages added to completed snapshot.
- Hypatia read-only review result.
- RED and GREEN commands with results.
- LLM judge state: not enabled for this round; no quality score claimed.
- Next candidate: 第 7 轮 full workflow contract/evidence archive.

- [ ] **Step 2: Run document checks**

Run:

```bash
git diff --check -- docs/strategy/goal-mode-playbook.md docs/strategy/goal-mode-cga-template.md docs/strategy/goal-mode-subagents.md docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md docs/superpowers/specs/2026-07-07-new-agents-value-discovery-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-value-discovery-partial-streaming.md tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
```

Run:

```bash
rg -n "T[B]D|implement[ ]later|<填[入]|待[补]" docs/strategy/goal-mode-playbook.md docs/strategy/goal-mode-cga-template.md docs/strategy/goal-mode-subagents.md docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md docs/superpowers/specs/2026-07-07-new-agents-value-discovery-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-value-discovery-partial-streaming.md
```

Expected: no output for `git diff --check`; no forbidden placeholder output.

- [ ] **Step 3: Run full local automation**

Run:

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

Expected: pass outside sandbox if Playwright or port binding is blocked by sandbox permissions. If sandbox fails with `EPERM` for port binding or Chromium, rerun with approved non-sandbox execution and record both results.

## LLM Judge Rule

This round does not enable a new VALUE LLM judge. If any VALUE judge score is produced or referenced, the pass line is `score >= 80`; a lower score immediately becomes the current P0 repair story with documented gap analysis and rerun evidence.
