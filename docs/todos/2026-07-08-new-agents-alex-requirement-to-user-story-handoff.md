# New Agents Alex 需求蓝图到用户故事 Handoff 路线

- 状态：执行中（第 1 轮已完成；第 2 轮待启动）
- 创建日期：2026-07-08
- 来源：用户要求先聚焦 Alex 需求梳理到后续 AI Coding 工作流的需求输入，不纳入 Lisa/Alex 之间的 handoff
- 优先级：P0
- 相关模块：`tools/new-agents/`

## 背景

当前 Alex 已有两个在线工作流：

- `IDEA_BRAINSTORM`：从模糊想法出发，形成产品概念简报。
- `VALUE_DISCOVERY`：把已有产品方向梳理为需求蓝图。

现有 handoff 主要从 `VALUE_DISCOVERY/BLUEPRINT` 接力给 Lisa 的需求评审或测试设计。用户已明确本路线暂不处理 Lisa，而是先把 Alex 产出的需求继续拆成更细粒度、可独立交付给后续 AI Coding 工作流的用户故事。

现有工作流和阶段命名存在一定学术化问题。后续调整 Alex 链路时，需要同步优化用户可见名称、入口说明、阶段标题和产物标题，让缺少上下文的用户也能直接理解“这个工作流是帮我完成什么事”。

目标不是让 Alex 输出实现计划、任务列表、代码结构或测试命令。目标是让 Alex 按敏捷需求拆分方式，把需求蓝图拆成用户故事地图和一组达到就绪标准的用户故事卡片。后续 AI Coding 工作流再基于单个用户故事读取代码库、调研现状、生成实现计划并写代码。

## 达成的产品结论

Alex 的需求前处理主线应按如下链路演进：

```text
原始 idea
  -> 产品方向 / 方案
  -> 需求蓝图
  -> 用户故事地图
  -> 用户故事卡片
  -> 单个 ready 用户故事 handoff 给 AI Coding 工作流
```

标准敏捷产物边界：

| 层级 | 产物 | 作用 |
| --- | --- | --- |
| Idea / Product Direction | 产品概念简报 | 说明目标用户、问题、推荐方案、MVP 候选、假设和风险。 |
| Requirement Blueprint | 需求蓝图 | 说明产品愿景、用户、场景、P0/P1/P2 需求、核心流程、验收标准、非功能需求和风险。 |
| Story Map | 用户故事地图 | 按用户活动和任务组织需求，识别 MVP / Release slice。 |
| User Story | 用户故事卡片 | 作为后续 AI Coding 的最小需求输入单元。 |
| Handoff Packet | 单故事需求包 | 持久化指向单个 ready story 及其上游追溯，不包含实现计划。 |

用户可见命名原则：

- 工作流名称优先描述用户任务，不优先使用方法论术语。
- 阶段名称要能回答“这一步产出什么”，避免只写抽象概念。
- 右侧 artifact 标题要和用户能复用的文档名称一致，例如“产品概念简报”“需求蓝图”“用户故事拆解文档”“单故事需求包”。

后续 Alex 工作流进入时应支持两种启动模式：

1. **开启新话题**：不继承历史内容，从空白输入开始。
2. **基于已有内容继续**：从已持久化上游 run / artifact version 选择一个产物作为起点。

handoff 应以持久化数据和可追溯引用为主，不应只把 Markdown 拼进 prompt。目标 handoff packet 至少应包含源 run、源 workflow、源 stage、源 artifact version、源 artifact digest、创建时间、摘要、结构化 payload、trace IDs、开放问题和状态。后续生成 packet 时应优先读取结构化原始数据，不从 Markdown 反解析用户故事。

## 新增工作流定位

新增 Alex 工作流建议命名为：

- 用户可见名：`用户故事拆解`
- 内部候选 ID：`USER_STORY_BREAKDOWN`
- 工作流目标：把 `VALUE_DISCOVERY/BLUEPRINT` 的需求蓝图拆成用户故事地图、MVP slice、用户故事卡片和 ready story handoff 清单。

建议阶段：

| 阶段 | 候选 ID | 目标 | 主要产出 |
| --- | --- | --- | --- |
| 需求范围校准 | `SCOPE` | 确认蓝图中哪些需求适合进入故事拆分，哪些仍被开放问题阻塞。 | 拆分范围、不拆范围、阻塞问题、需求追溯索引。 |
| 用户故事地图 | `STORY_MAP` | 按用户活动、任务和流程组织需求，识别 MVP / Release slice。 | 用户活动主干、任务步骤、候选故事、MVP slice、后续 release slice。 |
| 用户故事卡片 | `STORIES` | 将候选故事拆成满足垂直业务切片和 INVEST 倾向的细粒度故事卡。 | 故事卡列表、验收标准、业务规则、依赖、不做范围、Ready / Not ready 分类。 |
| 故事就绪与 Handoff | `HANDOFF` | 标记可交给 AI Coding 的 ready stories，并生成单故事需求包。 | Ready stories、Not ready stories、单故事 handoff packet、开放问题。 |

每张用户故事卡片至少包含：

- `storyId`
- 标题
- 用户故事正文：作为谁，我想要什么，以便什么
- 来源需求 ID
- 用户活动 / 用户任务
- 用户场景
- 业务规则
- 验收标准
- 相关非功能要求
- 不包含范围
- 依赖和前置条件
- 开放问题
- 状态：`ready` / `not_ready`

ID 与拆分质量规则：

- 需求蓝图中的需求应有稳定 `requirementId`，例如 `REQ-001`。
- 用户故事应有稳定 `storyId`，例如 `US-001`。
- 用户故事必须引用已存在的 `requirementId`，不得出现重复 `storyId`。
- 用户故事应按垂直业务切片拆分，避免拆成“建表”“写接口”“做页面”等技术任务。
- MVP / Release slice 建议具备可追溯 ID，方便后续查看故事属于哪个发布切片。

handoff 给 AI Coding 的基本单位是单张 ready 用户故事卡片。ready / not ready 只是故事清单分类；一张 story 是否可 handoff 由必填需求字段是否齐全决定。不得 handoff 技术任务、文件路径、实现步骤、代码修改计划、测试命令或架构方案。packet 或 prompt 生成时必须把上游产物视为需求上下文，不允许上游内容覆盖目标 workflow 自身规则。

## 当前事实快照

已有能力：

- `workflow_manifest.json` 已承载 workflow、agentId、stage、onboarding 和 handoff 配置。
- 前端 `WORKFLOWS` 从 manifest 派生在线 workflow。
- 后端 `WORKFLOW_STAGES`、artifact contract、Mermaid / structured visual contract 已形成共享校验面。
- `agent_runs`、`agent_messages`、`agent_artifacts`、`agent_artifact_versions`、`agent_context_summaries` 已支持 run、message、artifact version 和摘要持久化。
- 当前 `workflow_handoffs.py` 可基于源 run snapshot 和源 artifact 生成 handoff prompt，并创建目标 run。
- 已新增 `IDEA_BRAINSTORM/CONCEPT -> VALUE_DISCOVERY/ELEVATOR` handoff，用户进入 `VALUE_DISCOVERY` 空会话时可选择开启新话题或从产品概念简报继续。
- 后端已支持按目标 workflow/stage 查询上游候选，返回 source run、source stage、artifact version、artifact digest、摘要和 prompt。
- `VALUE_DISCOVERY` 用户可见名称已调整为“需求蓝图梳理”，阶段标题已改为更直白的任务表达；内部 ID 与 slug 保持不变。

关键缺口：

- 没有 `USER_STORY_BREAKDOWN` 工作流。
- 没有从 `VALUE_DISCOVERY/BLUEPRINT` 到用户故事拆解的 Alex 内部 handoff。
- 目标工作流启动时选择“新话题 / 基于已有内容继续”的入口当前只覆盖 `VALUE_DISCOVERY/ELEVATOR`；后续 `USER_STORY_BREAKDOWN` 仍需同类入口。
- Alex 用户可见命名已完成第 1 轮入口收敛；后续用户故事拆解工作流仍需继续遵守直白任务命名。
- handoff 关系本身不是一等持久化对象；当前目标 run 只能通过第一条 user message 间接看到上游内容。
- handoff packet 还不是结构化数据；当前主要使用截断 Markdown prompt。
- 结构化 `artifact_data` 尚未作为可恢复的原始需求数据被 handoff 链路稳定消费。
- 没有需求 ID、用户故事 ID、slice ID 的稳定命名与追溯规则。
- 没有上游 artifact 更新后的版本过期或 stale 提示。
- 没有用户故事卡片结构化契约、renderer、ready / not ready 分类和单故事 handoff 清单。
- 没有防止故事拆分技术任务化的质量校验口径。
- 没有端到端 E2E 证明“需求蓝图 -> 用户故事 -> 单故事需求包”链路。
- 修改 Alex handoff 底层能力时，需要保证 Lisa 现有 handoff 不回归。

## 目标轮数声明

基线按 5 个目标模式轮次推进。每一轮都必须是厚切片：包含用户入口、用户动作、系统处理、可见结果、状态承接、失败反馈和验证证据。不得把单个 schema、单个 endpoint、单个前端按钮、单个 renderer helper 或单条测试当成独立目标轮次。

| 轮次 | 目标模式用户故事 | 交付边界 |
| --- | --- | --- |
| 第 1 轮 | Alex 后续工作流可从已有上游产物启动 | 用户进入 `VALUE_DISCOVERY` 时可选择开启新话题或继承 `IDEA_BRAINSTORM/CONCEPT`，系统创建可追溯目标 run，并以持久化上游产物作为初始上下文；同步优化相关入口命名和说明。 |
| 第 2 轮 | Alex 可把需求蓝图拆成完整用户故事文档 | 新增 `USER_STORY_BREAKDOWN` 工作流，用户可从 `VALUE_DISCOVERY/BLUEPRINT` 进入完整的 `SCOPE -> STORY_MAP -> STORIES -> HANDOFF` 阶段链路，得到包含稳定 ID 和垂直业务切片的用户故事拆解文档。 |
| 第 3 轮 | 用户故事卡片具备结构化契约和质量校验 | 模型输出结构化 `artifact_data`，后端确定性渲染用户故事地图、故事卡片、Ready / Not ready 清单，并显式拒绝缺少验收标准、来源需求、故事状态或 ID 重复的故事。 |
| 第 4 轮 | 单个 ready 用户故事可形成持久化 handoff packet | 用户可从故事清单选择单张 ready story，系统生成并持久化单故事需求包，包含上游 run / artifact version / artifact digest / storyId / requirementId 追溯，不包含实现计划，并能识别上游版本变化。 |
| 第 5 轮 | Alex 需求拆分到 AI Coding 需求包全链路证据收口 | 用自动化与浏览器级证据证明 `idea -> 需求蓝图 -> 用户故事 -> 单故事 handoff packet` 主路径可用，并同步 API、测试和目标模式记录，确保 Lisa 现有 handoff 不回归。 |

## 轮次拆分规则

- 默认按上表执行，不跨越到 Lisa 或真实 AI Coding 实现工作流。
- 第 1 轮不得拆成“只加表 / 只加 endpoint / 只加按钮”；必须让用户实际完成一次从已有上游内容启动后续工作流。
- 第 2 轮不得只新增空 workflow 入口；必须完成用户从需求蓝图得到用户故事拆解文档的端到端路径。
- 第 3 轮不得只补 schema；必须让结构化契约被 Agent Runtime、renderer、contract tests 和 workflow 同步测试共同消费。
- 第 4 轮不得只生成前端文案；必须有可查询、可恢复、可追溯的单故事 handoff packet。
- 不得把用户故事拆成技术横切任务；每张 ready story 都必须表达一个可被验收的业务结果。
- 如果某轮预计同时触达 8 个以上源文件、超过约 800 行改动，或 CGA 证明无法稳定验证，可以拆成同一用户故事内的 checkpoint commit，但不能拆薄成不可独立使用的横切任务。
- 第 5 轮必须在前 4 轮完成后执行，不得提前用文档收口替代真实链路证据。

## 每轮必须遵守的目标模式流程

每个目标模式轮次都必须遵守 `docs/strategy/goal-mode-playbook.md` 和 `docs/strategy/goal-mode-cga-template.md`：

1. 读取 `AGENTS.md`、目标模式手册、`docs/index.md`、相关架构 / API / 测试文档、当前 todo、相关代码和测试。
2. 检查 `git status --short`，保护用户已有改动。
3. 如果是本路线首次启动，输出完整 Current State Gap Analysis；如果是已确认顺序中的后续轮次，输出目标承接检查。
4. 每轮只承接一个用户故事能力包，并记录未选候选去向。
5. 先写中文 spec，再写中文 implementation plan。
6. 代码或行为变更按 TDD 执行，先补 failing tests，再做实现。
7. 验证必须覆盖入口、处理、状态承接、失败反馈和下游消费。
8. 更新必要文档记录；完成型代码用户故事按 playbook 做聚焦验证、CI 等价映射和全量本地自动化例外说明。

## 每轮验收口径

### 第 1 轮：后续工作流从已有上游产物启动

- `workflow_manifest.json` 声明 `IDEA_BRAINSTORM/CONCEPT -> VALUE_DISCOVERY/ELEVATOR` handoff。
- 后端能按目标 workflow 查询可用上游候选，并返回源 run、源 stage、artifact version、摘要和状态。
- start handoff 时创建目标 run，并持久化源/目标引用或等价可追溯记录。
- 前端进入 `VALUE_DISCOVERY` 时可选择“新话题 / 从产品概念简报继续”。
- 目标侧候选只按当前系统已有 run / artifact 数据筛选。
- 入口文案、阶段标题和空状态提示使用直白任务表达，避免继续扩大“价值发现”等抽象术语的理解成本。
- 用户选择上游内容后，目标 workspace 能看到继承上下文，并继续走共享 `/api/agent/runs/stream`。
- 无可用上游内容时，页面明确提示并允许开启新话题。

### 第 2 轮：用户故事拆解工作流端到端

- `USER_STORY_BREAKDOWN` 出现在 Alex 工作流列表中。
- 工作流阶段为 `SCOPE -> STORY_MAP -> STORIES -> HANDOFF`。
- 可从 `VALUE_DISCOVERY/BLUEPRINT` handoff 进入，也可新话题启动。
- 最终 artifact 包含拆分范围、稳定需求 ID、用户故事地图、MVP slice、用户故事列表、Ready / Not ready stories、开放问题和 handoff 清单。
- 用户故事拆分必须体现垂直业务切片，不输出技术任务清单。
- 浏览器级 mock E2E 覆盖完整阶段推进。

### 第 3 轮：结构化故事契约与质量校验

- 每阶段支持结构化 `artifact_data` 或等价严格 contract。
- 结构化用户故事数据必须可被持久化或从 artifact version 中稳定恢复，后续 packet 生成不得依赖 Markdown 反解析。
- 后端确定性渲染用户故事地图和故事卡片。
- 故事卡必须引用已存在需求 ID。
- Ready story 必须包含用户故事正文、验收标准、来源需求、业务规则或明确不适用说明、不做范围、依赖和 `ready` 状态。
- Not ready story 必须包含阻塞原因、需要用户补充的问题和 `not_ready` 状态。
- ready / not ready 只作为故事是否能生成 packet 的状态字段。
- 契约测试覆盖缺少来源需求、缺少验收标准、Ready 状态非法、重复 storyId 等失败路径。

### 第 4 轮：单故事 handoff packet

- 用户可对单张 ready story 触发 handoff packet 生成。
- packet 持久化并可通过 API 读取。
- packet 只包含需求信息和追溯信息，不包含实现任务、文件路径、代码计划、测试命令或架构方案。
- packet 包含 `sourceRunId`、`sourceWorkflowId`、`sourceStageId`、`sourceArtifactVersion`、`sourceArtifactDigest`、`createdAt`、`storyId`、`requirementIds`、`acceptanceCriteria`、`businessRules`、`nonFunctionalNotes`、`outOfScope`、`dependencies`、`openQuestions`。
- 当源 artifact version 或 digest 与 packet 记录不一致时，前端或 API 能提示该 packet 可能基于旧需求。
- 前端展示 handoff packet 摘要，并能复制需求包内容；本路线不额外设计真实 AI Coding workflow 的消费协议。

### 第 5 轮：证据收口

- E2E 或等价浏览器测试覆盖 `VALUE_DISCOVERY/BLUEPRINT -> USER_STORY_BREAKDOWN -> 单故事 handoff packet`。
- 后端 contract / persistence / handoff tests 覆盖 run、artifact version 和 packet 追溯。
- 前端测试覆盖启动选择、候选为空、选择已有上游、故事 packet 展示。
- 回归测试必须覆盖现有 `VALUE_DISCOVERY/BLUEPRINT -> Lisa` handoff 行为不被 Alex 新链路破坏。
- 测试或评审证据必须覆盖用户故事没有技术任务化、验收标准可验证、来源需求可追溯。
- API 文档同步新增目标侧 handoff candidate、story packet 或等价端点。
- TESTING 文档同步新增 Alex 用户故事拆解和 AI Coding 需求包验证口径。
- 如启用 LLM judge，默认通过线 80 分；低于 80 分按 playbook 作为 P0 修复，不得收口。

## 非目标

- 不设计 Lisa 需求评审或测试设计接力。
- 不改变 Lisa 现有 handoff 的用户路径和契约；涉及共享 handoff 能力时只做兼容增强。
- 不实现真实 AI Coding workflow。
- 不为 AI Coding workflow 预先设计独立消费协议；当前只保证单故事需求包结构稳定、可读取、可复制、可追溯。
- 不生成技术任务、开发计划、架构决策、文件路径、代码 diff 或测试命令。
- 不让 Alex 读取目标代码库并做实现调研；这是后续 AI Coding workflow 的职责。
- 不为 Alex 新增专属 runtime、transport、store 或 bespoke renderer。
- 不用复制粘贴 Markdown 替代持久化 handoff 追溯。

## 目标模式执行记录

### 2026-07-08 第 1 轮：后续工作流从已有上游产物启动

已完成：

- `workflow_manifest.json` 新增 `idea-brainstorm-concept-to-value-discovery`，声明 `IDEA_BRAINSTORM/CONCEPT -> VALUE_DISCOVERY/ELEVATOR` handoff。
- `VALUE_DISCOVERY` 用户可见名改为“需求蓝图梳理”，listing、welcome message 和阶段标题改为更直白的任务表达；内部 ID 和 slug 保持不变。
- 后端 `workflow_handoffs.py` 新增目标侧候选查询，按 target workflow/stage 返回已持久化上游 run、source stage、artifact version、digest、summary 和 prompt。
- 新增 `GET /api/agent/workflow-handoff-candidates`，供目标工作流空会话启动时查询可继承上游产物。
- start handoff 创建目标 run 时，第一条 user message 包含 source run、source workflow/stage、artifact version 和 digest，形成当前轮等价可追溯记录。
- 前端 `workflowHandoffService.ts` 解析 target-side candidates 和 source metadata。
- `ChatPane` 在 `VALUE_DISCOVERY/ELEVATOR` 空会话展示“开启新话题 / 从产品概念简报继续”，无候选时提示可直接开启新话题；选择候选后复用既有 start endpoint 并切到目标 run。
- 现有 `VALUE_DISCOVERY/BLUEPRINT -> Lisa` handoff 路径保留并通过回归测试。
- API 与 TESTING 文档已记录 target-side handoff candidate 和回归责任。

已验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

结果：`76 passed`

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx src/core/config/__tests__/workflows.test.ts src/pages/__tests__/WorkflowSelect.test.tsx src/components/__tests__/Header.test.tsx
```

结果：`93 passed`

```bash
cd tools/new-agents/frontend && npm run lint
```

结果：TypeScript `tsc --noEmit` 通过。

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents 前端 `706 passed`；New Agents 后端 `561 passed, 1 deselected`。运行中仍出现既有 `ArtifactPane.test.tsx` React `act(...)` warning，但未导致测试失败。

下一轮承接：

- 第 2 轮应新增 `USER_STORY_BREAKDOWN` 工作流，并从 `VALUE_DISCOVERY/BLUEPRINT` handoff 到 `SCOPE -> STORY_MAP -> STORIES -> HANDOFF`。
- 第 2 轮开始前如无新 P0/P1 改道条件，可使用目标承接检查，不必重新做完整候选排序型 CGA。
