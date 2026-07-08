# IDEA CONVERGE 契约同步 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `IDEA_BRAINSTORM/CONVERGE` 的 artifact_data 关键不变量从 manifest 这一份配置同步进入后端 structured instruction 和前端 stage prompt。

**Architecture:** 在 `workflow_manifest.json` 的 CONVERGE stage 新增 `artifactDataContract`，后端通过 `workflow_manifest.py` helper 格式化为 structured output instruction，前端在构建 `WORKFLOWS` 时把同一份 contract guidance 追加到 stage description。Pydantic validators、共享 Agent Runtime、typed SSE、store 和 ArtifactPane 不变。

**Tech Stack:** Python 3.11, pytest, TypeScript 5.x, Vitest, JSON manifest.

---

### Task 1: 写 RED 测试

**Files:**
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`

- [x] **Step 1: 增加后端 manifest -> instruction 同步测试**

在 `test_workflow_contract_sync.py` imports 中加入：

```python
from agent_runtime import build_structured_output_instruction
from workflow_manifest import (
    format_artifact_data_contract_instruction,
    get_stage_artifact_data_contract,
)
```

添加测试：

```python
def test_converge_artifact_data_contract_manifest_drives_backend_instruction():
    contract = get_stage_artifact_data_contract("IDEA_BRAINSTORM", "CONVERGE")

    assert contract is not None
    assert "modelOutputRules" in contract
    assert "forbiddenOutputs" in contract
    assert "rendererOutputs" in contract

    instruction = build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "CONVERGE",
    )
    formatted = format_artifact_data_contract_instruction(
        "IDEA_BRAINSTORM",
        "CONVERGE",
    )

    assert formatted in instruction
    for rule in contract["modelOutputRules"]:
        assert rule in instruction
    for forbidden in contract["forbiddenOutputs"]:
        assert forbidden in instruction
    for renderer_output in contract["rendererOutputs"]:
        assert renderer_output in instruction
```

Expected RED: import fails because `get_stage_artifact_data_contract` / `format_artifact_data_contract_instruction` do not exist.

- [x] **Step 2: 增加后端 instruction 单元测试**

在 `test_agent_runtime.py` 的 CONVERGE instruction 测试附近添加：

```python
def test_idea_converge_structured_output_instruction_uses_manifest_artifact_data_contract():
    instruction = build_structured_output_instruction(
        "IDEA_BRAINSTORM",
        "CONVERGE",
    )

    assert "artifact_data 中所有字符串必须非空" in instruction
    assert "ice_evaluations.idea_id 必须唯一" in instruction
    assert "decision_matrix.recommended_idea_id" in instruction
    assert "validation_experiments.idea_ids" in instruction
    assert "merge_paths.source_idea_ids" in instruction
    assert "不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 quadrantChart" in instruction
    assert "后端会负责确定性渲染右侧收敛聚焦产物和 Mermaid quadrantChart" in instruction
```

Expected RED: this may still pass before implementation because old instruction contains similar text, but it becomes a guard after the manifest-driven formatter lands. The workflow sync test is the primary RED.

- [x] **Step 3: 增加前端 manifest -> prompt 同步测试**

在 `workflows.test.ts` 里添加：

```typescript
    it('appends manifest artifact data contract guidance to IDEA CONVERGE prompt description', () => {
        const convergeStage = WORKFLOWS.IDEA_BRAINSTORM.stages.find(stage => stage.id === 'CONVERGE');

        expect(convergeStage).toBeDefined();
        expect(convergeStage?.description).toContain('【artifact_data 契约同步约束】');
        expect(convergeStage?.description).toContain('ice_evaluations.idea_id 必须唯一');
        expect(convergeStage?.description).toContain('decision_matrix.recommended_idea_id');
        expect(convergeStage?.description).toContain('validation_experiments.idea_ids');
        expect(convergeStage?.description).toContain('merge_paths.source_idea_ids');
        expect(convergeStage?.description).toContain('不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 quadrantChart');
        expect(convergeStage?.description).toContain('后端会负责确定性渲染右侧收敛聚焦产物和 Mermaid quadrantChart');
    });
```

Expected RED: fails because `WORKFLOWS` currently uses only static `CONVERGE_PROMPT` and does not append manifest contract guidance.

- [x] **Step 4: 运行 RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_converge_artifact_data_contract_manifest_drives_backend_instruction tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_converge_structured_output_instruction_uses_manifest_artifact_data_contract -q
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "appends manifest artifact data contract guidance"
```

Expected: backend sync test fails because helper is missing; frontend test fails because prompt description does not include manifest guidance.

Result: backend selected run failed during collection because `workflow_manifest` did not export `format_artifact_data_contract_instruction`; frontend selected run failed because CONVERGE description did not contain `【artifact_data 契约同步约束】`.

### Task 2: 增加 manifest contract 与后端 formatter

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/backend/workflow_manifest.py`

- [x] **Step 1: 在 CONVERGE stage 声明 `artifactDataContract`**

在 `IDEA_BRAINSTORM/CONVERGE` stage 的 `visualContract` 后加入：

```json
"artifactDataContract": {
  "modelOutputRules": [
    "ice_evaluations.idea_id 必须唯一",
    "ice_evaluations.rank 必须唯一",
    "impact、confidence、effort 必须是 1 到 5 的整数",
    "ice_score 必须等于 impact * confidence / effort",
    "decision_matrix.recommended_idea_id、validation_experiments.idea_ids 和 merge_paths.source_idea_ids 只能引用已存在的 idea_id",
    "推荐方案必须同时出现在 ICE 结论和决策矩阵中",
    "stage_gate 至少包含一个 checked=true"
  ],
  "forbiddenOutputs": [
    "完整 Markdown 文档",
    "Markdown 表格",
    "Mermaid 代码块",
    "quadrantChart"
  ],
  "rendererOutputs": [
    "右侧收敛聚焦产物",
    "Mermaid quadrantChart"
  ]
}
```

- [x] **Step 2: 增加 backend manifest stage helper**

在 `workflow_manifest.py` 中加入：

```python
def get_workflow_stage(workflow_id: str, stage_id: str) -> dict[str, Any]:
    workflow = load_workflow_manifest()["workflows"].get(workflow_id)
    if workflow is None:
        raise ValueError(f"未知 workflowId: {workflow_id}")
    for stage in workflow.get("stages", []):
        if stage.get("id") == stage_id:
            return stage
    raise ValueError(f"未知 workflow stage: {workflow_id}/{stage_id}")


def get_stage_artifact_data_contract(
    workflow_id: str,
    stage_id: str,
) -> dict[str, Any] | None:
    stage = get_workflow_stage(workflow_id, stage_id)
    contract = stage.get("artifactDataContract")
    if contract is None:
        return None
    if not isinstance(contract, dict):
        raise ValueError(
            f"artifactDataContract 必须是对象: {workflow_id}/{stage_id}"
        )
    return contract
```

- [x] **Step 3: 增加 formatter 和 list 校验**

在 `workflow_manifest.py` 中加入：

```python
def _string_list(value: Any, field_name: str, workflow_id: str, stage_id: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(
            f"artifactDataContract.{field_name} 必须是非空字符串数组: "
            f"{workflow_id}/{stage_id}"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"artifactDataContract.{field_name} 包含空值: "
                f"{workflow_id}/{stage_id}"
            )
        result.append(item.strip())
    return result


def format_artifact_data_contract_instruction(
    workflow_id: str,
    stage_id: str,
) -> str:
    contract = get_stage_artifact_data_contract(workflow_id, stage_id)
    if contract is None:
        return "artifact_data 中所有字符串必须非空；数组必须至少包含一项。"

    model_output_rules = _string_list(
        contract.get("modelOutputRules"),
        "modelOutputRules",
        workflow_id,
        stage_id,
    )
    forbidden_outputs = _string_list(
        contract.get("forbiddenOutputs"),
        "forbiddenOutputs",
        workflow_id,
        stage_id,
    )
    renderer_outputs = _string_list(
        contract.get("rendererOutputs"),
        "rendererOutputs",
        workflow_id,
        stage_id,
    )
    return (
        "artifact_data 中所有字符串必须非空；数组必须至少包含一项；"
        + "；".join(model_output_rules)
        + "。不要输出"
        + "、".join(forbidden_outputs)
        + "，后端会负责确定性渲染"
        + "和 ".join(renderer_outputs)
        + "。"
    )
```

### Task 3: 后端 instruction 消费 manifest contract

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [x] **Step 1: import formatter**

在 imports 中加入：

```python
from workflow_manifest import format_artifact_data_contract_instruction
```

- [x] **Step 2: 替换 CONVERGE 手写约束句**

把 `IDEA_CONVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` 改为 f-string，并替换原手写约束句：

```python
IDEA_CONVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION = f"""
...
{format_artifact_data_contract_instruction("IDEA_BRAINSTORM", "CONVERGE")}
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
所有字符串内容必须使用合法 JSON 转义；最终 JSON 必须能被 json.loads 解析。
"""
```

Keep the JSON object example unchanged.

### Task 4: 前端 prompt description 消费 manifest contract

**Files:**
- Modify: `tools/new-agents/frontend/src/core/workflowRegistry.ts`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`

- [x] **Step 1: 扩展 manifest stage 类型**

在 `workflowRegistry.ts` 中加入：

```typescript
export type ArtifactDataContract = {
    modelOutputRules?: string[];
    forbiddenOutputs?: string[];
    rendererOutputs?: string[];
};
```

并把 `WorkflowManifestStage` 改为：

```typescript
export type WorkflowManifestStage = {
    id: string;
    name: string;
    promptTemplateId: string;
    artifactDataContract?: ArtifactDataContract;
};
```

- [x] **Step 2: 增加前端 formatter**

在 `workflows.ts` 中加入：

```typescript
const compactStrings = (items: string[] | undefined): string[] => (
    Array.isArray(items)
        ? items.map(item => item.trim()).filter(Boolean)
        : []
);

const formatArtifactDataContractPrompt = (
    contract: { modelOutputRules?: string[]; forbiddenOutputs?: string[]; rendererOutputs?: string[] } | undefined
): string => {
    if (!contract) return '';

    const modelOutputRules = compactStrings(contract.modelOutputRules);
    const forbiddenOutputs = compactStrings(contract.forbiddenOutputs);
    const rendererOutputs = compactStrings(contract.rendererOutputs);
    if (!modelOutputRules.length && !forbiddenOutputs.length && !rendererOutputs.length) {
        return '';
    }

    const lines = ['【artifact_data 契约同步约束】'];
    if (modelOutputRules.length) {
        lines.push(`- ${modelOutputRules.join('；')}`);
    }
    if (forbiddenOutputs.length) {
        lines.push(`- 不要输出${forbiddenOutputs.join('、')}。`);
    }
    if (rendererOutputs.length) {
        lines.push(`- 后端会负责确定性渲染${rendererOutputs.join('和 ')}。`);
    }
    return `\n\n${lines.join('\n')}`;
};
```

- [x] **Step 3: 构建 stage description 时追加 guidance**

把 `description: content.description` 改为：

```typescript
description: `${content.description}${formatArtifactDataContractPrompt(stage.artifactDataContract)}`,
```

### Task 5: GREEN、回归和记录

**Files:**
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- Modify: this plan

- [x] **Step 1: Run GREEN**

Run the RED commands again.

Expected:

- backend selected tests pass.
- frontend selected test passes.

Result: backend selected tests `2 passed`; frontend selected test `1 passed`.

- [x] **Step 2: Run focused backend regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_converge_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_converge_structured_output_instruction_uses_manifest_artifact_data_contract tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_rejects_unknown_recommended_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_rejects_invalid_ice_score tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_skips_validation_experiments_with_unknown_idea_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_skips_merge_paths_with_unknown_idea_reference -q
```

Expected: all selected tests pass.

Result: `19 passed`.

- [x] **Step 3: Run focused frontend regression**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts
```

Expected: all workflow config tests pass.

Result: `16 passed`.

- [x] **Step 4: Run New Agents regression**

Run:

```bash
./scripts/test/test-local.sh new-agents
```

Expected: New Agents frontend and backend suites pass.

Result: New Agents Frontend `719 passed`; New Agents Backend `626 passed, 1 deselected`. Existing React `ArtifactPane.test.tsx` `act(...)` warning still appeared but did not fail the suite.

- [x] **Step 5: Update todo execution record**

Add a new record to `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` for `IDEA_BRAINSTORM/CONVERGE` artifactDataContract sync. Include:

- selected slice and why visual work was deferred;
- RED/GREEN results;
- focused backend / frontend / New Agents results;
- residual risk that only CONVERGE has migrated to manifest artifactDataContract.

Result: updated `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` with RED/GREEN, focused regression, New Agents regression and residual risks.

### Task 6: 全量验证、提交和推送

**Files:**
- Modify: this plan

- [x] **Step 1: Run full local validation**

Run:

```bash
./scripts/test/test-local.sh all
```

If default sandbox fails on browser or port permissions, rerun with approved non-sandbox execution and record both results.

Result: default sandbox `./scripts/test/test-local.sh all` failed on environment permissions: MidScene proxy could not bind `0.0.0.0:3002` with `listen EPERM`, and Playwright Chromium failed with `bootstrap_check_in ... Permission denied (1100)`. Approved non-sandbox rerun passed with `EXIT_STATUS:0`; key results included Intent Tester API `294 passed`, severe flake8 check passed, MidScene proxy `17 passed`, Common Frontend lint/build passed, New Agents Frontend `719 passed`, New Agents Backend `626 passed, 1 deselected`, and New Agents Browser E2E `11 passed, 10 deselected`.

- [x] **Step 2: Run diff checks**

Run:

```bash
rg -n "T[B]D|TO[ ]?DO|待[ ]?补|未[ ]?决|place[ ]?holder" docs/superpowers/specs/2026-07-08-new-agents-converge-contract-sync-design.md docs/superpowers/plans/2026-07-08-new-agents-converge-contract-sync.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
git diff --check -- tools/new-agents/workflow_manifest.json tools/new-agents/backend/workflow_manifest.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/frontend/src/core/workflowRegistry.ts tools/new-agents/frontend/src/core/workflows.ts tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts docs/superpowers/specs/2026-07-08-new-agents-converge-contract-sync-design.md docs/superpowers/plans/2026-07-08-new-agents-converge-contract-sync.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
```

Stage only this slice and run:

```bash
git diff --cached --check
git diff --cached --name-only
```

Result: 占位词扫描无命中；`git diff --check` and `git diff --cached --check` passed; staged file list was limited to this CONVERGE contract-sync slice.

- [x] **Step 3: Commit and push**

Commit message:

```bash
git commit -m "fix(new-agents): 同步Alex收敛契约约束"
git push
```

After push, verify:

```bash
git rev-parse HEAD
git rev-parse @{u}
```

Expected: both SHAs match.

Result: committed core slice as `7239cde9 fix(new-agents): 同步Alex收敛契约约束`; pushed to `origin/codex/structured-failure-diagnostics`; local `HEAD` and upstream both resolved to `7239cde9afbf817c78af6eab0f7b6339f4465aa0`.
