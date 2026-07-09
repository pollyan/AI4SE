# INCIDENT_REVIEW/TIMELINE timeline-map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `INCIDENT_REVIEW/TIMELINE` from Mermaid `timeline` to deterministic `ai4se-visual timeline-map` across backend renderer, visual contracts, frontend preview, export, prompts, tests, and docs.

**Architecture:** The model still outputs only `artifact_data`; backend deterministic renderer generates Markdown plus fenced `ai4se-visual` JSON. `timeline-map` becomes a shared structured visual type consumed by the existing `StructuredVisual` component and export helpers, with no Lisa/Alex-specific runtime or ArtifactPane branch.

**Tech Stack:** Python 3.11 + Pydantic backend renderer/contract tests; React 19 + TypeScript 5.x + Vitest frontend parser/component/export tests; shared `workflow_manifest.json` config.

---

## File Map

- Modify: `tools/new-agents/workflow_manifest.json`
  - Move `timeline-map` from planned complex visual types to current types.
  - Change `INCIDENT_REVIEW/TIMELINE` visual contract from Mermaid `timeline` to structured visual `timeline-map`.
  - Change renderer output text from `Mermaid timeline` to `ai4se-visual timeline-map`.
- Modify: `tools/new-agents/backend/agent_contracts.py`
  - Remove TIMELINE from `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS`.
  - Add TIMELINE to `REQUIRED_ARTIFACT_STRUCTURED_VISUALS`.
  - Add `timeline-map` schema prompt and validation.
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
  - Stop emitting Mermaid timeline for TIMELINE.
  - Add `_render_timeline_map_visual()` and append it to TIMELINE artifact.
- Modify tests:
  - `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
  - `tools/new-agents/backend/tests/test_agent_contracts.py`
  - `tools/new-agents/backend/tests/test_agent_runtime.py`
  - `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify frontend:
  - `tools/new-agents/frontend/src/core/structuredVisuals.ts`
  - `tools/new-agents/frontend/src/components/StructuredVisual.tsx`
  - `tools/new-agents/frontend/src/core/artifactExport.ts`
  - `tools/new-agents/frontend/src/core/docxExport.ts`
  - `tools/new-agents/frontend/src/core/prompts/incident_review/timeline.ts`
- Modify frontend tests:
  - `tools/new-agents/frontend/src/core/__tests__/structuredVisuals.test.ts`
  - `tools/new-agents/frontend/src/components/__tests__/StructuredVisual.test.tsx`
  - `tools/new-agents/frontend/src/core/__tests__/artifactExport.test.ts`
  - `tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`
  - `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
  - `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`
- Modify docs:
  - `docs/TESTING.md`
  - `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`

---

### Task 1: Backend Visual Contract Red Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`

- [ ] **Step 1: Write failing contract tests**

Add focused assertions that TIMELINE now requires `timeline-map` and no longer requires Mermaid `timeline`:

```python
def test_incident_timeline_requires_timeline_map_not_mermaid_timeline():
    assert ("INCIDENT_REVIEW", "TIMELINE") not in REQUIRED_ARTIFACT_MERMAID_DIAGRAMS
    assert REQUIRED_ARTIFACT_STRUCTURED_VISUALS[("INCIDENT_REVIEW", "TIMELINE")] == [
        "timeline-map"
    ]
```

Add a negative artifact contract test:

```python
def test_incident_timeline_rejects_missing_timeline_map_visual():
    output = AgentTurnOutput(
        chat="已生成事件时间线。",
        artifact_update=ArtifactUpdate(
            type="replace",
            markdown="# 故障复盘报告\n\n## 1. 事件概要\n...\n## 9. 阶段门禁\n...",
        ),
        next_stage=None,
    )

    with pytest.raises(ValueError, match="timeline-map"):
        validate_agent_turn(output, workflow_id="INCIDENT_REVIEW", stage_id="TIMELINE")
```

In workflow sync tests, assert manifest TIMELINE visual contract contains `requiredStructuredVisuals: ["timeline-map"]`, not `requiredMermaidDiagrams`.

- [ ] **Step 2: Run RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "incident_timeline or visual_protocol"
```

Expected: fail because TIMELINE still requires Mermaid `timeline` and `timeline-map` is unsupported.

### Task 2: Backend Contract and Renderer

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
- Modify: backend tests from Task 1 plus `test_artifact_data_renderers.py` and `test_agent_runtime.py`

- [ ] **Step 1: Update manifest and contract maps**

Expected manifest shape:

```json
"visualContract": {
  "requiredStructuredVisuals": ["timeline-map"]
}
```

Expected backend maps:

```python
REQUIRED_ARTIFACT_STRUCTURED_VISUALS = {
    ("INCIDENT_REVIEW", "TIMELINE"): ["timeline-map"],
    ...
}
```

- [ ] **Step 2: Add `timeline-map` validation**

Add contract validation equivalent to:

```python
def is_valid_timeline_map_visual_block(block: dict[str, Any]) -> bool:
    if block.get("type") != "timeline-map":
        return False
    events = block.get("events")
    if not isinstance(events, list) or not events:
        return False
    event_ids: set[str] = set()
    for event in events:
        if not isinstance(event, dict):
            return False
        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in event_ids:
            return False
        event_ids.add(event_id)
        for field in ("time", "title", "description"):
            if not isinstance(event.get(field), str) or not event[field].strip():
                return False
        fact_ids = event.get("factIds")
        if not isinstance(fact_ids, list) or not fact_ids:
            return False
        if not all(isinstance(fact_id, str) and fact_id.strip() for fact_id in fact_ids):
            return False
    return True
```

Wire it from `is_valid_structured_visual_block()`.

- [ ] **Step 3: Add renderer**

Add helper equivalent to:

```python
def _render_timeline_map_visual(events: list[IncidentTimelineEvent]) -> str:
    visual = {
        "type": "timeline-map",
        "title": "事件时间线",
        "events": [
            {
                "id": f"TL-{index:03d}",
                "time": event.time,
                "title": event.event,
                "description": event.detail,
                "factIds": event.fact_ids,
                "confidence": event.confidence,
                "blocking": event.blocking,
                "status": event.status,
            }
            for index, event in enumerate(events, start=1)
        ],
    }
    return "```ai4se-visual\n" + json.dumps(visual, ensure_ascii=False, indent=2) + "\n```"
```

Append this helper in `render_incident_review_timeline_markdown()` and remove Mermaid timeline output.

- [ ] **Step 4: Update renderer/runtime tests**

Expected assertions:

```python
assert "```ai4se-visual" in output.artifact_update.markdown
assert '"type": "timeline-map"' in output.artifact_update.markdown
assert "```mermaid" not in output.artifact_update.markdown
assert "timeline\n" not in output.artifact_update.markdown
```

- [ ] **Step 5: Run GREEN backend focus**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "incident_timeline or visual_contract or timeline_map"
```

Expected: all selected tests pass.

### Task 3: Frontend Parser and Component

**Files:**
- Modify: `tools/new-agents/frontend/src/core/structuredVisuals.ts`
- Modify: `tools/new-agents/frontend/src/components/StructuredVisual.tsx`
- Modify: `tools/new-agents/frontend/src/core/__tests__/structuredVisuals.test.ts`
- Modify: `tools/new-agents/frontend/src/components/__tests__/StructuredVisual.test.tsx`

- [ ] **Step 1: Write parser RED tests**

Add tests equivalent to:

```typescript
it('parses timeline-map events', () => {
  const result = parseStructuredVisual(JSON.stringify({
    type: 'timeline-map',
    title: '事件时间线',
    events: [{
      id: 'TL-001',
      time: '10:05',
      title: '支付回调失败',
      description: '回调多次超时',
      factIds: ['F-001'],
      confidence: '高',
      blocking: '是',
      status: '已确认',
    }],
  }));

  expect(result.valid).toBe(true);
  if (result.valid) {
    expect(result.visual.kind).toBe('timeline');
    expect(result.visual.events[0].factIds).toEqual(['F-001']);
  }
});

it('rejects timeline-map duplicate event ids', () => {
  const result = parseStructuredVisual(JSON.stringify({
    type: 'timeline-map',
    events: [
      { id: 'TL-001', time: '10:05', title: 'A', description: 'A', factIds: ['F-001'] },
      { id: 'TL-001', time: '10:06', title: 'B', description: 'B', factIds: ['F-002'] },
    ],
  }));

  expect(result.valid).toBe(false);
});
```

- [ ] **Step 2: Run RED frontend parser**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/structuredVisuals.test.ts --run -t "timeline-map"
```

Expected: fail because `timeline-map` is unsupported.

- [ ] **Step 3: Implement parser and component**

Add types:

```typescript
export interface TimelineStructuredVisualEvent {
    id: string;
    time: string;
    title: string;
    description: string;
    factIds: string[];
    confidence?: string;
    blocking?: string;
    status?: string;
}

export interface TimelineStructuredVisual {
    kind: 'timeline';
    type: Extract<StructuredVisualType, 'timeline-map'>;
    title?: string;
    events: TimelineStructuredVisualEvent[];
}
```

Render timeline cards in `StructuredVisual.tsx` when `visual.kind === 'timeline'`.

- [ ] **Step 4: Run GREEN frontend parser/component**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx --run -t "timeline-map|StructuredVisual"
```

Expected: selected tests pass.

### Task 4: Frontend Export and Prompt Sync

**Files:**
- Modify: `tools/new-agents/frontend/src/core/artifactExport.ts`
- Modify: `tools/new-agents/frontend/src/core/docxExport.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/incident_review/timeline.ts`
- Modify tests:
  - `tools/new-agents/frontend/src/core/__tests__/artifactExport.test.ts`
  - `tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`
  - `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
  - `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`

- [ ] **Step 1: Write RED export/prompt tests**

Expected assertions:

```typescript
expect(exportedText).toContain('事件时间线');
expect(exportedText).toContain('TL-001');
expect(exportedText).toContain('F-001');
expect(exportedText).not.toContain('"type":"timeline-map"');
```

Prompt tests should assert TIMELINE prompt no longer contains Mermaid timeline instructions.

- [ ] **Step 2: Run RED frontend sync tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactExport.test.ts src/core/__tests__/docxExport.test.ts src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run -t "timeline|timeline-map|INCIDENT"
```

Expected: fail on unsupported timeline-map export and old Mermaid prompt expectations.

- [ ] **Step 3: Implement export and prompt changes**

Export should convert timeline visual to readable lines:

```typescript
事件时间线
- TL-001 10:05 支付回调失败
  说明：回调多次超时
  事实：F-001
  可信度：高
  阻断性：是
  状态：已确认
```

Prompt should say backend renders timeline-map from `artifact_data`, and the model must not output Mermaid or `ai4se-visual` JSON.

- [ ] **Step 4: Run GREEN frontend sync tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactExport.test.ts src/core/__tests__/docxExport.test.ts src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
```

Expected: selected files pass.

### Task 5: Docs, Regression, Commit

**Files:**
- Modify: `docs/TESTING.md`
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`

- [ ] **Step 1: Update docs**

Record that `INCIDENT_REVIEW/TIMELINE` visual source changed from Mermaid `timeline` to `ai4se-visual timeline-map`, and that `timeline-map` is now a current structured visual type.

- [ ] **Step 2: Run focused regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "incident_timeline or timeline_map or visual_contract"
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx src/core/__tests__/artifactExport.test.ts src/core/__tests__/docxExport.test.ts src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
git diff --check
```

Expected: all pass.

- [ ] **Step 3: Run New Agents module regression**

Run:

```bash
./scripts/test/test-local.sh new-agents
```

Expected: New Agents frontend and backend tests pass.

- [ ] **Step 4: Record full verification boundary**

If `./scripts/test/test-local.sh all` is run and environment blocks MidScene/Playwright, record exact failure. If not run, record why New Agents module regression is the slice gate.

- [ ] **Step 5: Commit and push**

Run:

```bash
git status -sb
git diff --shortstat
git add tools/new-agents/workflow_manifest.json tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/frontend/src/core/structuredVisuals.ts tools/new-agents/frontend/src/components/StructuredVisual.tsx tools/new-agents/frontend/src/core/artifactExport.ts tools/new-agents/frontend/src/core/docxExport.ts tools/new-agents/frontend/src/core/prompts/incident_review/timeline.ts tools/new-agents/frontend/src/core/__tests__/structuredVisuals.test.ts tools/new-agents/frontend/src/components/__tests__/StructuredVisual.test.tsx tools/new-agents/frontend/src/core/__tests__/artifactExport.test.ts tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
git diff --cached --name-only
git commit -m "feat(new-agents): 用 timeline-map 渲染故障时间线"
git push origin master
```

Expected: focused commit pushed to GitHub.

## Plan Self-Review

- Spec coverage: tasks cover backend visual contract, renderer, manifest, frontend parser/component, export, prompt sync, docs, verification and commit.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: plan uses `timeline-map`, `kind: 'timeline'`, `events`, `factIds` consistently across backend and frontend.
