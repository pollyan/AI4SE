# DeepSeek V4 DELIVERY Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `TEST_DESIGN/DELIVERY` 通过 `artifact_data` schema 和后端确定性 renderer 生成完整测试设计交付文档。

**Architecture:** 沿用已有 `artifact_data_renderers.py` 单文件 schema/renderer 模式，在共享 `agent_runtime.py` 中为 DELIVERY 增加 structured output instruction 和支持开关。输出仍进入现有 `AgentTurnOutput`、artifact contract、typed SSE 和 run persistence，不新增任何 agent-specific runtime。

**Tech Stack:** Python 3.11、Pydantic v2、pytest、现有 New Agents backend contract/runtime tests。

---

## File Map

- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: 增加合法 DELIVERY 数据、negative schema test、contract-valid renderer test。
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: 增加 DELIVERY parse、instruction、retry prompt、raw stream renderer test。
- Modify `tools/new-agents/backend/artifact_data_renderers.py`: 增加 DELIVERY schema、跨字段校验、renderer helper、dispatch 分支。
- Modify `tools/new-agents/backend/agent_runtime.py`: 增加 DELIVERY instruction、support set、instruction dispatch。
- Modify `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: 更新当前进展与迁移顺序。

## Task 1: RED renderer contract tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`

- [ ] **Step 1: Add valid DELIVERY fixture and expected renderer test**

Add `VALID_DELIVERY_ARTIFACT_DATA` near the existing CASES fixture. The fixture must include non-empty arrays for document info, metrics, summaries, coverage map, open risks, checklist, signoffs, and change log.

Add:

```python
def test_render_delivery_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已整理测试设计交付文档。",
            "artifact_data": VALID_DELIVERY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已整理测试设计交付文档。",
            "artifact_data": VALID_DELIVERY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update is not None
    markdown = first.artifact_update.markdown
    assert "# 测试设计文档" in markdown
    assert '"type": "coverage-map"' in markdown
    validate_agent_turn(first, workflow_id="TEST_DESIGN", current_stage_id="DELIVERY")
```

- [ ] **Step 2: Add negative consistency test**

Add:

```python
def test_delivery_artifact_data_rejects_inconsistent_case_totals():
    invalid = {
        **VALID_DELIVERY_ARTIFACT_DATA,
        "delivery_metrics": {
            **VALID_DELIVERY_ARTIFACT_DATA["delivery_metrics"],
            "total_cases": 99,
        },
    }

    with pytest.raises(ValueError, match="total_cases"):
        render_agent_turn_from_artifact_data(
            {
                "chat": "已整理测试设计交付文档。",
                "artifact_data": invalid,
                "stage_action": None,
                "warnings": [],
            },
            workflow_id="TEST_DESIGN",
            current_stage_id="DELIVERY",
        )
```

- [ ] **Step 3: Run RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: fails because DELIVERY renderer is not configured or schema symbols are missing.

## Task 2: GREEN delivery schema and renderer

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] **Step 1: Add Pydantic models**

Add focused `StrictArtifactDataModel` subclasses for delivery metrics, summaries, coverage rows, open risks, signoffs, and change log. Use `Field(min_length=1)` for required arrays and `Field(ge=0)` for counts.

- [ ] **Step 2: Add cross-field validator**

In `DeliveryArtifactData`, validate:

```python
case_total = sum(item.case_count for item in self.case_summary_items)
if self.delivery_metrics.total_cases != case_total:
    raise ValueError("delivery_metrics.total_cases must match case_summary_items total_cases")
```

Also validate high risk count from open risks.

- [ ] **Step 3: Add renderer dispatch**

Add:

```python
elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "DELIVERY"):
    artifact_data = DeliveryArtifactData.model_validate(payload["artifact_data"])
    markdown = render_test_design_delivery_markdown(artifact_data)
```

- [ ] **Step 4: Add renderer helpers**

Create `render_test_design_delivery_markdown()` that returns the exact required headings and uses `_markdown_table()` and `_json_fence()` patterns already present in the file.

- [ ] **Step 5: Run GREEN renderer tests**

Run the renderer test file command from Task 1. Expected: pass.

## Task 3: RED runtime tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [ ] **Step 1: Import DELIVERY fixture**

Import `VALID_DELIVERY_ARTIFACT_DATA` from `test_artifact_data_renderers`.

- [ ] **Step 2: Add parse test**

Add:

```python
def test_parse_agent_turn_output_text_renders_delivery_artifact_data():
    output = parse_agent_turn_output_text(
        json.dumps(
            {
                "chat": "已整理测试设计交付文档。",
                "artifact_data": VALID_DELIVERY_ARTIFACT_DATA,
                "stage_action": None,
                "warnings": [],
            }
        ),
        deps=AgentTurnValidationDeps(
            workflow_id="TEST_DESIGN",
            current_stage_id="DELIVERY",
        ),
    )

    assert output.artifact_update is not None
    assert "# 测试设计文档" in output.artifact_update.markdown
    assert '"type": "coverage-map"' in output.artifact_update.markdown
```

- [ ] **Step 3: Add instruction and retry tests**

Assert `build_structured_output_instruction("TEST_DESIGN", "DELIVERY")` contains `artifact_data`, `coverage_map`, and does not contain `artifact_update`. Assert `build_raw_json_retry_prompt(..., current_stage_id="DELIVERY")` asks for `artifact_data` fix and not Markdown rewrite.

- [ ] **Step 4: Run RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -q
```

Expected: fails because runtime support set and instruction dispatch do not include DELIVERY.

## Task 4: GREEN runtime support

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [ ] **Step 1: Add DELIVERY instruction**

Add `DELIVERY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` after CASES instruction. The JSON example must use `artifact_data`, `delivery_metrics`, `coverage_map`, `stage_action: null`, and warn not to output Markdown, tables, Mermaid, or `coverage-map` fenced JSON.

- [ ] **Step 2: Add support and dispatch**

Include `("TEST_DESIGN", "DELIVERY")` in `supports_artifact_data_rendering()` and return the DELIVERY instruction in `build_structured_output_instruction()`.

- [ ] **Step 3: Run runtime tests**

Run the runtime test command from Task 3. Expected: pass.

## Task 5: Docs and expanded verification

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [ ] **Step 1: Update todo progress**

Add that `TEST_DESIGN/DELIVERY` is completed and update migration order so other workflows remain pending.

- [ ] **Step 2: Run focused verification**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q
```

- [ ] **Step 3: Run expanded shared runtime/API verification**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_test_asset_parsing.py tools/new-agents/backend/tests/test_test_assets.py -q
```

- [ ] **Step 4: Compile touched backend modules**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py
```

- [ ] **Step 5: Stage and whitespace check**

Run:

```bash
git add docs/superpowers/specs/2026-06-23-deepseek-v4-delivery-artifact-data-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-delivery-artifact-data.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
git diff --cached --check
```

Expected: no output from `git diff --cached --check`.

## Self-Review

- Spec coverage: tasks cover schema, renderer, runtime instruction, retry, tests, docs, and verification.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: fixture and model names use `DeliveryArtifactData`, `delivery_metrics`, `coverage_map`, `case_summary_items`, matching planned tests and implementation.
