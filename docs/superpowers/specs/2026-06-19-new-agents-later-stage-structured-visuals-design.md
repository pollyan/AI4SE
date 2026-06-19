# New Agents 后续阶段结构化可视化契约设计

## 背景

首阶段已经建立专业可视化契约基线，但用户明确要求可视化增强不只覆盖首阶段。当前后续阶段仍偏向 Mermaid，部分业务视图更适合稳定结构化协议，以降低语法失败概率并提升专业可读性。

## 用户价值

- 用户在关键后续阶段能看到风险、行动、旅程、覆盖关系等业务视图，而不是只读长文档。
- 高价值矩阵和看板走 `ai4se-visual` 共享协议，减少模型自由生成 Mermaid 的失败面。
- 专业方法论固化到 artifact contract 和 prompt，避免只靠模型临场发挥。

## 范围

本切片覆盖四个后续阶段：

- `TEST_DESIGN/STRATEGY`：新增 `risk-board`，表达风险、FMEA 因子、RPN、缓解策略和覆盖建议。
- `INCIDENT_REVIEW/IMPROVEMENT`：新增 `action-board`，表达 SMART 改进行动、责任角色、期限、状态和验证方式。
- `VALUE_DISCOVERY/JOURNEY`：新增 `journey-map`，表达旅程阶段、任务、触点、情绪、痛点和机会。
- `TEST_DESIGN/DELIVERY`：新增 `coverage-map`，表达需求、风险、测试点、用例和验收覆盖状态。

## 非目标

- 不新增 Lisa/Alex 专属渲染分支。
- 不引入复杂自定义 HTML 或 workflow-specific 前端组件。
- 不移除已存在且有价值的 Mermaid 图。

## 验收

- 后端契约声明上述四个阶段的结构化可视化类型。
- 契约 prompt 包含对应 JSON schema 要求。
- 前端共享 `StructuredVisual` 能解析并渲染新增类型。
- 对应 prompt 模板包含 fenced `ai4se-visual` 示例。
- 相关后端、前端测试、构建和 `git diff --check` 通过。
