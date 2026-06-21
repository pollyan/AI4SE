# TEST_DESIGN 产出物专业化规格

## Current State Gap Analysis

### 事实源快照

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/todos/archive/2026-06-22-new-agents-artifact-professionalization-target.md`、`docs/todos/archive/2026-06-22-new-agents-artifact-professionalization-design.md`
- 已读取：`tools/new-agents/frontend/src/core/prompts/test_design/clarify.ts`、`strategy.ts`、`cases.ts`、`delivery.ts`
- 已读取：`tools/new-agents/frontend/src/core/workflows.ts`
- 已读取：`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/tests/test_agent_contracts.py`、`tools/new-agents/backend/tests/test_workflow_contract_sync.py`、`tools/new-agents/backend/tests/test_stream_services.py`
- 已读取：`tools/new-agents/backend/test_asset_parsing.py`、`tools/new-agents/backend/test_assets.py`、`tools/new-agents/backend/tests/test_test_assets.py`
- 当前工作区已有无关 zip 改动：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`，本轮不触碰。
- 当前工作区已有目标状态文档改动：`docs/todos/archive/2026-06-22-new-agents-artifact-professionalization-target.md`、`docs/todos/archive/2026-06-22-new-agents-artifact-professionalization-design.md`，本轮沿用并避免回滚。
- Worktree 隔离降级：当前输入文档改动已存在于主工作区，另建 worktree 会丢失最新目标状态上下文；本轮限定写入 `TEST_DESIGN` artifact 专业化相关文件。

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| `TEST_DESIGN` 全链路 artifact 专业化 | `CLARIFY` 偏薄；`STRATEGY` 资源/门禁不足；`CASES` 缺断言和执行状态；`DELIVERY` 偏拼接 | 用户输入需求 -> Lisa 澄清需求 -> 制定策略 -> 生成用例 -> 交付评审文档 -> 测试资产导出可继续消费 | 单独改某一 stage 会让前后阶段字段无法衔接，例如 `CASES` 新字段需要 `STRATEGY` 测试点和风险来源支撑，也需要 test asset parser 兼容 | Prompt/template、backend contract、contract sync tests、test asset parsing tests、stream service fixture 全部通过 |
| `REQ_REVIEW` 入口质量专业化 | 第一阶段缺 Mermaid，问题清单状态和复审条件不足 | 用户评审需求 -> 得到可签署评审报告 -> 作为 Lisa 测试设计输入 | 与 `TEST_DESIGN` 相关但属于另一条用户入口，本轮并入会扩大风险 | 下一轮 contract/template/judge 证据 |
| 新可视化控件 | `ai4se-visual` 当前统一表格渲染 | 用户查看 artifact -> 获得地图/看板体验 | 用户已明确当前优先内容专业化，不开发新控件 | 后续 UI 组件测试和截图 |

### 候选 gap

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `TEST_DESIGN` 全链路 artifact 专业化 | 用户最高频路径 + 目标状态设计 | 四个 stage 都成为可评审、可追溯、可协作的专业测试设计文档 | 有基础章节、Mermaid、`risk-board`、`traceability-matrix`、`coverage-map` | 缺字段级模板、阶段门禁、协作状态和部分下游扩展字段 | 最高 | 中，涉及 prompt/contract/parser/tests | Python contract tests、parser tests、template sync tests | 本轮 |
| `REQ_REVIEW` 专业化 | 需求质量入口 | 需求评审能给 `TEST_DESIGN` 提供高质量输入 | 有问题清单和报告 | 第一阶段 Mermaid 和问题关闭闭环不足 | 高 | 中 | contract/template/judge | 下一轮 |
| `VALUE_DISCOVERY` handoff 专业化 | Alex 到 Lisa handoff | 产品价值文档更适合作为测试输入 | 有蓝图和 roadmap | 证据等级、验证假设、测试可验证性不足 | 中高 | 中 | handoff + artifact tests | 后续 |

### 排序结论

1. 本轮选择 `TEST_DESIGN`，因为它是用户使用最多的测试用例生成工作流，且 `CLARIFY -> STRATEGY -> CASES -> DELIVERY` 的质量会级联影响最终测试用例专业度。
2. `REQ_REVIEW` 暂不并入，因为它是独立需求评审入口；它的产出可以在下一轮作为 `TEST_DESIGN` 上游质量增强。
3. 新可视化控件暂缓，本轮仅复用现有 Mermaid 和 `ai4se-visual` type/columns/rows 结构。

### 切片厚度门禁

| 门禁 | 本轮满足情况 |
| --- | --- |
| 入口 | 用户在 New Agents 选择 `TEST_DESIGN` 并输入需求 |
| 动作 | Lisa 生成四阶段 artifact |
| 处理 | prompt/template 牵引字段级输出，backend contract 校验关键标题、字段和 visual，parser 读取新增用例字段 |
| 可见结果 | 右侧 artifact 具备事实、风险、测试点、用例、交付门禁 |
| 状态承接 | `CLARIFY` 的事实/规则进入策略，`STRATEGY` 的风险/测试点进入用例，`CASES` 的覆盖关系进入交付和测试资产导出 |
| 失败反馈 | 缺关键标题、表头或 visual 时 contract test 失败；缺可解析用例表时 parser 显式失败 |
| 证据 | backend pytest、contract sync tests、test asset parser tests、diff check |
| 结论 | 通过，属于完整用户主路径能力包 |

## 本轮 Milestone

作为专业测试人员，当我使用 Lisa 的测试设计工作流时，我可以得到从需求澄清、风险策略、可执行用例到交付评审的连续专业文档链路，从而让测试用例生成结果可评审、可追溯、可继续协作和可导出消费。

## Artifact 目标规格

### TEST_DESIGN / CLARIFY

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 测试需求分析与澄清基线 |
| 目标角色 | 测试负责人、产品经理、研发负责人 |
| 专业用途 | 把原始需求转为可测试、可评审、可进入策略阶段的基线 |
| 目标章节 | 文档信息；需求事实清单；被测系统与边界；业务规则与数据状态；核心链路与异常链路；待澄清问题；隐式质量需求；后续测试设计输入；阶段门禁 |
| 推荐格式 | 文档信息表、事实表、范围表、业务规则表、Mermaid flowchart、问题表、质量需求表、门禁 checklist |
| 必填字段 | 事实 ID、需求事实、来源、证据等级、状态；模块/页面/API/用户角色/数据对象；规则 ID、触发条件、边界值、异常处理、验收口径；问题 ID、优先级、阻断性、当前假设、责任方、状态 |
| 可视化要求 | 必须包含 Mermaid flowchart，展示用户入口、系统边界、核心服务、数据存储、外部依赖、成功反馈和失败反馈 |
| 协作状态字段 | 状态、阻断性、证据等级、责任方 |
| 阶段门禁 | 测试范围/不测范围明确；至少一条主链路和一条异常链路可测试；P0 阻断项有确认结论或显式 AI 假设；可产出策略阶段风险种子和测试点候选 |
| Contract 护栏 | 校验目标章节、关键协作表头和 flowchart |
| Judge/E2E 建议 | 判断是否能让测试负责人直接进入风险策略设计，不接受只有摘要和泛泛问题 |

### TEST_DESIGN / STRATEGY

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 风险驱动测试策略蓝图 |
| 目标角色 | 测试架构师、测试负责人、研发负责人 |
| 专业用途 | 把澄清基线转为质量目标、FMEA 风险、测试技术和测试点拓扑 |
| 目标章节 | 策略摘要；质量目标；风险识别与 FMEA；风险矩阵；测试技术选型；测试分层策略；测试点拓扑；资源与取舍；阶段门禁 |
| 推荐格式 | 短文本、质量目标表、FMEA 表、Mermaid quadrantChart、`risk-board`、Mermaid block-beta、测试点拓扑表、门禁 checklist |
| 必填字段 | 目标 ID、质量目标、度量口径；风险 ID、失效模式、影响、S/O/D/RPN、缓解策略、覆盖建议；技术 ID、针对目标、技术类别、选择理由；测试点 ID、关联风险、层级、优先级、预估用例数 |
| 可视化要求 | 保留 quadrantChart、`risk-board`、block-beta；风险 ID 和测试点 ID 必须能互相追溯 |
| 协作状态字段 | 覆盖状态、资源取舍是否需确认、风险接受状态 |
| 阶段门禁 | 所有 P0 风险有覆盖建议；测试点拓扑可被 `CASES` 消费；资源取舍有明确影响说明 |
| Contract 护栏 | 校验新增章节、核心表头、quadrantChart、block-beta、risk-board |
| Judge/E2E 建议 | 判断策略是否风险驱动，是否有可执行测试点，而不是泛泛列测试类型 |

### TEST_DESIGN / CASES

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 可执行测试用例资产草案 |
| 目标角色 | 测试工程师、自动化测试工程师、测试负责人 |
| 专业用途 | 将策略阶段测试点转为可人工执行、可自动化评估、可导出消费的测试资产 |
| 目标章节 | 用例统计；用例设计依据；按维度分组的用例清单；测试数据与环境；自动化候选；测试点覆盖追溯；开放问题；阶段门禁 |
| 推荐格式 | Mermaid pie、依据表、分维度用例表、数据环境表、自动化候选表、`traceability-matrix`、问题表、门禁 checklist |
| 必填字段 | ID、用例标题、优先级、测试维度、关联测试点、关联风险、前置条件、操作步骤、测试数据、预期结果、断言、执行层级、自动化建议、状态 |
| 可视化要求 | 保留用例优先级 pie 和 `traceability-matrix` |
| 协作状态字段 | 状态：草稿 / 待确认 / 可执行 / 需补环境；开放问题的阻断性、责任方 |
| 阶段门禁 | P0 测试点 100% 有用例；每条用例有测试数据和断言；未覆盖测试点列入开放问题 |
| Contract 护栏 | 校验新增章节、核心用例表头和 `traceability-matrix` |
| 下游消费 | Markdown parser 应导出新增扩展字段；持久化数据库暂不扩 schema，作为本轮残余风险记录 |
| Judge/E2E 建议 | 判断用例是否可执行、是否含数据和断言、是否能被 test assets 导出 |

### TEST_DESIGN / DELIVERY

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 测试设计交付评审文档 |
| 目标角色 | 测试负责人、产品经理、研发负责人、项目管理者 |
| 专业用途 | 汇总需求、风险、测试点、用例、开放问题和验收状态，形成可评审交付件 |
| 目标章节 | 文档信息；执行摘要；需求分析摘要；测试策略摘要；测试用例摘要；覆盖地图；开放风险；交付验收清单；签署确认；变更记录 |
| 推荐格式 | 文档信息表、摘要表、`coverage-map`、开放风险表、验收 checklist、签署表、变更记录表 |
| 必填字段 | 项目、版本、总用例数、P0/P1/P2 数量、高风险项、覆盖率、开放问题、责任方、验收状态、签署角色 |
| 可视化要求 | 保留 `coverage-map`，行字段为需求、风险、测试点、用例、验收状态 |
| 协作状态字段 | 开放风险状态、风险接受结论、责任方、签署状态 |
| 阶段门禁 | P0 风险和 P0 用例闭环；开放问题有处理结论；交付验收清单可签署 |
| Contract 护栏 | 校验新增章节、coverage-map 和关键交付字段 |
| Judge/E2E 建议 | 判断终稿是否是可评审交付件，不接受简单拼接“参见上文” |

## 验收条件

1. Given `TEST_DESIGN/CLARIFY` 产出物
   When 后端 contract 校验
   Then 缺少需求事实清单、业务规则与数据状态、阶段门禁或 flowchart 时应失败
   Evidence: `tools/new-agents/backend/tests/test_agent_contracts.py`

2. Given `TEST_DESIGN` 四个 prompt/template
   When contract sync tests 扫描模板
   Then 每个模板包含 backend contract 要求的标题、字段和 visual 示例
   Evidence: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`

3. Given `TEST_DESIGN/CASES` 新用例表
   When test asset parser 导出 Markdown
   Then 新增 `断言`、`执行层级`、`自动化建议`、`状态` 可出现在导出结果和 intent tester draft 描述中
   Evidence: `tools/new-agents/backend/tests/test_test_assets.py`

4. Given stream service 使用 CLARIFY 合法样例
   When 新 contract 注入系统提示词并校验模型输出
   Then 合法样例包含新增标题和 flowchart，不破坏 shared Agent Runtime
   Evidence: `tools/new-agents/backend/tests/test_stream_services.py`

## 明确不纳入本轮

- 不开发新的地图、看板、矩阵专属前端控件。
- 不创建 agent-specific runtime、transport、state store、SSE/API path 或 bespoke rendering pipeline。
- 不做数据库 schema 迁移来持久化 `CASES` 扩展字段；本轮先保证模板、contract 和 Markdown 导出层可用。
- 不一次性改造 `REQ_REVIEW`、`VALUE_DISCOVERY`、`IDEA_BRAINSTORM`、`INCIDENT_REVIEW`。
