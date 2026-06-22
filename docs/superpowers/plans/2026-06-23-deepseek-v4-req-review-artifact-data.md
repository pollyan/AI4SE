# DeepSeek V4 REQ_REVIEW Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `REQ_REVIEW/REVIEW` 通过 `artifact_data` schema 和后端确定性 renderer 生成完整需求评审问题清单。

**Architecture:** 沿用现有 `artifact_data_renderers.py` 中按 workflow/stage 分派 schema 和 renderer 的模式，在共享 `agent_runtime.py` 中为 `REQ_REVIEW/REVIEW` 增加 structured output instruction 和支持开关。输出仍进入现有 `AgentTurnOutput`、artifact contract、typed SSE 和 run persistence，不新增任何 agent-specific runtime。

**Tech Stack:** Python 3.11、Pydantic v2、pytest、现有 New Agents backend contract/runtime tests。

---

## File Map

- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: 增加合法 REVIEW 数据、negative schema test、contract-valid renderer test。
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: 增加 REVIEW parse、instruction、retry prompt、raw stream renderer test。
- Modify `tools/new-agents/backend/artifact_data_renderers.py`: 增加 REVIEW schema、跨字段校验、renderer helper、dispatch 分支。
- Modify `tools/new-agents/backend/agent_runtime.py`: 增加 REVIEW instruction、support set、instruction dispatch。
- Modify `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: 更新当前进展与迁移顺序。

## Task 1: RED renderer contract tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`

- [ ] **Step 1: Add valid REVIEW fixture**

Add `VALID_REQ_REVIEW_ARTIFACT_DATA` after the TEST_DESIGN fixtures. Include `review_info`, `scope_items`, `quality_overview`, `issue_statistics`, `issue_groups`, `revision_suggestions`, and `stage_gate`.

- [ ] **Step 2: Add negative consistency test**

Add a test named `test_req_review_artifact_data_rejects_inconsistent_issue_statistics()` that sets `p0_count` to an incorrect value and expects `ReqReviewArtifactData.model_validate()` to raise `ValidationError` matching `issue_statistics`.

- [ ] **Step 3: Add deterministic contract test**

Add `test_render_req_review_artifact_data_is_deterministic_and_contract_valid()` that renders `REQ_REVIEW/REVIEW`, asserts both renders equal, asserts required title, `flowchart`, fenced `ai4se-visual`, and `"type": "score-matrix"`, then calls `validate_agent_turn()`.

- [ ] **Step 4: Run RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: fails because `ReqReviewArtifactData` or `REQ_REVIEW/REVIEW` renderer is not configured.

## Task 2: GREEN REVIEW schema and renderer

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] **Step 1: Add Pydantic models**

Add focused `StrictArtifactDataModel` subclasses for review info, scope item, quality overview, issue statistics, issue item, issue group, and revision suggestion. Use `Field(min_length=1)` for required arrays and `Field(ge=1, le=5)` for severity score.

- [ ] **Step 2: Add cross-field validator**

In `ReqReviewArtifactData`, validate that issue statistics match issue priorities and revision suggestion references point to existing issue IDs.

- [ ] **Step 3: Add renderer dispatch**

Add:

```python
elif (workflow_id, current_stage_id) == ("REQ_REVIEW", "REVIEW"):
    artifact_data = ReqReviewArtifactData.model_validate(payload["artifact_data"])
    markdown = render_req_review_review_markdown(artifact_data)
```

- [ ] **Step 4: Add renderer helpers**

Create `render_req_review_review_markdown()` and helper renderers for review info, scope, quality overview, quality flowchart, issue statistics plus score matrix, issue groups, revision suggestions, and stage gate.

- [ ] **Step 5: Run GREEN renderer tests**

Run the renderer test file command from Task 1. Expected: pass.

## Task 3: RED runtime tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [ ] **Step 1: Import REVIEW fixture**

Import `VALID_REQ_REVIEW_ARTIFACT_DATA` from `test_artifact_data_renderers`.

- [ ] **Step 2: Add parse test**

Add `test_parse_agent_turn_output_text_renders_req_review_artifact_data()` that parses JSON containing `artifact_data`, `stage_action` targeting `REPORT`, and asserts rendered Markdown starts with `# 需求评审问题清单` and contains `"type": "score-matrix"`.

- [ ] **Step 3: Add instruction and retry tests**

Assert `build_structured_output_instruction("REQ_REVIEW", "REVIEW")` contains `artifact_data`, `issue_groups`, `score-matrix`, and `"target_stage_id": "REPORT"`, and does not contain `artifact_update.markdown`. Assert retry prompt requests `artifact_data` fix and not Markdown rewrite.

- [ ] **Step 4: Add raw stream final render test**

Add a DeepSeek raw stream test that yields REVIEW artifact_data and asserts final output is rendered before final validation.

- [ ] **Step 5: Run RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -q
```

Expected: fails because runtime support set and instruction dispatch do not include `REQ_REVIEW/REVIEW`.

## Task 4: GREEN runtime support

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [ ] **Step 1: Add REVIEW instruction**

Add `REQ_REVIEW_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` after DELIVERY instruction. The JSON example must use `artifact_data`, `issue_statistics`, `issue_groups`, `stage_action` targeting `REPORT`, and warn not to output Markdown, tables, Mermaid, or `score-matrix` fenced JSON.

- [ ] **Step 2: Add support and dispatch**

Include `("REQ_REVIEW", "REVIEW")` in `supports_artifact_data_rendering()` and return the REVIEW instruction in `build_structured_output_instruction()`.

- [ ] **Step 3: Run runtime tests**

Run the runtime test command from Task 3. Expected: pass.

## Task 5: Docs and expanded verification

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [ ] **Step 1: Update todo progress**

Add that `REQ_REVIEW/REVIEW` is completed and update migration order so `REQ_REVIEW/REPORT` and other workflows remain pending.

- [ ] **Step 2: Run focused verification**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q
```

- [ ] **Step 3: Run expanded shared runtime/API verification**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py -q
```

- [ ] **Step 4: Compile touched backend modules**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py
```

- [ ] **Step 5: Stage and whitespace check**

Run:

```bash
git add docs/superpowers/specs/2026-06-23-deepseek-v4-req-review-artifact-data-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-req-review-artifact-data.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
git diff --cached --check
```

Expected: no output from `git diff --cached --check`.

## Self-Review

- Spec coverage: tasks cover schema, renderer, runtime instruction, retry, tests, docs, and verification.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: fixture and model names use `ReqReviewArtifactData`, `issue_statistics`, `issue_groups`, `revision_suggestions`, matching planned tests and implementation.
