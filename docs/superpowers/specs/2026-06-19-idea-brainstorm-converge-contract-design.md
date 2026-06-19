# IDEA_BRAINSTORM CONVERGE 评分口径契约收紧设计

## 背景

`docs/plans/2026-06-19-new-agents-artifact-audit.md` 指出 `IDEA_BRAINSTORM/CONVERGE` 有 ICE 评估表，但后端 contract 没有机械要求评分口径、淘汰理由和推荐方案。这样创意收敛可能只展示分数和排名，缺少可复核的决策依据。

## 用户故事

作为创意工作坊参与者，当 Alex 生成《收敛聚焦》产物时，我希望每个创意的 Impact、Confidence、Ease 评分都带有口径说明，并明确淘汰理由、推荐方案和下一步验证，从而可以解释为什么保留或放弃某个创意。

## 范围

进入本轮：

- 收紧后端 `IDEA_BRAINSTORM/CONVERGE` artifact contract。
- 更新 `CONVERGE_PROMPT` 和 `CONVERGE_TEMPLATE`，让前端 prompt/template 与后端 contract 同步。
- 增加后端契约测试，验证缺少新增字段会被拒绝。
- 更新 todo 和审计记录。

不进入本轮：

- 不修改 `CONCEPT`。
- 不新增独立字段级 parser，只使用现有 heading/substring contract 机制。
- 不调用真实模型。
- 不修改 UI。

## 验收条件

1. `IDEA_BRAINSTORM/CONVERGE` artifact 缺少评分口径、淘汰理由、推荐方案或下一步验证字段时会被 `validate_agent_turn(...)` 拒绝。
2. `build_artifact_contract_prompt("IDEA_BRAINSTORM", "CONVERGE")` 包含新增字段要求。
3. `CONVERGE_TEMPLATE` 的 ICE 表包含新增字段。
4. 聚焦后端契约测试通过。

## 验证计划

- 先写失败契约测试。
- 更新 contract 和前端模板。
- 运行 `tools/new-agents/backend/tests/test_agent_contracts.py` 聚焦测试。
- 运行 `git diff --check`。
