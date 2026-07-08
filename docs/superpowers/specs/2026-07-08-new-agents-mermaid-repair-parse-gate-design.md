# New Agents Mermaid Repair Parse Gate 设计

## 目标承接检查

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`。
- 已读取：`tools/new-agents/frontend/src/services/mermaidRetryService.ts`、`tools/new-agents/frontend/src/components/Mermaid.tsx`、`tools/new-agents/frontend/src/components/ChatPane.tsx`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/core/llm.ts`。
- 工作区状态：`tools/new-agents` 和 `docs/todos` 当前无未提交改动；工作区仍存在用户确认的无关大规模变更，本轮只 stage 本功能相关文件。

承接结论：
- 当前 P0 待办是“结构化产出失败治理”的第 7 轮视觉稳定化专项。
- `INCIDENT_REVIEW/ROOT_CAUSE.cause-map` 结构化视觉纵切已完成；本轮选择剩余未闭合的“收紧 Mermaid repair 架构边界”。
- 当前 `/api/utils/mermaid/repair` 是用户显式触发的辅助入口，不能自动替换正式 artifact，不能把失败状态包装成成功。
- 只做前端 Mermaid parse 不足以完整覆盖 todo 中的 artifact contract 要求；ArtifactPane 替换当前 artifact 时需要把 workflow、stage 和完整 artifact 交给后端共享 contract 校验。

质量门与改道检查：
- 未发现新的 LLM judge 低于 80 分记录。
- 本轮不改变 Agent Runtime、typed SSE、artifact_data contract、run persistence 或 Lisa/Alex 工作流配置。
- 本轮必须保证 repair 失败继续显式展示原始 Mermaid 错误，不隐藏为成功渲染。

子智能体 / 旁路审查决策：
- 已派发只读 explorer `Tesla` 审查 Mermaid repair 调用路径、测试缺口和是否需要 backend 改动；其结论是 ArtifactPane 当前会直接 `setArtifactContent(updatedContent)`，完整满足 todo 需要后端 artifact contract 校验。
- 主 Agent 继续本地实现不重叠路径：spec/plan、前后端聚焦测试和最小实现。
- 不派发可写 worker，原因是当前写入范围集中在同一 repair 链路，高冲突组件由主 Agent 统一接线更安全。

## 用户故事

作为 New Agents 用户，当右侧产出物或消息中的 Mermaid 图表渲染失败并点击“重新生成图表”时，我希望系统只在修复结果通过 Mermaid 语法校验后才替换原图表代码；如果修复结果仍然无效，页面继续展示原始错误和手动修复入口，而不是把坏图写回正式内容。

## 验收条件

1. Given Mermaid repair endpoint 返回合法 `repairedCode`
   When 前端 `retryMermaidGeneration()` 收到响应
   Then 它必须先调用 Mermaid parse 校验修复后的代码，校验通过后才返回可替换代码。

2. Given Mermaid repair endpoint 返回的 `repairedCode` 仍然无法 parse
   When 用户在 ArtifactPane 或 ChatPane 点击重新生成图表
   Then `retryMermaidGeneration()` 返回 `null`，父组件不替换当前 Markdown，原始 Mermaid 错误状态继续可见。

3. Given repair endpoint 失败、返回无效 JSON shape、空代码或 parse 返回 `false`
   When `retryMermaidGeneration()` 处理结果
   Then 它返回 `null`，不抛出未捕获异常，不写入 artifact/message。

4. Given ArtifactPane 对当前 artifact 中的 Mermaid block 触发 repair
   When 前端请求 `/api/utils/mermaid/repair`
   Then 请求必须携带 `workflowId`、`stageId` 和 `currentArtifact`，后端在返回 repairedCode 前替换候选 block 并调用共享 `validate_agent_turn` 校验完整 artifact contract。

5. Given 后端 contract 校验发现替换后的 artifact 缺少必需标题、必需 Mermaid 类型或必需结构化视觉
   When repair endpoint 处理该请求
   Then 返回 JSON error，前端 `retryMermaidGeneration()` 返回 `null`，父组件不写入 artifact/message。

6. Given 正式 `agent_turn` artifact 带 Mermaid block
   When 共享 SSE 解析路径处理最终 artifact
   Then 现有 `core/llm.ts` Mermaid parse gate 仍然生效；本轮不降低正式 artifact contract。

## 设计取舍

- Mermaid parse gate 放在前端 `mermaidRetryService.ts`，因为当前浏览器前端已依赖 `mermaid.parse`，而 backend Flask repair endpoint 没有 Mermaid JS runtime。
- Artifact contract gate 放在后端同一个 `/api/utils/mermaid/repair` endpoint 中，作为可选上下文增强：只有请求带 `workflowId`、`stageId`、`currentArtifact` 时校验完整 artifact；ChatPane 不带 artifact 上下文，只做 Mermaid parse。
- ChatPane 和 ArtifactPane 都通过同一个 `retryMermaidGeneration()` 替换 Mermaid block；service 层 parse 门禁覆盖两条路径，ArtifactPane 额外传入 artifact context 触发后端 contract 门禁。
- 后端 `/api/utils/mermaid/repair` 不新增专属 API；仍然是共享 repair endpoint，只在有完整上下文时调用共享 `validate_agent_turn`。
- 本轮不增加自动修复、不重新生成正式 artifact、不推进 stage、不新增 workflow 专属渲染路径。

## 实现边界

允许写入：
- `docs/superpowers/specs/2026-07-08-new-agents-mermaid-repair-parse-gate-design.md`
- `docs/superpowers/plans/2026-07-08-new-agents-mermaid-repair-parse-gate.md`
- `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- `tools/new-agents/frontend/src/services/mermaidRetryService.ts`
- `tools/new-agents/frontend/src/services/__tests__/mermaidRetryService.test.ts`
- `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- `tools/new-agents/backend/request_schemas.py`
- `tools/new-agents/backend/routes.py`
- `tools/new-agents/backend/tests/test_request_schemas.py`
- `tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py`

不触碰：
- backend Agent Runtime、workflow manifest、artifact_data renderer、Lisa/Alex 专属配置。
- `ChatPane.tsx` 行为；ArtifactPane 只增加 repair 请求上下文，不改变渲染管线或 store 结构。
- 当前工作区中的用户既有大规模改动。
