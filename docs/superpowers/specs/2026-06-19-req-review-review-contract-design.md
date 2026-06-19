# REQ_REVIEW REVIEW 问题清单契约收紧设计

## 背景

`docs/plans/2026-06-19-new-agents-artifact-audit.md` 指出 `REQ_REVIEW/REVIEW` 是当前最薄的 artifact contract：后端只要求 `# 需求评审问题清单`、`## 评审概要` 和 `## 问题统计`，但没有机械要求问题清单表格包含可执行字段。这样模型可能输出标题完整但缺少具体问题字段的空洞评审清单。

## 用户故事

作为需求评审调用方，当 Lisa 生成《需求评审问题清单》时，我希望每个问题至少具备问题描述、优先级、所属需求章节、影响范围、证据/依据、建议和责任方/确认人，从而让产品经理或需求负责人可以直接确认和跟进。

## 范围

进入本轮：

- 收紧后端 `REQ_REVIEW/REVIEW` artifact contract。
- 更新 `REVIEW_PROMPT` 和 `REVIEW_TEMPLATE`，让前端 prompt/template 与后端 contract 同步。
- 增加后端契约测试，验证缺少新增字段会被拒绝。
- 更新 todo 和审计记录。

不进入本轮：

- 不修改 `REQ_REVIEW/REPORT`。
- 不新增独立字段级 parser，只使用现有 heading/substring contract 机制。
- 不调用真实模型。
- 不修改 UI。

## 验收条件

1. `REQ_REVIEW/REVIEW` artifact 缺少影响范围、证据/依据或责任方/确认人字段时会被 `validate_agent_turn(...)` 拒绝。
2. `build_artifact_contract_prompt("REQ_REVIEW", "REVIEW")` 包含新增字段要求。
3. `REVIEW_TEMPLATE` 的问题表包含新增字段。
4. 聚焦后端契约测试通过。

## 验证计划

- 先写失败契约测试。
- 更新 contract 和前端模板。
- 运行 `tools/new-agents/backend/tests/test_agent_contracts.py` 聚焦测试。
- 运行 `git diff --check`。
