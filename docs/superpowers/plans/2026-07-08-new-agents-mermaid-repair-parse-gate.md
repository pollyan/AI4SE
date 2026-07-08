# New Agents Mermaid Repair Parse Gate Implementation Plan

> **For agentic workers:** This plan is intentionally small. Use the main Agent as integrator; only read-only explorer/reviewer subagents are appropriate unless a future slice creates disjoint write scopes.

**Goal:** 让 Mermaid repair 结果在写回 ChatPane / ArtifactPane 前必须通过 Mermaid parse，repair 失败继续保持显式错误状态。

**Architecture:** 保持 `/api/utils/mermaid/repair` 为用户显式辅助入口。前端 `retryMermaidGeneration()` 请求 repair endpoint 后，对 `repairedCode` 做 trim、Mermaid sanitizer 和 `mermaid.parse(..., { suppressErrors: false })` 校验；只有校验通过才返回代码。ArtifactPane 调用时额外传入 `workflowId/stageId/currentArtifact`，后端在返回前替换候选 Mermaid block 并复用 `validate_agent_turn` 校验完整 artifact contract。调用方仍按现有 `null -> 不替换` 行为保留原始错误。

**Tech Stack:** TypeScript, Vitest, Mermaid JS, existing New Agents frontend service.

## File Map

- Modify: `tools/new-agents/frontend/src/services/__tests__/mermaidRetryService.test.ts`
  - Mock `mermaid.parse`。
  - 覆盖 repair 成功必须 parse 后返回。
  - 覆盖 repaired code parse 失败返回 `null`。
  - 覆盖 parse 返回 `false` 返回 `null`。
- Modify: `tools/new-agents/frontend/src/services/mermaidRetryService.ts`
  - 引入 existing `sanitizeMermaidCode`。
  - 支持可选 artifact context，并随 repair 请求发给后端。
  - repair response shape 通过后先 validate repaired code。
  - 失败时返回 `null`，不让父组件替换 Markdown。
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - 调用 `retryMermaidGeneration()` 时传入当前 workflow、stage 和 artifact content。
- Modify: `tools/new-agents/backend/request_schemas.py`
  - `MermaidRepairRequest` 增加可选 `workflowId/stageId/currentArtifact`。
  - 上下文字段必须成组出现；有上下文时 `blockIndex` 必填且 workflow/stage 必须匹配。
- Modify: `tools/new-agents/backend/routes.py`
  - repair 成功后如果有 artifact context，替换候选 Mermaid block 并调用 `validate_agent_turn`。
  - contract 校验失败返回 JSON error，不返回可写入的 `repairedCode`。
- Modify: `tools/new-agents/backend/tests/test_request_schemas.py`
  - 覆盖上下文字段成组校验。
- Modify: `tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py`
  - 覆盖有上下文时会做 artifact contract 校验。
  - 覆盖 contract 失败时 endpoint 返回错误。
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
  - 记录本轮执行、验证和子智能体审查结果。

## Task 1: RED tests

- [x] 更新 `mermaidRetryService.test.ts`，加入 Mermaid mock、parse gate 和 artifact context 请求体断言。
- [x] 更新 backend request schema / endpoint tests，加入 contract gate 断言。
- [x] 运行：

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/mermaidRetryService.test.ts
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_request_schemas.py::test_parse_mermaid_repair_request_accepts_artifact_contract_context tools/new-agents/backend/tests/test_request_schemas.py::test_parse_mermaid_repair_request_requires_complete_artifact_contract_context tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py::test_mermaid_repair_validates_candidate_artifact_contract tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py::test_mermaid_repair_rejects_candidate_when_artifact_contract_fails -q
```

Expected: 至少新增测试失败，原因是当前 service 未调用 `mermaid.parse`，且会返回未验证的 repaired code。

## Task 2: Implement parse gate

- [x] 在 `mermaidRetryService.ts` 中增加内部 `validateRepairedMermaidCode()`。
- [x] 对 endpoint 返回的 `repairedCode` 先 trim；空值直接失败。
- [x] 用 `sanitizeMermaidCode()` 生成用于 parse 和返回的规范化代码。
- [x] 调用 `mermaid.parse(sanitized, { suppressErrors: false })`；异常或返回 `false` 都视为修复失败。
- [x] 保持 fetch / response shape 错误返回 `null` 的现有外部契约。
- [x] 让 ArtifactPane 传入 artifact context。

## Task 3: Implement backend artifact contract gate

- [x] 扩展 `MermaidRepairRequest` 和 parser。
- [x] 添加 backend helper 替换 nth Mermaid block。
- [x] 有 artifact context 时构造 `AgentTurnOutput(chat="已完成 Mermaid 图表修复校验。", artifact_update.replace.markdown=candidate)` 并调用 `validate_agent_turn`。
- [x] Contract failure 转为 repair JSON error，前端保持 `null -> 不替换`。

## Task 4: Verification and record

- [x] 运行聚焦 service 测试。
- [x] 运行相关前端回归：

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/mermaidRetryService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/ArtifactPane.test.tsx src/core/__tests__/llm.test.ts
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_request_schemas.py tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

- [x] 运行 `cd tools/new-agents/frontend && npm run lint`。
- [x] 更新结构化失败治理 todo 的第 7 轮记录。
- [x] `git diff --check`。
- [ ] 如果当前功能切片完整，通过后提交并 push；按用户指令，当前功能完成后再评估是否把所有用户既有代码改动一起提交到 GitHub。
