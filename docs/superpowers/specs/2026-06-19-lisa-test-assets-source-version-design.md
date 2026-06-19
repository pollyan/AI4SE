# Lisa Test Assets Source Version Design

## Current State Gap Analysis

- P1 #7 已具备从 `TEST_DESIGN/CASES` artifact 导出 `testCases` 和 `coverageTrace` 的基础能力。
- `agent_artifact_versions` 已记录每个 artifact version，snapshot 的 current artifact 已包含 `versionNumber`。
- 当前 `GET /api/agent/runs/{runId}/test-assets` 没有暴露导出资产来自哪个 artifact version，后续无法审计“这批用例对应哪版测试用例集”。

## Chosen Design

在测试资产导出响应中新增 `sourceArtifactVersion`，直接使用 CASES current artifact 的 `versionNumber`。同一 run/stage 多次写入 CASES artifact 后，导出结果应反映最新 current version。

## Requirements

- `export_lisa_test_assets` 返回 `sourceArtifactVersion`。
- endpoint 透传该字段。
- 多次记录 CASES artifact version 后，导出字段必须等于最新 version number。
- 不新增版本选择参数，不新增 UI，不改变 artifact version 存储模型。

## Verification

- `test_test_assets.py` 覆盖 source version 字段和更新后最新 version。
- endpoint 测试覆盖响应字段。
- 后端聚焦与全量测试通过。
