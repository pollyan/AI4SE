# New Agents 策略图表生成器与 schema 强化设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/TESTING.md`、`docs/CODING_STANDARDS.md`、`docs/DESIGN_PRINCIPLES.md`。
- 已读取：`docs/todos/archive/2026-06-25-new-agents-test-strategy-artifact-format-regression.md`、`docs/todos/archive/2026-06-24-new-agents-test-strategy-artifact-format-streaming-bug.md`、`docs/superpowers/specs/2026-06-23-deepseek-v4-strategy-artifact-data-design.md`、`docs/superpowers/plans/2026-06-23-deepseek-v4-strategy-artifact-data.md`。
- 已读取：`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/agent_runtime.py`、`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`。
- 工作区状态：已有无关脏文件 `dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`、`tools/intent-tester/test-results/proxy/junit.xml` 和 `docs/mockups/`，本轮不触碰。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| A. STRATEGY 图表确定性生成强化 | 用户截图中的 STRATEGY 格式失败、Mermaid 易错、模型仍要输出 RPN、标签转义缺测试 | 用户进入策略制定 -> 模型输出业务数据 -> 后端生成正式策略蓝图和图表 -> 用户看到稳定产物或明确失败 | 只改 prompt、只改 RPN 或只改 Mermaid 转义都不能闭合“策略蓝图稳定呈现” | 后端 renderer/runtime 测试、契约校验、全量验证记录 |
| B. 结构化失败 UI 诊断强化 | 左侧“结构化结果未更新”仍较笼统 | 失败时用户看到字段级错误与重试建议 | 不解决 Mermaid/业务数据错误源，属于另一个可见诊断体验 | 前端截图、SSE 错误消息测试 |
| C. 全工作流图表 schema 工具化 | 把所有 Mermaid 类型改成统一后端生成器 | 多工作流都使用 schema -> generator -> renderer | 跨多个阶段和图类型，破坏面大，不适合当前截图指向的紧急路径 | 多阶段契约测试和真实 smoke |

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 用户最新目标和当前 STRATEGY 失败 | 模型只填业务结构化数据，RPN 和图表由后端确定性生成 | STRATEGY 已有 artifact_data renderer、Mermaid 和 risk-board 由后端生成 | RPN 仍由模型必填；Mermaid 标签特殊字符未收紧 | 直接降低策略制定阶段格式失败率 | 小到中，限定后端 schema/runtime/tests | 聚焦 pytest 可覆盖 | 本轮 |
| B | 用户截图中的失败反馈 | 失败原因可直接指向字段和重试动作 | 有 generic 结构化失败提示 | 用户不知道是哪类字段导致 | 提升可诊断性 | 需要前端/后端错误协议变更 | API/UI 测试 | 下一轮候选 |
| C | 长期方案讨论 | 各图表类型统一 schema 化工具 | 部分阶段已有 renderer | 统一抽象未成型 | 长期收益高 | 跨阶段高破坏面 | 覆盖范围大 | 后续专项 |

排序结论：
1. 选择 A，因为它直接回应用户“Mermaid 图格式经常失败”的主路径，并且能在共享 runtime 内通过小范围 schema / renderer / prompt / 测试完成闭环。
2. B 暂不选，因为它改善失败后的解释，但不减少当前格式错误本身。
3. C 暂不选，因为它是更大重构，当前用户要求先完成本方案开发。

切片准入判断：
- 用户功能包边界：TEST_DESIGN / STRATEGY 策略蓝图图表稳定生成。并入 RPN 派生、Mermaid 标签规范化、runtime instruction 更新、最终与流式渲染测试。排除前端错误文案改造和跨工作流统一图表框架。
- 用户可感知动作链：用户确认进入策略制定 -> 模型返回策略业务字段 -> 后端验证和生成策略蓝图图表 -> 右侧正式产物稳定显示 -> 用例编写阶段可继续消费。
- 相邻缺口合并：把 RPN 派生和 Mermaid 标签规范化合并处理，因为二者共同作用于同一 STRATEGY 图表稳定链路。
- 过薄风险检查：本轮不是单 helper 修复；它消除模型输出派生字段导致的结构化失败，并强化正式产物图表生成契约。
- 能力增量句：完成后，用户现在可以在策略制定阶段让模型只输出业务风险评分，后端负责生成稳定 Mermaid 和 risk-board 图表，错误输入仍会显式失败。

切片厚度门禁：
- 入口：`/api/agent/runs/stream` typed Agent Runtime 的 TEST_DESIGN / STRATEGY 阶段。
- 动作：模型输出 `artifact_data`，运行时解析并渲染策略蓝图。
- 处理：Pydantic schema 验证业务字段，后端派生 RPN 并生成 Markdown、Mermaid、ai4se-visual。
- 可见结果：右侧产物是正式策略蓝图，包含风险矩阵、风险明细、risk-board 和测试金字塔。
- 状态承接：产物仍走既有 `artifact_update.markdown` 和 workflow contract，可被后续阶段消费。
- 失败反馈：错误 RPN、非法范围和空字段继续显式 ValidationError，不做静默 fallback。
- 证据：新增/更新 pytest、contract validation、全量本地验证或环境阻塞记录。
- 结论：通过。

本轮用户故事：

作为测试设计工作流用户，当我进入策略制定阶段并让 AI 生成风险驱动策略时，我可以只依赖模型填写业务数据，由后端稳定生成 Mermaid 和 risk-board 图表，从而减少正式产物格式错误和流式结构化失败。

验收条件：
1. Given STRATEGY `artifact_data.risks[]` 只有 S/O/D 而没有 `rpn`
   When 后端解析并渲染 artifact
   Then 风险表、Mermaid 图和 risk-board 使用后端计算的 RPN，contract validation 通过
   Evidence: `test_artifact_data_renderers.py` 与 `test_agent_runtime.py`
2. Given STRATEGY `artifact_data.risks[]` 显式传入错误 `rpn`
   When 后端验证 schema
   Then 仍然抛出字段级 ValidationError，不生成假成功产物
   Evidence: Pydantic 校验测试
3. Given 风险名或分层名包含双引号、反斜杠和换行
   When 后端生成 Mermaid
   Then Mermaid 代码块标签被规范化，不出现标签内裸换行或破坏性引号
   Evidence: Mermaid 特殊字符测试
4. Given 构建 STRATEGY raw JSON instruction
   When 模型读取输出要求
   Then prompt 明确说明不要输出 Markdown/Mermaid/risk-board，RPN 由后端根据 S/O/D 计算
   Evidence: runtime instruction 测试

## Superpowers Brainstorming 自问自答

Explore Project Context：
- New Agents 架构要求 Lisa、Alex 和未来 agents 共享 runtime、transport、state 和 UI；本轮不能新增 STRATEGY 专用 API 或渲染管线。
- 当前 STRATEGY 已有 `StrategyArtifactData` 和 `render_test_design_strategy_markdown`，图表已经由后端输出 `quadrantChart`、`block-beta` 和 `ai4se-visual risk-board`。
- 旧 spec 要求模型输出 `rpn`，当前 validator 校验 `rpn == severity * occurrence * detection`。这能防止错误数据，但增加模型格式和算术负担。
- 当前 `_escape_mermaid_label` 只替换双引号；对换行和反斜杠没有测试覆盖。
- 本轮目标不大到需要跨阶段抽象化所有图表；先把用户实际卡住的 STRATEGY 阶段闭环做稳。

Visual Companion Decision：
- 本轮不是新增前端视觉样式或 HTML mockup；用户已经认可未来渲染效果，当前问题是后端图表生成稳定性。因此不需要新增视觉伴随稿。

Clarifying Questions：
- 用户是谁？使用 TEST_DESIGN 工作流的用户，需要在策略制定阶段看到正式策略蓝图。
- 用户要完成什么？确认 AI 生成的风险驱动测试策略，并进入用例编写。
- 成功状态是什么？右侧产物完整渲染，图表不因模型输出 Mermaid/RPN 细节而失败。
- 输入来源是什么？模型输出的 JSON `artifact_data`，特别是风险 S/O/D、风险名称、测试层级。
- 约束是什么？不新增 agent-specific runtime；不做 silent fallback；错误输入必须可诊断。
- 失败路径是什么？错误范围、空字段、显式错误 RPN 继续 ValidationError。
- 下游承接是什么？`artifact_update.markdown` 保持现有 contract，后续 CASES 阶段继续引用策略产物。
- 不做什么？不重写前端错误展示；不把 Mermaid 生成器抽象到所有 workflow；不引入新依赖。

Approaches：
- 方案 A：保留现有 STRATEGY renderer，收紧 schema：RPN 改为后端派生，错误显式 RPN 仍失败，补 Mermaid 标签规范化。优点是范围小、共享 runtime 内完成；缺点是只覆盖 STRATEGY 当前图表。推荐。
- 方案 B：新增模型可调用“Mermaid 工具”。优点是看起来贴合用户提议；缺点是仍让模型参与图表语法选择，还需要工具调用协议和错误恢复，稳定性不如确定性代码。
- 方案 C：新增跨工作流图表生成器抽象。优点是长期统一；缺点是会同时碰多个阶段、图类型和历史契约，不适合当前 P0 修复。

Presented Design：
- Architecture：继续使用 `artifact_data -> Pydantic schema -> renderer -> AgentTurnOutput` 共享链路。
- Components：修改 `StrategyRisk`，把 `rpn` 变为可选输入和后端派生输出；修改 `_escape_mermaid_label`，规范化 Mermaid 标签；修改 STRATEGY structured output instruction。
- Data Flow：模型输出 risk S/O/D -> `StrategyRisk.validate_rpn` 计算 expected -> `render_test_design_strategy_markdown` 读取模型实例中的 RPN -> Markdown/Mermaid/risk-board 统一使用该值。
- Error Handling：缺省 RPN 是合法输入；错误 RPN 是显式错误；非法 S/O/D、空字符串和额外字段沿用现有失败。
- Testing：先写失败测试，再实现；覆盖 renderer、runtime instruction、parse final JSON、stream partial rendering 和 contract validation。
- 子智能体：未使用。当前工具规则要求用户明确要求子智能体才可分发，本轮改动集中且无需并行写入。

## 实现边界

允许写入：
- `docs/todos/2026-06-25-new-agents-strategy-chart-generator-schema-hardening.md`
- `docs/superpowers/specs/2026-06-25-new-agents-strategy-chart-generator-schema-hardening-design.md`
- `docs/superpowers/plans/2026-06-25-new-agents-strategy-chart-generator-schema-hardening.md`
- `tools/new-agents/backend/artifact_data_renderers.py`
- `tools/new-agents/backend/agent_runtime.py`
- `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- `tools/new-agents/backend/tests/test_agent_runtime.py`

不触碰：
- 现有无关生成包和 mockup 脏文件。
- 前端 artifact diff / visual renderer 代码。
- 工作流 manifest、Agent API path、SSE transport 或 agent-specific runtime。
