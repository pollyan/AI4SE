# New Agents Artifact Data Regression Fixture Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 建立第 8A 轮全阶段 `artifact_data` 回归门禁，让所有在线 artifact-data 阶段的固定 fixture、renderer contract、runtime instruction 矩阵和 manifest visual contract 同步关系都有可失败测试保护。

**Architecture:** 在后端测试层新增 `ARTIFACT_DATA_STAGE_FIXTURES` 单一登记表，覆盖 `supports_artifact_data_rendering()` 支持的全部 stage key。`test_agent_runtime.py` 的 artifact-data instruction 参数从该 registry 派生，`test_workflow_contract_sync.py` 反向比对 manifest `visualContract` 与后端 required visual maps。生产 runtime 不变。

**Tech Stack:** Python 3.12 test suite, pytest, Pydantic renderer models, New Agents shared workflow manifest.

---

## Files

- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
  - Add `ARTIFACT_DATA_STAGE_FIXTURES`.
  - Add registry coverage and contract-valid rendering tests.
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
  - Import `ARTIFACT_DATA_STAGE_FIXTURES`.
  - Derive `ARTIFACT_DATA_STREAMING_STAGES` from registry keys.
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
  - Add manifest visual contract extraction helper.
  - Add reverse sync test for backend required Mermaid / structured visual maps.
- Modify: `docs/TESTING.md`
  - Document the fixture registry and visual contract sync tests as第 8 轮全工作流门禁入口.
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
  - Record第 8A 轮 completion evidence and residual risks.

## Task 1: Add RED Fixture Registry Tests

- [x] **Step 1: Add imports for runtime support check**

In `tools/new-agents/backend/tests/test_artifact_data_renderers.py`, update imports:

```python
from agent_contracts import WORKFLOW_STAGES, validate_agent_turn
from agent_runtime import supports_artifact_data_rendering
```

- [x] **Step 2: Add failing registry tests near the bottom after valid user story fixtures**

Add these tests after `VALID_USER_STORY_HANDOFF_ARTIFACT_DATA` and before the existing `test_render_user_story_breakdown_artifact_data_is_deterministic_and_contract_valid` parameterized test:

```python
def _runtime_supported_artifact_data_stage_keys() -> set[tuple[str, str]]:
    return {
        (workflow_id, stage_id)
        for workflow_id, stage_ids in WORKFLOW_STAGES.items()
        for stage_id in stage_ids
        if supports_artifact_data_rendering(workflow_id, stage_id)
    }


def test_artifact_data_stage_fixture_registry_covers_runtime_supported_stages():
    fixture_stage_keys = set(ARTIFACT_DATA_STAGE_FIXTURES)
    runtime_stage_keys = _runtime_supported_artifact_data_stage_keys()

    assert fixture_stage_keys == runtime_stage_keys


@pytest.mark.parametrize(
    ("workflow_id", "stage_id", "artifact_data"),
    [
        (workflow_id, stage_id, fixture["artifact_data"])
        for (workflow_id, stage_id), fixture in sorted(
            ARTIFACT_DATA_STAGE_FIXTURES.items()
        )
    ],
)
def test_artifact_data_stage_fixture_registry_renders_contract_valid_outputs(
    workflow_id,
    stage_id,
    artifact_data,
):
    output = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成当前阶段产出物，请查看右侧文档。",
            "artifact_data": artifact_data,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )

    assert output is not None
    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown
    assert output.artifact_data == artifact_data
    assert validate_agent_turn(
        output,
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    ) == output
```

- [x] **Step 3: Run RED verification**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_covers_runtime_supported_stages tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_renders_contract_valid_outputs -q
```

Expected: FAIL with `NameError: name 'ARTIFACT_DATA_STAGE_FIXTURES' is not defined`.

## Task 2: Implement Fixture Registry

- [x] **Step 1: Add `ARTIFACT_DATA_STAGE_FIXTURES`**

In `tools/new-agents/backend/tests/test_artifact_data_renderers.py`, after `VALID_USER_STORY_HANDOFF_ARTIFACT_DATA`, add:

```python
ARTIFACT_DATA_STAGE_FIXTURES = {
    ("TEST_DESIGN", "CLARIFY"): {
        "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
    },
    ("TEST_DESIGN", "STRATEGY"): {
        "artifact_data": VALID_STRATEGY_ARTIFACT_DATA,
    },
    ("TEST_DESIGN", "CASES"): {
        "artifact_data": VALID_CASES_ARTIFACT_DATA,
    },
    ("TEST_DESIGN", "DELIVERY"): {
        "artifact_data": VALID_DELIVERY_ARTIFACT_DATA,
    },
    ("REQ_REVIEW", "REVIEW"): {
        "artifact_data": VALID_REQ_REVIEW_ARTIFACT_DATA,
    },
    ("REQ_REVIEW", "REPORT"): {
        "artifact_data": VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
    },
    ("INCIDENT_REVIEW", "TIMELINE"): {
        "artifact_data": VALID_INCIDENT_TIMELINE_ARTIFACT_DATA,
    },
    ("INCIDENT_REVIEW", "ROOT_CAUSE"): {
        "artifact_data": VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA,
    },
    ("INCIDENT_REVIEW", "IMPROVEMENT"): {
        "artifact_data": VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA,
    },
    ("IDEA_BRAINSTORM", "DEFINE"): {
        "artifact_data": VALID_IDEA_DEFINE_ARTIFACT_DATA,
    },
    ("IDEA_BRAINSTORM", "DIVERGE"): {
        "artifact_data": VALID_IDEA_DIVERGE_ARTIFACT_DATA,
    },
    ("IDEA_BRAINSTORM", "CONVERGE"): {
        "artifact_data": VALID_IDEA_CONVERGE_ARTIFACT_DATA,
    },
    ("IDEA_BRAINSTORM", "CONCEPT"): {
        "artifact_data": VALID_IDEA_CONCEPT_ARTIFACT_DATA,
    },
    ("VALUE_DISCOVERY", "ELEVATOR"): {
        "artifact_data": VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
    },
    ("VALUE_DISCOVERY", "PERSONA"): {
        "artifact_data": VALID_VALUE_PERSONA_ARTIFACT_DATA,
    },
    ("VALUE_DISCOVERY", "JOURNEY"): {
        "artifact_data": VALID_VALUE_JOURNEY_ARTIFACT_DATA,
    },
    ("VALUE_DISCOVERY", "BLUEPRINT"): {
        "artifact_data": VALID_VALUE_BLUEPRINT_ARTIFACT_DATA,
    },
    ("USER_STORY_BREAKDOWN", "SCOPE"): {
        "artifact_data": VALID_USER_STORY_SCOPE_ARTIFACT_DATA,
    },
    ("USER_STORY_BREAKDOWN", "STORY_MAP"): {
        "artifact_data": VALID_USER_STORY_MAP_ARTIFACT_DATA,
    },
    ("USER_STORY_BREAKDOWN", "STORIES"): {
        "artifact_data": VALID_USER_STORIES_ARTIFACT_DATA,
    },
    ("USER_STORY_BREAKDOWN", "HANDOFF"): {
        "artifact_data": VALID_USER_STORY_HANDOFF_ARTIFACT_DATA,
    },
}
```

- [x] **Step 2: Run GREEN verification for registry tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_covers_runtime_supported_stages tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_renders_contract_valid_outputs -q
```

Expected: PASS, 22 tests total: one coverage test plus 21 parameterized stage fixture tests.

## Task 3: Derive Runtime Stage Matrix From Registry

- [x] **Step 1: Import registry in `test_agent_runtime.py`**

Update the `from test_artifact_data_renderers import (...)` block to include:

```python
    ARTIFACT_DATA_STAGE_FIXTURES,
```

- [x] **Step 2: Replace hand-written streaming stage list**

Replace the current `ARTIFACT_DATA_STREAMING_STAGES = [...]` with:

```python
ARTIFACT_DATA_STREAMING_STAGES = sorted(ARTIFACT_DATA_STAGE_FIXTURES)
```

- [x] **Step 3: Run focused runtime instruction test**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming -q
```

Expected: PASS with 21 parameterized cases.

## Task 4: Add Manifest Visual Contract Reverse Sync Test

- [x] **Step 1: Add helper to `test_workflow_contract_sync.py`**

After `_workflow_manifest()`, add:

```python
def _workflow_manifest_visual_contracts(field_name: str) -> dict[tuple[str, str], list[str]]:
    manifest = _workflow_manifest()
    result: dict[tuple[str, str], list[str]] = {}
    for workflow_id, workflow in manifest["workflows"].items():
        for stage in workflow["stages"]:
            visual_contract = stage.get("visualContract") or {}
            values = visual_contract.get(field_name) or []
            if values:
                result[(workflow_id, stage["id"])] = values
    return result
```

- [x] **Step 2: Add sync test**

After `test_shared_workflow_manifest_stage_keys_match_required_artifact_contracts`, add:

```python
def test_shared_workflow_manifest_visual_contract_matches_backend_required_visuals():
    assert (
        _workflow_manifest_visual_contracts("requiredMermaidDiagrams")
        == REQUIRED_ARTIFACT_MERMAID_DIAGRAMS
    )
    assert (
        _workflow_manifest_visual_contracts("requiredStructuredVisuals")
        == REQUIRED_ARTIFACT_STRUCTURED_VISUALS
    )
```

- [x] **Step 3: Run focused visual sync test**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_shared_workflow_manifest_visual_contract_matches_backend_required_visuals -q
```

Expected: PASS if manifest and backend maps are currently synchronized; FAIL if drift exists, then inspect the diff and update the stale side only if the current source of truth is clear.

## Task 5: Update Documentation Records

- [x] **Step 1: Update `docs/TESTING.md`**

In the New Agents partial artifact / contract section near the 21-stage matrix, add a short paragraph:

```markdown
第 8 轮全工作流回归门禁新增 `ARTIFACT_DATA_STAGE_FIXTURES` 测试登记表：所有 `supports_artifact_data_rendering()` 支持的在线阶段都必须在该 registry 中有固定 `artifact_data` 样例；registry 样例必须能通过 deterministic renderer 和 `validate_agent_turn()`。`test_agent_runtime.py` 的 artifact-data instruction 顺序矩阵从该 registry 派生，避免新增阶段时漏掉 raw JSON visible streaming 门禁。`test_workflow_contract_sync.py` 同时反向校验 `workflow_manifest.json` 的 `visualContract` 与后端 required Mermaid / structured visual maps 完全一致。
```

- [x] **Step 2: Update todo**

In `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`:

- Update status line to mention “第 8A 轮 artifact_data fixture registry 回归门禁已完成”.
- Under “增加结构化失败回归门禁”, add progress note that all runtime-supported artifact-data stages now have registry fixtures.
- Add execution record “2026-07-08 第 8A 轮：artifact_data 全阶段 fixture registry 回归门禁”.

Include RED, GREEN, batch verification, residual risks:

```markdown
残余风险：
- 本轮不迁移 20 个阶段的 `artifactDataContract` 到 manifest。
- 本轮不增加 backend Mermaid JS parse 或 `mmdc` 渲染门禁。
- 模型输出字段 / 后端派生字段 / 视觉协议来源的完整全阶段矩阵仍属第 8 轮后续文档收口候选。
```

- [x] **Step 3: Run docs check**

Run:

```bash
git diff --check -- docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/superpowers/specs/2026-07-08-new-agents-artifact-data-regression-fixture-registry-design.md docs/superpowers/plans/2026-07-08-new-agents-artifact-data-regression-fixture-registry.md
```

Expected: no output.

Run:

```bash
rg -n "T[B]D|T[O]DO|implement[ ]later|<填[入]|待[补]" docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/superpowers/specs/2026-07-08-new-agents-artifact-data-regression-fixture-registry-design.md docs/superpowers/plans/2026-07-08-new-agents-artifact-data-regression-fixture-registry.md
```

Expected: exit code 1 and no matches.

## Task 6: Verification, Commit, Push

- [x] **Step 1: Run backend focused regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_covers_runtime_supported_stages tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_renders_contract_valid_outputs tools/new-agents/backend/tests/test_agent_runtime.py::test_artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_shared_workflow_manifest_visual_contract_matches_backend_required_visuals -q
```

Expected: PASS.

- [x] **Step 2: Run related backend suite**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

Expected: PASS.

- [x] **Step 3: Run New Agents batch verification**

Run:

```bash
./scripts/test/test-local.sh new-agents
```

Expected: New Agents frontend and backend pass.

- [x] **Step 4: Run full local automation before commit**

Run:

```bash
./scripts/test/test-local.sh all
```

Expected: exit code 0. If sandbox blocks port or Chromium permissions, rerun non-sandbox and record the sandbox failure separately.

- [x] **Step 5: Commit ownership check**

Run:

```bash
git status -sb
git diff --shortstat
git diff --cached --name-only
```

Expected: only this slice files staged.

- [x] **Step 6: Commit and push**

Run:

```bash
git add tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/superpowers/specs/2026-07-08-new-agents-artifact-data-regression-fixture-registry-design.md docs/superpowers/plans/2026-07-08-new-agents-artifact-data-regression-fixture-registry.md
git commit -m "test(new-agents): 增加 artifact data 全阶段回归门禁"
git push
```

Expected: commit and push succeed on `codex/structured-failure-diagnostics`.
