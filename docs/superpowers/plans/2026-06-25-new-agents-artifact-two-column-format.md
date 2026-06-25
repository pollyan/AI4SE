# New Agents 产出物二列说明表去表格化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将右侧 Artifact 中说明性二列表格统一渲染为定义列表，保留风险、追溯、矩阵、用例等结构化表格。

**Architecture:** 在后端 deterministic renderer 的 `_markdown_table` 出口增加窄规则：仅固定二列说明表头转定义列表，其他表格保持原样。不改 Agent Runtime、SSE、store、ArtifactPane 或 artifact_data schema。

**Tech Stack:** Python 3.12, pytest, Markdown, ReactMarkdown existing renderer.

---

### Task 1: Red Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify as needed: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`

- [x] **Step 1: Add renderer test for strategy summary**

Assert rendered `TEST_DESIGN/STRATEGY` Markdown contains `## 1. 策略摘要`, does not contain `| 字段 | 内容 |`, and still contains bullet-style key/value lines.

- [x] **Step 2: Add renderer test for document info**

Assert rendered Markdown contains `## 附录：文档信息`, does not contain `| 字段 | 内容 |` or `| 维度 | 内容 |`.

- [x] **Step 3: Add/keep table-preservation assertion**

Assert risk/FMEA or other multi-column sections still contain Markdown table headers such as `| 风险 ID |` or `| 目标 ID |`.

- [x] **Step 4: Run red tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: FAIL because the current renderer still outputs `| 字段 | 内容 |` for strategy summary and document info.

Result: FAIL observed before implementation, with the expected `| 字段 | 内容 |` assertions.

### Task 2: Shared Renderer Update

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [x] **Step 1: Add definition-list helper**

Add `_definition_list(rows)` near `_markdown_table`.

- [x] **Step 2: Special-case only explanatory two-column headers**

In `_markdown_table`, when `headers` equals one of:

```python
[
    ["字段", "内容"],
    ["维度", "内容"],
    ["格子", "内容"],
    ["属性", "详情"],
]
```

return `_definition_list(rows)` instead of a table.

- [x] **Step 3: Preserve all other tables**

Leave existing table rendering untouched for all other headers.

### Task 3: Verification

**Files:**
- Tests touched above.

- [x] **Step 1: Run renderer tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: PASS.

Result: PASS, 75 tests.

- [x] **Step 2: Run runtime and frontend parser regressions**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -k "artifact_data_before_final_output or paragraph_level" -q
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/llm.test.ts
```

Expected: PASS after updating any assertions that only encoded the old two-column table shape.

Result: PASS, 18 backend runtime tests and 72 frontend parser tests.

- [x] **Step 3: Compile backend file**

Run:

```bash
.venv/bin/python -m py_compile tools/new-agents/backend/artifact_data_renderers.py
```

Expected: PASS.

Result: PASS.

### Task 4: Todo Record and Commit

**Files:**
- Move/update: `docs/todos/2026-06-25-new-agents-artifact-format-over-tabularization-audit.md`
- Create/update: `docs/todos/archive/2026-06-25-new-agents-artifact-format-over-tabularization-audit.md`
- Create: this spec and plan.

- [x] **Step 1: Archive completed todo**

Move the todo to archive, mark status `已完成`, and record the scoped audit decision: explanatory two-column tables converted, structural multi-column tables retained.

- [x] **Step 2: Run targeted diff and doc checks**

Run targeted `git diff --check` for this story and the doc placeholder Python check.

Result: PASS. `git diff --check` returned clean and placeholder scan found no matches.

- [x] **Step 3: Stage only this story**

Stage renderer, tests, spec, plan, and archived todo only.

Result: PASS. Only this story's renderer, tests, spec, plan, and archived todo were staged.

- [x] **Step 4: Commit**

Run:

```bash
git commit -m "feat: 优化产出物二列说明格式"
```

Result: PASS. The staged change set was committed with this message.
