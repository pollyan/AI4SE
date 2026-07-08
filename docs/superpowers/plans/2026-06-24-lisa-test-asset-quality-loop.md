# Lisa 测试资产质量闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Lisa 测试资产集合拥有统一 `qualitySummary`，并让 issue、测试点覆盖、风险生命周期三类质量动作共同驱动 Header 与资产中心中的可交付状态。

**Architecture:** 后端 `test_assets.py` 在现有 collection 序列化中计算权威 `qualitySummary`；前端 `testAssetService.ts` 严格解析该 contract；`testAssetQuality.ts` 复用同规则支持本地 issue 更新后重算；`TestAssetsPage` 和 `Header` 只展示和调用现有资产 API，不新增 runtime、SSE、workflow manifest 或 renderer。

**Tech Stack:** Python 3.11、Flask/SQLAlchemy、pytest、React 19、TypeScript、Vitest、Testing Library。

---

## 当前执行状态

本轮在隔离 worktree `/Users/anhui/Documents/myProgram/AI4SE/.worktrees/lisa-test-asset-quality-loop-goal-mainline` 中执行，分支 `codex/lisa-test-asset-quality-loop-goal-mainline`，基线为上一轮已验证 Artifact 诊断 commit `e4c205e3`。主工作区存在 intent-tester zip、`docs/plans/tech-debt.md` 和两个 todo 文件的既有未提交改动，本轮不在主工作区写入。

已有堆叠分支 `codex/lisa-test-asset-quality-loop-after-diagnostics` 的最后一个 commit `a4231d99` 可作为 Lisa 相关实现参考，但不能直接作为本轮结果，因为该分支还包含 Alex、DeepSeek 和 Artifact 等多个前置能力包。本轮只允许形成 Lisa 测试资产质量闭环的聚焦 commit。

## 验证结果

- `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_test_assets.py -q`: 30 passed。
- `npm run test -- --run src/services/__tests__/testAssetService.test.ts src/core/__tests__/testAssetQuality.test.ts src/pages/__tests__/TestAssetsPage.test.tsx src/components/__tests__/Header.test.tsx`: 4 个测试文件通过，66 个测试通过。
- `npm run lint`: 通过，`tsc --noEmit` 无错误。
- `git diff --check`: 通过，无空白错误。

## Task 1: 后端 `qualitySummary` contract

**Files:**
- Modify: `tools/new-agents/backend/test_assets.py`
- Modify: `tools/new-agents/backend/tests/test_test_assets.py`

- [x] **Step 1: 写后端 RED 测试**

在 `test_test_assets.py` 中新增或扩展测试：

```python
def test_materialized_lisa_test_assets_include_quality_summary(app):
    with app.app_context():
        run_id = seed_test_design_run_with_cases_artifact()
        collection = materialize_lisa_test_assets(run_id)

    assert collection["qualitySummary"] == {
        "status": "blocked",
        "label": "存在阻断",
        "pendingIssueCount": 2,
        "confirmedIssueCount": 0,
        "ignoredIssueCount": 0,
        "uncoveredTestPointCount": 1,
        "partialTestPointCount": 0,
        "openRiskCount": 2,
        "mitigatingRiskCount": 0,
        "acceptedRiskCount": 0,
        "closedRiskCount": 0,
        "gates": [
            {
                "id": "asset-issues",
                "status": "blocked",
                "title": "资产问题",
                "detail": "2 个待处理问题需要确认或忽略。",
            },
            {
                "id": "test-point-coverage",
                "status": "blocked",
                "title": "测试点覆盖",
                "detail": "1 个测试点未覆盖，0 个测试点部分覆盖。",
            },
            {
                "id": "risk-lifecycle",
                "status": "attention",
                "title": "风险处置",
                "detail": "2 个风险待处置，0 个风险缓解中。",
            },
        ],
    }
```

再补一个状态变化测试：确认/忽略所有 issue、把测试点改为 `已覆盖`、把风险改为 `accepted` 或 `closed` 后，重新读取 collection，`qualitySummary.status` 变为 `ready`。

- [x] **Step 2: 运行后端 RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_test_assets.py -q
```

Expected: FAIL，原因是 collection 尚未包含 `qualitySummary`。

- [x] **Step 3: 实现后端 summary**

在 `test_assets.py` 中新增 `_build_quality_summary(issues, test_points, risk_matrix)`，统计 issue/test point/risk 状态并返回稳定 dict。在 `_serialize_collection()` 中追加 `"qualitySummary": _build_quality_summary(...)`。

- [x] **Step 4: 运行后端 GREEN**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_test_assets.py -q
```

Expected: PASS。

## Task 2: 前端 service 严格解析

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/testAssetService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`

- [x] **Step 1: 写 service RED 测试**

在有效 collection fixture 中加入 `qualitySummary`，断言解析后的 status/gates 可访问；新增缺失 `qualitySummary` 和非法 gate status 的测试，期望抛出 `Invalid test asset collection response`。

- [x] **Step 2: 运行 service RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts
```

Expected: FAIL，原因是 type/parser 尚未识别 `qualitySummary`。

- [x] **Step 3: 实现类型和 parser**

在 `types.ts` 增加：

```ts
export type TestAssetQualityStatus = 'blocked' | 'attention' | 'ready';
export type TestAssetQualityGateStatus = 'blocked' | 'attention' | 'pass';
export type TestAssetQualityGate = {
    id: string;
    status: TestAssetQualityGateStatus;
    title: string;
    detail: string;
};
export type TestAssetQualitySummary = {
    status: TestAssetQualityStatus;
    label: string;
    pendingIssueCount: number;
    confirmedIssueCount: number;
    ignoredIssueCount: number;
    uncoveredTestPointCount: number;
    partialTestPointCount: number;
    openRiskCount: number;
    mitigatingRiskCount: number;
    acceptedRiskCount: number;
    closedRiskCount: number;
    gates: TestAssetQualityGate[];
};
```

在 `testAssetService.ts` 中新增 `parseQualitySummary()`，并让 `parseCollection()` 必须解析 `qualitySummary`。

- [x] **Step 4: 运行 service GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts
```

Expected: PASS。

## Task 3: 前端本地质量重算 helper

**Files:**
- Create: `tools/new-agents/frontend/src/core/testAssetQuality.ts`
- Create: `tools/new-agents/frontend/src/core/__tests__/testAssetQuality.test.ts`
- Modify: `tools/new-agents/frontend/src/core/types.ts`

- [x] **Step 1: 写 helper RED 测试**

覆盖三类输入：

- 有 pending issue 或 `未覆盖` 测试点时返回 `blocked`。
- 只有 confirmed issue、`部分覆盖` 或 open/mitigating 风险时返回 `attention`。
- issue 均 ignored、测试点均 `已覆盖`、风险 accepted/closed 时返回 `ready`。

- [x] **Step 2: 运行 helper RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/testAssetQuality.test.ts
```

Expected: FAIL，原因是 `testAssetQuality.ts` 不存在。

- [x] **Step 3: 实现 helper**

新增 `buildTestAssetQualitySummary(collection)` 和 `withTestAssetQualitySummary(collection)`，规则与后端一致。helper 不访问 React、store 或网络。

- [x] **Step 4: 运行 helper GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/testAssetQuality.test.ts
```

Expected: PASS。

## Task 4: 资产中心质量闭环 UI

**Files:**
- Modify: `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`
- Modify: `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`

- [x] **Step 1: 写资产中心 RED 测试**

新增测试覆盖：

- 页面顶部显示 `存在阻断`、资产问题 gate、测试点覆盖 gate 和风险处置 gate。
- 调用 `updateTestAssetIssueStatus()` 后本地 collection 更新并重算 summary。
- 保存测试点覆盖和风险状态后，页面显示新的 quality summary。

- [x] **Step 2: 运行资产中心 RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx -t "质量"
```

Expected: FAIL，原因是页面尚未渲染 quality summary。

- [x] **Step 3: 实现资产中心展示**

在资产统计卡前增加质量状态面板，展示 `qualitySummary.label`、gate 列表和关键计数。issue 状态更新后使用 `withTestAssetQualitySummary()` 重算 collection；测试点和风险沿用现有更新/刷新逻辑并保持 summary 一致。

- [x] **Step 4: 运行资产中心 GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx
```

Expected: PASS。

## Task 5: Header 快捷面板质量状态

**Files:**
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [x] **Step 1: 写 Header RED 测试**

更新 Header 测试 fixture，包含 `qualitySummary`；新增断言测试资产快捷面板显示 `存在阻断` / `需要关注` / `可交付` 和 gate 摘要。

- [x] **Step 2: 运行 Header RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx -t "质量状态"
```

Expected: FAIL，原因是 Header 尚未展示 summary。

- [x] **Step 3: 实现 Header 展示**

在已有测试资产 modal 中增加紧凑质量 panel，展示状态 label、gate 数量和 gate 详情；不加入完整编辑操作，避免复制资产中心。

- [x] **Step 4: 运行 Header GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx
```

Expected: PASS。

## Task 6: 文档记录、CI 等价验证和提交

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/superpowers/specs/2026-06-24-lisa-test-asset-quality-loop-design.md`
- Modify: `docs/superpowers/plans/2026-06-24-lisa-test-asset-quality-loop.md`

- [x] **Step 1: 更新 todo**

将 E04 记录为已消化，说明本轮完成的是 Lisa 测试资产质量 summary/gate/状态更新闭环；明确不纳入 intent-tester 自动执行、handoff 上下文强化、跨 run 趋势或真实模型 smoke。

- [x] **Step 2: 运行 CI 等价验证**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_test_assets.py -q
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/core/__tests__/testAssetQuality.test.ts src/pages/__tests__/TestAssetsPage.test.tsx src/components/__tests__/Header.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: 全部 PASS。

- [x] **Step 3: 提交**

Run:

```bash
git status -sb
git add docs/superpowers/specs/2026-06-24-lisa-test-asset-quality-loop-design.md docs/superpowers/plans/2026-06-24-lisa-test-asset-quality-loop.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md tools/new-agents/backend/test_assets.py tools/new-agents/backend/tests/test_test_assets.py tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/testAssetQuality.ts tools/new-agents/frontend/src/core/__tests__/testAssetQuality.test.ts tools/new-agents/frontend/src/services/testAssetService.ts tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts tools/new-agents/frontend/src/pages/TestAssetsPage.tsx tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx tools/new-agents/frontend/src/components/Header.tsx tools/new-agents/frontend/src/components/__tests__/Header.test.tsx
git commit -m "feat(new-agents): 补齐 Lisa 测试资产质量闭环"
```

Expected: commit 只包含 Lisa 测试资产质量闭环相关文件。
