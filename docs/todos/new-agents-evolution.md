# New Agents 演进 Todo

本文记录 `tools/new-agents/` 的长期演进 backlog。目标模式启动时应读取本文，并在完成主目标之外持续消化高优先级 todo。

## 使用规则

- `P0`：影响后续能力评估、专业可信度、主链路质量或目标模式选题的优先事项。
- `P1`：直接提升 Lisa / Alex 业务价值或平台扩展能力的事项。
- `P2`：体验、生态和增强型能力，等待 P0/P1 稳定后推进。
- 每次目标模式完成相关工作后，应更新对应条目的状态、证据和后续拆分。
- 这些 todo 不是一次性执行计划；进入实现前仍需按 `docs/strategy/goal-mode-playbook.md` 做 Current State Gap Analysis、spec、plan 和验证。

## P0 高优先级

### 1. 建立专业大模型 E2E 评判体系

**目标**：把浏览器级工作流测试中的可选 LLM judge 演进成衡量 New Agents 能力的核心评估手段。评判不只看最终 artifact，还要覆盖完整交互过程、专业方法使用、用户引导质量和信息重点表达。

**待办**：

- 扩展 `tests/e2e/new_agents_browser/` 的评判输入，从“最终产物文本”扩展为“完整会话轨迹 + 阶段切换 + 每阶段产物 + 最终产物”。
- 设计 Lisa 测试专家视角评判 rubric：需求澄清、风险识别、测试策略、测试用例、覆盖追溯、边界条件、异常路径、非功能需求、可执行性。
- 设计 Alex 业务分析师视角评判 rubric：问题定义、用户画像、用户旅程、价值主张、需求拆解、优先级、验收标准、业务闭环。
- 设计交互体验评判 rubric：对话引导是否清晰、是否主动说明使用的方法、是否突出关键风险/结论、是否避免大段重复 artifact、是否能帮助用户做确认和补充。
- 设计可视化评判 rubric：图表是否存在、是否适合当前阶段、是否能帮助快速理解重点、是否与正文一致、是否可渲染。
- 输出严格 JSON verdict，至少包含 `pass`、`score`、`dimension_scores`、`issues`、`evidence`、`recommendations`。
- 保持默认 E2E 确定性测试不依赖模型；LLM judge 继续通过显式环境变量启用。
- 将评判结果纳入后续目标模式收尾证据：当改动影响工作流、prompt、artifact 或 UI 引导时，应说明是否运行了 judge，未运行则说明原因。

**验收证据**：

- 浏览器 E2E 能收集并传入完整工作流轨迹。
- judge 能按 Lisa / Alex 两类专业角色输出分维度评分。
- 至少覆盖 Lisa `test-design` 和 Alex `value-discovery` 两条完整流程。

### 2. 系统性审视并升级所有工作流产出物

**目标**：从专业测试人员和专业业务分析人员视角重新审视每个 workflow 的 artifact 是否合理、完整、可执行、可复用。

**待办**：

- 为 Lisa 工作流建立专业 artifact 标准：测试设计、需求评审、故障复盘分别定义必备章节、专业方法、质量门槛和可视化要求。
- 为 Alex 工作流建立专业 artifact 标准：创意头脑风暴、价值发现，以及后续 PRD / 用户故事方向分别定义方法论、结构和判断标准。
- 对现有 `WORKFLOWS`、阶段 prompt、template、后端 artifact heading contract 做逐项差距分析。
- 明确哪些内容属于 prompt，哪些属于 artifact contract，哪些应由前端可视化组件承担，避免只靠提示词维持质量。
- 给每个阶段补“专业方法显性表达”：让左侧对话明确说明本轮使用了什么分析方法、为什么用、得到什么关键结论。

**验收证据**：

- 每个在线 workflow 都有专业产物审计结论。
- 每个阶段都有明确的方法论、产物结构和质量校验点。
- 评判体系能检测“方法论缺失”和“产物空洞”。

### 3. 建立产出物可视化增强规范

**目标**：让用户不只阅读枯燥 Markdown 报告，而是能通过图表、矩阵、时间线、看板、评分卡快速理解重点。

**待办**：

- 恢复并制度化 Mermaid 使用：为每个 workflow/stage 定义推荐图形，如风险矩阵、测试金字塔、测试点拓扑、时间线、5-Why 链路、用户旅程、路线图。
- 评估 Mermaid 之外的可视化块：例如风险热力图、需求-风险-用例追溯矩阵、用户旅程组件、评分卡、行动项看板。
- 设计结构化可视化协议，避免模型直接手写复杂 HTML；优先让模型输出结构化数据，前端用共享组件渲染。
- 将可视化要求纳入 artifact contract 和 LLM judge rubric。
- 保持所有可视化走共享渲染管线，不为 Lisa / Alex 建立独立渲染分支。

**验收证据**：

- 每个核心工作流至少有一个阶段具备稳定可视化输出。
- 可视化内容能被 E2E 或组件测试验证。
- LLM judge 能评价可视化是否提升理解，而不只是是否出现图表。

## P1 中优先级

### 4. 共享 workflow manifest

**目标**：将 workflow、stage、persona、artifact contract、listing、slug、可视化要求收敛为共享配置源，降低前后端漂移风险。

**待办**：

- 设计 manifest schema。
- 从 manifest 生成或加载前端 `WORKFLOWS` 与后端 `WORKFLOW_STAGES` / artifact contract。
- 保留现有 `test_workflow_contract_sync.py` 作为迁移护栏。

### 5. 服务端会话与产物持久化

**目标**：从浏览器 localStorage 过渡到服务端 run/session/artifact/version 持久化，支持恢复、审计、分享和评判数据采集。

**待办**：

- 设计 `agent_runs`、`agent_messages`、`agent_artifacts`、`artifact_versions` 数据模型。
- 保持 typed SSE 主链路不分叉。
- 为 LLM judge 提供可复用的会话轨迹来源。

### 6. 上下文管理与摘要机制

**目标**：替代前端简单拼接历史和截断前序产物的方式，建立服务端 context builder。

**待办**：

- 分层保存用户补充、阶段关键结论、产物摘要和决策。
- 明确截断策略和可见告警。
- 让模型能基于摘要稳定跨阶段推进。

### 7. Lisa 测试资产闭环

**目标**：让 Lisa 从报告生成升级为测试资产管理助手。

**待办**：

- 测试点库、用例版本、需求覆盖追溯、风险矩阵和评审问题闭环。
- 支持导出给 intent-tester 或其他测试管理工具，但短期不改 intent-tester 主链路。

### 8. Alex 到 Lisa 的跨智能体接力

**目标**：形成从价值发现 / PRD / 用户故事到需求评审 / 测试设计的连续流程。

**待办**：

- 先以 workflow 配置表达接力，不新增 agent-specific runtime。
- 明确 Alex 产物如何作为 Lisa 前序上下文。
- 用 E2E 和 judge 验证跨角色专业连续性。

### 9. 规则与架构文档持续校准机制

**目标**：让 `AGENTS.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、`docs/DESIGN_PRINCIPLES.md`、`docs/component-inventory.md` 等规则和架构文档持续反映当前代码，而不是长期滞后于实现。

**待办**：

- 基于当前代码、测试、Docker 配置、New Agents 运行时和工作流配置，做一次批量文档校准审计。
- 更新已经过期的架构、API、测试、组件和 Agent 工作规则描述，特别是 New Agents typed Agent Runtime、共享工作流基础设施、LLM judge、`docs/todos/` 和 goal mode 读取规则。
- 建立目标模式文档同步检查清单：当改动影响架构、API、测试门禁、工作流契约、Agent 规则、部署方式或长期 todo 时，必须判断并更新对应文档。
- 在 `docs/strategy/goal-mode-playbook.md` 中强化文档校准原则：目标模式每轮收尾不仅更新 spec/plan，也要更新稳定事实源；发现过期文档时应写入 todo 或直接修正。
- 为批量校准保留明确证据：列出校准过的文件、对应代码事实、未校准原因和后续候选。

**验收证据**：

- 完成一次当前代码状态驱动的文档批量校准。
- 目标模式 playbook 明确要求在相关变更后同步稳定规则/架构文档。
- 后续目标模式可以从 `docs/todos/` 或 playbook 中发现并持续消化文档过期问题。

## P2 后续增强

### 10. Artifact 协作体验

- 局部重写。
- 章节锁定。
- 版本 diff。
- 批注。
- 接受 / 拒绝变更。
- Word / PDF / Markdown 多格式导出。

### 11. 运行时可观测性

- 记录 run id、workflow、stage、模型、耗时、错误码、contract retry 次数、token 估算。
- 提供基本统计视图，帮助发现高失败率阶段和低质量输出。

### 12. 模型配置与供应商治理

- 默认 LLM 配置管理 UI。
- 密钥轮换。
- 模型可用性检测。
- 供应商错误归因。
- 按环境启用不同模型。
