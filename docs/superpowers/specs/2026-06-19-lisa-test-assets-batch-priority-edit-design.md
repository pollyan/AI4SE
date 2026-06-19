# Lisa 测试资产批量优先级编辑设计

## Current State Gap Analysis

事实源快照：

- 已读取 `docs/todos/new-agents-evolution.md` 的 P1 #7。
- 已核对 `tools/new-agents/frontend/src/components/Header.tsx`、`tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`、`tools/new-agents/frontend/src/services/testAssetService.ts`。

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. 批量修改用例优先级 | P1 #7 | 用户能一次把当前资产集合里的用例优先级改为 P0/P1/P2 | 已能编辑单条用例并追加版本 | 多条用例需逐条打开编辑 | 降低资产维护成本，收敛“批量编辑”缺口 | 前端小切片，复用现有 PATCH | Header 测试 | 本轮 |
| B. 完整资产中心页面 | P1 #7 | 独立资产中心、筛选、批量操作、多视图 | 目前在 Header 弹层中展示 | 文件复杂度高，信息架构未拆 | 价值高 | 需要页面级设计 | 后续 |
| C. 风险/测试点独立管理 | P1 #7 | 风险和测试点可独立编辑生命周期 | 当前只读展示 | 缺服务端实体写回 | 价值高 | 后端/前端较大 | 后续 |

排序结论：选择 A，因为它复用现有 `PATCH /api/agent/test-assets/{collectionId}/test-cases/{caseId}`，能在不扩大架构面的情况下推进批量编辑能力。

## 目标

在 Lisa 测试资产弹层中，用户可以选择一个目标优先级，并将当前集合里的所有测试用例批量更新为该优先级。每条更新继续通过现有单条 case PATCH 追加版本。

## 设计

- 在测试资产弹层的 intent-tester 草稿操作条附近加入“批量优先级”控件。
- 用户选择 `P0/P1/P2` 后点击“应用优先级”。
- 前端依次调用 `updateTestAssetCase(collectionId, caseId, { title, priority })`，保留原标题，仅改优先级。
- 成功后用返回的 case 替换 `testAssetCollection.testCases` 中对应条目，并显示“已批量更新 N 条用例优先级”。
- 失败时显示“批量更新测试用例失败”；已成功的服务端更新不做前端回滚。

## 边界

本轮不新增：

- 后端批量 PATCH endpoint。
- 用例选择器和部分选择。
- 风险/测试点实体编辑。
- 完整资产中心页面。

## 验收条件

1. Given 当前测试资产集合有 2 条用例
   When 用户选择 `P1` 并点击“应用优先级”
   Then 前端调用两次 `updateTestAssetCase`，每次保留原 title 并传入 `priority: "P1"`。

2. Given 服务端返回更新后的 case
   When 批量更新完成
   Then 弹层展示更新后的优先级和成功提示。

3. Given 任一更新失败
   When 批量更新执行
   Then UI 显示失败提示，不伪造成功。

## 风险

当前采用前端顺序调用单条 PATCH，性能适合本地演示和中小规模资产集；后续完整资产中心可以再引入服务端批量 endpoint、选择器和部分成功报告。
