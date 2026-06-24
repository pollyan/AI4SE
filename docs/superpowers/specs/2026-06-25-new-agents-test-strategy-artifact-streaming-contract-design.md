# New Agents 测试策略产出物结构化流式契约设计

日期：2026-06-25

## 背景

`docs/todos/refactor/2026-06-24-new-agents-test-strategy-artifact-format-streaming-bug.md` 记录了 TEST_DESIGN 工作流第二阶段 STRATEGY 的两个问题：最终产出物格式不稳定，以及右侧产出物不像第一阶段一样逐步流式呈现。

当前代码已经具备后端 `artifact_data` 结构化渲染能力，且 STRATEGY raw JSON 流式路径已有后端测试覆盖。剩余风险集中在提示词契约不一致和前端缺少 STRATEGY delta 回归覆盖。

## Current State Gap Analysis

### 现状证据

- `tools/new-agents/backend/agent_runtime.py` 已为 `TEST_DESIGN/STRATEGY` 提供 `artifact_data` 结构化输出指令，并要求模型不要输出完整 Markdown、Mermaid 代码块或 risk-board JSON 代码块，由后端确定性渲染。
- `tools/new-agents/backend/tests/test_agent_runtime.py` 已覆盖 STRATEGY raw JSON 流式输出在最终完成前渲染出 `artifact_update.markdown`。
- `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts` 的通用系统提示仍写死“如果本轮需要更新右侧产出物，必须提供完整、全部的 Markdown 文档内容”。
- `tools/new-agents/backend/agent_contracts.py` 的 Markdown 产出物契约没有声明 `artifact_data` 结构化契约优先级，容易与运行时追加的 `artifact_data` 指令并存时产生冲突。
- `tools/new-agents/frontend/src/core/__tests__/llm.test.ts` 已覆盖 STRATEGY 最终 `agent_turn`，但没有覆盖 STRATEGY `agent_delta` 草稿帧先于最终帧更新右侧产出物。

### 目标状态

- 前端通用系统提示表达为“完整产出物数据”，并明确后端结构化契约要求 `artifact_data` 时以 `artifact_data` 为准。
- 后端 Markdown 契约明确只约束 `artifact_update.markdown` 输出形态；当运行时追加 `artifact_data` 结构化指令时，模型应返回完整 `artifact_data`，由后端渲染 Markdown。
- STRATEGY typed SSE 前端解析测试覆盖 `run_started`、`agent_delta.artifact_update.markdown` 和最终 `agent_turn.artifact_update.markdown`，确保草稿帧可先于最终帧更新右侧产出物。

### 非目标

- 不新增 workflow 专属 runtime、API path、store 或 renderer。
- 不重写 TEST_DESIGN 全阶段模板。
- 不改变阶段推进成熟度门禁；该问题由独立 todo 处理。
- 不把结构化产物降级成裸 JSON 或纯文本展示。

## 验收标准

- STRATEGY 系统提示不再把所有产出物更新强制写死为 Markdown。
- 后端 Markdown 契约包含 `artifact_data` 结构化契约优先说明。
- 前端可解析 STRATEGY `agent_delta` 草稿 artifact，并在最终 `agent_turn` 到达后收敛到最终 artifact。
- 现有后端 `artifact_data` 渲染、Mermaid/ai4se-visual 合同和共享 Agent Runtime 流式路径不退化。
