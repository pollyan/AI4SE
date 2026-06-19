# New Agents Artifact 冲突非重叠插入自动合并计划

## 范围

补齐 Artifact 保存冲突中的安全自动合并基础能力：当服务端和用户草稿都只是相对旧版本插入内容时，允许用户一键合并双方补充。

## 步骤

1. 补失败测试：
   - 旧版本包含标题、背景、共同内容。
   - 服务端在背景后和文末各插入一行。
   - 用户草稿在背景后插入另一行。
   - 冲突后点击 `自动合并非重叠变更`。
   - 断言编辑草稿同时包含服务端和用户插入，并写入审计事件。
2. 实现安全插入段检测：
   - 旧版本行必须按顺序存在于服务端版本和草稿。
   - 不满足时返回 `null`，不显示自动合并按钮。
3. 实现合并：
   - 每个 gap 先保留服务端插入，再追加草稿独有插入。
   - 保留旧版本行顺序。
4. 接入 UI：
   - 只在 `autoMergedConflictContent` 存在时显示按钮。
   - 点击后更新 `editDraft` 并写入 `artifact_auto_merge_applied`。
5. 更新文档：
   - spec / plan。
   - `docs/todos/new-agents-ux-professionalization.md` 完成记录。
   - `docs/strategy/goal-mode-playbook.md` 记录 sub-agent worktree 流程。
6. 验证：
   - 聚焦测试先失败后通过。
   - 运行 ArtifactPane 与 store 相关测试。
   - 运行 frontend lint/build 与 `git diff --check`。
   - 提交并 push。
