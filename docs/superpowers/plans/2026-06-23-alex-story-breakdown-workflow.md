# Alex 用户故事拆解 Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 PRD Review 主线基线上上线 Alex `STORY_BREAKDOWN`，让用户能从 PRD、需求蓝图或 PRD Review 修订蓝图生成 Epic、User Story、AC、依赖风险、Sprint 切片和 Lisa handoff 输入。

**Architecture:** 新能力继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、artifact_data renderer、run/artifact persistence 和共享前端 workflow registry。Workflow 差异通过 `workflow_manifest.json`、stage prompt、Pydantic schema、deterministic renderer、handoff 配置和测试表达，不新增 Alex 专属 runtime/API/store/renderer。

**Tech Stack:** Python 3.11+/Pydantic/pytest，TypeScript 5.x/React/Vitest，New Agents shared runtime。

---

## 文件结构

- Modify: `tools/new-agents/workflow_manifest.json`，新增 `STORY_BREAKDOWN` workflow、4 个 stage、artifact/visual contract、handoff、onboarding。
- Modify: `tools/new-agents/frontend/src/core/types.ts`，加入 `STORY_BREAKDOWN`。
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`，注册 Story Breakdown prompt/template。
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/input_analysis.ts`。
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/epic_mapping.ts`。
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/story_backlog.ts`。
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/sprint_plan.ts`。
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`，新增在线 workflow 验收。
- Modify: `tools/new-agents/backend/agent_contracts.py`，新增 stages/headings/structured visual requirements。
- Modify: `tools/new-agents/backend/agent_runtime.py`，新增 structured output instruction、artifact_data readiness stage 和 dispatch。
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`，新增 schema、validators 和 renderer。
- Modify: `tools/new-agents/backend/workflow_handoffs.py`，新增最终阶段 Lisa handoff。
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`，新增 schema/renderer tests。
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`，新增 runtime parse/instruction tests。
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`，新增 prompt file sync mapping。
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_registry.py`，新增 workflow registry stage/prompt assertions。
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`，新增 handoff tests。
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 和 `docs/todos/refactor/README.md`，记录 E13 消化结果。

## Task 1: RED - backend story artifact_data and renderer tests

- [ ] **Step 1: Write failing tests**

Add a valid Story Breakdown fixture and tests in `tools/new-agents/backend/tests/test_artifact_data_renderers.py`:

```python
from artifact_data_renderers import StoryBreakdownArtifactData


def test_story_breakdown_artifact_data_rejects_unknown_epic_reference() -> None:
    invalid = copy.deepcopy(VALID_STORY_BREAKDOWN_ARTIFACT_DATA)
    invalid["stories"][0]["epic_id"] = "EPIC-404"

    with pytest.raises(ValidationError, match="unknown epic ids"):
        StoryBreakdownArtifactData.model_validate(invalid)


def test_story_breakdown_artifact_data_rejects_unknown_story_reference() -> None:
    invalid = copy.deepcopy(VALID_STORY_BREAKDOWN_ARTIFACT_DATA)
    invalid["acceptance_criteria"][0]["story_id"] = "ST-404"

    with pytest.raises(ValidationError, match="unknown story ids"):
        StoryBreakdownArtifactData.model_validate(invalid)


def test_story_breakdown_artifact_data_requires_stage_gate_checked() -> None:
    invalid = copy.deepcopy(VALID_STORY_BREAKDOWN_ARTIFACT_DATA)
    invalid["stage_gate"] = [{"checked": False, "item": "仍缺少 Sprint 门禁"}]

    with pytest.raises(ValidationError, match="stage_gate"):
        StoryBreakdownArtifactData.model_validate(invalid)


@pytest.mark.parametrize(
    ("stage_id", "expected_heading"),
    [
        ("INPUT_ANALYSIS", "## 输入分析"),
        ("EPIC_MAPPING", "## Epic Map"),
        ("STORY_BACKLOG", "## User Story Backlog"),
        ("SPRINT_PLAN", "## Sprint 切片建议"),
    ],
)
def test_render_story_breakdown_artifact_data_is_deterministic_and_contract_valid(stage_id, expected_heading):
    output = {
        "chat": "我已完成用户故事拆解，请查看右侧故事包。",
        "artifact_data": VALID_STORY_BREAKDOWN_ARTIFACT_DATA,
        "stage_action": None,
        "warnings": [],
    }
    first = render_agent_turn_from_artifact_data(output, workflow_id="STORY_BREAKDOWN", current_stage_id=stage_id)
    second = render_agent_turn_from_artifact_data(output, workflow_id="STORY_BREAKDOWN", current_stage_id=stage_id)

    assert first == second
    assert first.artifact_update.markdown is not None
    assert "# 用户故事拆解包" in first.artifact_update.markdown
    assert expected_heading in first.artifact_update.markdown
    if stage_id == "SPRINT_PLAN":
        assert '"type": "story-map"' in first.artifact_update.markdown
    assert validate_agent_turn(first, workflow_id="STORY_BREAKDOWN", current_stage_id=stage_id) == first
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q -k "story_breakdown"
```

Expected: FAIL or collection error because `StoryBreakdownArtifactData` and renderer dispatch do not exist.

## Task 2: RED - runtime, manifest sync, frontend config, handoff tests

- [ ] **Step 1: Add runtime tests**

In `tools/new-agents/backend/tests/test_agent_runtime.py`, add:

```python
def test_parse_agent_turn_output_text_renders_story_breakdown_artifact_data() -> None:
    json_text = json.dumps(
        {
            "chat": "我已整理 Sprint 切片，请确认右侧内容。",
            "artifact_data": VALID_STORY_BREAKDOWN_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    output = parse_agent_turn_output_text(json_text, workflow_id="STORY_BREAKDOWN", current_stage_id="SPRINT_PLAN")

    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert output.artifact_update.markdown.startswith("# 用户故事拆解包")
    assert '"type": "story-map"' in output.artifact_update.markdown


def test_story_breakdown_structured_output_instruction_requests_artifact_data_not_markdown() -> None:
    instruction = build_structured_output_instruction("STORY_BREAKDOWN", "SPRINT_PLAN")

    assert "artifact_data" in instruction
    assert "stories" in instruction
    assert "sprint_slices" in instruction
    assert "story-map" in instruction
    assert "不要输出完整 Markdown" in instruction
    assert "artifact_update.markdown" not in instruction
```

- [ ] **Step 2: Add sync and registry tests**

Add `STORY_BREAKDOWN` prompt file mappings to `test_workflow_contract_sync.py`, and add explicit stage/prompt assertions to `test_workflow_contract_registry.py`.

- [ ] **Step 3: Add frontend config test**

In `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`, assert `story-breakdown` is an online Alex workflow with 4 stages.

- [ ] **Step 4: Add handoff test**

In `tools/new-agents/backend/tests/test_workflow_handoffs.py`, assert final `STORY_BREAKDOWN/SPRINT_PLAN` handoff to Lisa includes Stories, AC, dependencies, risks, and target workflow intent.

- [ ] **Step 5: Run tests to verify RED**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_contract_registry.py tools/new-agents/backend/tests/test_workflow_handoffs.py -q -k "story_breakdown or prompt_files_exist or registry"
cd tools/new-agents/frontend && corepack pnpm test src/core/config/__tests__/workflows.test.ts
```

Expected: failures because manifest, backend contract/runtime/renderer, prompt files, frontend workflow and handoff are missing.

## Task 3: GREEN - shared workflow config and frontend prompt registry

- [ ] **Step 1: Add manifest workflow**

Add `STORY_BREAKDOWN` to `workflow_manifest.json` with `agentId: "alex"`, slug `story-breakdown`, name `用户故事拆解`, four stages, listing preview, onboarding, artifact headings, `story-map` visual contract, and handoff from `SPRINT_PLAN` to Lisa.

- [ ] **Step 2: Register frontend workflow**

Update `WorkflowType`, import four Story Breakdown prompt/template modules in `workflows.ts`, and add `story_breakdown.input_analysis`, `story_breakdown.epic_mapping`, `story_breakdown.story_backlog`, `story_breakdown.sprint_plan` entries.

- [ ] **Step 3: Create prompt/template modules**

Create four prompt files with stage-specific guidance. Each prompt/template must be longer than 100 trimmed characters and must ask for structured thinking while relying on backend `artifact_data` rendering.

- [ ] **Step 4: Run frontend workflow test**

Run:

```bash
cd tools/new-agents/frontend && corepack pnpm test src/core/config/__tests__/workflows.test.ts
```

Expected: frontend workflow registry test passes.

## Task 4: GREEN - backend contract/runtime/renderer/handoff

- [ ] **Step 1: Add contract config**

Add `STORY_BREAKDOWN` to `WORKFLOW_STAGES`, required headings for all four stages, and required structured visual `story-map` for `SPRINT_PLAN`.

- [ ] **Step 2: Add runtime instruction**

Add `STORY_BREAKDOWN_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`, readiness tuples, and dispatch in `build_structured_output_instruction()`.

- [ ] **Step 3: Add Pydantic models and renderer**

Add `StoryBreakdownArtifactData` and nested models, cross-field validators, stage-specific markdown renderer, and dispatch in `render_agent_turn_from_artifact_data()`.

- [ ] **Step 4: Add handoff builder/config**

Use existing manifest/handoff infrastructure. Handoff text must summarize Epics, Stories, AC, dependencies, risks and Sprint plan for Lisa.

- [ ] **Step 5: Run backend focused tests**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_contract_registry.py tools/new-agents/backend/tests/test_workflow_handoffs.py -q -k "story_breakdown or prompt_files_exist or registry"
```

Expected: Story Breakdown tests pass.

## Task 5: Docs, expanded verification, commit

- [ ] **Step 1: Update todo docs**

Mark E13 consumed, update ability map from 6 workflows / 21 stages to 7 workflows / 25 stages, keep E03/E04/DeepSeek closure as future candidates.

- [ ] **Step 2: Run expanded backend verification**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_contract_registry.py tools/new-agents/backend/tests/test_workflow_handoffs.py -q
```

- [ ] **Step 3: Run frontend verification**

Run:

```bash
cd tools/new-agents/frontend && corepack pnpm test src/core/config/__tests__/workflows.test.ts
```

- [ ] **Step 4: Run static checks**

Run:

```bash
python3 -m json.tool tools/new-agents/workflow_manifest.json >/tmp/story_breakdown_manifest_check.json
git diff --check
```

- [ ] **Step 5: Commit**

Run:

```bash
git status --short
git add docs/superpowers/specs/2026-06-23-alex-story-breakdown-workflow-design.md docs/superpowers/plans/2026-06-23-alex-story-breakdown-workflow.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md tools/new-agents/workflow_manifest.json tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/workflows.ts tools/new-agents/frontend/src/core/prompts/story_breakdown tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/workflow_handoffs.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_contract_registry.py tools/new-agents/backend/tests/test_workflow_handoffs.py
git commit -m "feat(new-agents): 上线 Alex 用户故事拆解 workflow"
```

Expected: one focused commit for this milestone.

