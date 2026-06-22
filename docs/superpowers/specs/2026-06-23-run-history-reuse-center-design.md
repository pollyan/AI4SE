# Run History Reuse Center Design

## Current State Gap Analysis

- `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 中 E06 仍为 P1 活跃缺口：历史 run 需要支持继续、复制为新 run、按 workflow/质量筛选、预览当前 artifact。
- 当前后端 `/api/agent/runs` 已支持 workflow、query、pagination，并返回 `currentArtifact.summary`；`/api/agent/runs/{runId}` 已支持 snapshot 恢复。
- 当前前端 Header 历史会话弹层可打开历史列表、搜索、按当前 workflow 筛选和导航到原 run，但不能按复用质量筛选，不能在列表内预览 artifact 细节，也不能复制为新的持久化 run。
- 如果只在前端复制 workspace 状态，会产生没有服务端 runId 的伪会话；本轮必须提供真实后端 clone endpoint，让复制结果可被 snapshot、后续生成和历史列表承接。

## Chosen Design

在现有共享 run persistence 与 Header 历史入口上做增强，不新增 agent 专属 runtime、SSE、store 或 renderer：

- 后端 `list_agent_runs` 增加轻量 `qualityStatus`，并支持 `qualityStatus` query filter：
  - `reusable`: run 状态不是 `failed` 且存在当前 artifact。
  - `needs_artifact`: run 状态不是 `failed` 且没有当前 artifact。
  - `failed`: run 状态为 `failed`。
- 后端新增 `POST /api/agent/runs/{runId}/clone`：
  - 创建新的 runId，复制 workflow/agent/currentStage/model。
  - 复制 messages。
  - 复制每个 artifact 的当前版本为新 run 的 v1，并保留 `artifactData`。
  - 复制 context summaries。
  - 不复制 comments、section locks、audit events、turn metrics；这些是源 run 的审阅/运行痕迹，新 run 应作为可继续工作的独立副本。
- 前端 `runSnapshotService` 解析 `qualityStatus`，增加 `cloneRun` service。
- Header 历史会话弹层增加质量筛选、artifact 预览卡片和“复制为新会话”动作。
- 复制成功后关闭历史弹层并跳转到新 run 的 workspace URL，复用现有 URL runId 恢复链路。

## Requirements

- `GET /api/agent/runs?qualityStatus=reusable` 只返回匹配质量状态的 run；未知质量状态返回 400。
- run list item 必须返回 `qualityStatus`，前端解析时缺失或非法值要显式失败。
- clone endpoint 必须返回完整 snapshot，且 snapshot 的 runId 不同于源 runId。
- clone endpoint 复制后的 artifact version 从 1 开始，但内容和 artifactData 与源 run 当前版本一致。
- clone endpoint 不复制协作审阅痕迹和 turn metrics，避免把源 run 的人工审阅状态误当成新 run 状态。
- Header 历史中心必须保留现有打开原 run 能力，同时新增质量筛选、预览和复制动作。
- 失败时 UI 显示“无法复制历史会话”，不跳转。

## Non-Goals

- 不实现收藏、跨 run 对比、分享权限或 run 删除。
- 不做完整 artifact diff 预览。
- 不复制 test asset collections 或 intent-tester 执行结果。
- 不新增新 Agent Runtime、SSE endpoint、agent-specific store 或 renderer。

## Verification

- Backend: run list quality status/filter tests；clone persistence/API tests。
- Frontend service: run list qualityStatus parsing/filter query；cloneRun request/response parsing；malformed quality status failure。
- Frontend Header: quality filter request、artifact preview display、clone success navigation、clone failure feedback。
- Store: existing snapshot restore tests continue covering cloned snapshot recovery.

