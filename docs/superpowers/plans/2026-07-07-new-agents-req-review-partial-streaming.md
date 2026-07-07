# New Agents REQ_REVIEW Partial Artifact Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `REQ_REVIEW/REVIEW` 和 `REQ_REVIEW/REPORT` 在 raw JSON streaming 期间基于已闭合 `artifact_data` 字段生成正式需求评审 artifact delta。

**Architecture:** 复用共享 Agent Runtime、typed SSE、`render_partial_agent_turn_from_artifact_data()` dispatch、`AgentTurnOutput.artifact_patch` 和 ArtifactPane 消费链路。只新增 REQ_REVIEW 两个 partial renderer，不改 final schema、final renderer、API、store 或 workflow manifest。

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, React/Vitest 回归测试。

---

## File Structure

- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: 增加 REVIEW 和 REPORT partial renderer 测试。
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: 把 REVIEW 和 REPORT raw JSON stream 测试从 final-only 升级成多段 partial delta 测试。
- Modify `tools/new-agents/backend/artifact_data_renderers.py`: 增加 REQ_REVIEW partial dispatch 和两个 partial renderer。
- Modify `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`: 记录第 3 轮状态、验证证据、LLM judge 状态。

## Task 1: RED renderer tests

- [x] **Step 1: Add REVIEW partial renderer test**

Add `test_render_partial_req_review_artifact_data_builds_formal_incremental_markdown_and_patch()` near the existing REQ_REVIEW renderer tests. It should create a first payload with `review_info` and `scope_items`, then a second payload adding `quality_overview` and `issue_statistics`.

Expected assertions:

- first output starts with `# 需求评审问题清单`;
- first output contains `## 评审范围与不评审范围` and not `## 需求质量总览`;
- second output contains `## 问题统计` and `"type": "score-matrix"`;
- second output does not contain `## 按维度问题清单`;
- second output has an `add_after` patch when section counts permit.

- [x] **Step 2: Add REPORT partial renderer test**

Add `test_render_partial_req_review_report_artifact_data_builds_formal_incremental_markdown_and_patch()`. It should create a first payload with `conclusion`, a second payload adding `review_info` and `issue_statistics`.

Expected assertions:

- first output starts with `# 需求评审报告`;
- first output contains `## 评审结论` and not `## 评审信息`;
- second output contains `## 问题统计` and not `## 优先级看板`;
- second output has an `add_after` patch for `h2:问题统计:1` after `h2:评审信息:1`.

- [x] **Step 3: Run renderer tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_req_review_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_req_review_report_artifact_data_builds_formal_incremental_markdown_and_patch -q
```

Expected: FAIL because REQ_REVIEW partial dispatch returns `None`.

## Task 2: GREEN partial renderers

- [x] **Step 1: Add dispatch branches**

In `render_partial_agent_turn_from_artifact_data()`, add:

```python
    elif (workflow_id, current_stage_id) == ("REQ_REVIEW", "REVIEW"):
        field_order = [
            "scope_items",
            "quality_overview",
            "issue_statistics",
            "issue_groups",
            "revision_suggestions",
            "stage_gate",
        ]
        renderer = render_partial_req_review_review_markdown
        markdown = render_partial_req_review_review_markdown(payload["artifact_data"])
    elif (workflow_id, current_stage_id) == ("REQ_REVIEW", "REPORT"):
        field_order = [
            "conclusion",
            "review_info",
            "issue_statistics",
            "issue_closures",
            "review_conditions",
            "signoffs",
            "change_log",
        ]
        renderer = render_partial_req_review_report_markdown
        markdown = render_partial_req_review_report_markdown(payload["artifact_data"])
```

- [x] **Step 2: Add REVIEW partial renderer**

Add `render_partial_req_review_review_markdown(data: Any) -> str | None`. It must validate `review_info`, render `scope_items` first, then append `quality_overview`, quality flowchart, `issue_statistics`, `issue_groups`, `revision_suggestions`, `stage_gate`, and finally review info.

- [x] **Step 3: Add REPORT partial renderer**

Add `render_partial_req_review_report_markdown(data: Any) -> str | None`. It must render `conclusion` first, then append `review_info`, `issue_statistics`, `priority-board`, `issue_closures`, `review_conditions`, `signoffs`, and `change_log` in final renderer order.

- [x] **Step 4: Run renderer tests and verify GREEN**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_req_review_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_req_review_report_artifact_data_builds_formal_incremental_markdown_and_patch -q
```

Expected: PASS.

## Task 3: Runtime streaming tests

- [x] **Step 1: Upgrade REVIEW runtime test**

In `test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output()`, split `final_json` into chunks after `scope_items` and after `issue_statistics`. Assert at least two partial artifact markdowns before final output.

- [x] **Step 2: Upgrade REPORT runtime test**

In `test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output()`, split `final_json` into chunks after `conclusion` and after `issue_statistics`. Assert at least two partial artifact markdowns before final output.

- [x] **Step 3: Run runtime tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output -q
```

Expected: PASS after Task 2.

## Task 4: Focused regression

- [x] **Step 1: Run all partial runtime tests completed so far**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output -q
```

Expected: PASS.

- [x] **Step 2: Run backend focused regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_test_assets.py -q
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

Update the vertical-slices todo:

- Move `REQ_REVIEW/REVIEW` and `REQ_REVIEW/REPORT` to completed partial streaming snapshot.
- Add 第 3 轮 execution record with spec, plan, scope, verification commands, LLM judge status, and residual risks.
- Update top status to 第 1-3 轮 completed deterministic verification if verification succeeds.

- [x] **Step 2: Run document checks**

Run:

```bash
git diff --check -- docs/strategy/goal-mode-playbook.md docs/strategy/goal-mode-cga-template.md docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md docs/superpowers/specs/2026-07-07-new-agents-cases-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-cases-partial-streaming.md docs/superpowers/specs/2026-07-07-new-agents-delivery-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-delivery-partial-streaming.md docs/superpowers/specs/2026-07-07-new-agents-req-review-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-req-review-partial-streaming.md tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
```

Expected: no output.

Run:

```bash
rg -n "T[B]D|implement[ ]later|<填[入]|待[补]" docs/strategy/goal-mode-playbook.md docs/strategy/goal-mode-cga-template.md docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md docs/superpowers/specs/2026-07-07-new-agents-cases-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-cases-partial-streaming.md docs/superpowers/specs/2026-07-07-new-agents-delivery-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-delivery-partial-streaming.md docs/superpowers/specs/2026-07-07-new-agents-req-review-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-req-review-partial-streaming.md
```

Expected: only intentional rule text, if any.

- [x] **Step 3: Run deterministic full local automation**

Run outside sandbox if needed:

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

Expected: PASS.

## LLM Judge Gate

If an LLM judge run is enabled or referenced, score must be at least 80 to count as quality pass. If score is below 80, record the judge feedback, analyze REQ_REVIEW-related and unrelated gaps separately, fix in-scope gaps, and rerun judge. If credentials, quota, or environment block rerun, record the block and do not claim quality gate pass.

## Self-Review

- Spec coverage: plan covers REVIEW and REPORT partial renderers, runtime streaming, final contract regression, frontend stream consumption regression, todo update, LLM judge 80 gate, deterministic full automation.
- Placeholder scan: no unresolved placeholder markers are present.
- Type consistency: all planned fields match `ReqReviewArtifactData`, `ReqReviewReportArtifactData`, and existing renderer helper names.
