# DeepSeek V4 Readiness Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为当前 New Agents 在线 workflow 建立 DeepSeek V4 `artifact_data` readiness gate，并收口对应活动 todo。

**Architecture:** 后端 runtime 暴露只读 ready stage 集合，测试从共享 `workflow_manifest.json` 派生当前 stage 集合并与 runtime 比对。readiness gate 还验证 DeepSeek V4 capability/model settings 和所有 stage 的 structured output instruction，不改变生产 SSE/API/persistence 协议。

**Tech Stack:** Python 3.11+、pytest、PydanticAI runtime helper、JSON manifest。

---

## File Structure

- Create: `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`
  - 负责 DeepSeek V4 readiness gate。
- Modify: `tools/new-agents/backend/agent_runtime.py`
  - 增加 `ARTIFACT_DATA_READY_STAGES` 常量和 `get_artifact_data_ready_stages()` helper；`supports_artifact_data_rendering()` 复用该常量。
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
  - 标记主线完成，记录 readiness gate。
- Modify: `docs/todos/refactor/README.md`
  - 从活动入口移除 DeepSeek V4 收口文件，保留 New Agents 增强诊断。
- Create: `docs/superpowers/specs/2026-06-23-deepseek-v4-readiness-closure-design.md`
  - 本轮中文设计。
- Create: `docs/superpowers/plans/2026-06-23-deepseek-v4-readiness-closure.md`
  - 本实施计划。

## Task 1: Readiness Gate RED

**Files:**
- Create: `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path

from agent_runtime import (
    build_model_settings,
    build_structured_output_instruction,
    get_artifact_data_ready_stages,
    resolve_structured_output_capability,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOW_MANIFEST = REPO_ROOT / "tools/new-agents/workflow_manifest.json"


def _manifest_stages() -> set[tuple[str, str]]:
    manifest = json.loads(WORKFLOW_MANIFEST.read_text(encoding="utf-8"))
    return {
        (workflow_id, stage["id"])
        for workflow_id, workflow in manifest["workflows"].items()
        for stage in workflow["stages"]
    }


def test_all_manifest_stages_are_deepseek_artifact_data_ready():
    assert get_artifact_data_ready_stages() == _manifest_stages()


def test_artifact_data_ready_stages_do_not_prompt_model_for_markdown_artifacts():
    for workflow_id, stage_id in sorted(get_artifact_data_ready_stages()):
        instruction = build_structured_output_instruction(workflow_id, stage_id)
        assert "artifact_data" in instruction
        assert "artifact_update.markdown" not in instruction
        assert "不要输出完整 Markdown" in instruction


def test_deepseek_v4_uses_json_object_only_with_thinking_disabled():
    capability = resolve_structured_output_capability("deepseek-v4-flash")
    assert capability == "json_object_only"
    assert build_model_settings("deepseek-v4-flash") == {
        "extra_body": {"thinking": {"type": "disabled"}}
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q
```

Expected: FAIL during import because `get_artifact_data_ready_stages` does not exist.

## Task 2: Runtime Helper GREEN

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [ ] **Step 1: Add ready stage constant and helper**

Implementation:

```python
ARTIFACT_DATA_READY_STAGES: frozenset[tuple[str, str]] = frozenset(
    {
        ("IDEA_BRAINSTORM", "DEFINE"),
        ("IDEA_BRAINSTORM", "DIVERGE"),
        ("IDEA_BRAINSTORM", "CONVERGE"),
        ("IDEA_BRAINSTORM", "CONCEPT"),
        ("TEST_DESIGN", "CLARIFY"),
        ("TEST_DESIGN", "STRATEGY"),
        ("TEST_DESIGN", "CASES"),
        ("TEST_DESIGN", "DELIVERY"),
        ("REQ_REVIEW", "REVIEW"),
        ("REQ_REVIEW", "REPORT"),
        ("VALUE_DISCOVERY", "ELEVATOR"),
        ("VALUE_DISCOVERY", "PERSONA"),
        ("VALUE_DISCOVERY", "JOURNEY"),
        ("VALUE_DISCOVERY", "BLUEPRINT"),
        ("INCIDENT_REVIEW", "TIMELINE"),
        ("INCIDENT_REVIEW", "ROOT_CAUSE"),
        ("INCIDENT_REVIEW", "IMPROVEMENT"),
    }
)


def get_artifact_data_ready_stages() -> set[tuple[str, str]]:
    return set(ARTIFACT_DATA_READY_STAGES)
```

Then update `supports_artifact_data_rendering()`:

```python
def supports_artifact_data_rendering(workflow_id: str, current_stage_id: str) -> bool:
    return (workflow_id, current_stage_id) in ARTIFACT_DATA_READY_STAGES
```

- [ ] **Step 2: Run readiness test**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q
```

Expected: PASS.

## Task 3: Todo Closure

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Modify: `docs/todos/refactor/README.md`

- [ ] **Step 1: Update DeepSeek todo**

Set status to completed / ready to archive, add a final progress bullet:

```markdown
> 状态: 已完成，待归档

- 2026-06-23 已完成收口门禁: 新增 `test_deepseek_v4_readiness.py`，确保当前 manifest 全部 stage 都进入 `artifact_data` ready set，DeepSeek V4 Flash 保持 `json_object_only` 和 thinking disabled，所有 ready stage prompt 均不要求模型输出完整 Markdown artifact。
```

- [ ] **Step 2: Update refactor README**

Remove the DeepSeek V4 file from active entries and add it to archive/completed note. Keep `2026-06-23-new-agents-enhancement-diagnostic.md` as active.

## Task 4: Verification and Commit

- [ ] **Step 1: Run focused verification**

```bash
python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_contract_registry.py -q
```

Expected: PASS.

- [ ] **Step 2: Run artifact renderer smoke scope**

```bash
python3 -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: PASS.

- [ ] **Step 3: Inspect diff and status**

```bash
git diff --stat
git status --short
```

Expected: only this milestone files changed.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-06-23-deepseek-v4-readiness-closure-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-readiness-closure.md tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_deepseek_v4_readiness.py docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md docs/todos/refactor/README.md
git commit -m "test(new-agents): 收口 DeepSeek V4 readiness 门禁"
```

Expected: focused commit on `codex/deepseek-v4-readiness-closure`.

## Self-Review

- Spec coverage: plan covers readiness test, runtime helper, todo closure, verification, commit.
- Placeholder scan: no TODO/TBD placeholders.
- Scope check: this plan intentionally excludes new Alex workflows and real DeepSeek smoke.
