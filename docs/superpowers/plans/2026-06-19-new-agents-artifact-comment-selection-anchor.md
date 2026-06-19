# New Agents Artifact Comment Selection Anchor Plan

## Steps

1. 写 RED 测试：
   - ArtifactPane：选中预览区文本后新增批注，摘录使用选区文本。
   - Store/service：`anchorText` 能保存、恢复、同步，旧数据缺字段时兼容。
   - Backend：artifact collaboration API 和 snapshot 返回 `anchorText`。
2. 扩展 `ArtifactComment` 类型、store sanitize/add 逻辑和 `runSnapshotService` parser。
3. 扩展后端 `AgentArtifactComment` model、collaboration 读写和旧表 schema upgrade。
4. 在 ArtifactPane 预览容器捕获合法选区，并在新增批注时写入 `artifactExcerpt` / `anchorText`。
5. 运行目标测试、lint、build、diff check。
6. 更新 `docs/todos/new-agents-ux-professionalization.md` 进展记录。
