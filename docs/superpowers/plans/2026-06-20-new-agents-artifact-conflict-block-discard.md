# New Agents Artifact Conflict Block Discard Plan

## Steps

1. 写 RED 测试：连续两行草稿新增内容显示 `丢弃变更块` 操作，点击后一次移除两行并记录块级轨迹。
2. 从 `conflictDraftDiff` 派生连续 added block。
3. 在 block 起始行渲染 `丢弃块` 操作。
4. 实现 `discardConflictDraftBlock`，批量移除草稿行并记录 `artifact_merge_block_discarded`。
5. 运行组件/store 测试，确认 RED 转 GREEN。
6. 运行 lint、build、diff check。
7. 更新 `docs/todos/new-agents-ux-professionalization.md` 进展记录。
