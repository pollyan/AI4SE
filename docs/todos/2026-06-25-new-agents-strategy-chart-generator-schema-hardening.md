# New Agents 策略图表生成器与 schema 强化

- 状态：已完成
- 日期：2026-06-25
- 来源：用户反馈，TEST_DESIGN / STRATEGY 阶段经常在 Mermaid 图或结构化产物更新时失败
- 优先级：P0

## 背景

用户确认希望把 STRATEGY 阶段的 Mermaid / 图表部分从“模型直接写格式”进一步收敛为“模型只填业务结构化数据，后端确定性生成图表骨架”。当前代码已经使用 `artifact_data` 渲染策略蓝图，但仍要求模型输出 `rpn` 这种可由 `severity * occurrence * detection` 推导的字段，并且 Mermaid 标签转义对换行、反斜杠等输入缺少明确测试。

## 目标

在 `tools/new-agents` 共享 Agent Runtime 内完成策略阶段图表稳定性强化：

- 模型不再需要必填 RPN，后端根据 S/O/D 确定性计算。
- 如果模型显式给出错误 RPN，后端仍然显式失败，不做静默兼容。
- Mermaid `quadrantChart` 和 `block-beta` 的骨架继续由后端生成，并对特殊标签做规范化。
- `ai4se-visual risk-board` 继续由后端固定结构生成。
- 更新提示词、测试和目标模式记录，避免把方案变成 Lisa 专用 runtime 或独立渲染管线。

## 验收口径

- STRATEGY `artifact_data.risks[]` 缺少 `rpn` 时可以生成完整策略蓝图。
- 生成的风险表、risk-board 和 Mermaid 图中的 RPN 均来自后端计算。
- STRATEGY `artifact_data.risks[]` 显式给出错误 `rpn` 时仍触发 Pydantic 校验失败。
- Mermaid 标签中的双引号、反斜杠和换行不会破坏代码块结构。
- 聚焦后端测试覆盖 runtime instruction、最终渲染、流式部分渲染和契约校验。

## 本轮记录

- 设计与执行要点：已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。

## 完成记录

- 已将 STRATEGY `risks[].rpn` 改为可选输入，后端根据 S/O/D 派生。
- 已保留显式错误 RPN 的 ValidationError。
- 已规范化 Mermaid 标签中的空白、反斜杠和双引号。
- 已更新 STRATEGY structured output instruction，模型不再需要输出 Mermaid、risk-board 或 RPN。
- 已补充 renderer/runtime/contract 相关测试和全量验证记录。
