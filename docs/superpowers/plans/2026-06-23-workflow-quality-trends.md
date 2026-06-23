# Workflow Quality Trends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 Header 运行统计中加入跨 run 工作流质量趋势，让用户能基于持久化 artifact 判断 workflow/stage 的产物质量分布、最差阶段和最近问题。

**Architecture:** 后端在现有 `/api/agent/observability` 响应中追加 `qualityTrend`，从 `AgentRun`、`AgentArtifact` 当前版本和 workflow contract 派生 deterministic 质量摘要。前端严格解析该字段，并在现有 Header 运行统计 modal 中展示趋势、空态和最近问题，不新增 agent 专属 runtime、API、store 或 renderer。

**Tech Stack:** Flask + SQLAlchemy + Pytest；React 19 + TypeScript + Vitest；New Agents shared workflow manifest、run persistence、observability endpoint。

---

## File Map

- Modify: `tools/new-agents/backend/run_persistence.py`
  - 增加 `qualityTrend` 聚合 helper。
  - 在 `get_runtime_observability_summary()` 返回值中追加 `qualityTrend`。
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
  - 增加 quality trend 聚合与过滤测试。
- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - 增加 observability quality trend 类型。
- Modify: `tools/new-agents/frontend/src/services/observabilityService.ts`
  - 严格解析 `qualityTrend`。
- Modify: `tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts`
  - 覆盖合法解析与 malformed payload。
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
  - 在运行统计 modal 中展示跨 run 质量趋势。
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
  - 覆盖趋势展示和空态。
- Modify: `docs/todos/refactor/README.md`
  - 记录本轮 E08 跨 run 趋势消化结果。
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - 更新 E08 状态和 Goal Mode 消化记录。

## Commit Boundary

本轮预计一个聚焦 commit：`feat(new-agents): 增加跨 run 工作流质量趋势`。如果实现过程中发现前后端改动超过约 800 行或触达 8 个以上源文件，再评估拆出文档/测试 checkpoint；当前计划保持一个原子能力闭环。

### Task 1: Backend RED Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [ ] **Step 1: Add failing aggregation test**

在 `test_agent_observability_endpoint_groups_formatted_output_diagnostics` 前后新增：

```python
def test_agent_observability_endpoint_returns_quality_trend_from_persisted_artifacts(
    app,
    client,
):
    ready_artifact = "\n".join([
        "# 测试策略蓝图",
        "## 1. 策略摘要",
        "## 2. 质量目标",
        "## 3. 风险识别与 FMEA",
        "## 4. 测试技术选型",
        "## 5. 测试分层策略",
        "## 6. 测试点拓扑",
        "## 7. 资源与取舍",
        "## 8. 阶段门禁",
        "```mermaid",
        "quadrantChart",
        "```",
        "```mermaid",
        "block-beta",
        "```",
        "```ai4se-visual",
        '{"type":"risk-board","title":"风险板","columns":[]}',
        "```",
    ])
    blocked_artifact = "# 测试策略蓝图\n\n## 1. 策略摘要\n\n阻断: 缺少风险矩阵。"

    with app.app_context():
        ready_run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(ready_run.id, "STRATEGY", ready_artifact)
        blocked_run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(blocked_run.id, "STRATEGY", blocked_artifact)
        empty_run = create_agent_run("TEST_DESIGN", "lisa", "CASES")

    response = client.get("/api/agent/observability?workflowId=TEST_DESIGN")

    assert response.status_code == 200
    trend = response.json["qualityTrend"]
    assert trend["totalRuns"] == 3
    assert trend["artifactRuns"] == 2
    assert trend["averageScore"] < 100
    assert trend["statusCounts"]["ready"] == 1
    assert trend["statusCounts"]["blocked"] >= 1
    assert trend["statusCounts"]["notStarted"] >= 1
    assert trend["worstStage"]["workflowId"] == "TEST_DESIGN"
    assert trend["worstStage"]["stageId"] in {"STRATEGY", "CASES"}
    strategy = next(item for item in trend["byStage"] if item["stageId"] == "STRATEGY")
    assert strategy["runCount"] == 2
    assert strategy["artifactCount"] == 2
    assert strategy["statusCounts"]["ready"] == 1
    assert any(item["title"] == "缺少必填标题" for item in strategy["topPending"])
    assert any(issue["runId"] == blocked_run.id for issue in trend["recentIssues"])
```

- [ ] **Step 2: Add failing filter test**

继续新增：

```python
def test_agent_observability_endpoint_filters_quality_trend_by_workflow_and_stage(
    app,
    client,
):
    clarify_artifact = "# 需求分析文档\n\n## 8. 阶段门禁\n\n阻断: 缺少背景。"
    blueprint_artifact = "# 需求蓝图\n\n## 1. 目标与范围\n\n## 阶段门禁"

    with app.app_context():
        clarify_run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        record_artifact_version(clarify_run.id, "CLARIFY", clarify_artifact)
        strategy_run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(strategy_run.id, "STRATEGY", "# 测试策略蓝图")
        value_run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(value_run.id, "BLUEPRINT", blueprint_artifact)

    response = client.get(
        "/api/agent/observability?workflowId=TEST_DESIGN&stageId=CLARIFY"
    )

    assert response.status_code == 200
    trend = response.json["qualityTrend"]
    assert trend["totalRuns"] == 1
    assert trend["artifactRuns"] == 1
    assert [item["stageId"] for item in trend["byStage"]] == ["CLARIFY"]
    assert all(issue["stageId"] == "CLARIFY" for issue in trend["recentIssues"])
```

- [ ] **Step 3: Run RED backend tests**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_quality_trend_from_persisted_artifacts tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_filters_quality_trend_by_workflow_and_stage -q
```

Expected: fail with `KeyError: 'qualityTrend'` or equivalent missing field.

### Task 2: Backend GREEN Implementation

**Files:**
- Modify: `tools/new-agents/backend/run_persistence.py`

- [ ] **Step 1: Import manifest contract access**

Add imports near the existing `agent_contracts` import:

```python
from workflow_contract_registry import get_workflow_contract
```

- [ ] **Step 2: Add status constants and text detectors**

Add near `FORMAT_FAILURE_KIND_METADATA`:

```python
QUALITY_STATUSES = {
    "ready",
    "attention",
    "blocked",
    "notStarted",
    "insufficientEvidence",
}
QUALITY_BLOCKER_TERMS = ("阻断", "缺少", "失败")
QUALITY_ATTENTION_TERMS = ("待确认", "未确认", "开放问题", "缺失信息", "需要补充")
```

- [ ] **Step 3: Add quality scoring helpers**

Add helper functions before `get_runtime_observability_summary()`:

```python
def _empty_quality_status_counts() -> dict:
    return {
        "ready": 0,
        "attention": 0,
        "blocked": 0,
        "notStarted": 0,
        "insufficientEvidence": 0,
    }


def _quality_pending_item(title: str, detail: str, severity: str, action: str) -> dict:
    return {
        "title": title,
        "detail": detail,
        "severity": severity,
        "action": action,
    }


def _score_artifact_quality(workflow_id: str, stage_id: str, content: str) -> dict:
    if not content.strip():
        return {
            "score": 0,
            "status": "notStarted",
            "pending": [
                _quality_pending_item(
                    "暂无可评估 artifact",
                    "该 run 当前阶段还没有持久化 artifact。",
                    "not-started",
                    "先生成并保存该阶段产物。",
                )
            ],
        }

    pending = []
    score = 100
    contract = get_workflow_contract(workflow_id).stages.get(stage_id)
    if contract is None:
        return {
            "score": 0,
            "status": "insufficientEvidence",
            "pending": [
                _quality_pending_item(
                    "缺少阶段质量契约",
                    f"{workflow_id}/{stage_id} 没有可用于趋势计算的 contract。",
                    "attention",
                    "补齐 workflow contract 后再纳入质量趋势。",
                )
            ],
        }

    for heading in contract.required_headings:
        if heading not in content:
            score -= 20
            pending.append(_quality_pending_item(
                "缺少必填标题",
                f"缺少 {heading}",
                "blocker",
                "补齐 artifact contract 要求的标题。",
            ))

    for diagram in contract.required_mermaid_diagrams:
        if diagram not in content:
            score -= 20
            pending.append(_quality_pending_item(
                "缺少 Mermaid 图表",
                f"缺少 {diagram} Mermaid 图表。",
                "blocker",
                "补齐当前阶段要求的 Mermaid 可视化。",
            ))

    for visual_type in contract.required_structured_visuals:
        if f'"type":"{visual_type}"' not in content and f'"type": "{visual_type}"' not in content:
            score -= 20
            pending.append(_quality_pending_item(
                "缺少结构化可视化",
                f"缺少 {visual_type} ai4se-visual。",
                "blocker",
                "补齐当前阶段要求的结构化可视化。",
            ))

    if "阶段门禁" not in content:
        score -= 16
        pending.append(_quality_pending_item(
            "缺少阶段门禁",
            "artifact 没有阶段门禁或交付检查段落。",
            "blocker",
            "补齐阶段门禁和下一步检查项。",
        ))

    if any(term in content for term in QUALITY_ATTENTION_TERMS):
        score -= 8
        pending.append(_quality_pending_item(
            "存在未关闭问题",
            "artifact 中仍包含待确认、开放问题或缺失信息。",
            "attention",
            "关闭待确认项或记录风险接受条件。",
        ))
    if any(term in content for term in QUALITY_BLOCKER_TERMS):
        score -= 8

    score = max(0, min(100, score))
    severities = {item["severity"] for item in pending}
    status = "blocked" if "blocker" in severities else "attention" if pending else "ready"
    return {
        "score": score,
        "status": status,
        "pending": pending,
    }
```

- [ ] **Step 4: Add aggregation helper**

Add:

```python
def _quality_trend_summary(
    *,
    limit: int,
    workflow_id: str | None,
    stage_id: str | None,
) -> dict:
    run_query = AgentRun.query
    if workflow_id is not None:
        run_query = run_query.filter(AgentRun.workflow_id == workflow_id)
    runs = run_query.order_by(AgentRun.created_at.desc(), AgentRun.id.desc()).all()

    status_counts = _empty_quality_status_counts()
    stage_index: dict[tuple[str, str], dict] = {}
    recent_issues = []
    score_total = 0
    scored_count = 0
    artifact_runs = 0

    for run in runs:
        stage_ids = [stage_id] if stage_id is not None else list(WORKFLOW_STAGES[run.workflow_id])
        for current_stage_id in stage_ids:
            artifact = AgentArtifact.query.filter_by(
                run_id=run.id,
                stage_id=current_stage_id,
            ).first()
            content = ""
            created_at = run.created_at.isoformat() if run.created_at else None
            if artifact is not None and artifact.current_version_id is not None:
                snapshot = _artifact_snapshot(artifact)
                content = snapshot["content"]
                artifact_runs += 1
                created_at = snapshot.get("updatedAt") or created_at
            quality = _score_artifact_quality(run.workflow_id, current_stage_id, content)
            status_counts[quality["status"]] += 1
            score_total += quality["score"]
            scored_count += 1

            key = (run.workflow_id, current_stage_id)
            stage_item = stage_index.setdefault(key, {
                "workflowId": run.workflow_id,
                "stageId": current_stage_id,
                "runCount": 0,
                "artifactCount": 0,
                "scoreTotal": 0,
                "statusCounts": _empty_quality_status_counts(),
                "pendingIndex": {},
            })
            stage_item["runCount"] += 1
            stage_item["artifactCount"] += 1 if content.strip() else 0
            stage_item["scoreTotal"] += quality["score"]
            stage_item["statusCounts"][quality["status"]] += 1
            for pending in quality["pending"]:
                pending_key = (pending["title"], pending["severity"], pending["action"])
                pending_item = stage_item["pendingIndex"].setdefault(pending_key, {
                    "title": pending["title"],
                    "count": 0,
                    "severity": pending["severity"],
                    "action": pending["action"],
                })
                pending_item["count"] += 1
                if len(recent_issues) < limit:
                    recent_issues.append({
                        "runId": run.id,
                        "workflowId": run.workflow_id,
                        "stageId": current_stage_id,
                        "score": quality["score"],
                        "status": quality["status"],
                        "title": pending["title"],
                        "detail": pending["detail"],
                        "action": pending["action"],
                        "createdAt": created_at,
                    })

    by_stage = []
    for item in stage_index.values():
        run_count = item["runCount"]
        top_pending = sorted(
            item["pendingIndex"].values(),
            key=lambda pending: (-pending["count"], pending["title"]),
        )[:3]
        by_stage.append({
            "workflowId": item["workflowId"],
            "stageId": item["stageId"],
            "runCount": run_count,
            "artifactCount": item["artifactCount"],
            "averageScore": round(item["scoreTotal"] / run_count) if run_count else 0,
            "statusCounts": item["statusCounts"],
            "topPending": top_pending,
        })
    by_stage.sort(key=lambda item: (item["averageScore"], item["workflowId"], item["stageId"]))

    worst_stage = None
    if by_stage:
        worst = by_stage[0]
        worst_stage = {
            "workflowId": worst["workflowId"],
            "stageId": worst["stageId"],
            "averageScore": worst["averageScore"],
            "status": _dominant_quality_status(worst["statusCounts"]),
            "pendingCount": sum(item["count"] for item in worst["topPending"]),
            "runCount": worst["runCount"],
            "action": (
                worst["topPending"][0]["action"]
                if worst["topPending"]
                else "当前阶段质量趋势稳定，可继续观察。"
            ),
        }

    return {
        "totalRuns": len(runs),
        "artifactRuns": artifact_runs,
        "averageScore": round(score_total / scored_count) if scored_count else 0,
        "statusCounts": status_counts,
        "worstStage": worst_stage,
        "byStage": by_stage,
        "recentIssues": recent_issues,
    }
```

Also add:

```python
def _dominant_quality_status(status_counts: dict) -> str:
    priority = ["blocked", "attention", "notStarted", "insufficientEvidence", "ready"]
    return max(priority, key=lambda status: (status_counts.get(status, 0), -priority.index(status)))
```

- [ ] **Step 5: Add response field**

Inside `get_runtime_observability_summary()` return dict, add:

```python
"qualityTrend": _quality_trend_summary(
    limit=limit,
    workflow_id=workflow_id,
    stage_id=stage_id,
),
```

- [ ] **Step 6: Run backend GREEN tests**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_quality_trend_from_persisted_artifacts tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_filters_quality_trend_by_workflow_and_stage -q
```

Expected: both pass.

### Task 3: Frontend RED Tests

**Files:**
- Modify: `tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [ ] **Step 1: Extend service fixture and assertions**

Add `qualityTrend` to `OBSERVABILITY_PAYLOAD`:

```typescript
qualityTrend: {
    totalRuns: 3,
    artifactRuns: 2,
    averageScore: 72,
    statusCounts: {
        ready: 1,
        attention: 1,
        blocked: 1,
        notStarted: 0,
        insufficientEvidence: 0,
    },
    worstStage: {
        workflowId: 'TEST_DESIGN',
        stageId: 'STRATEGY',
        averageScore: 44,
        status: 'blocked',
        pendingCount: 2,
        runCount: 2,
        action: '补齐 artifact contract 要求的标题。',
    },
    byStage: [
        {
            workflowId: 'TEST_DESIGN',
            stageId: 'STRATEGY',
            runCount: 2,
            artifactCount: 2,
            averageScore: 44,
            statusCounts: {
                ready: 1,
                attention: 0,
                blocked: 1,
                notStarted: 0,
                insufficientEvidence: 0,
            },
            topPending: [
                {
                    title: '缺少必填标题',
                    count: 1,
                    severity: 'blocker',
                    action: '补齐 artifact contract 要求的标题。',
                },
            ],
        },
    ],
    recentIssues: [
        {
            runId: 'run-quality-1',
            workflowId: 'TEST_DESIGN',
            stageId: 'STRATEGY',
            score: 44,
            status: 'blocked',
            title: '缺少必填标题',
            detail: '缺少 ## 2. 质量目标',
            action: '补齐 artifact contract 要求的标题。',
            createdAt: '2026-06-23T09:00:00',
        },
    ],
},
```

Assert in first test:

```typescript
expect(summary.qualityTrend.averageScore).toBe(72);
expect(summary.qualityTrend.worstStage?.stageId).toBe('STRATEGY');
expect(summary.qualityTrend.recentIssues[0].runId).toBe('run-quality-1');
```

- [ ] **Step 2: Add malformed test**

Add:

```typescript
it('fails explicitly when quality trend is malformed', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(
        JSON.stringify({
            ...OBSERVABILITY_PAYLOAD,
            qualityTrend: {
                ...OBSERVABILITY_PAYLOAD.qualityTrend,
                averageScore: '72',
            },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
    ));

    await expect(fetchObservabilitySummary({ limit: 20 })).rejects.toThrow(
        'Invalid observability summary response'
    );
});
```

- [ ] **Step 3: Add Header display assertions**

In Header observability fixture, include the same `qualityTrend`. In `opens runtime observability summary`, add:

```typescript
expect(screen.getByText('跨 run 质量趋势')).toBeTruthy();
expect(screen.getByText('平均质量分 72')).toBeTruthy();
expect(screen.getByText('最差阶段 TEST_DESIGN / STRATEGY')).toBeTruthy();
expect(screen.getByText('run-quality-1 · TEST_DESIGN/STRATEGY')).toBeTruthy();
```

Add empty-state test by mocking `fetchObservabilitySummary` with `qualityTrend.totalRuns = 0` and arrays empty:

```typescript
it('shows an empty state when quality trend has no evidence', async () => {
    vi.mocked(fetchObservabilitySummary).mockResolvedValue({
        ...OBSERVABILITY_SUMMARY,
        qualityTrend: {
            totalRuns: 0,
            artifactRuns: 0,
            averageScore: 0,
            statusCounts: {
                ready: 0,
                attention: 0,
                blocked: 0,
                notStarted: 0,
                insufficientEvidence: 0,
            },
            worstStage: null,
            byStage: [],
            recentIssues: [],
        },
    });

    renderHeader();
    clickMoreAction(/运行统计/);

    expect(await screen.findByText('当前筛选范围暂无质量趋势证据')).toBeTruthy();
});
```

- [ ] **Step 4: Run RED frontend tests**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/tools/new-agents/frontend/node_modules/.bin/vitest run src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx
```

Expected: fail because production types/parser/UI do not expose `qualityTrend`.

### Task 4: Frontend GREEN Implementation

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/observabilityService.ts`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`

- [ ] **Step 1: Add TypeScript types**

Add observability quality trend interfaces in `core/types.ts` next to existing observability types:

```typescript
export type ObservabilityQualityStatus =
    'ready' | 'attention' | 'blocked' | 'notStarted' | 'insufficientEvidence';

export interface ObservabilityQualityStatusCounts {
    ready: number;
    attention: number;
    blocked: number;
    notStarted: number;
    insufficientEvidence: number;
}

export interface ObservabilityQualityPending {
    title: string;
    count: number;
    severity: string;
    action: string;
}

export interface ObservabilityQualityStage {
    workflowId: WorkflowType;
    stageId: string;
    runCount: number;
    artifactCount: number;
    averageScore: number;
    statusCounts: ObservabilityQualityStatusCounts;
    topPending: ObservabilityQualityPending[];
}

export interface ObservabilityQualityWorstStage {
    workflowId: WorkflowType;
    stageId: string;
    averageScore: number;
    status: ObservabilityQualityStatus;
    pendingCount: number;
    runCount: number;
    action: string;
}

export interface ObservabilityQualityRecentIssue {
    runId: string;
    workflowId: WorkflowType;
    stageId: string;
    score: number;
    status: ObservabilityQualityStatus;
    title: string;
    detail: string;
    action: string;
    createdAt: string | null;
}

export interface ObservabilityQualityTrend {
    totalRuns: number;
    artifactRuns: number;
    averageScore: number;
    statusCounts: ObservabilityQualityStatusCounts;
    worstStage: ObservabilityQualityWorstStage | null;
    byStage: ObservabilityQualityStage[];
    recentIssues: ObservabilityQualityRecentIssue[];
}
```

Add `qualityTrend: ObservabilityQualityTrend;` to `ObservabilitySummary`.

- [ ] **Step 2: Parse quality trend**

In `observabilityService.ts`, import the new types and add parser helpers:

```typescript
const parseQualityStatus = (value: unknown): ObservabilityQualityStatus => {
    if (
        value === 'ready'
        || value === 'attention'
        || value === 'blocked'
        || value === 'notStarted'
        || value === 'insufficientEvidence'
    ) {
        return value;
    }
    throw new Error(INVALID_OBSERVABILITY_ERROR);
};

const parseQualityStatusCounts = (value: unknown): ObservabilityQualityStatusCounts => {
    if (!isRecord(value)) throw new Error(INVALID_OBSERVABILITY_ERROR);
    return {
        ready: parseInteger(value.ready),
        attention: parseInteger(value.attention),
        blocked: parseInteger(value.blocked),
        notStarted: parseInteger(value.notStarted),
        insufficientEvidence: parseInteger(value.insufficientEvidence),
    };
};
```

Add parsers for pending/stage/worst/recent/trend and include `qualityTrend: parseQualityTrend(payload.qualityTrend)` in `parseSummary()`.

- [ ] **Step 3: Render quality trend section**

In `Header.tsx`, inside the observability modal before base metric cards, add a section:

```tsx
<section className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
  <div className="flex flex-wrap items-start justify-between gap-3">
    <div>
      <h4 className="text-sm font-semibold text-white">跨 run 质量趋势</h4>
      <div className="mt-2 text-xl font-bold text-white">
        平均质量分 {observabilitySummary.qualityTrend.averageScore}
      </div>
      <div className="mt-1 text-xs text-slate-500">
        {observabilitySummary.qualityTrend.artifactRuns} 个 artifact run / {observabilitySummary.qualityTrend.totalRuns} 个 run
      </div>
    </div>
    <div className="flex flex-wrap gap-2 text-xs">
      <span className="rounded bg-emerald-500/10 px-2 py-1 font-semibold text-emerald-200">
        ready {observabilitySummary.qualityTrend.statusCounts.ready}
      </span>
      <span className="rounded bg-amber-500/10 px-2 py-1 font-semibold text-amber-200">
        attention {observabilitySummary.qualityTrend.statusCounts.attention}
      </span>
      <span className="rounded bg-red-500/10 px-2 py-1 font-semibold text-red-200">
        blocked {observabilitySummary.qualityTrend.statusCounts.blocked}
      </span>
    </div>
  </div>
  {observabilitySummary.qualityTrend.totalRuns === 0 ? (
    <div className="mt-3 rounded-lg bg-[#111827] p-3 text-sm text-slate-500">
      当前筛选范围暂无质量趋势证据
    </div>
  ) : (
    <div className="mt-4 grid gap-3 lg:grid-cols-2">
      ...
    </div>
  )}
</section>
```

Fill the body with worst stage, stage rows and recent issues using existing visual style.

- [ ] **Step 4: Run frontend GREEN tests**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/tools/new-agents/frontend/node_modules/.bin/vitest run src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx
```

Expected: pass.

### Task 5: Docs and Verification

**Files:**
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

- [ ] **Step 1: Update todo records**

Record:

- E08 跨 run 质量趋势已完成 deterministic 本地闭环。
- E08 仍保留 LLM judge evidence 为后续候选。
- 下一批候选为 DeepSeek real smoke、E12 scaffold/codegen、prompt/template version、LLM judge。

- [ ] **Step 2: Run full focused verification**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_groups_formatted_output_diagnostics tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_quality_trend_from_persisted_artifacts tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_filters_quality_trend_by_workflow_and_stage -q
```

Expected: pass.

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/tools/new-agents/frontend/node_modules/.bin/vitest run src/core/__tests__/workflowQuality.test.ts src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx
```

Expected: pass.

- [ ] **Step 3: Inspect diff and commit**

Run:

```bash
git status --short
git diff --stat
git diff --check
```

Then stage only this milestone’s files and commit:

```bash
git add docs/superpowers/specs/2026-06-23-workflow-quality-trends-design.md docs/superpowers/plans/2026-06-23-workflow-quality-trends.md docs/todos/refactor/README.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md tools/new-agents/backend/run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/services/observabilityService.ts tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts tools/new-agents/frontend/src/components/Header.tsx tools/new-agents/frontend/src/components/__tests__/Header.test.tsx
git commit -m "feat(new-agents): 增加跨 run 工作流质量趋势"
```

Expected: commit succeeds on branch `codex/workflow-quality-trends`.

## Self Review

- Spec coverage: plan covers backend aggregation, frontend parser, Header UI, tests, docs, verification, commit.
- Placeholder scan: no TBD/TODO placeholders; all commands and paths are concrete.
- Type consistency: backend uses `qualityTrend`; frontend types and parser use matching `qualityTrend`, `statusCounts`, `worstStage`, `byStage`, `recentIssues` names.
