# TEST_DESIGN CASES 用例统计后端化与引用门禁 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `TEST_DESIGN/CASES` 不再要求模型维护用例统计，并避免 partial preview 展示未知 `case_id` 引用章节。

**Architecture:** 在 `CasesArtifactData` validator 中派生缺省 `case_statistics`，复用 case_id helper 同时保护 final validation 与 partial renderer。正式 artifact 标题和共享 Agent Runtime 不变，阶段差异只落在 schema、renderer、prompt 和测试。

**Tech Stack:** Python 3.11, Pydantic v2, pytest, TypeScript prompt template, New Agents shared Agent Runtime.

---

### Task 1: 写 RED 测试

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [x] **Step 1: 增加 CASES 派生统计和 case_id 引用测试**

在 `test_cases_artifact_data_rejects_inconsistent_statistics` 附近加入：

```python
def test_cases_artifact_data_derives_statistics_when_missing():
    payload = copy.deepcopy(VALID_CASES_ARTIFACT_DATA)
    payload.pop("case_statistics")

    data = CasesArtifactData.model_validate(payload)

    assert data.case_statistics.total == 2
    assert data.case_statistics.p0_count == 1
    assert data.case_statistics.p1_count == 1
    assert data.case_statistics.p2_count == 0


def test_cases_artifact_data_rejects_unknown_automation_candidate_case_reference():
    invalid = copy.deepcopy(VALID_CASES_ARTIFACT_DATA)
    invalid["automation_candidates"][0]["case_id"] = "TC-404"

    with pytest.raises(ValidationError, match="automation_candidates"):
        CasesArtifactData.model_validate(invalid)
```

- [x] **Step 2: 增加 CASES partial 派生统计测试**

替换或扩展现有 `test_render_partial_cases_artifact_data_builds_formal_incremental_markdown_and_patch`，新增明确行为：

```python
def test_render_partial_cases_artifact_data_derives_statistics_from_case_groups():
    bases_only_payload = {
        "chat": "我正在生成测试用例集。",
        "artifact_data": {
            "document_info": VALID_CASES_ARTIFACT_DATA["document_info"],
            "design_bases": VALID_CASES_ARTIFACT_DATA["design_bases"],
        },
        "stage_action": None,
        "warnings": [],
    }

    assert (
        render_partial_agent_turn_from_artifact_data(
            bases_only_payload,
            workflow_id="TEST_DESIGN",
            current_stage_id="CASES",
        )
        is None
    )

    payload = {
        **bases_only_payload,
        "artifact_data": {
            **bases_only_payload["artifact_data"],
            "case_groups": VALID_CASES_ARTIFACT_DATA["case_groups"],
        },
    }

    output = render_partial_agent_turn_from_artifact_data(
        payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert output is not None
    assert output.artifact_update.markdown.startswith("# 测试用例集")
    assert "## 1. 用例统计" in output.artifact_update.markdown
    assert "**统计摘要**：共 2 条用例，P0: 1 条 | P1: 1 条 | P2: 0 条" in output.artifact_update.markdown
    assert "## 2. 用例设计依据" in output.artifact_update.markdown
    assert "## 3. 按维度分组的用例清单" in output.artifact_update.markdown
    assert output.artifact_patch is None
```

- [x] **Step 3: 增加 CASES partial 引用门禁测试**

在 partial cases 测试附近加入：

```python
def test_render_partial_cases_artifact_data_skips_automation_candidates_with_unknown_case_reference():
    payload = {
        "chat": "我正在生成测试用例集。",
        "artifact_data": {
            "document_info": VALID_CASES_ARTIFACT_DATA["document_info"],
            "design_bases": VALID_CASES_ARTIFACT_DATA["design_bases"],
            "case_groups": VALID_CASES_ARTIFACT_DATA["case_groups"],
            "test_data_environments": VALID_CASES_ARTIFACT_DATA["test_data_environments"],
            "automation_candidates": [
                {**VALID_CASES_ARTIFACT_DATA["automation_candidates"][0], "case_id": "TC-404"}
            ],
        },
        "stage_action": None,
        "warnings": [],
    }

    output = render_partial_agent_turn_from_artifact_data(
        payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert output is not None
    assert "## 4. 测试数据与环境" in output.artifact_update.markdown
    assert "## 5. 自动化候选" not in output.artifact_update.markdown


def test_render_partial_cases_artifact_data_skips_coverage_trace_with_unknown_case_reference():
    payload = {
        "chat": "我正在生成测试用例集。",
        "artifact_data": {
            "document_info": VALID_CASES_ARTIFACT_DATA["document_info"],
            "design_bases": VALID_CASES_ARTIFACT_DATA["design_bases"],
            "case_groups": VALID_CASES_ARTIFACT_DATA["case_groups"],
            "test_data_environments": VALID_CASES_ARTIFACT_DATA["test_data_environments"],
            "automation_candidates": VALID_CASES_ARTIFACT_DATA["automation_candidates"],
            "coverage_trace": [
                {**VALID_CASES_ARTIFACT_DATA["coverage_trace"][0], "covered_cases": ["TC-404"]}
            ],
        },
        "stage_action": None,
        "warnings": [],
    }

    output = render_partial_agent_turn_from_artifact_data(
        payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert output is not None
    assert "## 5. 自动化候选" in output.artifact_update.markdown
    assert "## 6. 测试点覆盖追溯" not in output.artifact_update.markdown
```

- [x] **Step 4: 增加 prompt 和 raw streaming RED 测试**

在 `test_cases_structured_output_instruction_requests_artifact_data_not_markdown` 附近加入：

```python
def test_cases_structured_output_instruction_omits_derived_statistics():
    instruction = build_structured_output_instruction("TEST_DESIGN", "CASES")

    assert '"case_statistics"' not in instruction
    assert "case_groups" in instruction
    assert "用例总数和 P0/P1/P2 分布由后端" in instruction
```

在现有 CASES raw streaming 测试后加入：

```python
def test_runtime_raw_json_stream_turn_renders_cases_after_case_groups_without_model_statistics(monkeypatch):
    artifact_data = copy.deepcopy(VALID_CASES_ARTIFACT_DATA)
    artifact_data.pop("case_statistics")
    final_json = json.dumps(
        {
            "chat": "我正在逐段形成测试用例集。",
            "artifact_data": artifact_data,
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

    bases_prefix = prefix_after_artifact_data_member("design_bases")
    cases_prefix = prefix_after_artifact_data_member("case_groups")
    chunks = [
        bases_prefix,
        cases_prefix[len(bases_prefix) :],
        final_json[len(cases_prefix) :],
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
            "请生成测试用例集",
            workflow_id="TEST_DESIGN",
            current_stage_id="CASES",
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

    assert len(partial_markdowns) >= 1
    assert partial_markdowns[0].startswith("# 测试用例集")
    assert "## 1. 用例统计" in partial_markdowns[0]
    assert "## 3. 按维度分组的用例清单" in partial_markdowns[0]
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert outputs[-1].artifact_data["case_statistics"] == {
        "total": 2,
        "p0_count": 1,
        "p1_count": 1,
        "p2_count": 0,
    }
```

- [x] **Step 5: 运行 RED 命令**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_derives_statistics_when_missing tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_automation_candidate_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_derives_statistics_from_case_groups tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_skips_automation_candidates_with_unknown_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_skips_coverage_trace_with_unknown_case_reference tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_omits_derived_statistics tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_cases_after_case_groups_without_model_statistics -q
```

Expected before implementation: selected tests fail because `case_statistics` is required, CASES prompt still asks for it, and partial renderer does not gate case_id references.

### Task 2: 实现后端派生统计和引用门禁

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [x] **Step 1: Add helper functions**

Add helpers near CASES models:

```python
def _flatten_cases(case_groups: list[CaseGroup]) -> list[TestCaseItem]:
    return [case for group in case_groups for case in group.cases]


def _derive_case_statistics(case_groups: list[CaseGroup]) -> CaseStatistics:
    cases = _flatten_cases(case_groups)
    return CaseStatistics(
        total=len(cases),
        p0_count=sum(1 for case in cases if case.priority == "P0"),
        p1_count=sum(1 for case in cases if case.priority == "P1"),
        p2_count=sum(1 for case in cases if case.priority == "P2"),
    )


def _collect_case_ids(case_groups: list[CaseGroup]) -> set[str]:
    return {case.case_id for case in _flatten_cases(case_groups)}
```

Add validators for duplicate IDs, statistics, automation candidates, and coverage trace. Error messages must include `case_statistics`, `automation_candidates`, or `coverage_trace` respectively so existing diagnostic field-path behavior remains useful.

- [x] **Step 2: Make `case_statistics` optional and derived**

Change `CasesArtifactData`:

```python
case_statistics: CaseStatistics | None = None
```

In `validate_case_consistency()`:

```python
_validate_unique_case_ids(self.case_groups)
derived_statistics = _derive_case_statistics(self.case_groups)
if self.case_statistics is None:
    self.case_statistics = derived_statistics
else:
    _validate_case_statistics_matches(self.case_statistics, derived_statistics)
case_ids = _collect_case_ids(self.case_groups)
_validate_automation_candidate_case_references(self.automation_candidates, case_ids)
_validate_coverage_trace_case_references(self.coverage_trace, case_ids)
return self
```

- [x] **Step 3: Update CASES full renderer**

Because validator guarantees `case_statistics` is populated after validation, keep the rendered headings unchanged. Add a local guard before rendering:

```python
if data.case_statistics is None:
    raise ValueError("case_statistics must be derived before rendering")
```

Then call `_render_case_statistics(data.case_statistics)`.

- [x] **Step 4: Update CASES partial renderer**

Rewrite `render_partial_test_design_cases_markdown()` so it:

1. validates `document_info`;
2. requires `design_bases` and `case_groups` before returning any markdown;
3. validates duplicate case IDs and derives statistics from `case_groups`;
4. renders sections 1-3 in one first partial;
5. validates `automation_candidates.case_id` before rendering section 5;
6. validates `coverage_trace.covered_cases` before rendering section 6;
7. returns previous trusted sections when a later section is invalid.

Update CASES `field_order` in `render_partial_agent_turn_from_artifact_data()` to:

```python
field_order = [
    "design_bases",
    "case_groups",
    "test_data_environments",
    "automation_candidates",
    "coverage_trace",
    "open_questions",
    "stage_gate",
]
```

### Task 3: 同步 prompt 和前端模板提示

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`
- Modify: `tools/new-agents/frontend/src/core/prompts/test_design/cases.ts`

- [x] **Step 1: Update backend structured output instruction**

Remove `"case_statistics"` from the CASES JSON example. Replace the consistency note with:

```text
artifact_data 中所有字符串必须非空；数组必须至少包含一项；用例总数和 P0/P1/P2 分布由后端根据 case_groups 计算，不需要输出 case_statistics；automation_candidates.case_id 与 coverage_trace.covered_cases 只能引用已存在的 case_groups[].cases[].case_id。
```

- [x] **Step 2: Update frontend CASES prompt**

Add a warning bullet:

```typescript
- 结构化链路中不要手写用例统计数量；用例总数和 P0/P1/P2 分布由后端根据用例清单计算。
```

Do not remove the final `CASES_TEMPLATE` statistics section.

### Task 4: GREEN、回归和文档记录

**Files:**
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- Modify: this plan

- [x] **Step 1: Run GREEN**

Run the RED command again.

Expected: `7 passed`.

- [x] **Step 2: Run CASES focused regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_inconsistent_statistics tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_coverage_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_cases_artifact_data_is_contract_valid_and_asset_parseable tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data -q
```

Expected: all selected CASES tests pass.

- [x] **Step 3: Run backend shared regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: backend shared regression passes.

- [x] **Step 4: Update todo execution record**

Add a new execution record for “第 6 轮首个纵切：TEST_DESIGN/CASES 统计后端化与 case_id 引用门禁”, including RED/GREEN and regression results. Update the top status and progress bullets for:

- 可计算字段从模型输出中移除
- 收敛 ID 与引用关系
- 高失败阶段纵切专项修复

### Task 5: 全量验证、提交和推送

**Files:**
- Modify: this plan

- [x] **Step 1: Run New Agents and full local validation**

Run:

```bash
./scripts/test/test-local.sh new-agents
./scripts/test/test-local.sh all
```

If default sandbox fails on browser or port permissions, rerun the full command with approved non-sandbox execution and record both the environment failure and successful rerun.

Result:

- `./scripts/test/test-local.sh new-agents`: New Agents Frontend `718 passed`; New Agents Backend `617 passed, 1 deselected`; existing React `ArtifactPane.test.tsx` `act(...)` warning only.
- `./scripts/test/test-local.sh all` default sandbox: failed on environment permissions, including MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` and Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`.
- `./scripts/test/test-local.sh all` non-sandbox: Intent Tester API `294 passed`; flake8 severe check passed; MidScene proxy `17 passed`; Common Frontend lint/build passed; New Agents Frontend `718 passed`; New Agents Backend `617 passed, 1 deselected`; Browser E2E had one setup `page.goto(http://127.0.0.1:64656/new-agents/)` timeout before test-body skip logic.
- Browser E2E rerun non-sandbox with `.venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q`: `11 passed, 10 deselected`.

- [x] **Step 2: Run diff checks**

Run:

```bash
git diff --check -- tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/frontend/src/core/prompts/test_design/cases.ts docs/superpowers/specs/2026-07-08-new-agents-cases-derived-statistics-reference-gate-design.md docs/superpowers/plans/2026-07-08-new-agents-cases-derived-statistics-reference-gate.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
```

Stage only this slice and run:

```bash
git diff --cached --check
git diff --cached --name-only
```

- [x] **Step 3: Commit and push**

Commit message:

```bash
git commit -m "fix(new-agents): 后端派生Lisa用例统计"
git push
```

After push, verify:

```bash
git rev-parse HEAD
git rev-parse @{u}
```

Expected: both SHAs match.
