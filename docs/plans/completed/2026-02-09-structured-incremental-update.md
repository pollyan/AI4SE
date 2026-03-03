# 结构化增量更新实施计划

> **给 Claude 的提示:** 必需子技能：使用 superpowers:executing-plans 来逐个任务地实施此计划。

**目标:** 将工件生成从“无状态的全量 Markdown 替换”转换为“有状态的结构化增量更新”，以提高稳定性和用户体验。

**架构:**
- **后端:** 修改 `LisaState` 以存储 Pydantic 对象而不是 Markdown 字符串。实现 `ArtifactNode` 逻辑，将 LLM 生成的 JSON 补丁与现有状态合并。
- **前端:** 更新 `ArtifactPanel`，以便使用专门的组件（ReactFlow/Mermaid, 表格）直接渲染结构化的 JSON 数据，而不是解析 Markdown。
- **协议:** 使用 Pydantic 模型作为数据交换的单一事实来源 (SSOT)。

**技术栈:** Python (Pydantic, LangGraph), React (TypeScript, Tailwind), Mermaid/ReactFlow

---

### 任务 1: 后端数据结构化 (MVP: 需求文档)

**文件:**
- 修改: `tools/ai-agents/backend/agents/lisa/state.py`
- 修改: `tools/ai-agents/backend/agents/lisa/nodes/artifact_node.py`
- 修改: `tools/ai-agents/backend/agents/lisa/artifact_patch.py`
- 测试: `tools/ai-agents/backend/tests/test_artifact_structure.py`

**步骤 1: 编写状态结构的失败测试**

```python
# tools/ai-agents/backend/tests/test_artifact_structure.py
import pytest
from tools.ai-agents.backend.agents.lisa.state import LisaState
from tools.ai-agents.backend.agents.lisa.artifact_models import RequirementDoc

def test_state_stores_structured_artifact():
    state = LisaState()
    # verify artifacts is Dict[str, Dict] or Pydantic model, not str
    state["artifacts"] = {
        "requirement": {
            "scope": ["login"],
            "rules": [],
            "flow_mermaid": "graph TD; A-->B;"
        }
    }
    assert isinstance(state["artifacts"]["requirement"], dict)
```

**步骤 2: 更新 LisaState 定义**

修改 `tools/ai-agents/backend/agents/lisa/state.py` 中的 `LisaState`，将 `artifacts` 显式类型化为 `Dict[str, Any]` (或 `Dict[str, Union[RequirementDoc, ...]]`)。

**步骤 3: 实现 JSON 补丁逻辑**

增强 `tools/ai-agents/backend/agents/lisa/artifact_patch.py` 以支持通过 ID 更新列表项。

**列表合并规则定义：**

| 场景 | 行为 |
|------|------|
| Patch 中有新 ID | 追加到列表末尾 |
| Patch 中 ID 已存在 | 更新该项的字段 |
| 原列表中的项不在 Patch 中 | 保留（不删除） |
| LLM 返回无效 JSON | 捕获异常，记录日志，返回原状态 |

```python
def test_patch_update_list_item_by_id():
    original = {"items": [{"id": "1", "val": "a"}, {"id": "2", "val": "b"}]}
    patch = {"items": [{"id": "1", "val": "updated"}]}
    # Expected: items[0] updated, items[1] unchanged
    result = merge_artifacts(original, patch)
    assert result["items"][0]["val"] == "updated"
    assert len(result["items"]) == 2

def test_patch_append_new_item():
    original = {"items": [{"id": "1", "val": "a"}]}
    patch = {"items": [{"id": "2", "val": "new"}]}
    result = merge_artifacts(original, patch)
    assert len(result["items"]) == 2
    assert result["items"][1]["id"] == "2"

def test_patch_invalid_json_returns_original():
    original = {"items": [{"id": "1", "val": "a"}]}
    invalid_patch = "not a json"
    result = merge_artifacts(original, invalid_patch)
    assert result == original  # 返回原状态，不崩溃
```

**步骤 4: 更新 ArtifactNode 以跳过 Markdown 转换**

修改 `tools/ai-agents/backend/agents/lisa/nodes/artifact_node.py`:
- 移除 `UpdateStructuredArtifact` 处理程序中的 `convert_to_markdown` 调用。
- 改为从状态加载现有的工件（如果有）。
- 调用 `merge_artifacts(old_state, new_patch)`。
- 将结果保存回状态。

**步骤 5: 提交**

```bash
git add tools/ai-agents/backend/agents/lisa/state.py tools/ai-agents/backend/agents/lisa/nodes/artifact_node.py tools/ai-agents/backend/agents/lisa/artifact_patch.py tools/ai-agents/backend/tests/test_artifact_structure.py
git commit -m "feat(backend): support structured artifact storage and incremental patching"
```

---

### 任务 2: 前端数据适配 (MVP: 假设列表)

**文件:**
- 创建: `tools/ai-agents/frontend/src/components/artifact/StructuredRequirementView.tsx`
- 修改: `tools/ai-agents/frontend/src/components/artifact/ArtifactRenderer.tsx`
- 测试: `tools/ai-agents/frontend/src/components/artifact/__tests__/StructuredRequirementView.test.tsx`

**步骤 1: 创建测试数据夹具**

创建一个包含 `RequirementDoc` 样本数据（范围、规则、假设）的 JSON 文件。

**步骤 2: 创建 StructuredRequirementView 组件**

创建 `StructuredRequirementView.tsx`，接受 `RequirementDoc` 对象作为 props。
- 实现 `ScopeSection` (列表)
- 实现 `RuleTable` (包含列: ID, 描述, 来源)
- 实现 `AssumptionTable` (包含列: ID, 问题, 状态, 备注)

**步骤 3: 更新 ArtifactRenderer**

修改 `ArtifactRenderer.tsx`:
- 检查 `artifact.content` 是对象 (JSON) 还是字符串 (Markdown)。
- 如果是对象，渲染 `StructuredRequirementView`。
- 如果是字符串，保持现有的 `RequirementView`（用于迁移期间的向后兼容）。

**步骤 4: 验证渲染**

运行前端测试或 Storybook（如果可用）以验证新组件是否正确渲染 JSON 数据。

**步骤 5: 提交**

```bash
git add tools/ai-agents/frontend/src/components/artifact/StructuredRequirementView.tsx tools/ai-agents/frontend/src/components/artifact/ArtifactRenderer.tsx
git commit -m "feat(frontend): add structured renderer for requirement docs"
```

---

### 任务 3: 增量更新的 LLM 提示词工程

**文件:**
- 修改: `tools/ai-agents/backend/agents/lisa/prompts/artifacts.py`
- 测试: `tools/ai-agents/backend/tests/test_prompt_generation.py`

**步骤 1: 编写提示词生成测试**

```python
def test_prompt_instructs_incremental_update():
    prompt = build_artifact_update_prompt(
        artifact_key="req",
        current_stage="clarify",
        template_outline="",
        existing_artifact={"assumptions": [{"id": "Q1"}]}
    )
    assert "INCREMENTAL UPDATE" in prompt
    assert "Q1" in prompt  # Context should be included
```

**步骤 2: 更新 Prompt 构建器**

修改 `build_artifact_update_prompt` 以:
- 接受 `existing_artifact` 作为参数。
- 如果存在，注入到提示词中: "Current State: {json}"。
- 添加指令: "Only output changed items. Use ID to match existing items." (仅输出更改的项目。使用 ID 匹配现有项目。)

**步骤 3: 提交**

```bash
git add tools/ai-agents/backend/agents/lisa/prompts/artifacts.py
git commit -m "feat(prompt): optimize prompt for incremental json updates"
```

---

### 任务 4: 端到端验证 (Spike)

**文件:**
- 创建: `tools/ai-agents/backend/tests/test_e2e_flow.py`

**步骤 1: 模拟完整流程**

编写一个脚本，用于：
1. 用空工件初始化 `LisaState`。
2. 模拟 LLM 响应 1 (创建 Q1, Q2)。
3. 调用 `ArtifactNode` -> 验证状态有 Q1, Q2。
4. 模拟 LLM 响应 2 (更新 Q1 状态, 添加 Q3)。
5. 调用 `ArtifactNode` -> 验证状态有 Q1(已更新), Q2(未变), Q3。

**步骤 2: 运行并修复**

运行脚本并修复 `artifact_patch.py` 或 `ArtifactNode` 中的任何集成问题。

**步骤 3: 提交**

```bash
git add tools/ai-agents/backend/tests/test_e2e_flow.py
git commit -m "test(e2e): verify structured incremental update flow"
```
