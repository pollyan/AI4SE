# Alex PRD 质量评审与补全 Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Alex `PRD_REVIEW` 做成共享 Agent Runtime 上的在线 workflow，覆盖 manifest、前端入口、prompt/template、后端 contract、artifact_data renderer 和最小验证。

**Architecture:** 所有新增能力通过共享 `workflow_manifest.json`、前端 `WORKFLOWS` registry、后端 `WORKFLOW_STAGES` / artifact contract、共享 Agent Runtime structured output instruction 和 `artifact_data_renderers.py` dispatch 接入。PRD 差异只表现为 workflow 配置、阶段 prompt/template、Pydantic schema 与 renderer 分支，不新增 Alex 专属 runtime、API、store 或 UI renderer。

**Tech Stack:** Python 3.11+/Pydantic/pytest，TypeScript 5.x/React/Vitest，New Agents typed SSE 和 manifest-driven workflow registry。

---

## 文件结构

- Modify: `tools/new-agents/workflow_manifest.json`，新增 `PRD_REVIEW` manifest、stages、artifact/visual contract。
- Modify: `tools/new-agents/frontend/src/core/types.ts`，把 `PRD_REVIEW` 加入 `WorkflowType`。
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`，注册 PRD Review prompt/template module。
- Create: `tools/new-agents/frontend/src/core/prompts/prd_review/inventory.ts`。
- Create: `tools/new-agents/frontend/src/core/prompts/prd_review/quality_audit.ts`。
- Create: `tools/new-agents/frontend/src/core/prompts/prd_review/completion_plan.ts`。
- Create: `tools/new-agents/frontend/src/core/prompts/prd_review/revision_blueprint.ts`。
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`，新增 Alex 在线 workflow 验收。
- Modify: `tools/new-agents/backend/agent_contracts.py`，新增 `PRD_REVIEW` stages、headings、structured visual requirements。
- Modify: `tools/new-agents/backend/agent_runtime.py`，新增 PRD Review `artifact_data` structured output instruction、readiness stage 和 dispatch。
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`，新增 PRD Review schema、validators 和 deterministic renderer。
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`，新增 PRD Review schema/renderer tests。
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`，新增 runtime parse/instruction tests。
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`，新增 prompt file sync mapping。
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`，记录 E14 消化结果。
- Modify: `docs/todos/refactor/README.md`，保持活跃入口与实际候选一致。

## Task 1: RED - 后端 artifact_data contract tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`

- [ ] **Step 1: Write failing tests**

Add a valid PRD Review fixture and tests that import `PrdReviewArtifactData`, call `render_agent_turn_from_artifact_data`, and validate every stage:

```python
from artifact_data_renderers import PrdReviewArtifactData


def test_prd_review_artifact_data_rejects_unknown_finding_reference() -> None:
    invalid = copy.deepcopy(VALID_PRD_REVIEW_ARTIFACT_DATA)
    invalid["completion_actions"][0]["finding_ids"] = ["F-404"]

    with pytest.raises(ValueError, match="unknown finding_id"):
        PrdReviewArtifactData.model_validate(invalid)


def test_prd_review_artifact_data_rejects_unknown_section_reference() -> None:
    invalid = copy.deepcopy(VALID_PRD_REVIEW_ARTIFACT_DATA)
    invalid["acceptance_criteria"][0]["related_section_ids"] = ["SEC-404"]

    with pytest.raises(ValueError, match="unknown section_id"):
        PrdReviewArtifactData.model_validate(invalid)


def test_prd_review_artifact_data_requires_stage_gate_checked() -> None:
    invalid = copy.deepcopy(VALID_PRD_REVIEW_ARTIFACT_DATA)
    invalid["stage_gate"] = [{"checked": False, "item": "PRD 仍缺少业务目标"}]

    with pytest.raises(ValueError, match="stage_gate"):
        PrdReviewArtifactData.model_validate(invalid)


@pytest.mark.parametrize(
    "stage_id, expected_title",
    [
        ("INVENTORY", "# PRD 输入盘点"),
        ("QUALITY_AUDIT", "# PRD 质量评审"),
        ("COMPLETION_PLAN", "# PRD 补全建议"),
        ("REVISION_BLUEPRINT", "# PRD 修订蓝图"),
    ],
)
def test_render_prd_review_artifact_data_is_deterministic_and_contract_valid(
    stage_id: str,
    expected_title: str,
) -> None:
    output = {
        "chat": "我已完成 PRD 质量评审数据整理，并生成可复审的修订建议。",
        "artifact_data": VALID_PRD_REVIEW_ARTIFACT_DATA,
        "stage_action": None,
        "warnings": [],
    }

    first = render_agent_turn_from_artifact_data(
        output,
        workflow_id="PRD_REVIEW",
        current_stage_id=stage_id,
    )
    second = render_agent_turn_from_artifact_data(
        output,
        workflow_id="PRD_REVIEW",
        current_stage_id=stage_id,
    )

    assert first.artifact == second.artifact
    assert expected_title in first.artifact
    validate_agent_turn(
        first.artifact,
        workflow_id="PRD_REVIEW",
        current_stage_id=stage_id,
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k "prd_review"
```

Expected: FAIL or collection error because `PrdReviewArtifactData` and renderer dispatch are not implemented.

## Task 2: RED - runtime and manifest/frontend sync tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`

- [ ] **Step 1: Write failing backend runtime tests**

Add tests that prove PRD Review uses `artifact_data` and never asks the model to emit full Markdown:

```python
def test_prd_review_structured_output_instruction_requests_artifact_data_not_markdown() -> None:
    instruction = build_structured_output_instruction("PRD_REVIEW", "REVISION_BLUEPRINT")

    assert '"artifact_data"' in instruction
    assert "不要输出完整 Markdown" in instruction
    assert "PRD 修订蓝图" in instruction
```

- [ ] **Step 2: Add manifest sync prompt mappings**

Add these entries to `FRONTEND_PROMPT_FILES`:

```python
("PRD_REVIEW", "INVENTORY"): FRONTEND_CORE / "prompts/prd_review/inventory.ts",
("PRD_REVIEW", "QUALITY_AUDIT"): FRONTEND_CORE / "prompts/prd_review/quality_audit.ts",
("PRD_REVIEW", "COMPLETION_PLAN"): FRONTEND_CORE / "prompts/prd_review/completion_plan.ts",
("PRD_REVIEW", "REVISION_BLUEPRINT"): FRONTEND_CORE / "prompts/prd_review/revision_blueprint.ts",
```

- [ ] **Step 3: Add frontend workflow test**

Add:

```typescript
it('should configure PRD_REVIEW as an online Alex workflow', () => {
    const workflows = getAgentWorkflows('alex');
    const prdReview = workflows.find(w => w.id === 'prd-review');

    expect(prdReview).toBeDefined();
    expect(prdReview?.status).toBe('online');
    expect(prdReview?.name).toBe('PRD 质量评审与补全');
    expect(prdReview?.link).toBe('/workspace/alex/prd-review');

    const wf = WORKFLOWS.PRD_REVIEW;
    expect(wf.agentId).toBe('alex');
    expect(wf.slug).toBe('prd-review');
    expect(wf.stages.map(stage => stage.id)).toEqual([
        'INVENTORY',
        'QUALITY_AUDIT',
        'COMPLETION_PLAN',
        'REVISION_BLUEPRINT',
    ]);
});
```

- [ ] **Step 4: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "prd_review or prompt_files_exist"
cd tools/new-agents/frontend && corepack pnpm test src/core/config/__tests__/workflows.test.ts
```

Expected: backend fails because `PRD_REVIEW` instruction/manifest/prompt files are missing; frontend fails because `WORKFLOWS.PRD_REVIEW` does not exist.

## Task 3: GREEN - workflow manifest and frontend registry

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/prd_review/inventory.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/prd_review/quality_audit.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/prd_review/completion_plan.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/prd_review/revision_blueprint.ts`

- [ ] **Step 1: Add `PRD_REVIEW` to manifest**

Add workflow id `PRD_REVIEW`, `agentId: "alex"`, slug `prd-review`, name `PRD 质量评审与补全`, four stages, prompt template IDs under `prd_review.*`, required artifact headings from the spec, and visual contract requirements `score-matrix`, `action-board`, `roadmap`.

- [ ] **Step 2: Register frontend type and prompt modules**

Update `WorkflowType` union with `PRD_REVIEW`, import the four PRD Review prompt/template exports, and add `prd_review.inventory`, `prd_review.quality_audit`, `prd_review.completion_plan`, `prd_review.revision_blueprint` entries to `STAGE_CONTENT_BY_TEMPLATE_ID`.

- [ ] **Step 3: Create prompt/template modules**

Each module exports two strings. The prompt explains stage goals; the template tells the user what PRD material to provide. Each string must exceed 100 trimmed characters so existing workflow config tests prove usable content exists.

- [ ] **Step 4: Run frontend test**

Run:

```bash
cd tools/new-agents/frontend && corepack pnpm test src/core/config/__tests__/workflows.test.ts
```

Expected: workflow config tests pass after registry and prompt content are wired.

## Task 4: GREEN - backend contract and runtime

**Files:**
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/agent_runtime.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`

- [ ] **Step 1: Add backend stage and contract config**

Add `PRD_REVIEW` to `WORKFLOW_STAGES`, add required headings for all four stages, and add required structured visual entries for `QUALITY_AUDIT`, `COMPLETION_PLAN`, and `REVISION_BLUEPRINT`.

- [ ] **Step 2: Add PRD Review structured output instruction**

Add `PRD_REVIEW_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` with JSON shape containing `chat`, `artifact_data`, `stage_action`, `warnings`, and nested fields from the spec. Include explicit text: `不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 ai4se-visual fenced block`.

- [ ] **Step 3: Add readiness and dispatch**

Add all four PRD Review stage tuples to `supports_artifact_data_rendering()`, and return the PRD Review instruction from `build_structured_output_instruction()` for every `PRD_REVIEW` stage.

- [ ] **Step 4: Run backend sync/runtime tests**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "prd_review or prompt_files_exist or manifest"
```

Expected: runtime instruction and manifest sync tests pass after contract config is in place.

## Task 5: GREEN - artifact_data schema and deterministic renderer

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [ ] **Step 1: Add Pydantic models**

Add models for PRD inventory items, quality findings, completion actions, revision sections, acceptance criteria, handoff inputs, and `PrdReviewArtifactData`. Set `extra="forbid"` and use existing non-empty validators.

- [ ] **Step 2: Add cross-field validators**

Validate unique `finding_id`, `action_id`, and `section_id`; validate action finding references; validate acceptance and handoff section references; require at least one checked stage gate.

- [ ] **Step 3: Add Markdown renderer**

Add renderer functions that generate stage-specific Markdown headings and structured visual fenced JSON blocks:

- `INVENTORY`: input inventory and missing information.
- `QUALITY_AUDIT`: quality overview, score matrix visual, findings and risk impact.
- `COMPLETION_PLAN`: action-board visual, completion actions, revision structure, verification.
- `REVISION_BLUEPRINT`: roadmap visual, revision sections, rewrites, acceptance criteria, Lisa handoff, review conditions.

- [ ] **Step 4: Add dispatch**

Update `render_agent_turn_from_artifact_data()` to route `("PRD_REVIEW", stage)` to the PRD Review renderer.

- [ ] **Step 5: Run renderer tests**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q -k "prd_review"
```

Expected: PRD Review schema, renderer and runtime tests pass.

## Task 6: Docs, full verification, commit

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/README.md`

- [ ] **Step 1: Update todo records**

Mark E14 as consumed by this milestone, add a dated goal-mode record, update the current ability map from 5 workflows / 17 stages to 6 workflows / 21 stages, and keep E13 as a next candidate.

- [ ] **Step 2: Run expanded backend verification**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_contract_registry.py -q
```

Expected: all selected backend tests pass.

- [ ] **Step 3: Run frontend workflow verification**

Run:

```bash
cd tools/new-agents/frontend && corepack pnpm test src/core/config/__tests__/workflows.test.ts
```

Expected: workflow config tests pass.

- [ ] **Step 4: Run static checks**

Run:

```bash
python3 -m json.tool tools/new-agents/workflow_manifest.json >/tmp/prd_review_manifest_check.json
git diff --check
```

Expected: JSON is valid and `git diff --check` emits no whitespace errors.

- [ ] **Step 5: Commit**

Run:

```bash
git status --short
git add docs/superpowers/specs/2026-06-23-alex-prd-review-workflow-design.md docs/superpowers/plans/2026-06-23-alex-prd-review-workflow.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md tools/new-agents/workflow_manifest.json tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/workflows.ts tools/new-agents/frontend/src/core/prompts/prd_review tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py
git commit -m "feat(new-agents): 上线 Alex PRD 质量评审 workflow"
```

Expected: one focused commit for this milestone.
