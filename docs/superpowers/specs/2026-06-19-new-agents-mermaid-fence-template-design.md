# New Agents Mermaid Fence 模板可靠性设计

## 背景

部分 workflow prompt 模板使用 `\${FENCE}`，会在运行时输出字面量 `${FENCE}`，导致模型示例不是合法 Markdown fenced code block。这会提高 Mermaid 和结构化可视化失败概率。

## 范围

- 修复所有 `tools/new-agents/frontend/src/core/prompts/` 中残留的字面量 `\${FENCE}`。
- 增加全量模板测试，确保 `WORKFLOWS` 中暴露给运行时的模板不再包含 `${FENCE}` 字面量。

## 非目标

- 不调整 Mermaid 图语义和业务内容。
- 不新增新的可视化类型。

## 验收

- 全量模板测试能防止 `${FENCE}` 字面量再次进入 workflow template。
- 相关 Mermaid 示例测试通过。
- 前端构建通过。
