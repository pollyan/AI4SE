# New Agents 阶段推进成熟度门禁计划

日期：2026-06-25

关联 spec：`docs/superpowers/specs/2026-06-25-new-agents-stage-readiness-gate-design.md`

## 用户故事

作为测试设计工作流使用者，我在需求澄清阶段仍有高优先级阻断问题待确认时，不希望系统建议或显示进入策略制定的 CTA，而是明确告诉我还需要确认哪些关键缺口。

## 实施步骤

1. 后端红测
   - 在 `test_stream_services.py` 中构造 CLARIFY artifact：P0 阻断待确认问题 + 模型返回 `stage_action=STRATEGY`。
   - 断言 `agent_delta` 和 `agent_turn` 输出都取消 `stage_action`，追加 `stage_readiness_blocked` warning，并在 chat 里说明不能进入下一阶段。

2. 前端红测
   - 在 `llm.test.ts` 中构造 `agent_turn`：chat 含进入下一阶段语义，`stage_action=null`，`warnings=["stage_readiness_blocked"]`。
   - 断言最终 chunk 的 `action` 为空。

3. 实现共享门禁
   - 新增后端门禁模块，集中定义 `STAGE_READINESS_BLOCKED_WARNING` 和 `apply_stage_readiness_gate()`。
   - 第一版只覆盖 `TEST_DESIGN/CLARIFY` 的 P0/P1 阻断待确认问题。
   - 在 `stream_services.stream_agent_run_events()` 发出 `AgentTurnOutput` 前应用门禁。

4. 前端 warning 兜底
   - 在 `llm.ts` 中识别 `stage_readiness_blocked`，阻止聊天语义推断 `NEXT_STAGE`。

5. 归档 todo
   - 将活跃 todo 移入 `docs/todos/archive/` 并补完成记录。
   - 更新 `docs/todos/refactor/README.md` 当前入口和已归档列表。

## 验证

- `cd tools/new-agents/backend && ../../../.venv/bin/python -m pytest tests/test_stream_services.py -q`
- `cd tools/new-agents/frontend && npm run test -- src/core/__tests__/llm.test.ts`
- `git diff --check -- <本故事相关路径>`
- `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all`；若当前沙箱阻塞本地端口或 Chromium 启动，记录阻塞原因并保留聚焦验证证据。
