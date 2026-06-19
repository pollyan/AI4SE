# TEST_DESIGN CASES 用例字段契约收紧设计

## 背景

`docs/plans/2026-06-19-new-agents-artifact-audit.md` 建议在 `REQ_REVIEW/REVIEW` 之后优先收紧 `TEST_DESIGN/CASES`。当前后端 contract 只要求《测试用例集》的三段标题：用例统计、用例清单、测试点覆盖追溯。前端模板虽有表格字段，但后端无法拒绝标题完整、字段缺失的空洞用例集。

## 用户故事

作为测试设计使用者，当 Lisa 生成测试用例集时，我希望每条用例至少包含用例 ID、标题、优先级、测试维度、关联测试点、关联风险、前置条件、操作步骤、测试数据和预期结果，从而可以直接进入评审、执行或导入测试管理系统。

## 范围

进入本轮：

- 收紧后端 `TEST_DESIGN/CASES` artifact contract。
- 更新 `CASES_PROMPT` 和 `CASES_TEMPLATE`，让前端 prompt/template 与后端 contract 同步。
- 增加后端契约测试，验证缺少新增字段会被拒绝。
- 更新 todo 和审计记录。

不进入本轮：

- 不修改 `TEST_DESIGN/DELIVERY` 汇总结构。
- 不新增独立字段级 parser，只使用现有 heading/substring contract 机制。
- 不调用真实模型。
- 不修改 UI。

## 验收条件

1. `TEST_DESIGN/CASES` artifact 缺少测试维度、关联测试点或测试数据字段时会被 `validate_agent_turn(...)` 拒绝。
2. `build_artifact_contract_prompt("TEST_DESIGN", "CASES")` 包含新增字段要求。
3. `CASES_TEMPLATE` 的用例表包含新增字段。
4. 聚焦后端契约测试通过。

## 验证计划

- 先写失败契约测试。
- 更新 contract 和前端模板。
- 运行 `tools/new-agents/backend/tests/test_agent_contracts.py` 聚焦测试。
- 运行 `git diff --check`。
