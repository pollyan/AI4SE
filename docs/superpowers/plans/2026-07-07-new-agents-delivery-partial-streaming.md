# New Agents DELIVERY Partial Artifact Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `TEST_DESIGN/DELIVERY` 在 raw JSON streaming 期间基于已闭合 `artifact_data` 字段生成正式测试设计交付文档 partial artifact delta。

**Architecture:** 复用现有共享 Agent Runtime、typed SSE、`render_partial_agent_turn_from_artifact_data()` dispatch、`AgentTurnOutput.artifact_patch` 和 ArtifactPane 消费链路。只新增 DELIVERY partial renderer，不改最终 DELIVERY schema、最终 renderer、API、store 或 workflow manifest。

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, React/Vitest 回归测试。

---

## File Structure

- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: 增加 DELIVERY partial renderer 测试，复用 `VALID_DELIVERY_ARTIFACT_DATA`。
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: 增加 DELIVERY raw JSON streaming 多段 partial delta 测试。
- Modify `tools/new-agents/backend/artifact_data_renderers.py`: 增加 DELIVERY partial dispatch 和 `render_partial_test_design_delivery_markdown()`。
- Modify `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`: 记录第 2 轮状态、验证证据、LLM judge 风险。

## Task 1: RED renderer test

- [ ] **Step 1: Add failing DELIVERY partial renderer test**

In `tools/new-agents/backend/tests/test_artifact_data_renderers.py`, add:

```python
def test_render_partial_delivery_artifact_data_builds_formal_incremental_markdown_and_patch():
    summary_payload = {
        "chat": "我正在形成测试设计交付文档。",
        "artifact_data": {
            "document_info": VALID_DELIVERY_ARTIFACT_DATA["document_info"],
            "executive_summary": VALID_DELIVERY_ARTIFACT_DATA["executive_summary"],
        },
        "stage_action": None,
        "warnings": [],
    }

    summary_output = render_partial_agent_turn_from_artifact_data(
        summary_payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    )

    assert summary_output is not None
    assert summary_output.artifact_update.markdown.startswith("# 测试设计文档")
    assert "## 1. 执行摘要" in summary_output.artifact_update.markdown
    assert "## 2. 需求分析摘要" not in summary_output.artifact_update.markdown
    assert "## 附录：文档信息" not in summary_output.artifact_update.markdown
    assert summary_output.artifact_patch is None

    requirement_payload = {
        **summary_payload,
        "artifact_data": {
            **summary_payload["artifact_data"],
            "requirement_summary": VALID_DELIVERY_ARTIFACT_DATA[
                "requirement_summary"
            ],
        },
    }
    requirement_output = render_partial_agent_turn_from_artifact_data(
        requirement_payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    )

    assert requirement_output is not None
    assert "## 2. 需求分析摘要" in requirement_output.artifact_update.markdown
    assert "## 3. 测试策略摘要" not in requirement_output.artifact_update.markdown
    assert requirement_output.artifact_patch is not None
    assert requirement_output.artifact_patch.operation == "add_after"
    assert requirement_output.artifact_patch.section_anchor == "h2:2. 需求分析摘要:1"
    assert requirement_output.artifact_patch.after_section_anchor == "h2:1. 执行摘要:1"
    assert (
        requirement_output.artifact_patch.base_content
        == summary_output.artifact_update.markdown
    )
```

- [ ] **Step 2: Run renderer test and verify RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_delivery_artifact_data_builds_formal_incremental_markdown_and_patch -q
```

Expected: FAIL because DELIVERY partial dispatch returns `None`.

## Task 2: GREEN DELIVERY partial renderer

- [ ] **Step 1: Add DELIVERY dispatch**

In `tools/new-agents/backend/artifact_data_renderers.py`, add a `("TEST_DESIGN", "DELIVERY")` branch in `render_partial_agent_turn_from_artifact_data()`:

```python
    elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "DELIVERY"):
        field_order = [
            "executive_summary",
            "requirement_summary",
            "strategy_summary_items",
            "case_summary_items",
            "coverage_map",
            "open_risks",
            "acceptance_checklist",
            "signoffs",
            "change_log",
            "document_info",
        ]
        renderer = render_partial_test_design_delivery_markdown
        markdown = render_partial_test_design_delivery_markdown(
            payload["artifact_data"]
        )
```

- [ ] **Step 2: Add partial renderer**

Add `render_partial_test_design_delivery_markdown(data: Any) -> str | None` near the other partial renderers. It must:

- Return `None` unless `data` is a dict with valid `document_info`.
- Return `None` until `executive_summary` is present.
- Append sections in the same order as `render_test_design_delivery_markdown()`.
- Return already-valid sections if a later field is missing or invalid.
- Append `## 附录：文档信息` only after `delivery_metrics` and `document_info` are both valid.

Implementation skeleton:

```python
def render_partial_test_design_delivery_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "document_info" not in data:
        return None
    try:
        document_info = DocumentInfo.model_validate(data["document_info"])
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 测试设计文档"]
    try:
        if "executive_summary" not in data:
            return None
        sections.append(
            _render_delivery_executive_summary(
                _validate_partial_list(
                    data["executive_summary"],
                    DeliveryExecutiveSummaryItem,
                )
            )
        )

        if "requirement_summary" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_requirement_summary(
                _validate_partial_list(
                    data["requirement_summary"],
                    DeliveryRequirementSummaryItem,
                )
            )
        )

        if "strategy_summary_items" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_strategy_summary(
                _validate_partial_list(
                    data["strategy_summary_items"],
                    DeliveryStrategySummaryItem,
                )
            )
        )

        if "case_summary_items" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_case_summary(
                _validate_partial_list(
                    data["case_summary_items"],
                    DeliveryCaseSummaryItem,
                )
            )
        )

        if "coverage_map" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_coverage_map(
                _validate_partial_list(
                    data["coverage_map"],
                    DeliveryCoverageMapItem,
                )
            )
        )

        if "open_risks" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_open_risks(
                _validate_partial_list(data["open_risks"], DeliveryOpenRisk)
            )
        )

        if "acceptance_checklist" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_acceptance_checklist(
                _validate_partial_list(data["acceptance_checklist"], StageGateCheck)
            )
        )

        if "signoffs" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_signoffs(
                _validate_partial_list(data["signoffs"], DeliverySignoff)
            )
        )

        if "change_log" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_change_log(
                _validate_partial_list(data["change_log"], DeliveryChangeLogItem)
            )
        )

        if "delivery_metrics" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_document_info(
                document_info,
                DeliveryMetrics.model_validate(data["delivery_metrics"]),
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)
```

- [ ] **Step 3: Run renderer test and verify GREEN**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_delivery_artifact_data_builds_formal_incremental_markdown_and_patch -q
```

Expected: PASS.

## Task 3: RED runtime streaming test

- [ ] **Step 1: Replace existing DELIVERY final-only stream test with partial stream test**

In `tools/new-agents/backend/tests/test_agent_runtime.py`, update `test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output()` so `fake_stream_chat_completion_content()` yields three JSON chunks:

1. partial JSON through `executive_summary`;
2. partial JSON through `requirement_summary`;
3. remaining complete JSON.

Assert:

- at least two `AgentTurnDeltaOutput` items before final output have `artifact_update.markdown`;
- first partial contains `## 1. 执行摘要` but not `## 2. 需求分析摘要`;
- second partial contains `## 2. 需求分析摘要` but not `## 3. 测试策略摘要`;
- at least one partial patch has `operation == "add_after"`;
- final output still contains `coverage-map`.

- [ ] **Step 2: Run runtime test and verify RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output -q
```

Expected before Task 2 implementation: FAIL because no partial DELIVERY output exists. Expected after Task 2 but before the test rewrite: existing test may pass final-only behavior; after rewrite it must pass only if partial runtime behavior works.

## Task 4: Runtime regression

- [ ] **Step 1: Run DELIVERY runtime test**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output -q
```

Expected: PASS.

- [ ] **Step 2: Run all TEST_DESIGN partial runtime tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output -q
```

Expected: PASS.

- [ ] **Step 3: Run focused backend regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_test_assets.py -q
```

Expected: PASS.

## Task 5: Frontend and documentation regression

- [ ] **Step 1: Run focused frontend stream tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Update todo**

In `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`:

- Mark `TEST_DESIGN/DELIVERY` as completed in the fact snapshot.
- Add a 第 2 轮 execution record with spec, plan, scope, delivery summary, verification commands, LLM judge status, and residual risks.
- Update top status to show 第 1-2 轮 completed deterministic verification and 第 3-7 pending, unless verification says otherwise.

- [ ] **Step 3: Run document checks**

Run:

```bash
git diff --check -- docs/strategy/goal-mode-playbook.md docs/strategy/goal-mode-cga-template.md docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md docs/superpowers/specs/2026-07-07-new-agents-cases-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-cases-partial-streaming.md docs/superpowers/specs/2026-07-07-new-agents-delivery-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-delivery-partial-streaming.md tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
```

Expected: no output.

Run:

```bash
rg -n "T[B]D|implement[ ]later|<填[入]|待[补]" docs/strategy/goal-mode-playbook.md docs/strategy/goal-mode-cga-template.md docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md docs/superpowers/specs/2026-07-07-new-agents-cases-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-cases-partial-streaming.md docs/superpowers/specs/2026-07-07-new-agents-delivery-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-delivery-partial-streaming.md
```

Expected: only playbook checklist mentions of placeholder markers, if any.

## Task 6: Full verification decision

- [ ] **Step 1: Run deterministic full local automation before commit**

Run outside sandbox if needed:

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

Expected: PASS.

- [ ] **Step 2: Handle LLM judge gate**

If `./scripts/test/test-local.sh all` with LLM judge enabled is run or referenced:

- score must be at least 80 to count as quality pass;
- if score is below 80, record the judge feedback, analyze DELIVERY-related and non-DELIVERY-related gaps separately, fix DELIVERY-relevant gaps if they are in scope, and rerun judge;
- if external model credentials, quota, or environment block rerun, record it as a residual risk and do not claim LLM quality gate pass.

## Self-Review

- Spec coverage: plan covers partial renderer, runtime partial delta, final contract regression, frontend stream consumption regression, todo update, LLM judge 80 gate, deterministic full automation.
- Placeholder scan: no unresolved placeholder markers are present.
- Type consistency: all planned fields match `DeliveryArtifactData` and existing renderer helper names.
