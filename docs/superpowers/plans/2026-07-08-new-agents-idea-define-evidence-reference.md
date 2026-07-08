# New Agents IDEA DEFINE Evidence Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize `IDEA_BRAINSTORM/DEFINE` root-problem evidence coverage by replacing fragile exact-text coverage with strict problem/evidence ID references.

**Architecture:** Keep the shared Agent Runtime and deterministic renderer. Add root/subproblem ID references to the existing DEFINE artifact_data schema, validate the reference graph in Pydantic, render IDs in the existing Markdown artifact, and update the structured output instruction plus regression tests.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing New Agents backend artifact_data renderer and Agent Runtime.

---

### Task 1: Add RED Tests For ID-Based Root Coverage

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [ ] **Step 1: Write failing schema tests**

Add tests proving `IDEA_BRAINSTORM/DEFINE` can pass without exact root text copying when ID references are valid, and fails when problem IDs are unknown or root coverage is missing:

```python
def test_idea_define_artifact_data_accepts_id_based_root_problem_coverage_without_exact_text_copy():
    payload = copy.deepcopy(VALID_IDEA_DEFINE_ARTIFACT_DATA)
    payload["problem_landscape"]["root_problem_id"] = "P-ROOT"
    payload["evidence_items"][0]["related_problem"] = "方向优先级和投入判断"
    payload["evidence_items"][0]["related_problem_ids"] = ["P-ROOT"]
    payload["problem_user_fit"][0]["evidence_or_assumption"] = "受访者提到方向筛选焦虑"
    payload["problem_user_fit"][0]["evidence_ids"] = ["EV-001"]

    result = IdeaDefineArtifactData.model_validate(payload)

    assert result.problem_landscape.root_problem == "独立开发者变现方向选择困难"
    assert result.evidence_items[0].related_problem_ids == ["P-ROOT"]
```

```python
def test_idea_define_artifact_data_rejects_unknown_related_problem_reference():
    payload = copy.deepcopy(VALID_IDEA_DEFINE_ARTIFACT_DATA)
    payload["evidence_items"][0]["related_problem_ids"] = ["P-404"]

    with pytest.raises(ValidationError, match="unknown problem ids"):
        IdeaDefineArtifactData.model_validate(payload)
```

```python
def test_idea_define_artifact_data_requires_root_problem_id_coverage():
    payload = copy.deepcopy(VALID_IDEA_DEFINE_ARTIFACT_DATA)
    payload["evidence_items"][0]["related_problem_ids"] = ["P-001"]
    payload["problem_user_fit"][0]["evidence_ids"] = ["EV-001"]

    with pytest.raises(ValidationError, match="root_problem_id"):
        IdeaDefineArtifactData.model_validate(payload)
```

- [ ] **Step 2: Write failing prompt/runtime tests**

Add or update tests proving the structured output instruction now asks for `root_problem_id` and `related_problem_ids`, and no longer asks for exact root text copying:

```python
def test_idea_define_structured_output_instruction_uses_problem_ids_for_root_coverage():
    instruction = build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "DEFINE",
    )

    assert "root_problem_id" in instruction
    assert "related_problem_ids" in instruction
    assert "原样包含 problem_landscape.root_problem" not in instruction
```

- [ ] **Step 3: Run RED verification**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_accepts_id_based_root_problem_coverage_without_exact_text_copy tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_rejects_unknown_related_problem_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_idea_define_artifact_data_requires_root_problem_id_coverage tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_define_structured_output_instruction_uses_problem_ids_for_root_coverage -q
```

Expected before implementation: at least the new ID-based acceptance test and prompt test fail because `root_problem_id` / `related_problem_ids` are not part of the schema or instruction.

### Task 2: Implement DEFINE Reference Graph Validation

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] **Step 1: Add schema fields**

Update `IdeaProblemLandscape` and `IdeaEvidenceItem`:

```python
class IdeaProblemLandscape(StrictArtifactDataModel):
    root_problem_id: str
    root_problem: str
    subproblems: list[IdeaSubproblem] = Field(min_length=1)


class IdeaEvidenceItem(StrictArtifactDataModel):
    evidence_id: str
    related_problem: str
    related_problem_ids: list[str] = Field(min_length=1)
    source: str
    evidence_level: str
    validation_action: str
    owner: str
    validation_status: str
```

- [ ] **Step 2: Replace exact-text validator with ID graph validator**

In `IdeaDefineArtifactData.validate_idea_define_consistency`, compute known problem IDs from `root_problem_id` plus subproblem IDs, reject duplicates and unknown references, require root coverage through evidence, then require at least one problem-user-fit row to cite evidence that covers root:

```python
root_problem_id = self.problem_landscape.root_problem_id
problem_ids = {item.problem_id for item in self.problem_landscape.subproblems}
if root_problem_id in problem_ids:
    raise ValueError("problem_landscape.root_problem_id duplicates subproblem problem_id")

known_problem_ids = {root_problem_id, *problem_ids}
unknown_problem_ids = sorted(
    {
        problem_id
        for item in self.evidence_items
        for problem_id in item.related_problem_ids
        if problem_id not in known_problem_ids
    }
)
if unknown_problem_ids:
    raise ValueError(
        "evidence_items references unknown problem ids: "
        + ", ".join(unknown_problem_ids)
    )

root_evidence_ids = {
    item.evidence_id
    for item in self.evidence_items
    if root_problem_id in item.related_problem_ids
}
if not root_evidence_ids:
    raise ValueError("problem_landscape.root_problem_id must be covered by evidence_items")

fit_root_evidence_ids = {
    evidence_id
    for item in self.problem_user_fit
    for evidence_id in item.evidence_ids
    if evidence_id in root_evidence_ids
}
if not fit_root_evidence_ids:
    raise ValueError(
        "problem_user_fit must reference evidence covering problem_landscape.root_problem_id"
    )
```

- [ ] **Step 3: Keep existing strict failures**

Do not remove duplicate evidence ID, duplicate subproblem ID, unknown evidence ID, or stage gate validation.

### Task 3: Render Stable Problem IDs

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`

- [ ] **Step 1: Render root problem row**

Update `_render_idea_problem_landscape` so the table includes the root problem before subproblems:

```python
rows = [
    (landscape.root_problem_id, "根问题", landscape.root_problem, "-"),
    *[
        (item.problem_id, "子问题", item.problem, "、".join(item.symptoms))
        for item in landscape.subproblems
    ],
]
return (
    "## 问题域全景\n"
    + "\n".join(lines)
    + "\n\n"
    + _markdown_table(["问题 ID", "类型", "问题", "表现"], rows)
)
```

- [ ] **Step 2: Render related problem IDs in evidence table**

Update `_render_idea_evidence_items` rows and headers:

```python
(
    item.evidence_id,
    ", ".join(item.related_problem_ids),
    item.related_problem,
    item.source,
    item.evidence_level,
    item.validation_action,
    item.owner,
    item.validation_status,
)
```

Header becomes:

```python
[
    "证据 ID",
    "关联问题 ID",
    "关联问题",
    "证据来源",
    "证据等级",
    "验证动作",
    "owner",
    "验证状态",
]
```

- [ ] **Step 3: Update deterministic render assertions**

Assert final DEFINE Markdown contains `P-ROOT` and `关联问题 ID`.

### Task 4: Update Runtime Instruction And Fixtures

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [ ] **Step 1: Update valid fixture**

Add `root_problem_id` to `VALID_IDEA_DEFINE_ARTIFACT_DATA["problem_landscape"]` and `related_problem_ids` to each evidence item.

- [ ] **Step 2: Update structured output instruction**

Update the example shape in `IDEA_DEFINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`:

```json
"problem_landscape": {"root_problem_id": "P-ROOT", "root_problem": "...", "subproblems": [{"problem_id": "P-001", "problem": "...", "symptoms": ["..."]}]},
"evidence_items": [{"evidence_id": "EV-001", "related_problem": "...", "related_problem_ids": ["P-ROOT"], "source": "用户访谈/数据/社区讨论/类比案例/AI 假设", "evidence_level": "事实证据/用户陈述/合理推断/待验证", "validation_action": "...", "owner": "产品/用户研究/业务/用户确认", "validation_status": "已验证/部分验证/待验证"}],
```

Replace the exact-copy rule with:

```text
problem_landscape.root_problem_id 必须唯一且不能与 subproblems.problem_id 重复；evidence_items.related_problem_ids 只能引用 root_problem_id 或已存在的 subproblems.problem_id；至少一个 evidence_items.related_problem_ids 必须包含 root_problem_id；problem_user_fit.evidence_ids 必须至少引用一条支撑 root_problem_id 的 evidence。
```

- [ ] **Step 3: Run focused GREEN verification**

Run the RED command again. Expected: all selected tests pass.

### Task 5: Regression, Docs, Commit, Push

**Files:**
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- Modify: this plan and matching spec only for execution evidence.

- [ ] **Step 1: Run focused backend regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: pass.

- [ ] **Step 2: Run New Agents local verification**

Run:

```bash
./scripts/test/test-local.sh new-agents
```

Expected: pass, with only known non-fatal React `act(...)` warnings if they appear.

- [ ] **Step 3: Run full local automation before commit**

Run:

```bash
./scripts/test/test-local.sh all
```

Expected: pass. If sandbox blocks MidScene or Playwright, rerun with approved escalation and record both attempts.

- [ ] **Step 4: Update todo execution record**

Record RED/GREEN, focused regression, New Agents verification, full local verification, residual risks, and that DeepSeek tool calling spike remains open.

- [ ] **Step 5: Commit and push focused files**

Stage only this slice:

```bash
git add docs/superpowers/specs/2026-07-08-new-agents-idea-define-evidence-reference-design.md docs/superpowers/plans/2026-07-08-new-agents-idea-define-evidence-reference.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
git commit -m "fix(new-agents): 稳定Alex问题域证据引用"
git push
```

Expected: branch `codex/structured-failure-diagnostics` pushed to GitHub with `HEAD == origin/codex/structured-failure-diagnostics`.

## Self-Review

- Spec coverage: plan covers schema, validator, rendering, instruction, RED/GREEN tests, regression, todo record, commit and push.
- Red-flag scan: no deferred implementation markers or deferred implementation steps.
- Type consistency: field names are `root_problem_id` and `related_problem_ids` consistently across schema, prompt, tests, and renderer.
