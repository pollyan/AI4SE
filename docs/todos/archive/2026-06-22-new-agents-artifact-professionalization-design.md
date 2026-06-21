# New Agents 产出物专业化目标状态设计

## 状态

- 类型：第一轮 Current State Gap Analysis 与目标状态设计
- 输入：`docs/todos/refactor/2026-06-22-new-agents-artifact-professionalization-target.md`
- 范围：`tools/new-agents/` 全部 workflow/stage artifact
- 当前状态：设计完成，待后续按 workflow / artifact 进入目标模式切片实现
- 本轮边界：只新增本文档；不修改运行时代码、prompt/template、backend contract、测试或前端可视化组件

## Current State Gap Analysis

### 事实源快照

已读取并作为事实源：

- 仓库与目标模式规则：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`
- 本轮输入：`docs/todos/refactor/2026-06-22-new-agents-artifact-professionalization-target.md`
- Workflow 配置：`tools/new-agents/workflow_manifest.json`
- 前端 workflow 拼装：`tools/new-agents/frontend/src/core/workflows.ts`
- 全量 prompt/template：`tools/new-agents/frontend/src/core/prompts/test_design/*.ts`、`req_review/*.ts`、`value_discovery/*.ts`、`idea_brainstorm/*.ts`、`incident_review/*.ts`
- 后端 artifact contract：`tools/new-agents/backend/agent_contracts.py`
- Contract 同步测试：`tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- 结构化可视化：`tools/new-agents/frontend/src/core/structuredVisuals.ts`、`tools/new-agents/frontend/src/components/StructuredVisual.tsx`
- API 契约：`docs/api-contracts.md` 中 New Agents runtime、artifact、test assets 相关段落

工作树状态：

- 当前工作区已有无关 zip 改动：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`，本轮不触碰。
- 当前工作区已有上一轮文档准备改动：`docs/todos/refactor/README.md` 与未跟踪的 `docs/todos/refactor/2026-06-22-new-agents-artifact-professionalization-target.md`。
- 因本轮输入文档仍在当前工作区且未跟踪，worktree 隔离降级为当前工作区继续；本轮只新增本文档，避免覆盖既有改动。

### 当前 artifact 体系总览

当前 New Agents artifact 体系由四层组成：

| 层 | 当前事实 | 专业化含义 | 当前缺口 |
| --- | --- | --- | --- |
| Workflow 元数据 | `workflow_manifest.json` 定义 5 个 workflow、17 个 stage、2 个 handoff | 决定用户看到的工作流、阶段顺序和 agent 归属 | Manifest 不承载 artifact 质量目标、章节格式、门禁和评审标准 |
| Prompt/template | `frontend/src/core/workflows.ts` 将每个 stage 绑定到对应 prompt/template TS 模块 | 直接牵引模型生成右侧 artifact | 多数模板定义了标题和示例表格，但没有完整定义每章目的、字段粒度、协作状态和阶段门禁 |
| Backend contract | `agent_contracts.py` 校验 required headings、部分 Mermaid 类型和部分 `ai4se-visual` 类型 | 防止模型完全偏离模板或漏掉关键图表 | Contract 主要是“存在性校验”，不能防止空泛正文、低密度表格、缺少待确认状态或缺少专业证据 |
| Visual rendering | `StructuredVisual` 支持 10 种 `ai4se-visual` type，但统一渲染为表格 | 可以先承载结构化看板、地图、矩阵数据 | 类型语义存在，但没有专属地图/看板 UI；本轮不开发新控件 |

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| A. 全 workflow artifact 目标状态设计 | 用户要求全面审视所有产出物；输入文档要求逐 workflow/stage 定义目标状态；当前 template 和 contract 粒度不足 | 用户启动后续目标模式 -> agent 读取目标设计 -> 按 workflow 切片修改 prompt/contract/test -> 产出物专业度可被评审 | 如果只分析 `TEST_DESIGN/CLARIFY`，无法形成全局标准；如果只写原则，后续目标模式无法按 stage 实施 | 本文档覆盖 17 个 stage，包含当前问题、目标章节、格式、字段、门禁和评审建议 |
| B. TEST_DESIGN 专项重构实施 | 当前测试设计工作流是用户最高频使用场景；`CLARIFY` 明显偏薄 | 用户输入需求 -> Lisa 输出测试分析基线 -> 用户确认边界 -> 后续策略/用例质量提升 | 这是后续实现切片，不应和本轮目标状态设计混在一起 | 后续 prompt/contract/test/LLM judge 变更 |
| C. 结构化可视化专属渲染 | 当前 `ai4se-visual` 类型统一表格渲染，地图/看板体验不足 | 用户查看 artifact -> 对 journey/risk/coverage 有更强视觉理解 | 属于新 UI 功能，用户明确要求本轮先不做 | 后续前端组件截图和可视化测试 |

### 候选 gap

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. 全 workflow artifact 目标状态设计 | 用户最新目标 + target 文档 | 为 17 个 stage 形成可执行规格 | 有章节模板和存在性 contract | 缺少统一专业规格 | 高，支撑后续所有目标模式切片 | 低，只写文档 | 文档覆盖清单、diff check | 本轮 |
| B. TEST_DESIGN/CLARIFY 实施 | 用户最强痛点 | 澄清阶段成为测试分析基线文档 | 有 4 个章节和 flowchart | 缺少事实、规则、异常链路、协作状态和门禁 | 高 | 中，需要 prompt/contract/test/LLM judge | 后续测试和模型评审 | 下一轮优先 |
| C. `ai4se-visual` 专属 UI | 用户体验讨论 | journey-map/risk-board/coverage-map 形成专属视觉 | 统一表格渲染 | 视觉表达不够强 | 中 | 中高，涉及 UI/测试 | 前端组件测试和截图 | 暂缓 |

排序结论：

1. 本轮选择 A，因为用户明确要求“先全面扫描并产出目标状态”，且后续会用目标模式逐 workflow 消化。
2. B 是最推荐的下一轮实现切片，尤其是 `TEST_DESIGN/CLARIFY`。
3. C 属于新功能，用户明确要求第二步再考虑。

### 切片准入判断

- 用户功能包边界：本轮产出“全 workflow artifact 专业化目标状态设计”，用于后续目标模式消费。
- 用户可感知动作链：用户提供目标模式提示词 -> 本轮扫描事实源 -> 新增设计文档 -> 用户后续可按文档启动实现目标。
- 完整功能检查：目标用户是后续执行目标模式的 Codex 和项目维护者；完成后可按 workflow/stage 切片重构产出物；失败时通过文档检查发现遗漏。
- 相邻缺口合并：合并了 prompt/template、backend contract、visual contract、LLM judge、E2E evidence 的目标状态设计，不拆成零散原则。
- 厚切片合并结论：本轮是工程信任闭环，不是单个字段或单个 prompt 修改。
- Superpowers 成本合理性：全量产出物目标状态会决定后续多轮目标模式方向，值得完整 CGA 和文档设计。
- 能力增量句：完成后，用户现在可以用一份统一目标状态文档驱动后续按 workflow、按 artifact 的专业化重构。

### 切片厚度门禁

| 门禁 | 本轮满足情况 |
| --- | --- |
| 入口 | 用户提供目标模式提示词和输入文档 |
| 动作 | 只读扫描指定事实源，新增目标状态设计文档 |
| 处理 | 对 17 个 stage 做当前问题和目标规格设计 |
| 可见结果 | `docs/todos/refactor/2026-06-22-new-agents-artifact-professionalization-design.md` |
| 状态承接 | 后续目标模式可直接引用本文档进入 prompt/contract/test 切片 |
| 失败反馈 | 若缺 stage、缺字段、误触代码，通过自检和 git diff 暴露 |
| 证据 | 文档覆盖清单、`git diff --check`、关键词扫描 |
| 结论 | 作为工程信任闭环通过 |

## 当前问题总览

### 横向问题

| 问题 | 当前事实 | 影响 |
| --- | --- | --- |
| 模板偏章节级 | 多数 template 给出标题和示例表格，但没有逐章节定义目的、字段粒度、人工确认规则 | 模型容易生成“看起来有结构、实则信息密度不足”的 artifact |
| Contract 偏存在性校验 | `agent_contracts.py` 校验 required headings、Mermaid 类型、`ai4se-visual` schema | 能拦住缺标题/缺图表，拦不住空泛段落、无证据结论、无责任状态 |
| 协作状态不统一 | 仅少数阶段提示“待确认/已确认”“阶段门禁”，没有统一字段 | 用户难以判断哪些是事实、假设、阻断项和可后续跟进项 |
| 第一阶段可视化覆盖不全 | `TEST_DESIGN/CLARIFY`、`IDEA_BRAINSTORM/DEFINE`、`INCIDENT_REVIEW/TIMELINE` 有 Mermaid；`VALUE_DISCOVERY/ELEVATOR` 和 `REQ_REVIEW/REVIEW` 没有 required Mermaid | 不满足“每个 workflow 第一阶段至少一个有认知价值 Mermaid 图”的目标 |
| `ai4se-visual` 语义强于渲染 | 现有 10 种 type 都统一表格渲染 | 可作为第一步结构化数据承载，但不应在本轮承诺专属地图/看板体验 |
| 终稿类 artifact 以拼接为主 | `TEST_DESIGN/DELIVERY`、`INCIDENT_REVIEW/IMPROVEMENT` 依赖“完整引用前序阶段” | 缺少交付摘要、签署门禁、开放风险和可验收闭环 |
| LLM judge 未形成统一质量口径 | 现有 contract sync 关注模板和 visual 示例 | 后续需要用模型评估专业完整性、可操作性、非空泛性 |

## Workflow / Stage 当前问题清单

| Workflow | Stage | 当前问题 |
| --- | --- | --- |
| `TEST_DESIGN` | `CLARIFY` | 章节方向正确，但缺少需求事实清单、业务规则表、数据/状态模型、异常链路、待确认问题表字段、AI 假设和阶段门禁表；当前 contract 只校验 4 个二级标题和 flowchart。 |
| `TEST_DESIGN` | `STRATEGY` | 有 FMEA、risk-board、测试金字塔和测试点拓扑，但质量目标、风险来源、测试技术选型理由、资源取舍和覆盖准入不够结构化。 |
| `TEST_DESIGN` | `CASES` | 用例表字段较完整，但缺少用例设计依据、用例状态、自动化候选、断言粒度、数据构造方式、执行层级和不可执行风险。 |
| `TEST_DESIGN` | `DELIVERY` | 以汇总拼接为主，缺少执行前验收、开放风险、签署意见、变更记录和交付质量门禁。 |
| `REQ_REVIEW` | `REVIEW` | 问题清单专业度较好，但第一阶段缺 Mermaid；缺少需求质量总览图、评审范围、不评审范围、问题状态和修订验收口径。 |
| `REQ_REVIEW` | `REPORT` | 有结论、问题分布、priority-board，但缺少复审条件、问题关闭状态、责任承诺和版本变更信息。 |
| `VALUE_DISCOVERY` | `ELEVATOR` | 有价值定位四要素和 score-matrix，但第一阶段缺 Mermaid；缺少价值结构图、证据等级、未验证假设和定位风险。 |
| `VALUE_DISCOVERY` | `PERSONA` | 用户画像字段较完整，但缺少画像证据、决策链、购买/使用分离、反画像和访谈验证状态。 |
| `VALUE_DISCOVERY` | `JOURNEY` | 有 journey Mermaid 和 journey-map，但缺少关键时刻、触发条件、替代方案成本、机会优先级评分和验证实验。 |
| `VALUE_DISCOVERY` | `BLUEPRINT` | 已接近产品需求蓝图，但需求表字段缺少范围边界、非功能要求、依赖、验收 owner 和测试可验证性等级。 |
| `IDEA_BRAINSTORM` | `DEFINE` | 有问题假设和 mindmap，但缺少证据等级、目标用户分层、问题发生场景、不可做边界和验证门禁。 |
| `IDEA_BRAINSTORM` | `DIVERGE` | 有创意卡片，但缺少创意来源、适用场景、依赖假设、反例、风险和后续可验证性。 |
| `IDEA_BRAINSTORM` | `CONVERGE` | 有 ICE 和 quadrantChart，但缺少评分证据来源、敏感性分析、资源约束和最终推荐的验证计划。 |
| `IDEA_BRAINSTORM` | `CONCEPT` | 有定位、Lean Canvas、MVP 和增长漏斗，但缺少核心假设清单、实验优先级、决策记录和不可做范围。 |
| `INCIDENT_REVIEW` | `TIMELINE` | 事实还原门禁较强，但缺少事实来源、证据链接、影响量化可信度和推测隔离表。 |
| `INCIDENT_REVIEW` | `ROOT_CAUSE` | 有 5-Why、cause-map、鱼骨图，但缺少证据强度、可行动性判定、根因置信度和排除项。 |
| `INCIDENT_REVIEW` | `IMPROVEMENT` | SMART 行动清单较强，但缺少行动与根因覆盖率、复查日期、失败回滚、风险接受和组织学习机制。 |

## 目标状态总设计

### 统一 artifact 结构

每个 artifact 的目标结构分为六类章节，具体标题可按 workflow 调整：

| 章节类型 | 推荐格式 | 目的 | 必填元素 |
| --- | --- | --- | --- |
| 文档元信息 | 表格 | 让读者知道对象、版本、时间、来源和状态 | 文档名、对象、版本、生成/更新时间、当前阶段状态 |
| 核心事实/结论 | 表格 + 短文本 | 提炼当前阶段可依赖的事实和结论 | ID、结论、来源、置信度、状态 |
| 专业分析主体 | 表格 + Mermaid / `ai4se-visual` | 承载该阶段最重要的专业分析 | 领域字段、优先级、依据、风险、建议 |
| 待确认与协作 | 表格 | 区分阻断项、非阻断项、AI 假设和已确认项 | ID、问题、优先级、阻断性、当前假设、责任方、状态 |
| 可视化表达 | Mermaid / `ai4se-visual` | 降低结构理解成本 | 图表必须映射正文 ID 或字段 |
| 阶段门禁 | 检查清单 | 判断是否可以进入下一阶段 | 必填项完成状态、开放风险、用户确认要求 |

### 统一协作状态字段

后续所有需要人机协作的表格建议使用以下状态枚举，prompt/template 先引导，contract 后续按阶段选择性校验：

| 字段 | 建议值 | 用途 |
| --- | --- | --- |
| `状态` | 已确认 / 待确认 / AI 假设 / 不适用 | 区分事实和假设 |
| `阻断性` | 阻断 / 非阻断 | 判断是否允许进入下一阶段 |
| `优先级` | P0 / P1 / P2 | 排序和阶段门禁 |
| `证据等级` | 事实证据 / 用户陈述 / 合理推断 / 待验证 | 降低模型过度自信 |
| `责任方` | 产品 / 研发 / 测试 / 运维 / 业务方 / 用户确认 | 形成协作闭环 |

## 每个 artifact 的目标规格

### TEST_DESIGN / CLARIFY

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 测试需求分析与澄清基线 |
| 目标角色 | 测试负责人、产品经理、研发负责人 |
| 专业用途 | 将原始需求转为可测试、可评审、可进入策略设计的基线文档 |
| 目标章节 | 文档信息；需求事实清单；被测系统与边界；业务规则与数据状态；核心链路与异常链路；待澄清问题；隐式质量需求；后续测试设计输入；阶段门禁 |
| 章节格式 | 文档信息表；事实/规则/问题表；Mermaid flowchart；非功能需求表；门禁 checklist |
| 必填字段 | 事实 ID、需求事实、来源、状态；模块/页面/API/角色/数据对象；规则 ID、触发条件、边界、异常、验收口径；问题 ID、优先级、阻断性、当前假设、责任方、状态 |
| 可视化要求 | Mermaid flowchart 表达用户入口、系统边界、核心服务、数据存储、外部依赖、成功/失败反馈；图中节点必须和范围表一致 |
| 协作状态 | 必须区分已确认、待确认、AI 假设、阻断、非阻断 |
| 阶段门禁 | P0 阻断问题有明确确认或显式默认假设；测试范围/不测范围明确；核心业务规则和至少一条异常链路可测试 |
| Contract 建议 | required headings 增加“需求事实清单”“业务规则与数据状态”“阶段门禁”；后续可校验待澄清问题表头 |
| LLM Judge 建议 | 重点评估是否从“几段澄清摘要”升级为测试分析基线，是否能直接支撑策略阶段 |

章节级目标：

| 章节 | 格式 | 必填内容 |
| --- | --- | --- |
| 文档信息 | 表格 | 需求名称、输入来源、当前阶段、生成时间、整体结论 |
| 需求事实清单 | 表格 | 事实 ID、事实描述、来源、证据等级、状态 |
| 被测系统与边界 | 表格 + bullet | 测试范围、不测范围、用户角色、入口、模块、接口 |
| 业务规则与数据状态 | 表格 | 规则 ID、条件、边界值、状态流转、异常处理、验收口径 |
| 核心链路与异常链路 | Mermaid + 表格 | 主流程、逆向流程、失败/重试/并发路径 |
| 待澄清问题 | 表格 | 问题 ID、优先级、阻断性、影响范围、当前假设、责任方、状态 |
| 隐式质量需求 | 表格 | 性能、安全、兼容、合规、可观测性要求 |
| 后续测试设计输入 | 表格 | 风险种子、测试点候选、测试数据需求 |
| 阶段门禁 | checklist | 能否进入策略阶段、未决风险和确认要求 |

### TEST_DESIGN / STRATEGY

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 风险驱动测试策略蓝图 |
| 目标角色 | 测试架构师、测试负责人、研发负责人 |
| 专业用途 | 把澄清基线转为质量目标、风险优先级、测试技术和测试点拓扑 |
| 目标章节 | 策略摘要；质量目标；风险识别与 FMEA；风险矩阵；测试技术选型；测试分层；测试点拓扑；资源与取舍；阶段门禁 |
| 章节格式 | 短文本；表格；Mermaid quadrantChart/block-beta；`risk-board` |
| 必填字段 | 质量目标、可测指标、风险 ID、失效模式、S/O/D/RPN、缓解策略、覆盖建议、测试点 ID、层级、优先级、预估用例数 |
| 可视化要求 | 保留 quadrantChart、risk-board、测试金字塔；图表风险 ID 与风险明细一致 |
| 协作状态 | 高风险项必须标注是否已覆盖；资源取舍必须标注是否需用户确认 |
| 阶段门禁 | 所有 P0 风险有覆盖建议；测试点拓扑能追溯到风险或质量目标 |
| Contract 建议 | 保持 required visual；后续增加“资源与取舍”“阶段门禁”标题或表头校验 |
| LLM Judge 建议 | 评估策略是否风险驱动，而不是泛泛列测试类型 |

### TEST_DESIGN / CASES

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 可执行测试用例资产草案 |
| 目标角色 | 测试工程师、自动化测试工程师、测试负责人 |
| 专业用途 | 将测试点转为可人工执行、可导出、可追溯、可二次编辑的用例集合 |
| 目标章节 | 用例统计；用例设计依据；按维度分组的用例清单；测试数据与环境；自动化候选；覆盖追溯；开放问题；阶段门禁 |
| 章节格式 | Mermaid pie；表格；`traceability-matrix`；checklist |
| 必填字段 | ID、标题、优先级、维度、关联测试点、关联风险、前置条件、操作步骤、测试数据、预期结果、断言、执行层级、自动化建议、状态 |
| 可视化要求 | 保留用例分布 pie 和 traceability-matrix |
| 协作状态 | 每条用例标注草稿/待确认/可执行/需补环境；不可执行原因必须显式写出 |
| 阶段门禁 | P0 测试点 100% 有用例；所有用例有预期结果和测试数据；未覆盖测试点列入开放问题 |
| Contract 建议 | 现有 CASES 表头较完整；后续可增加“断言”“执行层级”“状态”校验 |
| LLM Judge 建议 | 评估用例是否可执行、是否包含数据和断言、是否能被 test-assets 导出消费 |

### TEST_DESIGN / DELIVERY

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 测试设计交付评审文档 |
| 目标角色 | 测试负责人、产品经理、研发负责人、项目管理者 |
| 专业用途 | 汇总需求、风险、测试点、用例、验收和开放风险，形成可评审交付件 |
| 目标章节 | 文档信息；执行摘要；需求分析摘要；测试策略摘要；测试用例摘要；覆盖地图；开放风险；交付验收清单；签署确认；变更记录 |
| 章节格式 | 表格；短文本；`coverage-map`；checklist |
| 必填字段 | 项目、版本、总用例数、高风险项、覆盖率、开放问题、签署角色、验收状态 |
| 可视化要求 | 保留 coverage-map，行必须包含需求、风险、测试点、用例、验收状态 |
| 协作状态 | 开放风险必须标注是否可接受、责任方和后续处理方式 |
| 阶段门禁 | P0 风险和 P0 用例闭环；开放问题有处理结论；交付验收清单明确 |
| Contract 建议 | required headings 增加执行摘要、开放风险、签署确认、变更记录 |
| LLM Judge 建议 | 评估终稿是否可被测试负责人拿去评审，而不是简单拼接 |

### REQ_REVIEW / REVIEW

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 需求质量诊断与评审问题清单 |
| 目标角色 | 产品经理、测试负责人、研发负责人 |
| 专业用途 | 从测试可验证性和交付风险角度识别需求缺陷 |
| 目标章节 | 评审信息；评审范围与不评审范围；需求质量总览；Mermaid 质量维度图；问题统计；按维度问题清单；修订建议；阶段门禁 |
| 章节格式 | 表格；Mermaid flowchart 或 quadrantChart；`score-matrix` |
| 必填字段 | 问题 ID、维度、问题描述、优先级、所属章节、影响范围、证据/依据、建议、责任方、状态 |
| 可视化要求 | 第一阶段新增 Mermaid，建议用 flowchart 展示需求质量维度和风险流向，或 quadrantChart 展示影响/可测试性缺口 |
| 协作状态 | 问题必须标注待 PM 确认、已确认、需研发判断或非阻断 |
| 阶段门禁 | P0 问题必须有修订建议和责任方；评审结论不能替代问题清单 |
| Contract 建议 | 增加 REQUIRED_ARTIFACT_MERMAID_DIAGRAMS for `REQ_REVIEW/REVIEW`；保留 score-matrix |
| LLM Judge 建议 | 评估问题是否有证据，不接受“建议完善需求”这类空泛描述 |

### REQ_REVIEW / REPORT

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 可签署需求评审报告 |
| 目标角色 | 产品负责人、测试负责人、研发负责人 |
| 专业用途 | 给出可追责的评审结论、问题关闭要求和复审条件 |
| 目标章节 | 评审结论；判定标准；评审信息；问题统计；优先级看板；问题关闭清单；复审条件；签署确认；变更记录 |
| 章节格式 | 文本；Mermaid pie；`priority-board`；表格；checklist |
| 必填字段 | 结论、结论理由、P0/P1/P2 数量、问题 ID、责任方、下一步、关闭状态、复审条件 |
| 可视化要求 | 保留 pie 和 priority-board |
| 协作状态 | 所有 P0/P1 问题必须有责任方和关闭状态 |
| 阶段门禁 | 有 P0 时结论不得为通过；无责任方的问题不得视为可关闭 |
| Contract 建议 | 增加“复审条件”“问题关闭状态”“变更记录” |
| LLM Judge 建议 | 评估结论和问题严重度是否一致 |

### VALUE_DISCOVERY / ELEVATOR

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 价值定位诊断报告 |
| 目标角色 | 产品经理、创业者、业务负责人 |
| 专业用途 | 用最小信息澄清产品是什么、为谁解决什么、为什么有价值 |
| 目标章节 | 定位摘要；价值结构图；目标用户与场景；痛点证据；差异化价值；商业可行性；未验证假设；60 秒电梯演讲；阶段门禁 |
| 章节格式 | 短文本；Mermaid flowchart；表格；`score-matrix` |
| 必填字段 | 用户、场景、痛点、现有方案、不足、独特价值、证据等级、付费意愿、验证动作 |
| 可视化要求 | 第一阶段新增 Mermaid，建议 flowchart 展示“目标用户 -> 痛点 -> 现有方案不足 -> 产品价值 -> 商业验证” |
| 协作状态 | 价值主张和付费意愿必须标注证据等级或待验证 |
| 阶段门禁 | 目标用户、核心痛点、差异化和至少一个验证动作明确后才进入 persona |
| Contract 建议 | 增加 REQUIRED_ARTIFACT_MERMAID_DIAGRAMS for `VALUE_DISCOVERY/ELEVATOR`；保留 score-matrix |
| LLM Judge 建议 | 评估是否避免泛泛“提升效率”，是否有清晰目标用户和证据 |

### VALUE_DISCOVERY / PERSONA

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 用户画像与决策链分析 |
| 目标角色 | 产品经理、用户研究、业务负责人 |
| 专业用途 | 明确核心用户、行为、痛点、决策角色和验证缺口 |
| 目标章节 | 画像摘要；主要画像；行为与场景；决策链；痛点证据；反画像；用户优先级；阶段门禁 |
| 章节格式 | 表格；bullet；checklist |
| 必填字段 | 用户类型、角色定义、使用者/决策者/付费者、行为场景、痛点、频率、影响程度、证据等级、优先级理由 |
| 可视化要求 | 可选 `score-matrix` 或普通表格，不要求新增 visual |
| 协作状态 | 缺少证据的画像标注待验证；AI 推断画像不得当事实 |
| 阶段门禁 | 至少一个核心用户画像有场景、痛点、影响和证据等级 |
| Contract 建议 | 增加决策链、反画像、证据等级相关表头校验 |
| LLM Judge 建议 | 评估画像是否能指导后续旅程，而不是人口统计堆砌 |

### VALUE_DISCOVERY / JOURNEY

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 用户旅程与机会地图 |
| 目标角色 | 产品经理、设计师、业务负责人 |
| 专业用途 | 找到关键旅程、情绪低谷和产品切入机会 |
| 目标章节 | 用户旅程地图；结构化旅程地图；关键阶段分析；痛点优先级；机会评分；切入策略；验证实验；阶段门禁 |
| 章节格式 | Mermaid journey；`journey-map`；表格 |
| 必填字段 | 阶段、触点、用户任务、用户目标、情绪评分、关键痛点、现有方案不足、机会假设、成功指标 |
| 可视化要求 | 保留 journey 和 journey-map；journey 阶段必须来自用户实际场景 |
| 协作状态 | 机会假设必须标注待验证或已验证 |
| 阶段门禁 | 主要机会点必须关联高优先级痛点和成功指标 |
| Contract 建议 | 现有 contract 已覆盖 journey 与 journey-map；后续可增加“验证实验”标题 |
| LLM Judge 建议 | 评估旅程是否具体到任务和触点，不接受通用模板套话 |

### VALUE_DISCOVERY / BLUEPRINT

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 可评审需求蓝图 |
| 目标角色 | 产品经理、测试负责人、研发负责人 |
| 专业用途 | 将价值发现成果转为可评审、可测试、可排期的需求蓝图 |
| 目标章节 | 文档信息；产品概述；目标用户；核心需求；功能架构；核心流程；非功能需求；验收标准；成功指标；MVP 范围；路线图；风险评估；阶段门禁 |
| 章节格式 | 表格；Mermaid mindmap/flowchart；`roadmap` |
| 必填字段 | 需求 ID、优先级、用户故事、对应痛点、范围边界、依赖、验收标准、可测试性等级、owner |
| 可视化要求 | 保留功能架构、主流程图、roadmap |
| 协作状态 | 每条需求标注已确认/待确认/AI 假设 |
| 阶段门禁 | P0 需求有验收标准、成功指标和可测试性等级 |
| Contract 建议 | 增加非功能需求、可测试性等级、阶段门禁标题 |
| LLM Judge 建议 | 评估是否可交给 Lisa 做测试设计，不只是产品构想 |

### IDEA_BRAINSTORM / DEFINE

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 问题域验证基线 |
| 目标角色 | 产品经理、创新顾问、创业者 |
| 专业用途 | 明确要解决的问题是否真实、对谁重要、失败风险是什么 |
| 目标章节 | 问题假设；目标用户；问题域全景；证据与验证状态；问题-用户-场景匹配；约束边界；反向验证；阶段门禁 |
| 章节格式 | 文本；表格；Mermaid mindmap；checklist |
| 必填字段 | 目标用户、场景、问题、现有方案、不足、证据等级、验证状态、失败原因 |
| 可视化要求 | 保留 mindmap，节点必须对应问题域表格 |
| 协作状态 | 未验证问题必须标注待验证；不允许把假设写成事实 |
| 阶段门禁 | 问题、用户、场景、至少一个证据或验证计划明确 |
| Contract 建议 | 增加证据与验证状态、阶段门禁标题 |
| LLM Judge 建议 | 评估是否停留在问题域，没有提前跳到解决方案 |

### IDEA_BRAINSTORM / DIVERGE

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 创意发散卡片库 |
| 目标角色 | 产品经理、创新顾问、团队成员 |
| 专业用途 | 基于问题域生成多样、可追溯、可后续评估的创意候选 |
| 目标章节 | 发散方法说明；发散全景图；创意卡片库；创意来源与假设；搁置/排除记录；阶段门禁 |
| 章节格式 | Mermaid mindmap；表格 |
| 必填字段 | 编号、HMW 问句、创意技术、具体维度、对应问题、方案概述、差异化、关键假设、状态 |
| 可视化要求 | 保留 mindmap；创意节点必须与卡片编号一致 |
| 协作状态 | Active/Parked/Killed 必须有理由 |
| 阶段门禁 | 至少 3 个 Active 或 Parked 创意，且每个能追溯到问题域 |
| Contract 建议 | 增加关键假设、状态理由表头 |
| LLM Judge 建议 | 评估创意是否基于问题域，而不是凭空发散 |

### IDEA_BRAINSTORM / CONVERGE

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 创意收敛决策记录 |
| 目标角色 | 产品经理、业务负责人、团队决策者 |
| 专业用途 | 通过证据化评分和资源约束选出推荐方案 |
| 目标章节 | 决策矩阵；评分口径；ICE 评估；淘汰与合并记录；推荐方案；验证实验；阶段门禁 |
| 章节格式 | Mermaid quadrantChart；表格；可选 flowchart |
| 必填字段 | 创意编号、影响力、信心、实现难度、评分理由、证据来源、排名、结论、淘汰/合并理由、验证实验 |
| 可视化要求 | 保留 quadrantChart；合并时保留 flowchart |
| 协作状态 | 推荐方案必须标注是否用户确认；淘汰创意不可无理由消失 |
| 阶段门禁 | 推荐方案、淘汰理由、最小验证实验明确 |
| Contract 建议 | 增加“验证实验”“证据来源”表头 |
| LLM Judge 建议 | 评估评分是否有依据，是否避免只给排名 |

### IDEA_BRAINSTORM / CONCEPT

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 产品概念决策简报 |
| 目标角色 | 产品经理、业务负责人、团队沟通对象 |
| 专业用途 | 汇总问题、方案、MVP、增长和风险，形成可沟通概念简报 |
| 目标章节 | 定位声明；核心假设；Lean Canvas；MVP 功能地图；增长漏斗；Pre-mortem 风险；验证路线；下一步行动 |
| 章节格式 | 文本；表格；Mermaid pie/flowchart；`mvp-map` |
| 必填字段 | 目标用户、痛点、品类、价值主张、差异化、MVP 模块、验证指标、风险、验证动作 |
| 可视化要求 | 保留 mvp-map；MVP 功能分布和增长漏斗需要对应前文 |
| 协作状态 | 核心假设和下一步行动必须有状态和负责人角色 |
| 阶段门禁 | 概念能在 3 秒内说明品类，MVP 能验证定位声明 |
| Contract 建议 | 增加核心假设、验证路线标题 |
| LLM Judge 建议 | 评估是否可用于团队沟通，而不是概念口号 |

### INCIDENT_REVIEW / TIMELINE

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 故障事实还原记录 |
| 目标角色 | SRE、测试负责人、研发负责人、复盘主持人 |
| 专业用途 | 在不做根因推断的前提下还原事实、影响和处理过程 |
| 目标章节 | 事件概要；影响量化；事实来源；事件时间线；事实摘要；参与人员；待补充信息；阶段门禁 |
| 章节格式 | 表格；Mermaid timeline；checklist |
| 必填字段 | 故障名称、等级、发现/恢复时间、持续时长、影响范围、影响量化、事实来源、可信度、参与角色、主要行动 |
| 可视化要求 | 保留 timeline；时间点不得使用会破坏 Mermaid 的半角冒号格式 |
| 协作状态 | 待补充信息标注阻断性；推测必须移出事实摘要 |
| 阶段门禁 | 故障表现、时间、影响范围、处理过程四项齐全 |
| Contract 建议 | 增加事实来源、影响量化可信度、阶段门禁标题 |
| LLM Judge 建议 | 评估是否严格事实还原，不提前归因 |

### INCIDENT_REVIEW / ROOT_CAUSE

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 根因分析记录 |
| 目标角色 | SRE、研发负责人、质量改进负责人 |
| 专业用途 | 基于事实完成可行动的系统性根因分析 |
| 目标章节 | 事件还原保留；5-Why 分析链；根因证据表；原因鱼骨图；根因结论；排除项；阶段门禁 |
| 章节格式 | 表格；`cause-map`; Mermaid mindmap |
| 必填字段 | 层级、问题、回答、原因类型、证据、证据强度、直接原因、根本原因、促成因素、可行动性 |
| 可视化要求 | 保留 cause-map 和 mindmap |
| 协作状态 | 根因结论标注置信度；未验证原因标注待确认 |
| 阶段门禁 | 至少 3 层 5-Why；根本原因可行动；鱼骨图至少 2 类原因 |
| Contract 建议 | 增加证据强度、可行动性、排除项表头 |
| LLM Judge 建议 | 评估因果链是否跳跃，是否避免归咎个人 |

### INCIDENT_REVIEW / IMPROVEMENT

| 字段 | 目标状态 |
| --- | --- |
| Artifact 名称 | 故障复盘改进闭环报告 |
| 目标角色 | 质量改进负责人、研发负责人、SRE、管理者 |
| 专业用途 | 将根因转化为可追踪、可验收、防复发的改进行动 |
| 目标章节 | 报告信息；事件还原；根因分析；改进优先级；改进行动清单；根因覆盖检查；防复发清单；复查计划；经验教训；签署确认 |
| 章节格式 | 表格；Mermaid pie；`action-board`；checklist |
| 必填字段 | 行动 ID、措施、类型、对应根因、负责人、期限、验证方式、验收标准、优先级、状态、追踪机制、复查日期 |
| 可视化要求 | 保留 action-board 和改进分布 pie |
| 协作状态 | 每项行动必须有状态；无法落地的行动不得作为正式措施 |
| 阶段门禁 | 每个根本原因至少一个改进行动；紧急行动有期限和验收标准 |
| Contract 建议 | 增加根因覆盖检查、复查计划标题 |
| LLM Judge 建议 | 评估是否拒绝空话，是否形成根因到行动的闭环 |

## 每个 workflow 第一阶段 Mermaid 建议

| Workflow | 第一阶段 | 当前状态 | 目标 Mermaid | 图表目的 |
| --- | --- | --- | --- | --- |
| `TEST_DESIGN` | `CLARIFY` | 已有 flowchart required | 保留并强化为系统边界与核心链路图 | 让用户快速看清测什么、不测什么、依赖什么 |
| `REQ_REVIEW` | `REVIEW` | 无 required Mermaid | 新增 `flowchart` 或 `quadrantChart` | 展示需求质量维度、问题流向或影响/可测试性分布 |
| `VALUE_DISCOVERY` | `ELEVATOR` | 无 required Mermaid | 新增 `flowchart` | 展示目标用户、痛点、现有方案不足、产品价值和商业验证关系 |
| `IDEA_BRAINSTORM` | `DEFINE` | 已有 mindmap required | 保留并强化问题域全景图 | 展示核心问题、子问题、表现和影响 |
| `INCIDENT_REVIEW` | `TIMELINE` | 已有 timeline required | 保留并强化事件时间线 | 展示发现、响应、处理、恢复确认全过程 |

## `ai4se-visual` 适用章节清单

当前只复用已有通用表格渲染，不开发新控件。

| Type | 推荐使用章节 | 当前/目标用途 |
| --- | --- | --- |
| `score-matrix` | `REQ_REVIEW/REVIEW` 需求质量总览；`VALUE_DISCOVERY/ELEVATOR` 价值主张评分 | 对多维质量或价值做结构化评分 |
| `risk-board` | `TEST_DESIGN/STRATEGY` 风险处置看板 | 展示 FMEA 三因子、RPN、缓解和覆盖 |
| `traceability-matrix` | `TEST_DESIGN/CASES` 覆盖追溯 | 测试点到用例覆盖关系 |
| `coverage-map` | `TEST_DESIGN/DELIVERY` 交付覆盖地图 | 需求、风险、测试点、用例、验收闭环 |
| `priority-board` | `REQ_REVIEW/REPORT` 问题优先级看板 | P0/P1/P2 问题、影响、责任方、下一步 |
| `journey-map` | `VALUE_DISCOVERY/JOURNEY` 用户旅程结构化地图 | 阶段、任务、触点、情绪、痛点、机会 |
| `roadmap` | `VALUE_DISCOVERY/BLUEPRINT` 产品路线图 | 版本、时间、核心功能、目标、成功指标 |
| `mvp-map` | `IDEA_BRAINSTORM/CONCEPT` MVP 功能地图 | 模块、MVP 层级、用户价值、验证指标 |
| `cause-map` | `INCIDENT_REVIEW/ROOT_CAUSE` 5-Why 根因链 | 层级、问题、回答、原因类型、证据 |
| `action-board` | `INCIDENT_REVIEW/IMPROVEMENT` SMART 行动看板 | 行动、根因、负责人、期限、状态、验证 |

## 后续按 workflow 重构优先级

1. `TEST_DESIGN/CLARIFY`：最高优先级。它是用户当前最明显痛点，也是测试策略和用例质量的上游。
2. `TEST_DESIGN/STRATEGY` + `TEST_DESIGN/CASES`：建立需求、风险、测试点、用例的闭环，影响测试资产导出。
3. `REQ_REVIEW/REVIEW`：第一阶段缺 Mermaid，且与产品经理协作强相关。
4. `VALUE_DISCOVERY/ELEVATOR` + `BLUEPRINT`：补齐产品经理视角和向 Lisa handoff 的可测试性。
5. `INCIDENT_REVIEW` 全链路：当前门禁和专业方法较强，适合在测试设计稳定后升级。
6. `IDEA_BRAINSTORM` 全链路：当前结构可用，但需要提升证据、收敛和验证质量。

## LLM Judge 评审维度

统一维度：

| 维度 | 评分问题 | 不合格信号 |
| --- | --- | --- |
| 专业完整性 | 是否覆盖该阶段真实工作所需的关键内容？ | 只有标题，没有业务规则、证据、责任或验收 |
| 信息粒度 | 是否具体到角色、模块、接口、数据、规则、风险、测试点或指标？ | 大量“优化体验”“提升效率”“加强管理” |
| 可操作性 | 读者是否能据此继续评审、拆解、执行或决策？ | 读完仍不知道下一步谁确认什么 |
| 可追溯性 | 需求、问题、风险、测试点、用例、行动之间是否有关联 ID？ | 风险和用例互不引用 |
| 协作清晰度 | 是否区分已确认、待确认、AI 假设、阻断和非阻断？ | 模型假设被写成事实 |
| 可视化有效性 | Mermaid 或 `ai4se-visual` 是否表达真实业务结构？ | 图表节点和正文无关 |
| 阶段门禁 | 是否说明能否进入下一阶段以及理由？ | 有 P0 问题仍建议推进 |
| 非空泛性 | 是否避免无证据、无边界、无验收口径的口号？ | 用抽象建议替代具体字段 |

样例用例建议：

| Workflow | 样例输入 | Judge 重点 |
| --- | --- | --- |
| `TEST_DESIGN` | 登录功能、优惠券 API、支付流程 | 澄清是否形成测试基线；用例是否可执行和可追溯 |
| `REQ_REVIEW` | 故意缺验收标准和边界值的 PRD | 是否能找出 P0/P1 问题并给证据 |
| `VALUE_DISCOVERY` | “AI 生成测试用例”产品方向 | 是否明确用户、痛点证据、价值和可测试需求 |
| `IDEA_BRAINSTORM` | 模糊产品想法 | 是否先验证问题，再发散和收敛 |
| `INCIDENT_REVIEW` | 支付失败生产事故 | 是否区分事实/推测，根因是否可行动，改进是否 SMART |

## 后续改造建议

### Prompt/template 先做

适合先进入 prompt/template 的要求：

- 章节结构、章节目的和推荐格式。
- 表格字段和示例行。
- AI 假设、待确认、阻断性、证据等级的写法。
- 每个 workflow 第一阶段的 Mermaid 图要求。
- 阶段门禁的 chat 与 artifact 表达。

### Backend contract 后做

适合进入后端 contract 的要求：

- 新 required headings。
- 新 required Mermaid diagram 类型。
- 新 required `ai4se-visual` type。
- 关键表头存在性校验，例如问题 ID、优先级、阻断性、状态、责任方。
- 禁止跳过必需 artifact 阶段。

不建议第一轮 contract 校验：

- 文本质量、专业性、因果合理性、证据是否充分。这些更适合 LLM Judge。

### LLM Judge / E2E evidence

适合进入 LLM Judge 的要求：

- 是否专业、完整、可操作。
- 是否避免空泛表达。
- 是否真的支撑下一阶段。
- Mermaid 是否有认知价值而非装饰。
- 用例是否可执行、可导出、可追溯。

适合进入 E2E evidence 的要求：

- 共享 `/api/agent/runs/stream` typed Agent Runtime 仍被使用。
- artifact pane 能渲染新增 Mermaid 和 `ai4se-visual`。
- 阶段推进不绕过确认控件。
- 测试资产导出仍能解析 `TEST_DESIGN/CASES`。

## 不纳入本轮的事项

- 不开发新的地图、看板、矩阵专属前端控件。
- 不重构 `StructuredVisual` 为多形态渲染器。
- 不拆分 `ArtifactPane.tsx`、`store.ts`、`run_persistence.py` 或 Agent Runtime。
- 不修改 `/api/agent/runs/stream` request/response/SSE 协议。
- 不新增 agent-specific runtime、transport、state store、SSE/API path 或 bespoke rendering pipeline。
- 不直接修改 prompt/template、backend contract 或测试。
- 不提交或推送。
