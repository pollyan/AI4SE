# New Agents Value Elevator 评分汇总后端化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `VALUE_DISCOVERY/ELEVATOR` 的总分和平均分由后端根据 `score_matrix` 确定性生成，模型只输出评分明细和判断文本。

**Architecture:** 继续复用共享 Agent Runtime 的 `artifact_data -> Pydantic model -> deterministic renderer -> typed AgentTurnOutput` 链路。`ValueScoreSummary.total_score` 与 `average_score` 改为可选输入，缺省时由 `ValueDiscoveryElevatorArtifactData` validator 写回计算值，显式错误时仍抛出 ValidationError。

**Tech Stack:** Python 3.11, Pydantic v2, pytest, New Agents shared Agent Runtime.

---

## File Map

- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
  - `ValueScoreSummary` 字段可选化。
  - `ValueDiscoveryElevatorArtifactData.validate_value_consistency` 负责派生缺省汇总。
  - 现有 `_render_value_score_matrix` 继续读取规范化后的 summary。
- Modify: `tools/new-agents/backend/agent_runtime.py`
  - `VALUE_ELEVATOR_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` 示例去掉 `total_score` / `average_score`，文案说明由后端计算。
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
  - 增加缺省评分汇总可计算测试。
  - 保留显式错误汇总失败测试。
  - 更新 partial renderer payload 测试，证明缺省汇总也能输出评分章节。
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
  - 增加 final raw JSON parse 接受缺省汇总测试。
  - 更新 structured output instruction 测试，防止 prompt 再要求模型输出派生字段。
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
  - 记录第 3 轮首个纵切的实现、验证和残余风险。
- Modify: this plan and matching spec files only for execution evidence.

## Task 1: RED tests for VALUE ELEVATOR derived score summary

- [x] **Step 1: Add renderer schema red tests**

In `tools/new-agents/backend/tests/test_artifact_data_renderers.py`, add tests near the existing value elevator tests:

```python
def test_value_elevator_artifact_data_computes_missing_score_summary_fields():
    data = copy.deepcopy(VALID_VALUE_ELEVATOR_ARTIFACT_DATA)
    data["score_summary"].pop("total_score")
    data["score_summary"].pop("average_score")

    artifact = ValueDiscoveryElevatorArtifactData.model_validate(data)

    assert artifact.score_summary.total_score == 16
    assert artifact.score_summary.average_score == 3.2


def test_render_partial_value_elevator_artifact_data_computes_score_summary_fields():
    score_payload = {
        "chat": "我正在生成价值定位分析。",
        "artifact_data": {
            "document_info": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["document_info"],
            "positioning_summary": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["positioning_summary"],
            "value_flow": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["value_flow"],
            "target_scenarios": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["target_scenarios"],
            "pain_evidence": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["pain_evidence"],
            "differentiators": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["differentiators"],
            "business_feasibility": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["business_feasibility"],
            "score_matrix": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["score_matrix"],
            "score_summary": {
                "judgement": VALID_VALUE_ELEVATOR_ARTIFACT_DATA["score_summary"]["judgement"],
            },
        },
        "stage_action": None,
        "warnings": [],
    }

    output = render_partial_agent_turn_from_artifact_data(
        score_payload,
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert output is not None
    assert "总分 16，平均分 3.20" in output.artifact_update.markdown
```

- [x] **Step 2: Add runtime red tests**

In `tools/new-agents/backend/tests/test_agent_runtime.py`, add or update tests:

```python
def test_parse_agent_turn_output_text_renders_value_elevator_without_model_score_totals():
    artifact_data = copy.deepcopy(VALID_VALUE_ELEVATOR_ARTIFACT_DATA)
    artifact_data["score_summary"].pop("total_score")
    artifact_data["score_summary"].pop("average_score")

    output = _parse_agent_turn_output_text(
        json.dumps(
            {
                "chat": "已生成价值定位分析。",
                "artifact_data": artifact_data,
                "stage_action": {"type": "request_next_stage", "target_stage_id": "PERSONA"},
                "warnings": [],
            },
            ensure_ascii=False,
        ),
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert "总分 16，平均分 3.20" in output.artifact_update.markdown
    assert output.artifact_data["score_summary"]["total_score"] == 16
    assert output.artifact_data["score_summary"]["average_score"] == 3.2
```

Update `test_value_elevator_structured_output_instruction_requests_artifact_data_not_markdown` to assert:

```python
assert '"score_summary": {"judgement": "..."}' in instruction
assert '"total_score"' not in instruction
assert "average_score" not in instruction
assert "总分和平均分由后端根据 score_matrix.score 计算" in instruction
```

- [x] **Step 3: Run RED command**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_value_elevator_artifact_data_computes_missing_score_summary_fields tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_value_elevator_artifact_data_computes_score_summary_fields tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_value_elevator_without_model_score_totals tools/new-agents/backend/tests/test_agent_runtime.py::test_value_elevator_structured_output_instruction_requests_artifact_data_not_markdown -q
```

Expected: fail because `total_score` / `average_score` are currently required and prompt still asks for them.

## Task 2: Implement minimal derived score summary behavior

- [x] **Step 1: Update `ValueScoreSummary`**

In `tools/new-agents/backend/artifact_data_renderers.py`:

```python
class ValueScoreSummary(StrictArtifactDataModel):
    total_score: int | None = Field(default=None, ge=1)
    average_score: float | None = Field(default=None, ge=1, le=5)
    judgement: str
```

- [x] **Step 2: Update validator**

In `ValueDiscoveryElevatorArtifactData.validate_value_consistency`, replace the score checks with:

```python
total_score = sum(item.score for item in self.score_matrix)
if self.score_summary.total_score is None:
    self.score_summary.total_score = total_score
elif self.score_summary.total_score != total_score:
    raise ValueError("score_summary.total_score must equal score_matrix score sum")

expected_average = round(total_score / len(self.score_matrix), 2)
if self.score_summary.average_score is None:
    self.score_summary.average_score = expected_average
elif abs(self.score_summary.average_score - expected_average) > 0.001:
    raise ValueError(
        "score_summary.average_score must equal score_matrix average score "
        f"({expected_average})"
    )
```

- [x] **Step 3: Update structured output instruction**

In `tools/new-agents/backend/agent_runtime.py`, change the `score_summary` example to:

```json
"score_summary": {"judgement": "..."}
```

Change the constraints sentence to say:

```text
score_matrix.score 必须是 1 到 5 的整数；score_summary 只需要输出 judgement，总分和平均分由后端根据 score_matrix.score 计算。
```

- [x] **Step 4: Run GREEN command**

Run the same RED command. Expected: `4 passed`.

## Task 3: Regression and documentation closure

- [x] **Step 1: Run focused backend regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: all selected tests pass.

- [x] **Step 2: Update todo record**

In `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`, update:

- Status line to include 第 3 轮首个纵切已完成 or execution record in progress.
- Mark the 第 3 轮 checkbox as partially completed for `VALUE_DISCOVERY/ELEVATOR` if broader round still has future candidates.
- Add an execution record with RED, GREEN, focused regression, full validation, commit/push status.

- [x] **Step 3: Run New Agents verification**

Run:

```bash
./scripts/test/test-local.sh new-agents
```

Expected: New Agents frontend and backend suites pass.

- [x] **Step 4: Run full local verification before commit**

Run:

```bash
./scripts/test/test-local.sh all
```

Expected: full local suite passes. If sandbox blocks MidScene/Playwright, rerun with approved escalation and record the sandbox failure plus non-sandbox result.

- [x] **Step 5: Commit and push focused value batch**

Stage only this round's files:

```bash
git add docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/superpowers/specs/2026-07-08-new-agents-value-elevator-derived-score-summary-design.md docs/superpowers/plans/2026-07-08-new-agents-value-elevator-derived-score-summary.md tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
git commit -m "fix(new-agents): 后端派生价值定位评分汇总"
git push
```

Expected: `HEAD` equals `origin/codex/structured-failure-diagnostics` after push.

## Verification Record

- RED: `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_value_elevator_artifact_data_computes_missing_score_summary_fields tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_value_elevator_artifact_data_computes_score_summary_fields tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_value_elevator_without_model_score_totals tools/new-agents/backend/tests/test_agent_runtime.py::test_value_elevator_structured_output_instruction_requests_artifact_data_not_markdown -q` -> `4 failed`;旧实现仍要求 `score_summary.total_score` / `average_score`，partial renderer 未输出评分章节，prompt 仍包含旧示例。
- GREEN: 同一命令 -> `4 passed`。
- Focused backend regression: `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q` -> `348 passed`。
- New Agents verification: `./scripts/test/test-local.sh new-agents` -> frontend `718 passed`; backend `601 passed, 1 deselected`；保留既有 `ArtifactPane.test.tsx` React `act(...)` warning。
- Full verification sandbox: `./scripts/test/test-local.sh all` -> failed due MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` and Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`.
- Full verification non-sandbox: `./scripts/test/test-local.sh all` -> passed；Intent Tester API `294 passed`，MidScene proxy `17 passed`，Common Frontend lint/build passed，New Agents Frontend `718 passed`，New Agents Backend `601 passed, 1 deselected`，New Agents Browser E2E `11 passed, 10 deselected`。
