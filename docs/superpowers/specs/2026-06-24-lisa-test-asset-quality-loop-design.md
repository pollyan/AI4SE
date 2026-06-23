# Lisa 测试资产质量闭环设计

## 背景

Lisa `TEST_DESIGN/CASES` 已经能把测试用例集物化为测试资产集合，并支持测试用例编辑、资产 issue 确认/忽略、测试点覆盖校准、风险生命周期维护、intent-tester 映射和执行结果记录。当前缺口不是单个 API 或单个控件，而是这些动作没有汇总成一个统一、可追踪、可验收的资产质量状态。用户看到“资产问题”“覆盖率”“风险矩阵”时，仍需要自己判断这批资产是否已经可以交付。

本轮能力包把 E04 “Lisa 测试资产质量闭环”收束为一个端到端质量门禁：后端根据持久化 issue、测试点和风险实时计算 `qualitySummary`；前端严格解析该 contract；资产中心和 Header 入口展示同一质量状态；用户处理 issue、测试点和风险后，质量状态随动作更新。

不新增 Lisa 专属 runtime、API path、store 或 renderer；继续复用现有 `test_assets.py`、`routes_test_assets.py`、前端 `testAssetService`、Header 快捷面板和 `TestAssetsPage`。

## Superpowers 头脑风暴记录

### Explore Project Context

问: 当前代码说明 Lisa 测试资产能力已经有什么？

答: 后端 `test_assets.py` 已经能导出和物化 Lisa 测试资产，持久化测试用例、测试点、资产 issue、风险矩阵和 intent-tester 映射。前端 `Header` 已有测试资产快捷面板，`TestAssetsPage` 已有资产中心、issue 状态更新、测试点编辑、风险生命周期编辑和 intent-tester 操作。已有测试覆盖 `test_test_assets.py`、`testAssetService.test.ts`、`Header.test.tsx` 和 `TestAssetsPage.test.tsx`。

问: 当前需求是否过大，需要拆成多个 Superpowers？

答: 不需要。E04 的用户目标是“测试点、风险、用例 issue 可修复、确认、追踪并影响资产质量状态”。如果只做后端 summary、只做 Header 展示或只做 issue 状态更新，都不能让用户完成“判断资产是否可交付”这段真实任务。本轮必须把后端 summary、前端 contract、资产中心展示、Header 展示和状态更新一起纳入同一能力包。

问: 当前已有堆叠分支能否直接作为本轮结果？

答: 不能。`codex/lisa-test-asset-quality-loop-after-diagnostics` 包含 Alex PRD、Story、DeepSeek readiness、Artifact 诊断等前置提交，不是聚焦 Lisa 的干净 milestone。本轮只能把其中 Lisa 相关设计和实现作为参考，在基于上一轮 Artifact 诊断 commit 的隔离 worktree 中形成单独 commit。

### Visual Companion Decision

问: 是否需要浏览器 visual companion？

答: 不需要。这里不是重新设计资产中心布局，而是在已有 Header 面板和资产中心中增加质量状态、gate 和统计信息。验收重点是 contract 与状态变化是否正确；组件测试足以覆盖可见文案和交互更新。

### Clarifying Questions

问: 主要用户是谁？

答: 使用 Lisa 测试设计工作流并进入测试资产中心的测试负责人、研发评审者和需要把测试资产导入 intent-tester 的用户。

问: 用户要完成什么？

答: 用户要知道当前测试资产集是否存在阻断项、需要关注还是已经可交付，并通过处理 asset issue、校准测试点覆盖和维护风险状态让质量状态变化。

问: 成功状态是什么？

答: 用户在 Header 快捷面板和资产中心都能看到同一个质量状态；待处理 issue 或未覆盖测试点会阻断交付；已确认 issue、部分覆盖测试点、open/mitigating 风险会提示关注；全部 issue 处理、测试点覆盖、风险 accepted/closed 后显示可交付。

问: 输入来源是什么？

答: 后端持久化的 `AgentTestAssetIssue.status`、`AgentTestPointAsset.status`、`AgentRiskMatrixAsset.status`，以及前端获取到的 `TestAssetCollection`。

问: 关键约束是什么？

答: 必须复用现有 test asset API 和页面，不新增 workflow runtime、SSE、manifest 或 renderer；前端 service 必须严格校验 `qualitySummary`，不能对缺失字段静默 fallback；Header 不复制完整编辑工作台，只显示状态和 gate。

问: 失败路径是什么？

答: 后端未知集合、未知 issue/test point/risk 继续显式失败；前端收到缺失或非法 `qualitySummary` 直接抛出 invalid response；本地 issue 状态更新后如果只返回 issue，需要用共享纯函数重算当前 collection 的 summary，避免 UI 显示旧状态。

问: 下游承接是什么？

答: 质量闭环会成为后续 handoff 上下文强化、运行质量评分和 CI/evidence 管理的输入，但本轮不做跨 run 趋势、intent-tester 自动执行或外部系统写入。

### Approaches

方案 A: 后端权威 `qualitySummary` + 前端严格解析 + 前端本地重算 helper。

取舍: 后端作为持久化状态的权威来源，前端 service 拒绝非法 contract；issue 单项更新后用纯函数本地重算，测试点和风险保存后沿用现有集合刷新或状态替换。实现面覆盖完整用户闭环，推荐采用。

方案 B: 只在前端根据 collection 计算质量状态，不改后端 response。

取舍: 实现更快，但 API contract 无法表达资产质量，Header、资产中心和未来消费者容易出现计算口径分叉，也无法在后端测试中证明持久化动作影响质量状态。本轮不选。

方案 C: 新增独立质量 API 或质量评分模型。

取舍: 可以扩展到复杂评分，但会新增 API surface 或模型依赖，不符合当前“确定性质量门禁”目标；E04 需要的是 issue/覆盖/风险驱动的可验收闭环，不需要 LLM judge。本轮不选。

### Presented Design

Architecture: `test_assets.py` 在 `_serialize_collection()` 中追加 `qualitySummary`。该 summary 由 issue 状态、测试点覆盖状态和风险生命周期确定性计算。前端 `testAssetService.ts` 严格解析 summary，`testAssetQuality.ts` 提供同规则纯函数供本地状态更新使用。

Components: 后端新增 `_build_quality_summary()` 和测试；前端新增 `TestAssetQualitySummary` / `TestAssetQualityGate` 类型、service parser、`withTestAssetQualitySummary()` helper、资产中心质量面板和 Header 紧凑质量面板。

Data Flow: 用户物化或打开资产集合 -> 后端返回 `qualitySummary` -> service 校验 -> Header 与资产中心展示。用户确认/忽略 issue 后，前端用返回的 issue 替换本地列表并重算 summary；用户保存测试点/风险后，使用现有后端更新结果与刷新/替换流程保持 summary 一致。

Error Handling: 后端对非法 patch 保持显式 `ValueError`；前端对非法 response 抛出 `Invalid test asset collection response`；summary 规则不使用隐藏默认值。没有资产问题、测试点或风险时，计数为 0，gate 显示通过。

Testing: 先补后端 RED 测试证明 `qualitySummary` 缺失并覆盖 blocked/attention/ready；再补 service parser RED；再补前端 helper RED；再补 `TestAssetsPage` 和 `Header` UI RED。实现后运行后端 test assets 聚焦测试、前端 service/helper/page/Header 聚焦测试、`npm run lint`、`git diff --check`。

## 用户故事

作为 Lisa 测试资产用户，我希望在 Header 快捷面板和资产中心看到当前资产集的统一质量状态，并能通过处理 issue、校准测试点覆盖、维护风险状态，让系统明确告诉我资产是否仍有阻断、需要关注或已经可交付。

## 范围

纳入本轮：

- 后端 `TestAssetCollection` 序列化新增 `qualitySummary`。
- `qualitySummary` 统计 issue、测试点和风险状态，并输出 gate 列表。
- 前端 service 对 `qualitySummary` 做严格 contract 校验。
- 新增前端纯函数，支持本地 collection 重算 summary。
- `TestAssetsPage` 展示质量状态、gate 和统计信息，并在 issue/test point/risk 操作后保持状态更新。
- `Header` 测试资产快捷面板展示同一质量状态和 gate 摘要。
- 更新 active todo，记录 E04 消化结果和剩余候选。

不纳入本轮：

- intent-tester 自动执行或自动回写。
- 新增 Lisa/Alex/DeepSeek 专属 runtime、API path、store 或 renderer。
- LLM judge、真实模型 smoke、跨 run 质量趋势。
- 重做资产中心整体视觉布局。
- Workflow handoff 上下文强化。

## 质量状态规则

`qualitySummary` 结构：

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
- ignored issue 不阻断质量状态；confirmed issue 表示真实问题已被确认，仍需要关注。
- accepted/closed 风险不阻断；open/mitigating 风险需要关注。

## 验收条件

- 后端物化资产集合后返回 `qualitySummary`，并能随 issue、测试点、风险状态变化。
- 前端 service 遇到缺失或非法 `qualitySummary` 明确失败。
- 资产中心能展示质量状态和 gate，并在 issue/test point/risk 操作后更新。
- Header 快捷面板展示同一质量状态，不复制完整编辑能力。
- 不新增 agent-specific runtime、API path、store 或 renderer。

## 验证计划

- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_test_assets.py -q`
- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/core/__tests__/testAssetQuality.test.ts src/pages/__tests__/TestAssetsPage.test.tsx src/components/__tests__/Header.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `git diff --check`
