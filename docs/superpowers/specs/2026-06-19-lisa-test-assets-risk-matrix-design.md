# Lisa Test Assets Risk Matrix Design

## Current State Gap Analysis

- P1 #7 要求 Lisa 从报告生成走向测试资产管理，其中包含风险矩阵。
- 当前 `test-assets` 导出已包含 `testCases`、`coverageTrace`、`coverageSummary` 和 `assetIssues`，但调用方还不能按风险聚合查看关联测试点、用例、维度和覆盖状态。
- 完整风险实体库、风险编辑和风险生命周期仍是后续较大切片。

## Chosen Design

在 `GET /api/agent/runs/{runId}/test-assets` 响应中新增派生字段 `riskMatrix`：

- `risk`: 风险 ID 或名称。
- `testCases`: 关联该风险的测试用例 ID 列表。
- `testPoints`: 关联该风险的测试点列表。
- `priorities`: 该风险关联的测试点/用例优先级集合。
- `dimensions`: 关联测试维度集合。
- `coverageStatuses`: 该风险关联测试点的覆盖状态集合。

风险矩阵从已解析的 `testCases` 和 `coverageTrace` 确定性计算。空风险、`-`、`无` 不进入矩阵。

## Requirements

- `riskMatrix` 必须稳定排序，便于测试和前端消费。
- 同一风险关联多个用例和测试点时应去重。
- endpoint 透传 `riskMatrix`。
- 不新增数据库风险表，不修改 intent-tester 主链路。

## Verification

- Service 测试覆盖风险矩阵输出。
- Endpoint 测试覆盖响应字段。
- 后端全量测试和 `git diff --check` 通过。
