# DeepSeek V4 格式化失败分诊闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在共享运行统计中新增 DeepSeek/格式化输出失败的最近处置队列，让用户按当前 workflow/stage 逐条定位 formatted-output failure 并获得行动建议。

**Architecture:** 后端只扩展现有 `/api/agent/observability` contract，从已有 `AgentRunTurnMetric` 派生 `formatFailureDiagnostics.recentFailures`。前端同步 core types、service parser 和 Header 展示，不新增 DeepSeek 专属 runtime、API、store 或 renderer。

**Tech Stack:** Flask/SQLAlchemy/Python backend tests，React/TypeScript/Zustand/Vitest frontend tests。

---

## 文件范围

- Modify: `tools/new-agents/backend/run_persistence.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/observabilityService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Modify: `docs/todos/refactor/README.md`

## Task 1: 后端 recent formatted failure contract

- [x] Step 1: 在 `test_agent_endpoint.py` 里先扩展 `test_agent_observability_endpoint_groups_formatted_output_diagnostics`，断言 `formatFailureDiagnostics.recentFailures` 返回两条 formatted failure，普通 `SCHEMA_VALIDATION_FAILED` 不进入队列。

- [x] Step 2: 运行：
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_endpoint.py -q -k "formatted_output_diagnostics"`
  预期失败：`KeyError: 'recentFailures'` 或字段缺失断言失败。

- [x] Step 3: 修改 `run_persistence.py`，在 `_format_failure_diagnostics()` 中构造 `recentFailures`，每条包含 `turnId`、`runId`、`workflowId`、`stageId`、`provider`、`model`、`kind`、`label`、`errorCode`、`retryCount`、`createdAt`、`action`。

- [x] Step 4: 运行同一后端测试，预期通过。

- [x] Step 5: 新增 `test_agent_observability_endpoint_filters_formatted_output_recent_failures`，证明 `workflowId`/`stageId` 过滤会同步收窄 `recentFailures`、`byStage` 和 total。

## Task 2: 前端 service/types 严格解析

- [x] Step 1: 在 `observabilityService.test.ts` 的 payload 中添加 `recentFailures`，新增断言解析 `kind`、`label`、`action`、`retryCount`。

- [x] Step 2: 新增 negative test：删除 `formatFailureDiagnostics.recentFailures` 时 `fetchObservabilitySummary()` 抛出 `Invalid observability summary response`。

- [x] Step 3: 运行：
  `npm run test -- --run src/services/__tests__/observabilityService.test.ts`
  预期失败：parser 当前不要求或不返回 `recentFailures`。

- [x] Step 4: 修改 `core/types.ts` 和 `observabilityService.ts`，新增 `ObservabilityFormatFailureRecent` 类型和 parser。

- [x] Step 5: 运行同一前端 service test，预期通过。

## Task 3: Header 处置队列 UI

- [x] Step 1: 在 `Header.test.tsx` 的 observability payload 中添加 `recentFailures`，扩展“shows formatted output diagnostics in runtime observability summary”测试，断言显示“最近格式化失败处置”、错误 label、workflow/stage、provider/model、runId、重试次数和行动建议。

- [x] Step 2: 运行：
  `npm run test -- --run src/components/__tests__/Header.test.tsx -t "formatted output diagnostics"`
  预期失败：页面尚未显示处置队列。

- [x] Step 3: 修改 `Header.tsx` 的格式化输出诊断 section，在现有 top kind/stage/provider 下方新增最近失败列表和空态。

- [x] Step 4: 运行同一 Header test，预期通过。

## Task 4: 文档记录和验证

- [x] Step 1: 更新 DeepSeek todo 当前进展，记录格式化输出处置队列已完成，真实 DeepSeek smoke 仍需外部凭证/网络/额度。

- [x] Step 2: 更新 `docs/todos/refactor/README.md` 当前入口说明。

- [x] Step 3: 运行本轮验证：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_endpoint.py -q -k "formatted_output_diagnostics or filters_formatted_output_recent_failures"`
  - `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx src/core/__tests__/observabilityAlerts.test.ts`
  - `cd tools/new-agents/frontend && npm run build`
  - `git diff --check`

- [ ] Step 4: 聚焦提交：
  `feat(new-agents): 增加 DeepSeek 格式化失败处置队列`

## Self-review

- Spec 覆盖：后端 contract、前端 parser、Header UI、文档记录和验证命令均有任务。
- 占位检查：无 TBD/TODO。
- 类型一致性：计划使用 `recentFailures` 作为 `formatFailureDiagnostics` 的新增数组字段，前后端命名一致。
