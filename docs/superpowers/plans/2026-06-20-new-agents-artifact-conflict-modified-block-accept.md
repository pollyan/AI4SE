# New Agents Artifact 冲突修改块采纳计划

## 范围

实现 Artifact 保存冲突 diff 中的相邻修改块采纳能力，让用户可以把一组草稿修改原位合并到服务端较新版本。

## 步骤

1. 补一个失败测试：
   - 服务端版本包含两行服务端修改和一行服务端额外补充。
   - 用户草稿在同一位置包含两行用户修改。
   - 期望点击 `采纳修改块` 后，草稿保留服务端额外补充，并用用户修改替换服务端修改块。
2. 实现修改块派生：
   - 复用 `conflictDraftDiff`。
   - 识别连续 `removed` 后跟连续 `added` 的块。
   - 生成可访问按钮标签。
3. 实现采纳行为：
   - 以 `conflictArtifact.content` 为基准。
   - 对首个匹配的服务端删除块做原位替换。
   - 更新 `editDraft`。
4. 写入审计事件：
   - 新增 `artifact_merge_block_modified_accepted`。
   - 历史面板继续复用现有活动轨迹展示。
5. 验证：
   - 聚焦测试先失败后通过。
   - 运行 ArtifactPane 和 store 相关测试。
   - 运行 frontend lint/build 与 `git diff --check`。
