# Lisa Test Assets Coverage Summary Design

## Current State Gap Analysis

- P1 #7 已经可以从 `TEST_DESIGN/CASES` artifact 导出结构化 `testCases` 和 `coverageTrace`。
- 现有导出结果能列出追溯行，但调用方还需要自行统计覆盖质量，无法快速判断测试点库是否闭环。
- 完整测试资产 CRUD、风险矩阵实体和 intent-tester 接力仍是后续较大切片。

## Chosen Design

在 `GET /api/agent/runs/{runId}/test-assets` 响应中新增 `coverageSummary`，由已解析的 `coverageTrace` 确定性计算：

- `totalTestCases`
- `totalTestPoints`
- `coveredTestPoints`
- `partiallyCoveredTestPoints`
- `uncoveredTestPoints`
- `coverageRate`
- `byPriority`

覆盖率只把 `覆盖状态 == "已覆盖"` 计为 covered，`部分覆盖` 单独统计，`未覆盖` 单独统计。`byPriority` 按覆盖追溯中的优先级分组。

## Requirements

- coverage summary 必须从当前 `coverageTrace` 和 `testCases` 计算。
- 无覆盖追溯行时返回 0 统计，不伪造覆盖率。
- endpoint 透传 `coverageSummary`。
- 不新增资产表、不修改 CASES artifact contract、不接入 intent-tester。

## Verification

- `test_test_assets.py` 覆盖总体和按优先级统计。
- endpoint 测试覆盖响应包含 summary。
- 后端聚焦与全量测试通过。
