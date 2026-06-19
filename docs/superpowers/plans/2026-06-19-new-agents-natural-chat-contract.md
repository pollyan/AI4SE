# New Agents 左侧自然对话契约计划

## CGA 结论

ChatPane 已支持 Markdown 渲染和结构化失败卡片，问题不在于前端不会显示 Markdown，而在于模型侧 contract 仍带有固定栏目倾向。先调整后端契约，比引入 chat schema 更符合用户要求。

## 执行步骤

1. 新增失败测试，锁定自然顾问式 chat 契约。
2. 修改 `build_artifact_contract_prompt` 的 chat 约束。
3. 运行后端 contract 测试、ChatPane 测试、构建和 diff 检查。
4. 更新 todo 进展。
