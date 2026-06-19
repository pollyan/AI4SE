# New Agents Artifact 受控人工修改计划

## CGA 结论

当前 ArtifactPane 具备只读预览、代码视图、历史 diff/恢复和导出。缺口是没有显式编辑入口，用户无法把人工校准结果纳入当前 artifact 和历史链路。

## 执行步骤

1. 先写 ArtifactPane 失败测试，覆盖保存人工修改和取消编辑。
2. 在 ArtifactPane 工具条加入编辑入口、编辑 textarea、保存/取消操作。
3. 保存时更新 `artifactContent`、当前 `stageArtifacts` 和 `artifactHistory`。
4. 运行 ArtifactPane/store 测试、构建和 diff 检查。
5. 更新 todo 中 Artifact 协作进展和剩余边界。
