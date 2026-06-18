# AI4SE 目标模式运行手册

本文是 Codex / AI Coding Agent 在目标模式下持续演进 AI4SE 的运行手册。它用于减少目标提示词长度，把稳定执行方式沉淀为可版本化文档，并避免每轮都重新解释仓库结构、事实源、选题、验证和收尾规则。

## 1. 定位

AI4SE 是一个 Docker Compose 驱动的模块化 monorepo，包含统一门户、意图测试工具、New Agents 智能体工作台、共享配置和数据库工具。目标模式的职责不是机械执行任务清单，而是基于当前代码、文档、测试和用户最新目标，持续选择一个最有价值、可验收、风险可控的纵向切片推进。

目标模式由以下文件共同驱动：

- 启动提示词：只负责启动目标模式、指定本轮长期 / 短期目标入口，并要求第一步产出 Current State Gap Analysis。
- `AGENTS.md`：仓库级硬约束，例如 TDD、命名、禁止 silent fallback、禁止硬编码密钥、提交和 PR 习惯。
- `docs/index.md`：项目知识库入口，说明 AI4SE 的模块、架构、API、数据、部署和深层文档导航。
- `docs/strategy/goal-mode-playbook.md`：目标模式通用运行规则，也就是本文档。
- `docs/plans/goal-mode-tech-debt-rules.md`：New Agents 技术债消化的专项目标模式规则。
- `docs/plans/tech-debt.md`：当前 New Agents 功能问题、技术债、修复记录和后续候选。
- `docs/superpowers/specs/` 与 `docs/superpowers/plans/`：近期目标模式 spec / plan 产物。

提示词应保持短小，只引用稳定文件，不重复本手册、`AGENTS.md` 或深层需求文档中的细则。具体读取顺序、选题规则、产物位置、验证命令、提交边界和停机条件都由本手册承载。

## 2. 目标与授权边界

长期目标是让 AI4SE 保持为一个可本地部署、可演示、可持续演进的 AI for Software Engineering 工具集：

- `tools/frontend/` 提供统一入口和产品门户。
- `tools/intent-tester/` 提供 Flask + MidScene / Playwright 的意图测试能力。
- `tools/new-agents/` 提供结构化 Agent Runtime、typed SSE、多阶段工作流和可信 artifact 输出。
- `tools/shared/`、`scripts/`、`docs/` 提供共享配置、运维、测试和知识库基础设施。

如果用户没有指定本轮目标，默认从 `docs/plans/tech-debt.md` 中选择最高优先级、尚未完成、当前上下文可推进的 New Agents 工作项；但每轮仍必须先做 Current State Gap Analysis，不能直接套用上一轮结论或固定清单。

目标模式可以在符合 `AGENTS.md`、本手册、相关深层文档和当前代码事实的前提下，自主完成上下文读取、gap 排序、spec、plan、TDD 实现、验证和记录更新。

不要把用户确认作为常规节点。普通澄清由 Agent 基于文档、代码、测试和合理 assumptions 自行回答，并在 spec 或收尾说明中记录。

只有以下情况才停止并向用户汇报：

- 需要用户提供权限、凭证、外部服务访问、浏览器登录态或仓库访问。
- 当前任务需要联网安装依赖、访问模型供应商或调用外部 API，而环境未授权。
- 连续阻塞，且无法通过当前文档、代码、测试或合理 assumptions 推进。
- 用户最新消息明确要求暂停、只讨论、不改代码或等待确认。
- 当前架构、文档事实或用户目标之间存在无法自行裁决的根本冲突。

## 3. 启动协议

每轮目标模式启动后，先执行启动协议：

1. 读取 `AGENTS.md`。
2. 读取本手册。
3. 读取 `docs/index.md`，获取当前项目结构和深层文档导航。
4. 检查 `git status --short`。如果存在未提交变更，必须判断它们是用户改动、上一轮遗留还是当前轮输入；不得覆盖、回滚或格式化不属于本轮的变更。
5. 按任务方向读取相关事实源：架构、API、测试、编码规范、设计原则、技术债、已有 spec / plan、当前代码和测试。
6. 第一个实质性工作产物必须是 Current State Gap Analysis。

不要先写 implementation plan、先改代码、先跑固定 todo 清单，或直接沿用上一轮记忆。

## 4. 事实源与冲突优先级

每轮判断都必须基于当前文件，而不是上一轮记忆。

事实源默认顺序：

1. `AGENTS.md`
2. `docs/strategy/goal-mode-playbook.md`
3. `docs/index.md`
4. `docs/ARCHITECTURE.md`
5. `docs/api-contracts.md`
6. `docs/TESTING.md`
7. `docs/CODING_STANDARDS.md`
8. `docs/DESIGN_PRINCIPLES.md`
9. `docs/integration-architecture.md`
10. `docs/component-inventory.md`
11. `docs/plans/tech-debt.md`
12. `docs/plans/goal-mode-tech-debt-rules.md`
13. 与本轮相关的 `docs/superpowers/specs/`、`docs/superpowers/plans/`、测试需求、当前代码、测试、脚本和 git 历史。

如果某一轮只涉及特定模块，可以按需缩小读取范围，但必须在 CGA 中说明实际读取了哪些关键文件，以及哪些事实源因无关而未展开。

冲突裁决：

- 用户最新明确要求优先于历史文档。
- 当前代码和当前测试优先于过期文档。
- `AGENTS.md` 和本手册优先于普通计划文档。
- `docs/TESTING.md`、`docs/CODING_STANDARDS.md`、`docs/DESIGN_PRINCIPLES.md` 是工程护栏，不应被局部实现便利覆盖。
- `docs/plans/goal-mode-tech-debt-rules.md` 只对技术债目标模式生效；它不能替代本手册的通用启动协议，但可以补充 New Agents 专项规则。

发现文档与代码冲突时，不要默默选择一边。必须在 spec、plan 或收尾说明中写清楚冲突、取舍和后续处理。

## 5. 每轮循环

每轮按以下顺序执行：

1. 重新读取事实源和相关代码，不依赖上一轮记忆。
2. 检查 git 状态并保护用户已有改动。
3. 执行 Current State Gap Analysis：列出候选 gap、排序依据、未选候选去向、边界和验收证据。
4. 选择一个且只选择一个 milestone。milestone 必须是用户可观察的阶段动作，或能独立降低后续演进风险的工程信任闭环。
5. 写中文 spec，包含用户故事、场景、验收条件、风险、文件范围和验证计划。
6. 写中文 implementation plan，拆成 TDD 可执行步骤。
7. 先写失败测试或等价验收检查，再实现最小改动，再重构清理。
8. 运行与本轮改动匹配的最小验证；触及共享行为、跨层协议或用户主路径时扩大验证范围。
9. 更新必要的文档记录，例如 `docs/plans/tech-debt.md`、相关 spec / plan 或测试策略说明。
10. 如果用户或目标提示词明确要求提交，验证通过后创建聚焦 commit；未明确要求时不要自动 commit。
11. 收尾说明必须列出改动、验证命令、未运行验证及原因、残余风险和下一步候选。

### 5.1 子智能体加速规则

目标模式鼓励使用子智能体加速开发，但子智能体是并行执行工具，不是跳过 TDD、系统性调试或验证门禁的理由。主 Agent 始终负责选题、边界、最终集成和完成声明。

优先使用子智能体的场景：

- **Explorer 子智能体**: 用于并行读取独立事实源、定位候选缺口、审计文档冲突、梳理测试失败分组。Explorer 默认只读，不改文件；输出必须包含证据路径和结论边界。
- **Worker 子智能体**: 用于已有明确 spec / plan、且写入范围彼此独立的实现任务。分发时必须说明文件所有权、测试命令、禁止回滚他人改动，并要求直接在其工作区完成补丁。
- **Reviewer / Verification 子智能体**: 用于实现后做 spec 符合性审查、代码质量审查、风险点复核或并行运行独立验证。审查结果不能替代主 Agent 的最终 diff 检查和必要验证。

默认流程：

满足下列默认触发点时应分发子智能体；如果因为任务过小、执行环境不支持、上下文不足或用户只读要求而跳过，必须在 CGA 或收尾说明中记录原因。

1. 在 CGA 阶段，如果存在 2 个以上独立候选或多个事实源可并行读取，分发 explorer 子智能体并行审计。
2. 在 implementation plan 阶段，如果任务可拆成互不重叠的文件或模块切片，优先采用 `superpowers:subagent-driven-development`：每个任务由新 worker 实现，再经过 spec review 和 quality review。AI4SE 仓库规则覆盖该技能示例中的自动 commit 行为；worker 不得创建 commit，除非用户本轮明确要求提交。
3. 在多处失败彼此独立时，采用 `superpowers:dispatching-parallel-agents`：按失败文件、子系统或问题域分发，不让多个子智能体同时修改同一文件集合。
4. 子智能体运行期间，主 Agent 继续做不重叠工作，例如补文档、准备验证、审查其他模块；不要空等。主 Agent 不得同时修改 worker 所有权范围或共享记录文件；如必须更新 `docs/plans/tech-debt.md`、当前 plan 或 playbook，先把这些文件纳入主 Agent 保留范围，待 worker 返回后统一集成。
5. 子智能体返回后，主 Agent 必须审查其变更、解决冲突、运行必要验证，并把实际结果写入收尾说明。

如果用户要求“持续修技术债”但没有指定下一个缺陷，主 Agent 应优先把只读 explorer 用作候选发现器：每个 explorer 聚焦一个独立问题域，返回可复现现象、证据路径、建议 RED 用例和风险边界。主 Agent 只从这些候选中选择一个当前切片进入 TDD 修复；未选候选必须写入 `docs/plans/tech-debt.md`、当前计划或下一轮候选说明，避免子智能体发现被丢失。

当前仓库经常处于大规模未提交变更状态。分发任何可写 worker 前，主 Agent 必须先记录 `git status --short`，在提示中列出允许写入路径，并明确禁止 worker 修改该范围之外的文件。worker 返回后，主 Agent 必须用 `git diff -- <允许路径>` 和 `git status --short` 核对实际写入范围；如果发现越界改动，先隔离并审查，不得直接合并到当前切片。

子智能体验收至少包含三步：先读其最终说明，确认是否有 `NEEDS_CONTEXT`、`BLOCKED` 或未运行验证；再检查实际 diff 是否满足 spec 且没有额外重构；最后由主 Agent 在当前上下文重新运行本切片最小验证。只有这三步都完成后，子智能体结果才能进入完成记录。

不要使用子智能体的场景：

- 问题尚未分清边界，多个症状可能来自同一个根因。
- 任务需要连续修改同一文件或共享状态，多个 worker 会互相覆盖。
- 只是单行修复、单个聚焦测试或主 Agent 已经持有完整上下文，分发成本高于收益。
- 子智能体需要凭证、联网、浏览器登录态或外部权限，而主 Agent 尚未取得用户授权。
- 当前执行环境没有可用子智能体或任务分发能力；此时不要强行模拟并行，改为顺序执行只读探索或实现，并记录降级原因。

子智能体输出必须被当作工程输入，而不是完成证明。任何“已修复”“测试通过”“可合并”的说法，都必须由主 Agent 在当前上下文重新核对证据后才能对用户声明。

## 6. Current State Gap Analysis

CGA 的目标是基于最新代码、测试、文档和用户目标，判断下一步最有价值、最可验收、最少破坏当前契约的工作包。

每轮 CGA 必须包含：

- 事实源快照：本轮实际读取了哪些关键文件。
- 候选 gap：至少 2 个候选；如果确实只有 1 个，也要说明原因。
- 排序依据：为什么选中的 gap 比其他候选更适合作为本轮 milestone。
- 未选候选去向：保留为下一轮候选、写入技术债、归入更大工作包、标记 blocked / wont-do，或明确暂不处理。
- 验收口径：每个候选都要说明可以被什么证据验证。
- 边界判断：哪些内容进入本轮，哪些内容不进入本轮。

建议模板：

```markdown
### Current State Gap Analysis

事实源快照：
- 已读取：<列出本轮实际读取的关键文件>
- 按需未展开：<列出因无关而未展开的事实源，或写“无”>

候选 gap：
| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | docs/plans/tech-debt.md / 用户反馈 / 测试失败 | <目标态> | <当前能力> | <缺口> | <价值> | <风险/复杂度> | <验证方式> | 本轮 |
| B | <来源> | <目标态> | <当前能力> | <缺口> | <价值> | <风险/复杂度> | <验证方式> | 下一轮候选 |

排序结论：
1. 选择 A，因为 <选择理由>。
2. B 暂不选，因为 <暂缓理由和去向>。

本轮 milestone：
作为 <角色>，当我 <处于真实场景>，我可以 <完成完整动作或获得可信结果>，从而 <产生独立价值>。

验收条件：
1. Given <用户或调用方前提>
   When <触发动作>
   Then <用户可观察结果>
   Evidence: <测试、命令、artifact、日志、截图或文档证据>
```

CGA 要足够完整但不过度复述。已在 `AGENTS.md`、本手册或深层文档中稳定存在的规则，不要复制成长篇说明；只需引用事实源并说明本轮如何遵守。

## 7. Milestone 选择与粒度

AI4SE 不维护固定路线图。目标模式选题时，应同时考虑用户最新目标、当前代码事实、技术债优先级、测试可行性和用户可观察价值。

优先级默认如下：

1. 用户最新明确目标。
2. 阻断主路径演示、使用或部署的 P0 问题。
3. 会导致 silent fallback、协议混用、密钥泄露、错误写入或证据失真的工程风险。
4. `docs/plans/tech-debt.md` 中高优先级且可形成纵向切片的工作项。
5. 能提高后续目标模式迭代可信度的测试、验证和文档护栏。
6. 普通清理、性能优化和历史文档整理。

一个合格 milestone 应能回答：

- 用户或调用方从哪里开始。
- 用户看到什么状态、说明、选择或风险。
- 用户做出什么决定，或调用方完成什么动作。
- 系统执行什么核心能力。
- 成功后接到主流程哪里。
- 失败时如何显式停止、解释原因并给出下一步。
- 有哪些 evidence 可以证明这条链路真的走通。

常见过薄切片及处理方式：

| 过薄切片 | 为什么过薄 | 应并入的厚切片 |
| --- | --- | --- |
| 只新增 schema / 类型 | 只有机器契约，没有用户可见结果和消费链路 | 并入 API / SSE / 前端状态写入 / 测试证据闭环 |
| 只修一个 parser 分支 | 用户只获得错误分类，主流程没有新增可理解能力 | 并入请求边界、错误文案、端点测试和 UI 可见错误 |
| 只改 prompt | LLM 输入改变但用户价值不可证明 | 并入 artifact 质量、契约校验、真实或 mock 输出验收 |
| 只补测试 | 验证加强但能力不变 | 并入对应用户故事的 TDD / 验收任务；工程信任闭环例外需说明独立价值 |
| 只更新文档措辞 | 不改变后续执行行为或当前能力边界 | 并入当前主路径文案、playbook 规则或稳定事实源校准 |

受控例外：如果某个底层缺口会导致后续工作出现 silent fallback、安全风险、证据失真或无法验证，允许作为工程信任闭环进入 milestone。但它仍必须给调用方或后续目标模式提供独立价值，不能停在内部 helper。

## 8. AI4SE 模块映射

不同模块的纵向切片形态不同，CGA 和验收应按模块映射。

### 统一门户 `tools/frontend/`

- 用户入口：`/`、`/profile` 和门户导航。
- 核心风险：链接失效、模块入口误导、构建失败、响应式布局破损。
- 典型证据：组件测试、`npm run build`、截图或浏览器 walkthrough。

### Intent Tester `tools/intent-tester/`

- 用户入口：测试用例管理、执行记录、MidScene / Playwright 操作、WebSocket 进度。
- 核心风险：执行编排断裂、浏览器自动化代理不可用、变量解析错误、下载包过期。
- 典型证据：Flask API 测试、Jest proxy 测试、执行 service 测试、必要时浏览器级验证。

### New Agents `tools/new-agents/`

- 用户入口：Agent 选择、Workflow 选择、Workspace 对话、阶段确认、Artifact 预览和导出。
- 核心风险：LLM 输出污染协议、typed SSE 解析错误、阶段推进错乱、左侧 chat 与右侧 artifact 混用、默认 LLM 配置缺失、认证 / 网关不一致。
- 典型证据：后端契约测试、API / SSE 测试、前端流解析测试、状态编排测试、浏览器工作流测试、可选真实模型 smoke。
- 架构原则：所有 Agent 共用一套运行时、typed SSE/API、状态编排和 UI 基础设施；Lisa、Alex 以及后续 Agent 只能通过 `agentId`、workflow 配置、阶段 prompt、artifact template 和后端契约差异化。除非用户明确批准架构变更，不得新增 agent-specific runtime、独立流式端点、独立 store 或专用渲染管线。
- 工作流变更必须同步检查 frontend `WORKFLOWS` / slug / agent workflow listing、backend `WORKFLOW_STAGES` / artifact contract headings、prompt/template 文件和共享运行链路测试。差异优先表达为配置或契约，不要写成基础设施分支。

### Shared / Scripts / Docker

- 用户入口：`./scripts/dev/deploy-dev.sh`、Docker Compose、迁移脚本、健康检查。
- 核心风险：环境变量落点错误、服务端口暴露不一致、密钥进入前端、脚本不可执行。
- 典型证据：shell 语法检查、Compose config 渲染、健康检查、最小服务启动验证。

## 9. TDD 与实现规则

默认执行 TDD：

1. 先写或更新失败测试，证明当前缺口存在。
2. 运行聚焦测试，确认失败原因符合预期。
3. 写最小实现让测试通过。
4. 运行聚焦测试确认通过。
5. 根据风险扩大验证范围。
6. 必要时重构，但不得改变本轮目标边界。

纯文档工作可以用文档核对清单替代代码测试，但必须说明没有运行代码测试的原因，并至少做以下检查：

- 文档路径、链接和引用存在。
- 文档没有 `TODO`、`TBD` 或未解释的占位。
- 文档不与 `AGENTS.md`、`docs/index.md`、`docs/TESTING.md` 或当前代码事实冲突。
- 如果文档定义后续执行规则，必须说明它如何被目标模式读取和执行。

禁止事项：

- 禁止引入 `as any`、`@ts-ignore`、空 `catch`、裸 `except Exception` 或静默 fallback。
- 禁止用隐藏 fallback、生产 mock、假数据、固定成功响应或静默降级掩盖真实错误。数据、协议或业务逻辑不满足契约时，必须显式失败并返回可诊断错误；不能为了让用户“看起来有结果”而给出不真实返回。
- 禁止为了让测试通过而删除断言、降低 schema 严格度或绕过协议校验。
- 禁止在前端源码、测试快照、文档示例中写入真实 API Key、Token 或密码。
- 禁止保留废弃协议作为“以防万一”的兼容层，除非本轮目标明确要求过渡且有移除计划。
- 禁止覆盖、回滚或格式化不属于本轮的用户改动。

## 10. 验证矩阵

按本轮影响范围选择验证命令。不要声称未运行的测试已通过。

| 影响范围 | 推荐验证 |
| --- | --- |
| 全仓 Python 语法风险 | `flake8 --select=E9,F63,F7,F82 .` |
| 全仓本地验证 | `./scripts/test/test-local.sh` |
| Docker 开发栈 | `./scripts/dev/deploy-dev.sh`，必要时配合健康检查 |
| New Agents 后端 | `cd tools/new-agents/backend && python3 -m pytest -m "not slow" -q` |
| New Agents 后端语法兜底 | `python3 -m py_compile <changed-python-files>` |
| New Agents 前端 | `cd tools/new-agents/frontend && npm test` |
| New Agents 前端类型 / lint | `cd tools/new-agents/frontend && npm run lint` |
| New Agents 前端构建 | `cd tools/new-agents/frontend && npm run build` |
| New Agents 浏览器工作流 | `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q` |
| Intent Tester proxy | `cd tools/intent-tester && npm run test:proxy` |
| 统一门户 | `cd tools/frontend && npm run build` |
| Compose 配置 | `docker compose -f docker-compose.dev.yml config --services`，按需检查 `dev-cn` / `prod` |

真实模型 smoke 只在用户明确要求、环境变量齐备且网络 / 额度可用时运行。缺少 key 或 provider 失败时要明确说明，不能把 mock 测试说成真实模型验证。

## 11. 文档与记录

目标模式产物默认使用中文。英文只保留命令、路径、API、schema、类型名、包名、协议名和不可翻译专有名词。

建议产物位置：

- 本轮设计：`docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- 本轮计划：`docs/superpowers/plans/YYYY-MM-DD-<topic>.md`
- 技术债状态：`docs/plans/tech-debt.md`
- 目标模式专项规则：`docs/plans/goal-mode-tech-debt-rules.md`
- 通用目标模式规则：`docs/strategy/goal-mode-playbook.md`

如果本轮改动改变了用户主路径、部署方式、API 契约、测试门禁或 Agent 工作流，必须判断是否同步以下文档：

- `docs/index.md`
- `docs/ARCHITECTURE.md`
- `docs/api-contracts.md`
- `docs/TESTING.md`
- `docs/component-inventory.md`
- `docs/deployment-guide.md`
- `docs/plans/tech-debt.md`

如果决定不更新，收尾说明中要写原因，例如“只改内部测试，不改变公开契约”。

## 12. 提交与 PR

默认不要自动 commit，除非用户本轮明确要求、目标提示词明确要求，或当前目标模式任务本身规定必须提交。

如果需要提交：

1. 先确认 `git status --short`，只 stage 本轮相关文件。
2. 运行本轮必要验证。
3. commit 信息保持聚焦，符合仓库近期习惯：中文祈使句或 Conventional Commit，例如 `fix(new-agents): 修复阶段确认续写污染`。
4. 不把无关脏文件、生成包、临时缓存或用户未确认的删除一起提交。

PR 描述应包含：

- 问题背景。
- 解决方案。
- 影响模块。
- 验证命令和结果。
- UI 变化截图或说明。
- 未覆盖风险和后续工作。

## 13. 目标模式提示词模板

```text
请按照 `AGENTS.md` 和 `docs/strategy/goal-mode-playbook.md` 进入目标模式，持续推进 AI4SE。

本轮目标：
- <写明长期目标或当前阶段目标>
- 如果没有更高优先级用户指令，优先从 `docs/plans/tech-debt.md` 中选择最高优先级、尚未完成、当前可推进的工作项。

执行要求：
- 先读取 `AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md` 和当前目标相关深层文档。
- 检查 `git status --short`，保护用户已有改动。
- 第一个实质性产物必须是 Current State Gap Analysis。
- 每轮只选择一个可验收 milestone。
- 鼓励按需使用子智能体加速只读探索、独立实现切片和复核验证；主 Agent 负责最终集成与完成判断。
- 严格执行 TDD；纯文档工作用核对清单替代代码测试并说明原因。
- 运行相关验证；无法运行的验证要说明原因。
- 未经我明确要求不要 commit。

请开始执行，并在关键节点给出简短进度说明。
```
