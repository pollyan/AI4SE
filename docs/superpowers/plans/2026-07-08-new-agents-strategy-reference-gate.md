# TEST_DESIGN STRATEGY 内部引用门禁 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `TEST_DESIGN/STRATEGY` 的 `QG/R/TS/TP` 内部引用在 final validation 和 partial preview 中保持自洽。

**Architecture:** 在 `StrategyArtifactData` after validator 中增加 ID 唯一性和引用完整性校验；partial renderer 将测试技术、测试分层、测试点三个强相关章节成组输出，避免预览最终会失败的引用链。共享 Agent Runtime、SSE、store、ArtifactPane 和视觉协议不变。

**Tech Stack:** Python 3.11, Pydantic v2, pytest, TypeScript prompt template, New Agents shared Agent Runtime.

---

### Task 1: 写 RED 测试

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [x] **Step 1: 增加 final validator 失败测试**

在 STRATEGY artifact-data 测试附近加入：

```python
def test_strategy_artifact_data_rejects_duplicate_strategy_ids():
    invalid = copy.deepcopy(VALID_STRATEGY_ARTIFACT_DATA)
    invalid["quality_goals"].append({**invalid["quality_goals"][0]})

    with pytest.raises(ValidationError, match="quality_goals"):
        StrategyArtifactData.model_validate(invalid)


def test_strategy_artifact_data_rejects_unknown_test_point_references():
    invalid = copy.deepcopy(VALID_STRATEGY_ARTIFACT_DATA)
    invalid["test_points"][0]["quality_goal"] = "QG-404"
    invalid["test_points"][0]["risk"] = "R-404"
    invalid["test_points"][0]["technique"] = "TS-404"

    with pytest.raises(ValidationError, match="test_points"):
        StrategyArtifactData.model_validate(invalid)


def test_strategy_artifact_data_rejects_unknown_technique_and_layer_references():
    invalid = copy.deepcopy(VALID_STRATEGY_ARTIFACT_DATA)
    invalid["test_techniques"][0]["target"] = "QG-404 / R-404"
    invalid["test_techniques"][0]["applies_to"] = "R-404 / TP-404"
    invalid["test_layers"][0]["related"] = "R-404 / TP-404"

    with pytest.raises(ValidationError, match="test_techniques"):
        StrategyArtifactData.model_validate(invalid)
```

- [x] **Step 2: 增加 partial 分组与引用门禁测试**

在 `test_render_partial_test_design_strategy_markdown` 附近加入：

```python
def test_render_partial_strategy_artifact_data_waits_for_references_before_sections_four_to_six():
    payload = {
        "chat": "我正在生成测试策略。",
        "artifact_data": {
            "document_info": VALID_STRATEGY_ARTIFACT_DATA["document_info"],
            "strategy_summary": VALID_STRATEGY_ARTIFACT_DATA["strategy_summary"],
            "quality_goals": VALID_STRATEGY_ARTIFACT_DATA["quality_goals"],
            "risks": VALID_STRATEGY_ARTIFACT_DATA["risks"],
            "test_techniques": VALID_STRATEGY_ARTIFACT_DATA["test_techniques"],
            "test_layers": VALID_STRATEGY_ARTIFACT_DATA["test_layers"],
        },
        "stage_action": None,
        "warnings": [],
    }

    output = render_partial_agent_turn_from_artifact_data(
        payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert output is not None
    assert "## 3. 风险识别与 FMEA" in output.artifact_update.markdown
    assert "## 4. 测试技术选型" not in output.artifact_update.markdown

    payload["artifact_data"]["test_points"] = VALID_STRATEGY_ARTIFACT_DATA["test_points"]
    output = render_partial_agent_turn_from_artifact_data(
        payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert output is not None
    assert "## 4. 测试技术选型" in output.artifact_update.markdown
    assert "## 5. 测试分层策略" in output.artifact_update.markdown
    assert "## 6. 测试点拓扑" in output.artifact_update.markdown


def test_render_partial_strategy_artifact_data_skips_sections_four_to_six_with_unknown_reference():
    invalid_techniques = copy.deepcopy(VALID_STRATEGY_ARTIFACT_DATA["test_techniques"])
    invalid_techniques[0]["applies_to"] = "R-404 / TP-404"
    payload = {
        "chat": "我正在生成测试策略。",
        "artifact_data": {
            "document_info": VALID_STRATEGY_ARTIFACT_DATA["document_info"],
            "strategy_summary": VALID_STRATEGY_ARTIFACT_DATA["strategy_summary"],
            "quality_goals": VALID_STRATEGY_ARTIFACT_DATA["quality_goals"],
            "risks": VALID_STRATEGY_ARTIFACT_DATA["risks"],
            "test_techniques": invalid_techniques,
            "test_layers": VALID_STRATEGY_ARTIFACT_DATA["test_layers"],
            "test_points": VALID_STRATEGY_ARTIFACT_DATA["test_points"],
        },
        "stage_action": None,
        "warnings": [],
    }

    output = render_partial_agent_turn_from_artifact_data(
        payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert output is not None
    assert "## 3. 风险识别与 FMEA" in output.artifact_update.markdown
    assert "## 4. 测试技术选型" not in output.artifact_update.markdown
```

- [x] **Step 3: 增加 prompt 与 raw streaming RED 测试**

在 STRATEGY prompt 测试附近补充断言：

```python
def test_strategy_structured_output_instruction_requests_internal_id_references():
    instruction = build_structured_output_instruction("TEST_DESIGN", "STRATEGY")

    assert "test_points.quality_goal、test_points.risk、test_points.technique" in instruction
    assert "只能引用 artifact_data 中已定义的 QG/R/TS ID" in instruction
```

在 raw JSON streaming 测试附近加入：

```python
def test_runtime_raw_json_stream_turn_waits_for_strategy_references_before_sections_four_to_six(monkeypatch):
    final_json = json.dumps(
        {
            "chat": "我正在逐段形成风险驱动测试策略。",
            "artifact_data": VALID_STRATEGY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )

    def prefix_after_artifact_data_member(member_name: str) -> str:
        decoder = json.JSONDecoder()
        artifact_key_index = final_json.index('"artifact_data"')
        index = final_json.index("{", artifact_key_index) + 1
        while index < len(final_json):
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            key, key_end = decoder.raw_decode(final_json[index:])
            assert isinstance(key, str)
            index += key_end
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            assert final_json[index] == ":"
            index += 1
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            _, value_end = decoder.raw_decode(final_json[index:])
            index += value_end
            if key == member_name:
                return final_json[:index]
            while index < len(final_json) and final_json[index].isspace():
                index += 1
            if index < len(final_json) and final_json[index] == ",":
                index += 1
        raise AssertionError(f"artifact_data member not found: {member_name}")

    risks_prefix = prefix_after_artifact_data_member("risks")
    techniques_prefix = prefix_after_artifact_data_member("test_techniques")
    layers_prefix = prefix_after_artifact_data_member("test_layers")
    points_prefix = prefix_after_artifact_data_member("test_points")
    chunks = [
        risks_prefix,
        techniques_prefix[len(risks_prefix) :],
        layers_prefix[len(techniques_prefix) :],
        points_prefix[len(layers_prefix) :],
        final_json[len(points_prefix) :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        yield from chunks

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="你是测试专家。",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "请制定测试策略",
            workflow_id="TEST_DESIGN",
            current_stage_id="STRATEGY",
        )
    )
    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert len(partial_markdowns) >= 2
    assert "## 3. 风险识别与 FMEA" in partial_markdowns[0]
    assert "## 4. 测试技术选型" not in partial_markdowns[0]
    assert "## 4. 测试技术选型" in partial_markdowns[-1]
    assert "## 6. 测试点拓扑" in partial_markdowns[-1]
    assert isinstance(outputs[-1], AgentTurnOutput)
```

- [x] **Step 4: 运行 RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_duplicate_strategy_ids tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_unknown_test_point_references tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_unknown_technique_and_layer_references tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_strategy_artifact_data_waits_for_references_before_sections_four_to_six tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_strategy_artifact_data_skips_sections_four_to_six_with_unknown_reference tools/new-agents/backend/tests/test_agent_runtime.py::test_strategy_structured_output_instruction_requests_internal_id_references tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_waits_for_strategy_references_before_sections_four_to_six -q
```

Expected before implementation: selected tests fail because STRATEGY currently does not validate internal references and partial renderer shows sections 4-5 before `test_points`.

Result before implementation: `6 failed, 1 passed`. Failures confirmed missing final reference validators, early partial preview of sections 4-5 before `test_points`, and missing prompt reference rule. The raw streaming test already passed because the old stream only emitted the final grouped state.

### Task 2: 实现 STRATEGY ID 与引用门禁

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [x] **Step 1: 增加引用提取和校验 helper**

Add helpers near STRATEGY models:

```python
_STRATEGY_REFERENCE_PATTERN = re.compile(r"\b(QG|R|TS|TP)-\d+\b")


def _extract_strategy_references(value: str) -> dict[str, set[str]]:
    references: dict[str, set[str]] = {"QG": set(), "R": set(), "TS": set(), "TP": set()}
    for prefix, full_id in _STRATEGY_REFERENCE_PATTERN.findall(value):
        references[prefix].add(full_id)
    return references
```

Use a direct `for match in _STRATEGY_REFERENCE_PATTERN.finditer(value)` implementation if needed so `full_id = match.group(0)`.

Add helpers for uniqueness and reference checks:

```python
def _validate_unique_strategy_ids(label: str, values: list[str]) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{label} contains duplicate ids")


def _validate_strategy_reference_field(
    field_label: str,
    value: str,
    allowed_prefixes: set[str],
    known_ids_by_prefix: dict[str, set[str]],
) -> None:
    references = _extract_strategy_references(value)
    used_allowed = set()
    unknown = []
    for prefix in allowed_prefixes:
        used_allowed.update(references[prefix])
        unknown.extend(
            sorted(item for item in references[prefix] if item not in known_ids_by_prefix[prefix])
        )
    if not used_allowed:
        raise ValueError(f"{field_label} must reference existing {'/'.join(sorted(allowed_prefixes))} ids")
    if unknown:
        raise ValueError(f"{field_label} references unknown ids: {', '.join(unknown)}")
```

- [x] **Step 2: 在 `StrategyArtifactData` after validator 中调用门禁**

Add `@model_validator(mode="after")`:

```python
@model_validator(mode="after")
def validate_strategy_references(self) -> "StrategyArtifactData":
    goal_ids = [item.goal_id for item in self.quality_goals]
    risk_ids = [item.risk_id for item in self.risks]
    technique_ids = [item.technique_id for item in self.test_techniques]
    point_ids = [item.point_id for item in self.test_points]
    _validate_unique_strategy_ids("quality_goals", goal_ids)
    _validate_unique_strategy_ids("risks", risk_ids)
    _validate_unique_strategy_ids("test_techniques", technique_ids)
    _validate_unique_strategy_ids("test_points", point_ids)
    known_ids_by_prefix = {
        "QG": set(goal_ids),
        "R": set(risk_ids),
        "TS": set(technique_ids),
        "TP": set(point_ids),
    }
    for item in self.test_techniques:
        _validate_strategy_reference_field(
            "test_techniques.target",
            item.target,
            {"QG", "R", "TP"},
            known_ids_by_prefix,
        )
        _validate_strategy_reference_field(
            "test_techniques.applies_to",
            item.applies_to,
            {"R", "TP"},
            known_ids_by_prefix,
        )
    for item in self.test_layers:
        _validate_strategy_reference_field(
            "test_layers.related",
            item.related,
            {"QG", "R", "TP"},
            known_ids_by_prefix,
        )
    for item in self.test_points:
        _validate_strategy_reference_field(
            "test_points.quality_goal",
            item.quality_goal,
            {"QG"},
            known_ids_by_prefix,
        )
        _validate_strategy_reference_field(
            "test_points.risk",
            item.risk,
            {"R"},
            known_ids_by_prefix,
        )
        _validate_strategy_reference_field(
            "test_points.technique",
            item.technique,
            {"TS"},
            known_ids_by_prefix,
        )
    return self
```

- [x] **Step 3: 更新 STRATEGY partial renderer**

Inside `render_partial_test_design_strategy_markdown()`:

1. validate and store `quality_goals` before rendering section 2;
2. validate and store `risks` before rendering section 3;
3. if any of `test_techniques`, `test_layers`, or `test_points` is missing, return sections through risks;
4. validate all three lists and call the same reference helper before rendering sections 4-6;
5. if validation fails, return sections through risks.

Keep tradeoffs and stage gate behavior unchanged after section 6.

### Task 3: 同步 STRATEGY prompt

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`
- Modify: `tools/new-agents/frontend/src/core/prompts/test_design/strategy.ts`

- [x] **Step 1: Update backend structured output instruction**

Append the STRATEGY consistency sentence:

```text
test_points.quality_goal、test_points.risk、test_points.technique 只能引用 artifact_data 中已定义的 QG/R/TS ID；test_techniques.target、test_techniques.applies_to、test_layers.related 只能引用 artifact_data 中已定义的 QG/R/TP ID。
```

- [x] **Step 2: Update frontend STRATEGY prompt**

Add a bullet:

```typescript
所有 QG/R/TS/TP 引用必须引用同一份策略蓝图中已经定义的 ID；不要在测试点、测试技术或分层策略里编造未定义 ID。
```

### Task 4: GREEN、回归和记录

**Files:**
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- Modify: this plan

- [x] **Step 1: Run GREEN**

Run the RED command again.

Expected: all selected tests pass.

Result: `7 passed`.

- [x] **Step 2: Run STRATEGY focused regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_rejects_inconsistent_rpn tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_computes_missing_rpn_for_generated_visuals tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_mermaid_labels_are_normalized_for_special_characters tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_strategy_artifact_data_is_deterministic_and_contract_valid tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_strategy_artifact_data_without_model_rpn tools/new-agents/backend/tests/test_agent_runtime.py::test_strategy_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_strategy_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_strategy_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data -q
```

Expected: all selected STRATEGY tests pass.

Result: `10 passed`.

- [x] **Step 3: Run backend shared regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: backend shared regression passes.

Result: `371 passed`.

- [x] **Step 4: Update todo execution record**

Add a new execution record for “第 6 轮第二个纵切：TEST_DESIGN/STRATEGY 内部引用门禁”, including RED/GREEN and regression results. Update the top status and progress bullets for:

- 收敛 ID 与引用关系
- 针对高失败阶段做纵切专项修复

### Task 5: 全量验证、提交和推送

**Files:**
- Modify: this plan

- [x] **Step 1: Run New Agents and full local validation**

Run:

```bash
./scripts/test/test-local.sh new-agents
./scripts/test/test-local.sh all
```

If default sandbox fails on browser or port permissions, rerun with approved non-sandbox execution and record both the environment failure and rerun result.

New Agents result:

```bash
./scripts/test/test-local.sh new-agents
```

Result: New Agents Frontend `718 passed`; New Agents Backend `624 passed, 1 deselected`. Existing `ArtifactPane.test.tsx` React `act(...)` warning still appeared but did not fail the suite.

Full validation result:

```bash
./scripts/test/test-local.sh all
```

Default sandbox result: failed on environment permissions, not product assertions. Failure points were MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` and Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`.

Approved non-sandbox rerun, first attempt: Intent Tester API `294 passed`; flake8 severe check passed; MidScene proxy `17 passed`; Common Frontend lint/build passed; New Agents Frontend `718 passed`; New Agents Backend `624 passed, 1 deselected`; Browser E2E `1 failed, 10 passed, 10 deselected`. The failure was `test_alex_final_artifact_passes_optional_llm_judge`, with score `75`, below the playbook threshold of `80`.

Unplanned quality-gate fix: the Alex `VALUE_DISCOVERY/BLUEPRINT` browser mock was missing business delivery -> metrics -> retrospective feedback, priority rationale, analysis method, retrospective journey coverage, and interaction acceptance criteria. Updated `tests/e2e/new_agents_browser/sse_mock.py` and recorded the fix in `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`.

Targeted recheck:

```bash
.venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py::test_alex_final_artifact_passes_optional_llm_judge -q
```

Result: `1 passed`.

Approved non-sandbox rerun, second attempt:

```bash
./scripts/test/test-local.sh all
```

Result: passed. Key results: Intent Tester API `294 passed`; flake8 severe check passed; MidScene proxy `17 passed`; Common Frontend lint/build passed; New Agents Frontend `718 passed`; New Agents Backend `624 passed, 1 deselected`; New Agents Browser E2E `11 passed, 10 deselected`.

- [x] **Step 2: Run diff checks**

Run:

```bash
rg -n "T[B]D|TO[ ]?DO|待[ ]?补|未[ ]?决|place[ ]?holder" docs/superpowers/specs/2026-07-08-new-agents-strategy-reference-gate-design.md docs/superpowers/plans/2026-07-08-new-agents-strategy-reference-gate.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md
git diff --check -- tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/frontend/src/core/prompts/test_design/strategy.ts docs/superpowers/specs/2026-07-08-new-agents-strategy-reference-gate-design.md docs/superpowers/plans/2026-07-08-new-agents-strategy-reference-gate.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md tests/e2e/new_agents_browser/sse_mock.py docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md
```

Stage the Alex judge evidence fix separately, then stage this STRATEGY slice and run:

```bash
git diff --cached --check
git diff --cached --name-only
```

Results:

- Placeholder scan: no matches.
- `git diff --check` for STRATEGY and Alex judge files: passed.
- Alex judge evidence staged check: `git diff --cached --check` passed; staged files were `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md` and `tests/e2e/new_agents_browser/sse_mock.py`.
- STRATEGY staged check: `git diff --cached --check` passed; staged files were this plan, the STRATEGY design spec, the structured-artifact todo, backend renderer/runtime/tests, and frontend STRATEGY prompt.

- [ ] **Step 3: Commit and push**

Commit messages:

```bash
git commit -m "test(new-agents): 补强Alex蓝图评审证据"
git commit -m "fix(new-agents): 收紧Lisa策略引用门禁"
git push
```

After push, verify:

```bash
git rev-parse HEAD
git rev-parse @{u}
```

Expected: both SHAs match.
