# Codex 目标模式技术债消化规则

> 适用范围: 使用 Codex 目标模式逐步消化 `docs/plans/tech-debt.md` 中的 New Agents 技术债工作项。
> 更新日期: 2026-06-05

## 目标

让 Codex 在目标模式中持续、分阶段、可验证地推进 `docs/plans/tech-debt.md`，每次只处理一个明确工作项，遵循 TDD、文档驱动和项目现有约束，避免一次性大改导致不可控。

## 输入文档

目标模式执行时必须优先读取:

- `AGENTS.md`
- `docs/index.md`
- `docs/plans/tech-debt.md`
- 与当前工作项相关的深层文档，例如:
  - `docs/architecture.md`
  - `docs/integration-architecture.md`
  - `docs/api-contracts.md`
  - `docs/TESTING.md`
  - `docs/CODING_STANDARDS.md`
  - `docs/DESIGN_PRINCIPLES.md`
  - `docs/component-inventory.md`
  - `docs/development-guide.md`

如果工作项涉及外部库，必须优先查询官方文档；本项目约定使用 Context7 查询外部库文档。如果当前环境没有 Context7 工具，必须明确说明，并使用官方文档或官方仓库作为替代依据。

## 工作项选择规则

1. 从 `docs/plans/tech-debt.md` 中选择优先级最高、尚未完成、可以在当前上下文推进的工作项。
2. 默认顺序按 `P0`、`P1`、`P2`、`P3` 推进。
3. 如果同优先级内有多个工作项，优先选择依赖最少、验证路径最清楚的工作项。
4. 不允许跳过 `P0` 工作项去做后续清理，除非当前 `P0` 明确被阻塞。
5. 如果工作项过大，必须先拆成一个可落地的最小垂直切片，并把拆分结果写回计划文档或实现计划文档。

## 执行循环

每轮目标模式必须遵循以下循环:

1. **读取上下文**
   - 读取 `docs/plans/tech-debt.md`。
   - 读取当前工作项相关代码、测试和文档。
   - 检查 `git status --short`，不得覆盖用户已有改动。

2. **定义本轮切片**
   - 明确本轮只完成哪个工作项或哪个子切片。
   - 明确涉及文件、测试命令、验收标准。
   - 如果需要引入依赖，先修改对应 `requirements.txt` 或 `package.json`，并说明原因。

3. **TDD 红绿重构**
   - 先写失败测试，证明当前缺口存在。
   - 再写最小实现让测试通过。
   - 最后在测试通过前提下清理结构。
   - 如果是纯文档工作，可以用文档核对清单替代代码测试，但必须说明没有运行代码测试的原因。

4. **确定性优先**
   - 不做静默降级。
   - 不吞异常。
   - 不用隐藏 fallback、生产 mock、假数据或固定成功响应掩盖数据/逻辑错误。
   - 数据、协议或业务逻辑不满足契约时，直接抛出或返回 typed error，让用户看到真实、可诊断的失败原因。
   - 不用兼容层保留废弃协议，除非当前工作项明确要求临时过渡。
   - 对结构化协议、API 契约、模型字段使用显式 schema 和测试约束。

5. **共享 Agent 基础设施优先**
   - `tools/new-agents` 中所有 Agent 必须复用同一套运行时、typed SSE/API、状态编排和 UI 基础设施。
   - Lisa、Alex 和后续 Agent 的差异只能通过 `agentId`、workflow 配置、阶段 prompt、artifact template、onboarding 文案和后端 artifact 契约表达。
   - 禁止为了单个 Agent 或单个 workflow 新增平行 runtime、独立流式端点、独立 store、专用渲染管线或旧协议兼容路径，除非用户明确批准并有文档化迁移计划。
   - 任何 workflow 变更都必须同步检查 frontend `WORKFLOWS` / slug / agent workflow listing、backend `WORKFLOW_STAGES` / artifact contract headings、prompt/template 文件和共享运行链路测试。

6. **验证**
   - 运行与本轮改动最相关的最小测试。
   - 如果触及共享行为或工作流主链路，继续运行更大范围测试。
   - 前端常用验证:
     - `cd tools/new-agents/frontend && npm test`
     - `cd tools/new-agents/frontend && npm run lint`
   - 后端常用验证:
     - `cd tools/new-agents/backend && pytest`
   - 如未运行某项验证，必须说明原因。

7. **更新记录**
   - 如果工作项完成，更新 `docs/plans/tech-debt.md` 或对应实施计划，记录完成状态和验证证据。
   - 如果只完成部分切片，记录下一步最小动作。
   - 不要未经用户明确要求 commit。

## 子智能体加速规则

New Agents 技术债修复默认鼓励使用子智能体，但主 Agent 必须保持一个清晰的当前切片，负责最终集成、验证和记录更新。

推荐分工:

1. **Explorer**: 在 CGA 或系统性调试阶段并行审计独立问题域，例如前端流解析、状态编排、后端请求 schema、SSE 契约、Compose / Nginx 配置。Explorer 只读，输出根因证据、候选修复点和建议验证，不直接改文件。
2. **Worker**: 在已有明确 RED 用例或 implementation plan 后执行独立补丁。每个 worker 必须有不重叠的文件所有权，例如只负责 `tools/new-agents/backend/request_schemas.py` 及对应测试，或只负责 `tools/new-agents/frontend/src/core/llm.ts` 及对应测试。
3. **Reviewer / Verification**: 在 worker 或主 Agent 完成切片后，独立检查 spec 符合性、禁止模式、协议契约和验证缺口。reviewer 只能提出问题和证据，是否修改由主 Agent 或对应 worker 处理。

默认触发点:

- 同时存在 2 个以上候选技术债，且它们分属不同模块时，先分发 explorer 并行读取，再由主 Agent 选择本轮 milestone。
- 一个工作项拆成多个互不重叠的文件切片时，优先使用 `superpowers:subagent-driven-development`，按任务逐个派发 worker，并在每个任务后做 spec review 与 quality review。worker 只提交补丁结果、测试证据和风险说明，不创建 commit；commit 仍由主 Agent 按仓库提交规则处理。
- 多个测试文件失败且根因看起来独立时，使用 `superpowers:dispatching-parallel-agents`，按测试文件或问题域分发调查。
- 浏览器级验证、文档规则审查、禁止模式扫描等可以与主实现并行时，可分发 verification 子智能体，但最终完成声明仍以主 Agent 读取的命令输出和 diff 为准。
- 当前工作区有大量未提交改动时，优先使用只读 explorer 和 verification 子智能体；只有在可写范围能被精确限定到不重叠文件集合时，才分发 worker。
- 没有指定下一个修复项时，至少优先考虑分发只读 explorer 搜索候选缺陷；explorer 必须返回建议 RED 用例和证据路径，主 Agent 再选择一个切片亲自或通过单个 worker 执行 RED → GREEN → 验证。

禁止并行分发的情况:

- 多个子智能体会修改同一文件、同一 store 状态机、同一 API schema 或同一测试文件。
- 还没有完成根因定位，只是对同一症状提出多个猜测性修复。
- 当前任务需要按顺序执行 RED → GREEN → REFACTOR，后一项依赖前一项输出。
- 工作区已有未归因的大量用户改动，且子智能体无法获得足够上下文来避免覆盖。

分发提示必须包含:

- 目标问题和验收标准。
- 允许读取和修改的文件范围。
- 必须遵守 `AGENTS.md`、TDD、禁止回滚他人改动、禁止 `as any` / `@ts-ignore` / 静默 fallback。
- 需要返回的证据: 根因、改动文件、RED / GREEN 命令、未运行验证及原因、残余风险。
- 统一状态: `status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED`，并列出读取文件、修改文件、验证命令与结果、未运行验证、残余风险。

主 Agent 验收子智能体结果时必须:

- 对照分发提示核对实际改动是否越界。
- 读取相关 diff，而不是只信任子智能体摘要。
- 在当前上下文重新运行本切片最小验证；如环境无法运行，必须记录阻塞原因和替代验证。
- 将子智能体输出中的残余风险写入 `docs/plans/tech-debt.md` 或收尾说明，不得静默丢弃。
- 将未采纳的子智能体候选写入 `docs/plans/tech-debt.md`、当前计划或下一轮候选说明，确保并行探索结果不会只停留在对话上下文中。

## PydanticAI P0 工作项专用规则

`P0: 引入 PydanticAI 约束智能体输出结构` 是当前第一优先级。执行时必须遵循:

1. 先做最小试点，不全量迁移所有工作流。
2. 试点范围演进:
   - 初始试点从后端新增实验 Agent Runtime 开始。
   - 初始覆盖 `TEST_DESIGN` 工作流的 `CLARIFY` 阶段，再逐步扩展到其他工作流和阶段。
   - 当前主链路已迁移到 `/api/agent/runs/stream`，旧 `/api/chat/stream` 已删除；后续工作不得恢复旧文本代理端点或旧标签协议作为兼容层。
3. 输出协议必须由 Pydantic 模型表达，不能继续依赖 `<CHAT>`、`<ARTIFACT>`、`<ACTION>` 文本标签作为核心协议。
4. 前端只消费 typed event，不直接信任 LLM 自由文本。
5. 结构化输出之后还必须做应用级校验:
   - Artifact 是否为空。
   - 阶段动作是否合法。
   - Mermaid 代码块是否可解析。
   - Markdown 是否满足当前阶段模板的最低结构要求。
6. 如果 PydanticAI 引入成本或兼容性不符合预期，必须保留失败证据，并给出替代方案，例如仅使用 Pydantic schema + OpenAI structured output 兼容层。
7. 依赖选择默认使用 `pydantic-ai-slim[openai]`，不要使用全量 `pydantic-ai` 元包，避免无关 provider extras 拉长解析时间并污染运行环境。
8. 当前后端试点已固定为 `pydantic-ai-slim[openai]==1.104.0` 与 `openai>=2.29.0,<3`；该版本来自本地 Docker 构建使用的 PyPI 镜像可解析版本集合，后续变更版本时必须先查官方文档或官方包元数据，并重新跑后端测试。

## LangGraph 决策规则

当前不把 LangGraph 作为主线引入。

除非出现以下至少一种情况，否则不要把当前轻量阶段工作流迁移到 LangGraph:

- 需要跨阶段自由回跳。
- 需要并行子任务或多 Agent 协作。
- 需要长任务恢复、checkpoint 回放、后台任务继续执行。
- 需要复杂人工审批流。
- 单纯 reducer/state machine 已经无法清晰表达当前业务流程。

如果后续评估 LangGraph，必须先写独立 Spike 文档，不允许在 PydanticAI 输出结构化试点中顺手引入。

## 禁止事项

- 禁止一次性重写整个 New Agents。
- 禁止在没有测试保护时改核心 Agent 协议。
- 禁止为了让测试通过而删除失败测试。
- 禁止把 API Key、Token、密码写入源码、测试快照或文档示例中的真实值。
- 禁止用 `as any`、`@ts-ignore`、`@ts-expect-error` 规避类型问题。
- 禁止新增静默 fallback 来掩盖协议错误。
- 禁止绕过项目脚本直接做 Docker 底层操作。

## 完成判定

一个工作项只有同时满足以下条件，才能标记为完成:

- 需求在代码、测试或文档中有明确落点。
- 相关测试和 lint 已通过，或未运行的原因被明确记录。
- 没有引入新的禁止模式。
- 技术债文档或实施计划已更新。
- `git diff` 只包含本轮目标相关变更。

## 目标模式提示词模板

在 Codex 目标模式中可以使用以下提示词:

```text
请按照 `docs/plans/goal-mode-tech-debt-rules.md` 的规则，持续消化 `docs/plans/tech-debt.md` 中的 New Agents 技术债。

本轮请从最高优先级、尚未完成、且当前上下文可推进的工作项开始。默认优先处理 `P0: 引入 PydanticAI 约束智能体输出结构`，除非你在读取当前代码和文档后证明它被阻塞。

执行要求:
- 全程遵循 `AGENTS.md`。
- 先读取 `docs/index.md`、`docs/plans/tech-debt.md`、`docs/plans/goal-mode-tech-debt-rules.md` 以及当前工作项相关深层文档。
- 不要一次性重写整个 New Agents；每轮只做一个可验证的最小垂直切片。
- 鼓励按需使用子智能体并行探索、独立实现和复核验证；不得让多个子智能体争用同一文件或绕过 TDD / 验证门禁。
- 严格执行 TDD：先写失败测试，再做最小实现，再重构。
- 如果涉及外部库，优先使用 Context7 查询官方文档；如果当前环境没有 Context7，明确说明并使用官方文档替代。
- 工作完成前运行相关测试和 lint；如果某项验证无法运行，说明原因。
- 完成或部分完成后，更新对应计划文档，记录验证证据和下一步。
- 未经我明确要求不要 commit。

请开始执行，并在每个阶段给出简短进度说明。
```

## 待补充: 外部项目规则原文

用户提到有一段来自另一个项目的 Codex 目标模式规则文本。当前上下文尚未包含该原文。

后续如果补充原文，应按以下方式融合:

1. 保留本项目不可协商规则: `AGENTS.md`、TDD、中文交流、确定性优先、Docker 优先。
2. 将外部规则中适合自动化长目标推进的部分并入“执行循环”和“完成判定”。
3. 删除与本项目冲突的规则，例如绕过测试、宽松降级、默认提交、默认重写架构。
4. 如果外部规则包含更好的轮询、阻塞处理、交接摘要、目标拆分策略，应合并到本文档。
