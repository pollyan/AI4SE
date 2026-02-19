# 上下文感知产出物同步 (Context-Aware Artifact Sync) 测试需求文档

## 1. 简介 (Introduction)
本测试需求文档旨在验证 **Lisa 智能体上下文感知产出物同步** 功能的正确性。该功能通过引入 Hint 机制，解决 Artifact Agent 缺乏 Reasoning Agent 上下文的问题，确保关键决策和风险提示能准确同步到文档中。

## 2. 测试范围 (Test Scope)
- **核心逻辑**: Reasoning Agent 生成 Hint -> LisaState 传递 Hint -> Artifact Agent 接收并注入 Prompt。
- **涉及模块**:
    - `ReasoningResponse` Schema 定义
    - `LisaState` 状态管理
    - `build_artifact_update_prompt` Prompt 构建逻辑
    - `reasoning_node` 与 `artifact_node` 的数据流转

## 3. 功能测试需求 (Functional Requirements)

| 需求ID | 需求描述 | 优先级 | 验收标准 (Acceptance Criteria) |
| :--- | :--- | :--- | :--- |
| **REQ-001** | **Hint 字段定义** | P0 | `ReasoningResponse` 中 `artifact_update_hint` 字段必须为可选 (Optional)，且默认值为 None。 |
| **REQ-002** | **Prompt 注入逻辑 - 有 Context** | P0 | 当传入有效的 `reasoning_hint` 时，`build_artifact_update_prompt`生成的 Prompt 必须包含 `CONTEXT FROM REASONING AGENT` 上下文块。 |
| **REQ-003** | **Prompt 注入逻辑 - 无 Context** | P0 | 当 `reasoning_hint` 为 None 时，Prompt 中**严禁**出现空的上下文块或占位符，需保持原样。 |
| **REQ-004** | **上下文优先级** | P1 | 若同时存在 `reasoning_hint` 和 `incremental_context`，Hint 上下文块必须出现在 Incremental Context 之前，以确保高优先级指令被优先处理。 |
| **REQ-005** | **状态传递** | P0 | `reasoning_node` 输出的 Hint 必须被正确写入 `LisaState`，并在随后的 `artifact_node` 执行中被正确读取。 |

## 4. 场景测试用例 (Scenario Test Cases)

### SC-01: 关键信息确认 (Critical Info Confirmation)
**前置条件**: 用户在对话中确认了一个关键技术决策（例如：确认使用乐观锁）。
**输入**:
- User Input: "确认库存扣减使用乐观锁方案。"
**预期结果**:
1.  `ReasoningResponse.artifact_update_hint` 不为空，包含 "库存使用乐观锁" 及潜在风险提示。
2.  `ArtifactNode` 的 Prompt 中包含 `**来自推理智能体的重要上下文**: ...库存使用乐观锁...`。
3.  最终生成的文档更新了相关章节，明确了乐观锁机制及风险。

### SC-02: 无需更新场景 (No Update Scenario)
**前置条件**: 用户进行闲聊或简单确认，未涉及文档变更。
**输入**:
- User Input: "好的，明白了。"
**预期结果**:
1.  `ReasoningResponse.artifact_update_hint` 为 None 或空字符串。
2.  `ArtifactNode` 的 Prompt 中不包含 `CONTEXT FROM REASONING AGENT` 区块。
3.  文档未发生不必要的变更。

### SC-03: 混合上下文场景 (Mixed Context Scenario)
**前置条件**: 既有增量更新需求（如 Status 变更），又有关键 Hint（如新增风险点）。
**输入**:
- User Input: "把这个任务标记为完成，并且注意下高并发问题。"
**预期结果**:
1.  Prompt 同时包含 Incremental Context (任务状态) 和 Hint Context (高并发风险)。
2.  Hint Context 在 Prompt 中的位置靠前，作为高优先级指导。

## 5. 依赖与环境 (Dependencies)
- **测试环境**: 本地 pytest 环境。
- **数据依赖**: 需要 mock `LisaState` 和 `ReasoningResponse` 对象。
