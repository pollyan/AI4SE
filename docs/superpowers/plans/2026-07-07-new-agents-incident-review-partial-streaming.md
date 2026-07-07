# New Agents INCIDENT_REVIEW Partial Artifact Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `INCIDENT_REVIEW/TIMELINE`、`INCIDENT_REVIEW/ROOT_CAUSE` 和 `INCIDENT_REVIEW/IMPROVEMENT` 在 raw JSON streaming 期间基于已闭合 `artifact_data` 字段生成正式故障复盘 artifact delta。

**Architecture:** 复用共享 Agent Runtime、typed SSE、`render_partial_agent_turn_from_artifact_data()` dispatch、`AgentTurnOutput.artifact_patch` 和 ArtifactPane 消费链路。只新增 INCIDENT_REVIEW 三个 partial renderer，不改 final schema、final renderer、API、store、workflow manifest 或前端渲染管线。

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, React/Vitest 回归测试。

## Global Constraints

- 遵守 `AGENTS.md`：所有 New Agents workflow 继续共享一套 runtime、transport、state 和 UI infrastructure。
- 不输出进度页、裸 JSON、字段名调试状态或 synthetic reveal 作为正式 partial artifact。
- 代码行为变更按 TDD：先写 failing tests，确认 RED，再实现。
- Final `agent_turn` 仍必须通过完整 workflow contract、Mermaid contract 和 structured visual contract。
- 如果启用或引用 LLM judge，默认 `score >= 80`；本轮未新增 INCIDENT_REVIEW LLM judge，因此不能声称真实模型质量评分。

---

## File Structure

- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: 增加 TIMELINE、ROOT_CAUSE、IMPROVEMENT partial renderer tests。
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: 把三个 INCIDENT_REVIEW raw JSON stream tests 从 final-only 升级为 final 前多段 partial delta tests。
- Modify `tools/new-agents/backend/artifact_data_renderers.py`: 增加 INCIDENT_REVIEW partial dispatch 和三个 partial renderer。
- Modify `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`: 记录第 4 轮状态、验证证据、LLM judge 状态和残余风险。

## Task 1: RED renderer tests

- [x] **Step 1: Add TIMELINE partial renderer test**

Add `test_render_partial_incident_timeline_artifact_data_builds_formal_incremental_markdown_and_patch()` near the existing partial renderer tests in `tools/new-agents/backend/tests/test_artifact_data_renderers.py`.

Test shape:

```python
def test_render_partial_incident_timeline_artifact_data_builds_formal_incremental_markdown_and_patch():
    summary_payload = {
        "chat": "我正在还原故障事件时间线。",
        "artifact_data": {
            "incident_summary": VALID_INCIDENT_TIMELINE_ARTIFACT_DATA["incident_summary"],
        },
        "stage_action": None,
        "warnings": [],
    }

    summary_output = render_partial_agent_turn_from_artifact_data(
        summary_payload,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="TIMELINE",
    )

    assert summary_output is not None
    assert summary_output.artifact_update.markdown.startswith("# 故障复盘报告")
    assert "## 1. 事件概要" in summary_output.artifact_update.markdown
    assert "## 2. 影响量化" not in summary_output.artifact_update.markdown
    assert summary_output.artifact_patch is None

    impact_payload = {
        **summary_payload,
        "artifact_data": {
            **summary_payload["artifact_data"],
            "impact_metrics": VALID_INCIDENT_TIMELINE_ARTIFACT_DATA["impact_metrics"],
        },
    }
    impact_output = render_partial_agent_turn_from_artifact_data(
        impact_payload,
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="TIMELINE",
    )

    assert impact_output is not None
    assert "## 2. 影响量化" in impact_output.artifact_update.markdown
    assert "## 3. 事实来源" not in impact_output.artifact_update.markdown
    assert impact_output.artifact_patch is not None
    assert impact_output.artifact_patch.operation == "add_after"
    assert impact_output.artifact_patch.section_anchor == "h2:2. 影响量化:1"
    assert impact_output.artifact_patch.after_section_anchor == "h2:1. 事件概要:1"
```

- [x] **Step 2: Add ROOT_CAUSE partial renderer test**

Add `test_render_partial_incident_root_cause_artifact_data_builds_formal_incremental_markdown_and_patch()`.

Expected assertions:

- first payload with `analysis_context` returns `# 故障复盘报告` and `## 6. 根因分析`;
- first payload does not contain `### 6.1 5-Why 分析链`;
- second payload adds `why_chain` and contains `### 6.1 5-Why 分析链`;
- second output contains `"type": "cause-map"`;
- second output does not contain `### 6.2 根因证据表`;
- second output has `add_after` patch for `h3:6.1 5-Why 分析链:1` after `h2:6. 根因分析:1`.

- [x] **Step 3: Add IMPROVEMENT partial renderer test**

Add `test_render_partial_incident_improvement_artifact_data_builds_formal_incremental_markdown_and_patch()`.

Expected assertions:

- first payload with `report_info` returns `# 故障复盘报告` and `## 报告信息`;
- first payload does not contain `## 第一部分：事件还原`;
- second payload adds `timeline_summary` and has `add_after` patch for `h2:第一部分：事件还原:1` after `h2:报告信息:1`;
- later payload with `root_cause_summary`, `priority_distribution` and `improvement_actions` contains `pie title 改进措施优先级分布` and `"type": "action-board"`;
- later payload does not contain `#### 7.3 根因覆盖检查`.

- [x] **Step 4: Run renderer tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_incident_timeline_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_incident_root_cause_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_incident_improvement_artifact_data_builds_formal_incremental_markdown_and_patch -q
```

Expected: FAIL because INCIDENT_REVIEW partial dispatch returns `None`.

## Task 2: GREEN partial renderers

- [x] **Step 1: Add dispatch branches**

In `render_partial_agent_turn_from_artifact_data()`, add branches:

```python
    elif (workflow_id, current_stage_id) == ("INCIDENT_REVIEW", "TIMELINE"):
        field_order = [
            "incident_summary",
            "impact_metrics",
            "fact_sources",
            "timeline_events",
            "fact_separation",
            "fact_summary",
            "participants",
            "missing_information",
            "stage_gate",
        ]
        renderer = render_partial_incident_review_timeline_markdown
        markdown = render_partial_incident_review_timeline_markdown(payload["artifact_data"])
    elif (workflow_id, current_stage_id) == ("INCIDENT_REVIEW", "ROOT_CAUSE"):
        field_order = [
            "analysis_context",
            "why_chain",
            "cause_evidence",
            "fishbone_categories",
            "root_cause_conclusions",
            "excluded_causes",
            "unverified_causes",
            "stage_gate",
        ]
        renderer = render_partial_incident_review_root_cause_markdown
        markdown = render_partial_incident_review_root_cause_markdown(payload["artifact_data"])
    elif (workflow_id, current_stage_id) == ("INCIDENT_REVIEW", "IMPROVEMENT"):
        field_order = [
            "report_info",
            "timeline_summary",
            "root_cause_summary",
            "priority_distribution",
            "improvement_actions",
            "root_cause_coverage",
            "prevention_checklist",
            "review_plan",
            "residual_risks",
            "lessons_learned",
            "organizational_learning",
            "signoffs",
            "stage_gate",
        ]
        renderer = render_partial_incident_review_improvement_markdown
        markdown = render_partial_incident_review_improvement_markdown(payload["artifact_data"])
```

- [x] **Step 2: Add TIMELINE partial renderer**

Add `render_partial_incident_review_timeline_markdown(data: Any) -> str | None`. It must:

- require `data` to be a dict;
- require valid `incident_summary`;
- append sections in final renderer order;
- render `timeline_events` only after `fact_sources` exists, because timeline event rows reference fact ids in the final schema;
- return `None` before the first real section and `_join_partial_sections(sections)` after each valid prefix.

- [x] **Step 3: Add ROOT_CAUSE partial renderer**

Add `render_partial_incident_review_root_cause_markdown(data: Any) -> str | None`. It must:

- require valid `analysis_context`;
- append `why_chain`, `cause_evidence`, `fishbone_categories`, `root_cause_conclusions`, `excluded_causes`, `unverified_causes`, `stage_gate` in final order;
- preserve `cause-map` under `why_chain`;
- preserve mindmap under `fishbone_categories`;
- return the last valid prefix if a later field is absent or invalid.

- [x] **Step 4: Add IMPROVEMENT partial renderer**

Add `render_partial_incident_review_improvement_markdown(data: Any) -> str | None`. It must:

- require valid `report_info`;
- append `timeline_summary` and `root_cause_summary` before the improvement section;
- append `## 第三部分：改进措施` and `### 7. 改进措施` only when either `priority_distribution` or `improvement_actions` exists;
- render `priority_distribution` if present;
- render `improvement_actions` if present and preserve `action-board`;
- append `root_cause_coverage`, `prevention_checklist`, `review_plan`, `residual_risks`, `lessons_learned`, `organizational_learning`, `signoffs`, and `stage_gate` in final order.

- [x] **Step 5: Run renderer tests and verify GREEN**

Run the same command from Task 1 Step 4.

Expected: PASS.

## Task 3: Runtime streaming tests

- [x] **Step 1: Upgrade TIMELINE runtime test**

In `test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output()`, split `final_json` into at least three chunks after the `incident_summary`, `fact_sources`, and `timeline_events` members. Assert:

- at least three partial `AgentTurnDeltaOutput` values appear before the final `AgentTurnOutput`;
- first partial contains `## 1. 事件概要` and not `## 2. 影响量化`;
- later partial contains `## 4. 事件时间线` and Mermaid `timeline`;
- final output remains contract-valid and requests `ROOT_CAUSE`.

- [x] **Step 2: Upgrade ROOT_CAUSE runtime test**

In `test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output()`, split after `analysis_context`, `why_chain`, and `fishbone_categories`. Assert:

- at least three partial deltas appear before final;
- first partial contains `## 6. 根因分析` and not `### 6.1 5-Why 分析链`;
- later partial contains `### 6.1 5-Why 分析链` and `"type": "cause-map"`;
- later partial contains `### 6.3 原因鱼骨图` and `mindmap`;
- final output remains contract-valid and requests `IMPROVEMENT`.

- [x] **Step 3: Upgrade IMPROVEMENT runtime test**

In `test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output()`, split after `report_info`, `root_cause_summary`, and `improvement_actions`. Assert:

- at least three partial deltas appear before final;
- first partial contains `## 报告信息` and not `## 第一部分：事件还原`;
- later partial contains `## 第三部分：改进措施`, `pie title 改进措施优先级分布`, and `"type": "action-board"`;
- final output remains contract-valid and has no next stage action.

- [x] **Step 4: Run runtime tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output -q
```

Expected: PASS after Task 2.

## Task 4: Focused regression

- [x] **Step 1: Run all partial runtime tests completed so far**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output -q
```

Expected: PASS.

- [x] **Step 2: Run backend focused regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: PASS.

- [x] **Step 3: Run frontend stream regression**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx
```

Expected: PASS.

## Task 5: Documentation and full verification

- [x] **Step 1: Update todo**

Update `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`:

- Move `INCIDENT_REVIEW/TIMELINE`, `INCIDENT_REVIEW/ROOT_CAUSE`, and `INCIDENT_REVIEW/IMPROVEMENT` to completed partial streaming snapshot.
- Add 第 4 轮 execution record with spec, plan, scope, verification commands, LLM judge status, and residual risks.
- Update top status to 第 1-4 轮 completed deterministic verification if verification succeeds.
- Update next candidate to 第 5 轮 `IDEA_BRAINSTORM`.

- [x] **Step 2: Run document checks**

Run:

```bash
git diff --check -- docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md docs/superpowers/specs/2026-07-07-new-agents-incident-review-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-incident-review-partial-streaming.md tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
```

Expected: no output.

Run:

```bash
rg -n "T[B]D|implement[ ]later|<填[入]|待[补]" docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md docs/superpowers/specs/2026-07-07-new-agents-incident-review-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-incident-review-partial-streaming.md
```

Expected: no output.

- [x] **Step 3: Run deterministic full local automation**

Run outside sandbox if needed:

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

Expected: PASS.

## LLM Judge Gate

This round does not add or reference an INCIDENT_REVIEW LLM judge. If a judge run is enabled during execution, score must be at least 80 to count as quality pass. If score is below 80, record the judge feedback, analyze in-scope INCIDENT_REVIEW gaps, fix prompt/contract/renderer/test data gaps, and rerun judge. If credentials, quota, or environment block rerun, record the block and do not claim quality gate pass.

## Self-Review

- Spec coverage: plan covers TIMELINE, ROOT_CAUSE, IMPROVEMENT partial renderers, runtime streaming, final contract regression, frontend stream consumption regression, todo update, LLM judge 80 gate, deterministic full automation.
- Placeholder scan: no unresolved placeholder markers are present.
- Type consistency: all planned fields match `IncidentTimelineArtifactData`, `IncidentRootCauseArtifactData`, `IncidentImprovementArtifactData`, and existing renderer helper names.
