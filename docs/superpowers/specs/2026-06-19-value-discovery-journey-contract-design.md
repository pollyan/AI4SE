# VALUE_DISCOVERY JOURNEY 用户旅程契约收紧设计

## 背景

`docs/plans/2026-06-19-new-agents-artifact-audit.md` 指出 `VALUE_DISCOVERY/JOURNEY` 当前只要求旅程地图、关键阶段、痛点排序和机会点标题，但没有机械要求旅程阶段的结构化字段。这样模型可能输出标题完整却无法判断用户任务、触点、情绪低谷、痛点证据和机会指标。

## 用户故事

作为价值发现使用者，当 Alex 生成《用户旅程分析》时，我希望每个关键阶段至少包含旅程阶段、触点渠道、用户任务、情绪评分、关键痛点、现有方案不足、机会假设和成功指标，从而能判断产品切入点是否真实、具体、可验证。

## 范围

进入本轮：

- 收紧后端 `VALUE_DISCOVERY/JOURNEY` artifact contract。
- 更新 `JOURNEY_PROMPT` 和 `JOURNEY_TEMPLATE`，让前端 prompt/template 与后端 contract 同步。
- 增加后端契约测试，验证缺少新增字段会被拒绝。
- 更新 todo 和审计记录。

不进入本轮：

- 不修改 `VALUE_DISCOVERY/BLUEPRINT`。
- 不新增独立字段级 parser，只使用现有 heading/substring contract 机制。
- 不调用真实模型。
- 不修改 UI。

## 验收条件

1. `VALUE_DISCOVERY/JOURNEY` artifact 缺少用户任务、情绪评分、机会假设或成功指标字段时会被 `validate_agent_turn(...)` 拒绝。
2. `build_artifact_contract_prompt("VALUE_DISCOVERY", "JOURNEY")` 包含新增字段要求。
3. `JOURNEY_TEMPLATE` 的关键阶段表包含新增字段。
4. 聚焦后端契约测试通过。

## 验证计划

- 先写失败契约测试。
- 更新 contract 和前端模板。
- 运行 `tools/new-agents/backend/tests/test_agent_contracts.py` 聚焦测试。
- 运行 `git diff --check`。
