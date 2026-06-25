# New Agents 前端 Artifact Patch 流消费 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让前端 typed Agent Runtime 流能校验、传递并消费可选 `artifact_patch`，成功时局部应用，失败时用完整 Markdown fallback。

**Architecture:** `llm.ts` 负责 SSE contract 校验和 chunk 搬运；`agentCore.ts` 负责把 chunk 规约成 artifact update decision；`chatService.ts` 负责调用 store patch action，并保留完整 markdown 替换路径作为事实源和 fallback。

**Tech Stack:** TypeScript、Vitest、React Testing Library hook tests。

---

## File Structure

- Modify: `tools/new-agents/frontend/src/core/llm.ts`
  - 增加 `artifact_patch` 类型、校验、final chunk 搬运。
- Modify: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
  - 覆盖合法 patch chunk 和非法 patch contract。
- Modify: `tools/new-agents/frontend/src/core/agentCore.ts`
  - `AgentStreamChunk` / `AgentArtifactUpdateDecision` 携带 patch。
- Modify: `tools/new-agents/frontend/src/core/__tests__/agentCore.test.ts`
  - 覆盖 reducer 保留 patch。
- Modify: `tools/new-agents/frontend/src/services/chatService.ts`
  - patch 优先，失败或锁定时 full markdown fallback。
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`
  - 覆盖 patch 成功和 patch/full mismatch fallback。
- Modify: `docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md`
  - 记录本切片进展。

## Task 1: LLM Parser and Stream Chunk

**Files:**
- Modify: `tools/new-agents/frontend/src/core/llm.ts`
- Modify: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`

- [x] **Step 1: Write failing parser tests**

Add `artifactPatch?: ArtifactSectionPatch` to the local `TestStreamChunk` type in `llm.test.ts`, importing `ArtifactSectionPatch` from `../../store`.

Append near the typed Agent Runtime tests:

```ts
        it('passes artifact_patch through the final structured runtime chunk with full markdown fallback', async () => {
            const base = '# 需求分析文档\n\n## 范围\n\n旧范围';
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 0,
                artifactContent: base,
                stageArtifacts: { CLARIFY: base },
            });
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentTurnEvent({
                        chat: '已局部更新需求分析文档。',
                        artifact_update: {
                            type: 'replace',
                            markdown: '# 需求分析文档\n\n## 范围\n\n新范围',
                        },
                        artifact_patch: {
                            operation: 'replace',
                            sectionAnchor: 'h2:范围:1',
                            replacementMarkdown: '## 范围\n\n新范围',
                            baseContent: base,
                        },
                        stage_action: null,
                        warnings: [],
                    }),
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(generateResponseStream('更新范围'));

            expect(results.at(-1)).toEqual({
                chatResponse: '已局部更新需求分析文档。',
                newArtifact: '# 需求分析文档\n\n## 范围\n\n新范围',
                action: '',
                hasArtifactUpdate: true,
                artifactPatch: {
                    operation: 'replace',
                    sectionAnchor: 'h2:范围:1',
                    replacementMarkdown: '## 范围\n\n新范围',
                    baseContent: base,
                },
            });
        });

        it('rejects malformed artifact_patch payloads in structured runtime events', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"ok","artifact_update":{"type":"replace","markdown":"# 文档"},"artifact_patch":{"operation":"replace","sectionAnchor":"","replacementMarkdown":"## 空"},"stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            await expect(collectStream(generateResponseStream('hi')))
                .rejects
                .toThrow('结构化智能体 SSE 事件格式错误');
        });
```

- [x] **Step 2: Run parser tests and verify red**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/llm.test.ts -t "artifact_patch"
```

Expected: FAIL because chunk does not include `artifactPatch` and malformed patch is not rejected.

- [x] **Step 3: Implement parser / mapper changes**

In `llm.ts`:

- Import `ArtifactSectionPatch`.
- Add `artifactPatch?: ArtifactSectionPatch` to `StreamChunk`.
- Add `artifact_patch?: ArtifactSectionPatch | null` to `AgentTurnOutput` and `AgentTurnDeltaOutput`.
- Add helper `normalizeArtifactPatch(value: unknown): ArtifactSectionPatch | null` that validates operation, sectionAnchor, replacementMarkdown, optional baseContent.
- During `agent_delta` and `agent_turn` validation, normalize patch when present; reject invalid patch; for `agent_turn`, require `artifact_update.type === 'replace'` when patch is present.
- In `mapAgentTurnToStreamChunks`, `mapAgentTurnToFinalChunk`, and `mapAgentTurnToArtifactRevealChunks`, add `...(isFinalChunk && output.artifact_patch ? { artifactPatch: output.artifact_patch } : {})`.

- [x] **Step 4: Run parser tests and verify green**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/llm.test.ts -t "artifact_patch"
```

Expected: PASS.

## Task 2: Agent Core Reducer

**Files:**
- Modify: `tools/new-agents/frontend/src/core/agentCore.ts`
- Modify: `tools/new-agents/frontend/src/core/__tests__/agentCore.test.ts`

- [x] **Step 1: Write failing reducer test**

Append inside `describe('reduceAgentStreamChunk', ...)`:

```ts
    it('preserves artifact patches on artifact update decisions', () => {
        const patch = {
            operation: 'replace' as const,
            sectionAnchor: 'h2:范围:1',
            replacementMarkdown: '## 范围\n\n新范围',
            baseContent: '# 文档\n\n## 范围\n\n旧范围',
        };

        const decision = reduceAgentStreamChunk(
            {
                chatResponse: '已局部更新。',
                newArtifact: '# 文档\n\n## 范围\n\n新范围',
                action: '',
                hasArtifactUpdate: true,
                artifactPatch: patch,
            },
            {
                stageIndex: 0,
                stageCount: 4,
                currentStageId: 'CLARIFY',
                hasTransitioned: false,
            }
        );

        expect(decision.artifactUpdate).toEqual({
            stageId: 'CLARIFY',
            content: '# 文档\n\n## 范围\n\n新范围',
            patch,
        });
    });
```

- [x] **Step 2: Run reducer test and verify red**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/agentCore.test.ts -t "artifact patches"
```

Expected: FAIL because reducer drops patch.

- [x] **Step 3: Implement reducer changes**

In `agentCore.ts`:

- Import `ArtifactSectionPatch`.
- Add `artifactPatch?: ArtifactSectionPatch` to `AgentStreamChunk`.
- Add `patch?: ArtifactSectionPatch` to `AgentArtifactUpdateDecision`.
- When returning `artifactUpdate`, spread `...(chunk.artifactPatch ? { patch: chunk.artifactPatch } : {})`.

- [x] **Step 4: Run reducer test and verify green**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/agentCore.test.ts -t "artifact patches"
```

Expected: PASS.

## Task 3: Chat Service Patch Consumption

**Files:**
- Modify: `tools/new-agents/frontend/src/services/chatService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`

- [x] **Step 1: Write failing chatService tests**

Append near existing artifact stream tests:

```ts
    it('applies matching artifact patches from the stream before falling back to full replacement', async () => {
        const base = '# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n保持不变';
        useStore.setState({
            artifactContent: base,
            stageArtifacts: { CLARIFY: base },
        });
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '已局部更新',
                newArtifact: '# 文档\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变',
                action: '',
                hasArtifactUpdate: true,
                artifactPatch: {
                    operation: 'replace',
                    sectionAnchor: 'h2:范围:1',
                    replacementMarkdown: '## 范围\n\n新范围',
                    baseContent: base,
                },
            };
        });

        const { result } = renderHook(() => useChatService());
        act(() => result.current.setInput('更新范围'));

        await act(async () => {
            await result.current.handleSend();
        });

        expect(useStore.getState().artifactContent).toBe('# 文档\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变');
        expect(useStore.getState().artifactChangeIndex).toEqual([
            expect.objectContaining({ anchor: 'h2:范围:1' }),
        ]);
    });

    it('falls back to full markdown when artifact patch result does not match the full artifact', async () => {
        const base = '# 文档\n\n## 范围\n\n旧范围';
        const fullFallback = '# 文档\n\n## 范围\n\n完整替换结果';
        useStore.setState({
            artifactContent: base,
            stageArtifacts: { CLARIFY: base },
        });
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '已更新',
                newArtifact: fullFallback,
                action: '',
                hasArtifactUpdate: true,
                artifactPatch: {
                    operation: 'replace',
                    sectionAnchor: 'h2:范围:1',
                    replacementMarkdown: '## 范围\n\n局部结果',
                    baseContent: base,
                },
            };
        });

        const { result } = renderHook(() => useChatService());
        act(() => result.current.setInput('更新范围'));

        await act(async () => {
            await result.current.handleSend();
        });

        expect(useStore.getState().artifactContent).toBe(fullFallback);
    });
```

- [x] **Step 2: Run chatService tests and verify red**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/chatService.test.ts -t "artifact patches|artifact patch result"
```

Expected: FAIL because service ignores `artifactPatch`.

- [x] **Step 3: Implement chatService patch preference**

In `chatService.ts`, inside `if (decision.artifactUpdate)`:

- Compute `protectedArtifactContent` exactly as today from full markdown.
- If `decision.artifactUpdate.patch` exists and there are no current stage locks, call `latestState.applyArtifactSectionPatch(...)`.
- Use patch result only when `result.applied && result.content === protectedArtifactContent`.
- Otherwise run the existing full replacement path.

- [x] **Step 4: Run chatService tests and verify green**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/chatService.test.ts -t "artifact patches|artifact patch result"
```

Expected: PASS.

## Task 4: Records, Verification, and Commit

**Files:**
- Modify: active todo and this slice docs.

- [x] **Step 1: Run focused verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/llm.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts -t "artifact_patch|artifact patches|artifact patch result"
```

Expected: PASS.

- [x] **Step 2: Run expanded frontend verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/llm.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run test
```

Expected: all PASS, except any pre-existing warnings should be recorded.

- [x] **Step 3: Update active todo**

Append a progress section for “前端 typed SSE patch 流消费”，including verification and remaining backend emit / memoized rendering work.

- [x] **Step 4: Diff check, stage, commit**

Run:

```bash
git diff --check -- docs/superpowers/specs/2026-06-25-new-agents-artifact-patch-stream-consumption-design.md docs/superpowers/plans/2026-06-25-new-agents-artifact-patch-stream-consumption.md docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md tools/new-agents/frontend/src/core/llm.ts tools/new-agents/frontend/src/core/__tests__/llm.test.ts tools/new-agents/frontend/src/core/agentCore.ts tools/new-agents/frontend/src/core/__tests__/agentCore.test.ts tools/new-agents/frontend/src/services/chatService.ts tools/new-agents/frontend/src/services/__tests__/chatService.test.ts
git add docs/superpowers/specs/2026-06-25-new-agents-artifact-patch-stream-consumption-design.md docs/superpowers/plans/2026-06-25-new-agents-artifact-patch-stream-consumption.md docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md tools/new-agents/frontend/src/core/llm.ts tools/new-agents/frontend/src/core/__tests__/llm.test.ts tools/new-agents/frontend/src/core/agentCore.ts tools/new-agents/frontend/src/core/__tests__/agentCore.test.ts tools/new-agents/frontend/src/services/chatService.ts tools/new-agents/frontend/src/services/__tests__/chatService.test.ts
git diff --cached --check
git commit -m "feat: 消费前端产出物 patch 流"
```

Expected: commit succeeds and existing intent-tester generated files remain unstaged.

## Self-Review

- Spec coverage: parser criteria map to Task 1; reducer criteria map to Task 2; chatService success/fallback criteria map to Task 3; records and CI-equivalent verification map to Task 4.
- Placeholder scan: plan uses concrete paths, tests, implementation steps, commands, and expected outcomes.
- Type consistency: `artifact_patch`, `artifactPatch`, `ArtifactSectionPatch`, and store `applyArtifactSectionPatch(...)` are consistently mapped across layers.
