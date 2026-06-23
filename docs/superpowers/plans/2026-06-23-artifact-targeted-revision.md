# Artifact 定向修订闭环实施计划

## Milestone

完成 Artifact 定向修订闭环：用户从现有 Artifact 章节侧栏选择未锁定章节重生成，系统复用共享 typed SSE runtime 生成候选 artifact，但只合并目标章节，保留锁定章节和非目标章节，并写入现有 artifact 历史。

## TDD 步骤

1. 新增 shared Markdown section helper 测试。
   - 覆盖解析标题、生成稳定 anchor、只替换目标章节。
   - 覆盖锁定章节保护。
   - 覆盖锁定目标章节和模型返回缺目标章节的失败。

2. 新增 `useChatService` 定向修订测试。
   - 成功路径：mock `generateResponseStream` 返回完整 artifact，其中目标章节更新、锁定章节被模型误改；期望最终只更新目标章节并恢复锁定章节。
   - 失败路径：mock 返回 artifact 缺失目标章节；期望 artifact、stage artifact、history 保持不变，并出现错误消息。

3. 新增 `ArtifactPane` UI 测试。
   - 展开章节锁定侧栏，未锁定章节展示并触发“重生成章节”。
   - 锁定章节的重生成动作禁用，不触发 shared stream。

4. 实现最小代码。
   - 新建 `core/artifactSections.ts`，承载 section 解析、锁匹配、锁定保护和目标章节合并。
   - 修改 `chatService.ts`，增加 `handleRegenerateArtifactSection()`，并为 `handleSend()` 增加内部定向合并选项。
   - 修改 `ArtifactPane.tsx`，复用 shared section helper，并在章节侧栏接入重生成动作。
   - 保持现有 store、runtime、SSE、manifest 和 renderer 不变。

5. 清理和文档。
   - 删除重复 section parser。
   - 更新 `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 和 README。

6. 验证。
   - 运行相关 frontend 单测。
   - 运行 `npm run build`。
   - 运行 `git diff --check`。
   - 验证通过后提交聚焦 commit。

## 风险与控制

- Markdown heading 解析不支持深层 `####`：沿用当前系统只管理 H1-H3 的约束，避免扩大行为面。
- 模型输出可能整体改写：客户端只提取目标章节，丢弃非目标章节变化。
- anchor 在重复标题下依赖出现顺序：沿用当前章节锁定的 occurrence anchor 逻辑，测试覆盖重复标题基础行为。
- 流式中间 artifact 可能多次到达：每次更新都基于运行开始时的原始 artifact 合并，避免中间候选污染非目标章节。
