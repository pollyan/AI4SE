# DeepSeek V4 格式化输出完成态收口 Plan

> 日期: 2026-06-23
> 对应 spec: `docs/superpowers/specs/2026-06-23-deepseek-v4-completion-closure-design.md`

## Milestone

完成 DeepSeek V4 格式化输出需求的“验证、归档、索引一致性”闭环，让目标模式后续轮次不再把已完成的 DeepSeek 结构化产物数据改造当作活动实现缺口。

## 实施步骤

1. 确认隔离 worktree 干净，保护主工作区已有未提交改动。
2. 新增 `tests/test_refactor_todo_index.py`，用 pytest 验收 `docs/todos/refactor/README.md` 的当前入口必须覆盖所有活动候选文件。
3. 先运行新增测试，确认当前状态 RED: README 写“暂无”，但目录内仍有活动候选。
4. 将 DeepSeek V4 结构化产物数据 todo 归档到 `docs/todos/archive/`，更新状态和完成态验收记录。
5. 更新 `docs/todos/refactor/README.md`，只保留仍活动的 enhancement diagnostic 入口，并加入 DeepSeek 归档链接。
6. 重新运行新增测试，确认 GREEN。
7. 运行 DeepSeek 完成态相关最小但覆盖共享 runtime/SSE/API/artifact/persistence 的验证:
   - `.venv/bin/python -m pytest tests/test_refactor_todo_index.py -q`
   - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_real_smoke.py -q`
   - `cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/buildSystemPrompt.test.ts`
   - `cd tools/new-agents/frontend && npm run lint`
   - `git diff --check`
8. 清理临时依赖链接或生成物，检查 git status。
9. 提交聚焦 commit。

## 风险与边界

- 本轮只做完成态收口，不改变 DeepSeek 运行时实现。
- 真实 DeepSeek smoke 默认可能因缺少凭证而 skip；这符合现有门禁设计，归档记录需说明。
- 如果前端 worktree 没有 `node_modules`，只临时复用主工作区已有依赖目录，提交前移除该链接。
