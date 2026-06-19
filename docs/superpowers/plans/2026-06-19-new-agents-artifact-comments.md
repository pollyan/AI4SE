# New Agents Artifact Comments Plan

## Steps

1. 在 store 测试中新增 RED 用例，验证批注新增、按阶段过滤、删除和清理。
2. 在 ArtifactPane 测试中新增 RED 用例，验证用户通过工具栏批注面板新增和删除批注。
3. 扩展 `core/types.ts` / store 类型与 sanitize/persist 逻辑，增加 artifact comments 状态和 actions。
4. 在 ArtifactPane 工具栏和面板中实现批注入口、输入、列表和删除。
5. 运行 store 与 ArtifactPane 测试、TypeScript 检查、构建、diff 检查。
6. 更新 `docs/todos/new-agents-ux-professionalization.md` 进展记录。
