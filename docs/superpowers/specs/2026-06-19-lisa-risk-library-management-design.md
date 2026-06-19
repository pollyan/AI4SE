# Lisa 风险库稳定身份与管理设计

## Current State Gap Analysis

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-evolution.md`、`tools/new-agents/backend/models.py`、`tools/new-agents/backend/test_assets.py`、`tools/new-agents/backend/routes.py`、`tools/new-agents/backend/tests/test_test_assets.py`、`tools/new-agents/backend/tests/test_agent_endpoint.py`、`tools/new-agents/frontend/src/core/types.ts`、`tools/new-agents/frontend/src/services/testAssetService.ts`、`tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`、`tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`、`tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`。
- 工作区隔离：当前目录不是独立 git worktree，且已有大量目标模式未提交改动。本轮沿用当前工作区，只修改 Lisa 测试资产风险库相关后端、前端、todo、spec 和 plan。
- 按需未展开：本轮不修改 Agent Runtime、workflow manifest、prompt、LLM judge、intent-tester 执行链路或模型配置。

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | P1 #7 Lisa 测试资产闭环 | 风险矩阵具备稳定风险 ID，支持新增、重命名、删除未关联风险，并在重建矩阵时保留同一风险实体 | 当前风险只按 `risk` 文本 PATCH，重建时清空再创建，数据库 ID 不对前端可见 | 风险身份不稳定，无法可靠重命名或管理手工风险 | 把风险矩阵从文本聚合升级为可治理风险库，承接后续自动化和评审 | 中等，涉及后端同步、重建策略、前端表单 | 后端 service/API 测试、前端 service/page 测试、lint | 本轮 |
| B | P1 #7 Lisa 测试资产闭环 | 受控自动批量写入 intent-tester 或导入后自动触发执行 | 已有手动导入和执行链接 | 自动化仍需人工点击 | 端到端效率高，但有外部写入和执行副作用 | 高，需要幂等、防重复、执行确认和结果回写策略 | 跨系统 service/E2E 测试 | 下一轮候选 |

排序结论：

1. 选择 A，因为它补齐风险库身份与 CRUD，是当前资产中心内部治理能力；没有稳定风险 ID 时继续做自动写入会缺少可靠风险追踪。
2. B 暂不选，因为自动写入 / 自动执行会影响 intent-tester 数据和运行状态，应在风险库可治理后作为更大副作用切片推进。

切片准入判断：

- 用户可感知动作链：用户进入资产中心 -> 在风险矩阵新增手工风险或编辑现有风险名 / 状态 / 责任人 / 备注 -> 保存后测试点、当前用例风险和风险矩阵同步更新 -> 风险矩阵重建或刷新后同一风险 ID 保留 -> 对无关联手工风险可删除。
- 相邻缺口合并：本轮合并稳定 ID 序列化、风险矩阵 upsert 重建、新增风险、按 ID 重命名、删除未关联风险、前端 service、资产中心 UI 和测试证据。
- Superpowers 成本合理性：该能力跨模型、派生重建、API、前端状态和资产中心主体验，值得完整 CGA/spec/plan/TDD/验证。
- 过薄风险检查：不是只暴露一个 `id` 字段；完成后用户可以管理风险库实体并维持风险身份。
- 能力增量句：完成后，用户现在可以在 Lisa 测试资产中心管理稳定风险库，新增风险、重命名风险并删除未关联风险，而不会在矩阵重建后丢失风险身份。

切片厚度门禁：

- 入口：Lisa 测试资产中心的风险矩阵区域。
- 动作：用户新增手工风险、按稳定 ID 编辑风险名称 / lifecycle，或删除无关联风险。
- 处理：后端以 `AgentRiskMatrixAsset` 作为风险实体，upsert 同步派生矩阵，并在重命名时同步当前测试点和当前用例版本。
- 可见结果：风险矩阵展示稳定 ID、手工风险标记、更新后的风险名称 / lifecycle，以及删除后的列表状态。
- 状态承接：风险 ID、manual 标记、lifecycle 和当前用例版本写入数据库；后续矩阵重建和 collection 刷新继续保留同一风险实体。
- 失败反馈：重复风险名、非法状态、未知风险和删除有关联风险都返回显式错误；前端显示错误，不伪造成功。
- 证据：后端 service/API 测试覆盖稳定 ID、重建保留、新增、重命名、删除和拒绝有关联删除；前端 service/page 测试覆盖解析、调用和资产中心交互。
- 结论：通过。该切片交付完整风险库管理能力包，不是单字段、单 endpoint 或单按钮微切片。

本轮 milestone：

作为 Lisa 测试资产使用者，当风险矩阵需要人工治理时，我可以新增风险、重命名风险、维护 lifecycle，并删除未关联风险，从而把风险从派生文本升级为稳定资产。

## 设计

### 后端

`AgentRiskMatrixAsset.id` 作为稳定风险 ID 暴露给前端。新增字段：

- `is_manual`：用户手工创建的风险，默认 `False`。

风险矩阵同步从“清空后重建”改为 upsert：

- 对当前 artifact / 测试点派生出的风险，优先按风险名复用现有风险行，更新关联用例、测试点、优先级、维度和覆盖状态。
- 已存在但当前不再派生、且不是手工风险的风险行会被删除。
- 手工风险即使暂无关联，也会保留为空关联风险。
- 同名风险的 `id/status/owner/note/is_manual` 保留。

新增后端 service / route：

- `POST /api/agent/test-assets/{collectionId}/risks`：创建手工风险。只需要 `risk`，可选 `status/owner/note`。
- `PATCH /api/agent/test-assets/{collectionId}/risks/by-id/{riskId}`：按稳定 ID 更新 `risk/status/owner/note`。如果 `risk` 重命名，会同步更新当前测试点风险字段，并为当前风险匹配的测试用例追加新版本，保证后续风险矩阵重建不会把旧风险名带回来。
- `DELETE /api/agent/test-assets/{collectionId}/risks/by-id/{riskId}`：删除无关联风险。若风险仍关联测试用例或测试点，返回显式错误，要求先重命名或迁移关联。

保留现有按风险名 PATCH route 兼容已有前端/测试，但资产中心新交互改用按 ID route。

### 前端

`TestAssetRisk` 增加：

- `id: number`
- `isManual: boolean`

`testAssetService` 新增：

- `createTestAssetRisk(collectionId, patch)`
- `updateTestAssetRiskById(collectionId, riskId, patch)`
- `deleteTestAssetRisk(collectionId, riskId)`

资产中心风险矩阵区：

- 展示风险 ID 和“手工风险”标记。
- 新增“新增风险”表单，保存后把风险加入当前 collection。
- 编辑风险表单增加“风险名称”字段，保存后调用按 ID 更新，并重新读取 collection，确保用例、测试点和风险矩阵联动刷新。
- 无关联风险显示“删除风险”按钮；有关联风险删除失败时显示错误。

### 边界

本轮不做跨 collection 全局风险库，不做风险合并，不做批量迁移，不把删除有关联风险自动改写为空风险。风险 ID 只在单个测试资产 collection 内稳定。

## 验收条件

1. Given 已实体化风险矩阵，When 读取资产集合，Then 每个风险包含稳定 `id` 和 `isManual`。
2. Given 风险已有 `id`，When 测试点校准触发风险矩阵重建，Then 同名风险保留原 `id`。
3. Given 用户新增手工风险，When 保存成功，Then 风险矩阵出现该风险，关联用例和测试点为空，`isManual=true`。
4. Given 用户按 ID 重命名有关联风险，When 保存成功，Then 当前测试点和当前测试用例风险同步为新名称，风险矩阵保留同一 `id` 并展示新名称。
5. Given 用户删除无关联风险，When 删除成功，Then 风险从当前集合移除；有关联风险删除返回显式错误。

## 验证计划

- `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`
- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `git diff --check`
