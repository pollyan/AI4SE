# INCIDENT_REVIEW IMPROVEMENT 行动项契约收紧设计

## 背景

`docs/plans/2026-06-19-new-agents-artifact-audit.md` 指出 `INCIDENT_REVIEW/IMPROVEMENT` 虽然有改进行动清单，但后端 contract 只校验章节标题，没有机械要求行动项包含负责人、期限、验证方式、状态和追踪机制。这样复盘报告可能看起来完整，却无法推动防复发措施落地。

## 用户故事

作为故障复盘负责人，当 Lisa 生成《故障复盘报告》终稿时，我希望每项改进行动都包含改进措施、类型、对应根因、负责人、完成期限、验证方式、验收标准、优先级、当前状态和追踪机制，从而可以直接分派、跟踪和复查。

## 范围

进入本轮：

- 收紧后端 `INCIDENT_REVIEW/IMPROVEMENT` artifact contract。
- 更新 `IMPROVEMENT_PROMPT` 和 `IMPROVEMENT_TEMPLATE`，让前端 prompt/template 与后端 contract 同步。
- 增加后端契约测试，验证缺少新增字段会被拒绝。
- 更新 todo 和审计记录。

不进入本轮：

- 不修改 `TIMELINE` 或 `ROOT_CAUSE`。
- 不新增独立字段级 parser，只使用现有 heading/substring contract 机制。
- 不调用真实模型。
- 不修改 UI。

## 验收条件

1. `INCIDENT_REVIEW/IMPROVEMENT` artifact 缺少验证方式、当前状态或追踪机制字段时会被 `validate_agent_turn(...)` 拒绝。
2. `build_artifact_contract_prompt("INCIDENT_REVIEW", "IMPROVEMENT")` 包含新增字段要求。
3. `IMPROVEMENT_TEMPLATE` 的行动清单包含新增字段。
4. 聚焦后端契约测试通过。

## 验证计划

- 先写失败契约测试。
- 更新 contract 和前端模板。
- 运行 `tools/new-agents/backend/tests/test_agent_contracts.py` 聚焦测试。
- 运行 `git diff --check`。
