# New Agents Alex 用户故事拆解工作流设计

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-ci-verification.md`、`docs/strategy/goal-mode-subagents.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、`docs/CODING_STANDARDS.md`、`docs/DESIGN_PRINCIPLES.md`、`docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`、`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`。
- 已读取代码与测试：`tools/new-agents/workflow_manifest.json`、`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/tests/test_workflow_contract_sync.py`、`tools/new-agents/backend/tests/test_workflow_handoffs.py`、`tools/new-agents/frontend/src/core/types.ts`、`tools/new-agents/frontend/src/core/workflows.ts`、`tools/new-agents/frontend/src/core/workflowRegistry.ts`、`tools/new-agents/frontend/src/core/config/agentWorkflows.ts`、`tools/new-agents/frontend/src/components/ChatPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`、`tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`、`tools/new-agents/frontend/src/pages/__tests__/WorkflowSelect.test.tsx`、`tests/e2e/new_agents_browser/sse_mock.py`、`tests/e2e/new_agents_browser/workflow_runner.py`、`tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py`。
- 当前工作区：存在大量与本轮无关的 `.agent`、`.claude`、`_bmad`、`.opencode`、intent-tester 产物和部分文档脏改动。本轮只写入 New Agents Alex 第 2 轮相关文件、spec / plan、todo 与必要 API / TESTING 记录，不回滚、不格式化、不 stage 无关文件。

已确认目标来源：

- 来源：`docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`。
- 本轮承接：第 2 轮，新增 `USER_STORY_BREAKDOWN`，让 Alex 可把需求蓝图拆成完整用户故事文档。
- 上一轮状态：第 1 轮已完成 `IDEA_BRAINSTORM/CONCEPT -> VALUE_DISCOVERY/ELEVATOR` 的目标侧 handoff 入口，并保留现有 `VALUE_DISCOVERY/BLUEPRINT -> Lisa` handoff。

改道条件检查：

- 新 P0/P1 或用户新目标：用户新增 Playbook commit / push 规则，已写入 `docs/strategy/goal-mode-playbook.md` 并完成上一批 commit / push；不改变本轮 Alex 第 2 轮目标。
- 未关闭质量门：上一批 New Agents 验证通过；结构化失败治理 todo 仍有第 0 / 第 3 轮待做，但用户当前追问和路线要求优先推进 Alex 需求拆分链路。
- 架构冲突：`docs/ARCHITECTURE.md` 仍称 Alex 有“价值发现”，当前 manifest 与 todo 已改为“需求蓝图梳理”。本轮按当前代码和 todo 为准，不在本轮扩散修改无关架构概览。
- 工作区冲突：无本轮目标文件已被用户改动的迹象；实施前继续按最新文件状态读取。
- 子智能体 / 旁路审查：本轮核心改动集中于同一条 manifest / backend contract / frontend prompt / ChatPane 入口 / E2E payload 同步链路。可写 worker 容易造成配置不同步，因此不派写入型子智能体；实现完成后可用聚焦测试和 diff 复核替代。

结论：继续承接 Alex 第 2 轮，不升级为完整 CGA。

## Brainstorming 记录

### Explore Project Context

当前系统已经具备共享工作流 manifest、后端 stage / artifact contract、前端 `WORKFLOWS` 派生、typed Agent Runtime SSE、run / artifact version 持久化和配置化 workflow handoff。`workflow_handoffs.py` 后端按 manifest 查询入站 / 出站接力，已经能支持新的 `VALUE_DISCOVERY/BLUEPRINT -> USER_STORY_BREAKDOWN/SCOPE`，主要缺的是 manifest 声明和前端目标侧入口泛化。

Alex 目前在线工作流只有：

- `IDEA_BRAINSTORM`：创意头脑风暴，最终输出产品概念简报。
- `VALUE_DISCOVERY`：需求蓝图梳理，最终输出需求蓝图。

用户想要的 Alex 主线是：

```text
原始 idea -> 产品方向 / 方案 -> 需求蓝图 -> 用户故事地图 -> 用户故事卡片 -> 单个 ready 用户故事 handoff 给 AI Coding
```

第 2 轮要交付的是“需求蓝图 -> 用户故事拆解文档”这一段。结构化 `artifact_data`、严格故事质量校验和持久化单故事 packet 已写入后续第 3 / 第 4 轮，不在本轮抢做。

### Visual Companion Decision

本轮不涉及页面视觉设计或布局方案选择，新增入口沿用现有 WorkflowSelect 与 ChatPane 目标侧 handoff 面板。无需浏览器视觉 companion；验收用浏览器级 mock E2E 验证完整阶段推进即可。

### Clarifying Questions

1. 用户是谁？
   - Alex 的目标用户是产品经理、业务负责人或创业者，他们已经有需求蓝图，想进一步拆成能交给后续 AI Coding 的需求单元。
2. 用户从哪里开始？
   - 可以从 Alex 工作流列表直接选择“用户故事拆解”开启新话题，也可以在空的用户故事拆解工作区选择继承已有 `VALUE_DISCOVERY/BLUEPRINT`。
3. 成功状态是什么？
   - 右侧 artifact 形成“用户故事拆解文档 / 单故事 Handoff 清单”，包含拆分范围、需求追溯 ID、用户故事地图、MVP slice、用户故事卡片、Ready / Not ready 分类、开放问题和 handoff 清单。
4. 本轮不做什么？
   - 不实现真实 AI Coding workflow；不生成技术任务、文件路径、实现计划、架构方案或测试命令；不把单故事 packet 持久化为一等对象；不新增 Alex 专属 runtime / API / store。
5. 失败路径是什么？
   - 没有可继承上游时，目标侧面板明确提示并允许开启新话题。模型输出缺少 artifact contract 标题或必需图表时，继续走现有 Agent Runtime contract 失败路径，不用 fallback 草稿隐藏。
6. 下游怎么承接？
   - 本轮的下游是文档级 handoff 清单。第 4 轮再把单张 ready story 转成持久化 handoff packet。

### Approaches

方案 A：只把“用户故事拆解”作为一个新在线 workflow，用 Markdown artifact contract 和 mock E2E 交付全阶段链路。

- 优点：符合第 2 轮边界，能快速让用户真实完成从蓝图到故事文档的主路径。
- 缺点：故事卡结构仍由 Markdown contract 约束，不能作为后续 packet 的稳定数据源。
- 结论：推荐。本轮先打通完整用户路径，后续第 3 轮再结构化。

方案 B：本轮同时新增结构化 `artifact_data`、renderer 和故事质量 validator。

- 优点：能更早为第 4 轮 packet 提供机器可读数据。
- 缺点：会把第 2 / 第 3 轮合并，触达 runtime renderer、schema、contract、prompt、E2E，破坏目标模式厚切片但不超载的边界。
- 结论：不选。结构化故事卡是第 3 轮。

方案 C：先只新增 manifest workflow 和 prompt，不改前端目标侧 handoff 入口。

- 优点：实现最小。
- 缺点：用户不能从需求蓝图选择继承上游，无法满足第 2 轮“可从 `VALUE_DISCOVERY/BLUEPRINT` handoff 进入”的验收。
- 结论：不选。前端入口泛化必须并入本轮。

## 推荐设计

### Workflow 与阶段

新增在线工作流：

- ID：`USER_STORY_BREAKDOWN`
- slug：`user-story-breakdown`
- agentId：`alex`
- 用户可见名：`用户故事拆解`
- 目标：从需求蓝图或新话题出发，生成可交给后续 AI Coding 准备流程的用户故事拆解文档。

阶段：

| 阶段 ID | 用户可见名 | 产物职责 |
| --- | --- | --- |
| `SCOPE` | 校准拆分范围 | 明确进入拆解的需求、稳定 `REQ-*`、不拆范围和阻塞问题。 |
| `STORY_MAP` | 绘制故事地图 | 按用户活动 / 用户任务组织故事，识别 MVP slice 与后续 release slice。 |
| `STORIES` | 编写故事卡片 | 形成垂直业务切片的用户故事卡，包含来源需求、验收标准、业务规则、依赖和 Ready / Not ready 状态。 |
| `HANDOFF` | 准备故事交接 | 输出 Ready stories、Not ready 阻塞项、单故事需求包清单和 AI Coding 输入边界说明。 |

### Artifact Contract

本轮使用 Markdown artifact contract 约束产物结构，不新增结构化故事 schema。

核心规则：

- 所有阶段必须包含稳定需求 ID，例如 `REQ-001`。
- 用户故事必须包含稳定 story ID，例如 `US-001`。
- story 必须引用已有 `REQ-*`，并表达“作为谁 / 我想要 / 以便什么”。
- story 拆分必须是垂直业务切片，明确禁止“建表 / 写接口 / 做页面 / 写测试”等技术任务清单。
- `HANDOFF` 只输出需求信息和追溯信息，不输出实现计划、代码路径、任务拆分或测试命令。

`SCOPE` 阶段要求一个轻量 Mermaid `flowchart`，满足现有“每个 workflow 首阶段都有视觉 contract”的机械门禁，并展示进入拆分、不拆范围和阻塞问题的关系。`STORY_MAP` 阶段也要求 Mermaid `flowchart`，用于可视化用户活动、任务、候选故事和 MVP slice 的关系。其余阶段本轮不引入新的 structured visual contract，避免把视觉协议治理和故事结构化提前合并。

### Handoff 入口

新增 manifest handoff：

```text
VALUE_DISCOVERY/BLUEPRINT -> USER_STORY_BREAKDOWN/SCOPE
```

label：`从需求蓝图继续拆用户故事`。

后端 `workflow_handoffs.py` 已按 manifest 泛化，不需要新增 workflow 专属 endpoint。需要新增测试证明：

- 源 run 有 `VALUE_DISCOVERY/BLUEPRINT` artifact 时，出站 handoff 包含 `USER_STORY_BREAKDOWN/SCOPE`。
- 目标侧查询 `USER_STORY_BREAKDOWN/SCOPE` 时，返回上游需求蓝图候选、artifact version、digest、summary 和 prompt。
- 启动 handoff 后目标 run 的第一条 user message 保留 source run、source workflow / stage、artifact version 和 digest。

前端 `ChatPane` 当前只在 `VALUE_DISCOVERY/ELEVATOR` 空会话展示目标侧 handoff 面板，且文案写死为“产品概念简报”。本轮改为基于 manifest 的入站 handoff 判断：

- 只要当前 workflow / stage 存在入站 handoff，且当前为空会话、无 currentRunId，就展示目标侧启动面板。
- 文案按 target workflow 提供轻量配置：
  - `VALUE_DISCOVERY/ELEVATOR`：继续显示“选择需求蓝图起点 / 产品概念简报”。
  - `USER_STORY_BREAKDOWN/SCOPE`：显示“选择用户故事拆解起点 / 需求蓝图”。
- 无候选时显示“暂无可继承的需求蓝图，可以直接开启新话题”。

### 前端配置

`WorkflowType` 增加 `USER_STORY_BREAKDOWN`。`workflow_manifest.json` 增加 workflow 定义后，`WORKFLOWS`、slug 映射、Alex online cards 仍由共享派生逻辑生成。

原 `NON_RUNTIME_AGENT_WORKFLOWS` 中 `story-breakdown` plan 卡片必须移除，避免同名能力同时以 plan 和 online 出现。Alex 仍保留 `competitive-analysis` plan 卡。

新增四个 prompt / template 文件：

```text
tools/new-agents/frontend/src/core/prompts/user_story_breakdown/scope.ts
tools/new-agents/frontend/src/core/prompts/user_story_breakdown/story_map.ts
tools/new-agents/frontend/src/core/prompts/user_story_breakdown/stories.ts
tools/new-agents/frontend/src/core/prompts/user_story_breakdown/handoff.ts
```

它们沿用现有 prompt 文件模式，导出 `*_PROMPT` 与 `*_TEMPLATE`，并在 `workflows.ts` 的 `STAGE_CONTENT_BY_TEMPLATE_ID` 中注册。

### Testing

按 TDD 执行，先补失败测试：

- backend contract sync：manifest stage、artifact headings、prompt files、Mermaid contract 和 handoff 目标同步。
- backend handoff：`VALUE_DISCOVERY/BLUEPRINT -> USER_STORY_BREAKDOWN/SCOPE` 出站、目标侧候选和启动追溯。
- frontend config：Alex online workflow 出现 `user-story-breakdown`，plan 卡片移除，stage prompts / templates 完整。
- ChatPane：`USER_STORY_BREAKDOWN/SCOPE` 空会话能拉取目标侧候选、显示需求蓝图文案、无候选时允许新话题、选择候选后进入 `/workspace/alex/user-story-breakdown?runId=...`。
- WorkflowSelect：Alex 列表显示“用户故事拆解”，点击进入对应 workspace。
- E2E mock：新增完整 `SCOPE -> STORY_MAP -> STORIES -> HANDOFF` 场景，验证每阶段 artifact headings、Mermaid `flowchart`、阶段确认和最终 artifact。

收尾验证：

- 聚焦 backend / frontend tests。
- `tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py`。
- `./scripts/test/test-local.sh new-agents`。
- 视最终 diff 风险，按 Playbook 判断是否需要 `./scripts/test/test-local.sh all`；若只影响 New Agents 且全仓 all 明显超出本轮耗时边界，收尾需记录例外理由和 CI 等价映射。

## 验收条件

1. Given 用户进入 Alex 工作流列表
   When 查看在线工作流
   Then 可以看到在线的“用户故事拆解”，且不再看到同名 Plan 卡片。

2. Given 已有 `VALUE_DISCOVERY/BLUEPRINT` 需求蓝图 artifact
   When 用户打开 `USER_STORY_BREAKDOWN/SCOPE` 空会话
   Then 页面展示“开启新话题 / 从需求蓝图继续拆用户故事”入口，并列出可继承候选。

3. Given 用户选择一个需求蓝图候选
   When 系统启动 handoff
   Then 创建目标 `USER_STORY_BREAKDOWN` run，第一条 user message 包含 source run、source workflow / stage、artifact version 和 digest，前端导航到目标 run。

4. Given 用户在“用户故事拆解”工作流中推进阶段
   When 完成 `SCOPE -> STORY_MAP -> STORIES -> HANDOFF`
   Then 最终 artifact 包含拆分范围、稳定需求 ID、用户故事地图、MVP slice、用户故事列表、Ready / Not ready stories、开放问题和 handoff 清单。

5. Given 模型输出缺少必需标题或 `STORY_MAP` 缺少 Mermaid `flowchart`
   When 后端校验 artifact
   Then 沿用现有 contract failure 显式报错，不持久化伪成功 artifact，不推进阶段。

## 非目标

- 不新增真实 AI Coding workflow。
- 不新增单故事 packet 持久化表、API 或复制入口。
- 不新增用户、权限或租户概念。
- 不改 Lisa 既有 workflow、handoff 目标或测试资产能力。
- 不新增 Alex 专属 runtime、SSE endpoint、store 或 renderer。
- 不把 Markdown 反解析为结构化故事数据；第 3 轮会处理结构化故事契约。
