# New Agents Artifact Section Locks Plan

## Steps

1. 在 store 测试中新增 RED 用例，验证章节锁新增、按阶段过滤、删除和清理。
2. 在 ArtifactPane 测试中新增 RED 用例，验证锁定章节后人工编辑修改该章节会被阻止，解锁后可保存。
3. 扩展 `core/types.ts` 与 store 状态，新增 artifact section locks 和持久化 sanitize。
4. 在 ArtifactPane 中实现 Markdown 章节提取、章节锁定面板和保存前校验。
5. 运行目标测试、TypeScript、构建和 diff 检查。
6. 更新 `docs/todos/new-agents-ux-professionalization.md`。
