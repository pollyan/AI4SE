# Lisa 测试资产中心设计

## Current State Gap Analysis

P1 #7 已经沉淀 Lisa 测试资产集合、用例版本、覆盖摘要、资产问题、风险矩阵、测试点覆盖、intent-tester 草稿导入和弹层内单条/全量优先级编辑。但这些能力仍集中在 Header 弹层里，不能作为一个可导航的资产中心承载较长资产列表、部分选择和后续扩展。

服务端已提供 `GET /api/agent/test-assets/{collectionId}` 和单条用例 `PATCH`。前端 `testAssetService` 目前只有 materialize 与 update 方法，缺少读取已实体化集合的 GET 方法。App 路由也没有资产中心页面。

## 切片准入判断

- 用户可感知动作链：用户在 Lisa 工作台打开测试资产，进入独立资产中心，查看覆盖概览、用例、问题、风险和测试点，选择部分用例批量修改优先级，并看到持久化后的版本变化。
- 相邻缺口合并：本轮合并资产中心入口、GET 集合读取、独立页面展示、部分选择模型、批量更新结果反馈和错误状态；不再把“批量字段操作”拆成独立小切片。
- Superpowers 成本合理性：该 milestone 交付一个可导航用户功能，并把已分散在弹层里的只读/编辑能力升级为更适合后续扩展的资产工作台，值得完整 CGA/spec/plan/TDD/验证。
- 过薄风险检查：本轮不是单按钮、单字段、单 helper、单 parser 或单测试；服务函数和 Header 入口都只是资产中心用户动作链的组成部分。

## User Story

作为 Lisa 用户，我希望从当前测试资产弹层进入一个独立资产中心，查看当前集合的覆盖概览、测试用例、资产问题、风险矩阵和测试点覆盖，并能选择部分用例批量修改优先级，而不是只能在小弹层里全量更新。

## Scope

- 新增 `fetchTestAssetCollection(collectionId)` 前端服务，复用现有集合 parser。
- 新增 `/test-assets/:collectionId` 前端路由和页面。
- Header 测试资产弹层在 materialize 成功后提供“打开资产中心”入口。
- 资产中心展示集合元信息、覆盖概览、用例列表、资产问题、风险矩阵和测试点覆盖。
- 资产中心支持选择全部/部分测试用例，并对选中用例批量更新 P0/P1/P2。
- 批量更新继续复用现有单条 `PATCH`，不新增后端批量 endpoint。

## Non-goals

- 不新增风险/测试点独立编辑库。
- 不自动写入 intent-tester 或触发执行。
- 不引入新的测试资产运行时、store 或后端 API 分支。
- 不在本切片做完整表格筛选、排序、分页或权限模型。

## Acceptance Criteria

1. `/new-agents/test-assets/7` 会调用 `GET /new-agents/api/agent/test-assets/7` 并渲染资产中心。
2. 非法 collection id 或加载失败会显示明确错误，不伪造空成功。
3. Header 弹层加载出集合后提供“打开资产中心”入口并导航到对应页面。
4. 资产中心可勾选部分用例，点击批量优先级后只更新选中用例。
5. 批量更新成功后页面中的对应用例优先级和版本号更新，并显示成功计数。
6. 测试覆盖服务解析、页面加载、Header 入口和部分选择批量编辑。
