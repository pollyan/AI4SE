# New Agents 测试策略产出物结构化流式契约计划

日期：2026-06-25

关联 spec：`docs/superpowers/specs/2026-06-25-new-agents-test-strategy-artifact-streaming-contract-design.md`

## 用户故事

作为测试设计工作流使用者，我在 STRATEGY 阶段生成测试策略蓝图时，希望右侧产出物能按草稿逐步显示并最终稳定成正式文档，且模型只需遵循后端结构化 `artifact_data` 契约，不再被通用 Markdown 指令干扰。

## 实施步骤

1. 补前端提示词测试
   - 在 `buildSystemPrompt.test.ts` 中断言 STRATEGY 提示包含 `artifact_data` 优先说明。
   - 断言提示不再包含旧的“必须提供完整、全部的 Markdown 文档内容”强制口径。

2. 补前端流式解析测试
   - 在 `llm.test.ts` 中为 TEST_DESIGN/STRATEGY 添加 `run_started -> agent_delta -> agent_turn` 场景。
   - 断言 delta 草稿 artifact 先更新右侧产物，最终帧替换为完整策略蓝图。

3. 收敛提示词和契约说明
   - 修改 `buildSystemPrompt.ts`，把“完整 Markdown”改为“完整产出物数据”，并声明 `artifact_data` 契约优先。
   - 修改 `agent_contracts.py`，明确 Markdown 契约只适用于 `artifact_update.markdown`，运行时 `artifact_data` 指令优先。
   - 必要时调整 `test_design/strategy.ts`，避免阶段提示要求模型手写 Mermaid/risk-board，而是要求提供结构化渲染所需业务数据。

4. 归档 todo
   - 将活跃 todo 移入 `docs/todos/archive/` 并补完成记录。
   - 更新 `docs/todos/refactor/README.md` 当前入口和已归档列表。

## 验证

- `cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts src/core/__tests__/llm.test.ts`
- `cd tools/new-agents/backend && ../../../.venv/bin/python -m pytest tests/test_agent_contracts.py tests/test_agent_runtime.py -q`
- `git diff --check`
- `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all`
