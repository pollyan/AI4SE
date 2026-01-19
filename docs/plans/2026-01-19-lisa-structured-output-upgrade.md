# Lisa 智能体产出物系统升级计划 (Phase 1 & 2)

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 彻底解决产出物更新不稳定的问题，通过引入 LangChain `with_structured_output` 和双节点架构，实现稳定、类型安全的文档生成与对话能力。

**Architecture:** 
- **Phase 1 (Hybrid Node)**: 采用 **Streaming Structured Output** 模式。在单节点内，替换 `bind_tools` 为 `with_structured_output`。定义 `WorkflowResponse` 复合结构体，模型可同时输出思考（`thought`）和文档更新（`update_artifact`）。**核心改进**：利用 LangChain 的 `stream` 能力监听 Pydantic 对象的局部更新（Partial Chunk），自动推送 `text-delta` (对话) 和 `artifact-update` (产出物) 给前端，彻底废弃手动正则解析。
- **Phase 2 (Dual Node)**: 将思考与行动拆分为独立节点（Reasoning Node + Artifact Node），实现关注点分离，进一步提升复杂场景下的稳定性。

**Tech Stack:** Python, LangChain, LangGraph, Pydantic

---

## Phase 1: 引入 Streaming Structured Output (单节点混合模式)

### Task 1: 定义复合响应结构体 `WorkflowResponse`

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/schemas.py`

**Step 1: Write the schema test**
创建 `tools/ai-agents/backend/tests/test_lisa_schemas.py`，测试 `WorkflowResponse` 能正确嵌套 `UpdateArtifact` 和 `thought`。

```python
from backend.agents.lisa.schemas import WorkflowResponse, UpdateArtifact

def test_workflow_response_structure():
    # 测试完整结构
    data = {
        "thought": "正在生成文档",
        "update_artifact": {
            "key": "test_design_strategy",
            "markdown_body": "# Strategy"
        }
    }
    resp = WorkflowResponse(**data)
    assert resp.thought == "正在生成文档"
    assert resp.update_artifact.key == "test_design_strategy"
```

**Step 2: Implement `WorkflowResponse`**
在 `schemas.py` 中定义结构体。

```python
class WorkflowResponse(BaseModel):
    thought: str = Field(description="思考过程、对用户的回复或澄清问题")
    update_artifact: Optional[UpdateArtifact] = Field(
        default=None, 
        description="需要更新的文档内容。仅在明确需要生成或修改文档时使用。"
    )
```

**Step 3: Verify**
运行测试确保 Schema 定义正确。

### Task 2: 创建 Streaming Listener 测试套件

**Files:**
- Create: `tools/ai-agents/backend/tests/agents/lisa/test_structured_streaming.py`

**Step 1: Create simulation test**
编写测试，模拟 `structured_llm.stream()` 返回的一系列 Partial WorkflowResponse 对象。
验证监听逻辑能：
1. 捕获 `thought` 的增量变化 -> 触发 `text-delta` 事件。
2. 捕获 `update_artifact` 的全量/增量变化 -> 触发 `artifact-update` 事件。

### Task 3: 改造 `workflow_execution_node` (核心)

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/nodes/workflow_test_design.py`

**Step 1: Replace `bind_tools` with `with_structured_output`**
- 移除 `llm.bind_tools(...)`
- 使用 `structured_llm = llm.with_structured_output(WorkflowResponse)`
- **Prompt 调整**: 更新 System Prompt，告知模型必须使用 `WorkflowResponse` 结构来回复。

**Step 2: Implement Streaming Loop**
- 使用 `for chunk in structured_llm.stream(messages):`
- `chunk` 是 `WorkflowResponse` 的实例（可能是 Partial 的）。
- **Diff Logic**: 
    - 比较当前 `chunk.thought` 和上一次的 `thought`，计算 delta，推送到 writer。
    - 检查 `chunk.update_artifact`。如果有值且发生变化，推送到 writer。

**Step 3: Final State Update**
- 流式结束后，使用最终完整的 `WorkflowResponse` 更新 `state["messages"]` (thought) 和 `state["artifacts"]` (update_artifact)。

**Step 4: Verify with Test**
运行 Task 2 创建的测试，以及现有的集成测试。

---

## Phase 2: 拆分双节点 (Dual Node Architecture)

### Task 4: 定义 `ReasoningNode` 和 `ArtifactNode`

**Files:**
- Create: `tools/ai-agents/backend/agents/lisa/nodes/reasoning.py`
- Create: `tools/ai-agents/backend/agents/lisa/nodes/artifact_updater.py`

**Step 1: Implement Reasoning Node**
- 只负责对话和决策。
- 输出：`AIMessage` (包含 "Next Step: Update Artifact" 的特殊标记或结构化意图)。

**Step 2: Implement Artifact Node**
- 只负责生成文档。
- 输入：当前对话上下文。
- 输出：`UpdateArtifact` (通过 `with_structured_output` 强制)。

### Task 5: 重构 Graph 结构

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/graph.py`

**Step 1: Update Nodes**
- 替换 `workflow_execution_node` 为 `reasoning_node` 和 `artifact_node`。

**Step 2: Add Conditional Edges**
- `reasoning_node` -> (check intent) -> `artifact_node`
- `reasoning_node` -> (no intent) -> `END`
- `artifact_node` -> `END` (或返回 reasoning 确认)

**Step 3: Verify**
运行全链路测试，确保对话和文档生成依然正常。

---

## Execution Handoff
Plan saved. Ready to execute Phase 1.
