# Alex 用户故事拆解 Workflow 主线化设计

## 背景

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 E13「Alex 用户故事拆解 workflow」列为 P0 增强点。当前 `master` 中 `story-breakdown` 只作为 Alex 的计划卡片出现，用户不能通过共享 Agent Runtime 执行该 workflow，也不能得到可进入研发评审、Sprint 切片和 Lisa 测试设计承接的 Story 包。

本轮目标是把 Alex `story-breakdown` 主线化为在线 runtime workflow。已有隔离分支 `codex/alex-story-breakdown-mainline-closure` 可作为工程输入，但本轮仍从当前 `master` 创建独立 worktree `codex/alex-story-breakdown-goal-current`，按 TDD 等价 RED 检查重新验证、移植和提交，确保当前主线可交付。

## Superpowers 头脑风暴执行记录

### 1. Explore Project Context

- 问：当前项目事实是什么，而不是我记忆里是什么？
  答：当前 `master` 是 `e35c9643 docs(goal): 明确 Superpowers 头脑风暴细化规则`，主工作区有既有未提交改动，不能直接写主工作区。本轮已创建隔离 worktree `.worktrees/alex-story-breakdown-goal-current`。`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 把 E13 Alex 用户故事拆解 workflow 标成 P0；当前主线只在 `agentWorkflows.ts` 中有 `story-breakdown` plan/listing 痕迹，`workflow_manifest.json`、backend contract、renderer、runtime 和 handoff 尚未支持 `STORY_BREAKDOWN`。已有旧分支 `codex/alex-story-breakdown-mainline-closure` 可作为工程输入，但不能当完成证明。本轮先用 Node 只读验收检查确认当前 manifest 缺 `STORY_BREAKDOWN` 并得到预期失败，再移植实现。
- 问：这个需求是否过大，需要拆成多个 spec？
  答：不需要拆成多个 spec。它是一个完整但边界清晰的能力包：上线一个 Alex runtime workflow。它触及前后端多个同步面，但用户意图、入口、产出、handoff 和验证闭环都是同一条动作链。不能拆成“先前端入口”“再后端 runtime”“再 handoff”，否则每一片都不可独立交付。
- 问：当前已有相关模式是什么？
  答：New Agents 已有 `TEST_DESIGN`、`REQ_REVIEW`、`INCIDENT_REVIEW`、`IDEA_BRAINSTORM`、`VALUE_DISCOVERY` 的共享 workflow 模式：manifest 声明 workflow/stage，前端 `WORKFLOWS` 和 prompt registry 提供入口与 stage prompt，后端 `WORKFLOW_STAGES`、artifact contract、artifact_data renderer 和 runtime instruction 保证产物结构，handoff 通过共享 `workflow_handoffs.py` 和 manifest 配置连接，不新增 agent-specific path。

### 2. Offer Visual Companion

- 问：这轮是否需要视觉辅助？
  答：不需要。当前核心是 workflow contract、runtime、prompt 和 handoff 的架构/行为设计，不是 UI layout 或视觉方案选择。用文本化设计和测试证据更直接。

### 3. Clarifying Questions

- 问：这个 workflow 的首要用户是谁？
  答：Alex 的主要用户：产品经理、业务分析师、研发负责人。他们拿着 PRD、需求蓝图或模糊产品描述，需要拆成研发 backlog。
- 问：这个用户的“成功”是什么？
  答：不是“生成一篇好看的文档”，而是生成能被研发评审、估算、排 Sprint、交给 Lisa 测试设计的结构化 Story 包。成功产物必须包含 Epic、User Story、AC、依赖/风险、Sprint 切片和 Lisa handoff 输入。
- 问：为什么不能用现有 `VALUE_DISCOVERY/BLUEPRINT`？
  答：`BLUEPRINT` 产出产品需求蓝图，它回答“要做什么、为什么做、MVP 范围是什么”。`STORY_BREAKDOWN` 回答“怎么拆成研发可交付 backlog”。两者上下游相邻，但不是同一个产物。
- 问：为什么不能用 Lisa `REQ_REVIEW`？
  答：Lisa 关注需求可测试性、歧义、边界、风险和复审条件。Story Breakdown 关注产品需求向研发交付包的拆解。它应能把结果交给 Lisa，而不是被 Lisa 替代。
- 问：输入应该支持哪些来源？
  答：三类：用户直接粘贴 PRD、从 Alex `VALUE_DISCOVERY/BLUEPRINT` 复制/交接来的需求蓝图、以及自由文本产品需求。第一轮不做自动读取另一个 run 的复杂交互，但 contract 和 prompt 要承认这些输入来源。
- 问：阶段应该怎么切？
  答：四阶段最合适：`INPUT_ANALYSIS` 输入盘点，`EPIC_MAPPING` Epic/能力地图，`STORY_BACKLOG` User Story 与 AC，`SPRINT_PLAN` Sprint 切片与 Lisa handoff。少于四阶段会让模型一次承担太多，超过四阶段会把估算、研发设计、发布管理带进来。
- 问：产物应采用 Markdown 直出还是 `artifact_data`？
  答：必须采用 `artifact_data`。DeepSeek V4 结构化产物方向已经明确：模型输出业务数据，后端 renderer 确定性生成 Markdown/Mermaid/`ai4se-visual`。Story Breakdown 如果回到 Markdown 直出，会倒退到格式不稳定路径。
- 问：哪些失败必须显式暴露？
  答：缺 Epic、Story 没有 AC、AC 引用不存在的 Story、Sprint 引用不存在的 Story、Lisa handoff 输入为空、required heading/visual 缺失。这些都不能被后端补假数据，也不能假装成功。
- 问：用户看到的入口是什么？
  答：Alex 工作流列表里 `story-breakdown` 必须是 online，link 是 `/workspace/alex/story-breakdown`，不是 plan 卡片。
- 问：handoff 的边界是什么？
  答：只提供到 Lisa `TEST_DESIGN/CLARIFY` 和 `REQ_REVIEW/REVIEW` 的上下文输入，不自动启动 Lisa，不做跨 workflow 编排，不新增 API。handoff prompt 必须带来源 workflow/stage/version 和 bounded source artifact。
- 问：CI 最大风险是什么？
  答：配置不同步。典型失败包括：前端 `WorkflowType` 没加 `STORY_BREAKDOWN`、manifest stage 和 backend `WORKFLOW_STAGES` 不一致、prompt file registry 缺模板、renderer 输出不满足 contract、handoff manifest 有目标但 backend 模板缺失。

### 4. Approaches

- 方案 A：只把 `story-breakdown` plan 卡片改成 online。
  优点：改动小。
  缺点：用户点击后没有 runtime workflow、contract、renderer 和 handoff，形成假入口。
  结论：不选。
- 方案 B：完整上线 `STORY_BREAKDOWN` runtime workflow，但仅用 Markdown 产物 contract。
  优点：实现比 `artifact_data` 快。
  缺点：违背 DeepSeek V4 结构化产物方向，重新把格式完整性风险交给模型，后续会再次出现“格式化输出不稳定”。
  结论：不选。
- 方案 C：完整上线 `STORY_BREAKDOWN` runtime workflow，并用 `artifact_data`、deterministic renderer 和 shared handoff。
  优点：形成真实用户能力闭环，符合 New Agents 共享架构和 DeepSeek V4 稳定输出方向；测试可以覆盖入口、runtime、contract、renderer、handoff。
  缺点：触及文件多，必须做更完整的 CI 等价验证。
  结论：选择。

### 5. Presented Design

- Architecture：`STORY_BREAKDOWN` 作为 `workflow_manifest.json` 中的 Alex workflow，不新增 runtime。前端通过 `WORKFLOWS`、slug mapping、workflow listing 和 prompt registry 暴露入口；后端通过 `WORKFLOW_STAGES`、artifact contract、runtime structured output instruction 和 renderer 支持执行；handoff 继续使用共享 handoff 配置。
- Components：`workflow_manifest.json` 是配置源；`frontend/src/core/workflows.ts` 和 `agentWorkflows.ts` 负责用户入口；`frontend/src/core/prompts/story_breakdown/*` 负责 stage prompt；`backend/agent_contracts.py` 负责 required headings/visuals；`backend/agent_runtime.py` 负责 `artifact_data` instruction 和 parse；`backend/artifact_data_renderers.py` 负责确定性渲染；`workflow_handoffs.py` 负责 Lisa handoff prompt。
- Data Flow：用户输入 PRD/蓝图 -> Alex `STORY_BREAKDOWN` stage prompt -> shared `/api/agent/runs/stream` -> 模型返回 JSON object with `artifact_data` -> backend schema/renderer -> `AgentTurnOutput` -> typed SSE -> 前端 ArtifactPane 展示 -> final `SPRINT_PLAN` 可 export handoff 到 Lisa。
- Error Handling：不合法 JSON、缺字段、空数组、引用不一致、renderer contract 失败都走现有 runtime error/retry path；不构造 fallback artifact；不隐藏失败。
- Testing：先 RED：frontend workflow test、backend sync test、runtime renderer test、handoff test 应在当前主线失败。再 GREEN：移植实现。最后运行 backend contract/runtime/renderer/handoff 聚焦测试、frontend workflow/prompt tests、`py_compile`、`git diff --check`。真实模型 smoke 不跑，原因是缺显式凭证/网络/额度。

## 用户故事

作为产品经理或业务分析师，当我已有 PRD、需求蓝图或产品需求描述时，我可以选择 Alex 的「用户故事拆解」workflow，通过共享 Agent Runtime 生成 Epic map、User Story backlog、验收标准、依赖风险、Sprint 切片建议和 Lisa handoff 输入，从而把产品需求交给研发评审并为后续 Lisa 测试设计准备结构化输入。

## 范围

纳入本轮：

- 新增在线 runtime workflow `STORY_BREAKDOWN`，slug 为 `story-breakdown`，agent 为 `alex`。
- 阶段为：`INPUT_ANALYSIS`、`EPIC_MAPPING`、`STORY_BACKLOG`、`SPRINT_PLAN`。
- 同步 `workflow_manifest.json`、前端 `WORKFLOWS`、Alex workflow listing、workflow type、prompt registry 和 prompt templates。
- 同步后端 `WORKFLOW_STAGES`、required headings、required Mermaid diagrams、required structured visuals。
- 新增或扩展 `artifact_data` structured output instruction，要求模型输出业务数据而不是完整 Markdown。
- 新增 deterministic renderer，输出固定 Markdown 标题、表格、Mermaid 和 `ai4se-visual`。
- 配置 Story 包最终阶段到 Lisa `TEST_DESIGN/CLARIFY` 和 `REQ_REVIEW/REVIEW` 的 handoff。
- 增加前后端测试证明该 workflow 继续走共享 `/api/agent/runs/stream`、共享 contract 和共享 UI 基础设施。

不纳入本轮：

- Alex `PRD_REVIEW` workflow。
- 外部项目管理工具写入或导出。
- 新增 agent-specific runtime、API path、state store 或 renderer。
- 真实 DeepSeek V4 / OpenAI smoke 自动门禁。

## 验收条件

1. Given Alex workflow 列表
   When 用户查看在线 workflow
   Then `story-breakdown` 显示为 online，并链接到 `/workspace/alex/story-breakdown`，`WORKFLOWS.STORY_BREAKDOWN` 包含 4 个阶段。

2. Given workflow manifest
   When 后端加载共享 workflow 配置
   Then `STORY_BREAKDOWN` 的 stage 顺序、prompt template、artifact headings、visual contract 与后端 contract registry 同步。

3. Given 模型返回合法 `artifact_data`
   When `parse_agent_turn_output_text()` 处理 `STORY_BREAKDOWN` 任一阶段
   Then 后端确定性渲染完整 Markdown artifact，并通过 `validate_agent_turn()`。

4. Given Story 包最终阶段 artifact
   When 用户请求 handoff
   Then 系统暴露到 Lisa `TEST_DESIGN/CLARIFY` 和 `REQ_REVIEW/REVIEW` 的 handoff，prompt 中包含来源 workflow/stage/version 和 bounded source artifact。

5. Given 本轮修改完成
   When 运行本地 CI 等价验证
   Then 后端聚焦 pytest、前端 workflow/prompt tests、`py_compile` 和 `git diff --check` 通过；未运行真实模型 smoke 的原因明确记录。

## 风险与约束

- 同步面较宽，必须用 sync tests 防止 manifest、backend contract、frontend prompt registry 漂移。
- Story 包 `artifact_data` 字段较多，renderer 和 contract 容易割裂；本轮用完整 fixture 驱动 renderer 和 runtime parse。
- Handoff 只提供 Lisa 输入上下文，不自动启动 Lisa workflow，避免扩大到跨 workflow 编排。
- 所有 `tools/new-agents/` 改动必须继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run/artifact 模型和共享 UI。

## CI 等价验证计划

| 远端 CI / 风险面 | 本地等价命令 | 目的 |
| --- | --- | --- |
| New Agents backend contract/runtime | `python3 -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_workflow_handoffs.py -q` | 覆盖 manifest、contract、runtime、renderer、handoff |
| New Agents frontend config/prompt | `cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts` | 覆盖 workflow listing、slug、prompt registry |
| Python 语法 | `python3 -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/workflow_handoffs.py` | 捕获语法和导入级错误 |
| Diff hygiene | `git diff --check` | 捕获 whitespace 错误 |

## Spec 自审

- 无 `TBD`、`TODO` 或未裁决占位。
- 本轮边界聚焦 `STORY_BREAKDOWN`，未混入 `PRD_REVIEW`、Artifact diagnostics 或 Lisa quality loop。
- 验收条件覆盖入口、配置同步、runtime 渲染、handoff 和 CI 等价验证。
- 与 `AGENTS.md` 的 New Agents 共享 runtime 约束一致。
