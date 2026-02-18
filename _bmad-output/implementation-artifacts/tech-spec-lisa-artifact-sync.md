---
title: 'Lisa 智能体上下文感知产出物同步'
slug: 'lisa-artifact-sync'
created: '2026-02-12'
status: 'done'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['LangGraph', 'Python 3.11', 'Pydantic v2', 'LangChain Core']
files_to_modify: ['tools/ai-agents/backend/agents/lisa/schemas.py', 'tools/ai-agents/backend/agents/lisa/state.py', 'tools/ai-agents/backend/agents/lisa/nodes/reasoning_node.py', 'tools/ai-agents/backend/agents/lisa/nodes/artifact_node.py', 'tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py', 'tools/ai-agents/backend/agents/lisa/prompts/artifacts.py']
code_patterns: ['StateGraph Workflow', 'Command-based Routing', 'Structured Output Stream', 'Incremental Artifact Patching']
test_patterns: ['pytest for backend unit tests', 'integration tests for graph execution']
---

# 概览 (Overview)

### 问题陈述 (Problem Statement)
在 Lisa 智能体架构中，`reasoning_node`（负责对话/推理）和 `artifact_node`（负责更新文档/产出物）作为两个独立的 LLM 调用运行。目前，`artifact_node` 缺乏关于 `reasoning_node` 中得出的具体推理过程或结论的上下文。这导致了数据不一致，即在聊天中确认的关键信息（例如：确认了某个 P0 阻塞性问题）没有及时反映在生成的文档中。

### 解决方案 (Solution)
我们将实施一个 **上下文感知产出物同步 (Context-Aware Artifact Synchronization)** 机制。具体包括：
1.  扩展 `ReasoningResponse` Schema，增加显式的 `artifact_update_hint`（产出物更新提示）字段。
2.  更新 `reasoning_node`，使其根据对话内容填充此提示（例如：“用户确认了库存并发使用数据库乐观锁”）。
3.  通过 `LisaState` 将此提示传递给 `artifact_node`。
4.  修改 `artifact_node` 的 Prompt，使其在生成工具调用时优先考虑此提示。

### 范围 (Scope)
- **包含 (In Scope)**:
    - 修改 `tools/ai-agents/backend/agents/lisa/schemas.py` (`ReasoningResponse`)。
    - 修改 `tools/ai-agents/backend/agents/lisa/state.py` (`LisaState`)。
    - 修改 `tools/ai-agents/backend/agents/lisa/nodes/reasoning_node.py`。
    - 修改 `tools/ai-agents/backend/agents/lisa/nodes/artifact_node.py`。
    - 修改 `tools/ai-agents/backend/agents/lisa/prompts/` 中的相关 Prompt。
- **不包含 (Out of Scope)**:
    - 前端 UI 变更。
    - 其他智能体 (Alex) 的变更。
    - 底层 LLM 配置的变更。

# 开发上下文 (Context for Development)

### 架构约束
- **状态管理**: 必须使用 LangGraph 的 `StateGraph` 和 `LisaState`。
- **工具使用**: 产出物更新必须继续使用 `update_artifact` 或 `UpdateStructuredArtifact` 工具。
- **向后兼容性**: 尽可能不破坏现有的状态检查点（添加可选字段）。

### 当前实现分析
- **推理节点 (Reasoning Node)**: 目前返回 `thought`（回复内容）、`progress_step`（进度步）和 `should_update_artifact`（是否更新标志）。它 **不返回** *具体要更新什么* 的指令。
- **产出物节点 (Artifact Node)**: 目前仅依赖 `state["messages"]` 和 `existing_artifact`。它不得不“重新推理”需要变更的内容，往往会遗漏上一步骤中的细微结论。

### 建议的数据流
1.  `ReasoningNode` -> 输出: `thought` + `artifact_update_hint`
    *   **关键修正**: `artifact_update_hint` **必须包含 ReasoningNode 生成的所有关键结论、衍生风险和新发现的问题**，而不仅仅是用户输入的回显。
    *   示例: "用户确认库存并发使用数据库乐观锁。**风险提示**: 高并发下失败率上升。**行动项**: 更新需求规则章节，明确乐观锁机制，并补充失败重试逻辑。"
2.  `State` -> 更新: `state.latest_artifact_hint = artifact_update_hint`
3.  `ArtifactNode` -> 输入: `state.latest_artifact_hint`
4.  `ArtifactNode` -> Prompt: "上下文提示: 推理智能体建议: {latest_artifact_hint}"

### 代码模式与锚点
- **Schema 定义**: `tools/ai-agents/backend/agents/lisa/schemas.py` -> `ReasoningResponse`
- **状态定义**: `tools/ai-agents/backend/agents/lisa/state.py` -> `LisaState` (添加 `latest_artifact_hint: Optional[str]`)
- **Reasoning Prompt**: `tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py` -> `WORKFLOW_TEST_DESIGN_SYSTEM` (添加关于 artifact_update_hint 的指令)
- **Artifact Prompt**: `tools/ai-agents/backend/agents/lisa/prompts/artifacts.py` -> `build_artifact_update_prompt` (添加参数并注入到模板中)

### 需修改文件列表
| 文件路径 | 变更类型 | 描述 |
|----------|----------|------|
| `tools/ai-agents/backend/agents/lisa/schemas.py` | Modify | 给 `ReasoningResponse` 添加 `artifact_update_hint` 字段 |
| `tools/ai-agents/backend/agents/lisa/state.py` | Modify | 给 `LisaState` 添加 `latest_artifact_hint` 字段 |
| `tools/ai-agents/backend/agents/lisa/nodes/reasoning_node.py` | Modify | 提取 hint 并更新到 State 中 |
| `tools/ai-agents/backend/agents/lisa/nodes/artifact_node.py` | Modify | 读取 hint 并传递给 Prompt 构建函数 |
| `tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py` | Modify | 更新 Reasoning Prompt 指令 |
| `tools/ai-agents/backend/agents/lisa/prompts/artifacts.py` | Modify | 更新 Artifact Prompt 模板以包含 hint |

# 实施计划 (Implementation Plan)

### 1. 基础架构扩展 (Infrastructure Extension)

- [ ] **Task 1: 更新 ReasoningResponse Schema**
  - **File**: `tools/ai-agents/backend/agents/lisa/schemas.py`
  - **Action**: 向 `ReasoningResponse` 类添加 `artifact_update_hint` 字段。
  - **Details**:
    ```python
    artifact_update_hint: Optional[str] = Field(
        default=None,
        description="给产出物更新智能体（Artifact Agent）的直接指令。必须包含本轮对话中确认的关键结论、新发现的风险或需要变更的文档章节。这将作为'全量推理结论交接'。"
    )
    ```

- [ ] **Task 2: 更新 LisaState 定义**
  - **File**: `tools/ai-agents/backend/agents/lisa/state.py`
  - **Action**: 向 `LisaState` 类添加 `latest_artifact_hint` 字段。
  - **Details**: 类型为 `Optional[str]`，默认值为 `None`。

### 2. 推理节点增强 (Reasoning Node Enhancement)

- [ ] **Task 3: 更新 Reasoning Prompt**
  - **File**: `tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py`
  - **Action**: 修改 `WORKFLOW_TEST_DESIGN_SYSTEM` 中的 "响应协议 (Structured Response Protocol)" 部分。
  - **Details**:
    - 增加对 `artifact_update_hint` 的强制要求：只要 `should_update_artifact` 为 True，该字段必填。
    - 明确要求该字段包含：用户决策、新发现的 Insights/Risks、具体的 Action Items。

- [ ] **Task 4: 更新 Reasoning Node 逻辑**
  - **File**: `tools/ai-agents/backend/agents/lisa/nodes/reasoning_node.py`
  - **Action**:
    - 从 `final_response` 中提取 `artifact_update_hint`。
    - 将其放入 `state_updates` 中，键名为 `latest_artifact_hint`。
    - 确保它被传递给后续的 `artifact_node`。

### 3. 产出物节点增强 (Artifact Node Enhancement)

- [ ] **Task 5: 更新 Artifact Prompt 构建器**
  - **File**: `tools/ai-agents/backend/agents/lisa/prompts/artifacts.py`
  - **Action**: 修改 `build_artifact_update_prompt` 函数签名，增加 `reasoning_hint: str | None = None` 参数。
  - **Details**: 在返回的 Prompt 字符串中（如 "系统内部指令..." 之前或之中），插入显式的上下文块：
    ```text
    **来自推理智能体的重要上下文 (CONTEXT FROM REASONING AGENT)**:
    {reasoning_hint}

    请务必根据上述上下文更新文档，尤其是其中提到的风险和决策。
    ```

- [ ] **Task 6: 更新 Artifact Node 逻辑**
  - **File**: `tools/ai-agents/backend/agents/lisa/nodes/artifact_node.py`
  - **Action**:
    - 从 `state` 中读取 `latest_artifact_hint`。
    - 调用 `build_artifact_update_prompt` 时传入此 hint。
    - (可选) 在更新完成后，考虑清空 `state["latest_artifact_hint"]` 以免污染下一轮（或者保留作为历史参考，视 LangGraph 机制而定，通常 State 是累积的，但 artifact_node 是瞬时的）。建议不主动清空，由 reasoning_node 在下一轮覆盖。

# 验收标准 (Acceptance Criteria)

- [ ] **AC 1: Hint 生成验证**
  - **Given**: 用户在对话中确认了一个 P0 问题（如“库存使用乐观锁”）。
  - **When**: `reasoning_node` 完成推理。
  - **Then**: 返回的 `ReasoningResponse` 中 `artifact_update_hint` 字段不为空，且包含“库存使用乐观锁”及可能的风险提示。

- [ ] **AC 2: State 传递验证**
  - **Given**: `reasoning_node` 返回了 hint。
  - **When**: 流程流转到 `artifact_node`。
  - **Then**: `artifact_node` 读取到的 `state["latest_artifact_hint"]` 与前者一致。

- [ ] **AC 3: 文档更新验证 (端到端)**
  - **Given**: 用户确认关键信息，且 Reasoning Node 生成了包含新风险的 hint。
  - **When**: `artifact_node` 执行完毕。
  - **Then**: 生成的 Markdown 文档中包含了用户确认的信息 **以及** Hint 中提到的衍生风险/注意事项。

- [ ] **AC 4: 回退兼容性**
  - **Given**: 旧的历史记录或未包含 hint 的对话。
  - **When**: `artifact_node` 执行。
  - **Then**: 系统不报错，Prompt 中 hint 部分为空或显示默认值，文档更新回退到原有逻辑。

# 依赖与测试 (Dependencies & Testing)

### 依赖
- 无新增外部库依赖。
- 强依赖 `langgraph` 和 `pydantic` 的现有版本。

### 测试策略
- **单元测试** ✅:
  - ✅ `TestReasoningHintInjection`（4 个用例）：验证 hint 注入、无 hint 时不注入、与 incremental context 共存、位置顺序。
  - ✅ `TestReasoningResponseArtifactUpdateHint`（4 个用例）：验证字段可选性、接受有效值、接受 None、不破坏其他字段。
  - 测试文件：`tools/ai-agents/backend/tests/test_prompt_generation.py`
- **集成测试 (Manual/E2E)**:
  - 启动 `ai-agents` 服务。
  - 与 Lisa 对话，模拟 P0 问题确认场景。
  - 检查后台日志中的 `artifact_update_hint` 内容。
  - 检查前端右侧文档是否同步更新。

# 备注 (Notes)
- **Prompt Engineering**: Hint 的 Prompt 指令需要精心调优，避免 LLM 将其视为“用户输入”而产生混淆。明确标注这是“内部上下文”。
- **Token Usage**: 增加 Hint 会略微增加 Token 消耗，但相比于文档不一致带来的返工，这是值得的。
