# New Agents Artifact 协作元数据服务端同步设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/store.ts`、`tools/new-agents/frontend/src/core/types.ts`、`tools/new-agents/frontend/src/services/runSnapshotService.ts`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/backend/models.py`、`tools/new-agents/backend/run_persistence.py`、`tools/new-agents/backend/routes.py`。
- 按需未展开：LLM runtime、Mermaid renderer、workflow prompts。本切片只同步 artifact 协作元数据，不改变模型调用或产出契约。

能力包聚合：
| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 批注/章节锁服务端同步 | Artifact 协作体验深化、批注/章节锁服务端 run snapshot 同步、历史会话恢复 | 用户添加批注/锁定章节 -> 保存到当前 run -> 重新打开历史会话 -> 批注/锁仍存在 | 只改前端恢复或只加后端表都无法形成用户可见闭环；必须覆盖持久化、API、snapshot、store 恢复 | 后端 pytest、前端 service/store Vitest |
| 批注回复/解决状态 | 批注协作深化 | 用户对批注回复或标记解决 | 需要更复杂 UI 和状态模型，适合作为同步后的增量 | 下一轮候选 |
| 精确正文选区锚点 | 批注锚定深化 | 用户选中文本创建批注并随正文变化定位 | 涉及 selection、锚点漂移和 diff 映射，本轮过大 | 下一轮候选 |

候选 gap：
| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 批注/章节锁服务端同步 | Todo P1.7 | run snapshot 能保存和恢复 artifact comments / section locks | 前端本地状态可用，但 restoreRunSnapshot 会清空 | 历史会话恢复和跨刷新协作断裂 | 高 | 中，需前后端契约 | 高 | 本轮 |
| 批注回复/解决状态 | Todo P1.7 剩余 | 批注可跟进处理状态 | 只能新增/删除 | 协作闭环较弱 | 中 | 中 | 高 | 后续 |
| 精确正文选区锚点 | Todo P1.7 剩余 | 批注绑定选区而非手动 excerpt | 只能记录 excerpt | 定位不够精确 | 中 | 中高 | 中 | 后续 |

排序结论：
1. 选择批注/章节锁服务端同步，因为它补齐现有 MVP 的最大断点：历史会话恢复后协作状态丢失。
2. 批注回复/解决状态暂不选，因为需要先有服务端状态基础。
3. 精确正文选区锚点暂不选，因为其复杂度高于当前同步闭环。

切片准入判断：
- 用户可感知动作链：在 ArtifactPane 添加批注或锁定章节 -> 系统同步到当前 run -> 从历史会话恢复 -> UI 继续显示批注和锁定。
- 相邻缺口合并：同时同步批注和章节锁，因为它们共享 stage-scoped artifact collaboration contract。
- Superpowers 成本合理性：跨前后端、涉及 snapshot 合约和值得回归测试。
- 过薄风险检查：不是单 endpoint；包含持久化、API、解析和状态恢复。
- 能力增量句：完成后，用户现在可以把产出物批注和章节锁随历史会话一起保存和恢复。

切片厚度门禁：
- 入口：ArtifactPane 批注和章节锁定面板。
- 动作：新增/删除批注，锁定/解锁章节。
- 处理：前端把当前协作元数据保存到 run；后端按 run/stage 持久化。
- 可见结果：历史会话 snapshot 返回 `artifactComments` 和 `artifactSectionLocks`，恢复后 UI 可见。
- 状态承接：协作状态与 run snapshot 绑定，不污染其他 workflow 或 stage。
- 失败反馈：service 对 malformed response 显式失败；无 currentRunId 时保持本地能力。
- 证据：pytest 和 Vitest 覆盖保存、snapshot、解析和恢复。
- 结论：通过。

## 用户故事

作为正在人工校准产出物的用户，当我给当前文档加批注或锁定已确认章节后，我希望这些协作状态跟随当前历史会话保存。之后我重新打开同一个 run 时，批注和锁仍然可见，从而不会误以为之前的校准约束已经丢失。

## 验收条件

1. Given 一个持久化 run，When 保存批注和章节锁，Then `get_run_snapshot` 返回 `artifactComments` 与 `artifactSectionLocks`。
2. Given snapshot 包含批注和章节锁，When 前端 `fetchRunSnapshot` 解析，Then 返回 typed `artifactComments` / `artifactSectionLocks`。
3. Given snapshot 包含当前 workflow 的协作元数据，When store 恢复 run snapshot，Then 对应 stage 的批注和锁可通过 getter 读出。
4. Given snapshot 中有不属于当前 workflow 的 stage，When store 恢复，Then 该协作元数据被过滤。

## 文件范围

- 修改：`tools/new-agents/backend/models.py`
- 修改：`tools/new-agents/backend/run_persistence.py`
- 修改：`tools/new-agents/backend/routes.py`
- 修改：`tools/new-agents/backend/tests/test_run_persistence.py`
- 修改：`tools/new-agents/backend/tests/test_agent_endpoint.py`
- 修改：`tools/new-agents/frontend/src/core/types.ts`
- 修改：`tools/new-agents/frontend/src/services/runSnapshotService.ts`
- 修改：`tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts`
- 修改：`tools/new-agents/frontend/src/store.ts`
- 修改：`tools/new-agents/frontend/src/__tests__/store.test.ts`
- 修改：`docs/todos/new-agents-ux-professionalization.md`

## 非目标

- 不实现批注回复、解决状态或权限。
- 不实现正文选区锚点漂移。
- 不改变模型上下文构造，不把批注和锁自动注入 LLM prompt。
- 不新增 Lisa/Alex 或 workflow-specific runtime 分支。
