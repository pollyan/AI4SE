# New Agents 右侧产物段落级真实流式 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 TEST_DESIGN/STRATEGY 右侧产物在 raw JSON streaming 过程中按已完成顶层字段生成正式 Markdown 增量，并在 ArtifactPane 当前内容后显示“正在生成下一段...”状态。

**Architecture:** 保持共享 `/api/agent/runs/stream` typed SSE、Agent Runtime、Zustand store 和 ArtifactPane 渲染管线。后端新增共享 partial JSON member 提取器，局部渲染复用现有 deterministic section render 函数；最终完整输出仍走现有 contract validation。

**Tech Stack:** Python 3.11, Pydantic, pytest, React 19, TypeScript, Vitest.

---

### Task 1: Backend Red Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [ ] **Step 1: Add a helper for stream prefixes**

Add a small test helper that finds the end offset of a completed top-level `artifact_data` member inside a JSON string by using `json.JSONDecoder().raw_decode`.

- [ ] **Step 2: Add STRATEGY paragraph-level red test**

Add a test where chunks stop after `strategy_summary`, then after `quality_goals`, then after the final object. Assert final-before artifact deltas include at least two increasing markdown frames: first contains `## 1. 策略摘要` but not `## 2. 质量目标`; second contains `## 2. 质量目标` but not `## 3. 风险识别与 FMEA`.

- [ ] **Step 3: Run red test**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -k "paragraph_level_strategy_artifact_data" -q
```

Expected: FAIL because current runtime only renders `artifact_data` after the full object closes.

### Task 2: Backend Implementation

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] **Step 1: Add completed-member extraction**

In `agent_runtime.py`, add `extract_completed_json_object_members(text, key)` near the JSON prefix helpers. It should find `"artifact_data": {`, parse only completed top-level key/value pairs, and return a `dict[str, Any]`. It must not include incomplete values.

- [ ] **Step 2: Add partial renderer entry**

In `artifact_data_renderers.py`, add `render_partial_agent_turn_from_artifact_data(payload, workflow_id, current_stage_id)`. For `TEST_DESIGN/STRATEGY`, build Markdown from existing section renderers as fields become available. Return `None` until at least one real section beyond the H1 is valid.

- [ ] **Step 3: Wire partial renderer**

In `build_partial_agent_delta(...)`, when no direct markdown exists and the full `artifact_data` object is not available, call the completed-member extractor and partial renderer. If rendering succeeds, emit `artifact_update.replace` with the partial Markdown.

- [ ] **Step 4: Preserve strict failure behavior**

Catch partial renderer validation errors locally and keep chat-only deltas if available. Do not emit progress pages, field-name progress, fake paragraphs, or hidden fallback success.

### Task 3: Frontend Position Indicator

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Add/adjust component test**

Add or update a test proving that when `isGenerating=true` and `artifactContent` is non-empty, ArtifactPane renders `正在生成下一段...` after the current artifact content.

- [ ] **Step 2: Update indicator copy**

Change the existing streaming position indicator text from `正在生成后续章节` to `正在生成下一段...`.

- [ ] **Step 3: Run focused frontend test**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.test.tsx
```

Expected: PASS.

### Task 4: Verification and Records

**Files:**
- Modify: `docs/todos/refactor/2026-06-25-new-agents-artifact-streaming-deep-diagnosis.md`
- Modify: `docs/todos/refactor/2026-06-25-new-agents-test-strategy-artifact-format-regression.md` if the streaming fix changes its status.
- Modify: `docs/todos/refactor/README.md` if a todo is completed or explicitly remains active.

- [ ] **Step 1: Run backend focused verification**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -k "paragraph_level_strategy_artifact_data or artifact_data_before_final_output or partial_artifact_data" -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend parser/service regressions**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.test.tsx
```

Expected: PASS.

- [ ] **Step 3: Run diff and docs checks**

Run:

```bash
git diff --check
python3 - <<'PY'
from pathlib import Path
tokens = ["TO" + "DO", "TB" + "D", "待" + "补充"]
paths = [
    Path("docs/superpowers/specs/2026-06-25-new-agents-paragraph-artifact-streaming-design.md"),
    Path("docs/superpowers/plans/2026-06-25-new-agents-paragraph-artifact-streaming.md"),
]
for path in paths:
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        if token in text:
            raise SystemExit(f"{path}: contains placeholder token {token}")
PY
```

Expected: `git diff --check` exits 0; `rg` returns no matches.

- [ ] **Step 4: Run full local automation before commit**

Run:

```bash
./scripts/test/test-local.sh all
```

Expected: PASS, unless an environment-only blocker is recorded with exact output and risk.

- [ ] **Step 5: Stage only this story**

Stage only New Agents streaming files, this spec/plan, and relevant todo updates. Do not stage existing intent-tester generated files.
