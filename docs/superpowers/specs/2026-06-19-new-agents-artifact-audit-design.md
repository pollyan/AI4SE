# New Agents Artifact 专业审计设计

## 背景

`docs/todos/new-agents-evolution.md` P0 #2 要求从专业测试人员和专业业务分析人员视角重新审视每个 workflow 的 artifact 是否合理、完整、可执行、可复用。当前仓库已有 5 个在线 workflow、前端 stage template 和后端 artifact heading contract，但缺少一份统一审计基线说明后续应优先升级哪些 prompt、contract、可视化和测试。

## 用户故事

作为目标模式执行者，当我准备升级 New Agents 工作流产出物时，我可以先阅读一份专业审计基线，知道每个在线 workflow 的目标、当前 contract 能力、主要差距和后续最小切片，从而避免凭直觉局部改 prompt。

## 范围

进入本轮：

- 新增一份 New Agents 在线 workflow artifact 专业审计文档。
- 覆盖 5 个在线 workflow：
  - `TEST_DESIGN`
  - `REQ_REVIEW`
  - `INCIDENT_REVIEW`
  - `IDEA_BRAINSTORM`
  - `VALUE_DISCOVERY`
- 对每个 workflow 记录专业目标、当前 contract 摘要、主要差距、推荐后续切片。
- 更新 `docs/todos/new-agents-evolution.md` P0 #2 进展记录。

不进入本轮：

- 不修改前端 prompt/template。
- 不修改后端 artifact contract。
- 不改运行时代码或 E2E 测试。
- 不做真实模型评测。

## 验收条件

1. 审计文档覆盖全部 5 个在线 workflow。
2. 每个 workflow 都有具体差距，而不是泛泛描述。
3. 审计文档明确后续候选切片，能被下一轮 CGA 直接引用。
4. 文档没有 `TODO`、`TBD` 或未解释占位。

## 验证计划

- 检查引用路径存在。
- 搜索文档占位符。
- 运行 `git diff --check`。
