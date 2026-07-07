# New Agents 测试用例集真实 Partial Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `TEST_DESIGN/CASES` 在 raw JSON streaming 过程中基于已闭合 `artifact_data` 字段输出正式 partial artifact delta，并保持最终测试用例集可通过 contract 和 Lisa 测试资产解析。

**Architecture:** 复用共享 Agent Runtime、typed SSE、`artifact_data_renderers.py` registry、`artifact_patch.add_after`、前端 `generateResponseStream()`、`chatService` 和共享 ArtifactPane。只新增 `TEST_DESIGN/CASES` 的 partial renderer 分支，不新增 stage 专属 runtime、API path、store 或 UI 管线。

**Tech Stack:** Python 3.11、Pydantic v2、pytest、TypeScript 5.x、Vitest、现有 New Agents backend/frontend 流式测试。

## Global Constraints

- 必须继续复用 `tools/new-agents` 共享 runtime、transport、state 和 UI infrastructure。
- `artifact_update.replace.markdown` 只能承载正式产物或经过正式 renderer 生成的局部正式产物。
- 不输出进度页、裸 JSON、字段名、字符数、固定延迟或 synthetic reveal。
- 代码或行为变更按 TDD 执行，先写 failing test，再实现生产代码。
- 不触碰当前无关脏文件：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`、`tools/intent-tester/test-results/proxy/junit.xml`、`docs/mockups/`。

---

## File Structure

- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`：新增 CASES partial renderer RED 测试。
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`：新增 CASES raw JSON streaming 段落级 RED 测试。
- Modify `tools/new-agents/backend/artifact_data_renderers.py`：注册 CASES partial renderer，新增 `render_partial_test_design_cases_markdown()`。
- Modify `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`：记录第 1 轮状态、spec/plan、验证和残余风险。

## Task 1: Partial Renderer Red/Green

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

**Interfaces:**
- Consumes: `VALID_CASES_ARTIFACT_DATA`, `render_partial_agent_turn_from_artifact_data(payload, workflow_id, current_stage_id)`.
- Produces: `render_partial_test_design_cases_markdown(data: Any) -> str | None` and a `("TEST_DESIGN", "CASES")` branch in `render_partial_agent_turn_from_artifact_data()`.

- [ ] **Step 1: Write the failing test**

Add `render_partial_agent_turn_from_artifact_data` to the import list in `tools/new-agents/backend/tests/test_artifact_data_renderers.py`, then add this test near `test_render_cases_artifact_data_is_contract_valid_and_asset_parseable`:

```python
def test_render_partial_cases_artifact_data_builds_formal_incremental_markdown_and_patch():
    statistics_payload = {
        "chat": "我正在生成测试用例集。",
        "artifact_data": {
            "document_info": VALID_CASES_ARTIFACT_DATA["document_info"],
            "case_statistics": VALID_CASES_ARTIFACT_DATA["case_statistics"],
        },
        "stage_action": None,
        "warnings": [],
    }

    statistics_output = render_partial_agent_turn_from_artifact_data(
        statistics_payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert statistics_output is not None
    assert statistics_output.artifact_update.markdown.startswith("# 测试用例集")
    assert "## 1. 用例统计" in statistics_output.artifact_update.markdown
    assert "## 2. 用例设计依据" not in statistics_output.artifact_update.markdown
    assert statistics_output.artifact_patch is None

    bases_payload = {
        **statistics_payload,
        "artifact_data": {
            **statistics_payload["artifact_data"],
            "design_bases": VALID_CASES_ARTIFACT_DATA["design_bases"],
        },
    }

    bases_output = render_partial_agent_turn_from_artifact_data(
        bases_payload,
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert bases_output is not None
    assert "## 2. 用例设计依据" in bases_output.artifact_update.markdown
    assert "## 3. 按维度分组的用例清单" not in bases_output.artifact_update.markdown
    assert bases_output.artifact_patch is not None
    assert bases_output.artifact_patch.operation == "add_after"
    assert bases_output.artifact_patch.section_anchor == "h2:2. 用例设计依据:1"
    assert bases_output.artifact_patch.after_section_anchor == "h2:1. 用例统计:1"
    assert bases_output.artifact_patch.base_content == statistics_output.artifact_update.markdown
    assert "## 2. 用例设计依据" in bases_output.artifact_patch.replacement_markdown
```

- [ ] **Step 2: Run RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_builds_formal_incremental_markdown_and_patch -q
```

Expected: FAIL because `render_partial_agent_turn_from_artifact_data()` returns `None` for `TEST_DESIGN/CASES`.

- [ ] **Step 3: Write minimal implementation**

In `tools/new-agents/backend/artifact_data_renderers.py`, add the CASES branch:

```python
    elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "CASES"):
        field_order = [
            "case_statistics",
            "design_bases",
            "case_groups",
            "test_data_environments",
            "automation_candidates",
            "coverage_trace",
            "open_questions",
            "stage_gate",
        ]
        renderer = render_partial_test_design_cases_markdown
        markdown = render_partial_test_design_cases_markdown(payload["artifact_data"])
```

Add this renderer before `render_partial_test_design_clarify_markdown()`:

```python
def render_partial_test_design_cases_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "document_info" not in data:
        return None
    try:
        DocumentInfo.model_validate(data["document_info"])
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 测试用例集"]
    try:
        if "case_statistics" not in data:
            return None
        sections.append(
            _render_case_statistics(
                CaseStatistics.model_validate(data["case_statistics"])
            )
        )

        if "design_bases" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_design_bases(
                _validate_partial_list(data["design_bases"], DesignBasis)
            )
        )

        if "case_groups" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_case_groups(
                _validate_partial_list(data["case_groups"], CaseGroup)
            )
        )

        if "test_data_environments" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_test_data_environments(
                _validate_partial_list(
                    data["test_data_environments"],
                    TestDataEnvironment,
                )
            )
        )

        if "automation_candidates" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_automation_candidates(
                _validate_partial_list(
                    data["automation_candidates"],
                    AutomationCandidate,
                )
            )
        )

        if "coverage_trace" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_coverage_trace(
                _validate_partial_list(data["coverage_trace"], CoverageTraceItem)
            )
        )

        if "open_questions" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_open_questions(
                _validate_partial_list(data["open_questions"], OpenQuestion)
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)
```

- [ ] **Step 4: Run GREEN**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_builds_formal_incremental_markdown_and_patch -q
```

Expected: PASS.

## Task 2: Runtime Paragraph Streaming Red/Green

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

**Interfaces:**
- Consumes: `PydanticAgentRuntime.stream_turn()`, `build_partial_agent_delta()`, `VALID_CASES_ARTIFACT_DATA`.
- Produces: test evidence that `TEST_DESIGN/CASES` yields multiple formal artifact deltas before final `AgentTurnOutput`.

- [ ] **Step 1: Write the failing test**

Add this test after existing strategy paragraph-level streaming coverage:

```python
def test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "我正在逐段形成测试用例集。",
            "artifact_data": VALID_CASES_ARTIFACT_DATA,
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

    statistics_prefix = prefix_after_artifact_data_member("case_statistics")
    bases_prefix = prefix_after_artifact_data_member("design_bases")
    chunks = [
        statistics_prefix,
        bases_prefix[len(statistics_prefix) :],
        final_json[len(bases_prefix) :],
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
    partial_patches = [
        output.artifact_patch
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_patch is not None
    ]

    assert len(partial_markdowns) >= 2
    assert partial_markdowns[0].startswith("# 测试用例集")
    assert "## 1. 用例统计" in partial_markdowns[0]
    assert "## 2. 用例设计依据" not in partial_markdowns[0]
    assert "## 2. 用例设计依据" in partial_markdowns[1]
    assert "## 3. 按维度分组的用例清单" not in partial_markdowns[1]
    assert partial_patches
    assert partial_patches[0].operation == "add_after"
    assert partial_patches[0].section_anchor == "h2:2. 用例设计依据:1"
    assert partial_patches[0].after_section_anchor == "h2:1. 用例统计:1"
    assert isinstance(outputs[-1], AgentTurnOutput)
    assert "## 3. 按维度分组的用例清单" in outputs[-1].artifact_update.markdown
    assert '"type": "traceability-matrix"' in outputs[-1].artifact_update.markdown
```

- [ ] **Step 2: Run RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data -q
```

Expected: FAIL before Task 1 GREEN, then PASS after Task 1 GREEN. If it fails for a different reason, fix the test setup before changing production code.

- [ ] **Step 3: Run focused runtime regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data -q
```

Expected: PASS, proving the new CASES branch does not regress existing partial stages.

## Task 3: Verification And Todo Update

**Files:**
- Modify: `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`

**Interfaces:**
- Consumes: pytest/Vitest outputs and current todo round table.
- Produces: todo status update for 第 1 轮 with spec/plan links, verification evidence, and next candidate.

- [ ] **Step 1: Run backend regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_test_assets.py -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend regression**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx
```

Expected: PASS. Existing frontend tests prove typed `agent_delta` artifact updates are parsed and written to `artifactContent` through the shared frontend chain.

- [ ] **Step 3: Update todo**

In `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`, change the top status to show 第 1 轮完成 after verification and add a progress section:

```markdown
## 目标模式执行记录

### 第 1 轮：`TEST_DESIGN/CASES`

- 状态：已完成
- Spec：`docs/superpowers/specs/2026-07-07-new-agents-cases-partial-streaming-design.md`
- Plan：`docs/superpowers/plans/2026-07-07-new-agents-cases-partial-streaming.md`
- 交付：`TEST_DESIGN/CASES` 支持基于已闭合 `artifact_data` 顶层字段生成正式 partial artifact delta；最终《测试用例集》仍通过 contract 并可解析为 Lisa 测试资产。
- 验证：记录本轮实际运行的每条命令、退出码和摘要；未运行的命令记录原因。
- 残余风险：真实模型 smoke 取决于本地默认模型配置；未执行时记录原因。
- 下一轮候选：第 2 轮 `TEST_DESIGN/DELIVERY`。
```

- [ ] **Step 4: Diff and CI-equivalent checks**

Run:

```bash
git diff --check
./scripts/test/test-local.sh all
```

Expected: PASS. If full local automation is not runnable, record exact failure or reason in the final note and do not claim full CI-equivalent coverage.

## Self-Review

- Spec coverage: plan covers partial renderer, runtime final-before delta, final contract/test asset parser, frontend shared delta consumption verification, and todo update.
- 占位扫描：无未决占位标记。
- Type consistency: function names, field names, anchors, stage IDs and test names match existing code conventions.
- Scope: one vertical user story, `TEST_DESIGN/CASES` only.
