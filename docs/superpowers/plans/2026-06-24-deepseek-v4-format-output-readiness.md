# DeepSeek V4 Format Output Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local readiness gate proving every online New Agents workflow stage keeps DeepSeek V4 formatting responsibilities in backend `artifact_data` renderers rather than model-generated Markdown/Mermaid.

**Architecture:** Reuse the shared Agent Runtime, `json_object_only` DeepSeek capability, existing `artifact_data` renderer registry, `AgentTurnOutput`, and artifact contract validation. Add matrix tests in the existing backend runtime test suite, then mark the DeepSeek V4 structured artifact todo as completed with explicit real-smoke caveats.

**Tech Stack:** Python 3.11, pytest, Pydantic models, existing Flask/New Agents backend test helpers.

---

## File Structure

- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
  - Add an all-stage readiness matrix and tests for support registry, structured instructions, retry prompts, deterministic renderer output, and DeepSeek capability settings.
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
  - Mark the DeepSeek V4 format-output migration completed locally and record readiness gate evidence.
- Modify: `docs/todos/refactor/README.md`
  - Update active todo entry so DeepSeek V4 is no longer treated as an unfinished stage-migration pool.
- Modify: `docs/superpowers/plans/2026-06-24-deepseek-v4-format-output-readiness.md`
  - Track executed steps and verification evidence.

## Task 1: Backend Readiness Gate RED/GREEN

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [x] **Step 1: Add failing readiness matrix tests**

Add imports:

```python
from agent_contracts import WORKFLOW_STAGES, validate_agent_turn
from artifact_data_renderers import render_agent_turn_from_artifact_data
from agent_runtime import supports_artifact_data_rendering
```

Add the matrix near the artifact data fixtures:

```python
DEEPSEEK_FORMAT_STAGE_FIXTURES = {
    ("TEST_DESIGN", "CLARIFY"): VALID_CLARIFY_ARTIFACT_DATA,
    ("TEST_DESIGN", "STRATEGY"): VALID_STRATEGY_ARTIFACT_DATA,
    ("TEST_DESIGN", "CASES"): VALID_CASES_ARTIFACT_DATA,
    ("TEST_DESIGN", "DELIVERY"): VALID_DELIVERY_ARTIFACT_DATA,
    ("REQ_REVIEW", "REVIEW"): VALID_REQ_REVIEW_ARTIFACT_DATA,
    ("REQ_REVIEW", "REPORT"): VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
    ("VALUE_DISCOVERY", "ELEVATOR"): VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
    ("VALUE_DISCOVERY", "PERSONA"): VALID_VALUE_PERSONA_ARTIFACT_DATA,
    ("VALUE_DISCOVERY", "JOURNEY"): VALID_VALUE_JOURNEY_ARTIFACT_DATA,
    ("VALUE_DISCOVERY", "BLUEPRINT"): VALID_VALUE_BLUEPRINT_ARTIFACT_DATA,
    ("INCIDENT_REVIEW", "TIMELINE"): VALID_INCIDENT_TIMELINE_ARTIFACT_DATA,
    ("INCIDENT_REVIEW", "ROOT_CAUSE"): VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA,
    ("INCIDENT_REVIEW", "IMPROVEMENT"): VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA,
    ("IDEA_BRAINSTORM", "DEFINE"): VALID_IDEA_DEFINE_ARTIFACT_DATA,
    ("IDEA_BRAINSTORM", "DIVERGE"): VALID_IDEA_DIVERGE_ARTIFACT_DATA,
    ("IDEA_BRAINSTORM", "CONVERGE"): VALID_IDEA_CONVERGE_ARTIFACT_DATA,
    ("IDEA_BRAINSTORM", "CONCEPT"): VALID_IDEA_CONCEPT_ARTIFACT_DATA,
}
```

Add tests:

```python
def test_deepseek_format_readiness_covers_every_online_stage():
    online_stages = {
        (workflow_id, stage_id)
        for workflow_id, stages in WORKFLOW_STAGES.items()
        for stage_id in stages
    }

    assert set(DEEPSEEK_FORMAT_STAGE_FIXTURES) == online_stages


DEEPSEEK_FORMAT_STAGE_CASES = [
    (workflow_id, stage_id, artifact_data)
    for (workflow_id, stage_id), artifact_data
    in sorted(DEEPSEEK_FORMAT_STAGE_FIXTURES.items())
]


@pytest.mark.parametrize(
    ("workflow_id", "stage_id", "artifact_data"),
    DEEPSEEK_FORMAT_STAGE_CASES,
)
def test_deepseek_format_readiness_uses_artifact_data_instructions(
    workflow_id,
    stage_id,
    artifact_data,
):
    instruction = build_structured_output_instruction(workflow_id, stage_id)
    retry_prompt = build_raw_json_retry_prompt(
        "请生成当前阶段产出物",
        ValueError("artifact_data.document_info 缺失"),
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )

    assert supports_artifact_data_rendering(workflow_id, stage_id)
    assert "artifact_data" in instruction
    assert "artifact_update.markdown" not in instruction
    assert "不要输出完整 Markdown" in instruction
    assert "后端会负责确定性渲染" in instruction
    assert "必须修正上述 artifact_data 数据问题" in retry_prompt
    assert "后端会根据 artifact_data 渲染右侧产出物" in retry_prompt
    assert "artifact_update.type 必须为 replace" not in retry_prompt


@pytest.mark.parametrize(
    ("workflow_id", "stage_id", "artifact_data"),
    DEEPSEEK_FORMAT_STAGE_CASES,
)
def test_deepseek_format_readiness_renderers_pass_artifact_contract(
    workflow_id,
    stage_id,
    artifact_data,
):
    output = render_agent_turn_from_artifact_data(
        {
            "chat": "我已按结构化数据生成当前阶段产出物，请查看右侧文档。",
            "artifact_data": artifact_data,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )

    assert output is not None
    assert output.artifact_update.type == "replace"
    validate_agent_turn(output, workflow_id=workflow_id, current_stage_id=stage_id)
```

- [x] **Step 2: Run test to verify RED or current gap**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q
```

Actual: PASS, `120 passed in 0.63s`. The current production code already satisfies the new readiness gate, so no production runtime change was needed.

- [x] **Step 3: Implement minimal production fix only if RED exposes a real gap**

If the test fails because a workflow/stage lacks `artifact_data` support, update only the missing branch in:

```python
def supports_artifact_data_rendering(workflow_id: str, current_stage_id: str) -> bool:
    return (workflow_id, current_stage_id) in {
        # add the missing tuple here
    }
```

If it fails because `build_structured_output_instruction()` returns `TEXT_STRUCTURED_OUTPUT_INSTRUCTION` for an online stage, add the missing stage-specific branch using the existing instruction constant for that stage. If it fails because renderer output violates artifact contract, fix the corresponding renderer in `artifact_data_renderers.py` so it emits the required headings or visuals.

Actual: skipped production changes because the new readiness gate passed against existing runtime and renderer code.

- [x] **Step 4: Run test to verify GREEN**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q
```

Expected: all runtime tests pass.

Actual: PASS, `120 passed in 0.63s`.

## Task 2: Todo Closure Records

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/superpowers/plans/2026-06-24-deepseek-v4-format-output-readiness.md`

- [x] **Step 1: Update DeepSeek todo status**

Set the DeepSeek todo status to completed locally and add a completion record:

```markdown
> 状态: 本地确定性改造已完成；真实 DeepSeek V4 Flash smoke 仍需显式凭证、网络和额度
```

Add a `完成记录` section describing:

- all 17 online stages covered by `artifact_data`;
- readiness gate proves support registry, instructions, retry prompt, renderer, and artifact contract;
- real DeepSeek smoke remains optional and externally gated.

- [x] **Step 2: Update refactor README**

In `docs/todos/refactor/README.md`, keep `2026-06-23-new-agents-enhancement-diagnostic.md` as active, but move DeepSeek V4 from active stage migration to completed/readiness evidence. Use wording that future rounds should not restart per-stage migration unless CGA finds a new regression.

- [x] **Step 3: Update this plan checklist**

Mark completed steps and record exact verification commands under the verification section.

## Task 3: Verification and Commit

**Files:**
- Modify: `docs/superpowers/plans/2026-06-24-deepseek-v4-format-output-readiness.md`

- [x] **Step 1: Run focused backend verification**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_contracts.py -q
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py
git diff --check
```

Expected: all commands exit 0.

Actual:

- `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q`: 120 passed.
- `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_contracts.py -q`: 160 passed.
- `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py`: passed.
- `git diff --check`: passed.

- [x] **Step 2: Review scope**

Run:

```bash
git status --short
git diff --stat
```

Expected: only runtime tests, DeepSeek todo docs, spec, and plan are changed unless Task 1 uncovered a production bug.

Actual: only runtime readiness tests, DeepSeek todo docs, spec, and plan changed; no production runtime code changed.

- [x] **Step 3: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-06-24-deepseek-v4-format-output-readiness-design.md docs/superpowers/plans/2026-06-24-deepseek-v4-format-output-readiness.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md docs/todos/refactor/README.md tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py
git commit -m "test(new-agents): 补齐 DeepSeek 格式化输出门禁"
```

If `agent_runtime.py` and `artifact_data_renderers.py` are unchanged, omit them from `git add`.

## Self-Review

- Spec coverage: tasks cover readiness matrix, instruction/retry assertions, renderer contract validation, todo closure, verification, and commit.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: function names and imports match current backend modules.
