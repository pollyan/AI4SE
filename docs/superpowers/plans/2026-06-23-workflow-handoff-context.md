# Workflow Handoff 上下文强化 Implementation Plan

## Milestone

完成一个共享 Workflow Handoff 上下文闭环：后端从来源 artifact 派生摘要、未确认项和目标输入说明，前端严格解析并展示，启动 handoff 后把增强 prompt 写入目标 run。

## TDD 步骤

1. RED: 扩展 backend handoff 测试。
   - 在 `test_workflow_handoffs.py` 断言 export 包含 `sourceArtifactSummary`、`unresolvedItems`、`targetInputSummary`。
   - 断言 prompt 包含摘要、未确认项、目标用途。
   - 断言 start 创建的 target run message 使用增强 prompt。

2. RED: 扩展 frontend service 测试。
   - 在 `workflowHandoffService.test.ts` 的 fetch/start payload 中加入新增字段。
   - 新增 malformed case，证明缺少或类型错误会显式失败。

3. RED: 扩展 ChatPane 测试。
   - 在 handoff mock 中加入新增字段。
   - 断言卡片展示来源版本、摘要、未确认项和目标用途。

4. GREEN: 后端最小实现。
   - 在 `workflow_handoffs.py` 中新增确定性摘要和未确认项提取 helper。
   - `_build_handoff` 返回新增字段。
   - `_build_handoff_prompt` 使用新增上下文，继续复用 `HANDOFF_CONTEXT_MAX_CHARS`。
   - 不新增 runtime、SSE、API path、store 或 renderer。

5. GREEN: 前端最小实现。
   - 扩展 `WorkflowHandoff` 类型。
   - 扩展 `workflowHandoffService` strict parser。
   - 扩展 `ChatPane` handoff card 呈现，保持共享 `applyWorkflowHandoff` 不变。

6. 文档记录。
   - 更新 `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`，将 E07 标记为已消化并写明边界与验证。
   - 更新 `docs/todos/refactor/README.md` 的当前入口说明。

7. 验证与提交。
   - 运行 backend handoff tests。
   - 如隔离 frontend worktree 缺 `node_modules`，临时复用主 worktree `node_modules` symlink，验证后删除。
   - 运行 frontend handoff/ChatPane tests、lint、`git diff --check`。
   - 检查 `git status --short`，形成聚焦 commit。

## 退出准则

- 所有新增字段由 backend export/start、frontend parser、ChatPane UI 和 tests 同步覆盖。
- 未触碰主 worktree 既有未提交改动。
- 无 agent-specific runtime/API/store/renderer。
