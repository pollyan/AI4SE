# New Agents 阶段推进成熟度门禁设计

日期：2026-06-25

## 背景

`docs/todos/refactor/2026-06-24-new-agents-stage-transition-readiness-gate.md` 记录了 TEST_DESIGN / CLARIFY 阶段在信息不足时仍可能展示进入 STRATEGY 的确认控件。当前前端既信任后端 `stage_action`，也会从聊天文案中推断 `NEXT_STAGE`，但缺少共享的确定性成熟度门禁。

本用户故事实现第一条门禁切片：当 CLARIFY 产物中存在 P0/P1 且“阻断”的待确认问题时，后端必须取消进入下一阶段动作，并让左侧对话说明缺口。

## Current State Gap Analysis

### 现状证据

- `tools/new-agents/backend/stream_services.py` 是共享 Agent Runtime typed SSE 出口；模型最终 `AgentTurnOutput` 会同时作为 `agent_delta` 和 `agent_turn` 发给前端。
- `tools/new-agents/frontend/src/core/llm.ts` 的 `getAgentTurnAction()` 会在 `stage_action` 存在时返回 `NEXT_STAGE`，也会从聊天文案推断下一阶段 CTA。
- `tools/new-agents/backend/artifact_data_renderers.py` 的 `ClarifyArtifactData` 已有 `clarification_questions` 字段，包含 `priority`、`blocking`、`status`，渲染后也保留同名表格列。
- 当前没有后端共享门禁模块，也没有 `stage_readiness_blocked` 这类可审计 warning。

### 目标状态

- 后端在发出最终 `AgentTurnOutput` 前执行共享门禁。
- 对 `TEST_DESIGN/CLARIFY`，如果右侧产物的待澄清问题包含 P0/P1、阻断、待确认/未确认/需补充状态，则：
  - `stage_action` 被置为 `null`。
  - `warnings` 增加 `stage_readiness_blocked`。
  - `chat` 追加不能进入下一阶段的原因和缺口清单。
- 前端看到 `stage_readiness_blocked` warning 时不推断 `NEXT_STAGE`。
- 不新增 agent/workflow 专属 runtime、API path、store 或 renderer。

### 非目标

- 不实现强制推进 UI 或风险接受审计字段。
- 不覆盖所有 workflow 的成熟度规则。
- 不把低优先级非阻断问题作为门禁。
- 不改变 typed SSE schema；复用现有 `warnings` 和 `stage_action`。

## 验收标准

- CLARIFY artifact 存在 P0/P1 阻断待确认问题且模型返回 `stage_action=request_next_stage` 时，后端发出的 delta/final 事件都不包含可用 stage action。
- 被门禁阻断的 turn 包含 `stage_readiness_blocked` warning，并在 chat 中说明还不能进入下一阶段。
- 前端即使收到可推进语气的 chat，只要有 `stage_readiness_blocked` warning，也不显示 NEXT_STAGE。
- 既有 artifact_truncated 降级逻辑不退化。
