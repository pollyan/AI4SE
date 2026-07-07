# New Agents Alex 用户故事结构化契约实施计划

## 用户故事

作为产品经理，当我让 Alex 把需求蓝图拆成用户故事时，我可以得到由结构化数据驱动的用户故事地图、故事卡片和 Ready / Not ready 清单，从而后续 AI Coding 需求包可以读取稳定的 story 数据，而不是反解析 Markdown。

## 写入边界

允许写入：

- `docs/superpowers/specs/2026-07-08-new-agents-user-story-structured-contract-design.md`
- `docs/superpowers/plans/2026-07-08-new-agents-user-story-structured-contract.md`
- `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`
- `docs/TESTING.md`
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/backend/agent_runtime.py`
- `tools/new-agents/backend/app.py`
- `tools/new-agents/backend/artifact_data_renderers.py`
- `tools/new-agents/backend/models.py`
- `tools/new-agents/backend/run_persistence.py`
- `tools/new-agents/backend/stream_services.py`
- `tools/new-agents/backend/tests/test_agent_runtime.py`
- `tools/new-agents/backend/tests/test_api.py`
- `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- `tools/new-agents/backend/tests/test_run_persistence.py`
- `tools/new-agents/backend/tests/test_stream_services.py`
- `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `tests/e2e/new_agents_browser/sse_mock.py`
- `tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py`

禁止触碰：

- 当前工作区已有的 BMad 删除、Intent Tester zip / junit、Lisa 场景文档、根 README / docs index 等无关脏改动。
- Lisa handoff 契约和测试资产专属路径，除非聚焦回归发现本轮破坏。

## TDD 顺序

1. RED：在 `test_artifact_data_renderers.py` 增加 `VALID_USER_STORY_*` fixture 和失败测试，覆盖：
   - final renderer 能从四阶段 `artifact_data` 渲染通过 contract 的 Markdown。
   - partial renderer 能在已闭合字段到达时输出正式递增章节。
   - 缺少来源需求、缺少验收标准、Ready 状态非法、重复 storyId、Not Ready 缺阻塞原因时校验失败。
2. RED：在 `test_agent_runtime.py` 增加 instruction / raw JSON streaming 测试，证明 `USER_STORY_BREAKDOWN` 使用 `artifact_data` 指令，final 前能产生 artifact delta，最终仍通过 contract。
3. RED：在 `test_stream_services.py`、`test_run_persistence.py` 和 `test_api.py` 增加结构化 payload 持久化、snapshot 恢复和旧表补列测试，证明后续 packet 不能依赖 Markdown 反解析。
4. RED：在 `test_workflow_contract_sync.py` 增加或调整矩阵，要求新增 workflow 阶段进入 artifact-data streaming 覆盖矩阵。
5. GREEN：在 `artifact_data_renderers.py` 增加 Pydantic 模型、validators、final renderer、partial renderer 和 dispatch。
6. GREEN：在 `agent_runtime.py` 接入四阶段 structured output instruction、support set 和 retry prompt 行为。
7. GREEN：在 `AgentTurnOutput -> stream_services -> AgentRunPersistence -> AgentArtifactVersion` 共享链路上传递可选 `artifact_data`，并保证 SSE 对前端仍不暴露该内部字段。
8. GREEN：更新 `sse_mock.py` 的用户故事拆解 mock payload 为 `artifact_data` 驱动或保留最终 Markdown 的同时补结构化字段验证用例；更新浏览器 E2E 断言结构化 renderer 产物仍包含业务垂直切片和 handoff 清单。
9. REFACTOR：清理重复表格渲染 helper，保持共享 renderer 风格，不引入 Alex 专属 runtime / API / store。
10. 文档记录：更新 todo 第 3 轮执行记录和 `docs/TESTING.md` 的 partial artifact streaming / artifactData 持久化覆盖矩阵。

## 预计验证

聚焦 RED/GREEN：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_user_story_breakdown_artifact_data_is_deterministic_and_contract_valid -q
```

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_user_story_breakdown_story_cards_reject_invalid_ready_story_quality -q
```

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_user_story_breakdown_artifact_data_before_final_output -q
```

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_stream_services.py::test_stream_agent_run_events_records_artifact_data_through_persistence_adapter tools/new-agents/backend/tests/test_run_persistence.py::test_record_artifact_version_persists_artifact_data_in_current_snapshot tools/new-agents/backend/tests/test_api.py::test_init_db_upgrades_existing_artifact_version_table_with_artifact_data -q
```

聚焦回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_api.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

浏览器级 mock：

```bash
.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py -q
```

New Agents 全量：

```bash
./scripts/test/test-local.sh new-agents
```

提交前全仓：

```bash
./scripts/test/test-local.sh all
```

如果默认 sandbox 因 MidScene 端口或 Playwright 权限失败，按 playbook 申请提权重跑并记录。

## CI 等价映射

| 远端 CI / 风险面 | 本地等价命令 |
| --- | --- |
| New Agents backend contract/runtime/persistence | `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_api.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q` |
| New Agents browser主路径 | `.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py -q` |
| New Agents package回归 | `./scripts/test/test-local.sh new-agents` |
| 全仓本地 CI 等价 | `./scripts/test/test-local.sh all` |

## 提交边界

本轮完成并通过验证后，按 playbook 创建一个聚焦 commit 并 push。只 stage 本轮允许写入文件；不 stage 当前工作区已有无关改动。
