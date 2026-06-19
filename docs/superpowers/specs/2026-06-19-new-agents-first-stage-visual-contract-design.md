# New Agents 首阶段可视化契约设计

## 背景

`docs/todos/new-agents-ux-professionalization.md` 要求每个在线 workflow 在所有适合阶段体现专业、有结构、可视化的产出质量，尤其是第一阶段要建立专业第一印象。

当前状态：

- `INCIDENT_REVIEW/TIMELINE` 已有 Mermaid timeline 契约。
- `IDEA_BRAINSTORM/DEFINE` 模板包含 Mermaid mindmap，但后端 contract 未强制。
- `TEST_DESIGN/CLARIFY` 模板描述“强制配合 Mermaid 流程图或时序图”，但后端 contract 未强制。
- `REQ_REVIEW/REVIEW` 缺少稳定可视化契约。
- `VALUE_DISCOVERY/ELEVATOR` 缺少稳定可视化契约。
- `ai4se-visual` 前端只支持 `traceability-matrix`，无法承载评分矩阵这类更稳定的业务可视化。

## 目标

- 所有在线 workflow 的首阶段都有至少一个 contract 级可视化要求。
- `TEST_DESIGN/CLARIFY` 强制包含 Mermaid `flowchart`。
- `IDEA_BRAINSTORM/DEFINE` 强制包含 Mermaid `mindmap`。
- `REQ_REVIEW/REVIEW` 和 `VALUE_DISCOVERY/ELEVATOR` 使用新增 `ai4se-visual` `score-matrix`，避免用复杂 Mermaid 表达评分矩阵。
- 前端共享 `StructuredVisual` 支持 `score-matrix`，仍以通用表格形式稳定渲染，不为 Lisa/Alex 或具体 workflow 分支。

## 非目标

- 不一次性完成所有后续阶段可视化审计。
- 不引入自定义 HTML 可视化。
- 不改 Agent Runtime、typed SSE 或工作流运行路径。
- 不替换已有 Mermaid repair 机制。

## 用户体验

用户进入任一 workflow 第一阶段后，右侧首份产出物都应包含可视化区域：

- 测试设计：系统边界与核心链路 flowchart。
- 需求评审：评审维度严重度/发现数量 score matrix。
- 故障复盘：事件 timeline。
- 创意头脑风暴：问题域 mindmap。
- 价值发现：价值主张评分/假设信心 score matrix。

这些要求由后端 contract 和前端 prompt/template 双向约束，减少模型自由发挥导致的缺失。

## 验收

- 后端测试证明所有在线 workflow 首阶段都有 Mermaid 或 structured visual contract。
- 后端 contract 能拒绝首阶段缺失对应可视化的 artifact。
- 前端 parser/component 能解析和渲染 `score-matrix`。
- 前端模板同步测试证明要求结构化 visual 的首阶段包含 `ai4se-visual` 示例。
- 相关 Python/TypeScript 测试通过。
