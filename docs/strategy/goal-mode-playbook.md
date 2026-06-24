# AI4SE 目标模式运行手册

本文是 Codex / AI Coding Agent 在目标模式下持续演进 AI4SE 的精简入口。它只保留每轮必须遵守的执行规则；详细模板、子智能体策略和 CI 等价验证分别下沉到专题附录，避免每轮把长示例和重复原则全部塞进上下文。

## 1. 定位

目标模式的职责不是复述 AI4SE 的仓库结构或机械执行任务清单，而是基于当前代码、文档、测试和用户最新目标，持续选择一个最有价值、可验收、风险可控的用户故事推进。仓库结构、架构事实、API 契约、测试命令和编码规范分别以 `AGENTS.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、`docs/CODING_STANDARDS.md` 和 `docs/DESIGN_PRINCIPLES.md` 为准。

目标模式由以下文件共同驱动：

- `AGENTS.md`：仓库级硬约束。本手册不重复其中的编码、架构、测试和提交细则。
- `docs/index.md`：项目知识库入口，说明模块、架构、API、数据、部署和深层文档导航。
- `docs/strategy/goal-mode-playbook.md`：目标模式通用运行入口，也就是本文档。
- `docs/strategy/goal-mode-cga-template.md`：CGA 模板、切片厚度门禁和常见过薄切片处理。
- `docs/strategy/goal-mode-subagents.md`：子智能体、并行协作、当前工作区保护和集成规则。
- `docs/strategy/goal-mode-ci-verification.md`：CI 等价验证、远端失败复盘和提交前验证表。
- `docs/todos/`：长期演进 todo，记录跨目标模式持续消化的高优先级产品、工程、测试和评判事项。
- `docs/plans/`：专项计划和专项目标模式规则。只有当本轮目标指向对应主题时，才展开相关计划。
- `docs/superpowers/specs/` 与 `docs/superpowers/plans/`：近期目标模式 spec / plan 产物。

提示词应保持短小，只引用稳定文件，不重复本手册、`AGENTS.md` 或深层需求文档中的细则。

## 2. 目标与授权边界

长期目标是让 AI4SE 保持为一个可本地部署、可演示、可持续演进的 AI for Software Engineering 工具集。具体模块职责不在本手册维护；每轮按启动协议读取稳定事实源，并在 CGA 中说明本轮实际消费了哪些模块事实。

如果用户没有指定本轮目标，默认从 `docs/todos/`、当前失败证据、活跃计划和相关 backlog 中选择最高优先级、尚未完成、当前上下文可推进的工作项；但每轮仍必须先做 Current State Gap Analysis，不能直接套用上一轮结论或固定清单。

如果用户指定了本轮主要目标，也必须快速扫描 `docs/todos/` 中的 P0/P1 条目。若存在与当前目标同向、低冲突、可形成纵向切片的高优先级 todo，应在 CGA 中纳入候选；若本轮不消化，必须说明暂缓原因和后续去向。

技术债、New Agents 专项演进、部署治理、评判体系等都属于可被目标模式处理的一类需求；只有当用户目标、todo 或 CGA 候选指向这些主题时，才读取对应专项计划，例如 `docs/plans/tech-debt.md`。

目标模式可以在符合 `AGENTS.md`、本手册、相关深层文档和当前代码事实的前提下，自主完成上下文读取、gap 排序、spec、plan、实现、验证和记录更新。不要把用户确认作为常规节点；普通澄清由 Agent 基于文档、代码、测试和合理 assumptions 自行回答，并在 spec 或收尾说明中记录。

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
5. 按任务方向读取相关事实源：架构、API、测试、编码规范、设计原则、todo、专项计划、已有 spec / plan、当前代码和测试。
6. 判断是否需要读取专题附录：CGA 模板见 `goal-mode-cga-template.md`，子智能体见 `goal-mode-subagents.md`，CI / 提交前验证见 `goal-mode-ci-verification.md`。
7. 第一个实质性工作产物必须是 Current State Gap Analysis。

不要先写 implementation plan、先改代码、先跑固定 todo 清单，或直接沿用上一轮记忆。

### 工作区保护

目标模式默认只在当前主工作区推进，不创建或切换 git worktree。启动时先记录 `git status --short`，限定本轮写入范围，只 stage 本轮相关文件；如需使用子智能体，按 `docs/strategy/goal-mode-subagents.md` 在当前工作区保护规则下分发只读探索、验证或严格限定写入范围的 worker。

只有用户明确要求使用独立工作区时，才允许重新讨论 worktree。默认情况下，CGA 或 spec 必须写清楚本轮允许写入路径和不会触碰的既有脏文件。不得因为任务简单就跳过 git 状态检查，也不得回滚、覆盖或格式化不属于本轮的改动。

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
11. `docs/todos/`
12. 与本轮相关的 `docs/todos/refactor/README.md` 当前入口、`docs/plans/`、`docs/superpowers/specs/`、`docs/superpowers/plans/`、测试需求、当前代码、测试、脚本和 git 历史。

如果某一轮只涉及特定模块，可以按需缩小读取范围，但必须在 CGA 中说明实际读取了哪些关键文件，以及哪些事实源因无关而未展开。

冲突裁决：

- 用户最新明确要求优先于历史文档。
- 当前代码和当前测试优先于过期文档。
- `AGENTS.md` 和本手册优先于普通计划文档。
- `docs/TESTING.md`、`docs/CODING_STANDARDS.md`、`docs/DESIGN_PRINCIPLES.md` 是工程护栏，不应被局部实现便利覆盖。
- 专项计划和专项规则只对其声明的目标范围生效；它们不能替代本手册的通用启动协议，但可以补充对应主题的执行规则。
- 归档 todo、历史计划和旧专项模板只能作为证据来源；如果其中的提交、用户确认、优先级或验证口径与本手册冲突，按本手册执行，并在 CGA 或收尾说明中记录取舍。

发现文档与代码冲突时，不要默默选择一边。必须在 spec、plan 或收尾说明中写清楚冲突、取舍和后续处理。

## 5. 每轮循环

每轮按以下顺序执行：

1. 重新读取事实源和相关代码，不依赖上一轮记忆。
2. 检查 git 状态并保护用户已有改动。
3. 执行 Current State Gap Analysis：把 todo 子项、用户反馈、测试失败和技术缺口聚合成候选能力包，列出排序依据、未选候选去向、边界和验收证据。CGA 详细模板见 `docs/strategy/goal-mode-cga-template.md`。
4. 选择一个且只选择一个用户故事（user story）。用户故事必须是用户可感知的完整能力包，或能独立降低后续演进风险的工程信任闭环。不得把单个控件、字段、helper、parser 分支、三方 merge 场景或单条测试当作独立用户故事，除非它本身解除阻断、风险或证据失真。
5. 选定用户故事后，用 Superpowers `brainstorming` 流程细化需求，再写中文 spec。目标模式的自动执行授权把用户审批节点改为 Agent 基于事实源的自问自答式裁决，但不能跳过上下文探索、澄清、方案比较、设计和测试思考。
6. 写中文 implementation plan，拆成本轮可执行步骤，并标注预计验证和提交边界。
7. 代码或行为变更按 `AGENTS.md` 和 Superpowers `test-driven-development` 技能执行；本手册不重复其具体流程。纯文档变更使用本节的文档核对清单。
8. 运行与本轮改动匹配的最小验证；触及共享行为、跨层协议或用户主路径时扩大验证范围。
9. 更新必要的文档记录，例如 `docs/todos/`、相关专项计划、spec / plan 或测试策略说明。
10. 完成型代码用户故事在进入提交或 push 前必须重跑仓库全量本地自动化，默认命令为 `./scripts/test/test-local.sh all`；这一步必须发生在最终代码和文档落定之后、`git commit` 之前。该命令必须让严重 lint、测试、构建或 E2E 失败反映为非零退出；如果脚本行为与此不一致，必须先修脚本或额外运行对应命令并在收尾说明中记录。只有纯文档变更、小范围无代码变更、环境权限阻塞或用户明确要求跳过时才允许例外，并必须在收尾说明中写明原因和风险。
11. 完成型用户故事在进入提交或 push 前必须做 CI 等价验证映射，详见 `docs/strategy/goal-mode-ci-verification.md`。全量本地自动化不能替代按改动风险选择的聚焦红绿测试；聚焦验证和全量验证都要报告。
12. 目标模式下，一个通过验证的完整用户故事默认必须形成聚焦 commit；如果用户明确要求不要提交、当前只是临时探索、验证未完成或存在未裁决风险，才可以暂不提交，并必须在收尾说明中写明原因。
13. 收尾说明必须列出改动、验证命令、未运行验证及原因、CI 等价覆盖判断、残余风险、提交 / push 状态和下一步候选。

## 6. 用户故事粒度门禁

目标模式默认切片单位是“完整用户故事”，不是“代码改动集合”。一个合格用户故事应能回答：

- 用户或调用方从哪里开始。
- 用户要完成什么真实动作。
- 系统完成什么核心处理。
- 成功后用户能看到、保存、恢复、下游消费或评判什么结果。
- 失败时如何显式停止、解释原因并给出下一步。
- 用什么测试、命令、截图、日志或 artifact 证明。
- 完成后能否用一句“用户现在可以...”或“调用方现在可以...”说清楚新增能力。

默认不通过的信号：

- 用户故事名称只能写成“新增字段”“补一个 endpoint”“修一个 parser”“调整一个按钮”“补一条测试”。
- 验收条件只验证内部函数，不验证 API、页面、工作流、下游消费或可见反馈。
- 当前切片显然只是某个用户动作链的前半段，而后半段没有技术阻断却被留到下一轮。
- 完成后只能汇报百分比增加 0.x%，但说不清用户多完成了什么。

不通过时，先尝试扩大边界，把同一用户场景下相邻的后端契约、前端服务、页面交互、状态持久化、错误反馈、下游消费和验证证据并入同一用户故事。只有扩大后会跨越不相关用户场景、显著增加破坏面，或当前候选本身解除 silent fallback、安全风险、证据失真或 CI 阻断时，才允许保持较小边界。

详细门禁、CGA 模板、过薄切片示例和能力包进度口径见 `docs/strategy/goal-mode-cga-template.md`。

## 7. 仓库事实消费规则

本手册不维护模块清单、技术栈、API 路径、workflow 配置面、测试矩阵或架构护栏的副本。CGA 和验收必须按本轮影响范围读取对应稳定事实源，并只在本轮产物中引用必要结论：

- 模块职责、开发命令和 New Agents 高优先级架构原则：`AGENTS.md`。
- 当前架构、服务拓扑、运行链路和模块细节：`docs/ARCHITECTURE.md`。
- HTTP/SSE/API 契约和请求响应结构：`docs/api-contracts.md`。
- 测试分层、New Agents 覆盖要求、真实模型 smoke 和 E2E / LLM judge 规则：`docs/TESTING.md`。
- 编码、设计、安全和失败显式化要求：`docs/CODING_STANDARDS.md` 与 `docs/DESIGN_PRINCIPLES.md`。

如果这些稳定事实源已经说明某条规则，本手册和本轮 spec / plan 只引用路径和本轮适用结论，不复制原文。发现事实源之间重复或冲突时，优先按第 4 节裁决，并把“是否需要收敛重复文档”作为后续文档候选记录。

## 8. 验证与记录

TDD 的具体执行方式由 `AGENTS.md` 和 Superpowers `test-driven-development` 技能承载，本手册不复述。目标模式只补充三条调度规则：

- 代码或行为变更必须在 plan 中说明将如何触发对应 TDD / 验收流程。
- 纯文档工作可以用文档核对清单替代代码测试，但必须说明没有运行代码测试的原因。
- 最终提交前运行仓库全量本地自动化。目标模式默认使用 `./scripts/test/test-local.sh all`；该脚本的覆盖范围和 CI 等价关系由 `docs/strategy/goal-mode-ci-verification.md` 与 `docs/TESTING.md` 维护，本手册不重复列举。

文档核对清单至少检查：

- 文档路径、链接和引用存在。
- 文档没有 `TODO`、`TBD` 或未解释的占位。
- 文档不与 `AGENTS.md`、`docs/index.md`、`docs/TESTING.md` 或当前代码事实冲突。
- 如果文档定义后续执行规则，必须说明它如何被目标模式读取和执行。

常用验证命令和 CI 等价验证规则见 `docs/strategy/goal-mode-ci-verification.md`。禁止模式、编码约束、安全要求和提交边界以 `AGENTS.md`、`docs/CODING_STANDARDS.md` 和 `docs/DESIGN_PRINCIPLES.md` 为准。

目标模式产物默认使用中文。英文只保留命令、路径、API、schema、类型名、包名、协议名和不可翻译专有名词。

建议产物位置：

- 本轮设计：`docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- 本轮计划：`docs/superpowers/plans/YYYY-MM-DD-<topic>.md`
- 长期 todo：`docs/todos/*.md`
- 专项计划或状态：`docs/plans/*.md`
- 通用目标模式规则：`docs/strategy/*.md`

如果本轮改动改变了用户主路径、部署方式、API 契约、测试门禁或 Agent 工作流，必须判断是否同步 `docs/index.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、`docs/component-inventory.md`、`docs/deployment-guide.md`、`docs/todos/` 或相关 `docs/plans/*.md`。如果决定不更新，收尾说明中要写原因。

## 9. 提交与 PR

普通任务默认不要自动 commit，除非用户本轮明确要求或任务本身规定必须提交。目标模式不同：每个完成必要实现、验证和文档记录的完整用户故事都应在进入下一用户故事前创建一个聚焦 commit，避免多个用户可感知能力包堆积成一个巨型提交。

提交边界：

1. 先确认 `git status -sb`，只 stage 本轮相关文件。
2. 先运行本轮必要聚焦验证、仓库全量本地自动化和 CI 等价映射，再提交；如果全量自动化失败，默认不得 commit 或 push，除非本轮任务就是记录/隔离该失败并已在收尾说明中明确风险。
3. 不把无关脏文件、生成包、临时缓存或用户未确认的删除一起提交。
4. 一个 commit 应对应一个用户可感知能力闭环、一个独立工程信任闭环或一个 bugfix。
5. 子智能体 / worker 不自行 commit 或 push；主 Agent 审查、集成并验证后按用户故事形成 commit。
6. 如果用户要求 push，则每个稳定用户故事 commit 后应及时 push，或按用户指定的一组稳定 commits 统一 push。
7. 收尾说明必须区分“最近 commit 的统计”和“当前未提交 diff”，并报告最新 commit SHA、`HEAD` 是否等于 `origin/<branch>`、当前未提交文件列表。

如果单个 commit 预计超过约 800 行、触达 8 个以上源文件、同时跨前端和后端运行时，或包含代码加测试加文档三类改动，必须先重新评估是否可拆成 checkpoint commit。只有当拆分会破坏可编译状态、割裂同一原子契约变更，或显著增加回归风险时，才允许保持一个 commit，并在收尾说明中解释原因。

PR 描述要求以 `AGENTS.md` 为准；目标模式收尾说明只补充用户故事边界、验证证据、CI 等价覆盖和未提交 / 未推送状态。

## 10. 目标模式提示词模板

```text
请按照 `AGENTS.md` 和 `docs/strategy/goal-mode-playbook.md` 进入目标模式，持续推进 AI4SE。

本轮目标：
- <写明长期目标或当前阶段目标>
- 如果没有更高优先级用户指令，优先从 `docs/todos/`、当前失败证据、活跃计划和相关 backlog 中选择最高优先级、尚未完成、当前可推进的工作项。
- 即使已有主要目标，也要扫描 `docs/todos/` 的 P0/P1 条目；与本轮目标同向时纳入 CGA 候选。

执行要求：
- 先读取 `AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md` 和当前目标相关深层文档。
- 检查 `git status --short`，保护用户已有改动。
- 第一个实质性产物必须是 Current State Gap Analysis。
- 每轮只选择一个可验收用户故事；该用户故事必须是用户可感知的完整能力包，或有独立价值的工程信任闭环。
- 选定用户故事后，先做中文自问自答头脑风暴，再生成中文 spec。
- 代码或行为变更按 `AGENTS.md` 和 Superpowers `test-driven-development` 技能执行；纯文档工作用核对清单替代代码测试并说明原因。
- 运行相关验证；无法运行的验证要说明原因。
- 完成型代码用户故事在 commit / push 前默认运行 `./scripts/test/test-local.sh all`；纯文档、小范围无代码、环境阻塞或我明确要求跳过时才可例外，并说明风险。
- commit / push 前运行本轮改动对应的本地 CI 等价验证；未运行或失败必须说明，并默认暂缓 push。
- 除非我明确要求不要 commit，否则完成型用户故事应形成聚焦 commit。

请开始执行，并在关键节点给出简短进度说明。
```
