# New Agents Mermaid 可视化契约设计

## 背景

`docs/todos/new-agents-evolution.md` P0 #3 要求建立产出物可视化增强规范。当前前端已有共享 Markdown/Mermaid 渲染、Mermaid 修复服务和部分 Mermaid 语法测试，LLM judge 也已有可视化维度。但后端 artifact contract 只检查标题和正文字段，无法拒绝关键阶段漏掉 Mermaid 图的产物。

现有标题校验会剥离 fenced code block，避免模型把标题藏在代码块里伪造。因此 Mermaid 不能通过 `REQUIRED_ARTIFACT_HEADINGS` 简单追加 ` ```mermaid ` 来校验，必须建立独立的可视化 contract。

## 用户故事

作为 New Agents 使用者，当 Lisa 或 Alex 生成关键工作流产物时，我希望每个核心 workflow 至少有一个阶段稳定输出适合当前分析任务的 Mermaid 图，从而能通过风险矩阵、时间线、用户旅程或评分矩阵快速理解重点。

## 范围

进入本轮：

- 新增后端 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS`，按 workflow/stage 定义必需 Mermaid 图类型。
- 在 artifact contract validation 中独立解析 fenced Mermaid code block。
- 更新 contract prompt，让模型知道当前阶段必须包含哪些 Mermaid 图。
- 增加后端契约测试，覆盖缺图拒绝和每个在线 workflow 至少一个可视化契约。
- 更新 todo 进展记录。

不进入本轮：

- 不新增非 Mermaid 结构化可视化协议。
- 不重写前端渲染管线。
- 不改 Mermaid repair 服务。
- 不调用真实模型。

## 首轮覆盖

- `TEST_DESIGN/STRATEGY`: `quadrantChart`、`block-beta`
- `REQ_REVIEW/REPORT`: `pie`
- `INCIDENT_REVIEW/TIMELINE`: `timeline`
- `INCIDENT_REVIEW/ROOT_CAUSE`: `mindmap`
- `INCIDENT_REVIEW/IMPROVEMENT`: `pie`
- `IDEA_BRAINSTORM/CONVERGE`: `quadrantChart`
- `VALUE_DISCOVERY/JOURNEY`: `journey`

## 验收条件

1. 必需可视化阶段缺少 Mermaid code block 或缺少指定图类型时会被 `validate_agent_turn(...)` 拒绝。
2. 每个在线 workflow 至少有一个 stage 出现在 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS`。
3. `build_artifact_contract_prompt(...)` 会列出当前阶段必需 Mermaid 图类型。
4. 后端契约测试和前端 Mermaid 相关测试通过。

## 验证计划

- 先写失败契约测试。
- 增加 Mermaid contract 数据结构和校验函数。
- 更新 prompt 生成。
- 运行后端契约测试、前端 Mermaid 测试和 diff 检查。
