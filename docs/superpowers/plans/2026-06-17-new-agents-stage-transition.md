# New Agents Stage Transition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the New Agents workflow transition loop so confirming a stage transition preserves the completed source artifact, advances to the target stage, and generates the next-stage artifact with the correct stage context.

**Architecture:** Keep the fix inside the existing frontend orchestration boundary. `agentCore.ts` should decide what a `NEXT_STAGE` chunk means, `chatService.ts` should apply artifact writes before stopping the stream, and `buildSystemPrompt.ts` should include prior-stage artifacts whenever a later stage needs context.

**Tech Stack:** React 19, Zustand, Vitest, TypeScript, existing typed Agent Runtime SSE adapter.

---

### Task 1: Preserve Source Artifact When NEXT_STAGE Is Returned

**Files:**
- Modify: `tools/new-agents/frontend/src/core/agentCore.ts`
- Modify: `tools/new-agents/frontend/src/core/__tests__/agentCore.test.ts`
- Modify: `tools/new-agents/frontend/src/services/chatService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`

- [x] **Step 1: Write the failing reducer test**

Update `tools/new-agents/frontend/src/core/__tests__/agentCore.test.ts` in `describe('reduceAgentStreamChunk')`. Replace the current `requests a pending transition and blocks unconfirmed next-stage artifact writes` expectation with this behavior:

```ts
it('requests a pending transition and preserves the completed current-stage artifact', () => {
    const decision = reduceAgentStreamChunk(
        {
            chatResponse: '当前阶段已完成，请确认进入下一阶段。',
            newArtifact: '# 需求分析文档\n最终版',
            action: 'NEXT_STAGE',
            hasArtifactUpdate: true,
        },
        {
            stageIndex: 0,
            stageCount: 4,
            currentStageId: 'CLARIFY',
            hasTransitioned: false,
        }
    );

    expect(decision).toEqual({
        assistantContent: '当前阶段已完成，请确认进入下一阶段。',
        artifactTruncated: false,
        artifactUpdate: {
            stageId: 'CLARIFY',
            content: '# 需求分析文档\n最终版',
        },
        pendingStageTransition: {
            fromStageIndex: 0,
            toStageIndex: 1,
        },
        hasTransitioned: true,
        shouldStopStream: true,
    });
});
```

- [x] **Step 2: Verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts
```

Expected: the new test fails because `reduceAgentStreamChunk(...)` does not return `artifactUpdate` for `NEXT_STAGE`.

- [x] **Step 3: Write the failing service test**

In `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`, add this test near the existing `NEXT_STAGE` tests:

```ts
it('should save the final source-stage artifact before stopping on NEXT_STAGE', async () => {
    vi.mocked(generateResponseStream).mockImplementation(async function* () {
        yield {
            chatResponse: '需求澄清完成，请确认进入策略制定。',
            newArtifact: '# 需求分析文档\n最终版',
            action: 'NEXT_STAGE',
            hasArtifactUpdate: true,
        };
        yield {
            chatResponse: '不应继续消费',
            newArtifact: '# 测试策略蓝图\n不应写入',
            action: '',
            hasArtifactUpdate: true,
        };
    });

    const { result } = renderHook(() => useChatService());

    act(() => {
        result.current.setInput('完成需求澄清');
    });

    await act(async () => {
        await result.current.handleSend();
    });

    const state = useStore.getState();
    expect(state.pendingStageTransition).toEqual({ fromStageIndex: 0, toStageIndex: 1 });
    expect(state.stageIndex).toBe(0);
    expect(state.artifactContent).toBe('# 需求分析文档\n最终版');
    expect(state.stageArtifacts.CLARIFY).toBe('# 需求分析文档\n最终版');
    expect(state.stageArtifacts.STRATEGY).toBeUndefined();
});
```

- [x] **Step 4: Verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts
```

Expected: the new test fails because `chatService.ts` stops the stream before applying an artifact update from the transition chunk.

- [x] **Step 5: Implement minimal reducer fix**

In `tools/new-agents/frontend/src/core/agentCore.ts`, update the `shouldRequestNextStage` branch to include the current-stage artifact when `chunk.hasArtifactUpdate` is true:

```ts
if (shouldRequestNextStage) {
    return {
        assistantContent: chunk.chatResponse,
        artifactTruncated: chunk.artifactTruncated === true,
        artifactUpdate: chunk.hasArtifactUpdate
            ? {
                stageId: context.currentStageId,
                content: chunk.newArtifact,
            }
            : undefined,
        pendingStageTransition: {
            fromStageIndex: context.stageIndex,
            toStageIndex: context.stageIndex + 1,
        },
        hasTransitioned: true,
        shouldStopStream: true,
    };
}
```

- [x] **Step 6: Implement minimal service ordering fix**

In `tools/new-agents/frontend/src/services/chatService.ts`, apply `decision.artifactUpdate` before checking `decision.shouldStopStream`. The stream loop should keep this order:

```ts
if (decision.pendingStageTransition) {
    useStore.getState().setPendingStageTransition(
        decision.pendingStageTransition
    );
}

if (decision.artifactUpdate) {
    const latestState = useStore.getState();
    latestState.setStageArtifact(
        decision.artifactUpdate.stageId,
        decision.artifactUpdate.content
    );
    latestState.setArtifactContent(
        decision.artifactUpdate.content
    );
    latestState.setArtifactTruncated(false);
    didUpdateArtifact = true;
}

if (decision.shouldStopStream) {
    abortControllerRef.current?.abort();
    break;
}
```

- [x] **Step 7: Verify GREEN for transition tests**

Run:

```bash
cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts
```

Expected: both modified test files pass.

### Task 2: Confirm Transition Uses Target Stage Context

**Files:**
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`

- [x] **Step 1: Add context assertion to the existing confirmation test**

In `should confirm pending stage transition through the service and continue generation`, keep the existing mocked stream and add an assertion after `handleConfirmStageTransition()`:

```ts
expect(useStore.getState().stageIndex).toBe(1);
expect(generateResponseStream).toHaveBeenCalledWith(
    '请继续生成当前阶段产出物',
    [],
    expect.any(AbortSignal)
);
```

This assertion already exists for the call shape; keep it and make sure the stage assertion is checked before reading generated artifacts.

- [x] **Step 2: Run the focused test**

Run:

```bash
cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should confirm pending stage transition through the service and continue generation"
```

Expected: pass after Task 1. If this fails, inspect whether `confirmStageTransition()` runs before `handleSend(...)`.

### Task 3: Include Prior Stage Artifacts In Later Stage Prompts

**Files:**
- Modify: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`
- Modify: `tools/new-agents/frontend/src/__tests__/p0-fixes.test.ts`

- [x] **Step 1: Write failing prompt test for non-final later stages**

In `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`, add:

```ts
it('injects previous stage artifacts when generating a later non-final stage', () => {
    const prompt = buildSystemPrompt({
        agentId: 'lisa',
        workflow: 'TEST_DESIGN',
        stageIndex: 1,
        currentArtifact: '# 测试策略蓝图',
        stageArtifacts: {
            CLARIFY: '# 需求分析文档\n\n关键需求事实',
        },
    });

    expect(prompt).toContain('前序阶段有效结论摘要');
    expect(prompt).toContain('阶段 [CLARIFY] 核心成果');
    expect(prompt).toContain('关键需求事实');
});
```

- [x] **Step 2: Update stale P0 test expectation**

In `tools/new-agents/frontend/src/__tests__/p0-fixes.test.ts`, change `should not inject previous artifacts context when not on last stage` so it asserts stage 0 does not inject previous artifacts, not every non-last stage:

```ts
it('should not inject previous artifacts context on the first stage', () => {
    const previousStageId = WORKFLOWS['TEST_DESIGN'].stages[0].id;
    const prompt = buildSystemPrompt({
        agentId: 'lisa',
        workflow: 'TEST_DESIGN',
        stageIndex: 0,
        currentArtifact: '# Doc',
        stageArtifacts: {
            [previousStageId]: 'some content',
        },
    });

    expect(prompt).not.toContain('前序阶段有效结论摘要');
});
```

- [x] **Step 3: Verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts src/__tests__/p0-fixes.test.ts
```

Expected: the new later-stage prompt test fails because `buildSystemPrompt(...)` only injects prior artifacts on the final stage.

- [x] **Step 4: Implement prior-stage context for every later stage**

In `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`, replace:

```ts
if (stageArtifacts && Object.keys(stageArtifacts).length > 0 && isLastStage) {
```

with:

```ts
if (stageArtifacts && Object.keys(stageArtifacts).length > 0 && stageIndex > 0) {
```

Keep the existing current-stage exclusion:

```ts
if (stageId !== currentStage.id && artifactContent) {
```

- [x] **Step 5: Verify GREEN for prompt tests**

Run:

```bash
cd tools/new-agents/frontend && npm test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts src/__tests__/p0-fixes.test.ts
```

Expected: both files pass.

### Task 4: Full Frontend Verification

**Files:**
- No production file changes beyond Tasks 1-3.

- [x] **Step 1: Run focused frontend regression suite**

Run:

```bash
cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts src/__tests__/p0-fixes.test.ts
```

Expected: all focused tests pass.

- [x] **Step 2: Run full frontend tests**

Run:

```bash
cd tools/new-agents/frontend && npm test
```

Expected: all frontend tests pass.

- [x] **Step 3: Run frontend type check**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
```

Expected: TypeScript exits 0.

- [x] **Step 4: Run frontend build**

Run:

```bash
cd tools/new-agents/frontend && npm run build
```

Expected: Vite build exits 0. Large chunk warnings may remain because that is a separate performance debt.

### Task 5: Update Debt Record

**Files:**
- Modify: `docs/plans/tech-debt.md`

- [x] **Step 1: Mark stage transition debt as fixed with verification evidence**

Under `2026-06-17 New Agents 当前功能性问题`, update `P0: 工作流无法正确流转到下一环节` with a `修复记录` subsection:

```md
**修复记录**:

- 2026-06-17: 修复 `NEXT_STAGE` chunk 先停止流导致当前阶段最终 artifact 未保存的问题；后续阶段 prompt 改为注入前序阶段 artifact 上下文。
- 验证: `cd tools/new-agents/frontend && npm test`
- 验证: `cd tools/new-agents/frontend && npm run lint`
- 验证: `cd tools/new-agents/frontend && npm run build`
```

- [x] **Step 2: Verify docs diff**

Run:

```bash
git diff -- docs/plans/tech-debt.md docs/superpowers/plans/2026-06-17-new-agents-stage-transition.md
```

Expected: diff only contains the stage-transition fix record and this implementation plan.
