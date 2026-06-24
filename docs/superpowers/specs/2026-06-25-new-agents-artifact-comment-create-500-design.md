# New Agents Artifact Comment Create 500 Design

## CGA 摘要

`docs/todos/refactor/2026-06-25-new-agents-artifact-comment-create-500.md` 是当前活跃 Bug。当前批注新增入口位于 `ArtifactPane`，前端通过 `updateRunArtifactCollaboration` 把 `comments` 和 `sectionLocks` 整体 PUT 到 `/api/agent/runs/{runId}/artifact-collaboration`。后端 route 只捕获请求校验和业务 `ValueError`，持久化层如果抛出 `SQLAlchemyError` 会落入 Flask 默认 500，前端也只展示状态码，无法给用户可诊断原因。

## 用户故事

作为 New Agents 用户，我在已有 Artifact 的产出物上新增批注时，批注应通过共享协作状态接口稳定保存并可恢复；如果 run、artifact 或持久化状态无效，后端应返回可诊断 JSON 错误，前端应展示错误并回滚本地 optimistic 批注，避免假装保存成功。

## 设计

- 后端 `PUT /api/agent/runs/{runId}/artifact-collaboration` 要求 payload 引用的 stage 已有 artifact version；缺失时返回 400 JSON 错误。
- 后端捕获 `SQLAlchemyError`，执行 session rollback，记录 request id 和 run id，返回统一 JSON `{ "error": "协作状态保存失败" }`。
- 前端 `updateRunArtifactCollaboration` 在非 2xx 响应时优先读取 JSON `error`，将其纳入抛出的错误消息。
- `ArtifactPane` 继续复用当前 optimistic local state 和共享 collaboration state PUT；保存失败时恢复本次操作前的 comments / sectionLocks，不新增 workflow、agent 或 comment 专属 API。

## 非目标

- 不重新设计批注 UI。
- 不新增单条批注 API。
- 不改变 run snapshot、artifact version、section lock 或 audit event contract。
- 不为 Lisa、Alex、DeepSeek 或特定 workflow 分叉 collaboration store / renderer。

## 验收

- 持久化异常不会返回默认 Flask HTML 500，响应体包含可诊断 `error`。
- 缺失 run 返回 404；缺失目标 artifact 返回 400。
- 前端保存失败提示包含后端错误消息，而不是只显示 HTTP status。
- 前端保存失败后不保留未成功持久化的本地批注。
- 有效 collaboration payload 的现有保存、snapshot 恢复和 audit event 行为不变。
