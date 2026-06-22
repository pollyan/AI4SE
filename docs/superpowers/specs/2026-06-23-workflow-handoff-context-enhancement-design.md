# Workflow Handoff Context Enhancement Design

## Current State Gap Analysis

- `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 中 E07 仍为 P1 活跃缺口：handoff 需要展示来源版本、关键摘要、未确认项和目标 workflow 输入。
- 2026-06-19 已完成 Alex 到 Lisa handoff 基础能力：manifest 声明 `VALUE_DISCOVERY/BLUEPRINT` 可交给 `TEST_DESIGN/CLARIFY` 或 `REQ_REVIEW/REVIEW`，后端可导出候选并启动目标 run。
- 当前 `workflow_handoffs.py` 只返回 `sourceArtifactVersion` 和一段由全文产物拼接出的 prompt；`ChatPane` 只展示按钮 label；`workflowHandoffService` 没有结构化 context contract。
- 用户在点击接力前看不到来源产物摘要、Lisa 将拿到哪些输入、还有哪些未确认项；目标 run 的首条消息也缺少可审计的上下文边界。

## Chosen Design

在现有共享 handoff API 上扩展只读 payload，不新增 runtime、SSE、API path、store 或 renderer：

- 后端为每个 handoff 构造 `context`：
  - `sourceArtifactTitle`: 来源 artifact 标题。
  - `sourceArtifactSummary`: 面向用户的来源摘要，优先从产物标题和 Lisa Handoff 输入派生。
  - `targetInputSummary`: 目标 workflow 将获得的输入摘要。
  - `unconfirmedItems`: 从来源产物中识别出的待确认/未确认/假设项列表。
- 后端 prompt 在全文产物前加入结构化“接力上下文”块，包含来源版本、目标阶段、输入摘要和未确认项。
- 前端 service 解析可选 `context`，保持旧 payload 兼容但对存在的 context 严格校验。
- `ChatPane` 在“跨智能体接力”卡片中展示来源版本、摘要、目标输入和未确认项数量/明细，让用户点击前能判断接力质量。
- `store.applyWorkflowHandoff` 继续使用现有 shared store，把后端返回的 prompt 作为目标 run 首条用户消息，不新增专属状态。

## Requirements

- handoff payload 包含现有字段，且在后端导出和 start 响应中携带同一份 `context`。
- prompt 必须包含来源 workflow/stage、目标 workflow/stage、来源 artifact version、目标输入摘要和未确认项。
- 结构化 context 必须由现有 artifact 内容确定性派生；不调用模型，不伪造成功状态，不使用隐藏 fallback 掩盖缺口。
- 当前已配置的两个 Alex 到 Lisa handoff 都可复用同一 context 构造逻辑。
- 前端对 malformed `context` 显式失败，不静默吞掉错误。
- `ChatPane` 展示信息必须保持紧凑，不改变消息流、typed SSE 或 run persistence 模型。

## Non-Goals

- 不新增 Lisa、Alex、DeepSeek 或未来 agent 专属 runtime/API/store/renderer。
- 不新增新的 workflow handoff 配置。
- 不实现 Run 历史中心复制/继续。
- 不实现全局 workflow 质量评分。
- 不做 LLM 生成摘要或 judge 打分。

## Verification

- Backend: `tests/test_workflow_handoffs.py` 覆盖 context 导出、prompt 注入、start target run 后首条消息。
- Frontend service: `workflowHandoffService.test.ts` 覆盖 context 解析和 malformed context 失败。
- Frontend UI/store: `ChatPane.test.tsx` 覆盖接力卡片展示 context；`store.test.ts` 保持 handoff 应用链路不回退。
- 最小验证：后端 handoff pytest、前端相关 Vitest、`npm run lint`、`git diff --check`。

