# New Agents Artifact Conflict Block Accept Plan

## Steps

1. 写 RED 测试：连续两行草稿新增内容显示 `采纳变更块`，点击后服务端版本草稿包含整个 block 并记录块级轨迹。
2. 扩展块级活动记录函数，支持 `artifact_merge_block_accepted`。
3. 实现 `acceptConflictDraftBlock`，以服务端版本为基准追加 block 行。
4. 在 block 起始行渲染 `采纳块` 操作。
5. 运行组件/store 测试，确认 RED 转 GREEN。
6. 运行 lint、build、diff check。
7. 更新 `docs/todos/new-agents-ux-professionalization.md` 进展记录。
