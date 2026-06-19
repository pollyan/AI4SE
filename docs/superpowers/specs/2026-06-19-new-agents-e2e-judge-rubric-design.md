# New Agents E2E Judge Rubric 设计

## 背景

上一切片已经让浏览器 E2E runner 返回结构化 `WorkflowRunResult`。但 `llm_judge.py` 仍沿用旧的简单 verdict：`pass`、`score`、`issues`。这不足以支撑 `docs/todos/new-agents-evolution.md` P0 #1 中的目标：按 Lisa / Alex 专业角色、交互体验和可视化质量做分维度评估，并输出可追踪证据。

本轮在不调用真实模型的前提下，先把 judge prompt 和 JSON 解析边界升级为严格 verdict。

## 用户故事

作为目标模式执行者，当我启用 New Agents E2E LLM judge 时，我希望 judge 被明确要求按工作流角色输出分维度评分、问题证据和改进建议；如果 judge 返回缺字段或非法结构，测试应明确失败，而不是把不完整结果当成有效质量评估。

## 范围

进入本轮：

- 扩展 `JudgeResult`，支持：
  - `passed`
  - `score`
  - `dimension_scores`
  - `issues`
  - `evidence`
  - `recommendations`
- 新增严格 JSON verdict 解析函数。
- `build_judge_prompt(...)` 根据 workflow 名称选择 Lisa 或 Alex 专业 rubric，并追加通用交互体验和可视化 rubric。
- 增加确定性测试覆盖：
  - Lisa prompt 包含测试专家维度。
  - Alex prompt 包含业务分析师维度。
  - 合法 verdict 可解析。
  - 缺字段或非法分数会失败。
- 更新 todo 进展记录。

不进入本轮：

- 不调用真实 LLM。
- 不把 judge 结果持久化。
- 不调整浏览器 E2E 场景内容。
- 不修改产品 UI / 后端运行时代码。

## 验收条件

1. Lisa judge prompt 包含需求澄清、风险识别、测试策略、测试用例、覆盖追溯、边界条件、异常路径、非功能需求和可执行性等测试专家维度。
2. Alex judge prompt 包含问题定义、用户画像、用户旅程、价值主张、需求拆解、优先级、验收标准和业务闭环等业务分析师维度。
3. prompt 明确要求输出严格 JSON，并包含 `dimension_scores`、`evidence`、`recommendations`。
4. verdict parser 对缺字段、非法分数、非法维度分数显式失败。

## 验证计划

- 先写失败测试覆盖 prompt 和 parser。
- 最小实现后运行 `test_llm_judge.py`。
- 运行 New Agents 浏览器 E2E 聚焦测试，确保可选 judge 关闭时仍是确定性路径。
- 运行 `git diff --check`。
