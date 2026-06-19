# New Agents 共享 Workflow Manifest 首轮设计

## Current State Gap Analysis

事实源快照：

- 已读取：`docs/todos/new-agents-evolution.md`、`docs/strategy/goal-mode-playbook.md`、`tools/new-agents/frontend/src/core/workflows.ts`、`tools/new-agents/frontend/src/core/types.ts`、`tools/new-agents/frontend/src/core/config/agentWorkflows.ts`、`tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`、`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/tests/test_workflow_contract_sync.py`。
- 工作区隔离：当前目录不是 linked worktree，且已有本轮目标模式大量未提交改动；本轮按 playbook 降级在当前工作区继续，只触碰本切片声明文件，不回滚既有改动。

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. 共享 workflow manifest 首轮 | P1 #4 | workflow id、agentId、slug、listing、stage id/name、onboarding 至少来自同一个数据源 | 前端 `WORKFLOWS` 持有运行时配置，后端用正则测试解析 `workflows.ts` | 后端 contract、前端 slug/listing/persona 元数据仍分散；没有机器可读共同事实源 | 降低后续工作流扩展和跨端漂移风险，是持久化、上下文 builder、跨 Agent 接力的前置基础 | 中等；若一次迁移 prompt/template 风险较高 | 后端 manifest sync 测试、前端 workflow config 测试 | 本轮 |
| B. 服务端会话持久化 | P1 #5 | run/session/artifact/version 服务端持久化 | 当前主要依赖浏览器 localStorage | 需要数据模型、API、迁移和 UI 恢复设计 | 价值高，但依赖 workflow/run 标识稳定 | 高 | 需要数据库和 API 测试 | 下一轮候选 |
| C. 文档批量校准 | P1 #9 | 架构/API/测试文档反映当前实现 | goal playbook 已改造，todo 有记录 | 仍需批量审计多个稳定文档 | 有助于目标模式长期质量 | 中等，偏文档 | 文档差异审计和引用检查 | 下一轮候选 |

排序结论：

1. 选择 A，因为 P0 首轮已经完成，P1 #4 是多个后续能力的基础；首轮只迁移非 prompt/template 元数据，能获得真实共享源收益且不破坏现有 prompt 模块边界。
2. B 暂不选，因为持久化会扩大到数据库、API、恢复 UI 和 judge 轨迹来源，当前缺少共享 workflow 元数据会增加漂移风险。
3. C 暂不选，因为文档校准应跟随刚完成的 manifest 切片一起记录更稳定的事实。

## 用户故事

作为 New Agents 维护者，当我新增或调整一个在线 workflow 时，我希望 workflow id、agentId、slug、展示文案、stage id/name 和 onboarding 信息至少有一个共享 manifest 作为共同事实源，从而避免前端展示、URL slug、后端阶段契约和测试各自漂移。

## 范围

进入本轮：

- 新增 `tools/new-agents/workflow_manifest.json`，覆盖 5 个在线 workflow 的基础元数据。
- 前端 `WORKFLOWS` 从 manifest 读取 workflow 基础元数据，再挂接现有 prompt/template 常量。
- 后端同步测试读取 manifest，校验 manifest stage 顺序与 `WORKFLOW_STAGES`、artifact contract stage keys 一致。
- 前端 workflow config 测试继续验证 slug/listing/card 派生。
- 更新 todo 进展记录。

不进入本轮：

- 不把 prompt/template 文本迁入 JSON。
- 不从 manifest 生成 Python contract 代码。
- 不迁移非 runtime 的 plan/offline workflow card。
- 不改路由、SSE、store 状态模型或 agent runtime。

## 验收条件

1. `tools/new-agents/workflow_manifest.json` 存在并覆盖所有 `WORKFLOW_STAGES` workflow。
2. 后端测试能证明 manifest stage id 顺序等于 `WORKFLOW_STAGES`。
3. 后端测试能证明 manifest stage keys 等于 `REQUIRED_ARTIFACT_HEADINGS` keys。
4. 前端 `WORKFLOWS` 的 id、agentId、slug、name、description、listing、stage id/name、onboarding 来自 manifest。
5. 前端 workflow config 测试和后端 contract sync 测试通过。

## 验证计划

- 先写后端 RED 测试，确认 manifest 缺失会失败。
- 新增 manifest，前端接入 manifest。
- 运行：
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_workflow_contract_sync.py -q`
  - `cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts`
  - `cd tools/new-agents/frontend && npm run lint`
  - `git diff --check`
