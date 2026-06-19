# New Agents E2E Judge Trace 设计

## 背景

`docs/todos/new-agents-evolution.md` 的 P0 首项要求把浏览器级工作流测试中的可选 LLM judge 演进成核心评估手段。当前 `tests/e2e/new_agents_browser/workflow_runner.py` 只返回最终 artifact 字符串，`llm_judge.py` 也只把最终 artifact 发给 judge，因此无法评价完整交互过程、阶段切换、每阶段产物质量和用户引导质量。

本轮只做数据底座：让浏览器 E2E runner 返回结构化工作流轨迹，并让 judge prompt 能消费这份轨迹。真实模型 rubric 和分角色评分在后续切片推进。

## 用户故事

作为目标模式执行者，当我运行 Lisa 或 Alex 的浏览器 E2E 工作流时，我可以获得完整工作流轨迹，包括用户输入、助手回复、阶段切换、每阶段产物和最终产物，从而让后续 LLM judge 不再只能评价最终 Markdown。

## 范围

进入本轮：

- 新增结构化运行结果类型，包含：
  - `final_artifact`
  - `stage_artifacts`
  - `conversation_events`
  - `stage_transitions`
- 修改 `run_complete_workflow(...)` 返回结构化结果。
- 保持现有 E2E 测试对最终 artifact 的断言能力。
- 修改 LLM judge helper，使其接收结构化结果并构造包含完整轨迹的 prompt。
- 增加确定性测试验证 prompt 包含轨迹信息，不调用真实模型。
- 更新 `docs/todos/new-agents-evolution.md` 的 P0 #1 进展记录。

不进入本轮：

- 不设计完整 Lisa/Alex 分角色 rubric。
- 不调用真实 LLM judge。
- 不修改 New Agents 产品运行时代码。
- 不改变 typed SSE、workflow 配置或前后端契约。

## 验收条件

1. `run_complete_workflow(...)` 返回对象包含最终 artifact、每阶段 artifact、会话事件和阶段切换事件。
2. Lisa / Alex 现有 E2E 测试仍能断言最终产物内容。
3. LLM judge prompt 能包含工作流名、完整会话轨迹、阶段切换、每阶段产物和最终产物。
4. 默认确定性测试不依赖真实模型或外部网络。

## 风险

- E2E runner 和 judge 调用签名变更会影响 Lisa/Alex 两个测试文件，需要同步修改。
- 会话轨迹从页面文本采集时可能包含 UI 噪声；本轮先记录关键用户输入、助手文本和阶段事件，后续 judge rubric 再收紧格式。
- 结构化结果不应把完整 artifact 塞回左侧 chat；本轮只收集测试证据，不改变 UI 行为。

## 验证计划

- 先写失败测试，验证 judge prompt 必须包含完整 run result 字段。
- 更新 runner / judge 后运行聚焦 pytest。
- 运行 `git diff --check` 检查文档和代码格式。
