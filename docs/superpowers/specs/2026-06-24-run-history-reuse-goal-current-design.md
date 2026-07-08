# Run 历史复用中心主线化设计

## 背景

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 E06「Run 历史中心增强」列为 P1 功能闭环切片。当前 `master` 是 `e35c9643 docs(goal): 明确 Superpowers 头脑风暴细化规则`，主线已有 run persistence、run list、run snapshot restore 和 Header 历史会话弹窗，但历史入口仍偏“恢复列表”，不是“复用中心”：用户无法在恢复前判断 run 是否有可复用 artifact，无法按复用状态筛选，也不能把一个历史 run 复制成独立新 run 后继续探索。

本轮目标是在隔离 worktree `.worktrees/run-history-reuse-goal-current` 中，把历史会话升级为完整复用闭环。已有旧分支 `codex/run-history-reuse-center-after-handoff` 的 `f3666273` 可作为工程输入，但该分支不包含当前 `master` 的 `e35c9643`，本轮必须重新基于当前主线做 RED 检查、移植、验证和提交。

## Superpowers 头脑风暴执行记录

### 1. Explore Project Context

- 问：当前项目事实是什么，而不是上一轮记忆是什么？
  答：`AGENTS.md` 要求 `tools/new-agents/` 继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、run/artifact persistence 和共享 UI。目标模式 playbook 要求本轮 CGA 后用 Superpowers 头脑风暴细化需求，再写中文 spec/plan，严格 TDD。当前主工作区有既有未提交改动，不能直接写。当前主线 `tools/new-agents/backend/run_persistence.py` 和 `routes.py` 有 run list / snapshot 基础，前端 Header 有历史会话弹窗，但缺 clone、reuseStatus、artifact 预览和复制失败反馈。
- 问：这个需求是否过大，需要拆成多个 spec？
  答：不需要拆成多个 spec。E06 是单一用户意图：复用历史工作。它需要后端列表/复制 API、前端 service、Header 交互和测试一起完成，否则用户无法从“找到历史 run”推进到“判断并继续复用”。但它不包含跨 run 对比、分享权限或质量治理面板，这些属于后续切片。
- 问：当前已有相关模式是什么？
  答：后端已有 `get_run_snapshot()`、run/message/artifact/context summary persistence；前端已有 `runSnapshotService` 和 Header 历史 modal；workspace state 可以恢复 snapshot。E06 应复用这些模型，不新增 runtime、SSE、agent 专属 store 或 renderer。

### 2. Visual Companion Decision

- 问：是否需要视觉辅助？
  答：不需要。虽然 Header 历史 modal 是 UI，但本轮遵循已有布局，只增加筛选、预览和动作，不需要另做视觉方案比较。用 component tests 验证用户交互更直接。

### 3. Clarifying Questions

- 问：这个能力包真正服务的用户是谁？
  答：持续使用 New Agents 的 PM、QA、BA 和研发负责人。他们经常需要回到历史分析、复制旧上下文做变体探索，或继续未完成的 run。
- 问：用户要完成的真实任务是什么？
  答：用户要在历史记录中快速判断哪个 run 值得复用，查看当前 artifact 摘要，然后继续原 run 或复制成新 run，避免从空白上下文重新开始。
- 问：成功状态是什么？
  答：历史弹窗不只是列表，而是复用中心：用户能按全部/当前 workflow/复用状态筛选，看到复用状态和 artifact 摘要，选择 run 后预览 artifact，点击继续进入源 run，点击复制为新 run 后进入新 run。
- 问：复用状态如何定义？
  答：本轮采用轻量规则，不替代 E08 质量评分：`ready` 表示 run 有当前 artifact 且状态不是 failed；`needs_artifact` 表示没有当前 artifact 且状态不是 failed；`failed` 表示 run 状态为 failed。
- 问：复制语义是什么？
  答：新 run 复制源 run 的 workflow、agent、current stage、model、messages、当前 artifact versions 和 context summaries，状态为 `active`。不复制协作批注、章节锁、审计事件、runtime metrics 或测试资产集合，因为这些是源 run 的审阅/执行历史。
- 问：失败路径有哪些？
  答：非法 `reuseStatus` 返回 400；源 run 不存在时 clone 返回明确错误；snapshot/preview 读取失败时前端展示错误；clone 失败时不导航、不修改当前 workspace，并显示可见错误。
- 问：哪些内容本轮明确不做？
  答：不做跨 run diff、不做收藏、不做多用户分享权限、不做 E08 workflow 质量评分、不做 E09 运行统计趋势、不做 agent 专属 API/store/runtime。

### 4. Approaches

- 方案 A：只在前端 Header 里增加本地筛选和预览。
  优点：改动小。
  缺点：不能复制为新 run，筛选无法由后端统一解释，历史列表仍无法形成复用闭环。
  结论：不选。
- 方案 B：新增 clone API 和 reuseStatus，但不改 Header 交互。
  优点：后端能力完整。
  缺点：用户仍看不到 artifact 预览，也不知道何时该 clone；能力不可发现。
  结论：不选。
- 方案 C：完整复用中心：后端 list/clone + 前端 service + Header 筛选/预览/继续/复制 + tests。
  优点：覆盖完整用户动作链，复用现有 persistence/snapshot/store，不新增运行时分支。
  缺点：触达后端 API 和 Header 主路径，必须扩大验证。
  结论：选择。

### 5. Presented Design

- Architecture：后端在既有 run persistence 上增加复用状态计算、`reuseStatus` 过滤和 `clone_agent_run()`；routes 增加 `POST /api/agent/runs/<run_id>/clone`。前端扩展 `runSnapshotService` 和 Header 历史 modal，继续复用 snapshot restore 和 workspace store。
- Components：`run_persistence.py` 负责 list item reuse status 和 clone；`routes.py` 负责查询参数校验和 clone endpoint；`runSnapshotService.ts` 负责严格解析和 clone 调用；`Header.tsx` 负责筛选、选中、预览、继续、复制和错误反馈；测试覆盖 persistence、endpoint、service 和 Header。
- Data Flow：用户打开历史 -> 前端用 workflow/reuseStatus 查询 run list -> 选中 run 后读取 snapshot 作为预览 -> 点击继续时恢复源 snapshot 并导航 -> 点击复制时调用 clone API -> 后端创建新 active run 并返回 snapshot -> 前端恢复新 snapshot 并导航到新 run。
- Error Handling：后端对非法复用状态显式 400；clone 源 run 不存在显式失败；前端对列表、预览和复制分别展示错误，不静默降级，不构造假 snapshot。
- Testing：先 RED 用当前基线检查 clone API / reuseStatus 缺失；GREEN 后运行 backend `test_run_persistence.py`、`test_agent_endpoint.py`，frontend `runSnapshotService.test.ts`、`Header.test.tsx`，再跑 `npm run lint`、`py_compile` 和 `git diff --check`。

## 用户故事

作为持续使用 New Agents 的用户，当我需要复用历史分析结果或基于旧 artifact 做新一轮探索时，我可以在历史中心筛选 run、预览 artifact、继续原 run 或复制为新 run，从而把历史工作转化为可继续推进的新上下文。

## 范围

纳入本轮：

- `GET /api/agent/runs` 支持 `reuseStatus=ready|needs_artifact|failed` 过滤。
- run list item 返回 `reuseStatus`。
- 新增 `POST /api/agent/runs/<run_id>/clone`，返回新 run snapshot。
- clone 复制 messages、当前 artifact versions、context summaries 和 run 元信息，不修改源 run。
- Header 历史弹窗展示复用状态筛选、当前 artifact 预览、继续和复制动作。
- 前端 service 严格解析 `reuseStatus`，支持 clone API。
- 文档记录 E06 已消化，并保留 E03/E05/E08/E09 作为后续候选。

不纳入本轮：

- 跨 run diff。
- 收藏。
- 多用户分享/权限。
- E08 workflow 质量评分。
- E09 运行统计趋势。
- 真实模型 smoke。
- 新增 Agent Runtime、SSE、workflow manifest、artifact renderer 或 agent 专属 store。

## 验收条件

1. Given 当前主线缺少 clone API
   When 运行 RED 检查
   Then `routes.py` 中没有 `/clone` route 或 endpoint tests 失败，证明本轮不是空跑。

2. Given run list 中存在 ready、needs_artifact、failed 三类 run
   When 调用 `GET /api/agent/runs?reuseStatus=<status>`
   Then 后端只返回对应状态，非法状态返回 400。

3. Given 一个包含 messages、artifact 和 context summary 的 run
   When 调用 clone API
   Then 新 run 为 active，保留 workflow/agent/stage/model/messages/current artifacts/context summaries，源 run 不变。

4. Given 用户打开 Header 历史中心
   When 用户筛选并选择 run
   Then 能看到 reuse status、最后消息、artifact 预览，以及继续/复制动作。

5. Given clone API 失败
   When 用户点击复制
   Then 前端展示错误，不导航，不污染当前 workspace。

## 风险与控制

- Header 组件已有较多职责，新增 UI 时只沿用现有 modal，不做大规模重构。
- clone 不能复制审计/协作历史，避免把源 run 的人工复审事实错误带到新 run。
- reuse status 是轻量复用状态，不等同于质量评分；后续 E08 可在此基础上增加质量筛选。
- 本轮触及主用户路径，验证范围必须覆盖 backend persistence/API、frontend service/Header 和 TypeScript lint。

## CI 等价验证计划

| 风险面 | 本地命令 | 目的 |
| --- | --- | --- |
| 后端 persistence/API | `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py -q` | 验证 reuseStatus、clone、snapshot 行为 |
| 前端 service/Header | `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/Header.test.tsx` | 验证严格解析、过滤、预览、继续、复制、错误反馈 |
| TypeScript | `cd tools/new-agents/frontend && npm run lint` | 捕获类型和 JSX 错误 |
| Python 语法 | `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/run_persistence.py tools/new-agents/backend/routes.py` | 捕获语法错误 |
| Diff hygiene | `git diff --check e35c9643..HEAD` | 捕获 whitespace 错误 |

## Spec 自审

- 无 TBD/TODO 占位。
- 范围聚焦 E06，不混入 E08/E09/E05。
- 覆盖入口、动作、系统处理、可见结果、状态承接、失败反馈和证据。
- 与 `AGENTS.md` 的共享 runtime / persistence / UI 约束一致。
