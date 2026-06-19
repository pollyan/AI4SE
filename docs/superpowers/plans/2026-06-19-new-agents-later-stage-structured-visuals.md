# New Agents 后续阶段结构化可视化契约计划

## CGA 结论

当前首阶段已有可视化契约，但后续阶段仍存在两个缺口：

- 专业关键判断多以 Markdown 表格或 Mermaid 表达，稳定性和可扫描性不足。
- `ai4se-visual` 只支持 `traceability-matrix` 与 `score-matrix`，无法覆盖风险、行动、旅程、覆盖等常见专业视图。

## 执行步骤

1. 写失败测试，锁定四个新增结构化可视化类型和阶段契约。
2. 扩展共享 `structuredVisuals` parser 与 `StructuredVisual` 默认标题。
3. 扩展后端 artifact contract 与 schema prompt。
4. 在四个阶段 prompt/template 中加入 fenced `ai4se-visual` 示例。
5. 运行针对性后端/前端测试、构建、diff 检查，并更新 todo 进展。

## 验证命令

- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `npm run test -- --run src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx`
- `npm run build`
- `git diff --check`
