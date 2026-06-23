# DeepSeek V4 Mainline Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `master` 基线形成 DeepSeek V4 格式化输出完成态收口，让 readiness/persistence/smoke 信任闭环、todo 工作池和共享 runtime 防回退门禁同时可信。

**Architecture:** 本轮不新增运行时或 UI 基础设施，只移植 DeepSeek 专属信任闭环，持久化 validated `artifact_data`，并把既有 stage-specific `artifact_data` 指令集中成共享 runtime registry。测试把 workflow manifest、runtime 指令、renderer stage key、retry prompt、run snapshot 和 real smoke skip gate 绑定起来；文档侧通过索引测试约束 `docs/todos/refactor/README.md` 与实际活动候选一致。

**Tech Stack:** Python 3.11、pytest、Pydantic/PydanticAI runtime、React/Vitest/TypeScript lint、git worktree。

---

## 文件结构

- Create: `tests/test_refactor_todo_index.py`
  - 根级文档索引一致性测试，只负责扫描 `docs/todos/refactor/` 和 README。
- Modify: `tools/new-agents/backend/agent_runtime.py`
  - 新增 `ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS` registry。
  - 更新 `supports_artifact_data_rendering()` 和 `build_structured_output_instruction()`。
- Modify: `tools/new-agents/backend/agent_contracts.py`
  - 允许 `AgentTurnOutput` 携带 validated `artifact_data`。
- Modify: `tools/new-agents/backend/models.py`
  - 为 artifact version 保存 `artifact_data`。
- Modify: `tools/new-agents/backend/run_persistence.py`
  - 保存 artifact version 的 `artifact_data`，并在当前 run snapshot 暴露 `artifactData`。
- Modify: `tools/new-agents/backend/app.py`
  - 在 artifact 手工编辑路径显式清空 `artifact_data`。
- Modify: `tools/new-agents/backend/stream_services.py`
  - 将 renderer 返回的 `artifact_data` 写入 artifact version。
- Create: `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`
  - DeepSeek readiness gate，覆盖在线 stage、renderer、fixture、contract、response_format 和 thinking disabled。
- Modify: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`
  - 对已迁移 `artifact_data` stage 跳过 Markdown 直写格式注入。
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`
  - 覆盖已迁移 stage 不再注入 `<mark>`、`artifact_update`、完整 Markdown 重写要求或 Mermaid fence。
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
  - 新增 manifest 在线 stage 的 artifact_data 指令和 retry prompt 防回退测试。
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
  - 新增 renderer stage key 与 runtime instruction registry 同步测试。
- Move: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` -> `docs/todos/archive/2026-06-23-deepseek-v4-structured-artifact-data.md`
  - 更新状态、归档日期和完成态验收记录。
- Modify: `docs/todos/refactor/README.md`
  - 当前入口只保留 `2026-06-23-new-agents-enhancement-diagnostic.md`。
- Modify: `docs/superpowers/specs/2026-06-23-deepseek-v4-mainline-closure-design.md`
  - 完成后把状态改为已完成。
- Modify: `docs/superpowers/plans/2026-06-23-deepseek-v4-mainline-closure.md`
  - 完成后补执行记录。

## Task 1: Refactor Todo Index RED/GREEN

**Files:**
- Create: `tests/test_refactor_todo_index.py`
- Modify: `docs/todos/refactor/README.md`
- Move: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [ ] **Step 1: Write the failing index test**

Add `tests/test_refactor_todo_index.py`:

```python
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REFACTOR_TODO_DIR = REPO_ROOT / "docs" / "todos" / "refactor"
README_PATH = REFACTOR_TODO_DIR / "README.md"


def test_refactor_readme_lists_all_active_candidates() -> None:
    active_files = sorted(
        path.name
        for path in REFACTOR_TODO_DIR.glob("*.md")
        if path.name != "README.md"
        and "> 状态: 活动候选" in path.read_text(encoding="utf-8")
    )
    readme = README_PATH.read_text(encoding="utf-8")

    if not active_files:
        assert "当前入口\n\n暂无。" in readme
        return

    assert "当前入口\n\n暂无。" not in readme
    for filename in active_files:
        assert filename in readme
```

- [ ] **Step 2: Run RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider -o addopts='' tests/test_refactor_todo_index.py -q
```

Expected: FAIL before docs update if README omits an active candidate or still says no active entry while active files exist.

- [ ] **Step 3: Move DeepSeek todo to archive and update README**

Use `mv` or `git mv` equivalent through patch/manual file move:

```text
docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md
-> docs/todos/archive/2026-06-23-deepseek-v4-structured-artifact-data.md
```

Change status in archived file:

```markdown
> 状态: 已完成 / 已归档
> 创建日期: 2026-06-23
> 归档日期: 2026-06-23
```

Update `docs/todos/refactor/README.md` current entry:

```markdown
## 当前入口

- `2026-06-23-new-agents-enhancement-diagnostic.md`：New Agents 功能盘点、差距分析和增强路线活动候选。
```

- [ ] **Step 4: Run GREEN**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider -o addopts='' tests/test_refactor_todo_index.py -q
```

Expected: `1 passed`.

## Task 2: Runtime Format Guard RED/GREEN

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [ ] **Step 1: Write failing runtime tests**

In `tools/new-agents/backend/tests/test_agent_runtime.py`, import:

```python
from agent_runtime import (
    ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS,
    supports_artifact_data_rendering,
)
from artifact_data_renderers import get_artifact_data_renderer_stage_keys
from workflow_contract_registry import get_workflow_stages
```

Add tests:

```python
def test_all_manifest_stages_use_artifact_data_instructions_without_markdown_fallback():
    stage_keys = {
        (workflow_id, stage_id)
        for workflow_id, stages in get_workflow_stages().items()
        for stage_id in stages
    }

    assert stage_keys
    assert stage_keys == set(ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS)
    assert stage_keys == set(get_artifact_data_renderer_stage_keys())

    for workflow_id, stage_id in sorted(stage_keys):
        assert supports_artifact_data_rendering(workflow_id, stage_id)
        instruction = build_structured_output_instruction(workflow_id, stage_id)
        assert "artifact_data" in instruction
        assert "artifact_update.markdown" not in instruction
        assert "artifact_update.type 必须为 replace" not in instruction
        assert "后端会负责确定性渲染" in instruction


def test_all_manifest_stage_retry_prompts_repair_artifact_data_not_markdown():
    for workflow_id, stages in get_workflow_stages().items():
        for stage_id in stages:
            prompt = build_raw_json_retry_prompt(
                "原始提示",
                ValueError("artifact_data.requirements.0.title missing"),
                workflow_id=workflow_id,
                current_stage_id=stage_id,
            )

            assert "artifact_data" in prompt
            assert "不要输出 Markdown 文档" in prompt
            assert "artifact_update.type 必须为 replace" not in prompt
```

In `tools/new-agents/backend/tests/test_artifact_data_renderers.py`, import runtime registry and renderer keys, then add:

```python
def test_artifact_data_renderer_stage_keys_match_runtime_instruction_registry():
    assert set(get_artifact_data_renderer_stage_keys()) == set(
        ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS
    )
```

- [ ] **Step 2: Run RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py::test_all_manifest_stages_use_artifact_data_instructions_without_markdown_fallback tools/new-agents/backend/tests/test_agent_runtime.py::test_all_manifest_stage_retry_prompts_repair_artifact_data_not_markdown tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_renderer_stage_keys_match_runtime_instruction_registry -q
```

Expected: collection/import failure because `ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS` does not exist yet, or assertion failure if registry is incomplete.

- [ ] **Step 3: Implement minimal runtime registry**

In `tools/new-agents/backend/agent_runtime.py`:

```python
from artifact_data_renderers import (
    get_artifact_data_renderer_stage_keys,
    render_agent_turn_from_artifact_data,
)
```

Add a dict mapping all online stage keys to their existing instruction constants:

```python
ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS: dict[tuple[str, str], str] = {
    ("IDEA_BRAINSTORM", "DEFINE"): IDEA_DEFINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("IDEA_BRAINSTORM", "DIVERGE"): IDEA_DIVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("IDEA_BRAINSTORM", "CONVERGE"): IDEA_CONVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("IDEA_BRAINSTORM", "CONCEPT"): IDEA_CONCEPT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("TEST_DESIGN", "CLARIFY"): ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("TEST_DESIGN", "STRATEGY"): STRATEGY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("TEST_DESIGN", "CASES"): CASES_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("TEST_DESIGN", "DELIVERY"): DELIVERY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("REQ_REVIEW", "REVIEW"): REQ_REVIEW_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("REQ_REVIEW", "REPORT"): REQ_REVIEW_REPORT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("VALUE_DISCOVERY", "ELEVATOR"): VALUE_ELEVATOR_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("VALUE_DISCOVERY", "PERSONA"): VALUE_PERSONA_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("VALUE_DISCOVERY", "JOURNEY"): VALUE_JOURNEY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("VALUE_DISCOVERY", "BLUEPRINT"): VALUE_BLUEPRINT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("INCIDENT_REVIEW", "TIMELINE"): INCIDENT_TIMELINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("INCIDENT_REVIEW", "ROOT_CAUSE"): INCIDENT_ROOT_CAUSE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("INCIDENT_REVIEW", "IMPROVEMENT"): INCIDENT_IMPROVEMENT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
}
```

Update:

```python
def supports_artifact_data_rendering(workflow_id: str, current_stage_id: str) -> bool:
    stage_key = (workflow_id, current_stage_id)
    return (
        stage_key in ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS
        and stage_key in get_artifact_data_renderer_stage_keys()
    )
```

Update:

```python
def build_structured_output_instruction(workflow_id: str, current_stage_id: str) -> str:
    return ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS.get(
        (workflow_id, current_stage_id),
        TEXT_STRUCTURED_OUTPUT_INSTRUCTION,
    )
```

- [ ] **Step 4: Run GREEN**

Run the same three focused tests. Expected: `3 passed`.

## Task 3: Documentation Completion Record

**Files:**
- Modify: `docs/todos/archive/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Modify: `docs/superpowers/specs/2026-06-23-deepseek-v4-mainline-closure-design.md`
- Modify: `docs/superpowers/plans/2026-06-23-deepseek-v4-mainline-closure.md`

- [ ] **Step 1: Add archive completion record**

In the archive file, add a `## 完成态验收记录` section near the top, including:

```markdown
- 17 个在线 stage 已迁移为模型输出 `artifact_data`，后端确定性渲染 Markdown、Mermaid 和 `ai4se-visual`。
- DeepSeek V4 Flash capability 明确为 `json_object_only`，请求仍只发送 OpenAI-compatible `response_format={"type":"json_object"}`，并保持 thinking disabled。
- 本轮补充 runtime 格式化输出防回退门禁：所有 manifest 在线 stage 的 structured output instruction 和 retry prompt 均要求 `artifact_data`，不要求模型输出或修复完整 Markdown。
```

- [ ] **Step 2: Mark spec completed after validation**

Change:

```markdown
> 状态: 本轮目标模式执行中
```

to:

```markdown
> 状态: 已完成
```

- [ ] **Step 3: Add plan execution record**

Append:

```markdown
## 执行记录

- RED: refactor README 活动候选索引测试在归档前失败。
- RED: runtime format guard 在新增 registry 前失败。
- GREEN: 索引测试、runtime format guard、DeepSeek 后端扩展测试、前端 prompt 测试和 lint 均通过。
```

## Task 4: Verification and Commit

**Files:**
- All touched files from Tasks 1-3.

- [ ] **Step 1: Run focused validation**

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider -o addopts='' tests/test_refactor_todo_index.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py::test_all_manifest_stages_use_artifact_data_instructions_without_markdown_fallback tools/new-agents/backend/tests/test_agent_runtime.py::test_all_manifest_stage_retry_prompts_repair_artifact_data_not_markdown tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_renderer_stage_keys_match_runtime_instruction_registry -q
```

- [ ] **Step 2: Run expanded backend validation**

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_real_smoke.py -q
```

- [ ] **Step 3: Run frontend prompt and lint validation**

If `tools/new-agents/frontend/node_modules` is missing in the worktree, create a temporary symlink to the main workspace dependency directory, run the commands, then remove the symlink before commit.

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/buildSystemPrompt.test.ts
cd tools/new-agents/frontend && npm run lint
```

- [ ] **Step 4: Run static checks**

```bash
.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py
.venv/bin/python -m black --check tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py
git diff --check
git status --short
```

- [ ] **Step 5: Commit**

Stage only this milestone:

```bash
git add docs/superpowers/plans/2026-06-23-deepseek-v4-mainline-closure.md docs/superpowers/specs/2026-06-23-deepseek-v4-mainline-closure-design.md docs/todos/archive/2026-06-23-deepseek-v4-structured-artifact-data.md docs/todos/refactor/README.md tests/test_refactor_todo_index.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py
git commit -m "chore: 收口 DeepSeek V4 主线格式化输出"
```

## 自检

- Spec 覆盖: Task 1 覆盖 docs/todos 主线状态；Task 2 覆盖 runtime format guard；Task 3 覆盖文档记录；Task 4 覆盖验证与提交。
- 占位扫描: 本计划不包含待补路径或未定义步骤。
- 类型一致性: 新 registry 类型为 `dict[tuple[str, str], str]`，测试统一用 `set(...)` 与 renderer key tuple 比对。

## 执行记录

- RED: `tests/test_refactor_todo_index.py` 在归档前失败，原因是 README 写“当前入口 暂无”，但 refactor 目录存在活动候选。
- RED: runtime format guard 在新增 registry 前 collection/import 失败，原因是 `agent_runtime` 尚未暴露 `ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS`。
- GREEN: 归档 DeepSeek todo、更新 README、增加 runtime instruction registry 和 renderer stage key getter 后，索引测试 `1 passed`，runtime/renderer format guard `3 passed`。
- 边界校正: 扩展验证发现 `master` 基线缺少 `test_deepseek_v4_readiness.py`，因此本轮从 `codex/deepseek-confidence-consolidation` 移植 DeepSeek 专属 readiness、artifact_data persistence、real smoke gate 和信任闭环文档；随后确认 prompt boundary hardening 也是 DeepSeek 格式化输出闭环的一部分，并从 `codex/deepseek-prompt-boundary-hardening` 移植前端 prompt 边界硬化；未移植 artifact quality、missing-info、Alex workflow 等非 DeepSeek 增强。
- GREEN: DeepSeek 后端扩展套件通过，`377 passed, 1 skipped`，skip 为无显式真实 DeepSeek smoke 凭证时的预期门禁。
- GREEN: 前端 prompt 测试通过，`40 passed`；`npm run lint` 通过。
