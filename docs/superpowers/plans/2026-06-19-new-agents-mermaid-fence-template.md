# New Agents Mermaid Fence 模板可靠性计划

## CGA 结论

当前部分模板导入了 `FENCE` 常量，但在模板字符串中写成 `\${FENCE}`，运行时不会插值为三反引号。这会使 Artifact 中的 Mermaid 示例无法被 Markdown renderer 识别。

## 执行步骤

1. 在 Mermaid 测试中增加全量模板检查，先观察失败。
2. 将残留 `\${FENCE}` 修为 `${FENCE}`。
3. 运行 Mermaid 相关测试、前端构建、`git diff --check`。
4. 更新 todo 进展。
