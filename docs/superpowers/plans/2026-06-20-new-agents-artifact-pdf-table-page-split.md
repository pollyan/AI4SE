# New Agents Artifact PDF Table Page Split Plan

## Steps

1. 写 RED 测试：长 `ai4se-visual` 表格导出为 2 页 PDF 时，PDF 中至少有 2 个表格矩形绘制操作。
2. 调整表格绘制函数，用表格行范围和当前页行范围求交集。
3. 对每页可见表格片段绘制外框、列线和行线。
4. 运行目标组件测试，确认 RED 转 GREEN。
5. 运行完整 `ArtifactPane` 测试、lint、build、diff check。
6. 更新 `docs/todos/new-agents-ux-professionalization.md` 进展记录。
