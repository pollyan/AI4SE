# E04 Lisa 测试资产质量闭环 Implementation Plan

## Milestone

交付 Lisa 测试资产集合级质量状态闭环：后端派生质量摘要，前端资产中心展示摘要，并在处理 issue、测试点和风险后刷新状态。

## 预计提交边界

一个聚焦 commit：后端 `assetQuality` payload、前端解析与展示、测试、todo/spec/plan 记录。

## TDD 步骤

1. RED：后端测试。
   - 在 `tools/new-agents/backend/tests/test_test_assets.py` 中新增测试，断言 materialized collection 返回 `assetQuality.status === "needs_action"`、pending issue、uncovered point、open risk 和 next actions。
   - 新增测试，依次确认 issue、覆盖测试点、关闭风险后，重新读取 collection 的 `assetQuality.status === "ready"`。

2. RED：前端 service 测试。
   - 在 `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts` 的 collection fixture 中要求 `assetQuality`。
   - 新增测试断言缺失或 malformed `assetQuality` 会抛出 `Invalid test asset collection response`。

3. RED：前端页面测试。
   - 在 `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx` 新增测试，断言页面展示“资产质量状态”、`需处理`、pending issue、open risk、未覆盖测试点和下一步动作。
   - 新增测试，点击“确认问题”后会调用 issue API、重新 fetch collection，并展示刷新后的 `已就绪` 状态。

4. GREEN：后端最小实现。
   - 在 `test_assets.py` 中新增 `_build_asset_quality(...)` 纯函数。
   - `_serialize_collection` 追加 `assetQuality` 字段。
   - 不新增数据库字段或 API path。

5. GREEN：前端最小实现。
   - 在 `core/types.ts` 增加 `TestAssetQuality` 类型，并加入 `TestAssetCollection`。
   - 在 `testAssetService.ts` 增加严格解析。
   - 在 `TestAssetsPage.tsx` 增加资产质量状态面板。
   - issue 状态更新成功后重新 fetch collection，保证摘要刷新；测试点/风险保存流程已刷新 collection，保持该行为。

6. 验证与记录。
   - 运行后端聚焦 pytest。
   - 运行前端 service/page 聚焦 Vitest。
   - 运行 `npm run lint`。
   - 运行 `git diff --check`。
   - 更新 `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 和 `docs/todos/refactor/README.md`。
   - 提交本轮 milestone。
