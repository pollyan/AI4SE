# New Agents 在线工作流 Artifact 专业审计

> 日期: 2026-06-19
> 范围: `tools/new-agents/` 当前在线 workflow artifact 专业性基线审计
> 事实源: `tools/new-agents/frontend/src/core/workflows.ts`、`tools/new-agents/backend/agent_contracts.py`、`docs/todos/new-agents-evolution.md`

## 1. 审计结论摘要

当前 New Agents 已具备较好的结构化产出物基础：5 个在线 workflow 都有前端 stage/template 配置，后端 `REQUIRED_ARTIFACT_HEADINGS` 也覆盖了全部 workflow/stage，能够机械拦截缺少关键标题的 artifact。

主要缺口不在“有没有文档结构”，而在三个层面：

- 专业方法显性不足：部分阶段标题能约束结构，但不能证明模型真的使用了专业方法，例如需求评审维度、业务分析方法、测试覆盖策略和复盘根因方法的质量。
- 可执行性约束不足：表格是否包含负责人、优先级、验收标准、覆盖关系、下一步动作等执行字段，当前大多依赖 prompt，不由契约机械保护。
- 可视化和评判闭环不足：已有矩阵、拓扑、时间线、鱼骨图、Lean Canvas 等迹象，但缺少跨 workflow 的可视化规范和 judge 维度映射。

后续升级建议按“评判标准 -> 单 workflow contract/prompt -> E2E/judge 验证”的顺序推进，不建议一次性重写所有 workflow。

## 2. 全局审计维度

后续每个 workflow 的 artifact 升级应同时满足以下维度：

| 维度 | 判断问题 | 推荐证据 |
| --- | --- | --- |
| 专业方法 | 产物是否显式使用该领域方法，而不是只给通用结论 | stage prompt、artifact contract、judge dimension |
| 可执行性 | 用户能否直接评审、分派、执行或导出使用 | 表格字段、行动项、验收标准、追溯关系 |
| 阶段边界 | 当前阶段是否只处理当前目标，不提前生成后续阶段内容 | typed SSE contract、stage_action、E2E |
| 信息继承 | 后续阶段是否吸收前序阶段关键结论 | E2E trace、system prompt integration |
| 可视化 | 图表/矩阵是否帮助理解，而不是装饰 | Mermaid / structured visual block、组件测试、judge |
| 左右栏职责 | chat 是否只做摘要、方法说明和引导，artifact 是否承载完整正文 | backend contract、frontend state tests |

## 3. Workflow 审计

### 3.1 `TEST_DESIGN` 测试设计

**专业目标**：帮助测试负责人从需求澄清到测试策略、测试用例和交付文档形成完整测试设计资产。

**当前 contract 摘要**：

- `CLARIFY`: 需求分析文档、被测系统与边界、系统交互与核心链路、待澄清问题、隐式需求与非功能性考量。
- `STRATEGY`: 测试策略蓝图、质量目标、风险分析、风险矩阵、风险明细、技术选型、测试分层、测试金字塔、测试点拓扑。
- `CASES`: 测试用例集、用例统计、用例清单、测试点覆盖追溯。
- `DELIVERY`: 测试设计文档、文档信息、需求分析、测试策略、测试用例、验收标准。

**主要差距**：

- `CASES` 只要求“用例清单”，没有机械要求用例字段包含前置条件、操作步骤、预期结果、优先级、需求/风险追溯。
- `STRATEGY` 有风险矩阵和测试点拓扑，但没有要求风险评分口径、准入准出、环境/数据策略和自动化分层建议。
- `DELIVERY` 是汇总文档，但没有要求变更记录、评审结论、未测风险和上线决策。
- 左侧 chat 是否显式说明 FMEA、测试金字塔、边界值、异常路径等方法，目前主要依赖 prompt 和模型行为。

**推荐后续切片**：

1. 已完成 `TEST_DESIGN/CASES` artifact contract 首轮收紧，要求用例字段和追溯字段。
2. 补 `TEST_DESIGN/STRATEGY` 的风险评分和准出标准字段。
3. 将 Lisa judge 的测试专家维度与 `TEST_DESIGN` E2E trace 对齐，检测方法论缺失。

### 3.2 `REQ_REVIEW` 需求评审

**专业目标**：从测试人员视角审查需求完整性、可测试性、边界、异常路径和上线风险，产出可行动的问题清单和评审报告。

**当前 contract 摘要**：

- `REVIEW`: 需求评审问题清单、评审概要、问题统计。
- `REPORT`: 需求评审报告、评审结论、判定标准、评审信息、问题统计、待确认问题清单、P0/P1/P2 分组、评审意见签署。

**主要差距**：

- `REVIEW` contract 过薄，只约束概要和统计，没有要求问题字段，例如问题 ID、严重级别、影响范围、证据、建议修改、责任方。
- 没有机械要求覆盖可测试性、完整性、一致性、边界、异常、非功能、安全/合规等评审维度。
- `REPORT` 有 P0/P1/P2 分组，但缺少“是否准入下一阶段 / 是否阻塞研发 / 是否需要补需求”的决策口径。
- 评审意见签署存在标题，但缺少签署角色、日期、结论和遗留风险字段要求。

**推荐后续切片**：

1. 已完成 `REQ_REVIEW/REVIEW` contract 首轮升级，要求结构化问题字段：`问题描述`、`优先级`、`所属需求章节`、`影响范围`、`证据/依据`、`建议`、`责任方/确认人`。
2. 已增加后端 contract 测试，拒绝只给标题不含问题字段的空洞评审清单。
3. 将 `REPORT` 的判定标准和签署信息改成可执行决策结构。

### 3.3 `INCIDENT_REVIEW` 故障复盘

**专业目标**：引导用户还原故障事实、定位根因、制定防复发措施，并形成可追踪的复盘报告。

**当前 contract 摘要**：

- `TIMELINE`: 故障复盘报告、事件概要、事件时间线、事实摘要、参与人员、待补充信息。
- `ROOT_CAUSE`: 根因分析、5-Why 分析链、原因鱼骨图、根因结论。
- `IMPROVEMENT`: 报告信息、事件还原、根因分析、改进措施、改进优先级分布、行动清单、防复发检查清单、经验教训、签署确认。

**主要差距**：

- `TIMELINE` 未要求影响范围、发现方式、恢复时间、用户影响、监控告警和关键证据来源。
- `ROOT_CAUSE` 有 5-Why 和鱼骨图标题，但没有要求区分直接原因、根本原因、促成因素和未证实假设。
- `IMPROVEMENT` 有行动清单，但没有机械要求 owner、截止时间、验证方式、优先级、状态和复盘追踪机制。
- 可视化要求分散：时间线、鱼骨图适合可视化，但当前没有统一可视化协议或 judge 检查。

**推荐后续切片**：

1. 已完成 `INCIDENT_REVIEW/IMPROVEMENT` 行动项字段首轮升级，优先保证防复发措施可执行。
2. 为 `TIMELINE` 增加影响范围和证据字段。
3. 把时间线和鱼骨图纳入可视化规范候选。

### 3.4 `IDEA_BRAINSTORM` 创意头脑风暴

**专业目标**：从模糊痛点出发，通过问题定义、创意发散、收敛评估和概念简报形成可沟通的产品概念。

**当前 contract 摘要**：

- `DEFINE`: 问题域分析、问题假设、目标用户画像、问题域全景、问题-用户-场景匹配、约束与边界、反向验证。
- `DIVERGE`: 创意发散、发散全景图、创意卡片库。
- `CONVERGE`: 收敛聚焦、决策矩阵、ICE 评估表、整合演进路径。
- `CONCEPT`: 产品概念简报、定位声明、Lean Canvas、MVP 功能分布、核心增长漏斗、Pre-mortem 风险分析、下一步行动。

**主要差距**：

- `DIVERGE` 没有要求创意数量、分类、差异化来源、风险假设和用户价值假设。
- `CONVERGE` 有 ICE 评估，但没有要求评分口径、权重、淘汰理由和合并逻辑。
- `CONCEPT` 结构较强，但缺少实验验证计划、目标指标和最小验证路径。
- Alex 的左侧 chat 是否说明发散/收敛方法，当前没有机械评估。

**推荐后续切片**：

1. 已完成 `IDEA_BRAINSTORM/CONVERGE` 首轮升级，要求评分口径、淘汰理由和推荐方案。
2. 为 `CONCEPT` 增加实验验证计划和成功指标字段。
3. 用 Alex judge 检测发散质量、收敛依据和概念可验证性。

### 3.5 `VALUE_DISCOVERY` 价值发现

**专业目标**：把已有产品方向系统化梳理为价值定位、用户画像、用户旅程和需求蓝图。

**当前 contract 摘要**：

- `ELEVATOR`: 价值定位分析、产品核心定位、目标用户概览、独特价值主张、商业可行性初判、60 秒电梯演讲。
- `PERSONA`: 用户画像分析、主要用户画像、基础特征、行为特征、需求动机、核心痛点、用户优先级排序。
- `JOURNEY`: 用户旅程分析、用户旅程地图、关键阶段详细分析、痛点优先级排序、核心机会点、产品切入策略。
- `BLUEPRINT`: 需求蓝图、文档信息、产品概述、产品愿景、定位声明、核心价值、目标用户、核心需求、核心流程、成功指标、MVP 范围与计划、风险评估。

**主要差距**：

- `ELEVATOR` 未要求目标用户、痛点、替代方案、差异化价值和商业假设之间的因果闭环。
- `PERSONA` 要求了画像结构，但没有要求证据来源、场景频率、购买/使用决策和反画像。
- `JOURNEY` 有旅程地图标题，但缺少阶段、触点、任务、痛点、情绪、机会点和指标字段的机械约束。
- `BLUEPRINT` contract 覆盖广，但 `需求蓝图` 不是严格 H1 标题要求，且缺少需求验收标准字段。

**推荐后续切片**：

1. 已完成 `VALUE_DISCOVERY/JOURNEY` 首轮升级，把用户旅程地图变成可评估结构。
2. 升级 `BLUEPRINT`，要求每个 P0/P1 需求包含验收标准和成功指标。
3. 将 Alex judge 的业务分析师维度映射到 `VALUE_DISCOVERY` E2E trace。

## 4. 推荐推进顺序

1. 已完成 `REQ_REVIEW/REVIEW` 问题清单字段收紧：当前 contract 最薄，最容易出现“标题完整但内容空洞”。
2. 已完成 `TEST_DESIGN/CASES` 用例字段收紧：用户价值直接，且和 Lisa 测试专家定位强相关。
3. 已完成 `VALUE_DISCOVERY/JOURNEY` 用户旅程结构化：支撑 Alex 业务分析质量。
4. 已完成 `INCIDENT_REVIEW/IMPROVEMENT` 行动项字段收紧：让复盘结果可执行。
5. 已完成 `IDEA_BRAINSTORM/CONVERGE` 评分口径收紧：让创意收敛有明确依据。

以上 5 个首轮 contract 收紧切片已完成。后续可继续推进各 workflow 的第二轮增强项，例如 `TEST_DESIGN/STRATEGY` 风险评分和准出标准、`REQ_REVIEW/REPORT` 可执行决策结构、`INCIDENT_REVIEW/TIMELINE` 影响范围和证据字段、`IDEA_BRAINSTORM/CONCEPT` 实验验证计划，以及 `VALUE_DISCOVERY/BLUEPRINT` P0/P1 验收标准和成功指标。

每个后续切片都应同时更新：

- 后端 `REQUIRED_ARTIFACT_HEADINGS` 或新增更细 contract。
- 对应 frontend template / prompt。
- 契约测试或 E2E/judge 测试。
- `docs/todos/new-agents-evolution.md` 进展记录。
