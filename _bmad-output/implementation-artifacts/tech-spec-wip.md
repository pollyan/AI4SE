---
title: 'Lisa 智能体上下文感知产出物同步'
slug: 'lisa-artifact-sync'
created: '2026-02-12'
status: 'in-progress'
stepsCompleted: [1]
tech_stack: []
files_to_modify: []
code_patterns: []
test_patterns: []
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
1.  `ReasoningNode` -> 输出: `thought` + `artifact_update_hint` ("用户确认库存并发使用数据库乐观锁。更新需求规则章节。")
2.  `State` -> 更新: `state.latest_artifact_hint = artifact_update_hint`
3.  `ArtifactNode` -> 输入: `state.latest_artifact_hint`
4.  `ArtifactNode` -> Prompt: "上下文提示: 推理智能体建议: {latest_artifact_hint}"
