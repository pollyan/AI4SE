# New Agents Alex 上游产物启动承接设计

- 日期：2026-07-08
- 状态：目标模式第 1 轮设计
- 来源：`docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`
- 本轮用户故事：当用户进入 Alex 的需求蓝图梳理工作流时，可以选择开启新话题，或从已有产品概念简报继续；系统基于持久化上游产物创建可追溯目标 run，并继续走共享 Agent Runtime。

## Current State Gap Analysis

### 事实源快照

已读取：

- `AGENTS.md`
- `docs/strategy/goal-mode-playbook.md`
- `docs/strategy/goal-mode-cga-template.md`
- `docs/index.md`
- `docs/api-contracts.md`
- `docs/TESTING.md`
- `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`
- `tools/new-agents/workflow_manifest.json`
- `tools/new-agents/backend/workflow_handoffs.py`
- `tools/new-agents/backend/routes.py`
- `tools/new-agents/backend/run_persistence.py`
- `tools/new-agents/backend/models.py`
- `tools/new-agents/backend/tests/test_workflow_handoffs.py`
- `tools/new-agents/backend/tests/test_agent_endpoint.py`
- `tools/new-agents/frontend/src/services/workflowHandoffService.ts`
- `tools/new-agents/frontend/src/components/ChatPane.tsx`
- `tools/new-agents/frontend/src/store.ts`
- 相关前端 handoff 测试

当前工作区存在大量既有脏文件和删除记录。本轮只允许写入 Alex 第 1 轮相关 New Agents handoff 代码、测试、manifest、API/TESTING 文档、spec/plan 和 Alex todo 执行记录；不回滚、不格式化、不 stage 无关变更。

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| A. Alex 后续工作流可从已有上游产物启动 | 缺少 `IDEA_BRAINSTORM/CONCEPT -> VALUE_DISCOVERY/ELEVATOR` handoff；缺少目标工作流启动选择；现有入口文案抽象；缺少目标侧候选查询 | 进入需求蓝图梳理 -> 选择新话题或选择产品概念简报 -> 系统创建目标 run -> 工作区载入继承上下文 -> 后续继续用 `/api/agent/runs/stream` | 只加 manifest、endpoint 或按钮都不能让用户完成一次真实承接 | 后端 handoff tests、API endpoint tests、前端 service / ChatPane / store tests、Lisa handoff 回归 |
| B. 用户故事拆解工作流 | 缺少 `USER_STORY_BREAKDOWN` 和 `SCOPE -> STORY_MAP -> STORIES -> HANDOFF` | 从需求蓝图进入用户故事拆解 -> 产出故事地图和故事卡片 | 需要完整新 workflow、prompt、contract、renderer 和 E2E，超过本轮启动承接目标 | 后续第 2 轮 workflow / contract / E2E 证据 |
| C. 单故事 handoff packet | handoff 关系不是一等对象；packet 还不是结构化数据；缺少 stale 提示 | 从 ready story 选择单张故事 -> 生成持久化需求包 -> 可复制给 AI Coding | 依赖第 2/3 轮故事结构化契约，当前还没有 story 数据源 | 后续第 4 轮 packet persistence/API/UI tests |

### 候选 gap

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Alex todo 第 1 轮 | `VALUE_DISCOVERY` 可从 `IDEA_BRAINSTORM/CONCEPT` 继续 | 只有 source-side run handoff，且只从 `VALUE_DISCOVERY/BLUEPRINT` 到 Lisa | 没有目标侧候选入口和 Alex 内部 handoff | 直接解决用户提出的工作流衔接问题，也是后续用户故事拆解前置能力 | 中等，触达后端、前端和 manifest，但复用现有 handoff | 高，mock 持久化 run/artifact 和前端交互即可验证 | 本轮 |
| B | Alex todo 第 2 轮 | 新增用户故事拆解 workflow | 只有 idea / value discovery | 缺少 workflow、stage、prompt、contract、renderer | 直接接近 AI Coding 需求输入 | 高，跨 schema/prompt/renderer/E2E | 高，但范围大 | 下一轮 |
| C | Alex todo 第 4 轮 | 单故事需求包持久化 | 只有 run/artifact version | 缺少 story 数据源和 packet schema | 形成给 AI Coding 的最小需求单位 | 高，依赖 B/C 前置 | 高，需 packet API/UI tests | 第 4 轮 |

排序结论：

1. 选择 A。它是用户最新确认的 Alex 主线第一段，也是后续用户故事拆解、单故事 packet 的入口前置。完成后用户可以真实地从产品概念简报继续梳理需求蓝图。
2. B 暂不选，因为它会新增完整 workflow，必须建立在目标侧承接入口稳定之后。
3. C 暂不选，因为单故事 packet 需要先有结构化故事卡片。

### 切片准入判断

- 用户功能包边界：本轮只做“产品概念简报 -> 需求蓝图梳理”的目标侧启动承接。
- 纳入相邻缺口：manifest 声明、后端目标候选查询、start handoff 可追溯 prompt、前端启动选择、入口文案直白化、Lisa 回归。
- 排除相邻缺口：不新增 `USER_STORY_BREAKDOWN`；不做一等 handoff packet 表；不做 AI Coding workflow 消费契约；不修改 Lisa 目标链路。
- 过薄风险检查：本轮不是单 endpoint 或单按钮，覆盖入口、用户动作、系统处理、可见结果、状态承接、失败反馈和验证。
- 能力增量句：完成后，用户现在可以在需求蓝图梳理页从已有产品概念简报继续，而不是手工复制粘贴上游 Markdown。

### 切片厚度门禁

- 入口：`/workspace/alex/value-discovery` 空会话页。
- 动作：用户选择“开启新话题”或选择某个已有“产品概念简报”继续。
- 处理：后端按目标 workflow/stage 查询所有可用上游 run/artifact；start 时创建 `VALUE_DISCOVERY/ELEVATOR` target run，并把上游 artifact 作为第一条持久化 user message。
- 可见结果：页面显示可继承候选、上游摘要、版本；选择后 workspace 切到目标 run，左侧出现继承上下文。
- 状态承接：目标 run、第一条 message、source run/version/digest 追溯信息随 run snapshot 可恢复；后续继续调用共享 `/api/agent/runs/stream`。
- 失败反馈：没有候选时明确提示可开启新话题；候选 payload malformed、未知 handoff 或目标不匹配时显式失败，不伪造成功。
- 证据：后端 service/API tests、前端 service/ChatPane/store tests、Lisa handoff regression、focused New Agents tests。
- 结论：通过。

### 本轮用户故事

作为 Alex 用户，当我已经有一份产品概念简报并进入需求蓝图梳理时，我可以选择从这份简报继续，而不是重新粘贴背景，从而让 idea 到需求蓝图的流程形成可追溯承接。

### 子智能体 / 旁路审查决策

本轮不派发子智能体。原因是改动集中在共享 handoff service、manifest 和同一组前后端测试，存在写入交叉；当前主 Agent 直接执行更容易保护既有脏工作区。验证阶段会用聚焦测试和 Lisa handoff 回归补偿旁路审查。

## Superpowers Brainstorming 自问自答

### Explore Project Context

New Agents 当前已把 workflow、agent、stage、onboarding、artifact contract 和 handoff 配在 `workflow_manifest.json`。后端 `workflow_handoffs.py` 已能从一个 source run snapshot 中找到配置化 source artifact，生成 handoff prompt，并创建 target run。前端 `ChatPane` 已能在当前 run 有 handoff 候选时显示 source-side action，并通过 `applyWorkflowHandoff` 切换到目标 workflow。

缺口是方向相反：用户进入后续 workflow 时看不到“从已有内容继续”的入口。现有 API 需要用户先位于 source run，无法在 `VALUE_DISCOVERY` 空会话页按目标 workflow 拉取可用 `IDEA_BRAINSTORM/CONCEPT` 候选。

### Visual Companion Decision

本轮涉及前端交互，但不是视觉设计专项。沿用 ChatPane 现有暗色面板、按钮和 starter prompt 样式，只增加启动选择区，不重新设计页面。

### Clarifying Questions

1. 谁是本轮用户？
   使用 Alex 做产品需求梳理的人，已经可能通过 `IDEA_BRAINSTORM` 得到产品概念简报。

2. 用户要完成什么？
   进入需求蓝图梳理时选择从某个已有产品概念简报继续，系统自动把上游内容带入第一轮上下文。

3. 成功状态是什么？
   目标 run 被创建，ChatPane 展示 handoff message，URL 带 target runId，后续发送消息会复用该 run 继续走共享 `/api/agent/runs/stream`。

4. 输入来源是什么？
   持久化 `IDEA_BRAINSTORM/CONCEPT` artifact 当前版本，不从 Markdown 手工粘贴、不从本地缓存伪造。

5. 是否需要用户权限或隔离？
   当前系统没有用户概念，因此不做权限和所有者过滤；候选只按 workflow/stage/artifact 存在性筛选。

6. 是否要一等持久化 handoff 关系？
   本轮不新增表。通过 target run 第一条 user message 持久化 source run、workflow/stage、artifact version、digest 和摘要，形成等价可追溯记录；一等 packet/关系表留到第 4 轮。

7. 如何避免影响 Lisa？
   现有 `VALUE_DISCOVERY/BLUEPRINT -> TEST_DESIGN/REQ_REVIEW` 配置、source-side endpoint 和 start endpoint 保持兼容，并补回归测试。

8. 是否要改掉“价值发现”这个名称？
   本轮只改与本路径直接相关的用户可见名称和说明，使入口更直白，例如“需求蓝图梳理”。更系统的命名治理留给后续 workflow 梳理。

### Approaches

推荐方案：扩展现有 handoff 能力，新增 target-side candidate query，并给 manifest 增加 Alex 内部 handoff。

- 优点：复用现有 run/artifact persistence 和 start handoff，不新增专属 runtime/API/store；能让用户在目标页完成选择；Lisa 现有路径兼容。
- 缺点：handoff 关系还不是一等表，只能通过目标 run 第一条 message 追溯；完整 packet 仍需后续轮次。

备选方案 A：只在 `IDEA_BRAINSTORM/CONCEPT` 完成后显示“继续梳理需求蓝图”按钮。

- 优点：改动最小，复用现有 source-side UI。
- 缺点：不能满足用户进入后续 workflow 时选择“新话题 / 基于已有内容继续”的启动模式。

备选方案 B：本轮直接新增 handoff relation / packet 表。

- 优点：追溯模型更完整。
- 缺点：会把第 4 轮的单故事 packet 和 stale 检测提前拉入，扩大范围；当前还没有用户故事数据源。

结论：采用推荐方案。

## 设计目标

本轮完成后：

- `workflow_manifest.json` 声明 `IDEA_BRAINSTORM/CONCEPT -> VALUE_DISCOVERY/ELEVATOR` handoff。
- 后端提供按 target workflow/stage 查询上游候选的只读 API。
- 候选返回 source run、source workflow/stage、artifact version、artifact digest、摘要、target workflow/stage、label 和 prompt。
- start handoff 创建 `VALUE_DISCOVERY/ELEVATOR` target run，并在第一条 user message 中持久化可追溯 source metadata。
- 前端进入 `VALUE_DISCOVERY` 空会话页时显示“开启新话题 / 从产品概念简报继续”。
- 没有候选时允许直接开启新话题，并给出清晰提示。
- 选择候选后切换到 target run，继续共享 `/api/agent/runs/stream`。

## 非目标

- 不新增 `USER_STORY_BREAKDOWN`。
- 不生成用户故事卡片、故事地图或单故事 packet。
- 不实现真实 AI Coding workflow。
- 不设计 AI Coding 消费契约。
- 不新增 Lisa handoff，不改变 Lisa 现有 source-side handoff 行为。
- 不新增 Alex 专属 runtime、SSE endpoint、store 或渲染管线。
- 不从 Markdown 反解析结构化 story 数据。

## 后端设计

### Manifest

新增 handoff：

```text
idea-brainstorm-concept-to-value-discovery
source: IDEA_BRAINSTORM / CONCEPT
target: VALUE_DISCOVERY / ELEVATOR / alex
label: 从产品概念简报继续梳理需求蓝图
promptTemplateId: source-artifact-handoff
```

同时将 `VALUE_DISCOVERY` 用户可见名称和 listing 文案改为更直白的“需求蓝图梳理”，避免继续扩大“价值发现”的理解门槛。内部 ID 和 slug 不变，减少兼容风险。

### Target Candidate API

新增只读端点：

```text
GET /api/agent/workflow-handoff-candidates?targetWorkflowId=VALUE_DISCOVERY&targetStageId=ELEVATOR
```

返回：

```json
{
  "targetWorkflowId": "VALUE_DISCOVERY",
  "targetStageId": "ELEVATOR",
  "handoffs": [
    {
      "id": "idea-brainstorm-concept-to-value-discovery",
      "label": "从产品概念简报继续梳理需求蓝图",
      "sourceRunId": "source-run-id",
      "sourceWorkflowId": "IDEA_BRAINSTORM",
      "sourceStageId": "CONCEPT",
      "sourceArtifactVersion": 1,
      "sourceArtifactDigest": "sha256:...",
      "sourceArtifactSummary": "产品概念简报...",
      "targetWorkflowId": "VALUE_DISCOVERY",
      "targetStageId": "ELEVATOR",
      "targetAgentId": "alex",
      "prompt": "请基于以下上游产物继续工作..."
    }
  ]
}
```

筛选规则：

- 只读取 manifest 中 target workflow/stage 匹配的 handoff。
- 只返回 source run 当前存在 source stage artifact 且 artifact 有 current version 的候选。
- 当前系统没有用户概念，不做权限和 owner 过滤。
- 默认按 source run/artifact 更新时间倒序，限制最近候选数量，避免页面过长。
- 未知 target workflow 或 stage mismatch 返回 JSON 400；无候选返回空数组。

### Prompt 追溯

`_build_handoff_prompt` 增加 source metadata 区块：

- 源 run
- 源 workflow/stage
- 源 artifact version
- 源 artifact digest
- target workflow/stage

这不是最终 packet 设计，但能保证 target run snapshot 的第一条 user message 可恢复来源。完整一等 handoff packet 留到第 4 轮。

## 前端设计

### Service

`workflowHandoffService.ts` 新增：

```text
fetchTargetWorkflowHandoffCandidates(targetWorkflowId, targetStageId)
```

解析同一个 `WorkflowHandoff` 类型，并扩展可选字段：

- `sourceRunId`
- `sourceArtifactDigest`
- `sourceArtifactSummary`

已有 `fetchWorkflowHandoffs(runId)` 和 `startWorkflowHandoff(runId, handoffId)` 保持兼容。

### ChatPane

当满足以下条件时查询 target-side candidates：

- `currentRunId` 为空
- `chatHistory.length === 0`
- 当前 workflow/stage 是 manifest 中某个 handoff 的 target

空状态展示：

- 主按钮：开启新话题。点击后隐藏承接选择区，用户继续使用 starter prompts 或输入框。
- 候选列表：从产品概念简报继续。每项展示 label、source stage、artifact version、summary/digest 短摘要。
- 无候选：提示“暂无可继承的产品概念简报，可以直接开启新话题”。

选择候选时：

- 使用 `handoff.sourceRunId` 调用现有 start endpoint。
- 调用 `applyWorkflowHandoff(startedHandoff)`。
- 导航到 target workflow slug，并带 `?runId=targetRunId`。

### Store

`applyWorkflowHandoff` 已能按 target workflow/stage 初始化工作区。本轮只需要让 `WorkflowHandoff` 可携带 source metadata；build handoff message 仍使用后端返回的 prompt。

## 错误处理

- target candidate API payload 非法时前端显式报错并不应用 handoff。
- target-side candidate 没有 `sourceRunId` 时不触发 start，避免伪成功。
- start endpoint 继续对未知 handoff 返回 JSON 404。
- source artifact 缺失或版本不存在时不返回候选。
- 所有新增错误都不更新右侧 artifact、不推进 stage、不生成 fallback 草稿。

## 测试策略

后端：

- `test_workflow_handoffs.py`：新增 `IDEA_BRAINSTORM/CONCEPT -> VALUE_DISCOVERY/ELEVATOR` source-side candidate。
- `test_workflow_handoffs.py`：新增 target-side query 返回 source run、artifact version、digest、summary 和 prompt。
- `test_workflow_handoffs.py`：start Alex handoff 创建 target run，第一条 message 包含 source run/version/digest 追溯。
- `test_workflow_handoffs.py`：Lisa 现有两个 handoff 不回归。
- `test_agent_endpoint.py`：新增 target candidate endpoint 正常、空结果、非法 target stage 测试。

前端：

- `workflowHandoffService.test.ts`：解析 target candidate endpoint，包含 source metadata；malformed payload 显式失败。
- `ChatPane.test.tsx`：进入 `VALUE_DISCOVERY` 空会话时查询并展示“开启新话题 / 从产品概念简报继续”。
- `ChatPane.test.tsx`：选择 target candidate 后用 sourceRunId start，并切换到 target run。
- `ChatPane.test.tsx`：无候选时提示并允许开启新话题。
- `store.test.ts`：可应用 Alex 内部 handoff，target agent/stage 校验仍生效。

回归：

- 保留并运行现有 Lisa handoff 测试。
- 运行相关 backend/frontend focused tests。
- 本轮触达共享 API 和前端交互，收尾前按可行范围运行 `./scripts/test/test-local.sh new-agents`；若因耗时或环境阻塞不能运行，记录原因和风险。
