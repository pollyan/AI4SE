# IDEA DIVERGE / CONVERGE Partial 引用门禁 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 IDEA_BRAINSTORM 的 DIVERGE / CONVERGE partial artifact preview 不展示已知跨引用错误章节。

**Architecture:** 抽取 final validator 中的关键引用校验 helper，并在 partial renderer 中逐段调用。final validation 仍保留完整 strict contract，partial renderer 只决定是否展示可信预览章节。

**Tech Stack:** Python 3.11, Pydantic v2, pytest, New Agents backend artifact renderer.

---

### Task 1: 写 RED 测试

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`

- [x] **Step 1: 增加 DIVERGE source unknown reference partial 测试**

Add a test near existing IDEA partial tests:

```python
def test_render_partial_idea_diverge_artifact_data_skips_sources_with_unknown_idea_reference():
    payload = {
        "chat": "我正在发散产品创意。",
        "artifact_data": {
            "divergence_method": VALID_IDEA_DIVERGE_ARTIFACT_DATA["divergence_method"],
            "idea_landscape": VALID_IDEA_DIVERGE_ARTIFACT_DATA["idea_landscape"],
            "idea_cards": VALID_IDEA_DIVERGE_ARTIFACT_DATA["idea_cards"],
            "idea_sources": [
                {**VALID_IDEA_DIVERGE_ARTIFACT_DATA["idea_sources"][0], "idea_ids": ["ID-404"]}
            ],
        },
        "stage_action": None,
        "warnings": [],
    }

    output = render_partial_agent_turn_from_artifact_data(
        payload,
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DIVERGE",
    )

    assert output is not None
    assert "## 创意卡片库" in output.artifact_update.markdown
    assert "## 创意来源与假设" not in output.artifact_update.markdown
```

- [x] **Step 2: 增加 CONVERGE partial 引用门禁测试**

Add tests for invalid recommended idea, invalid ICE score, unknown experiment idea, and unknown merge path idea.

- [x] **Step 3: 运行 RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_diverge_artifact_data_skips_sources_with_unknown_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_rejects_unknown_recommended_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_rejects_invalid_ice_score tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_skips_validation_experiments_with_unknown_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_skips_merge_paths_with_unknown_idea_reference -q
```

Expected before implementation: tests fail because current partial renderer previews invalid referenced sections.

### Task 2: 抽取共享校验 helper 并接入 partial renderer

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [x] **Step 1: Extract DIVERGE reference helpers**

Create helpers for idea id uniqueness, landscape references, source id uniqueness, and source references. Use them from both `IdeaDivergeArtifactData.validate_idea_diverge_consistency()` and `render_partial_idea_brainstorm_diverge_markdown()`.

- [x] **Step 2: Extract CONVERGE reference helpers**

Create helpers for ICE evaluation consistency, decision matrix references, recommended idea alignment, validation experiment references, and merge path references. Use them from both `IdeaConvergeArtifactData.validate_idea_converge_consistency()` and `render_partial_idea_brainstorm_converge_markdown()`.

- [x] **Step 3: Preserve partial behavior**

DIVERGE should return previously trusted sections when a later section is invalid. CONVERGE should return `None` when the initial decision matrix + ICE evaluations are inconsistent, and should return previous sections for invalid later experiment / merge path sections.

### Task 3: GREEN 和聚焦回归

**Files:**
- Test: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Test: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [x] **Step 1: Run focused GREEN**

Run the RED command again.

Expected: all new tests pass.

- [x] **Step 2: Run IDEA focused regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_diverge_artifact_data_rejects_duplicate_idea_id tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_diverge_artifact_data_rejects_unknown_source_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_diverge_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_converge_artifact_data_rejects_invalid_ice_score tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_converge_artifact_data_rejects_unknown_recommended_idea tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_converge_artifact_data_rejects_unknown_validation_experiment_idea tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_converge_artifact_data_rejects_unknown_merge_path_idea tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output -q
```

Expected: all selected IDEA tests pass.

- [x] **Step 3: Run backend regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: backend regression passes.

### Task 4: 更新 todo、验证、提交

**Files:**
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- Modify: this plan

- [x] **Step 1: Update todo execution record**

Record RED/GREEN, focused regression, any skipped full automation, and remaining risks.

- [x] **Step 2: Run final checks**

Run `git diff --check`, stage only this slice, then `git diff --cached --check`.

- [x] **Step 3: Commit and push**

Create a focused commit and push if verification passes.
