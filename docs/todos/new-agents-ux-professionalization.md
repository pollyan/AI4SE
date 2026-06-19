# New Agents UI/UX 与专业产出物优化 Todo

本文记录 `tools/new-agents/` 下一阶段仍需推进的用户体验、交互恢复、可视化和专业产出物优化。旧长期 backlog 已归档到 `docs/todos/archive/new-agents-evolution-2026-06-19.md`，本文件只保留尚未闭环、且用户可感知的优化项。

## 使用规则

- `P0`：直接影响主链路可用性、用户信任、专业可信度或高频操作效率。
- `P1`：明显提升 Lisa / Alex 的工作流体验、产出物质量或平台治理能力。
- `P2`：增强型能力，等待 P0/P1 稳定后推进。
- 所有改动必须继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract 和共享 UI 组件，不为 Lisa、Alex 或单个 workflow 新增运行时分支。
- 进入实现前仍需按 `docs/strategy/goal-mode-playbook.md` 做 Current State Gap Analysis、spec、plan 和验证。
- UI 优化应优先聚合成用户动作链，不把单按钮、单字段或单 endpoint 包装成独立 milestone。

## P0 高优先级

### 1. 工作区顶部操作收敛

**目标**：降低 Lisa / Alex 工作区顶部按钮密度，让用户更容易理解当前处于哪个工作流、哪个阶段、下一步能做什么。

**待办**：

- 重新梳理 Header 信息架构，保留少量一级操作，将低频能力收纳到“更多”或对应上下文区域。
- 一级操作建议保留：返回、工作流切换、阶段进度、新会话、历史会话。
- 将上下文摘要、运行统计、设置、导出报告等低频能力收敛到二级入口。
- 将产物相关操作优先放到右侧 ArtifactPane 工具条，避免 Header 与 ArtifactPane 重复导出入口。
- `TEST_DESIGN` 的测试资产入口保留为工作流专属能力，但应考虑移动到右侧产物/资产上下文，而不是混在全局按钮组中。
- 保持阶段条存在，但补充更清晰的已完成、当前、未开始状态；避免误导用户以为可以任意跳阶段。
- 审视右侧产物生成提示中的进度条：如果进度条不能与真实生成阶段、流式 token、artifact 章节完成度或可观测状态联动，就移除该装饰性进度条，只保留明确的“正在构建产出物”状态和必要的轻量动画。

**验收证据**：

- Header 在桌面宽度下不再出现一排等权重按钮。
- 高频操作与低频操作分层清晰。
- 导出、测试资产、运行统计等入口有明确归属，不再让用户困惑。
- 右侧产物生成提示不再出现“看似进度条但不动或无真实含义”的 UI；保留时必须能体现真实进度或明确的非确定性加载状态。
- Header 组件测试覆盖主要入口可用性和收敛后的菜单行为。

**进展记录**：

- 2026-06-19：完成第一块 CGA「工作区操作降噪与生成状态清理」。
  - Header 一级操作收敛为 `新会话`、`历史会话`、`更多操作`。
  - `上下文摘要`、`运行统计`、`TEST_DESIGN` 的 `测试资产` 和 `设置` 已收纳到 `更多操作`。
  - Header 移除 `导出报告`，产物导出只保留在 ArtifactPane 下载菜单。
  - ArtifactPane 移除无真实进度来源的横向进度条，保留明确生成文案和轻量非确定性动画。
  - 验证：`npm run test -- --run src/components/__tests__/Header.test.tsx src/components/__tests__/ArtifactPane.test.tsx`；`npm run build`；`git diff --check`。

### 2. 结构化输出失败与重试体验

**目标**：当 Agent Runtime 结构化输出、artifact contract、Mermaid 或 `ai4se-visual` 失败时，用户能立即理解失败原因并在当前语境中重试，而不是只看到提示词说“请重试”却找不到入口。

**待办**：

- 在结构化输出失败时显示明确的失败恢复卡片，包含失败原因、右侧产物是否保持不变、可执行下一步。
- 在失败卡片中提供主操作 `重试本阶段生成`，复用现有 retry/rollback 逻辑。
- 在连续失败时提供 `补充信息后再试` 引导，而不是继续盲目重试。
- 如果当前存在阶段推进确认，且上一轮产物更新失败或图表/结构化可视化失败，应阻断或弱化“确认进入下一阶段”，避免用户带着无效产物继续推进。
- Mermaid 图表失败时，右侧图表块保留 `重新生成图表`，左侧对话区域也应有轻量提示，避免用户必须滚动右侧才能发现问题。

**验收证据**：

- 结构化输出失败后，用户能在当前可见区域找到重试入口。
- 重试不会污染右侧产物，失败前的 artifact 可恢复。
- 阶段确认卡片不会在产物失败时误导用户继续进入下一阶段。
- 覆盖 ChatPane、chatService、Mermaid retry 和阶段确认相关测试。

**进展记录**：

- 2026-06-19：完成第一块结构化失败恢复切片。
  - ChatPane 会把 `结构化输出生成失败` 的 assistant 消息渲染为恢复卡片，明确提示 `右侧产出物已保持不变`。
  - 恢复卡片提供主操作 `重试本阶段生成`，复用现有 `handleRetry` / artifact rollback 逻辑。
  - 最新 assistant 消息为结构化失败时，隐藏阶段推进确认卡片，避免用户带着无效产物继续进入下一阶段。
  - 验证：`npm run test -- --run src/components/__tests__/ChatPane.test.tsx src/services/__tests__/chatService.test.ts`；`npm run build`；`git diff --check`。

### 3. 全流程专业产出物与可视化增强

**目标**：每个工作流在所有适合的阶段都要体现“专业、有结构、可视化”的产出质量。第一阶段要尤其重视专业第一印象，后续阶段如果从专业角度适合加入图表、矩阵、看板、时间线或评分卡，也应纳入产出物设计。

**待办**：

- 为每个在线 workflow 的所有阶段审视专业方法论、关键判断、风险/假设、下一阶段输入质量检查和可视化机会。
- 第一阶段尽量提供至少一个稳定可视化元素：Mermaid 或 `ai4se-visual`，用于建立专业第一印象。
- 后续阶段如果存在专业表达价值，也应加入可视化元素，例如风险矩阵、评分矩阵、用户旅程、测试覆盖追溯、行动看板、路线图或阶段对比。
- 推荐首阶段可视化：
  - `TEST_DESIGN/CLARIFY`：系统边界图、核心链路 flowchart、需求风险初筛矩阵。
  - `REQ_REVIEW/REVIEW`：评审维度矩阵、问题分布摘要、需求质量雷达的结构化替代组件。
  - `INCIDENT_REVIEW/TIMELINE`：事件 timeline、影响范围结构化摘要。
  - `IDEA_BRAINSTORM/DEFINE`：问题-用户-场景关系图、问题树 mindmap。
  - `VALUE_DISCOVERY/ELEVATOR`：价值主张结构图、用户-痛点-收益映射。
- 推荐后续阶段增强方向：
  - `TEST_DESIGN/STRATEGY/CASES/DELIVERY`：风险热力、测试金字塔、测试点拓扑、覆盖追溯矩阵、交付清单。
  - `REQ_REVIEW/REPORT`：问题优先级分布、责任归属矩阵、评审结论看板。
  - `INCIDENT_REVIEW/ROOT_CAUSE/IMPROVEMENT`：5-Why 链路、原因结构图、改进行动看板。
  - `IDEA_BRAINSTORM/DIVERGE/CONVERGE/CONCEPT`：创意空间图、ICE/RICE 评分矩阵、MVP 功能分布、增长漏斗。
  - `VALUE_DISCOVERY/PERSONA/JOURNEY/BLUEPRINT`：用户画像卡片、用户旅程图、需求蓝图架构、MVP 路线图。
- 优先使用稳定 Mermaid 类型或结构化可视化组件，不让模型自由生成复杂 HTML。
- 将专业章节和可视化要求纳入 artifact contract 或 prompt，避免只靠模型自由发挥。

**验收证据**：

- 每个在线 workflow 第一阶段都有明确专业章节和至少一个可视化策略。
- 每个在线 workflow 的后续关键阶段都有专业可视化机会审计，适合可视化的阶段已补充 Mermaid 或结构化可视化方案。
- 后端 contract 或测试能发现关键结构缺失。
- 前端能稳定渲染推荐可视化，失败时有显式错误。
- LLM judge 或 E2E 证据能评价全流程专业感和可视化质量。

**进展记录**：

- 2026-06-19：完成首阶段专业可视化契约基线。
  - 所有在线 workflow 的首阶段都已有 contract 级可视化要求：
    `TEST_DESIGN/CLARIFY` 要求 Mermaid `flowchart`；
    `REQ_REVIEW/REVIEW` 要求 `ai4se-visual score-matrix`；
    `INCIDENT_REVIEW/TIMELINE` 保持 Mermaid `timeline`；
    `IDEA_BRAINSTORM/DEFINE` 要求 Mermaid `mindmap`；
    `VALUE_DISCOVERY/ELEVATOR` 要求 `ai4se-visual score-matrix`。
  - 新增共享结构化可视化类型 `score-matrix`，前端复用 `StructuredVisual` 表格渲染，不为 Lisa/Alex 或具体 workflow 增加渲染分支。
  - 修复 `IDEA_BRAINSTORM/DEFINE` 模板中 Mermaid 围栏未实际插值的问题，确保 mindmap 能被渲染。
  - 验证：`.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py`；`npm run test -- --run src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx src/core/__tests__/mermaid.test.ts`；`npm run build`；`git diff --check`。
  - 剩余：后续阶段仍需继续做逐阶段可视化机会审计，并把适合的风险矩阵、行动看板、旅程图、覆盖图、路线图纳入 contract 或 prompt。
- 2026-06-19：完成第二块 CGA「后续阶段结构化可视化契约扩展」。
  - `TEST_DESIGN/STRATEGY` 新增 `ai4se-visual risk-board`，稳定表达 FMEA 风险、S/O/D、RPN、缓解策略和覆盖建议。
  - `INCIDENT_REVIEW/IMPROVEMENT` 新增 `ai4se-visual action-board`，稳定表达 SMART 改进行动、对应根因、负责人、期限、状态和验证方式。
  - `VALUE_DISCOVERY/JOURNEY` 新增 `ai4se-visual journey-map`，稳定表达旅程阶段、用户任务、触点、情绪评分、关键痛点和机会假设。
  - `TEST_DESIGN/DELIVERY` 新增 `ai4se-visual coverage-map`，稳定表达需求、风险、测试点、用例和验收状态覆盖关系。
  - 前端共享 `StructuredVisual` / parser 已支持 `risk-board`、`action-board`、`journey-map`、`coverage-map`，没有新增 Lisa/Alex 或 workflow 专属渲染分支。
  - 验证：`.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py`；`npm run test -- --run src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx src/core/__tests__/mermaid.test.ts src/components/__tests__/ArtifactPane.test.tsx`；`npm run build`。
  - 剩余：仍需审计其他后续阶段是否存在应补的结构化路线图、创意空间图、责任矩阵等。
- 2026-06-19：完成第三块 CGA「剩余关键阶段专业可视化补强」。
  - 新增共享结构化可视化类型 `priority-board`、`cause-map`、`mvp-map`、`roadmap`，继续复用 `ai4se-visual` JSON + 共享表格渲染。
  - `REQ_REVIEW/REPORT` 新增 `priority-board`，稳定表达问题、优先级、影响范围、责任方和下一步。
  - `INCIDENT_REVIEW/ROOT_CAUSE` 新增 `cause-map`，稳定表达 5-Why 层级、回答、原因类型和证据。
  - `IDEA_BRAINSTORM/CONCEPT` 新增 `mvp-map`，稳定表达 MVP 模块、用户价值、验证指标和取舍理由。
  - `VALUE_DISCOVERY/BLUEPRINT` 新增 `roadmap`，稳定表达版本、时间、核心功能、目标和成功指标。
  - 验证：`.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py::test_later_stage_structured_visual_contracts_cover_professional_views tools/new-agents/backend/tests/test_agent_contracts.py::test_validate_agent_turn_accepts_complete_required_artifact_template tools/new-agents/backend/tests/test_agent_contracts.py::test_build_artifact_contract_prompt_includes_required_structured_visual_contract`；`npm run test -- --run src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx`。
  - 剩余：可继续做 E2E/LLM judge 证据，评价全流程专业感和可视化质量。
- 2026-06-20：完成第四块 CGA「E2E 与 LLM judge 可视化质量证据硬化」。
  - E2E `StageExpectation` 新增 `visual_markers`，Lisa/Alex 浏览器主流程现在不仅检查 artifact 标题，还会检查每阶段 Mermaid 或 `ai4se-visual` marker。
  - `TEST_DESIGN` mock 产物覆盖首阶段 Mermaid `flowchart`、策略 `risk-board`、用例 `traceability-matrix` 和交付 `coverage-map`。
  - `VALUE_DISCOVERY` mock 产物覆盖 `score-matrix`、`journey-map` 和 `roadmap`。
  - Alex -> Lisa handoff mock 产物改为继承 Alex 的 AI 测试设计助手蓝图，避免接力后退回无关的登录支付样例。
  - LLM judge verdict 解析现在要求包含“可视化质量”或等价维度，且 artifact/handoff judge 都会校验该维度分数阈值。
  - 验证：先运行 `.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_llm_judge.py` 观察到 handoff prompt 缺少 `可视化质量` 失败，再实现后通过；先运行 `.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py` 观察到缺少 `flowchart TD` / `score-matrix` 失败，再补 mock 后同命令 6/6 通过；当前环境开启的可选 LLM judge 也覆盖并通过了 Alex -> Lisa handoff 质量评审。
  - 剩余：复杂 Mermaid/SVG 的 PDF/DOCX 高保真图片级嵌入仍可作为后续增强切片。

## P1 中优先级

### 4. Mermaid 可靠性与结构化可视化扩展

**目标**：降低 Mermaid 生成失败对用户体验的影响，同时把矩阵、评分、覆盖、风险等业务可视化逐步迁移到更稳定的结构化协议。

**待办**：

- 保留 Mermaid 用于流程图、时间线、mindmap、journey 等适合文本图语法的场景。
- 为高失败率 Mermaid 类型增加更窄的模板、示例和 sanitizer 规则。
- 扩展 `ai4se-visual` 类型，不止支持 `traceability-matrix`：
  - `score-matrix`：评分矩阵、ICE / RICE / 优先级评估。
  - `risk-board`：风险热力、处置状态、责任人。
  - `journey-map`：用户旅程阶段、任务、痛点、机会点。
  - `action-board`：故障复盘改进行动、状态和验证方式。
  - `coverage-map`：需求、风险、测试点、用例覆盖关系。
- 保持可视化渲染走共享组件，不为 Lisa/Alex 或具体 workflow 建独立渲染分支。

**验收证据**：

- 至少新增 1-2 个非 Mermaid 结构化可视化类型。
- 对应 parser、component、ArtifactPane 渲染和 contract 测试完整。
- Mermaid 失败率高的业务视图有结构化替代路径。

**进展记录**：

- 2026-06-19：新增 4 个共享结构化可视化类型：`risk-board`、`action-board`、`journey-map`、`coverage-map`。
  - 已纳入后端 artifact contract、contract prompt schema、前端 parser、共享渲染组件和 prompt 模板示例。
  - 覆盖阶段：`TEST_DESIGN/STRATEGY`、`INCIDENT_REVIEW/IMPROVEMENT`、`VALUE_DISCOVERY/JOURNEY`、`TEST_DESIGN/DELIVERY`。
  - 验证：`.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py`；`npm run test -- --run src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx src/core/__tests__/mermaid.test.ts src/components/__tests__/ArtifactPane.test.tsx`；`npm run build`。
- 2026-06-19：新增 4 个共享结构化可视化类型：`priority-board`、`cause-map`、`mvp-map`、`roadmap`。
  - 已纳入后端 artifact contract、contract prompt schema、前端 parser、共享渲染组件和 prompt 模板示例。
  - 覆盖阶段：`REQ_REVIEW/REPORT`、`INCIDENT_REVIEW/ROOT_CAUSE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/BLUEPRINT`。
  - 验证：`.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py::test_later_stage_structured_visual_contracts_cover_professional_views tools/new-agents/backend/tests/test_agent_contracts.py::test_validate_agent_turn_accepts_complete_required_artifact_template tools/new-agents/backend/tests/test_agent_contracts.py::test_build_artifact_contract_prompt_includes_required_structured_visual_contract`；`npm run test -- --run src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx`。
- 2026-06-19：完成 Mermaid fence 模板可靠性修复。
  - 修复 `TEST_DESIGN/CASES`、`REQ_REVIEW/REPORT`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`、`VALUE_DISCOVERY/BLUEPRINT` 中输出字面量 `${FENCE}` 的问题，避免模板示例无法形成真实 Mermaid fenced code block。
  - 新增 `WORKFLOWS` 全量模板测试，防止后续 workflow template 再暴露字面量 `${FENCE}`。
  - 验证：`rg -n '\\\\\\$\\{FENCE\\}' tools/new-agents/frontend/src/core/prompts` 无匹配；`npm run test -- --run src/core/__tests__/mermaid.test.ts`；`npm run build`。

### 5. 左侧对话自然表达与重点可扫描

**目标**：左侧对话继续像自然聊天，不做固定表单式摘要，但要避免长文本变成一整块难扫的纯文本。

**待办**：

- 不引入固定字段化 chat schema，不强制每轮出现“本轮结论 / 已更新内容 / 需要确认”等死板标题。
- 通过 prompt 引导 Lisa / Alex 使用自然顾问式表达：短段落、适度 bullet、少量重点加粗、必要时引用块。
- 正常对话保持自由聊天感；只有异常、阶段确认、信息不足时才使用明确组件或结构化卡片。
- 避免左侧复制完整 artifact 正文，继续保持 chat / artifact 职责分离。
- 检查当前 Markdown 样式在长对话、列表、引用、表格、代码和 Mermaid 失败块中的实际可读性。

**验收证据**：

- 长 assistant 回复保持可扫描，但不像系统表单。
- 失败、确认、信息不足等特殊场景有明确视觉状态。
- ChatPane 测试覆盖自然 Markdown 回复、异常恢复和阶段确认卡片。

**进展记录**：

- 2026-06-19：完成第一块 CGA「左侧自然顾问式对话契约」。
  - 后端 artifact contract 不再要求固定“本轮总结”栏目，改为引导自然顾问式对话。
  - 新契约要求 chat 使用短段落、适度 bullet、少量重点加粗或引用块提升扫读性，但不引入固定字段化 chat schema。
  - 保留 chat / artifact 职责分离：左侧只做自然承接和下一步引导，完整文档、表格、Mermaid 和结构化可视化仍放右侧 artifact。
  - 更新 Markdown 可读性测试示例，避免用“本轮总结”这类固定开头。
  - 验证：`.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py`；`npm run test -- --run src/components/__tests__/ChatPane.test.tsx src/components/__tests__/ChatPane.markdown.test.tsx`。

### 6. 模型配置与供应商治理融入体验

**目标**：把模型配置、供应商可用性、错误归因和运行统计融合到用户可理解的工作流体验中，而不是作为独立、割裂的 P2 管理功能。

**待办**：

- 当生成失败来自供应商、额度、限流或模型配置时，在失败恢复卡片中显示可理解诊断和下一步入口。
- 将模型连接检测结果、provider 错误归因、低成功率阶段告警与运行统计视图联动。
- 在设置入口收敛后，仍保证用户能快速完成默认 LLM 配置、密钥轮换和连接检测。
- 高失败率阶段或 provider 应能通过运行统计提示，辅助定位 Mermaid / contract / 模型供应商问题。
- 保留不同环境选择默认模型配置 key 的能力，不引入 workflow-specific 模型分支。

**验收证据**：

- 供应商类错误不会只显示原始异常，用户能看到可操作建议。
- 运行统计能帮助定位高失败率阶段、provider 和 contract retry。
- 设置入口收敛后，模型配置管理仍可发现、可使用、可测试。

**进展记录**：

- 2026-06-19：完成第一块 CGA「供应商失败归因与恢复提示」。
  - `chatService` 对默认模型未配置、401/403/API Key、额度/限流、网络/超时等错误做轻量归因，统一输出 `模型配置或供应商异常` 友好提示。
  - 失败提示包含可能原因、建议处理、右侧产物保持不变说明和原始错误附录，不再只显示裸 `**Error:**`。
  - ChatPane 会把供应商失败消息渲染为恢复卡片，提供 `重试本阶段生成`，并在最新消息为供应商失败时隐藏阶段推进确认。
  - 后端 context builder 会过滤该类控制反馈，避免下一轮把供应商错误卡片作为业务上下文送回模型。
  - 验证：`npm run test -- --run src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/ChatPane.markdown.test.tsx`；`.venv/bin/python -m pytest tools/new-agents/backend/tests/test_context_builder.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py`。

### 7. Artifact 协作体验深化

**目标**：从当前历史 diff / 恢复 / 简单导出，升级到更完整的文档协作能力。

**待办**：

- 支持用户在右侧产出物上进行受控人工修改，并明确修改如何进入 artifact history、stage artifact 和服务端 run snapshot。
- 增强人工修改失败恢复与后续协作处理，避免用户误以为校准已保存或已合并。
- 章节锁定。
- 批注。
- 逐行接受 / 拒绝变更。
- 真正富文本 DOCX 导出。
- 支持 Markdown 富排版、Mermaid 渲染和分页的 PDF 导出。

**验收证据**：

- 用户可以校准右侧产出物正文或局部章节，并能回滚、审阅差异。
- 人工修改不会绕过 artifact history，也不会破坏阶段产物与后续上下文的一致性。
- 导出的 Word/PDF 更接近专业交付物，而不是纯文本容器。

**进展记录**：

- 2026-06-19：完成第一块 CGA「Artifact 受控人工修改」。
  - ArtifactPane 新增 `编辑产出物` 入口，可在右侧直接编辑当前阶段 Markdown。
  - 保存修改会同步更新当前 `artifactContent` 和当前阶段 `stageArtifacts`，并写入 `artifactHistory`。
  - 如果当前内容尚未在当前阶段历史中，保存前会先保留一个当前版本备份，避免人工修改覆盖唯一可恢复状态。
  - 取消编辑不会改变 artifact、stage artifact 或 history。
  - 现有历史版本 diff / 恢复能力可用于审阅和回滚人工修改。
  - 验证：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`。
  - 剩余：章节锁定、批注、逐行接受/拒绝、富文本 DOCX/PDF 导出仍未完成。
- 2026-06-19：完成第二块 CGA「Artifact 服务端更新 API」。
  - 新增共享 `POST /api/agent/runs/<run_id>/artifacts`，支持把人工校准后的产出物保存为新的 artifact version。
  - 服务端复用 `record_artifact_version`，因此当前 artifact snapshot、版本号和 artifact 派生的 context summaries 会保持一致。
  - 前端新增 `updateRunArtifact` service，严格校验返回的 `stageId`、`content` 和 `versionNumber`，为下一步 ArtifactPane 保存接入服务端做准备。
  - 验证：`.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_update_endpoint_records_manual_artifact_version tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_update_endpoint_rejects_invalid_stage tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_update_endpoint_rejects_blank_content`；`npm run test -- --run src/services/__tests__/runSnapshotService.test.ts`。
  - 后续记录：ArtifactPane 保存接入和冲突提示见后续记录；仍需处理刷新后恢复。
- 2026-06-19：完成第三块 CGA「ArtifactPane 保存接入服务端版本」。
  - 当当前工作区存在 `currentRunId` 时，`编辑产出物` 的保存动作会调用服务端 artifact update API，成功后再更新本地 `artifactContent`、`stageArtifacts` 和 `artifactHistory`。
  - 服务端返回的 `versionNumber` 会进入本地历史版本 id，便于后续历史会话和服务端 snapshot 对齐。
  - 保存失败时保留编辑草稿并显示失败原因，不污染当前产出物、阶段产物或历史版本。
  - 无 `currentRunId` 的本地草稿场景仍保留原有本地保存能力。
  - 验证：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`。
  - 后续记录：冲突提示与冲突版本对比/刷新见后续记录；仍需章节锁定、批注、逐行接受/拒绝、富文本 DOCX/PDF 导出。
- 2026-06-19：完成第四块 CGA「Artifact 手工保存冲突提示」。
  - Artifact 更新 API 新增可选 `expectedVersionNumber`，由服务端比较当前 artifact version，防止旧页面或旧标签页静默覆盖新版本。
  - 如果版本已变化，服务端返回 `409` 和当前 artifact snapshot，前端 service 会抛出 typed `ArtifactConflictError`。
  - ArtifactPane 会从当前 run/stage 历史版本 id 推断用户开始编辑时的服务端版本；冲突时保留草稿、保留当前产物和历史版本，并提示服务端当前版本号。
  - 验证：`.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_update_endpoint_accepts_expected_current_version tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_update_endpoint_returns_409_for_stale_version`；`npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/ArtifactPane.test.tsx`。
  - 后续记录：冲突版本对比/刷新见下一条；仍需章节锁定、批注、逐行接受/拒绝、富文本 DOCX/PDF 导出。
- 2026-06-19：完成第五块 CGA「Artifact 冲突版本对比与刷新」。
  - 保存冲突后，ArtifactPane 会缓存服务端返回的当前 artifact snapshot，并在冲突卡片中提供 `对比服务端版本` 与 `刷新为服务端版本`。
  - `对比服务端版本` 使用现有 `buildLineDiff` 展示“服务端版本 vs 你的草稿”，用户能看到服务端新增/删除内容和自己的未保存修改。
  - `刷新为服务端版本` 会把服务端版本切回当前产物，同时把用户草稿保留进本地 artifact history，避免草稿丢失。
  - 验证：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`。
  - 剩余：章节锁定、批注、逐行接受/拒绝、富文本 DOCX/PDF 导出仍未完成。
- 2026-06-19：完成第六块 CGA「Artifact Word 富排版导出」。
  - Word 导出从纯 `<pre>` 文本容器升级为 Word-compatible HTML 文档，支持 Markdown 标题、段落、加粗、无序/有序列表、表格和代码块。
  - 导出文档加入专业交付物样式，表格、代码块、标题层级在 Word 中更容易阅读和二次编辑。
  - 继续先转义用户内容再做轻量 Markdown 渲染，避免 `<script>` 等 HTML 内容在导出文件中变成可执行标签。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx` 观察到新增富排版断言失败，再实现后同命令通过。
  - 剩余：真正 `.docx` 包级导出、富排版 PDF 的分页/Mermaid 渲染、章节锁定、批注、逐行接受/拒绝仍未完成。
- 2026-06-19：完成第七块 CGA「Artifact PDF 分页防截断」。
  - PDF 导出从固定单页、最多 42 行升级为按内容自动分页，长产出物不会静默丢失后续章节。
  - 生成的 PDF pages tree 会引用所有页面，并保留后续页面的 UTF-16BE 文本内容。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx` 观察到长文档分页断言失败，再实现后同命令通过。
  - 剩余：PDF 仍是文本型导出，Markdown 视觉样式、表格布局、Mermaid 渲染进 PDF 还未完成；章节锁定、批注、逐行接受/拒绝仍未完成。
- 2026-06-19：完成第八块 CGA「Artifact PDF Markdown 结构化排版」。
  - PDF 导出新增 Markdown 到 PDF 文本布局投影，标题不再带 `#`，列表转为项目符号或编号，表格转为对齐文本行，代码块去掉 fenced code block 围栏并缩进展示。
  - 该能力继续复用现有多页 PDF 和 UTF-16BE 文本输出，不新增 workflow-specific 或 agent-specific 导出分支。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx` 观察到 Markdown PDF 排版断言失败，再实现后同命令通过。
  - 剩余：PDF 仍未把 Mermaid/结构化可视化渲染为图形，也未实现真正图形表格边框；章节锁定、批注、逐行接受/拒绝、真正 `.docx` 包级导出仍未完成。
- 2026-06-19：完成第九块 CGA「Artifact 前端批注 MVP」。
  - ArtifactPane 工具栏新增 `批注` 入口，用户可在当前阶段产出物旁新增、查看和删除批注。
  - 批注绑定当前 workflow stage，并保存 `content`、`artifactExcerpt`、`createdAt`；切换阶段时只展示对应阶段批注。
  - 批注作为前端工作区状态持久化，切换 workflow、清空历史、应用 handoff 或恢复服务端 run snapshot 时清理，避免跨工作区污染。
  - 验证：先运行 `npm run test -- --run src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx` 观察到缺少批注 action 和 UI 入口失败，再实现后同命令通过。
  - 剩余：正文选区锚点、批注解决状态/回复、服务端 run snapshot 同步、章节锁定、逐行接受/拒绝、真正 `.docx` 包级导出仍未完成。
- 2026-06-19：完成第十块 CGA「Artifact 章节锁定 MVP」。
  - ArtifactPane 工具栏新增 `章节锁定` 入口，用户可按 Markdown 标题章节锁定当前阶段已确认内容。
  - 锁定记录绑定当前 workflow stage；切换阶段只展示对应阶段锁，切换 workflow、清空历史、应用 handoff 或恢复服务端 run snapshot 时清理，避免跨工作区污染。
  - 保存人工编辑时会校验锁定章节内容；如果锁定章节被修改，保存会被阻断并提示用户先解锁，不污染当前产物、阶段产物、历史版本或服务端版本。
  - 用户可在章节锁定面板解除锁定后再保存修改，适合保护已确认范围、关键决策、验收口径等内容。
  - 验证：先运行 `npm run test -- --run src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx` 观察到缺少章节锁 action 和 UI 入口失败，再实现后同命令通过；`npm run lint`；`npm run build`。
  - 剩余：重复标题的精确锚点、模型生成阶段的锁定遵守、服务端 run snapshot 同步、逐行接受/拒绝、真正 `.docx` 包级导出、PDF Mermaid/结构化可视化图形化导出仍未完成。
- 2026-06-19：完成第十一块 CGA「Artifact 冲突逐行合并 MVP」。
  - 保存人工编辑遇到服务端 artifact 版本冲突后，`对比服务端版本` 面板会在草稿新增行旁提供 `采纳` 和 `丢弃` 操作。
  - `丢弃` 会从当前编辑草稿中移除该草稿新增行，diff 立即更新，适合快速去掉不再需要的校准内容。
  - `采纳` 会以服务端当前版本为基准，把该草稿新增行保留进编辑草稿，用户仍需点击 `保存修改` 走现有冲突检测和服务端保存流程。
  - 该能力只处理可定位的草稿新增行，不自动保存、不覆盖当前 artifact、不修改服务端 API，也不引入 workflow-specific 分支。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx` 观察到缺少逐行操作按钮失败，再实现后同命令通过；`npm run test -- --run src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx`；`npm run lint`；`npm run build`。
  - 剩余：完整三方 merge、删除行/修改行语义合并、普通历史 diff 的逐行接受/拒绝、服务端合并轨迹、真正 `.docx` 包级导出、PDF Mermaid/结构化可视化图形化导出仍未完成。
- 2026-06-19：完成第十二块 CGA「Artifact DOCX 包级导出」。
  - `Word` 下载从 Word-compatible HTML `.doc` 升级为真正的 Office Open XML `.docx` 包。
  - 前端新增无依赖 `buildDocxPackage`，生成包含 `[Content_Types].xml`、`_rels/.rels`、`word/document.xml` 的最小 DOCX ZIP 包。
  - Markdown 标题、段落、列表、表格、代码块和转义文本会投影到 `word/document.xml`，`<script>` 等 HTML 内容只作为转义文本进入文档。
  - ArtifactPane 下载文件名改为 `<workflow>_artifact.docx`，MIME 改为 `application/vnd.openxmlformats-officedocument.wordprocessingml.document`。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx` 观察到仍下载 `.doc` 的断言失败，再实现后运行 `npm run test -- --run src/core/__tests__/docxExport.test.ts src/components/__tests__/ArtifactPane.test.tsx` 通过；`npm run test -- --run src/__tests__/store.test.ts src/core/__tests__/docxExport.test.ts src/components/__tests__/ArtifactPane.test.tsx`；`npm run lint`；`npm run build`。
  - 剩余：DOCX 高保真样式、页眉页脚、复杂列表编号、Mermaid/结构化可视化图形嵌入、PDF Mermaid/结构化可视化图形化导出仍未完成。
- 2026-06-19：完成第十三块 CGA「Artifact 历史 Diff 逐行审阅」。
  - 历史版本 `差异` 视图从只读对比升级为可逐行审阅：历史版本中被当前产物移除的非空行显示 `恢复此行`，当前产物新增的非空行显示 `丢弃当前行`。
  - `恢复此行` 会按历史版本中的行位置把该行插回当前 artifact，适合局部找回被误删的结论、风险或验收口径。
  - `丢弃当前行` 会从当前 artifact 中删除该新增行，适合局部撤销不需要的人工校准。
  - 每次行级操作都会先把修改前的当前产物写入 `artifactHistory`，再同步更新 `artifactContent` 和当前阶段 `stageArtifacts`，不绕过历史追踪。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx` 观察到缺少 `恢复此行` / `丢弃当前行` 按钮失败，再实现后同命令通过；`npm run test -- --run src/__tests__/store.test.ts src/core/__tests__/docxExport.test.ts src/components/__tests__/ArtifactPane.test.tsx`；`npm run lint`；`npm run build`。
  - 剩余：完整三方 merge、块级接受/拒绝、重复行精确锚点、PDF Mermaid/SVG 图片级嵌入仍未完成。
- 2026-06-19：完成第十四块 CGA「Artifact PDF 可视化语义投影」。
  - PDF 导出现在会识别 Mermaid fenced block，并输出 `Mermaid 图表：<diagramType>` 与图表内容摘要，避免在 PDF 中直接暴露 fenced code block。
  - PDF 导出现在会识别合法 `ai4se-visual` fenced block，复用共享 `parseStructuredVisual`，输出结构化可视化标题、列名和行值，避免客户看到原始 JSON。
  - 非法 `ai4se-visual` 会输出结构化可视化错误摘要，帮助定位产出物问题。
  - 普通代码块、Markdown 表格、分页和 DOCX 导出路径保持原行为。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx` 观察到 PDF 仍输出 Mermaid/JSON 原文导致断言失败，再实现后同命令通过；`npm run test -- --run src/__tests__/store.test.ts src/core/__tests__/docxExport.test.ts src/components/__tests__/ArtifactPane.test.tsx`；`npm run lint`；`npm run build`。
  - 剩余：PDF 仍未将 Mermaid 渲染为 SVG/图片，也未绘制结构化可视化表格边框；真正图形化 PDF 可作为后续高保真导出切片。
- 2026-06-19：完成第十五块 CGA「Artifact DOCX 表格高保真导出」。
  - Word 导出的 `.docx` 包新增 `word/styles.xml`，为标题和表格提供基础 OOXML 样式入口。
  - Markdown 表格不再作为 `模块 | 状态` 这类纯段落写入 Word，而是转换为真实 `w:tbl` / `w:tr` / `w:tc` 表格结构，便于客户在 Word 中继续编辑评分矩阵、风险矩阵、覆盖矩阵等专业产出物。
  - 表格单元格文本继续走 XML 转义，`<script>` 等 HTML 内容不会变成真实标签。
  - 验证：先运行 `npm run test -- --run src/core/__tests__/docxExport.test.ts` 观察到缺少 `word/styles.xml` 和真实表格结构导致断言失败，再实现后同命令通过；`npm run test -- --run src/core/__tests__/docxExport.test.ts src/components/__tests__/ArtifactPane.test.tsx`；`npm run lint`；`npm run build`；`git diff --check`。
  - 剩余：复杂列表编号、页眉页脚、Mermaid/结构化可视化图形嵌入、PDF Mermaid/SVG 图片级嵌入仍可作为后续切片。
- 2026-06-19：完成第十六块 CGA「Artifact 协作元数据服务端同步」。
  - 后端新增通用 artifact collaboration 持久化模型和共享 `PUT /api/agent/runs/<run_id>/artifact-collaboration`，可保存当前 run 的批注与章节锁。
  - `get_run_snapshot` 现在返回 `artifactComments` 与 `artifactSectionLocks`，历史会话恢复时不再丢失产出物批注和已确认章节锁。
  - 前端 `fetchRunSnapshot`、Zustand store 和 Workspace snapshot mock 已扩展协作字段；恢复 run 时会按当前 workflow stage 过滤并恢复批注/锁，避免跨工作流污染。
  - ArtifactPane 在有 `currentRunId` 时，新增/删除批注、锁定/解锁章节都会同步当前协作状态；无 runId 的本地草稿仍保持本地可用。
  - 验证：先运行 `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py::test_run_snapshot_returns_artifact_collaboration_state tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_collaboration_endpoint_replaces_state` 观察到缺少函数/路由失败；再运行 `npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts` 观察到 service/store 丢失协作字段失败；实现后运行 `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py`、`npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx src/pages/__tests__/Workspace.test.tsx`、`npm run lint`、`npm run build`、`git diff --check` 通过。
  - 剩余：PDF Mermaid/SVG 图片级嵌入、完整三方 merge / 块级合并轨迹仍可作为后续切片。
- 2026-06-19：完成第十七块 CGA「Artifact 模型生成遵守章节锁」。
  - 后端 `context_builder` 会把 run snapshot 中的 `artifactSectionLocks` 写入 `[已锁定产物章节]` 上下文块，明确提示模型“后续生成不得修改这些章节原文；如需调整，请先请用户解锁”。
  - 前端 `chatService` 在应用模型返回的 artifact update 前，会按当前 stage 的章节锁保护 Markdown section；如果模型改写锁定章节，最终右侧产物保留用户锁定的原文，同时允许未锁定章节正常更新。
  - 保护后的产物会进入 `artifactContent`、`stageArtifacts` 和最终 `artifactHistory`，避免后续阶段或回滚历史保存被模型改写污染。
  - 验证：先运行 `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_context_builder.py::test_build_run_context_prompt_includes_locked_artifact_sections` 观察到 prompt 缺少锁定章节失败；再运行 `npm run test -- --run src/services/__tests__/chatService.test.ts -t "should preserve locked artifact sections"` 观察到模型改写污染锁定章节失败；实现后运行 `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_context_builder.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py`、`npm run test -- --run src/services/__tests__/chatService.test.ts`、`npm run lint`、`npm run build`、`git diff --check` 通过。
  - 剩余：重复标题精确锚点、PDF Mermaid/SVG 图片级嵌入、完整三方 merge 轨迹仍可作为后续切片。
- 2026-06-19：完成第十八块 CGA「Artifact 批注回复与解决状态」。
  - Artifact 批注从单条静态备注升级为轻量协作线程，支持 `open/resolved` 状态、解决时间和多条回复。
  - 后端 artifact collaboration 状态会保存并恢复批注状态与回复，`PUT /api/agent/runs/<run_id>/artifact-collaboration` 和 run snapshot 继续复用同一个共享协作契约。
  - `init_db` 新增窄范围 schema upgrade，会为旧版 `agent_artifact_comments` 表补齐 `status`、`resolved_at_ms`、`replies_json` 三列，避免已有本地库升级后接口报错。
  - 前端批注面板新增 `未解决/已解决` 标识、`标记已解决/重新打开` 操作和回复输入区；这些操作会随现有协作状态同步到当前 server run。
  - 旧本地缓存中没有状态/回复字段的批注会被规范为 `open`、无回复，避免历史工作区恢复失败。
  - 验证：先运行 `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py::test_run_snapshot_returns_artifact_collaboration_state tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_collaboration_endpoint_replaces_state` 和 `npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx` 观察到缺少批注状态/回复失败；再运行 `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_api.py::test_init_db_upgrades_existing_artifact_comment_table` 观察到旧表不会自动补列失败；实现后运行 `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_api.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py`、`npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx`、`npm run lint`、`npm run build`、`git diff --check` 通过。
  - 剩余：PDF Mermaid/SVG 图片级嵌入、完整三方 merge / 块级合并轨迹仍可作为后续切片。
- 2026-06-19：完成第十九块 CGA「Artifact 批注正文选区锚点」。
  - 用户在右侧 Artifact 预览区选中文字后新增批注，批注摘录会优先使用选中文本，不再只能引用文档开头的默认正文行。
  - 批注新增 `anchorText` 元数据，前端 store、服务端 collaboration API 和 run snapshot 都会保存/恢复该字段；旧批注缺少该字段时兼容为 `null`。
  - `init_db` 的旧表升级补充 `anchor_text` 列，避免已有 `agent_artifact_comments` 表升级后无法保存选区锚点。
  - 当前实现只做轻量文本锚点和摘录，不做 DOM 高亮、滚动定位或 Markdown source map，避免把协作体验切片扩大成复杂编辑器能力。
  - 验证：先运行 `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_api.py::test_init_db_upgrades_existing_artifact_comment_table tools/new-agents/backend/tests/test_run_persistence.py::test_run_snapshot_returns_artifact_collaboration_state tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_collaboration_endpoint_replaces_state` 和 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts src/services/__tests__/runSnapshotService.test.ts` 观察到缺少 `anchorText` / `anchor_text` 与选区摘录失败；实现后运行同一前端目标测试、`.venv/bin/python -m pytest tools/new-agents/backend/tests/test_api.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py`、`npm run lint`、`npm run build`、`git diff --check` 通过。
  - 剩余：PDF Mermaid/SVG 图片级嵌入、完整三方 merge 轨迹仍可作为后续切片。
- 2026-06-20：完成第二十块 CGA「Artifact 服务端审阅轨迹」。
  - 后端新增通用 `AgentArtifactAuditEvent`，记录 run/stage 维度的 artifact 活动，不引入 Lisa/Alex 或 workflow 专属审计分支。
  - 人工保存 artifact 成功后记录 `artifact_saved`，协作状态替换成功后记录 `collaboration_updated`；`get_run_snapshot` 返回 `artifactAuditEvents`，历史 run 恢复后不会丢失最近活动。
  - 前端 `fetchRunSnapshot`、store 和 Workspace snapshot mock 已扩展活动轨迹字段；旧 snapshot 缺少该字段时兼容为空数组。
  - ArtifactPane 的 `历史版本` 面板新增 `活动轨迹` 区块，展示当前阶段最近活动，不新增顶栏按钮，保持操作入口收敛。
  - 验证：先运行 `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py::test_run_snapshot_returns_artifact_audit_events tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_update_endpoint_records_manual_artifact_version tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_collaboration_endpoint_replaces_state` 和 `npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx` 观察到缺少 `artifactAuditEvents`、store getter 和历史面板活动展示失败；实现后运行 `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py`、`npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx src/pages/__tests__/Workspace.test.tsx`、`npm run lint`、`npm run build`、`git diff --check` 通过。
  - 剩余：PDF Mermaid/SVG 图片级嵌入、完整三方 merge 轨迹仍可作为后续切片。
- 2026-06-20：完成第二十一块 CGA「Artifact 批注锚点定位高亮」。
  - 有正文锚点的 Artifact 批注新增 `定位正文` 操作，用户可从批注线程直接跳回右侧产出物中的对应内容。
  - 定位会自动切换到预览模式，并在现有共享 Markdown 渲染组件中高亮首个匹配文本，不新增 workflow 或 agent 专属渲染分支。
  - 高亮只消费当前批注的轻量 `anchorText`，不引入 Markdown source map、复杂编辑器或多匹配选择器，保持协作体验轻量可控。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "highlights anchored artifact text"` 观察到缺少 `定位正文` 按钮失败；实现后同命令通过，并运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx` 通过。
  - 剩余：PDF Mermaid/SVG 图片级嵌入、完整三方 merge 轨迹仍可作为后续切片。
- 2026-06-20：完成第二十二块 CGA「Artifact PDF 结构化表格绘制」。
  - PDF 导出从纯文本行投影扩展为轻量 document 模型，会记录合法 `ai4se-visual` 的列、行和起始位置。
  - 导出 PDF 时，结构化可视化会在 content stream 中绘制基础表格外框、列分隔线和行分隔线，让风险矩阵、覆盖矩阵、行动看板等产出更接近可交付文档。
  - 原有结构化可视化标题、列名和行值文本仍保留，PDF 继续具备可搜索文本，也兼容既有 Mermaid 文本摘要和 Markdown 导出路径。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "draws structured visual tables"` 观察到缺少 PDF 绘制操作失败；实现后同命令通过，并运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx` 通过。
  - 剩余：PDF Mermaid/SVG 图片级嵌入、完整三方 merge 轨迹仍可作为后续切片。
- 2026-06-20：完成第二十三块 CGA「Artifact PDF 跨页表格片段绘制」。
  - 长 `ai4se-visual` 表格导出 PDF 时，绘制逻辑会用结构化表格行范围和当前 PDF 页面行范围求交集。
  - 每个包含结构化表格行的页面都会绘制当前页可见片段的外框、列分隔线和行分隔线，避免第二页只剩纯文本。
  - 保留原有文本分页、可搜索文本、短表格绘制和 Mermaid 文本摘要路径，不引入新的 PDF 排版依赖。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "draws structured visual table borders"` 观察到两页 PDF 只有一个表格矩形失败；实现后同命令通过，并运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx` 通过。
  - 剩余：PDF Mermaid/SVG 图片级嵌入、完整三方 merge 轨迹仍可作为后续切片。
- 2026-06-20：完成第二十四块 CGA「Artifact 冲突行级合并轨迹」。
  - Store 新增本地 `addArtifactAuditEvent` action，复用既有 Artifact 活动轨迹数据结构，支持前端交互产生的审计事件。
  - 保存冲突对比中，用户点击 `采纳到草稿` 会记录 `artifact_merge_line_accepted`，点击 `丢弃此行` 会记录 `artifact_merge_line_discarded`。
  - 历史版本面板继续使用现有 `活动轨迹` 区块展示这些合并决策，不新增顶栏入口，保持 Artifact 操作收敛。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "records accepted conflict merge lines"` 观察到历史面板缺少合并轨迹失败；实现后同命令通过，并运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts` 通过。
  - 剩余：PDF Mermaid/SVG 图片级嵌入、完整三方 merge / 块级合并轨迹仍可作为后续切片。
- 2026-06-20：完成第二十五块 CGA「Artifact 冲突新增块丢弃」。
  - 冲突对比会识别连续的草稿新增行；当连续新增行超过 1 行时，在块起始行提供 `丢弃块` 操作。
  - 点击 `丢弃块` 会一次从编辑草稿中移除整个连续新增块，减少用户逐行清理多行误改的操作成本。
  - 块级丢弃会记录 `artifact_merge_block_discarded` 活动轨迹，历史面板可回看人工合并决策。
  - 现有逐行 `采纳` / `丢弃` 保持可用，不改变服务端保存或冲突 API。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "discards a contiguous draft-only block"` 观察到缺少 `丢弃变更块` 操作失败；实现后同命令通过，并运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts` 通过。
  - 剩余：PDF Mermaid/SVG 图片级嵌入、完整三方 merge / 块级采纳与修改块合并仍可作为后续切片。
- 2026-06-20：完成第二十六块 CGA「Artifact 冲突新增块采纳」。
  - 冲突对比中的连续草稿新增块现在会在块起始行提供 `采纳块` 操作。
  - 点击 `采纳块` 会以服务端当前版本为基准，把该新增块中尚未存在于服务端的行追加到编辑草稿，减少多行有效补充需要逐行采纳的问题。
  - 块级采纳会记录 `artifact_merge_block_accepted` 活动轨迹，历史面板可回看人工合并决策。
  - 现有逐行 `采纳` / `丢弃` 和 `丢弃块` 保持可用，不改变服务端保存或冲突 API。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "accepts a contiguous draft-only block"` 观察到缺少 `采纳变更块` 操作失败；实现后同命令通过，并运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts` 通过。
  - 剩余：PDF Mermaid/SVG 图片级嵌入、完整三方 merge / 修改块合并仍可作为后续切片。
- 2026-06-20：完成第二十七块 CGA「Artifact 冲突修改块采纳」。
  - 冲突对比现在会识别相邻的服务端删除块与草稿新增块，将其视为一组修改块。
  - 在修改块的草稿起始行提供 `采纳修改块` 操作，减少用户逐行采纳导致内容被追加到末尾的问题。
  - 点击 `采纳修改块` 会以服务端当前版本为基准，原位用用户草稿修改块替换服务端对应修改块，并保留服务端其他位置的更新。
  - 修改块采纳会记录 `artifact_merge_block_modified_accepted` 活动轨迹，历史面板可回看人工合并决策。
  - 现有逐行 `采纳` / `丢弃`、新增块 `采纳块` / `丢弃块` 保持可用，不改变服务端保存或冲突 API。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "accepts a modified conflict block"` 观察到缺少 `采纳修改块` 操作失败；实现后同命令通过。
  - 剩余：PDF Mermaid/SVG 图片级嵌入、完整三方 merge / 修改块保留与更复杂冲突解析仍可作为后续切片。
- 2026-06-20：完成第二十八块 CGA「Artifact PDF Mermaid 矢量投影」。
  - PDF 导出现在会对简单 `flowchart` / `graph` Mermaid 代码块提取节点和边，并在 PDF content stream 中绘制节点矩形、连接线和简化箭头。
  - Mermaid 节点标签会作为可搜索文本保留在 PDF 中，原有 Mermaid 类型摘要和源边描述也继续保留，避免图形化后丢失可读性。
  - 无法解析或非 flowchart/graph 的 Mermaid 仍走原有文字摘要降级路径，不阻断 PDF 导出。
  - 实现复用现有 Artifact PDF 导出路径，不新增 workflow/agent 专属导出分支，也不引入浏览器截图或异步 Mermaid runtime。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "draws Mermaid flowcharts as vector"` 观察到 PDF 只有文本摘要、缺少图形绘制命令失败；实现后同命令通过。
  - 剩余：完整三方 merge / 修改块保留与更复杂冲突解析、复杂 Mermaid/SVG 高保真嵌入仍可作为后续增强切片。
- 2026-06-20：完成第二十九块 CGA「Artifact 冲突修改块保留服务端」。
  - 冲突对比中的修改块现在除了 `采纳修改块` 外，还提供 `保留服务端` 操作。
  - 点击 `保留服务端` 会以服务端当前版本作为编辑草稿，保留服务端修改块和服务端其他更新，放弃用户草稿中的对应修改。
  - 修改块保留会记录 `artifact_merge_block_modified_kept` 活动轨迹，历史面板可回看人工合并决策。
  - 现有逐行 `采纳` / `丢弃`、新增块 `采纳块` / `丢弃块`、修改块 `采纳修改块` 保持可用，不改变服务端保存或冲突 API。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "keeps a server modified conflict block"` 观察到缺少 `保留服务端修改块` 操作失败；实现后同命令通过。
  - 剩余：完整三方 merge 的自动化语义合并、更复杂冲突解析、复杂 Mermaid/SVG 高保真嵌入仍可作为后续增强切片。
- 2026-06-20：完成第三十块 CGA「Artifact 冲突非重叠插入自动合并」。
  - 保存冲突现在会检测旧版本行是否仍按顺序存在于服务端版本和用户草稿；只有双方都只是插入内容时，才显示 `自动合并非重叠变更`。
  - 点击后编辑草稿会同时保留服务端插入和用户草稿独有插入，减少安全场景下逐行/逐块处理成本。
  - 自动合并会记录 `artifact_auto_merge_applied` 活动轨迹，历史面板可回看系统辅助合并决策。
  - 当时删除、改写、移动或锚点无法可靠匹配时不会自动合并，继续使用现有手工冲突处理能力，不改变服务端保存或冲突 API。
  - 同步更新 `docs/strategy/goal-mode-playbook.md`，明确后续多子智能体开发采用“可写 worker 独立 worktree、主 Agent 统一集成”的方式。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "auto-merges non-overlapping"` 观察到缺少 `自动合并非重叠变更` 入口失败；实现后同命令通过。
  - 剩余：更完整三方 merge 的删除/改写/移动语义、复杂 Mermaid/SVG 高保真嵌入仍可作为后续增强切片。
- 2026-06-20：完成第三十一块 CGA「Artifact 冲突安全删除自动合并」。
  - 保存冲突的自动合并从插入-only 扩展到“服务端只插入、用户草稿删除旧行并可插入补充”的安全场景。
  - 点击 `自动合并非重叠变更` 后，编辑草稿会同时保留服务端新增内容、用户补充内容，并应用用户删除旧行的意图。
  - 自动合并继续记录 `artifact_auto_merge_applied` 活动轨迹，不改变 UI 文案、服务端保存 API 或既有逐行/块级手工冲突处理。
  - 为避免重复旧行导致锚点不可判定，若草稿存在删除且旧版中存在重复非空行，则不会显示自动合并入口，继续交给人工对比处理。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "does not auto-merge draft deletions"` 观察到重复旧行仍显示自动合并入口失败；实现保守降级后同命令通过；`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx` 45/45 通过。
  - 剩余：更复杂的改写/移动语义自动合并、复杂 Mermaid/SVG 高保真嵌入仍可作为后续增强切片。
