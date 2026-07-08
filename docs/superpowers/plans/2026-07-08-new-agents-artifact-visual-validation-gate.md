# New Agents Artifact Visual Validation Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 New Agents 前端写入正式或流式 artifact 前校验 `ai4se-visual` fenced block，失败时显式阻断并保留原产物。

**Architecture:** 复用现有 `parseStructuredVisual()`，在 `structuredVisuals.ts` 提供 Markdown fenced block 提取和校验函数；`llm.ts` 在 final 与 partial artifact chunk yield 前统一校验 Mermaid 和 `ai4se-visual`；`chatService` 将该错误归类为结构化输出失败。

**Tech Stack:** React 19、TypeScript、Vitest、New Agents typed Agent Runtime SSE。

---

### Task 1: `ai4se-visual` Markdown 校验工具

**Files:**
- Modify: `tools/new-agents/frontend/src/core/structuredVisuals.ts`
- Test: `tools/new-agents/frontend/src/core/__tests__/structuredVisuals.test.ts`

- [ ] **Step 1: Write failing extractor and validator tests**

Add tests that expect these exports to exist:

```ts
import {
    extractStructuredVisualBlocks,
    parseStructuredVisual,
    validateStructuredVisualBlocks,
} from '../structuredVisuals';

it('extracts fenced ai4se-visual blocks from markdown', () => {
    const blocks = extractStructuredVisualBlocks([
        '# 文档',
        '```ai4se-visual',
        '{"type":"score-matrix","columns":["维度"],"rows":[{"维度":"价值"}]}',
        '```',
        '```json',
        '{"type":"not-visual"}',
        '```',
        '```ai4se-visual',
        '{"type":"roadmap","columns":["版本"],"rows":[{"版本":"MVP"}]}',
        '```',
    ].join('\n'));

    expect(blocks).toHaveLength(2);
    expect(blocks[0]).toContain('"score-matrix"');
    expect(blocks[1]).toContain('"roadmap"');
});

it('validates all fenced ai4se-visual blocks in markdown', () => {
    expect(() => validateStructuredVisualBlocks([
        '```ai4se-visual',
        '{"type":"score-matrix","columns":["维度"],"rows":[{"维度":"价值"}]}',
        '```',
        '',
        '```ai4se-visual',
        '{"type":"cause-map","nodes":[{"id":"Why-1","label":"Why-1","title":"直接原因"}],"edges":[]}',
        '```',
    ].join('\n'))).not.toThrow();
});

it('rejects malformed ai4se-visual blocks before artifact write', () => {
    expect(() => validateStructuredVisualBlocks([
        '```ai4se-visual',
        '{ broken',
        '```',
    ].join('\n'))).toThrow(
        'Artifact structured visual validation failed: 结构化可视化必须是合法 JSON。'
    );
});

it('rejects cause-map blocks with missing edge targets before artifact write', () => {
    expect(() => validateStructuredVisualBlocks([
        '```ai4se-visual',
        '{"type":"cause-map","nodes":[{"id":"Why-1","label":"Why-1","title":"直接原因"}],"edges":[{"source":"Why-1","target":"Why-404"}]}',
        '```',
    ].join('\n'))).toThrow(
        'Artifact structured visual validation failed: cause-map edge 引用了不存在的节点：Why-1 -> Why-404。'
    );
});
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/structuredVisuals.test.ts
```

Expected: fails because `extractStructuredVisualBlocks` and `validateStructuredVisualBlocks` are not exported.

- [ ] **Step 3: Implement Markdown visual extraction and validation**

Add to `structuredVisuals.ts`:

```ts
export function extractStructuredVisualBlocks(markdown: string): string[] {
    const blocks: string[] = [];
    const visualBlockPattern = /```ai4se-visual(?:[ \t].*)?\n([\s\S]*?)```/gi;
    let match = visualBlockPattern.exec(markdown);
    while (match) {
        const source = match[1].trim();
        if (source) blocks.push(source);
        match = visualBlockPattern.exec(markdown);
    }
    return blocks;
}

export function validateStructuredVisualBlocks(markdown: string): void {
    for (const block of extractStructuredVisualBlocks(markdown)) {
        const result = parseStructuredVisual(block);
        if (!result.valid) {
            throw new Error(`Artifact structured visual validation failed: ${result.message}`);
        }
    }
}
```

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/structuredVisuals.test.ts
```

Expected: all tests in the file pass.

### Task 2: Agent Runtime 前端写入前视觉 gate

**Files:**
- Modify: `tools/new-agents/frontend/src/core/llm.ts`
- Test: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`

- [ ] **Step 1: Write failing SSE tests**

Add focused tests under the structured Agent Runtime describe block:

```ts
it('rejects final artifacts with invalid ai4se-visual before yielding chunks', async () => {
    resetStore({
        workflow: 'VALUE_DISCOVERY',
        stageIndex: 0,
        artifactContent: '# 价值定位分析\n\n初始内容',
        stageArtifacts: { ELEVATOR: '# 价值定位分析\n\n初始内容' },
    });
    mockFetch.mockResolvedValueOnce({
        ok: true,
        body: createSSEStream([
            `data: ${JSON.stringify({
                type: 'agent_turn',
                output: {
                    chat: '已更新价值定位。',
                    artifact_update: {
                        type: 'replace',
                        markdown: [
                            '# 价值定位分析',
                            '```ai4se-visual',
                            '{ broken',
                            '```',
                        ].join('\n'),
                    },
                    stage_action: null,
                    warnings: [],
                },
            })}`,
            'data: [DONE]',
        ]),
    });

    await expect(collectStream(generateResponseStream('继续'))).rejects.toThrow(
        'Artifact structured visual validation failed: 结构化可视化必须是合法 JSON。'
    );
});

it('rejects partial artifact deltas with invalid ai4se-visual before yielding chunks', async () => {
    resetStore({
        workflow: 'VALUE_DISCOVERY',
        stageIndex: 0,
        artifactContent: '# 价值定位分析\n\n初始内容',
        stageArtifacts: { ELEVATOR: '# 价值定位分析\n\n初始内容' },
    });
    mockFetch.mockResolvedValueOnce({
        ok: true,
        body: createSSEStream([
            'data: {"type":"run_started"}',
            createAgentDeltaEvent({
                chat: '正在生成价值定位。',
                artifact_update: {
                    type: 'replace',
                    markdown: [
                        '# 价值定位分析',
                        '```ai4se-visual',
                        '{"type":"cause-map","nodes":[{"id":"Why-1","label":"Why-1","title":"直接原因"}],"edges":[{"source":"Why-1","target":"Why-404"}]}',
                        '```',
                    ].join('\n'),
                },
            }),
        ]),
    });

    await expect(collectStream(generateResponseStream('继续'))).rejects.toThrow(
        'Artifact structured visual validation failed: cause-map edge 引用了不存在的节点：Why-1 -> Why-404。'
    );
});
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts -t "ai4se-visual"
```

Expected: new tests fail because invalid `ai4se-visual` artifacts are yielded instead of rejected.

- [ ] **Step 3: Implement shared artifact visual validation in `llm.ts`**

Import the new validator:

```ts
import { validateStructuredVisualBlocks } from './structuredVisuals';
```

Add:

```ts
const validateArtifactVisualBlocks = async (markdown: string): Promise<void> => {
  validateStructuredVisualBlocks(markdown);
  await validateMermaidBlocks(markdown);
};
```

Replace every `await validateMermaidBlocks(newArtifact)` call in artifact write paths with:

```ts
await validateArtifactVisualBlocks(newArtifact);
```

In `mapAgentDeltaToStreamChunks()`, add before yielding:

```ts
if (hasArtifactUpdate) {
  await validateArtifactVisualBlocks(newArtifact);
}
```

- [ ] **Step 4: Run GREEN and focused regression**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts -t "ai4se-visual"
```

Expected: selected tests pass.

Then run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/core/__tests__/structuredVisuals.test.ts
```

Expected: both files pass.

### Task 3: Chat service recovery classification

**Files:**
- Modify: `tools/new-agents/frontend/src/services/chatService.ts`
- Test: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`

- [ ] **Step 1: Write failing chat service test**

Add a test next to existing artifact validation failure cases:

```ts
it('keeps artifact unchanged when structured visual validation fails', async () => {
    const originalArtifact = 'initial artifact';
    useStore.setState({
        artifactContent: originalArtifact,
        artifactHistory: [],
    });
    mockGenerateResponseStream.mockImplementationOnce(async function* () {
        throw new Error('Artifact structured visual validation failed: 结构化可视化必须是合法 JSON。');
    });

    await chatService.sendMessage('继续生成');

    const state = useStore.getState();
    expect(state.chatHistory[1].content).toContain('结构化输出生成失败');
    expect(state.chatHistory[1].content).toContain('右侧产出物已保持不变');
    expect(state.artifactContent).toBe(originalArtifact);
    expect(state.artifactHistory).toEqual([]);
});
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/chatService.test.ts -t "structured visual validation"
```

Expected: fails because `Artifact structured visual validation failed` is not mapped to structured artifact recovery.

- [ ] **Step 3: Extend error classification**

In `chatService.ts`, extend the existing artifact validation condition:

```ts
|| errorMessage.includes('Artifact structured visual validation failed')
```

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/chatService.test.ts -t "structured visual validation"
```

Expected: selected test passes.

### Task 4: Documentation, regression, and commit

**Files:**
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- Modify: current spec and plan files if verification evidence changes.

- [ ] **Step 1: Run focused frontend regression**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/structuredVisuals.test.ts src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/StructuredVisual.test.tsx
```

Expected: selected frontend regression passes.

- [ ] **Step 2: Run frontend type check**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
```

Expected: TypeScript `tsc --noEmit` passes.

- [ ] **Step 3: Update todo execution record**

Record:

- RED failures for structured visual tests.
- GREEN focused results.
- Whether `agent_delta` partial visual validation is covered.
- Residual risk: backend still does not run Mermaid JS parse; CI / `mmdc` rendering gate remains a later candidate.

- [ ] **Step 4: Run New Agents batch validation**

Run:

```bash
./scripts/test/test-local.sh new-agents
```

Expected: New Agents frontend and backend suites pass. Existing React `act(...)` warnings are acceptable only if tests exit 0.

- [ ] **Step 5: Run full local automation before commit**

Run:

```bash
./scripts/test/test-local.sh all
```

Expected: pass. If sandbox blocks MidScene proxy or Playwright, rerun non-sandbox with an output log and record the environment reason.

- [ ] **Step 6: Commit and push**

Before staging, run:

```bash
git status -sb
git diff --shortstat
git diff --cached --name-only
```

Stage only this slice:

```bash
git add docs/superpowers/specs/2026-07-08-new-agents-artifact-visual-validation-gate-design.md docs/superpowers/plans/2026-07-08-new-agents-artifact-visual-validation-gate.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md tools/new-agents/frontend/src/core/structuredVisuals.ts tools/new-agents/frontend/src/core/__tests__/structuredVisuals.test.ts tools/new-agents/frontend/src/core/llm.ts tools/new-agents/frontend/src/core/__tests__/llm.test.ts tools/new-agents/frontend/src/services/chatService.ts tools/new-agents/frontend/src/services/__tests__/chatService.test.ts
git commit -m "fix(new-agents): 阻断无效结构化视觉写入"
git push
```
