# New Agents Workflow 入口专业 Preview 设计

## 背景

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 E01 "Workflow 入口 preview" 标为 P0。当前 New Agents 已经通过共享 `workflow_manifest.json`、前端 `WORKFLOWS`、typed SSE 和共享 Agent Runtime 支撑 Lisa/Alex 多工作流，但用户在进入工作区前只能看到 workflow 名称和简短描述，无法判断它适合什么场景、不适合什么场景、需要准备什么输入、会交付什么产物。

本轮选择该切片，是因为它能独立改善 New Agents 主入口决策质量，同时不触碰后端 runtime、SSE、持久化或 artifact renderer。

## 用户故事

作为 New Agents 用户，我希望在选择 Lisa/Alex workflow 时直接看到每个 workflow 的适用场景、不适用场景、输入要求、预期产物和样例输入，这样我可以在进入工作区前判断当前目标是否匹配，并用更合适的启动信息开始工作。

## 范围

纳入本轮：

- 在 `tools/new-agents/workflow_manifest.json` 的每个在线 workflow `listing` 中补充 `preview` 元数据。
- 在前端类型和 `getAgentWorkflows()` 投影中承接 `preview`。
- 在 `WorkflowSelect` 页面展示 preview 信息，并保持 dev/plan 非运行时卡片行为不变。
- 添加配置同步测试和页面渲染测试，保证所有在线 workflow 都有完整 preview 且 UI 消费这些字段。
- 更新活跃 todo 记录，标明 E01 已由本轮 milestone 消化。

不纳入本轮：

- 自动 workflow 推荐排序。
- 生成后 artifact 质量诊断、质量评分或自动修复。
- DeepSeek V4 artifact data schema/renderer 改造。
- 新增 runtime、API path、store、renderer 或 agent-specific 分支。

## 数据模型

新增前端共享类型：

```ts
export interface WorkflowPreviewConfig {
    suitableFor: string[];
    notSuitableFor: string[];
    requiredInputs: string[];
    expectedOutputs: string[];
    sampleInput: string;
}
```

`WorkflowListingConfig` 增加：

```ts
preview: WorkflowPreviewConfig;
```

该字段属于 workflow 配置元数据，只服务入口展示和测试，不进入 Agent Runtime 请求，不改变 typed SSE 协议。

## UI 行为

在线 workflow 卡片继续点击进入现有 `/workspace/:agentId/:workflowSlug`。

每张在线卡片展示：

- 适合：2-3 条短句。
- 不适合：1-2 条短句。
- 准备输入：2-3 条短句。
- 产出：2-3 条短句。
- 样例输入：一条可复制理解的启动语句。

非在线 dev/plan 卡片继续显示原有状态和“即将推出”，不要求 preview，也不能被点击进入 workspace。

## 错误与边界

- preview 缺字段、空数组或空字符串由测试失败暴露，不在运行时静默 fallback。
- UI 只消费 `getAgentWorkflows()` 投影，不直接绕过共享 workflow registry。
- 文案保持简短，避免卡片内容撑破移动端布局。

## 验收条件

- 每个在线 workflow 的 `listing.preview` 都包含适用、不适用、输入要求、预期产物和样例输入。
- `getAgentWorkflows()` 返回的在线卡片保留 preview 数据，且与 `WORKFLOWS` 中 manifest 派生配置一致。
- `WorkflowSelect` 对 Lisa/Alex 在线 workflow 渲染 preview 区块。
- 点击在线 workflow 仍导航到原有 workspace URL。
- dev/plan workflow 不要求 preview，状态展示和不可点击行为不变。

## 验证计划

- 先补失败测试：
  - `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
  - `tools/new-agents/frontend/src/pages/__tests__/WorkflowSelect.test.tsx`
- 聚焦验证：
  - `cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/pages/__tests__/WorkflowSelect.test.tsx`
- 扩展验证：
  - `cd tools/new-agents/frontend && npm run lint`

## Worktree 决策

已执行隔离检查。当前主工作区存在未提交的活跃 todo 文件，本轮需要以它们作为事实源并更新其中一个 todo。为避免隔离 worktree 丢失当前未提交工作池输入，本轮在当前工作区串行执行，并严格限定写入范围，不触碰已有 zip 产物和无关 `docs/plans/tech-debt.md`。
