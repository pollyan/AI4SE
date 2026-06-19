# New Agents Artifact 批注回复与解决状态设计

## Current State Gap Analysis

事实源快照：
- 已读取：`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/core/types.ts`、`tools/new-agents/frontend/src/store.ts`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/services/runSnapshotService.ts`、`tools/new-agents/backend/models.py`、`tools/new-agents/backend/run_persistence.py`。
- 按需未展开：模型 runtime、workflow prompts、PDF/DOCX 导出。本切片只深化 artifact 批注协作，不改变模型生成和导出链路。

能力包聚合：
| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 批注回复与解决状态 | Todo P1.7 剩余：批注回复/解决状态、协作体验深化 | 用户添加批注 -> 回复讨论 -> 标记已解决/重新打开 -> 保存到 run snapshot -> 恢复后状态仍在 | 只做回复或只做状态都不能表达“这条批注处理完了吗”；两者一起形成完整处理闭环 | 后端 persistence/API 测试、前端 store/service/ArtifactPane 测试 |
| 正文选区精确锚点 | Todo P1.7 剩余 | 批注绑定具体选区 | 需要 selection 与锚点漂移策略 | 后续 |
| 服务端审阅轨迹 | Todo P1.7 剩余 | 记录每次行级/批注操作审计 | 需要审计模型和 API | 后续 |

候选 gap：
| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 批注回复与解决状态 | Todo P1.7 | 批注可跟进并关闭 | 当前只能新增/删除批注 | 无法表达讨论和处理完成 | 高 | 中 | 高 | 本轮 |
| 正文选区精确锚点 | Todo P1.7 | 批注定位更准确 | 只有 excerpt | 定位粗 | 中 | 中高 | 中 | 后续 |
| 服务端审阅轨迹 | Todo P1.7 | 操作可审计 | 当前只保存当前状态 | 审计不足 | 中 | 中高 | 高 | 后续 |

排序结论：
1. 选择批注回复与解决状态，因为它直接补齐“批注不仅能留，还能被处理”的用户闭环。
2. 正文锚点和审阅轨迹暂不选，因为需要更复杂的数据迁移和 UI 形态。

切片准入判断：
- 用户可感知动作链：打开批注面板 -> 回复批注 -> 标记已解决或重新打开 -> 历史会话恢复后状态仍在。
- 相邻缺口合并：回复和解决状态一起做，避免只有讨论没有 closure 或只有 closure 没有过程。
- Superpowers 成本合理性：跨前后端 contract、UI、store 和 snapshot，需要 TDD 验证。
- 过薄风险检查：不是单按钮；包含存储、同步、恢复和交互。
- 能力增量句：完成后，用户现在可以把 artifact 批注作为可处理事项推进，而不只是静态备注。

切片厚度门禁：
- 入口：ArtifactPane 批注面板。
- 动作：回复批注、标记已解决、重新打开。
- 处理：store 更新批注状态和 replies，service 同步 run collaboration state，后端持久化。
- 可见结果：批注卡显示状态、回复列表和操作按钮。
- 状态承接：snapshot 返回并恢复 status/replies。
- 失败反馈：同步失败复用现有协作状态错误提示。
- 证据：pytest、Vitest、lint/build/diff check。
- 结论：通过。

## 用户故事

作为审核产出物的用户，当我给文档留下批注后，我希望团队可以在批注下补充回复，并在问题处理完后标记为已解决；之后恢复历史会话时，这条批注的处理过程和状态仍然保留。

## 验收条件

1. Given 保存 artifact collaboration state 的 payload 包含批注 `status` 和 `replies`，When 后端保存并返回 snapshot，Then 这些字段被原样返回。
2. Given 前端 snapshot 包含批注 `status` 和 `replies`，When service 解析和 store 恢复，Then 状态和回复可读。
3. Given 用户在 ArtifactPane 回复批注，When 当前存在 `currentRunId`，Then UI 显示回复并调用协作同步 API。
4. Given 用户标记批注已解决或重新打开，When 当前存在 `currentRunId`，Then UI 状态变化并同步到 run。

## 文件范围

- 修改：`tools/new-agents/backend/models.py`
- 修改：`tools/new-agents/backend/run_persistence.py`
- 修改：`tools/new-agents/backend/tests/test_run_persistence.py`
- 修改：`tools/new-agents/backend/tests/test_agent_endpoint.py`
- 修改：`tools/new-agents/frontend/src/core/types.ts`
- 修改：`tools/new-agents/frontend/src/store.ts`
- 修改：`tools/new-agents/frontend/src/services/runSnapshotService.ts`
- 修改：`tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts`
- 修改：`tools/new-agents/frontend/src/__tests__/store.test.ts`
- 修改：`tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- 修改：`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
- 修改：`docs/todos/new-agents-ux-professionalization.md`

## 非目标

- 不做多人身份、权限或通知。
- 不做正文选区精确锚点。
- 不做服务端审计日志。
- 不改变 Agent Runtime 或 workflow-specific 行为。
