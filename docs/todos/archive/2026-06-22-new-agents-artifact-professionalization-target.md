# New Agents 产出物专业化目标状态

## 状态

- 类型：目标模式输入文档
- 范围：`tools/new-agents/` 全部 workflow 与 stage artifact
- 当前状态：待目标模式消化
- 产出目标：为后续按 workflow、按 artifact 的专业化重构提供统一目标状态、扫描提示词和规格模板

## 背景判断

当前 New Agents 的核心专业度主要由右侧产出物决定。现有 artifact template 已经具备章节框架、Markdown 表格、Mermaid 和 `ai4se-visual` 的基础能力，但整体仍偏“章节级模板”，不足以稳定牵引模型产出专业测试人员、产品经理、复盘专家可直接评审和继续工作的基线文档。

本轮不开发新的前端可视化控件。新的看板、地图、矩阵等专属渲染属于后续用户体验优化。本轮优先把产出物专业化做到位：即使仍以 Markdown 表格或通用 `ai4se-visual` 表格展示，也必须先定义清楚每个阶段应该产出什么、以什么格式产出、哪些字段必填、哪些内容必须被人工确认、什么条件下允许进入下一阶段。

## 目标状态总原则

### 1. Artifact 是专业工作文档，不是聊天摘要

每个阶段 artifact 都必须被设计为一份可被目标角色直接使用的工作文档：

- 测试人员可以据此继续拆测试点、设计用例、评估风险。
- 产品经理可以据此确认需求边界、业务规则、验收口径和优先级。
- 研发或架构人员可以据此确认系统边界、依赖契约、数据流和待澄清事项。
- 管理者可以据此判断阶段是否可推进、风险是否可接受、责任是否明确。

### 2. 模板必须定义内容和格式

不能只定义章节名称。每个章节都需要明确：

- 章节目的：该章节解决什么专业问题。
- 推荐格式：纯文本、bullet 列表、Markdown 表格、Mermaid、`ai4se-visual`、检查清单。
- 必填字段：表格列、ID 命名、优先级、状态、责任方、证据、验收标准等。
- 信息粒度：必须具体到模块、接口、角色、业务规则、边界值、状态、风险、测试点或可验证指标。
- 人机协作点：哪些内容允许 AI 基于合理假设补齐，哪些必须标注为待确认。
- 阶段门禁：哪些信息缺失时不得建议进入下一阶段。

### 3. 可视化优先服务理解，不做装饰

Mermaid 和结构化可视化的目标是降低理解成本，不是为了堆视觉效果。

规则：

- 每个 workflow 的第一个阶段 artifact 至少包含一个 Mermaid 图。
- Mermaid 必须表达该阶段的核心结构，例如系统边界、问题域、用户旅程、事件时间线、需求质量分布。
- 不接受装饰性 Mermaid。图中节点、边、阶段或象限必须对应正文中的真实内容。
- `ai4se-visual` 优先用于可校验、可导出、可追溯的结构化数据，例如风险看板、追溯矩阵、旅程地图、MVP 地图、路线图。
- 当前不新增前端可视化控件；如需更好的地图或看板渲染，作为第二阶段 UX 需求单独规划。

### 4. 产出物必须支持人机协作推进

每个 artifact 都要让用户知道：

- 哪些结论已确认。
- 哪些内容是 AI 假设。
- 哪些问题阻断下一阶段。
- 哪些问题可后续跟进但不阻断。
- 用户需要对哪些字段进行确认、修正或补充。

### 5. 差异继续沉入配置和契约

遵守 New Agents 架构原则：

- 保留共享 `/api/agent/runs/stream` typed Agent Runtime。
- 不新增 agent-specific runtime、transport、store、SSE/API path 或 bespoke rendering pipeline。
- 工作流差异优先进入 prompt/template、artifact contract、visualization contract、workflow manifest 和测试。
- 如果引入新的 artifact 质量要求，必须同步考虑后端 contract、前端 prompt/template、测试和 LLM judge 证据。

## 目标模式任务提示词

后续启动 Codex 目标模式时，可以直接使用以下提示词。

```text
请进入目标模式，围绕 New Agents 全部 workflow 的 artifact 专业化重构做第一轮 Current State Gap Analysis 和目标状态设计。本轮只做扫描、分析和文档设计，不修改运行时代码、prompt/template、contract 或测试。

输入文档：
docs/todos/refactor/2026-06-22-new-agents-artifact-professionalization-target.md

请扫描以下范围：
1. tools/new-agents/workflow_manifest.json
2. tools/new-agents/frontend/src/core/workflows.ts
3. tools/new-agents/frontend/src/core/prompts/**
4. tools/new-agents/backend/agent_contracts.py
5. tools/new-agents/backend/tests/test_workflow_contract_sync.py
6. tools/new-agents/frontend/src/core/structuredVisuals.ts
7. tools/new-agents/frontend/src/components/StructuredVisual.tsx
8. docs/api-contracts.md 中 New Agents artifact/runtime 相关内容

目标：
全面审视每个 workflow、每个 stage 的 artifact 当前状态，并以专业测试人员、专业产品经理、质量改进专家和目标用户视角，定义每个 artifact 的目标状态。

必须覆盖的 workflow/stage：
- TEST_DESIGN: CLARIFY, STRATEGY, CASES, DELIVERY
- REQ_REVIEW: REVIEW, REPORT
- VALUE_DISCOVERY: ELEVATOR, PERSONA, JOURNEY, BLUEPRINT
- IDEA_BRAINSTORM: DEFINE, DIVERGE, CONVERGE, CONCEPT
- INCIDENT_REVIEW: TIMELINE, ROOT_CAUSE, IMPROVEMENT

请重点回答：
1. 当前 artifact 是否足够专业、细致、可评审、可继续协作？
2. 当前 template 是否只定义了章节，还是定义了每个章节应包含的必要字段和格式？
3. 当前 artifact 是否能牵引模型持续补齐关键内容，而不是输出泛泛摘要？
4. 当前 artifact 是否能支持人机协作，例如区分已确认、待确认、AI 假设、阻断项和非阻断项？
5. 当前 artifact 是否有足够清晰的可视化表达，尤其是每个 workflow 第一阶段是否具备一个有实际认知价值的 Mermaid 图？
6. 当前 artifact contract 是否足以防止模型只输出空泛章节？
7. 哪些质量要求应该先进入 prompt/template，哪些应该进入后端 contract，哪些应该进入 LLM judge 或 E2E evidence？

产出要求：
请新增一份目标状态设计文档：
docs/todos/refactor/YYYY-MM-DD-new-agents-artifact-professionalization-design.md

文档必须包含：
1. 当前 artifact 体系总览。
2. 每个 workflow/stage 的当前问题清单。
3. 每个 workflow/stage 的目标 artifact 规格。
4. 每个 artifact 的章节结构、章节目的、推荐格式、必填字段、可视化要求、协作状态字段和阶段门禁。
5. 每个 workflow 的第一阶段 Mermaid 图建议。
6. 适合使用 `ai4se-visual` 的章节清单，明确当前只复用已有通用表格渲染，不开发新控件。
7. 后续按 workflow 重构的优先级建议。
8. LLM judge 评审维度和样例用例建议。
9. 不纳入本轮的事项，例如新可视化控件开发、大规模 UI 重构、Runtime 改造。

限制：
- 不修改运行时代码。
- 不直接改 prompt/template。
- 不直接改 backend contract。
- 不新增前端可视化组件。
- 不创建 agent-specific runtime、transport、state store、SSE/API path 或 bespoke rendering pipeline。
- 所有建议必须能在后续目标模式中拆成按 workflow、按 artifact 的薄切片。

输出风格：
- 用中文写。
- 以事实证据开头，引用具体文件路径。
- 区分“当前事实”“目标状态”“后续改造建议”。
- 不写空泛口号。
- 每个 artifact 的目标规格必须具体到段落和字段级别。
```

## Artifact 目标规格模板

后续目标状态设计文档中，每个 stage artifact 使用同一张规格表描述。

| 字段 | 说明 |
| --- | --- |
| Workflow | 例如 `TEST_DESIGN` |
| Stage | 例如 `CLARIFY` |
| Artifact 名称 | 面向用户展示的专业文档名称 |
| 目标角色 | 主要读者，例如测试负责人、产品经理、研发负责人、SRE |
| 专业用途 | 该 artifact 在真实工作流里承担什么决策或协作作用 |
| 当前问题 | 当前模板、提示词或 contract 的主要不足 |
| 目标章节 | 目标状态下必须包含的章节列表 |
| 章节格式 | 每章使用纯文本、bullet、表格、Mermaid、`ai4se-visual`、检查清单中的哪一种 |
| 必填字段 | 表格列、ID、优先级、状态、责任方、证据、验收标准等 |
| 可视化要求 | Mermaid 类型、`ai4se-visual` 类型、图表要表达的业务含义 |
| 协作状态 | 是否需要标注已确认、待确认、AI 假设、阻断、非阻断 |
| 阶段门禁 | 缺少哪些内容时不得请求进入下一阶段 |
| Contract 建议 | 哪些要求适合进入后端 required headings、visual contract 或 schema 校验 |
| LLM Judge 建议 | 后续如何用大模型评价专业度、完整性和可操作性 |

## 章节级规格模板

每个 artifact 的章节不只列标题，必须使用以下结构定义。

| 字段 | 说明 |
| --- | --- |
| 章节标题 | Markdown 标题，要求稳定、可校验 |
| 章节目的 | 为什么需要这一节 |
| 推荐格式 | 文本、bullet、表格、Mermaid、`ai4se-visual`、检查清单 |
| 必填内容 | 该章节必须出现哪些字段或结论 |
| 最低粒度 | 不能低于什么细节程度 |
| AI 可假设内容 | 模型可以基于上下文合理补全的内容 |
| 必须人工确认内容 | 必须标注待确认，不能直接当成事实的内容 |
| 不合格示例 | 哪类输出算空泛或不可用 |
| 合格示例摘要 | 用 1-2 句话描述合格输出应该长什么样 |

## 可视化选择规则

### Mermaid 适用场景

| 场景 | 推荐 Mermaid 类型 | 适用 artifact |
| --- | --- | --- |
| 系统边界、上下游依赖、核心链路 | `flowchart` | `TEST_DESIGN/CLARIFY`, `REQ_REVIEW/REVIEW` |
| 用户旅程和体验起伏 | `journey` | `VALUE_DISCOVERY/JOURNEY` |
| 问题域、产品结构、原因分类 | `mindmap` | `IDEA_BRAINSTORM/DEFINE`, `VALUE_DISCOVERY/BLUEPRINT`, `INCIDENT_REVIEW/ROOT_CAUSE` |
| 风险分布、价值可行性、创意评估 | `quadrantChart` | `TEST_DESIGN/STRATEGY`, `IDEA_BRAINSTORM/CONVERGE` |
| 时间线 | `timeline` | `INCIDENT_REVIEW/TIMELINE` |
| 分布统计 | `pie` | 用例分布、问题分布、改进措施分布 |

### `ai4se-visual` 适用场景

当前已有类型统一渲染为结构化表格。目标状态可以先使用这些类型，不开发新组件。

| 类型 | 推荐用途 |
| --- | --- |
| `traceability-matrix` | 需求、风险、测试点、用例之间的追溯 |
| `score-matrix` | 需求质量、价值主张、创意评估等多维评分 |
| `risk-board` | FMEA 风险、RPN、缓解策略、覆盖建议 |
| `action-board` | SMART 改进行动、负责人、期限、验证方式 |
| `journey-map` | 阶段、任务、触点、情绪、痛点、机会 |
| `coverage-map` | 交付文档中的需求到测试资产覆盖关系 |
| `priority-board` | P0/P1/P2 问题优先级和责任方 |
| `cause-map` | 5-Why 层级、回答、原因类型、证据 |
| `mvp-map` | MVP 模块、用户价值、验证指标、取舍理由 |
| `roadmap` | 版本、时间、核心功能、目标、成功指标 |

## 全量 workflow/stage 覆盖清单

后续目标状态设计必须逐项覆盖以下 artifact。

### TEST_DESIGN

| Stage | 当前 artifact | 目标侧重点 |
| --- | --- | --- |
| `CLARIFY` | 需求分析文档 | 从澄清摘要升级为测试分析基线文档，包含事实、边界、业务规则、异常链路、待确认问题、非功能需求和后续测试设计输入。 |
| `STRATEGY` | 测试策略蓝图 | 从策略摘要升级为风险驱动的测试策略，强化质量目标、FMEA、测试分层、测试点拓扑和资源取舍。 |
| `CASES` | 测试用例集 | 从用例表升级为可执行测试资产草案，强化前置条件、数据、步骤、断言、追溯和覆盖状态。 |
| `DELIVERY` | 测试设计文档 | 从拼接终稿升级为可交付评审文档，强化需求、风险、测试点、用例和验收状态闭环。 |

### REQ_REVIEW

| Stage | 当前 artifact | 目标侧重点 |
| --- | --- | --- |
| `REVIEW` | 需求评审问题清单 | 从问题清单升级为需求质量诊断报告，强化证据、影响、责任方、修订建议和测试风险。 |
| `REPORT` | 需求评审报告 | 从汇总报告升级为可签署评审结论，强化通过标准、阻断问题、处理承诺和复审条件。 |

### VALUE_DISCOVERY

| Stage | 当前 artifact | 目标侧重点 |
| --- | --- | --- |
| `ELEVATOR` | 价值定位分析 | 强化目标用户、痛点证据、差异化、商业可行性和 60 秒表达。第一阶段需补充 Mermaid 价值结构图。 |
| `PERSONA` | 用户画像分析 | 强化角色、行为、决策链、痛点证据、付费意愿和用户优先级。 |
| `JOURNEY` | 用户旅程分析 | 强化阶段、触点、情绪低谷、机会假设、成功指标和旅程地图。 |
| `BLUEPRINT` | 需求蓝图 | 强化需求优先级、用户故事、验收标准、MVP 范围、路线图和风险。 |

### IDEA_BRAINSTORM

| Stage | 当前 artifact | 目标侧重点 |
| --- | --- | --- |
| `DEFINE` | 问题域分析 | 强化问题真实性、证据、目标用户、场景、约束和失败假设。 |
| `DIVERGE` | 创意发散 | 强化创意来源、HMW、创意技术、差异化亮点和搁置理由。 |
| `CONVERGE` | 收敛聚焦 | 强化 ICE 评分依据、淘汰理由、合并逻辑、推荐方案和验证实验。 |
| `CONCEPT` | 产品概念简报 | 强化定位声明、Lean Canvas、MVP、增长漏斗、风险和下一步验证。 |

### INCIDENT_REVIEW

| Stage | 当前 artifact | 目标侧重点 |
| --- | --- | --- |
| `TIMELINE` | 故障复盘报告：事件还原 | 强化事实、时间线、影响量化、参与人员、缺失信息和事实/推测分离。 |
| `ROOT_CAUSE` | 故障复盘报告：根因分析 | 强化 5-Why 因果链、证据、原因分类、直接原因、根本原因和促成因素。 |
| `IMPROVEMENT` | 故障复盘报告：改进措施 | 强化 SMART 行动、责任、期限、验收标准、防复发检查清单和经验教训。 |

## LLM Judge 评审维度

后续每个 workflow 的重构都应考虑增加或更新 LLM judge。建议统一使用以下维度，再按 workflow 加权。

| 维度 | 评审问题 |
| --- | --- |
| 专业完整性 | 是否覆盖该阶段专业工作所需的关键内容？ |
| 信息粒度 | 是否具体到角色、模块、规则、接口、风险、测试点或指标？ |
| 可操作性 | 读者是否能据此继续评审、拆解、执行或决策？ |
| 可追溯性 | 需求、问题、风险、测试点、用例、行动之间是否有关联 ID 或明确引用？ |
| 协作清晰度 | 是否区分已确认、待确认、AI 假设、阻断项和非阻断项？ |
| 可视化有效性 | Mermaid 或 `ai4se-visual` 是否表达真实业务结构，而非装饰？ |
| 阶段门禁 | 是否明确说明哪些信息缺失会阻断下一阶段？ |
| 非空泛性 | 是否避免“提升效率”“加强管理”“优化体验”这类无证据、无边界、无验收口径的表述？ |

## 后续重构消化建议

建议目标模式后续按以下顺序消化，不要一次性改完所有 workflow。

1. `TEST_DESIGN/CLARIFY`：用户当前痛感最强，也是后续测试策略和用例质量的根。
2. `TEST_DESIGN/STRATEGY` 与 `TEST_DESIGN/CASES`：建立需求、风险、测试点、用例的闭环。
3. `REQ_REVIEW/REVIEW` 与 `REQ_REVIEW/REPORT`：强化产品经理和测试评审协作。
4. `VALUE_DISCOVERY` 全链路：让产品经理视角的产出物更像可评审的产品发现文档。
5. `INCIDENT_REVIEW` 全链路：补强复盘报告的事实、根因和改进闭环。
6. `IDEA_BRAINSTORM` 全链路：提升创意工作流的证据、收敛和验证质量。

每个切片都应包含：

- 先写或更新失败测试。
- 修改 prompt/template。
- 同步后端 artifact contract 和 visual contract。
- 更新 contract sync 测试。
- 需要时补充 LLM judge 或 E2E evidence。
- 不新增 runtime/API/store/UI 分支。

## 不纳入本轮的事项

- 不开发新的地图、看板、矩阵专属前端控件。
- 不重构 `StructuredVisual` 为多形态渲染器。
- 不拆分 `ArtifactPane.tsx`、`store.ts` 或后端 runtime。
- 不改变 `/api/agent/runs/stream`。
- 不新增独立 Agent API 或 agent-specific SSE path。
- 不把 Lisa/Alex 拆成各自运行时。
