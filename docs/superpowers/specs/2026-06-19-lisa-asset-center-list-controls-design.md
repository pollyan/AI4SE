# Lisa 资产中心列表管理设计

## Current State Gap Analysis

事实源快照：

- 已读取：`AGENTS.md`、`docs/index.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-evolution.md`、`tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`、`tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`。
- 工作区隔离：当前目录不是独立 git worktree，且已有大量目标模式未提交改动；本轮沿用当前工作区，只修改资产中心列表管理相关前端、todo、spec 和 plan，避免回滚或格式化无关改动。
- 按需未展开：本轮不修改后端资产模型、Agent Runtime、workflow manifest、prompt、intent-tester 导入 / 执行链路或模型配置。

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | P1 #7 Lisa 测试资产闭环 | 资产中心用例列表可排序、分页，并通过 URL 恢复搜索 / 优先级 / 排序 / 页码 / 页大小 | 当前资产中心只有本地搜索和优先级过滤，所有用例一次性展示，刷新后条件丢失 | 大集合浏览效率不足，无法分享或恢复同一资产视图 | 把资产中心从小样例工作台推进为可管理较大测试资产集合的页面能力 | 低到中等，前端状态和 URL 同步需避免循环更新 | React Testing Library 页面测试、TypeScript lint | 本轮 |
| B | P1 #7 Lisa 测试资产闭环 | 独立风险库支持创建、删除、重命名和稳定风险 ID | 当前风险生命周期按风险文本保存 | 缺少稳定风险身份和风险 CRUD | 长期价值高，但需要模型迁移和风险身份设计 | 中高，涉及后端模型和历史数据迁移 | 后端 API / 前端页面测试 | 下一轮候选 |
| C | P1 #7 Lisa 测试资产闭环 | 受控自动批量写入 intent-tester 或导入后自动触发执行 | 当前已有手动导入和执行链接 | 自动化仍需人工点击 | 端到端效率高，但存在污染外部测试库和误触发执行风险 | 高，需要确认、幂等、防重复、执行结果回写策略 | 跨系统 service / E2E 测试 | 后续更大能力包 |

排序结论：

1. 选择 A，因为它是用户可直接感知的资产中心管理能力，能一次性合并分页、排序、筛选条件持久化和可恢复链接，不是单控件微切片。
2. B 暂不选，因为风险生命周期刚完成，稳定风险 ID / CRUD 需要单独的数据迁移设计。
3. C 暂不选，因为自动写入和执行有外部副作用，应在资产管理体验稳定后再做受控自动化。

切片准入判断：

- 用户可感知动作链：用户进入 `/test-assets/{collectionId}` -> 输入搜索 / 选择优先级 -> 选择排序和页大小 -> 翻页 -> URL query 同步 -> 刷新或复制链接后恢复同一列表视图。
- 相邻缺口合并：本轮合并搜索持久化、优先级过滤持久化、排序、分页、页大小、页码边界修正、选择状态一致性和页面测试。
- Superpowers 成本合理性：该能力触及用户主页面的列表模型、URL 状态、批量选择和测试夹具，值得完整 CGA/spec/plan/TDD/验证。
- 过薄风险检查：不是单个筛选框或单个分页按钮；完成后用户获得完整、可恢复的大集合浏览能力。
- 能力增量句：完成后，用户现在可以在 Lisa 测试资产中心稳定浏览大量测试用例，并通过 URL 恢复同一搜索、筛选、排序和分页视图。

本轮 milestone：

作为 Lisa 测试资产使用者，当资产集合包含较多测试用例时，我可以搜索、筛选、排序、分页浏览，并在刷新或分享链接后恢复当前视图，从而持续管理同一批测试资产。

## 设计

### URL 状态模型

资产中心在 query string 中保存列表视图状态：

- `q`：搜索关键词，空值不写入 URL。
- `priority`：`all`、`P0`、`P1`、`P2`，默认 `all` 不写入 URL。
- `sort`：`id`、`priority`、`title`、`risk`，默认 `id` 不写入 URL。
- `direction`：`asc`、`desc`，默认 `asc` 不写入 URL。
- `page`：从 1 开始，默认 1 不写入 URL。
- `pageSize`：`5`、`10`、`20`，默认 `10` 不写入 URL。

页面初次加载和浏览器 query 变化时从 URL 解析状态。非法值回落到默认状态并在下一次用户操作时写出规范 query；不弹出错误，因为这是视图偏好，不是资产数据失败。

### 列表行为

列表处理顺序为：搜索 -> 优先级过滤 -> 排序 -> 分页。

排序规则：

- `id`、`title`、`risk` 按字符串本地比较。
- `priority` 按 P0、P1、P2 顺序排序，未知优先级排在已知优先级之后。
- `direction=desc` 反转排序结果。

当搜索、优先级、排序、方向或页大小变化时，页码回到 1。当前页超出过滤后总页数时自动夹紧到最后一页。选择全部只选择当前页可见用例，避免跨页误批量更新。

### UI

在现有测试用例工具栏中增加：

- 排序字段下拉。
- 排序方向下拉。
- 页大小下拉。
- 分页状态和上一页 / 下一页按钮。

显示计数从“显示 N / 总数”升级为“显示 A-B / 过滤后 N 条 / 总计 M 条”。当过滤后为空时显示空状态。

### 边界

本轮不做服务端分页，不改变资产 API，不持久化到数据库或 localStorage。URL 是本轮唯一持久化载体。风险矩阵、测试点和资产问题列表暂不分页；它们的管理能力已有独立闭环，后续如增长明显再单独聚合为面板级列表管理。

## 验收条件

1. Given URL 带 `q=失败&priority=P1&sort=risk&direction=desc&pageSize=5&page=1`，When 打开资产中心，Then 搜索、优先级、排序、方向、页大小控件恢复对应值，列表只展示匹配结果。
2. Given 用户修改搜索、优先级、排序、方向或页大小，When 页面更新列表，Then URL query 同步更新，页码回到 1。
3. Given 过滤后测试用例多于页大小，When 用户点击下一页，Then 页面只展示下一页用例，URL 中 `page` 同步更新。
4. Given 当前页只显示部分用例，When 用户点击选择全部并批量更新，Then 只更新当前页可见用例，不跨页更新隐藏用例。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `git diff --check`
