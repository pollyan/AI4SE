# DeepSeek V4 Prompt Boundary Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让已迁移 `artifact_data` stage 的前端 system prompt 不再要求 DeepSeek 输出 Markdown/mark/artifact_update，从 prompt 源头减少格式化冲突。

**Architecture:** 只改前端 prompt builder 的文案边界和测试，不新增 runtime/API/store/renderer。后端仍通过共享 Agent Runtime、typed SSE、artifact contract、renderer registry 和 persistence 交付最终 Markdown artifact。

**Tech Stack:** React/TypeScript、Vitest、Python 3.11、pytest。

---

### Task 1: 写 RED 测试证明 artifact_data stage 仍注入旧格式化要求

**Files:**
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`

- [x] **Step 1: 添加失败测试**

在 `buildSystemPrompt.test.ts` 中新增测试:

```ts
it('does not ask migrated artifact_data stages to format markdown artifacts', () => {
    const prompt = buildSystemPrompt({
        agentId: 'lisa',
        workflow: 'TEST_DESIGN',
        stageIndex: 0,
        currentArtifact: '# 需求分析文档\n已有内容',
    });

    expect(prompt).not.toContain('<mark>');
    expect(prompt).not.toContain('artifact_update');
    expect(prompt).not.toContain('必须提供完整、全部的 Markdown 文档内容');
    expect(prompt).not.toContain('```markdown');
    expect(prompt).toContain('当前工作流：测试设计');
    expect(prompt).toContain('当前阶段：需求澄清');
    expect(prompt).toContain('target_stage_id');
});
```

- [x] **Step 2: 运行 RED 测试**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected: 新测试失败，失败原因是当前 prompt 仍包含 `<mark>`、`artifact_update` 或 Markdown 完整产物规则。

### Task 2: 实现 artifact_data stage 数据模式 prompt

**Files:**
- Modify: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`

- [x] **Step 1: 新增 artifact_data stage 判断**

在 `buildSystemPrompt.ts` 增加 `ARTIFACT_DATA_STAGE_IDS` 和 `isArtifactDataStage()`:

```ts
const ARTIFACT_DATA_STAGE_IDS: Record<WorkflowType, ReadonlySet<string>> = {
    TEST_DESIGN: new Set(['CLARIFY', 'STRATEGY', 'CASES', 'DELIVERY']),
    REQ_REVIEW: new Set(['REVIEW', 'REPORT']),
    INCIDENT_REVIEW: new Set(['TIMELINE', 'ROOT_CAUSE', 'IMPROVEMENT']),
    IDEA_BRAINSTORM: new Set(['DEFINE', 'DIVERGE', 'CONVERGE', 'CONCEPT']),
    VALUE_DISCOVERY: new Set(['ELEVATOR', 'PERSONA', 'JOURNEY', 'BLUEPRINT']),
};

const isArtifactDataStage = (workflow: WorkflowType, stageId: string): boolean =>
    ARTIFACT_DATA_STAGE_IDS[workflow]?.has(stageId) ?? false;
```

- [x] **Step 2: 分离 Markdown 模式和数据模式文案**

当 `isArtifactDataStage(workflow, currentStage.id)` 为 `true` 时:

```ts
const artifactUpdateInstruction = '当前阶段已迁移为结构化业务数据模式；不要输出或维护 Markdown 产物正文，也不要使用 artifact_update。后端会根据 artifact_data 确定性渲染右侧产出物。';
const artifactContext = `当前右侧产物参考内容（后端已渲染，仅用于理解上下文，不要复制、补齐或回写 Markdown）：\n${cleanArtifact || '暂无已渲染产物。'}`;
```

Markdown 兼容路径保留原有 `<mark>` 和完整 Markdown 更新规则。

- [x] **Step 3: 扩展测试覆盖全部在线 migrated stage**

在测试中遍历代表性 workflow/stage，至少覆盖 `TEST_DESIGN/CLARIFY` 和 `VALUE_DISCOVERY/BLUEPRINT`，确认数据模式 prompt 不含旧格式化要求且保留 stage context。

- [x] **Step 4: 运行前端 GREEN 测试**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected: prompt 测试通过。

### Task 3: 后端与文档回归

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [x] **Step 1: 更新 DeepSeek todo**

在“当前进展”加入:

```md
- 2026-06-23 已完成 prompt 边界去格式化闭环: 已迁移 `artifact_data` stage 的前端 system prompt 不再注入 `<mark>`、`artifact_update` 或完整 Markdown 重写要求，避免与后端 DeepSeek `artifact_data` 指令冲突。
```

- [x] **Step 2: 运行后端扩展验证**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_deepseek_v4_readiness.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: 全部通过。

- [x] **Step 3: 运行 whitespace 检查**

Run:

```bash
git diff --check
```

Expected: exit 0，无输出。

- [x] **Step 4: 提交**

Run:

```bash
git add tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md docs/superpowers/specs/2026-06-23-deepseek-v4-prompt-boundary-hardening-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-prompt-boundary-hardening.md
git commit -m "fix: 收束 DeepSeek 结构化输出 prompt 边界"
```

Expected: 单一聚焦 commit 形成。
