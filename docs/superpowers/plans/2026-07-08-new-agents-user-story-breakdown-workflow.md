# Alex 用户故事拆解工作流 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Alex `USER_STORY_BREAKDOWN` online workflow so users can start from a value-discovery blueprint or a new topic and produce a full user story breakdown document.

**Architecture:** Keep New Agents on the shared manifest-derived workflow registry, backend artifact contracts, typed Agent Runtime SSE, persisted run / artifact handoff service, shared frontend store, and shared ChatPane / WorkflowSelect UI. Workflow differences are expressed as manifest data, prompt / template files, backend contract rows, tests, and E2E mock payloads.

**Tech Stack:** Python 3.11, Flask / SQLAlchemy tests, Pydantic contract validation, React 19 + TypeScript + Zustand, Vitest, Playwright E2E mock runner.

---

## File Map

- Create: `docs/superpowers/specs/2026-07-08-new-agents-user-story-breakdown-workflow-design.md`
- Create: `docs/superpowers/plans/2026-07-08-new-agents-user-story-breakdown-workflow.md`
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`
- Modify: `tools/new-agents/frontend/src/core/config/agentWorkflows.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/user_story_breakdown/scope.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/user_story_breakdown/story_map.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/user_story_breakdown/stories.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/user_story_breakdown/handoff.ts`
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
- Modify: `tools/new-agents/frontend/src/pages/__tests__/WorkflowSelect.test.tsx`
- Modify: `tests/e2e/new_agents_browser/sse_mock.py`
- Create: `tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py`
- Modify: `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`
- Modify if endpoint docs need clearer examples: `docs/api-contracts.md`
- Modify if testing matrix needs the new workflow evidence: `docs/TESTING.md`

## Constraints

- Do not add Alex-specific runtime, SSE endpoint, backend store, frontend store, or renderer.
- Do not alter Lisa existing `VALUE_DISCOVERY/BLUEPRINT -> TEST_DESIGN/CLARIFY` and `VALUE_DISCOVERY/BLUEPRINT -> REQ_REVIEW/REVIEW` behavior except to allow an additional Alex outbound handoff in the same manifest list.
- Do not implement structured `artifact_data` story schema or persistent single-story packet in this round.
- Do not output technical tasks, implementation plans, file paths, architecture decisions, or test commands inside the Alex story artifact templates.
- Do not stage unrelated dirty files.

---

### Task 1: Backend Contract And Handoff RED Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`

- [ ] **Step 1: Extend workflow contract sync expectations**

In `FRONTEND_PROMPT_FILES`, add four expected files:

```python
    ("USER_STORY_BREAKDOWN", "SCOPE"): (
        NEW_AGENTS_ROOT
        / "frontend"
        / "src"
        / "core"
        / "prompts"
        / "user_story_breakdown"
        / "scope.ts"
    ),
    ("USER_STORY_BREAKDOWN", "STORY_MAP"): (
        NEW_AGENTS_ROOT
        / "frontend"
        / "src"
        / "core"
        / "prompts"
        / "user_story_breakdown"
        / "story_map.ts"
    ),
    ("USER_STORY_BREAKDOWN", "STORIES"): (
        NEW_AGENTS_ROOT
        / "frontend"
        / "src"
        / "core"
        / "prompts"
        / "user_story_breakdown"
        / "stories.ts"
    ),
    ("USER_STORY_BREAKDOWN", "HANDOFF"): (
        NEW_AGENTS_ROOT
        / "frontend"
        / "src"
        / "core"
        / "prompts"
        / "user_story_breakdown"
        / "handoff.ts"
    ),
```

Rename `test_shared_workflow_manifest_declares_alex_to_lisa_handoffs` to `test_shared_workflow_manifest_declares_required_handoffs` and add the expected Alex internal handoff:

```python
        ("VALUE_DISCOVERY", "BLUEPRINT", "USER_STORY_BREAKDOWN", "SCOPE"),
```

- [ ] **Step 2: Add backend handoff tests for user story breakdown**

In `test_workflow_handoffs.py`, add:

```python
def test_export_run_handoffs_includes_alex_user_story_breakdown_target(app):
    with app.app_context():
        run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(run.id, "BLUEPRINT", BLUEPRINT_MARKDOWN)

        result = export_run_handoffs(run.id)

    targets = [
        (handoff["targetWorkflowId"], handoff["targetStageId"], handoff["targetAgentId"])
        for handoff in result["handoffs"]
    ]
    assert ("USER_STORY_BREAKDOWN", "SCOPE", "alex") in targets
    handoff = next(
        item for item in result["handoffs"]
        if item["targetWorkflowId"] == "USER_STORY_BREAKDOWN"
    )
    assert handoff["id"] == "value-discovery-blueprint-to-user-story-breakdown"
    assert handoff["label"] == "从需求蓝图继续拆用户故事"
    assert "VALUE_DISCOVERY/BLUEPRINT" in handoff["prompt"]
    assert "USER_STORY_BREAKDOWN/SCOPE" in handoff["prompt"]
```

Add:

```python
def test_export_target_workflow_handoffs_returns_upstream_requirement_blueprints(app):
    with app.app_context():
        source_run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(source_run.id, "BLUEPRINT", BLUEPRINT_MARKDOWN)
        source_run_id = source_run.id

        result = handoff_service.export_target_workflow_handoffs(
            "USER_STORY_BREAKDOWN",
            "SCOPE",
        )

    assert result["targetWorkflowId"] == "USER_STORY_BREAKDOWN"
    assert result["targetStageId"] == "SCOPE"
    assert len(result["handoffs"]) == 1
    handoff = result["handoffs"][0]
    assert handoff["id"] == "value-discovery-blueprint-to-user-story-breakdown"
    assert handoff["label"] == "从需求蓝图继续拆用户故事"
    assert handoff["sourceRunId"] == source_run_id
    assert handoff["sourceWorkflowId"] == "VALUE_DISCOVERY"
    assert handoff["sourceStageId"] == "BLUEPRINT"
    assert handoff["targetWorkflowId"] == "USER_STORY_BREAKDOWN"
    assert handoff["targetStageId"] == "SCOPE"
    assert handoff["targetAgentId"] == "alex"
    assert "需求蓝图" in handoff["sourceArtifactSummary"]
```

Add:

```python
def test_start_user_story_breakdown_handoff_persists_source_trace_in_target_message(app):
    with app.app_context():
        source_run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(source_run.id, "BLUEPRINT", BLUEPRINT_MARKDOWN)
        source_run_id = source_run.id

        result = start_workflow_handoff(
            source_run.id,
            "value-discovery-blueprint-to-user-story-breakdown",
        )
        target_snapshot = get_run_snapshot(result["targetRunId"])

    assert result["sourceRunId"] == source_run_id
    assert result["targetWorkflowId"] == "USER_STORY_BREAKDOWN"
    assert result["targetStageId"] == "SCOPE"
    assert result["targetAgentId"] == "alex"
    target_message = target_snapshot["messages"][0]["content"]
    assert f"源 run: {source_run_id}" in target_message
    assert "源 artifact version: 1" in target_message
    assert f"源 artifact digest: {result['sourceArtifactDigest']}" in target_message
    assert "VALUE_DISCOVERY/BLUEPRINT" in target_message
    assert "USER_STORY_BREAKDOWN/SCOPE" in target_message
```

- [ ] **Step 3: Run backend RED tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py -q
```

Expected: fail because `USER_STORY_BREAKDOWN` is not in `WORKFLOW_STAGES`, manifest, artifact headings, prompt files, or handoff config.

### Task 2: Frontend Config And ChatPane RED Tests

**Files:**
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
- Modify: `tools/new-agents/frontend/src/pages/__tests__/WorkflowSelect.test.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`

- [ ] **Step 1: Add workflow config tests**

In `workflows.test.ts`, update the Alex core workflow test to expect `user-story-breakdown`:

```ts
expect(ids).toContain('user-story-breakdown');
```

Add:

```ts
it('should have USER_STORY_BREAKDOWN workflow defined with correct agentId and stages', () => {
    const wf = WORKFLOWS.USER_STORY_BREAKDOWN;
    expect(wf).toBeDefined();
    expect(wf.name).toBe('用户故事拆解');
    expect(wf.agentId).toBe('alex');
    expect(wf.slug).toBe('user-story-breakdown');
    expect(wf.stages.map(stage => stage.id)).toEqual(['SCOPE', 'STORY_MAP', 'STORIES', 'HANDOFF']);
    for (const stage of wf.stages) {
        expect(stage.description.length).toBeGreaterThan(100);
        expect(stage.template.length).toBeGreaterThan(100);
    }
});

it('should expose user-story-breakdown as online instead of plan for Alex', () => {
    const workflows = getAgentWorkflows('alex');
    const storyBreakdown = workflows.find(w => w.id === 'user-story-breakdown');
    expect(storyBreakdown).toBeDefined();
    expect(storyBreakdown?.status).toBe('online');
    expect(storyBreakdown?.link).toBe('/workspace/alex/user-story-breakdown');
    expect(workflows.find(w => w.id === 'story-breakdown')).toBeUndefined();
});
```

- [ ] **Step 2: Add WorkflowSelect test**

In `WorkflowSelect.test.tsx`, extend `renders alex workflows`:

```ts
expect(screen.getByText('用户故事拆解')).toBeTruthy();
```

Add:

```ts
it('navigates to user story breakdown workflow', () => {
    renderComponent('alex');
    const card = screen.getByText('用户故事拆解').closest('[class*="rounded-2xl"]')!;
    fireEvent.click(card);
    expect(mockNavigate).toHaveBeenCalledWith('/workspace/alex/user-story-breakdown');
});
```

- [ ] **Step 3: Add ChatPane target-side handoff tests**

In `ChatPane.test.tsx`, add a test for `USER_STORY_BREAKDOWN/SCOPE` empty session:

```ts
it('loads target-side handoff choices when user story breakdown starts without a run', async () => {
    useStore.setState({
        workflow: 'USER_STORY_BREAKDOWN' as WorkflowType,
        stageIndex: 0,
        currentRunId: null,
        chatHistory: [],
    });
    vi.mocked(fetchTargetWorkflowHandoffCandidates).mockResolvedValue([
        {
            id: 'value-discovery-blueprint-to-user-story-breakdown',
            label: '从需求蓝图继续拆用户故事',
            sourceRunId: 'value-run-123',
            sourceWorkflowId: 'VALUE_DISCOVERY',
            sourceStageId: 'BLUEPRINT',
            sourceArtifactVersion: 1,
            sourceArtifactDigest: 'sha256:def456',
            sourceArtifactSummary: '# AI 测试设计助手需求蓝图',
            targetWorkflowId: 'USER_STORY_BREAKDOWN',
            targetStageId: 'SCOPE',
            targetAgentId: 'alex',
            prompt: '请基于需求蓝图继续拆用户故事。',
        },
    ]);

    render(<ChatPane />);

    await waitFor(() => {
        expect(fetchTargetWorkflowHandoffCandidates).toHaveBeenCalledWith('USER_STORY_BREAKDOWN', 'SCOPE');
    });
    expect(await screen.findByText('选择用户故事拆解起点')).toBeDefined();
    expect(screen.getByText('开启新话题')).toBeDefined();
    expect(screen.getByText('从需求蓝图继续拆用户故事')).toBeDefined();
    expect(screen.getByText(/# AI 测试设计助手需求蓝图/)).toBeDefined();
});
```

Add an apply test:

```ts
it('applies a target-side handoff choice from the user story breakdown empty state', async () => {
    useStore.setState({
        workflow: 'USER_STORY_BREAKDOWN' as WorkflowType,
        stageIndex: 0,
        currentRunId: null,
        chatHistory: [],
    });
    vi.mocked(fetchTargetWorkflowHandoffCandidates).mockResolvedValue([
        {
            id: 'value-discovery-blueprint-to-user-story-breakdown',
            label: '从需求蓝图继续拆用户故事',
            sourceRunId: 'value-run-123',
            sourceWorkflowId: 'VALUE_DISCOVERY',
            sourceStageId: 'BLUEPRINT',
            sourceArtifactVersion: 1,
            sourceArtifactDigest: 'sha256:def456',
            sourceArtifactSummary: '# AI 测试设计助手需求蓝图',
            targetWorkflowId: 'USER_STORY_BREAKDOWN',
            targetStageId: 'SCOPE',
            targetAgentId: 'alex',
            prompt: '请基于需求蓝图继续拆用户故事。',
        },
    ]);
    vi.mocked(startWorkflowHandoff).mockResolvedValue({
        id: 'value-discovery-blueprint-to-user-story-breakdown',
        label: '从需求蓝图继续拆用户故事',
        sourceRunId: 'value-run-123',
        sourceWorkflowId: 'VALUE_DISCOVERY',
        sourceStageId: 'BLUEPRINT',
        sourceArtifactVersion: 1,
        sourceArtifactDigest: 'sha256:def456',
        sourceArtifactSummary: '# AI 测试设计助手需求蓝图',
        targetRunId: 'story-run-456',
        targetWorkflowId: 'USER_STORY_BREAKDOWN',
        targetStageId: 'SCOPE',
        targetAgentId: 'alex',
        prompt: '请基于需求蓝图继续拆用户故事。',
    });

    render(<ChatPane />);
    fireEvent.click(await screen.findByText('从需求蓝图继续拆用户故事'));

    await waitFor(() => {
        expect(startWorkflowHandoff).toHaveBeenCalledWith(
            'value-run-123',
            'value-discovery-blueprint-to-user-story-breakdown'
        );
    });
    expect(useStore.getState().workflow).toBe('USER_STORY_BREAKDOWN');
    expect(useStore.getState().stageIndex).toBe(0);
    expect(useStore.getState().currentRunId).toBe('story-run-456');
    expect(mockNavigate).toHaveBeenCalledWith('/workspace/alex/user-story-breakdown?runId=story-run-456');
});
```

Add an empty state test:

```ts
it('shows a new-topic path when user story breakdown has no upstream candidates', async () => {
    useStore.setState({
        workflow: 'USER_STORY_BREAKDOWN' as WorkflowType,
        stageIndex: 0,
        currentRunId: null,
        chatHistory: [],
    });
    vi.mocked(fetchTargetWorkflowHandoffCandidates).mockResolvedValue([]);

    render(<ChatPane />);

    expect(await screen.findByText('暂无可继承的需求蓝图，可以直接开启新话题')).toBeDefined();
    expect(screen.getByText('开启新话题')).toBeDefined();
});
```

- [ ] **Step 4: Run frontend RED tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/pages/__tests__/WorkflowSelect.test.tsx src/components/__tests__/ChatPane.test.tsx
```

Expected: fail because workflow type, manifest, prompts, plan-card removal, and generic target-side handoff panel are not implemented.

### Task 3: Add Workflow Manifest, Backend Contracts, And Prompt Files

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/user_story_breakdown/scope.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/user_story_breakdown/story_map.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/user_story_breakdown/stories.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/user_story_breakdown/handoff.ts`

- [ ] **Step 1: Add manifest handoff**

In `workflow_manifest.json`, add this handoff after the idea-to-value handoff and before Lisa handoffs:

```json
{
  "id": "value-discovery-blueprint-to-user-story-breakdown",
  "sourceWorkflowId": "VALUE_DISCOVERY",
  "sourceStageId": "BLUEPRINT",
  "targetWorkflowId": "USER_STORY_BREAKDOWN",
  "targetStageId": "SCOPE",
  "targetAgentId": "alex",
  "promptTemplateId": "source-artifact-handoff",
  "label": "从需求蓝图继续拆用户故事"
}
```

- [ ] **Step 2: Add manifest workflow**

Add `USER_STORY_BREAKDOWN` after `VALUE_DISCOVERY` in `workflow_manifest.json`:

```json
"USER_STORY_BREAKDOWN": {
  "id": "USER_STORY_BREAKDOWN",
  "agentId": "alex",
  "slug": "user-story-breakdown",
  "name": "用户故事拆解",
  "description": "把需求蓝图拆成用户故事地图、MVP 切片、用户故事卡片和可交接故事清单。",
  "listing": {
    "name": "用户故事拆解",
    "description": "从需求蓝图或新话题出发，拆出可独立交付给后续 AI Coding 的用户故事卡片。",
    "icon": "ListChecks",
    "preview": {
      "suitableFor": [
        "已经有需求蓝图，需要拆成用户故事",
        "需要识别 MVP slice 和后续 release slice",
        "需要准备可交给 AI Coding 的单故事需求输入"
      ],
      "notSuitableFor": [
        "只有模糊想法，还没有产品方向或需求蓝图",
        "需要直接生成开发任务、代码结构或实现计划"
      ],
      "requiredInputs": [
        "需求蓝图、核心需求或产品范围说明",
        "目标用户、关键场景和业务规则",
        "MVP 约束、优先级或交付边界"
      ],
      "expectedOutputs": [
        "拆分范围和需求追溯索引",
        "用户故事地图与 MVP slice",
        "Ready / Not ready 用户故事卡片和 handoff 清单"
      ],
      "sampleInput": "基于这份需求蓝图，帮我拆成用户故事地图和可交给 AI Coding 的故事卡。"
    }
  },
  "stages": [
    {
      "id": "SCOPE",
      "name": "校准拆分范围",
      "promptTemplateId": "user_story_breakdown.scope",
      "artifactContract": {
        "requiredHeadings": [
          "# 用户故事拆解文档",
          "## 1. 拆分范围",
          "## 2. 需求追溯索引",
          "## 3. 不拆范围",
          "## 4. 阻塞问题",
          "## 5. 阶段门禁",
          "需求 ID",
          "优先级",
          "状态"
        ]
      },
      "visualContract": {
        "requiredMermaidDiagrams": [
          "flowchart"
        ]
      }
    },
    {
      "id": "STORY_MAP",
      "name": "绘制故事地图",
      "promptTemplateId": "user_story_breakdown.story_map",
      "artifactContract": {
        "requiredHeadings": [
          "# 用户故事拆解文档",
          "## 1. 用户活动主干",
          "## 2. 用户任务流",
          "## 3. 用户故事地图",
          "## 4. MVP Slice",
          "## 5. Release Slice",
          "## 6. 阶段门禁",
          "活动 ID",
          "任务 ID",
          "Story ID",
          "MVP"
        ]
      },
      "visualContract": {
        "requiredMermaidDiagrams": [
          "flowchart"
        ]
      }
    },
    {
      "id": "STORIES",
      "name": "编写故事卡片",
      "promptTemplateId": "user_story_breakdown.stories",
      "artifactContract": {
        "requiredHeadings": [
          "# 用户故事拆解文档",
          "## 1. 故事拆分原则",
          "## 2. 用户故事卡片",
          "## 3. Ready Stories",
          "## 4. Not Ready Stories",
          "## 5. 开放问题",
          "## 6. 阶段门禁",
          "Story ID",
          "作为",
          "我想要",
          "以便",
          "验收标准",
          "来源需求",
          "状态"
        ]
      }
    },
    {
      "id": "HANDOFF",
      "name": "准备故事交接",
      "promptTemplateId": "user_story_breakdown.handoff",
      "artifactContract": {
        "requiredHeadings": [
          "# 单故事 Handoff 清单",
          "## 1. Ready Story 总览",
          "## 2. 单故事需求包",
          "## 3. 上游追溯",
          "## 4. Not Ready 阻塞项",
          "## 5. AI Coding 输入边界",
          "## 6. 阶段门禁",
          "storyId",
          "requirementId",
          "acceptanceCriteria",
          "businessRules",
          "openQuestions"
        ]
      }
    }
  ],
  "onboarding": {
    "welcomeMessage": "你好！我是 Alex，用户故事拆解顾问。你可以直接描述需求范围，也可以从已有需求蓝图继续，我会帮你拆出用户故事地图、MVP 切片和可交接的故事卡片。",
    "starterPrompts": [
      "我有一份 AI 测试设计助手需求蓝图，帮我拆成用户故事",
      "请把会员权益需求拆成 MVP 用户故事和后续版本故事",
      "我想把客户反馈整理工具的需求拆成能交给 AI Coding 的故事卡"
    ],
    "inputPlaceholder": "粘贴需求蓝图、核心需求或产品范围..."
  }
}
```

- [ ] **Step 3: Add backend workflow stages and headings**

In `agent_contracts.py`, add:

```python
    "USER_STORY_BREAKDOWN": ["SCOPE", "STORY_MAP", "STORIES", "HANDOFF"],
```

Add `REQUIRED_ARTIFACT_HEADINGS` entries matching the manifest headings above.

Add:

```python
    ("USER_STORY_BREAKDOWN", "SCOPE"): ["flowchart"],
    ("USER_STORY_BREAKDOWN", "STORY_MAP"): ["flowchart"],
```

to `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS`.

- [ ] **Step 4: Add frontend type**

In `types.ts`, change:

```ts
export type WorkflowType = 'TEST_DESIGN' | 'REQ_REVIEW' | 'INCIDENT_REVIEW' | 'IDEA_BRAINSTORM' | 'VALUE_DISCOVERY';
```

to include:

```ts
| 'USER_STORY_BREAKDOWN'
```

- [ ] **Step 5: Create prompt files**

Create four files under `tools/new-agents/frontend/src/core/prompts/user_story_breakdown/`.

Each file must:

- export `*_PROMPT` and `*_TEMPLATE`;
- mention stable `REQ-*` and `US-*` IDs where relevant;
- explicitly forbid technical task lists;
- include all required headings from the contract;
- for `scope.ts` and `story_map.ts`, include a Mermaid `flowchart` fenced example using `${FENCE}mermaid`.

- [ ] **Step 6: Register prompt files**

In `workflows.ts`, import:

```ts
import { SCOPE_PROMPT, SCOPE_TEMPLATE } from './prompts/user_story_breakdown/scope';
import { STORY_MAP_PROMPT, STORY_MAP_TEMPLATE } from './prompts/user_story_breakdown/story_map';
import { STORIES_PROMPT, STORIES_TEMPLATE } from './prompts/user_story_breakdown/stories';
import { HANDOFF_PROMPT, HANDOFF_TEMPLATE } from './prompts/user_story_breakdown/handoff';
```

Add entries:

```ts
        'user_story_breakdown.scope': {
            description: SCOPE_PROMPT,
            template: SCOPE_TEMPLATE,
        },
        'user_story_breakdown.story_map': {
            description: STORY_MAP_PROMPT,
            template: STORY_MAP_TEMPLATE,
        },
        'user_story_breakdown.stories': {
            description: STORIES_PROMPT,
            template: STORIES_TEMPLATE,
        },
        'user_story_breakdown.handoff': {
            description: HANDOFF_PROMPT,
            template: HANDOFF_TEMPLATE,
        },
```

- [ ] **Step 7: Run backend contract tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py -q
```

Expected: backend contract / handoff tests pass or reveal exact sync misses to fix.

### Task 4: Generalize Target-Side Handoff Startup UI

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
- Modify: `tools/new-agents/frontend/src/core/config/agentWorkflows.ts`

- [ ] **Step 1: Remove Alex plan card**

In `agentWorkflows.ts`, delete the `NON_RUNTIME_AGENT_WORKFLOWS` item with:

```ts
id: 'story-breakdown'
```

Keep `competitive-analysis` as Alex plan.

- [ ] **Step 2: Add target handoff copy config**

In `ChatPane.tsx`, add near component-level helpers:

```ts
const TARGET_STARTUP_HANDOFF_COPY: Partial<Record<WorkflowType, {
  title: string;
  description: string;
  loading: string;
  empty: string;
}>> = {
  VALUE_DISCOVERY: {
    title: '选择需求蓝图起点',
    description: '可以从空白话题开始，也可以继承已有产品概念简报继续梳理。',
    loading: '正在查找可继承的产品概念简报...',
    empty: '暂无可继承的产品概念简报，可以直接开启新话题',
  },
  USER_STORY_BREAKDOWN: {
    title: '选择用户故事拆解起点',
    description: '可以从空白话题开始，也可以继承已有需求蓝图继续拆分。',
    loading: '正在查找可继承的需求蓝图...',
    empty: '暂无可继承的需求蓝图，可以直接开启新话题',
  },
};
```

- [ ] **Step 3: Generalize target startup condition**

Replace the hard-coded `shouldOfferTargetStartupHandoff` with:

```ts
  const targetStartupHandoffCopy = TARGET_STARTUP_HANDOFF_COPY[workflow];
  const shouldOfferTargetStartupHandoff = Boolean(
    targetStartupHandoffCopy
    && currentStageId === WORKFLOWS[workflow].stages[0]?.id
    && !currentRunId
    && chatHistory.length === 0
  );
```

This keeps the target startup panel limited to configured workflows and first stages.

- [ ] **Step 4: Use copy config in panel**

Replace hard-coded panel text with `targetStartupHandoffCopy?.title`, `.description`, `.loading`, and `.empty`. Keep the generic error text:

```tsx
<p className="mt-3 text-xs text-amber-100">暂时无法读取上游内容，可以直接开启新话题。</p>
```

- [ ] **Step 5: Run frontend focused tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/pages/__tests__/WorkflowSelect.test.tsx src/components/__tests__/ChatPane.test.tsx
```

Expected: pass after manifest and prompt work.

### Task 5: Add Browser Mock E2E For Full User Story Breakdown

**Files:**
- Modify: `tests/e2e/new_agents_browser/sse_mock.py`
- Create: `tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py`

- [ ] **Step 1: Add four StagePayload entries**

Add `("USER_STORY_BREAKDOWN", "...")` entries to `STAGE_PAYLOADS`:

- `SCOPE`: chat requests transition to `STORY_MAP`; markdown includes `# 用户故事拆解文档`, `## 1. 拆分范围`, `## 2. 需求追溯索引`, `REQ-001`, `REQ-002`, and no technical tasks.
- `STORY_MAP`: chat requests transition to `STORIES`; markdown includes required headings, `MVP Slice`, `US-001`, and a Mermaid `flowchart TD`.
- `STORIES`: chat requests transition to `HANDOFF`; markdown includes `## 2. 用户故事卡片`, Ready / Not Ready sections, `作为`, `我想要`, `以便`, `验收标准`, `来源需求`, `状态`.
- `HANDOFF`: final chat has no next stage; markdown includes `# 单故事 Handoff 清单`, `storyId`, `requirementId`, `acceptanceCriteria`, `businessRules`, `openQuestions`, and explicitly says not to include implementation plan, file paths, code changes, or test commands.

- [ ] **Step 2: Create E2E scenario test**

Create `test_alex_user_story_breakdown_workflow.py` with:

```python
from __future__ import annotations

import pytest

from .sse_mock import STAGE_PAYLOADS
from .workflow_runner import (
    StageExpectation,
    WorkflowScenario,
    run_complete_workflow,
)


pytestmark = pytest.mark.e2e


def _alex_user_story_breakdown_scenario() -> WorkflowScenario:
    return WorkflowScenario(
        agent_name="Alex",
        workflow_name="用户故事拆解",
        initial_heading="用户故事拆解",
        prompt="基于 AI 测试设计助手需求蓝图，拆成用户故事地图和可交接故事卡。",
        stages=(
            StageExpectation(
                stage_tab="校准拆分范围",
                transition_label="确认进入 绘制故事地图",
                artifact_headings=(
                    "# 用户故事拆解文档",
                    "## 1. 拆分范围",
                    "## 2. 需求追溯索引",
                    "REQ-001",
                ),
                user_turns=(
                    "范围确认：MVP 只覆盖需求澄清、测试策略和测试用例生成。",
                    "补充：先不包含团队模板适配和需求系统接入。",
                ),
            ),
            StageExpectation(
                stage_tab="绘制故事地图",
                transition_label="确认进入 编写故事卡片",
                artifact_headings=(
                    "# 用户故事拆解文档",
                    "## 3. 用户故事地图",
                    "## 4. MVP Slice",
                    "US-001",
                ),
                visual_markers=("flowchart TD",),
                user_turns=(
                    "故事地图确认：请把用户活动按输入需求、确认风险、生成资产组织。",
                    "MVP slice 确认：第一版要能形成可评审测试策略和用例。",
                ),
            ),
            StageExpectation(
                stage_tab="编写故事卡片",
                transition_label="确认进入 准备故事交接",
                artifact_headings=(
                    "# 用户故事拆解文档",
                    "## 2. 用户故事卡片",
                    "## 3. Ready Stories",
                    "## 4. Not Ready Stories",
                    "验收标准",
                    "来源需求",
                ),
                user_turns=(
                    "故事卡确认：每张故事都要按垂直业务切片，不要按前后端任务拆。",
                    "Ready 判断确认：缺验收标准或依赖不清楚的故事放 Not Ready。",
                ),
            ),
            StageExpectation(
                stage_tab="准备故事交接",
                transition_label=None,
                artifact_headings=(
                    "# 单故事 Handoff 清单",
                    "## 1. Ready Story 总览",
                    "## 2. 单故事需求包",
                    "## 5. AI Coding 输入边界",
                    "storyId",
                    "acceptanceCriteria",
                ),
            ),
        ),
    )


def test_alex_user_story_breakdown_workflow_completes_all_stages(new_agents_page):
    run_result = run_complete_workflow(new_agents_page, _alex_user_story_breakdown_scenario())

    assert "单故事 Handoff 清单" in run_result.final_artifact
    assert "实现计划" not in run_result.final_artifact
    assert "文件路径" not in run_result.final_artifact
    assert [snapshot.stage_name for snapshot in run_result.stage_artifacts] == [
        "校准拆分范围",
        "绘制故事地图",
        "编写故事卡片",
        "准备故事交接",
    ]
    assert len(run_result.stage_transitions) == 3


def test_alex_user_story_breakdown_mock_fixture_keeps_business_vertical_slices():
    combined = "\n".join(
        STAGE_PAYLOADS[("USER_STORY_BREAKDOWN", stage)].markdown
        for stage in ("SCOPE", "STORY_MAP", "STORIES", "HANDOFF")
    )

    for required_text in (
        "REQ-001",
        "US-001",
        "MVP Slice",
        "Ready Stories",
        "Not Ready Stories",
        "作为",
        "我想要",
        "以便",
        "acceptanceCriteria",
    ):
        assert required_text in combined

    for forbidden_text in ("建表", "写接口", "做页面", "代码修改", "测试命令"):
        assert forbidden_text not in combined
```

- [ ] **Step 3: Run E2E test**

Run:

```bash
.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py -q
```

Expected: pass if browser test fixture is available; if environment cannot launch Playwright, record the exact failure and keep deterministic fixture test as partial evidence.

### Task 6: Documentation Updates And Full Verification

**Files:**
- Modify: `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`
- Modify: `docs/api-contracts.md`
- Modify: `docs/TESTING.md`

- [ ] **Step 1: Update todo status**

In the Alex todo, change status to:

```markdown
- 状态：执行中（第 1、2 轮已完成；第 3 轮待启动）
```

Add an execution record for 第 2 轮 with changed files and verification results.

- [ ] **Step 2: Update API / testing docs if needed**

If the endpoint behavior remains the same but now supports another target-side handoff, update `docs/api-contracts.md` only to mention `USER_STORY_BREAKDOWN/SCOPE` as an example target-side handoff.

Update `docs/TESTING.md` New Agents Workflow Handoff layer to mention that target-side empty-session handoff now covers both `VALUE_DISCOVERY/ELEVATOR` and `USER_STORY_BREAKDOWN/SCOPE`.

- [ ] **Step 3: Run focused backend verification**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: pass.

- [ ] **Step 4: Run focused frontend verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/pages/__tests__/WorkflowSelect.test.tsx src/components/__tests__/ChatPane.test.tsx
```

Expected: pass.

- [ ] **Step 5: Run E2E browser verification**

Run:

```bash
.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py -q
```

Expected: pass or record environment-specific blocker.

- [ ] **Step 6: Run New Agents batch verification**

Run:

```bash
./scripts/test/test-local.sh new-agents
```

Expected: frontend and backend New Agents suites pass. Existing React `act(...)` warnings may appear only if they do not fail tests.

- [ ] **Step 7: Run diff hygiene**

Run:

```bash
git diff --check
```

Expected: no whitespace errors.

- [ ] **Step 8: Commit and push focused batch**

After verification, stage only this round's files:

```bash
git add docs/superpowers/specs/2026-07-08-new-agents-user-story-breakdown-workflow-design.md docs/superpowers/plans/2026-07-08-new-agents-user-story-breakdown-workflow.md docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md docs/api-contracts.md docs/TESTING.md tools/new-agents/workflow_manifest.json tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/workflows.ts tools/new-agents/frontend/src/core/config/agentWorkflows.ts tools/new-agents/frontend/src/core/prompts/user_story_breakdown/scope.ts tools/new-agents/frontend/src/core/prompts/user_story_breakdown/story_map.ts tools/new-agents/frontend/src/core/prompts/user_story_breakdown/stories.ts tools/new-agents/frontend/src/core/prompts/user_story_breakdown/handoff.ts tools/new-agents/frontend/src/components/ChatPane.tsx tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts tools/new-agents/frontend/src/pages/__tests__/WorkflowSelect.test.tsx tests/e2e/new_agents_browser/sse_mock.py tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py
git commit -m "feat(new-agents): 新增 Alex 用户故事拆解工作流"
git push
```

If any listed optional doc file is unchanged, omit it from `git add`.

## Plan Self-Review

- Spec coverage: the plan covers manifest, backend contract, frontend workflow listing, target-side handoff, prompt templates, E2E mock evidence, docs, verification, commit, and push.
- Placeholder scan: no `TBD` or unbounded implementation instructions remain; every task has exact files and commands.
- Type consistency: `USER_STORY_BREAKDOWN`, `SCOPE`, `STORY_MAP`, `STORIES`, `HANDOFF`, `user-story-breakdown`, and `user_story_breakdown.*` are used consistently.
- Scope check: structured story `artifact_data` and persistent single-story packet are explicitly excluded for later rounds.
