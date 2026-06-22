# DeepSeek V4 TEST_DESIGN/CASES Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `TEST_DESIGN/CASES` 由 DeepSeek V4 JSON mode 输出结构化测试用例数据，并由后端确定性渲染可展示、可持久化、可导出的测试用例集。

**Architecture:** 复用现有 `artifact_data_renderers.py` 作为共享 stage renderer registry，在既有 `AgentTurnOutput.artifact_update.markdown` contract 下新增 CASES schema 和 renderer。`agent_runtime.py` 只扩展 stage-specific artifact_data instruction/retry，不新增 workflow 专属 runtime、API、store 或前端协议。

**Tech Stack:** Python 3.11、Pydantic v2、pytest、现有 New Agents backend contract/runtime/test assets tests。

---

## 文件结构

- 修改 `tools/new-agents/backend/artifact_data_renderers.py`：新增 CASES Pydantic models、renderer、traceability visual helper 和 registry 分支。
- 修改 `tools/new-agents/backend/agent_runtime.py`：让 `TEST_DESIGN/CASES` 使用 `artifact_data` instruction，并提供 CASES JSON 示例。
- 修改 `tools/new-agents/backend/tests/test_artifact_data_renderers.py`：新增 CASES schema/render/contract/test asset parsing RED 测试。
- 修改 `tools/new-agents/backend/tests/test_agent_runtime.py`：新增 CASES instruction、parse、retry RED 测试。
- 修改 `tools/new-agents/backend/tests/test_test_assets.py`：新增 renderer 输出落入 persistence 后仍可导出的回归测试。
- 修改 `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`：记录 CASES 迁移完成和剩余 DELIVERY/其它 workflow。

## Task 1: RED - CASES renderer and asset parsing tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify later: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] **Step 1: 写失败测试**

在 `test_artifact_data_renderers.py` 中新增 `VALID_CASES_ARTIFACT_DATA`，包含 2 条用例、2 条覆盖追溯和 1 个开放问题。

新增测试：

```python
def test_cases_artifact_data_rejects_inconsistent_statistics():
    invalid = {**VALID_CASES_ARTIFACT_DATA, "case_statistics": {"total": 99, "p0_count": 1, "p1_count": 1, "p2_count": 0}}

    with pytest.raises(ValidationError, match="case_statistics"):
        CasesArtifactData.model_validate(invalid)


def test_cases_artifact_data_rejects_unknown_coverage_case_reference():
    invalid = {
        **VALID_CASES_ARTIFACT_DATA,
        "coverage_trace": [
            {
                **VALID_CASES_ARTIFACT_DATA["coverage_trace"][0],
                "covered_cases": ["TC-404"],
            }
        ],
    }

    with pytest.raises(ValidationError, match="coverage_trace"):
        CasesArtifactData.model_validate(invalid)


def test_render_cases_artifact_data_is_contract_valid_and_asset_parseable():
    output = render_agent_turn_from_artifact_data(
        {
            "chat": "我已生成可执行测试用例集，请确认右侧内容。",
            "artifact_data": VALID_CASES_ARTIFACT_DATA,
            "stage_action": {"type": "request_next_stage", "target_stage_id": "DELIVERY"},
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    )

    assert output is not None
    assert output.artifact_update.markdown is not None
    assert "# 测试用例集" in output.artifact_update.markdown
    assert "```ai4se-visual" in output.artifact_update.markdown
    assert '"type": "traceability-matrix"' in output.artifact_update.markdown
    assert validate_agent_turn(output, workflow_id="TEST_DESIGN", current_stage_id="CASES") == output

    parsed = parse_lisa_test_asset_markdown(output.artifact_update.markdown)
    assert [case["id"] for case in parsed["testCases"]] == ["TC-001", "TC-002"]
    assert parsed["coverageSummary"]["totalTestCases"] == 2
    assert parsed["riskMatrix"][0]["risk"] == "R-LOGIN-001"
```

- [ ] **Step 2: 运行 RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: FAIL，原因是 `CasesArtifactData` 未定义或 `TEST_DESIGN/CASES` renderer 未配置。

## Task 2: GREEN - CASES schema and renderer

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] **Step 1: 实现 schema**

新增模型：`CaseStatistics`、`DesignBasis`、`TestCaseItem`、`CaseGroup`、`TestDataEnvironment`、`AutomationCandidate`、`CoverageTraceItem`、`OpenQuestion`、`CasesArtifactData`。所有字符串非空，关键列表 `Field(min_length=1)`。`CasesArtifactData` 用 model validator 校验统计总数和 coverage 引用。

- [ ] **Step 2: 实现 renderer**

新增 `render_test_design_cases_markdown(data)`，输出固定章节：

- `# 测试用例集`
- `## 1. 用例统计`
- `## 2. 用例设计依据`
- `## 3. 按维度分组的用例清单`
- `## 4. 测试数据与环境`
- `## 5. 自动化候选`
- `## 6. 测试点覆盖追溯`
- `## 7. 开放问题`
- `## 8. 阶段门禁`

在覆盖追溯章节输出 Markdown 表格和 fenced `ai4se-visual` traceability-matrix。

- [ ] **Step 3: 注册 renderer**

更新 `render_agent_turn_from_artifact_data()`，当 `(workflow_id, current_stage_id) == ("TEST_DESIGN", "CASES")` 时校验 `CasesArtifactData` 并返回 `AgentTurnOutput`。

- [ ] **Step 4: 运行 GREEN**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: PASS。

## Task 3: RED/GREEN - Runtime instruction, parse and retry

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [ ] **Step 1: 写失败测试**

新增测试覆盖：

- `build_structured_output_instruction("TEST_DESIGN", "CASES")` 包含 `artifact_data`、`case_groups`、`coverage_trace`、`traceability-matrix`，且不要求模型输出完整 Markdown。
- `parse_agent_turn_output_text(..., workflow_id="TEST_DESIGN", current_stage_id="CASES")` 能把 CASES `artifact_data` 渲染为 contract-valid `AgentTurnOutput`。
- `build_raw_json_retry_prompt(..., workflow_id="TEST_DESIGN", current_stage_id="CASES")` 要求修正 `artifact_data`，不要求重写 Markdown 表格或 visual 代码块。

- [ ] **Step 2: 运行 RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -q
```

Expected: FAIL，原因是 CASES 尚未命中 artifact_data instruction 或 renderer registry。

- [ ] **Step 3: 实现 runtime 改动**

更新 `supports_artifact_data_rendering()` 支持 `("TEST_DESIGN", "CASES")`。新增 CASES artifact_data instruction，示例包含 `case_statistics`、`design_bases`、`case_groups`、`test_data_environments`、`automation_candidates`、`coverage_trace`、`open_questions`、`stage_gate`。

- [ ] **Step 4: 运行 GREEN**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -q
```

Expected: PASS。

## Task 4: Test asset export regression and docs

**Files:**
- Modify: `tools/new-agents/backend/tests/test_test_assets.py`
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [ ] **Step 1: 写导出回归测试**

在 `test_test_assets.py` 中从 renderer 生成 CASES markdown，保存为 `CASES` artifact，再调用 `export_lisa_test_assets(run.id)`。断言导出包含 `TC-001`、`TC-002`、coverage summary 和 risk matrix。

- [ ] **Step 2: 更新 todo**

在 DeepSeek todo 当前进展中新增 `TEST_DESIGN/CASES` 已迁移；迁移顺序保留 `TEST_DESIGN/DELIVERY` 和其它 workflow 未迁移。

- [ ] **Step 3: 格式化**

Run:

```bash
black tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_test_assets.py
```

- [ ] **Step 4: 验证**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_test_asset_parsing.py tools/new-agents/backend/tests/test_test_assets.py -q
.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py
git diff --check -- docs/superpowers/specs/2026-06-23-deepseek-v4-cases-artifact-data-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-cases-artifact-data.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_test_assets.py
```

- [ ] **Step 5: 聚焦提交**

只暂存本轮文件：

```bash
git add docs/superpowers/specs/2026-06-23-deepseek-v4-cases-artifact-data-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-cases-artifact-data.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_test_assets.py
git commit -m "feat: 支持 DeepSeek CASES 结构化产物数据"
```

## Self-review

- Spec 覆盖：schema、renderer、runtime instruction、retry、contract validation、test asset parsing/export、todo 更新和验证命令均有任务。
- Placeholder scan：无 TBD/TODO/implement later。
- Type consistency：计划中的类型名、函数名和字段与 CASES prompt/template 和测试资产解析字段一致。
