# Lisa 测试资产质量状态闭环 Spec

> 日期: 2026-06-23
> 状态: 本轮目标模式执行中

## 背景

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 中 E04 仍是 P0 活动候选: “Lisa 测试资产质量闭环”。当前代码已经具备较多底层能力:

- 后端 `test_assets.py` 可以物化 TEST_DESIGN/CASES 产物，持久化测试用例、测试点、资产问题、风险矩阵和 intent-tester 映射。
- API 已支持更新资产问题状态、校准测试点覆盖、编辑/新增/删除风险并刷新派生风险矩阵。
- Header 测试资产弹层和资产中心页面已经能展示并编辑这些字段。

剩余缺口是这些字段仍以分散列表呈现，用户需要自己判断资产是否可交付。E04 的关键不是再新增一个 Lisa 专属 runtime 或 API，而是把已有持久化字段汇总成稳定、可解释、可随操作变化的资产质量状态。

## 用户故事

作为 Lisa 测试资产使用者，我希望在测试资产弹层和资产中心一眼看到当前资产是否可交付、还有哪些阻断项或关注项，并在确认/忽略 issue、补齐测试点覆盖、处置风险后看到质量状态同步变化，这样我能判断资产是否可以进入后续测试设计交付或 intent-tester 导入执行。

## 范围

本轮包含:

- 新增共享前端纯函数，基于 `TestAssetCollection` 派生质量状态。
- 状态覆盖三档:
  - `blocked`: 存在待处理资产问题、未覆盖测试点，或 open 且未分配责任人的风险。
  - `attention`: 没有阻断项，但存在部分覆盖测试点、处置中的风险或已接受风险。
  - `ready`: 没有阻断项或关注项，资产可交付。
- 在 Header 测试资产弹层显示质量状态、阻断/关注计数和下一步动作。
- 在 TestAssetsPage 资产中心显示同一质量状态和明细，且操作后基于更新后的 collection 重新派生。
- 更新 enhancement diagnostic todo，记录 E04 已消化的完成定义与验证。

本轮不包含:

- 不新增后端 API、数据库字段或 Lisa 专属 runtime。
- 不新增 intent-tester 自动执行联动。
- 不实现全 workflow 质量评分 E08。
- 不改变共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run/artifact 模型。

## 质量状态规则

输入: `TestAssetCollection`。

输出:

- `status`: `blocked | attention | ready`
- `label`: 用户可读状态标签
- `summary`: 一句话说明当前资产质量
- `blockingItems`: 阻断项列表
- `attentionItems`: 关注项列表
- `nextAction`: 下一步动作建议

阻断项:

- `assetIssues` 中 `status === 'pending'`。
- `testPoints` 中 `status === '未覆盖'`。
- `riskMatrix` 中 `status === 'open'` 且 `owner` 为空。

关注项:

- `testPoints` 中 `status === '部分覆盖'`。
- `riskMatrix` 中 `status === 'mitigating'`。
- `riskMatrix` 中 `status === 'accepted'`。

已确认或忽略的 issue 不再阻断；已关闭风险不再进入关注项。

## 验收标准

- 纯函数测试覆盖 blocked、attention、ready 三档和 issue 状态变化。
- Header 弹层在加载资产后显示质量状态与下一步动作。
- TestAssetsPage 显示质量状态；当 issue 被确认后，状态计数随本地 collection 更新。
- TestAssetsPage 已有测试点/风险编辑路径继续通过，证明质量状态不破坏现有资产中心操作。
- `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 记录 E04 完成态。

## 验证计划

- `npm run test -- --run src/core/__tests__/testAssetQuality.test.ts src/components/__tests__/Header.test.tsx src/pages/__tests__/TestAssetsPage.test.tsx`
- `npm run lint`
- `git diff --check`
