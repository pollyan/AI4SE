# Lisa Test Assets Export Design

## Current State Gap Analysis

事实源快照：

- 已读取：`docs/todos/new-agents-evolution.md`、`tools/new-agents/frontend/src/core/prompts/test_design/cases.ts`、`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/run_persistence.py`、`tools/new-agents/backend/routes.py`、`tools/new-agents/backend/tests/test_agent_endpoint.py`。
- 按需未展开：intent-tester 主链路、完整测试管理 CRUD、前端资产管理 UI；本轮不接入外部测试执行系统。

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Lisa CASES artifact 导出结构化测试资产 | P1 #7 | 服务端可从已保存测试用例集导出可复用 test cases 和覆盖追溯 | CASES artifact 已有强字段 contract，但只是 Markdown | 无可复用测试资产 API，后续无法稳定接 intent-tester 或测试管理 | 打通报告到资产的第一步 | 中：需解析 Markdown 表格并显式失败 | service + endpoint 测试 | 本轮 |
| 测试点库/用例版本管理 | P1 #7 | 独立资产表、版本、覆盖追溯 | 只有 artifact versions | 需要新领域模型和 UI 流程 | 长期价值高 | 中高 | 多层测试 | 后续 |
| intent-tester 导出接入 | P1 #7 | 可把 Lisa 用例送入 intent-tester | intent-tester 已独立存在 | 需要跨工具契约 | 高 | 中高 | 集成测试 | 后续 |

排序结论：

1. 选择 CASES artifact 导出，因为当前 artifact contract 已强制字段齐全，解析导出是最小闭环。
2. 版本管理和 intent-tester 接入暂不选，等结构化资产输出稳定后再推进。

## Chosen Design

新增后端 `test_assets.py`，从 `get_run_snapshot(run_id)` 中读取 `TEST_DESIGN` workflow 的 `CASES` artifact，解析 Markdown 表格：

- `## 2. 用例清单` 下所有包含必填 CASES 字段的表格行解析为 `testCases`。
- `## 3. 测试点覆盖追溯` 下的表格解析为 `coverageTrace`。
- 返回 `runId`、`workflowId`、`sourceStageId`、`testCases`、`coverageTrace`。

新增只读端点 `GET /api/agent/runs/{runId}/test-assets`。无 run、非 TEST_DESIGN、缺少 CASES artifact、表格字段不完整时显式返回错误，不返回伪成功。

## Requirements

- 从标准 CASES Markdown 表格解析 ID、用例标题、优先级、测试维度、关联测试点、关联风险、前置条件、操作步骤、测试数据、预期结果。
- 覆盖追溯解析测试点、优先级、关联风险、覆盖用例、覆盖状态。
- 缺少 CASES artifact 时返回 diagnosable error。
- 非 TEST_DESIGN run 不导出 Lisa 测试资产。
- 不修改 typed SSE 主链路，不修改前端 UI，不接入 intent-tester。

## Verification

- `test_test_assets.py` 覆盖 service 解析成功、缺 artifact、非 TEST_DESIGN。
- `test_agent_endpoint.py` 覆盖 endpoint 成功和错误响应。
- 后端聚焦测试和全量测试通过。
