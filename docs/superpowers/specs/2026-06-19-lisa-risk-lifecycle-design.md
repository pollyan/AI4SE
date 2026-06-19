# Lisa 风险生命周期管理设计

## Current State Gap Analysis

事实源快照：

- 已读取：`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-evolution.md`、`tools/new-agents/backend/models.py`、`tools/new-agents/backend/test_assets.py`、`tools/new-agents/backend/routes.py`、`tools/new-agents/backend/tests/test_test_assets.py`、`tools/new-agents/backend/tests/test_agent_endpoint.py`、`tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`、`tools/new-agents/frontend/src/services/testAssetService.ts`、`tools/new-agents/frontend/src/core/types.ts`、`tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`。
- 工作区隔离：当前目录不是独立 git worktree，且已有大量目标模式未提交改动。本轮沿用当前工作区，只修改 Lisa 测试资产相关文件和本轮 spec/plan/todo。
- 按需未展开：本轮不修改 Agent Runtime、workflow manifest、prompt、intent-tester 执行链路或模型配置。

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | P1 #7 Lisa 测试资产闭环 | 风险矩阵可被处置、保存、恢复，并在测试点重建风险矩阵时保留同名风险生命周期 | 风险矩阵只读展示；测试点校准会重建风险矩阵 | 没有风险状态、责任人、备注、PATCH API 或前端编辑入口 | 把风险矩阵从报告升级为可管理资产，补齐“风险生命周期管理” | 中等，涉及模型字段、派生重建保留、API 和前端编辑 | 后端 service/API 测试、前端 service/page 测试、lint | 本轮 |
| B | P1 #7 Lisa 测试资产闭环 | 资产中心分页、排序、筛选条件持久化 | 已有搜索和优先级过滤 | 大集合浏览便利性不足 | 有体验价值，但不补齐资产治理闭环 | 低到中等，前端为主 | 前端页面测试 | 下一轮候选 |
| C | P1 #7 Lisa 测试资产闭环 | 受控自动写入 intent-tester 并可触发执行 | 已有人工单条/批量导入和执行链接 | 自动化仍需人工点击 | 端到端效率高，但外部写入/执行副作用明显 | 高，需要导入校准策略和执行确认 | 跨系统 API/E2E 测试 | 后续更大能力包 |

排序结论：

1. 选择 A，因为它与刚完成的测试点校准同属资产治理链路，能把风险矩阵从只读派生数据升级为可保存、可恢复、可处置的用户能力。
2. B 暂不选，因为它主要优化浏览效率，不改变资产能力边界。
3. C 暂不选，因为自动写入和执行需要额外的防污染策略，不适合在风险生命周期之前推进。

切片准入判断：

- 用户可感知动作链：用户进入 `/test-assets/{collectionId}` -> 在风险矩阵选择风险 -> 设置处置状态、责任人、备注 -> 保存 -> 页面显示最新风险生命周期 -> 刷新或测试点校准导致风险矩阵重建后，同名风险保留处置信息。
- 相邻缺口合并：本轮合并模型字段、风险序列化、重建保留逻辑、PATCH API、前端 service、资产中心编辑 UI、保存反馈和验证。
- Superpowers 成本合理性：该能力跨数据模型、派生重建、API 和 UI，值得完整 spec/plan/TDD/验证。
- 过薄风险检查：不是只新增字段或按钮；完成后用户可以实际管理风险生命周期。
- 能力增量句：完成后，用户现在可以在 Lisa 测试资产中心处置风险，并在资产刷新或测试点重建矩阵后保留风险处置状态。

本轮 milestone：

作为 Lisa 测试资产使用者，当我看到风险矩阵中的风险项时，我可以标记其处置状态、责任人和备注，从而把风险从只读报告项推进为可追踪的测试资产。

## 设计

### 后端

在 `AgentRiskMatrixAsset` 上增加生命周期字段：

- `status`：`open`、`mitigating`、`accepted`、`closed`。
- `owner`：责任人，可为空字符串。
- `note`：处置备注，可为空字符串。

实体化时风险默认为 `open`。更新风险时只允许 PATCH `status`、`owner`、`note`；未知风险或非法状态显式失败。重建风险矩阵时按 `risk` 名称保留已有生命周期字段，避免测试点校准造成处置信息丢失。

### 前端

`riskMatrix` 类型和 parser 增加 `status`、`owner`、`note`。`testAssetService` 新增 `updateTestAssetRisk()`。资产中心“风险矩阵”区增加编辑入口，允许保存状态、责任人和备注；保存后更新当前 collection 中对应风险项。

### 边界

本轮不新增风险创建、删除、重命名，也不把风险生命周期反写到测试点或用例。风险身份仍以 `risk` 文本为键；后续若需要稳定风险 ID，应另做迁移设计。

## 验收条件

1. Given 已实体化风险矩阵，When 更新风险状态、责任人和备注，Then 服务端保存并在重新读取 collection 时返回最新生命周期。
2. Given 同名风险已有生命周期，When 测试点校准触发风险矩阵重建，Then 同名风险保留处置信息。
3. Given 用户打开资产中心，When 编辑风险生命周期并保存，Then 页面显示保存成功和最新状态。
4. Given 未知风险或非法状态，When 调用 PATCH，Then 返回显式错误。

## 验证计划

- `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`
- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `git diff --check`
