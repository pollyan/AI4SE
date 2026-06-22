# DeepSeek V4 Value Elevator Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `VALUE_DISCOVERY/ELEVATOR` use DeepSeek-compatible `artifact_data` with backend validation and deterministic artifact rendering.

**Architecture:** Reuse the existing shared Agent Runtime and artifact data renderer registry. Add one stage-specific Pydantic schema and renderer, then wire `VALUE_DISCOVERY/ELEVATOR` into the same `supports_artifact_data_rendering()`, structured output instruction, retry, raw JSON parse, typed SSE, and contract validation paths already used by `TEST_DESIGN` and `REQ_REVIEW`.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing `AgentTurnOutput` and `validate_agent_turn()` contracts.

---

## File Map

- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: add fixture and RED tests for `ValueDiscoveryElevatorArtifactData`, deterministic rendering, contract validity, score consistency, and value-flow reference validation.
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: add RED tests for parse, structured output instruction, retry prompt, and raw JSON stream rendering for `VALUE_DISCOVERY/ELEVATOR`.
- Modify `tools/new-agents/backend/artifact_data_renderers.py`: add schema classes, dispatch branch, renderer, and helper functions for the value elevator artifact.
- Modify `tools/new-agents/backend/agent_runtime.py`: add `VALUE_ELEVATOR_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`, support tuple, and instruction dispatch.
- Modify `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: record the completed `VALUE_DISCOVERY/ELEVATOR` slice and narrow remaining work.

## Task 1: Renderer Contract RED Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`

- [ ] **Step 1: Add imports and fixture**

Add `ValueDiscoveryElevatorArtifactData` to the import block from `artifact_data_renderers`.

Add this fixture near the existing valid artifact data fixtures:

```python
VALID_VALUE_ELEVATOR_ARTIFACT_DATA = {
    "document_info": {
        "artifact_name": "价值定位诊断报告",
        "workflow": "VALUE_DISCOVERY",
        "stage": "ELEVATOR",
        "status": "可进入用户画像",
    },
    "positioning_summary": {
        "one_liner": "面向中小测试团队的 AI 测试设计助手，帮助把需求快速转成可评审测试资产。",
        "core_user": "缺少专职测试架构师的测试负责人",
        "core_pain": "需求到测试策略和用例之间缺少稳定方法，返工成本高。",
        "unique_value": "把需求澄清、风险分析和用例追溯统一到可审阅 artifact。",
        "current_judgement": "可继续画像分析",
    },
    "value_flow": {
        "nodes": [
            {"node_id": "USER", "label": "目标用户", "description": "测试负责人"},
            {"node_id": "SCENE", "label": "高价值场景", "description": "需求评审后快速产出测试设计"},
            {"node_id": "PAIN", "label": "核心痛点", "description": "测试设计依赖个人经验"},
            {"node_id": "EXISTING", "label": "现有方案", "description": "手工模板和零散评审"},
            {"node_id": "GAP", "label": "现有方案不足", "description": "缺少追溯和风险门禁"},
            {"node_id": "VALUE", "label": "产品独特价值", "description": "结构化生成可评审测试资产"},
            {"node_id": "PROOF", "label": "证据与验证动作", "description": "试点项目对比返工率"},
            {"node_id": "BUSINESS", "label": "商业可行性判断", "description": "按团队订阅或项目包付费"},
        ],
        "links": [
            {"from_node": "USER", "to_node": "SCENE", "label": "负责"},
            {"from_node": "SCENE", "to_node": "PAIN", "label": "暴露"},
            {"from_node": "PAIN", "to_node": "EXISTING", "label": "当前依赖"},
            {"from_node": "EXISTING", "to_node": "GAP", "label": "不足"},
            {"from_node": "GAP", "to_node": "VALUE", "label": "形成价值"},
            {"from_node": "VALUE", "to_node": "PROOF", "label": "需要验证"},
            {"from_node": "PROOF", "to_node": "BUSINESS", "label": "支撑"},
        ],
    },
    "target_scenarios": [
        {
            "dimension": "主要用户群体",
            "description": "中小研发团队中的测试负责人",
            "evidence_level": "用户陈述",
            "status": "AI 假设",
        },
        {
            "dimension": "核心使用场景",
            "description": "需求评审后 1 天内形成测试设计初稿",
            "evidence_level": "合理推断",
            "status": "待验证",
        },
    ],
    "pain_evidence": [
        {
            "pain_id": "PAIN-001",
            "description": "测试设计质量受个人经验影响大",
            "scene": "新需求进入开发前",
            "impact": "返工和漏测风险增加",
            "evidence_level": "用户陈述",
            "validation_action": "访谈 5 位测试负责人并收集返工案例",
            "status": "待验证",
        }
    ],
    "differentiators": [
        {
            "dimension": "核心优势",
            "our_value": "把需求、风险、测试点和用例放在同一追溯链",
            "existing_solution": "通用文档模板和人工评审",
            "evidence": "已有测试设计 workflow 可生成覆盖矩阵",
            "status": "AI 假设",
        }
    ],
    "business_feasibility": [
        {
            "dimension": "用户付费意愿",
            "judgement": "若能减少返工，团队负责人有试点预算",
            "basis": "测试质量与交付风险直接相关",
            "validation_action": "设置试点报价页并访谈预算负责人",
            "status": "待验证",
        }
    ],
    "score_matrix": [
        {
            "dimension": "痛点强度",
            "score": 4,
            "basis": "返工和漏测影响核心交付目标",
            "next_validation": "收集 3 个近期返工案例",
        },
        {
            "dimension": "目标用户清晰度",
            "score": 4,
            "basis": "测试负责人角色明确",
            "next_validation": "细分团队规模和行业",
        },
        {
            "dimension": "差异化",
            "score": 3,
            "basis": "追溯链和阶段门禁有差异，但需竞品对比",
            "next_validation": "对比 3 个测试管理工具",
        },
        {
            "dimension": "付费意愿",
            "score": 3,
            "basis": "预算假设尚未验证",
            "next_validation": "访谈预算负责人",
        },
        {
            "dimension": "证据强度",
            "score": 2,
            "basis": "当前主要来自合理推断",
            "next_validation": "完成用户访谈",
        },
    ],
    "score_summary": {
        "total_score": 16,
        "average_score": 3.2,
        "judgement": "值得进入用户画像，但必须补强证据。",
    },
    "assumptions": [
        {
            "assumption_id": "H-001",
            "content": "目标团队愿意为减少测试设计返工付费",
            "impact": "影响商业模式和定价",
            "validation_action": "定价访谈和试点报价",
            "owner": "产品",
            "status": "待验证",
        }
    ],
    "elevator_pitch": "我们为缺少专职测试架构师的中小测试团队提供 AI 测试设计助手。它能把需求澄清、风险分析、测试策略和用例追溯统一成可评审产物，减少因经验不一致造成的返工和漏测。不同于普通文档模板，它输出可追溯、可签署、可继续交给测试资产链路的专业 artifact。下一步需要通过测试负责人访谈验证痛点强度和付费意愿。",
    "stage_gate": [
        {"checked": True, "item": "目标用户、核心场景和核心痛点已明确。"},
        {"checked": True, "item": "痛点证据至少标注了证据等级和验证动作。"},
        {"checked": True, "item": "独特价值和商业可行性没有被写成未标注的事实。"},
        {"checked": True, "item": "未验证假设已列入假设清单，可被用户画像阶段继续验证。"},
    ],
}
```

- [ ] **Step 2: Add failing tests**

Add these tests after the existing renderer validation tests:

```python
def test_value_elevator_artifact_data_rejects_inconsistent_score_summary():
    invalid = copy.deepcopy(VALID_VALUE_ELEVATOR_ARTIFACT_DATA)
    invalid["score_summary"]["total_score"] = 99

    with pytest.raises(ValueError, match="score_summary.total_score"):
        ValueDiscoveryElevatorArtifactData.model_validate(invalid)


def test_value_elevator_artifact_data_rejects_unknown_value_flow_reference():
    invalid = copy.deepcopy(VALID_VALUE_ELEVATOR_ARTIFACT_DATA)
    invalid["value_flow"]["links"][0]["to_node"] = "UNKNOWN"

    with pytest.raises(ValueError, match="value_flow.links references unknown node ids"):
        ValueDiscoveryElevatorArtifactData.model_validate(invalid)


def test_render_value_elevator_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成价值定位分析。",
            "artifact_data": VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
            "stage_action": {"type": "request_next_stage", "target_stage_id": "PERSONA"},
            "warnings": [],
        },
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成价值定位分析。",
            "artifact_data": VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
            "stage_action": {"type": "request_next_stage", "target_stage_id": "PERSONA"},
            "warnings": [],
        },
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert first == second
    assert first.artifact_update is not None
    assert first.artifact_update.type == "replace"
    assert first.stage_action is not None
    assert first.stage_action.target_stage_id == "PERSONA"
    assert "# 价值定位分析" in first.artifact_update.markdown
    assert "flowchart TD" in first.artifact_update.markdown
    assert '"type": "score-matrix"' in first.artifact_update.markdown
    assert "60 秒电梯演讲" in first.artifact_update.markdown

    validate_agent_turn(first, workflow_id="VALUE_DISCOVERY", stage_id="ELEVATOR")
```

- [ ] **Step 3: Run RED tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: FAIL because `ValueDiscoveryElevatorArtifactData` is not implemented or renderer is not configured.

## Task 2: Runtime RED Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [ ] **Step 1: Import the fixture**

Add `VALID_VALUE_ELEVATOR_ARTIFACT_DATA` to the import block from `test_artifact_data_renderers`.

- [ ] **Step 2: Add runtime tests**

Add these tests near the existing artifact_data runtime tests:

```python
def test_parse_agent_turn_output_text_renders_value_elevator_artifact_data():
    output = parse_agent_turn_output_text(
        json.dumps(
            {
                "chat": "已生成价值定位分析。",
                "artifact_data": VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
                "stage_action": {"type": "request_next_stage", "target_stage_id": "PERSONA"},
                "warnings": [],
            },
            ensure_ascii=False,
        ),
        deps=AgentTurnValidationDeps(
            workflow_id="VALUE_DISCOVERY",
            current_stage_id="ELEVATOR",
        ),
    )

    assert output.artifact_update is not None
    assert "# 价值定位分析" in output.artifact_update.markdown
    assert "flowchart TD" in output.artifact_update.markdown
    assert '"type": "score-matrix"' in output.artifact_update.markdown
    assert output.stage_action is not None
    assert output.stage_action.target_stage_id == "PERSONA"


def test_value_elevator_structured_output_instruction_requests_artifact_data_not_markdown():
    instruction = build_structured_output_instruction(
        "VALUE_DISCOVERY",
        "ELEVATOR",
    )

    assert "artifact_data" in instruction
    assert "artifact_update" not in instruction
    assert "value_flow" in instruction
    assert "score_matrix" in instruction
    assert "target_stage_id\": \"PERSONA\"" in instruction
    assert "不要输出完整 Markdown" in instruction
    assert "score-matrix" in instruction


def test_value_elevator_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite():
    prompt = build_raw_json_retry_prompt(
        "原始提示",
        ValueError("score_summary.total_score must equal score_matrix score sum"),
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    )

    assert "artifact_data" in prompt
    assert "score_summary.total_score" in prompt
    assert "不要输出 Markdown 文档" in prompt
    assert "artifact_update.type 必须为 replace" not in prompt
```

Add a raw stream test by copying the existing raw stream artifact_data pattern and using `workflow_id="VALUE_DISCOVERY"`, `current_stage_id="ELEVATOR"`, and `VALID_VALUE_ELEVATOR_ARTIFACT_DATA`. The assertions must check the final emitted artifact contains `# 价值定位分析`, `flowchart TD`, and `"type": "score-matrix"`, and the first model call system prompt contains `artifact_data`.

- [ ] **Step 3: Run RED runtime tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -q
```

Expected: FAIL because `VALUE_DISCOVERY/ELEVATOR` is not listed in `supports_artifact_data_rendering()` and no instruction/renderer exists.

## Task 3: Implement Schema And Renderer

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] **Step 1: Add Pydantic models**

Add stage-specific model classes for `PositioningSummary`, `ValueFlowNode`, `ValueFlowLink`, `ValueFlow`, `TargetScenario`, `PainEvidence`, `Differentiator`, `BusinessFeasibility`, `ValueScore`, `ValueScoreSummary`, `ValueAssumption`, and `ValueDiscoveryElevatorArtifactData`.

The `ValueDiscoveryElevatorArtifactData` model must validate:

```python
node_ids = {node.node_id for node in self.value_flow.nodes}
unknown_references = sorted(
    {
        reference
        for link in self.value_flow.links
        for reference in (link.from_node, link.to_node)
        if reference not in node_ids
    }
)
if unknown_references:
    raise ValueError(
        "value_flow.links references unknown node ids: "
        + ", ".join(unknown_references)
    )

total_score = sum(item.score for item in self.score_matrix)
if self.score_summary.total_score != total_score:
    raise ValueError("score_summary.total_score must equal score_matrix score sum")
expected_average = round(total_score / len(self.score_matrix), 2)
if self.score_summary.average_score != expected_average:
    raise ValueError(
        "score_summary.average_score must equal score_matrix average score "
        f"({expected_average})"
    )
```

- [ ] **Step 2: Add dispatch**

In `render_agent_turn_from_artifact_data()`, add:

```python
elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "ELEVATOR"):
    artifact_data = ValueDiscoveryElevatorArtifactData.model_validate(
        payload["artifact_data"]
    )
    markdown = render_value_discovery_elevator_markdown(artifact_data)
```

- [ ] **Step 3: Add deterministic renderer helpers**

Add `render_value_discovery_elevator_markdown()` that returns sections in the exact contract order. Add helpers for:

- `_render_value_positioning_summary()`
- `_render_value_flow()`
- `_render_target_scenarios()`
- `_render_pain_evidence()`
- `_render_differentiators()`
- `_render_business_feasibility()`
- `_render_value_score_matrix()`
- `_render_value_assumptions()`
- `_render_elevator_pitch()`

Use existing `_markdown_table()`, `_mermaid_block()`, `_json_block()`, and `_render_stage_gate()` patterns.

- [ ] **Step 4: Run GREEN renderer tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: PASS for renderer tests.

## Task 4: Implement Runtime Wiring

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [ ] **Step 1: Add structured output instruction**

Add `VALUE_ELEVATOR_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` after the existing artifact data instructions. It must require field order `chat`, `artifact_data`, `stage_action`, `warnings`; include the `ValueDiscovery/ELEVATOR` field shape; require `target_stage_id` `"PERSONA"`; and explicitly prohibit full Markdown, Mermaid code blocks, `score-matrix` JSON code blocks, and tables.

- [ ] **Step 2: Add support tuple**

Add `("VALUE_DISCOVERY", "ELEVATOR")` to `supports_artifact_data_rendering()`.

- [ ] **Step 3: Add instruction dispatch**

Add:

```python
if (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "ELEVATOR"):
    return VALUE_ELEVATOR_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION
```

- [ ] **Step 4: Run GREEN runtime tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -q
```

Expected: PASS for runtime tests.

## Task 5: Documentation And Verification

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [ ] **Step 1: Update todo progress**

Add a current progress bullet:

```markdown
- 2026-06-23 已完成第七个垂直切片: `VALUE_DISCOVERY/ELEVATOR` 支持模型输出 `artifact_data`，后端校验价值流节点引用、价值评分汇总、目标用户场景、痛点证据、差异化、商业可行性、未验证假设和阶段门禁后，确定性渲染《价值定位分析》、Mermaid `flowchart` 和 `ai4se-visual` `score-matrix`。
```

Update the remaining migration sentence to say `VALUE_DISCOVERY` still remains `PERSONA/JOURNEY/BLUEPRINT`, plus `IDEA_BRAINSTORM` and `INCIDENT_REVIEW`.

- [ ] **Step 2: Format touched Python files**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/black tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
```

- [ ] **Step 3: Run focused verification**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q
```

- [ ] **Step 4: Run expanded shared runtime verification**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py -q
```

- [ ] **Step 5: Run compile and diff checks**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py
git diff --check
```

- [ ] **Step 6: Commit**

Stage only this milestone's files and commit:

```bash
git add docs/superpowers/specs/2026-06-23-deepseek-v4-value-elevator-artifact-data-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-value-elevator-artifact-data.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
git commit -m "feat: 支持 DeepSeek 价值定位结构化产物数据"
```
