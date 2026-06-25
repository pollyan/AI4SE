# New Agents 需求澄清段落级流式收束 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收束 `TEST_DESIGN/CLARIFY` 的段落级正式 Artifact 流式输出，让需求分析文档在 final 前按已完成章节递增显示，并保持最终完整产物和阶段续写行为稳定。

**Architecture:** 继续复用共享 `/api/agent/runs/stream` typed SSE、Agent Runtime、deterministic `artifact_data` renderer、Zustand store 和现有 ArtifactPane。后端只解析已闭合的 `artifact_data` 顶层字段并渲染已验证章节；前端不新增 workflow 专属渲染路径。

**Tech Stack:** Python 3.11, Pydantic, pytest, TypeScript 5.x, React 19, Vitest.

---

### Task 1: Backend Partial CLARIFY Contract

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [x] **Step 1: Verify the focused CLARIFY streaming test exists**

Confirm `tools/new-agents/backend/tests/test_agent_runtime.py` contains `test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data` with these assertions:

```python
assert len(partial_markdowns) >= 2
assert partial_markdowns[0].startswith("# 需求分析文档")
assert "## 1. 需求事实清单" in partial_markdowns[0]
assert "## 2. 被测系统与边界" not in partial_markdowns[0]
assert "## 2. 被测系统与边界" in partial_markdowns[1]
assert "## 3. 业务规则与数据状态" not in partial_markdowns[1]
assert isinstance(outputs[-1], AgentTurnOutput)
assert "## 3. 业务规则与数据状态" in outputs[-1].artifact_update.markdown
```

- [x] **Step 2: Run the focused backend test**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -k "paragraph_level_clarify_artifact_data" -q
```

Expected: PASS if the existing dirty implementation is already coherent; otherwise fail only on the CLARIFY partial renderer expectations.

Result: PASS with `.venv/bin/python`; an initial system `python3` run was interrupted because it produced no output under Python 3.14.2.

- [x] **Step 3: Fix only the CLARIFY partial renderer if needed**

If Step 2 fails, update `render_partial_agent_turn_from_artifact_data(...)` and `render_partial_test_design_clarify_markdown(...)` so:

```python
if (workflow_id, current_stage_id) == ("TEST_DESIGN", "CLARIFY"):
    markdown = render_partial_test_design_clarify_markdown(payload["artifact_data"])
elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "STRATEGY"):
    markdown = render_partial_test_design_strategy_markdown(payload["artifact_data"])
else:
    return None
```

and `render_partial_test_design_clarify_markdown(...)` returns `None` until `document_info` and `requirement_facts` validate, then appends sections in this order:

```python
[
    ("system_boundaries", _render_system_boundaries, SystemBoundary),
    ("business_rules", _render_business_rules, BusinessRule),
    ("flow_links", _render_flow_links, FlowLink),
    ("clarification_questions", _render_clarification_questions, ClarificationQuestion),
    ("quality_requirements", _render_quality_requirements, QualityRequirement),
    ("downstream_inputs", _render_downstream_inputs, DownstreamInput),
    ("stage_gate", _render_stage_gate, StageGateCheck),
]
```

Do not emit debug progress Markdown or partial invalid sections.

Result: No additional code change was needed after the existing dirty implementation passed the focused test.

- [x] **Step 4: Re-run the focused backend test**

Run the same command from Step 2.

Expected: PASS.

Result: PASS.

### Task 2: Frontend Stage Continuation Regression

**Files:**
- Modify: `tools/new-agents/frontend/src/services/chatService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`

- [x] **Step 1: Verify the continuation behavior**

Confirm `handleConfirmStageTransition()` appends the user-visible confirmation message, then calls:

```ts
await handleSend(STAGE_CONTINUATION_PROMPT, {
    appendUserMessage: false,
    useDraftAttachments: false,
});
```

Expected: the user history records `已确认进入<阶段名>` once, while the model receives `请继续生成当前阶段产出物`.

- [x] **Step 2: Run the focused frontend service tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/chatService.test.ts
```

Expected: PASS.

Result: PASS, 60 tests.

- [x] **Step 3: Fix only service/test mismatch if needed**

If Step 2 fails, align `chatService.ts` and `chatService.test.ts` to the behavior in Step 1. Do not change ChatPane layout, Agent Runtime transport, or workflow-specific prompt branches.

Result: No additional service/test change was needed after the focused tests passed.

### Task 3: Focused Cross-Layer Verification

**Files:**
- No new source files expected beyond Tasks 1-2.

- [x] **Step 1: Run backend partial streaming regression set**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -k "paragraph_level_clarify_artifact_data or paragraph_level_strategy_artifact_data or artifact_data_before_final_output" -q
```

Expected: PASS.

Result: PASS, 18 tests.

- [x] **Step 2: Run frontend service regression**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/chatService.test.ts
```

Expected: PASS.

Result: PASS, 60 tests.

- [x] **Step 3: Run diff hygiene**

Run:

```bash
git diff --check
```

Expected: exits 0.

Result: PASS.

### Task 4: Records, Todo Status, and Commit Boundary

**Files:**
- Modify: `docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md`
- Modify: `docs/superpowers/specs/2026-06-25-new-agents-clarify-paragraph-streaming-closure-design.md`
- Modify: `docs/superpowers/plans/2026-06-25-new-agents-clarify-paragraph-streaming-closure.md`

- [x] **Step 1: Update the incremental-rendering todo**

Append a short progress note to `docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md`:

```markdown
## 2026-06-25 进展：需求澄清段落级流式收束

- 已收束 `TEST_DESIGN/CLARIFY` 的 `artifact_data` partial renderer：当 `requirement_facts`、`system_boundaries` 等顶层字段在 raw JSON stream 中完整闭合时，后端可在 final 前发出正式 Markdown 增量。
- 这不是完整 `artifact_patch` / `changed_sections` 协议；长文档局部 patch、块级 memoized rendering、协作状态与导出回归仍保留在本 todo 后续能力包中。
- 验证：记录本轮实际运行命令和结果。
```

Result: Updated with focused verification results and retained full patch protocol as a later capability package.

- [x] **Step 2: Run doc placeholder check**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

tokens = ["TO" + "DO", "TB" + "D", "待" + "补充", "PLACE" + "HOLDER", "未" + "定"]
paths = [
    Path("docs/superpowers/specs/2026-06-25-new-agents-clarify-paragraph-streaming-closure-design.md"),
    Path("docs/superpowers/plans/2026-06-25-new-agents-clarify-paragraph-streaming-closure.md"),
]
for path in paths:
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        if token in text:
            raise SystemExit(f"{path}: contains placeholder token {token}")
PY
```

Expected: no output.

Result: PASS, no output.

- [x] **Step 3: Decide full local automation**

Because this story touches backend runtime and frontend service behavior, run full local automation before commit unless the environment blocks it:

```bash
./scripts/test/test-local.sh all
```

Expected: PASS. If it fails due to environment-only constraints, record exact output and do not claim full pass.

Result: `./scripts/test/test-local.sh all` failed in sandbox. It passed Intent Tester API tests, code quality check, Common Frontend lint/build, New Agents frontend tests, and New Agents backend tests. It failed unrelated/sandbox-sensitive suites: Intent Tester proxy could not bind/listen reliably (`listen EPERM: operation not permitted 0.0.0.0:3002` and proxy integration failures), and New Agents Browser E2E could not launch Chromium (`bootstrap_check_in ... Permission denied (1100)`). Two attempts to rerun the full script with elevated permissions timed out in automatic approval review. Additional relevant checks passed: `.venv/bin/python -m py_compile tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py`, `cd tools/new-agents/frontend && npm run lint`, and `cd tools/new-agents/frontend && npm run build`.

- [ ] **Step 4: Stage only this story**

Stage:

```bash
git add \
  tools/new-agents/backend/artifact_data_renderers.py \
  tools/new-agents/backend/tests/test_agent_runtime.py \
  tools/new-agents/frontend/src/services/chatService.ts \
  tools/new-agents/frontend/src/services/__tests__/chatService.test.ts \
  docs/superpowers/specs/2026-06-25-new-agents-clarify-paragraph-streaming-closure-design.md \
  docs/superpowers/plans/2026-06-25-new-agents-clarify-paragraph-streaming-closure.md \
  docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md
```

Do not stage:

```bash
dist/intent-test-proxy.zip
tools/intent-tester/frontend/static/intent-test-proxy.zip
tools/intent-tester/test-results/proxy/junit.xml
```

- [ ] **Step 5: Commit**

Run:

```bash
git commit -m "feat: 收束需求澄清产物段落级流式"
```

Expected: commit succeeds and contains only this user story.
