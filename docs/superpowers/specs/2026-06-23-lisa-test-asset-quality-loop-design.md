# Lisa 测试资产质量闭环设计

## 背景

Lisa TEST_DESIGN 已经能把 `CASES` 阶段产出物物化为测试资产集合，并支持用例编辑、资产 issue 确认/忽略、测试点覆盖校准、风险生命周期维护和 intent-tester 映射。当前缺口不是单个 API，而是这些动作没有汇总成一个统一、可追踪、可验收的资产质量状态。用户看到“资产问题”“覆盖率”“风险矩阵”时，仍需要自行判断测试资产是否已经可交付。

本轮按一个 Superpowers 流程完成一个厚切片：让 Lisa 测试资产集合拥有统一质量 summary，并让 issue、测试点、风险三类质量动作共同驱动这个状态。

## 目标

1. 后端 `TestAssetCollection` 序列化必须包含 `qualitySummary`，由持久化的 issue 状态、测试点覆盖状态和风险生命周期实时计算。
2. 前端 service 必须强校验 `qualitySummary` contract，避免旧结构或伪成功静默通过。
3. Lisa 测试资产中心必须展示质量状态、阻断/关注/通过 gate，并在确认/忽略 issue、保存测试点、保存风险后刷新或重算状态。
4. Header 中的 Lisa 测试资产快捷面板必须展示同一个质量状态，作为用户从当前 run 进入资产中心前的快速判断。
5. 不新增 Lisa 专属 runtime、API path、store 或 renderer；继续复用现有 `test_assets.py`、`routes_test_assets.py`、service parser 和共享 UI 页面。

## 非目标

1. 不改 Agent Runtime、typed SSE、workflow manifest 或模型调用链。
2. 不新增 DeepSeek/Lisa/Alex 专属传输或渲染基础设施。
3. 不引入真实模型 smoke；本轮只做本地确定性 contract/UI 验证。
4. 不重做资产中心整体视觉系统，只补质量闭环所需的状态、gate 和入口。

## 质量状态规则

`qualitySummary` 使用稳定、可测试的结构：

- `status`: `blocked | attention | ready`
- `label`: `存在阻断 | 需要关注 | 可交付`
- `pendingIssueCount`
- `confirmedIssueCount`
- `ignoredIssueCount`
- `uncoveredTestPointCount`
- `partialTestPointCount`
- `openRiskCount`
- `mitigatingRiskCount`
- `acceptedRiskCount`
- `closedRiskCount`
- `gates`: 每个 gate 包含 `id`、`status`、`title`、`detail`

判定规则：

- 有待处理 issue 或未覆盖测试点时，整体状态为 `blocked`。
- 没有阻断项，但存在已确认 issue、部分覆盖测试点、open/mitigating 风险时，整体状态为 `attention`。
- issue 均已忽略或不存在、测试点均已覆盖、风险均 accepted/closed 时，整体状态为 `ready`。
- ignored issue 不阻断质量状态；confirmed issue 代表用户已确认真实问题，仍需要关注。
- accepted/closed 风险不阻断；open/mitigating 风险需要关注。

## 用户体验

资产中心顶部从单纯统计卡升级为“质量状态 + gate 列表 + 统计卡”：

- 用户先看到 `存在阻断`、`需要关注` 或 `可交付`。
- gate 告诉用户阻断来自资产问题、测试点覆盖还是风险处置。
- 用户在同一页面继续执行现有操作：确认/忽略 issue、编辑测试点、编辑风险。
- 保存测试点和风险后沿用已有刷新集合逻辑，状态随后端 summary 更新。
- issue 状态更新后可以在本地更新 collection 并重算 summary，避免只为一个 issue 额外刷新整集合。

Header 快捷面板展示同一 summary 的简化版本：

- 显示质量状态和 gate 数量。
- 保留现有资产问题、风险矩阵、测试点覆盖和 intent-tester 草稿入口。
- 不在 Header 里复制完整资产中心编辑能力，避免两个编辑工作台分叉。

## 测试策略

按 TDD 执行：

1. 后端先补失败测试，证明物化集合包含 `qualitySummary`，并证明 issue、测试点、风险状态变化会改变 summary。
2. service parser 先补失败测试，证明缺失或非法 `qualitySummary` 会被拒绝。
3. 资产中心先补失败测试，证明 quality gate 可见，并在 issue/test point/risk 操作后更新。
4. Header 先补失败测试，证明快捷面板展示同一质量状态。
5. 只在 RED 通过预期失败后写实现。

## 验收标准

1. `tools/new-agents/backend/tests/test_test_assets.py` 通过，并覆盖 blocked/attention/ready 质量状态。
2. `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts` 通过，并覆盖 parser contract。
3. `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx` 通过，并覆盖质量状态随 issue/test point/risk 操作更新。
4. `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx` 通过，并覆盖快捷面板质量状态展示。
5. `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 更新 E04 进度，说明本轮消化内容和残余风险。
