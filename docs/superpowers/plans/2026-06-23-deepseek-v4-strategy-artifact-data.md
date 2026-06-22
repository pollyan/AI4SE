# DeepSeek V4 TEST_DESIGN/STRATEGY Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `TEST_DESIGN/STRATEGY` 像 `CLARIFY` 一样由 DeepSeek V4 JSON mode 输出 `artifact_data`，并由后端确定性渲染完整测试策略蓝图。

**Architecture:** 复用现有 `artifact_data_renderers.py` 作为共享 renderer registry，在同一 `AgentTurnOutput`/artifact Markdown contract 下新增 STRATEGY schema 和 renderer。`agent_runtime.py` 只扩展 stage capability/instruction/retry 选择，不新增 workflow 专属 runtime、API、store 或前端协议。

**Tech Stack:** Python 3.11、Pydantic v2、pytest、现有 New Agents backend contract/runtime tests。

---

## 文件结构

- 修改 `tools/new-agents/backend/artifact_data_renderers.py`：新增 STRATEGY Pydantic models、renderer、registry 分支和共享 Markdown/Mermaid/visual helper。
- 修改 `tools/new-agents/backend/agent_runtime.py`：让 `TEST_DESIGN/STRATEGY` 使用 `artifact_data` instruction；补充 STRATEGY JSON 示例；retry 文案继续围绕 `artifact_data`。
- 修改 `tools/new-agents/backend/tests/test_artifact_data_renderers.py`：先写 STRATEGY schema/render/contract RED 测试。
- 修改 `tools/new-agents/backend/tests/test_agent_runtime.py`：先写 STRATEGY instruction、parse、retry RED 测试。
- 修改 `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`：记录 STRATEGY 迁移完成和后续未迁移范围。

## Task 1: RED - STRATEGY artifact_data renderer tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify later: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] **Step 1: 写失败测试**

在 `test_artifact_data_renderers.py` 中新增 `VALID_STRATEGY_ARTIFACT_DATA`，覆盖 `document_info`、`strategy_summary`、`quality_goals`、`risks`、`test_techniques`、`test_layers`、`test_points`、`tradeoffs`、`stage_gate`。

新增测试：

```python
def test_strategy_artifact_data_rejects_inconsistent_rpn():
    invalid = {
        **VALID_STRATEGY_ARTIFACT_DATA,
        "risks": [
            {
                **VALID_STRATEGY_ARTIFACT_DATA["risks"][0],
                "rpn": 999,
            }
        ],
    }

    with pytest.raises(ValidationError, match="rpn"):
        StrategyArtifactData.model_validate(invalid)


def test_render_strategy_artifact_data_is_deterministic_and_contract_valid():
    first = render_agent_turn_from_artifact_data(
        {
            "chat": "我已形成风险驱动测试策略，请确认右侧蓝图。",
            "artifact_data": VALID_STRATEGY_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CASES",
            },
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )
    second = render_agent_turn_from_artifact_data(
        {
            "chat": "我已形成风险驱动测试策略，请确认右侧蓝图。",
            "artifact_data": VALID_STRATEGY_ARTIFACT_DATA,
            "stage_action": {
                "type": "request_next_stage",
                "target_stage_id": "CASES",
            },
            "warnings": [],
        },
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert first == second
    assert first is not None
    assert first.artifact_update.markdown is not None
    assert "# 测试策略蓝图" in first.artifact_update.markdown
    assert "quadrantChart" in first.artifact_update.markdown
    assert "block-beta" in first.artifact_update.markdown
    assert "```ai4se-visual" in first.artifact_update.markdown
    assert '"type": "risk-board"' in first.artifact_update.markdown
    assert (
        validate_agent_turn(
            first,
            workflow_id="TEST_DESIGN",
            current_stage_id="STRATEGY",
        )
        == first
    )
```

- [ ] **Step 2: 运行 RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: FAIL，原因是 `StrategyArtifactData` 未定义或 `TEST_DESIGN/STRATEGY` renderer 未配置。

## Task 2: GREEN - STRATEGY schema 与 renderer

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] **Step 1: 实现最小 schema**

新增模型：`StrategySummary`、`QualityGoal`、`StrategyRisk`、`TestTechnique`、`TestLayer`、`TestPoint`、`Tradeoff`、`StrategyArtifactData`。所有模型继承 `StrictArtifactDataModel`，列表字段使用 `Field(min_length=1)`，`StrategyRisk` 用 model validator 校验 `rpn == severity * occurrence * detection`。

- [ ] **Step 2: 实现确定性 renderer**

新增 `render_test_design_strategy_markdown(data)`，输出固定章节：

- `# 测试策略蓝图`
- `## 1. 策略摘要`
- `## 2. 质量目标`
- `## 3. 风险识别与 FMEA`
- `### 3.1 风险矩阵`
- `### 3.2 风险明细`
- `## 4. 测试技术选型`
- `## 5. 测试分层策略`
- `### 5.1 测试金字塔`
- `### 5.2 分层明细`
- `## 6. 测试点拓扑`
- `## 7. 资源与取舍`
- `## 8. 阶段门禁`

Mermaid 和 visual 输出由后端生成，不从模型复制 Markdown。

- [ ] **Step 3: 注册 renderer**

更新 `render_agent_turn_from_artifact_data()`，当 `(workflow_id, current_stage_id) == ("TEST_DESIGN", "STRATEGY")` 时校验 `StrategyArtifactData` 并返回 `AgentTurnOutput`。

- [ ] **Step 4: 运行 GREEN**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: PASS。

## Task 3: RED/GREEN - Runtime instruction、parse 与 retry

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [ ] **Step 1: 写失败测试**

新增测试覆盖：

- `build_structured_output_instruction("TEST_DESIGN", "STRATEGY")` 包含 `artifact_data`、`quality_goals`、`risks`、`risk-board`，且不要求模型输出完整 Markdown。
- `parse_agent_turn_output_text(..., workflow_id="TEST_DESIGN", current_stage_id="STRATEGY")` 能把 STRATEGY `artifact_data` 渲染为 contract-valid `AgentTurnOutput`。
- `build_raw_json_retry_prompt(..., workflow_id="TEST_DESIGN", current_stage_id="STRATEGY")` 要求修正 `artifact_data`，并禁止输出 Markdown/Mermaid/table。

- [ ] **Step 2: 运行 RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -q
```

Expected: FAIL，原因是 STRATEGY 尚未命中 artifact_data instruction 或 parse 分支。

- [ ] **Step 3: 实现最小 runtime 改动**

更新 `supports_artifact_data_rendering()` 支持 `("TEST_DESIGN", "STRATEGY")`。把 artifact_data instruction 从 CLARIFY 专用常量改成按 stage 取 schema 示例；STRATEGY 示例包含 `quality_goals`、`risks`、`test_techniques`、`test_layers`、`test_points`、`tradeoffs`、`stage_gate`。

- [ ] **Step 4: 运行 GREEN**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -q
```

Expected: PASS。

## Task 4: 文档记录与回归验证

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [ ] **Step 1: 更新 todo**

在当前进展中新增 `TEST_DESIGN/STRATEGY` 已迁移；在迁移顺序中把 `STRATEGY` 标记为已完成，并保留 `CASES`、`DELIVERY` 和其它 workflow 未迁移。

- [ ] **Step 2: 格式化**

Run:

```bash
black tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
```

- [ ] **Step 3: 最小验证**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py -q
.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py
git diff --check -- docs/superpowers/specs/2026-06-23-deepseek-v4-strategy-artifact-data-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-strategy-artifact-data.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
```

- [ ] **Step 4: 聚焦提交**

只暂存本轮文件，确认 `git status --short` 没有主工作区外文件，然后提交：

```bash
git add docs/superpowers/specs/2026-06-23-deepseek-v4-strategy-artifact-data-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-strategy-artifact-data.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
git commit -m "feat: 支持 DeepSeek STRATEGY 结构化产物数据"
```

## Self-review

- Spec 覆盖：schema、renderer、runtime instruction、retry、contract validation、todo 更新和验证命令均有对应任务。
- Placeholder scan：无 TBD/TODO/implement later。
- Type consistency：计划中的类型名、函数名和文件路径与现有 `CLARIFY` 实现模式一致。
