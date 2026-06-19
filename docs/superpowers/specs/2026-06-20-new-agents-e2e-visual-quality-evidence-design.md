# New Agents E2E 可视化质量证据硬化设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-ux-professionalization.md`、`tests/e2e/new_agents_browser/llm_judge.py`、`tests/e2e/new_agents_browser/test_llm_judge.py`、`tests/e2e/new_agents_browser/workflow_runner.py`、`tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py`、`tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py`、`tests/e2e/new_agents_browser/sse_mock.py`。
- 当前工作区：主目录不是 linked worktree；仅有 `dist/intent-test-proxy.zip` 与 `tools/intent-tester/frontend/static/intent-test-proxy.zip` 两个未提交遗留构建包。由于本切片集中在 E2E 质量证据链，主线程串行实现并在收尾中保持 zip 排除。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| E2E/LLM judge 可视化质量证据硬化 | P0.3 “LLM judge 或 E2E 证据能评价全流程专业感和可视化质量” | E2E 跑完整 Lisa/Alex 工作流 -> 每阶段 artifact 必须包含预期可视化 marker -> 可选 LLM judge verdict 必须包含“可视化质量”维度且达标 | 只校验 prompt 或只校验合同不能证明浏览器全流程产物实际包含可视化；只校验 marker 又不能证明 judge 评价可视化质量 | `test_llm_judge.py`、Lisa/Alex E2E scenario 测试 |
| PDF 复杂 Mermaid/SVG 高保真 | Artifact 导出剩余项 | 用户导出 PDF -> 复杂 Mermaid 以真实图形出现 | 涉及异步 Mermaid runtime、SVG/raster 或 PDF XObject，风险高于质量证据硬化 | PDF 导出单测和构建验证 |

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E2E/LLM judge 可视化质量证据硬化 | todo P0.3 / explorer 审计 | E2E 与 judge 都能证明全流程可视化质量 | 合同和 prompt 已要求可视化；judge parse 只要求 dimension_scores 非空；E2E 只看 headings | 缺少稳定证据证明浏览器全流程 artifact 实际有可视化，且 judge 没漏掉可视化评分 | 直接增强专业可信度的验收闭环 | 中等；需避免让可选 LLM judge 变成必跑外部依赖 | 纯 Python 单测和现有 E2E mock 流程 | 本轮 |
| PDF 复杂 Mermaid/SVG 高保真 | Artifact P1 导出体验 | 非 flowchart Mermaid 能以图形嵌入 PDF | 当前 flowchart/graph 简化矢量，其他 Mermaid 摘要降级 | 高复杂图导出仍不够美观 | 提升交付物外观 | 高；异步渲染和 PDF image 嵌入 | 前端 PDF 单测 | 下一轮候选 |

排序结论：
1. 选择 E2E/LLM judge 可视化质量证据硬化，因为它是 P0 专业可信度证据缺口，且能覆盖 Lisa/Alex 全流程。
2. PDF 高保真暂缓，因为它是 P1 导出增强，技术风险和改动面更大。

切片厚度门禁：
- 入口：现有 E2E scenario 与可选 LLM judge。
- 动作：浏览器跑完整 workflow，或 judge 解析 verdict。
- 系统处理：runner 断言 artifact headings 与 visual markers；judge parser 校验“可视化质量”维度。
- 可见结果：测试失败能明确指出缺少可视化 marker 或缺少/低分可视化质量维度。
- 状态承接：run result 继续提供 final artifact / stage artifacts 给 judge。
- 失败反馈：断言错误包含缺失 marker 或低分维度。
- 证据：新增 RED/GREEN 单测与 Lisa/Alex E2E mock 测试。

## 用户故事

作为产品和工程负责人，我希望我们不仅在合同里要求产物有图表，也能在浏览器 E2E 和 LLM judge 证据中证明 Lisa/Alex 的完整工作流实际包含专业可视化，并且 judge 没有忽略可视化质量维度。

## 目标行为

- `parse_judge_result` 必须拒绝缺少“可视化质量”或等价可视化维度的 verdict。
- `assert_llm_judges_artifact_quality` 必须检查可视化维度分数不低于阈值，低分时报出可视化维度问题。
- `WorkflowScenario` 的每个阶段可声明 `visual_markers`，runner 在 artifact pane 中断言这些 marker 存在。
- Lisa/Alex 现有 E2E scenario 至少覆盖首阶段和关键后续阶段的 Mermaid / `ai4se-visual` markers。
- `visual_markers` 是代码视图中的产物源契约证据，用于证明完整工作流实际产出了可渲染图表协议；Mermaid SVG 成功渲染和结构化可视化 UI 渲染仍由既有前端组件测试覆盖。

## 范围

进入本轮：
- 更新 judge parser / assertion。
- 更新 E2E workflow runner 的 stage expectation。
- 更新 Lisa/Alex E2E scenario 的可视化 marker。
- 更新 E2E SSE mock，使普通 Lisa/Alex 主路径和 Alex->Lisa handoff 路径都输出可验证的可视化产物。
- 更新 todo 进展记录。

不进入本轮：
- 不强制要求本地必须调用真实 LLM judge；如果环境已开启 `NEW_AGENTS_E2E_LLM_JUDGE`，则允许 focused E2E 覆盖真实 judge 证据。
- 不改后端 artifact contract、workflow manifest、prompt 或 Agent Runtime。
- 不改 PDF/DOCX 导出。
- 不覆盖全部在线 workflow 的 browser E2E，只先硬化 Lisa/Alex 主路径。

## 验收条件

1. 缺少“可视化质量”维度的 judge JSON 会被 `parse_judge_result` 拒绝。
2. 可视化质量维度低于阈值时，artifact quality assertion 会失败。
3. Lisa/Alex E2E scenario 会断言每阶段 artifact 中出现预期 Mermaid / `ai4se-visual` marker。
4. 现有可选 LLM judge 开关仍保持可选，不要求本地具备外部模型凭证。

## 验证计划

- RED/GREEN：`.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_llm_judge.py`
- E2E mock 验证：`.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py`
- `git diff --check`

## Self-Review

- Placeholder scan: 无 TBD/TODO。
- Scope check: 聚焦证据硬化，不混入 PDF 导出或模型合同。
- Ambiguity check: “可视化质量”维度支持中文精确名称与包含“可视化”的等价维度。
