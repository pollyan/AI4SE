# Alex 用户故事拆解 Workflow 主线落地设计

## 背景

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 E13「Alex 用户故事拆解 workflow」列为 P0 增强点。当前主线中 `story-breakdown` 只作为 Alex 的 plan 卡片存在，用户不能通过共享 Agent Runtime 执行该 workflow，也不能得到可研发评审和可交给 Lisa 承接的 Story 包。

本轮目标是把 `story-breakdown` 升级为在线 runtime workflow，并保持 `tools/new-agents/` 的共享架构约束：复用 `workflow_manifest.json`、共享 `/api/agent/runs/stream`、typed SSE、artifact contract、run/artifact persistence 和共享 UI，不新增 Alex 专属 runtime、API path、store 或 renderer。

## 自问自答头脑风暴

- 问：这个能力包真正服务的用户意图是什么？
  答：产品经理或业务分析师已有 PRD、需求蓝图或产品需求描述，希望把它拆成研发可评审、可排期、可测试的 Epic、User Story、AC、依赖和 Sprint 切片。
- 问：哪些相邻缺口必须同轮并入，否则用户仍无法完成任务？
  答：必须同时并入 workflow manifest、前端 workflow slug/listing、阶段 prompt、backend artifact contract、visual contract、runtime structured output instruction、renderer、handoff 配置和测试证据。只做其中一层会让入口、运行、产物或下游承接断裂。
- 问：哪些缺口本轮明确不做？
  答：不做 Alex PRD_REVIEW workflow、不写入 Jira/禅道等外部项目管理工具、不新增项目管理系统导出、不替代 Lisa 的测试视角需求评审。
- 问：失败时用户或调用方如何知道原因并继续推进？
  答：继续使用共享 contract validation、structured output retry 和 runtime error path；artifact_data 缺字段、引用不一致、required heading/visual 缺失时显式失败，不构造假成功 artifact。
- 问：哪些本地验证最接近 CI，本轮为什么足够？
  答：后端覆盖 contract sync、agent runtime、artifact renderer、handoff；前端覆盖 workflow config 和 prompt registry；再运行 `py_compile` 与 `git diff --check`。真实模型 smoke 需要凭证、网络和额度，不作为默认本地门禁。

## 用户故事

作为产品经理或业务分析师，当我已有 PRD、需求蓝图或产品需求描述时，我可以选择 Alex 的「用户故事拆解」workflow，通过共享 Agent Runtime 生成 Epic map、User Story backlog、验收标准、依赖风险、Sprint 切片建议和 Lisa handoff 输入，从而把产品需求交给研发评审并为后续测试设计准备结构化输入。

## 范围

纳入本轮：

- 新增 `STORY_BREAKDOWN` runtime workflow，slug 为 `story-breakdown`，agent 为 `alex`。
- 阶段建议为：需求输入盘点、Epic 拆分、User Story 与验收标准、Sprint 切片与交付包。
- 新增或同步 Alex workflow listing、onboarding、starter prompts、prompt templates。
- 后端 artifact contract 必须覆盖核心标题、Mermaid / `ai4se-visual` 要求和阶段顺序。
- 后端 renderer 接受 `artifact_data` 并确定性渲染 Markdown、Mermaid 和 structured visual。
- 配置 handoff，使最终 Story 包可作为 Lisa `TEST_DESIGN/CLARIFY` 或 `REQ_REVIEW/REVIEW` 输入。
- 增加前后端测试证明该 workflow 使用共享配置和共享 runtime，而不是专属路径。

不纳入本轮：

- `PRD_REVIEW` workflow。
- 外部项目管理工具写入。
- 用户权限、团队协作或跨租户分享。
- 真实 DeepSeek V4 Flash smoke 自动门禁。

## 验收条件

1. Given Alex workflow 列表
   When 用户查看在线 workflow
   Then `story-breakdown` 显示为 online，并链接到 `/workspace/alex/story-breakdown`
   Evidence: frontend workflow config test。

2. Given workflow manifest
   When 后端加载共享 workflow 配置
   Then `STORY_BREAKDOWN` 的阶段顺序、prompt template、artifact headings、visual contract 与后端 contract registry 同步
   Evidence: `test_workflow_contract_sync.py`。

3. Given 模型返回合法 `artifact_data`
   When `parse_agent_turn_output_text()` 处理 `STORY_BREAKDOWN` 任一阶段
   Then 后端确定性渲染完整 Markdown artifact，并通过 `validate_agent_turn()`
   Evidence: `test_agent_runtime.py` 与 `test_artifact_data_renderers.py`。

4. Given Story 包最终阶段 artifact
   When 用户请求 handoff
   Then 系统暴露到 Lisa `TEST_DESIGN/CLARIFY` 和 `REQ_REVIEW/REVIEW` 的 handoff，prompt 中包含来源 workflow/stage/version 和 bounded source artifact
   Evidence: `test_workflow_handoffs.py`。

5. Given 本轮修改完成
   When 运行 CI 等价验证
   Then 后端聚焦 pytest、前端 workflow/prompt tests、`py_compile`、`git diff --check` 通过；未运行真实模型 smoke 的原因明确记录
   Evidence: 收尾说明。

## 风险

- Workflow 同步面较多，容易出现 manifest、backend contract、frontend prompt registry 不一致。用 sync tests 把不一致变成失败。
- Story 包 artifact_data 字段较丰富，renderer 与 contract 容易割裂。先用一份完整 fixture 驱动 renderer，再补 runtime parse 测试。
- Handoff 与 Lisa 的边界容易过度扩张。本轮只提供上下文输入，不触发 Lisa 自动执行，也不新增 runtime 分支。

## CI 等价验证计划

| 远端 CI / 风险面 | 本地等价命令 | 目的 |
| --- | --- | --- |
| New Agents backend contract/runtime | `python3 -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_workflow_handoffs.py -q` | 覆盖 manifest、contract、runtime、renderer、handoff |
| New Agents frontend config/prompt | `cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts` | 覆盖 workflow listing、slug、prompt registry |
| Python 语法 | `python3 -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/workflow_handoffs.py` | 捕获语法和导入级错误 |
| Diff hygiene | `git diff --check` | 捕获 whitespace 错误 |
