# New Agents Artifact 历史 Diff 逐行审阅设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`。
- 当前工作区已有大量目标模式累计改动；本切片继续在当前工作区推进，限定写入 ArtifactPane、对应测试、todo/spec/plan。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 历史 diff 逐行审阅 | Artifact 协作体验里的“逐行接受 / 拒绝变更”；冲突 diff 已有 MVP，但普通历史 diff 仍只能整版恢复 | 打开历史版本 -> 切换差异 -> 对历史缺失行恢复、对当前新增行丢弃 -> 当前 artifact 更新并写入 history | 只显示按钮没有价值，必须覆盖当前产物更新、stage artifact 同步和历史备份 | ArtifactPane 组件测试 |
| 完整三方 merge | 删除行/修改行语义合并、上下文插入、相邻块合并 | 任意历史版本 -> 按块接受/拒绝 -> 合并为最终文档 | 需要更复杂 diff 模型，本轮过大 | 独立合并算法测试 |
| 服务端审阅轨迹 | 行级决策持久化到服务端 artifact versions 或 audit log | 多设备恢复行级审阅结果 | 需要后端契约，超出前端 MVP | API/集成测试 |

排序结论：
1. 选择“历史 diff 逐行审阅”，因为它补齐了用户在普通历史版本中局部恢复/丢弃的关键协作动作链。
2. 完整三方 merge 和服务端审阅轨迹暂缓，避免本轮变成通用文档合并系统。

切片厚度门禁：
- 入口：ArtifactPane `历史版本` -> `差异`。
- 动作：用户点击 `恢复此行` 或 `丢弃当前行`。
- 处理：系统生成新的当前 artifact 内容，并在修改前把当前版本写入 `artifactHistory`。
- 可见结果：diff 立即更新；当前 artifact 和当前 stage artifact 同步变化。
- 状态承接：用户仍可继续使用历史版本、恢复整版或后续手工编辑。
- 失败反馈：仅对非空且可定位行显示操作；无法定位时不改变内容。
- 证据：组件测试覆盖恢复历史行、丢弃当前行、history 备份和 stage artifact 同步。

## 用户故事

作为正在审阅历史版本的用户，我可以在差异视图里只恢复历史版本中的某一行，或者丢弃当前版本中某一行，而不用整版回滚，从而更安全地校准专业产出物。

## 验收条件

1. Given 当前产物和历史版本存在差异
   When 用户打开历史差异视图
   Then 历史版本中被移除的非空行显示 `恢复此行`，当前版本新增的非空行显示 `丢弃当前行`。

2. Given 用户点击 `恢复此行`
   Then 当前 artifact 包含该历史行，当前 stage artifact 同步更新，并写入修改前历史备份。

3. Given 用户点击 `丢弃当前行`
   Then 当前 artifact 删除该当前行，当前 stage artifact 同步更新，并写入修改前历史备份。

## 非目标

- 不实现完整三方 merge。
- 不实现块级接受/拒绝。
- 不新增服务端 API。
- 不改变现有整版恢复行为。
