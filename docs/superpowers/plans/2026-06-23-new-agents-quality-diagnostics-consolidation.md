# New Agents Quality Diagnostics Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已完成的 Artifact 质量诊断面板合流到最新 DeepSeek 结构化输出基线。

**Architecture:** 保持共享 New Agents 前端、ArtifactPane、typed SSE、manifest-derived contract 和现有 visual diagnostic store。通过 cherry-pick 合入 E03，不新增 agent-specific runtime、API、store 或 renderer。

**Tech Stack:** React 19、TypeScript 5.8、Vitest、Python 3.11、pytest、Git worktree/cherry-pick。

---

### Task 1: 记录红灯验收

**Files:**
- Read: `tools/new-agents/frontend/src/core/artifactQuality.ts`
- Read: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

- [x] **Step 1: 创建隔离 worktree**

Run:

```bash
git worktree add .worktrees/new-agents-quality-diagnostics-consolidation -b codex/new-agents-quality-diagnostics-consolidation codex/deepseek-prompt-boundary-hardening
```

Expected: worktree 干净，HEAD 为 `768a1718`。

- [x] **Step 2: 验证 E03 尚未合入**

Run:

```bash
git cherry HEAD codex/artifact-quality-diagnostics
test -f tools/new-agents/frontend/src/core/artifactQuality.ts
```

Expected: `git cherry` 输出 `+ a74cff03...`，`test -f` 返回非 0。

### Task 2: 合入 E03

**Files:**
- Create: `tools/new-agents/frontend/src/core/artifactQuality.ts`
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Create/Modify: `tools/new-agents/frontend/src/core/__tests__/artifactQuality.test.ts`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

- [x] **Step 1: Cherry-pick E03 commit**

Run:

```bash
git cherry-pick a74cff03
```

Expected: E03 files enter the branch. If todo conflicts, preserve both latest DS-related context and E03 completion text.

- [x] **Step 2: Inspect conflicts**

Run:

```bash
rg "<<<<<<<|>>>>>>>" docs tools
```

Expected: no conflict markers remain.

### Task 3: 验证合流后的前端行为

**Files:**
- Test: `tools/new-agents/frontend/src/core/__tests__/artifactQuality.test.ts`
- Test: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
- Test: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`

- [x] **Step 1: Run focused frontend tests**

Run:

```bash
npm run test -- --run src/core/__tests__/artifactQuality.test.ts src/components/__tests__/ArtifactPane.test.tsx src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected: tests pass.

- [x] **Step 2: Run TypeScript check**

Run:

```bash
npm run lint
```

Expected: `tsc --noEmit` passes.

### Task 4: 验证 DeepSeek 后端回归

**Files:**
- Test: `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`
- Test: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Test: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`

- [x] **Step 1: Run backend regression**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_deepseek_v4_readiness.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: tests pass.

- [x] **Step 2: Run whitespace check**

Run:

```bash
git diff --check
```

Expected: exit 0 with no output.

### Task 5: 提交整合结果

**Files:**
- Modify: all files introduced by E03 and this integration plan/spec.

- [x] **Step 1: Stage files**

Run:

```bash
git add tools/new-agents/frontend/src/core/artifactQuality.ts tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/__tests__/artifactQuality.test.ts tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/superpowers/specs/2026-06-23-new-agents-quality-diagnostics-consolidation-design.md docs/superpowers/plans/2026-06-23-new-agents-quality-diagnostics-consolidation.md
```

Expected: only本轮整合相关文件 staged。

- [x] **Step 2: Commit**

Run:

```bash
git commit -m "chore: 合流产物质量诊断到 DeepSeek 基线"
```

Expected: 聚焦 commit 形成，worktree clean。
