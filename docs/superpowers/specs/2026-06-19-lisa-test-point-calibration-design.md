# Lisa 测试点校准闭环设计

## Current State Gap Analysis

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-evolution.md`、`tools/new-agents/backend/test_assets.py`、`tools/new-agents/backend/routes.py`、`tools/new-agents/backend/tests/test_test_assets.py`、`tools/new-agents/backend/tests/test_agent_endpoint.py`、`tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`、`tools/new-agents/frontend/src/services/testAssetService.ts`、`tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`、`tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`、`tools/new-agents/frontend/src/core/types.ts`。
- 工作区隔离：当前目录不是独立 git worktree，且已有大量目标模式未提交改动。本轮沿用当前工作区，只修改 Lisa 测试资产相关文件和本轮 spec/plan/todo，避免把现有目标模式产物丢到新 worktree 之外。
- 按需未展开：本轮不修改 workflow、prompt、typed SSE 主链路、intent-tester 执行页和模型配置，因此未展开对应专项代码。

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | P1 #7 Lisa 测试资产闭环 | 测试点作为独立资产可校准、保存、恢复，并驱动覆盖概览和风险矩阵同步刷新 | 资产中心只读展示 `testPoints`，用例可编辑，资产问题可 triage | 没有测试点 PATCH API、前端服务或页面编辑入口；风险矩阵仍依赖实体化时快照 | 把“测试点库”从只读报告升级为可管理资产，是用户可感知能力包 | 中等，涉及后端实体、API、前端页面和测试；不改 SSE 主链路 | 后端 service/API 测试、前端 service/page 测试、lint | 本轮 |
| B | P1 #7 Lisa 测试资产闭环 | 资产中心支持分页、排序和筛选条件持久化 | 已有关键词搜索和优先级过滤 | 大集合浏览体验仍弱 | 有体验价值，但不改变核心资产能力 | 低到中等，主要前端状态和 URL/local storage | 前端页面测试 | 下一轮候选 |
| C | P1 #7 Lisa 测试资产闭环 | 自动批量写入 intent-tester 或导入后自动触发执行 | 已支持人工单条/批量导入和执行链接 | 自动化仍需人工点击 | 能提升端到端效率，但草稿未校准时可能污染外部用例库或误触发执行 | 高，跨系统写入与执行副作用明显 | 需要 intent-tester API/E2E 边界测试 | 归入更大“受控导入执行策略”能力包 |

排序结论：

1. 选择 A，因为它把测试点从只读展示升级为可保存资产，覆盖后端 API、前端操作、覆盖概览、风险矩阵和恢复证据，是当前 P1 #7 中最直接的用户可感知能力包。
2. B 暂不选，因为它主要改善列表浏览便利性，适合作为资产中心体验增强。
3. C 暂不选，因为自动写入/执行存在外部副作用，需要先有更完整的导入策略、校准门槛和执行确认。

切片准入判断：

- 用户可感知动作链：用户进入 `/test-assets/{collectionId}` -> 选择某个测试点 -> 调整优先级、关联风险、覆盖状态和覆盖用例 -> 保存 -> 页面重新显示最新覆盖概览、测试点明细和风险矩阵 -> 刷新后从服务端恢复。
- 相邻缺口合并：本轮合并测试点 PATCH API、后端校验、风险矩阵重建、前端 service 解析、页面编辑表单、保存反馈、错误状态和测试证据。
- Superpowers 成本合理性：该能力跨后端实体、API、前端服务和页面交互，完整流程成本匹配；不会为单字段或单按钮单独走一轮。
- 过薄风险检查：不是单端点或单控件；完成后用户可以独立管理测试点资产，并看到派生数据同步变化。
- 能力增量句：完成后，用户现在可以在 Lisa 测试资产中心直接校准测试点覆盖信息，并看到覆盖概览与风险矩阵按保存结果同步刷新。

本轮 milestone：

作为 Lisa 测试资产使用者，当我发现模型生成的测试点覆盖、优先级或风险关联不准确时，我可以在资产中心直接校准并保存测试点，使覆盖统计和风险矩阵反映校准后的资产状态。

## 设计

### 后端

新增测试点更新能力，复用现有 `AgentTestPointAsset` 实体，不新增 agent/workflow 专属运行时分支。PATCH 支持字段：

- `priority`：非空字符串。
- `risk`：非空字符串。
- `status`：只允许 `已覆盖`、`部分覆盖`、`未覆盖`。
- `testCases`：字符串数组，允许空数组表示未关联用例，但不允许空字符串项。

更新测试点后，服务端重建当前 collection 的风险矩阵，使 `GET /api/agent/test-assets/{collectionId}` 返回的 `coverageSummary` 和 `riskMatrix` 与最新测试点一致。未知 collection、未知测试点、未知字段或非法状态显式失败。

### 前端

`testAssetService` 新增 `updateTestAssetPoint()`，对测试点名称做 URL encode，解析服务端返回的测试点对象。`TestAssetsPage` 在“测试点覆盖”区新增编辑入口，允许选择优先级、覆盖状态，编辑关联风险和覆盖用例 CSV。保存成功后重新读取完整 collection，保证覆盖概览、风险矩阵和测试点明细一致。

### 边界

本轮不新增测试点创建 / 删除，不改用例版本模型，不自动写入 intent-tester，不触发 intent-tester 执行。测试点名称作为资产键保持不变，后续若需要重命名应单独设计迁移和关联更新规则。

## 验收条件

1. Given 已实体化 Lisa 测试资产集，When 调用测试点 PATCH 更新状态、风险和关联用例，Then 服务端保存测试点并在重新读取 collection 时返回更新后的覆盖概览和风险矩阵。
2. Given 未知测试点或非法状态，When 调用测试点 PATCH，Then API 返回显式错误，不伪造成功。
3. Given 用户打开资产中心，When 编辑并保存测试点，Then 页面显示保存成功，并刷新覆盖率、测试点明细和风险矩阵。
4. Given 服务端返回畸形测试点响应，When 前端 service 解析，Then 显式抛出协议错误。

## 验证计划

- `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`
- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `git diff --check`
