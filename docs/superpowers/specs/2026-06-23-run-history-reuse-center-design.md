# Run History Reuse Center Design

## Current State Gap

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 中 E06 要求历史 run 支持继续、复制为新 run、按 workflow/质量筛选、预览当前 artifact。当前代码已经具备基础设施：`GET /api/agent/runs` 可以列出、搜索、按当前 workflow 过滤历史 run，`GET /api/agent/runs/<run_id>` 可以恢复 snapshot，Header 里有“历史会话”弹窗并能点击打开旧 run。

缺口是它仍是“历史列表”，不是“复用中心”：用户无法在打开前预览当前 artifact，无法判断 run 是否可复用，无法把历史 run 复制成新 run 后继续探索，也没有失败反馈覆盖复制/预览路径。

## Milestone

把 Header 历史会话弹窗升级为 Run 历史复用中心。

用户现在可以：

- 按全部 / 当前 workflow / 复用状态筛选历史 run。
- 在列表中查看 run 的复用状态、当前 artifact 摘要和最后消息。
- 选中 run 后预览当前 artifact 正文节选。
- 选择“继续此 run”进入原 run。
- 选择“复制为新 run”创建独立新 run 并进入新 run，不修改源 run。

## Design Decisions

- 复制语义：新 run 复制源 run 的 workflow、agent、current stage、model、messages、当前 artifact versions 和 context summaries。
- 不复制协作批注、章节锁、审计事件、turn metrics、test asset collections。它们代表源 run 的审阅和执行历史，不应自动变成新 run 的事实。
- 新 run 状态为 `active`，用于后续继续生成。
- 复用状态是 run history 层面的轻量质量状态，不替代 E08 workflow 质量评分：
  - `ready`: run 有当前 artifact 且状态不是 failed。
  - `needs_artifact`: run 没有当前 artifact 且状态不是 failed。
  - `failed`: run 状态为 failed。
- run list API 增加可选 `reuseStatus` 查询参数，并在每个 list item 返回 `reuseStatus`。
- 前端继续复用现有 Header modal、`runSnapshotService` 和 store snapshot restore，不新增 agent 专属 store 或 runtime。

## Requirements

- `GET /api/agent/runs` 支持 `reuseStatus=ready|needs_artifact|failed`，非法值返回 400。
- run list item 返回 `reuseStatus`，前端 parser 严格校验。
- 新增 `POST /api/agent/runs/<run_id>/clone`，返回新 run snapshot。
- clone 不修改源 run。
- clone 后的新 run 能通过既有 `/api/agent/runs/<new_id>` 读取，并保留 messages、artifacts、context summaries。
- Header 历史中心展示复用状态筛选和当前 artifact 预览。
- “继续此 run”导航到源 run。
- “复制为新 run”调用 clone API、恢复返回 snapshot、导航到新 run。
- 列表、预览、复制失败必须有可见错误文案。

## Non-Goals

- 不做跨 run 差异对比。
- 不做 E08 的跨 workflow 质量评分。
- 不复制协作批注、章节锁、审计事件或 turn metrics。
- 不新增 Agent Runtime、SSE、workflow manifest、artifact renderer 或 agent 专属 API 分支。

## Acceptance Checks

- Backend persistence tests prove clone copies run context and does not mutate source.
- Backend endpoint tests prove list filtering and clone endpoint behavior.
- Frontend service tests prove strict parsing, `reuseStatus` query, and clone API.
- Header tests prove user can filter, preview, continue, clone, and see clone failure feedback.
- Todo docs mark E06 consumed and preserve E08/E09/E05 as next candidates.
