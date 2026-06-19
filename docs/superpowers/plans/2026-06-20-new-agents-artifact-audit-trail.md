# New Agents Artifact Audit Trail Plan

## Steps

1. 写 RED 测试：
   - 后端：artifact 保存和 collaboration 更新后 snapshot 返回活动事件。
   - 前端 service/store：解析并恢复 `artifactAuditEvents`。
   - ArtifactPane：历史面板展示当前阶段活动轨迹。
2. 扩展后端模型、旧表 schema upgrade、run persistence 事件记录与 snapshot 输出。
3. 扩展前端类型、snapshot parser、store sanitize/restore。
4. 在 ArtifactPane 历史面板加入“活动轨迹”区块，不新增顶栏按钮。
5. 运行目标测试、lint、build、diff check。
6. 更新 `docs/todos/new-agents-ux-professionalization.md` 进展记录。
