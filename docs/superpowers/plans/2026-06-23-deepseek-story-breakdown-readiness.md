# DeepSeek Story Breakdown Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把新增 Alex `STORY_BREAKDOWN` 四阶段纳入 DeepSeek V4 格式化输出 readiness gate，防止新 workflow 回退到模型直写 Markdown / Mermaid / fenced block。

**Architecture:** 继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、`artifact_data` renderer 和 run persistence。DeepSeek readiness 测试以 manifest stage set 为准，fixture registry 必须与 renderer registry 和 manifest 完全一致。

**Tech Stack:** Python 3.11、pytest、Pydantic、New Agents shared runtime。

---

## 文件结构

- Modify: `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`
  - 导入 `VALID_STORY_BREAKDOWN_ARTIFACT_DATA`，为 `STORY_BREAKDOWN` 四阶段注册 fixture。
- Modify: `docs/todos/archive/2026-06-23-deepseek-v4-structured-artifact-data.md`
  - 更新完成态记录，从旧 17 stage 扩展为包含 `STORY_BREAKDOWN` 四阶段的当前覆盖态。
- Modify: `docs/superpowers/specs/2026-06-23-deepseek-story-breakdown-readiness-design.md`
  - 完成后标记状态与执行证据。
- Modify: `docs/superpowers/plans/2026-06-23-deepseek-story-breakdown-readiness.md`
  - 勾选执行步骤并记录 RED/GREEN。

## Task 1: RED 确认

- [x] **Step 1: Run current DeepSeek readiness test**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py::test_deepseek_readiness_covers_every_manifest_stage -q
```

Expected RED:

```text
FAILED ... Extra items in the right set:
('STORY_BREAKDOWN', 'INPUT_ANALYSIS')
('STORY_BREAKDOWN', 'EPIC_MAPPING')
('STORY_BREAKDOWN', 'STORY_BACKLOG')
('STORY_BREAKDOWN', 'SPRINT_PLAN')
```

## Task 2: Fixture GREEN

- [x] **Step 1: Import Story Breakdown fixture**

In `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`, add `VALID_STORY_BREAKDOWN_ARTIFACT_DATA` to the import list from `test_artifact_data_renderers`.

- [x] **Step 2: Register all Story Breakdown stages**

Add these entries to `ARTIFACT_DATA_FIXTURES`:

```python
("STORY_BREAKDOWN", "INPUT_ANALYSIS"): VALID_STORY_BREAKDOWN_ARTIFACT_DATA,
("STORY_BREAKDOWN", "EPIC_MAPPING"): VALID_STORY_BREAKDOWN_ARTIFACT_DATA,
("STORY_BREAKDOWN", "STORY_BACKLOG"): VALID_STORY_BREAKDOWN_ARTIFACT_DATA,
("STORY_BREAKDOWN", "SPRINT_PLAN"): VALID_STORY_BREAKDOWN_ARTIFACT_DATA,
```

- [x] **Step 3: Run readiness GREEN**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q
```

Expected: all readiness tests pass; no real DeepSeek smoke is required by this file.

## Task 3: Documentation 收口

- [x] **Step 1: Update DeepSeek archive**

Update `docs/todos/archive/2026-06-23-deepseek-v4-structured-artifact-data.md` so completion notes say current readiness coverage includes:

- 原 17 个既有 online stage。
- `STORY_BREAKDOWN` 四阶段: `INPUT_ANALYSIS`、`EPIC_MAPPING`、`STORY_BACKLOG`、`SPRINT_PLAN`。
- Total current coverage is 21 online stages on the latest verified branch.

- [x] **Step 2: Mark spec and plan execution**

Mark spec status as `已完成` and append execution record with RED/GREEN commands.

## Task 4: Verification and Commit

- [x] **Step 1: Run focused and expanded validation**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_renderer_stage_keys_match_runtime_instruction_registry tools/new-agents/backend/tests/test_agent_runtime.py::test_all_manifest_stages_use_artifact_data_instructions_without_markdown_fallback tools/new-agents/backend/tests/test_agent_runtime.py::test_all_manifest_stage_retry_prompts_repair_artifact_data_not_markdown -q
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/tests/test_deepseek_v4_readiness.py
git diff --check
```

Expected: all commands pass.

- [ ] **Step 2: Commit**

Stage only the files listed in this plan and commit:

```bash
git add docs/superpowers/plans/2026-06-23-deepseek-story-breakdown-readiness.md docs/superpowers/specs/2026-06-23-deepseek-story-breakdown-readiness-design.md docs/todos/archive/2026-06-23-deepseek-v4-structured-artifact-data.md tools/new-agents/backend/tests/test_deepseek_v4_readiness.py
git commit -m "test: 补齐 Story Breakdown 的 DeepSeek readiness"
```

## 自检

- Spec 覆盖: readiness fixture、fake DeepSeek stream、contract validation、archive 事实均有任务覆盖。
- 占位扫描: 无 TBD/TODO/待补。
- 类型一致性: workflow id 使用 `STORY_BREAKDOWN`，stage id 使用 `INPUT_ANALYSIS`、`EPIC_MAPPING`、`STORY_BACKLOG`、`SPRINT_PLAN`。

## 执行记录

- RED: `test_deepseek_readiness_covers_every_manifest_stage` 失败，缺 `STORY_BREAKDOWN` 四阶段 fixture。
- GREEN: `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q` 通过，`64 passed`。
- Expanded: `test_deepseek_v4_readiness.py` + renderer/runtime registry 防回退测试通过，`67 passed`；`py_compile` 和 `git diff --check` 通过。
