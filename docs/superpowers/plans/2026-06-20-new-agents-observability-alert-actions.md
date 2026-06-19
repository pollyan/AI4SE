# New Agents Observability Alert Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add actionable model configuration recovery controls to the runtime observability provider alert.

**Architecture:** Introduce a small frontend config-check service that normalizes `/new-agents/api/config/check` responses. Header uses that service only for the `provider-issues` observability alert and keeps the existing observability modal structure. The change is frontend-only and does not alter Agent Runtime, SSE, workflow manifests, or backend observability contracts.

**Tech Stack:** React, Zustand, TypeScript, Vitest, Vite.

---

### Task 1: Shared Config Check Service

**Files:**
- Create: `tools/new-agents/frontend/src/services/configService.ts`
- Create: `tools/new-agents/frontend/src/services/__tests__/configService.test.ts`

- [ ] **Step 1: Write failing service tests**

Create `configService.test.ts` with tests:
- `checks default model connectivity with backend message fallback`
- `uses backend error text when model connectivity check fails`
- `uses default failure text when the config check request rejects`

The tests should mock `global.fetch`, call `checkDefaultLlmConfig()`, and assert:
- success response `{ ok: true, message: '模型配置可用' }` returns `{ ok: true, message: '模型配置可用' }`;
- HTTP failure with `{ error: 'API Key 无效' }` returns `{ ok: false, message: 'API Key 无效' }`;
- rejected fetch returns `{ ok: false, message: '模型连接检测失败' }`.

- [ ] **Step 2: Verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/configService.test.ts
```

Expected: FAIL because `configService.ts` does not exist.

- [ ] **Step 3: Implement service**

Add:

```ts
export type ConfigCheckResult = {
  ok: boolean;
  message: string;
};

const readString = (value: unknown): string | null => (
  typeof value === 'string' && value.trim() ? value.trim() : null
);

export const checkDefaultLlmConfig = async (): Promise<ConfigCheckResult> => {
  try {
    const response = await fetch('/new-agents/api/config/check', { method: 'POST' });
    let data: { ok?: unknown; message?: unknown; error?: unknown } = {};
    try {
      data = await response.json();
    } catch {
      data = {};
    }
    const ok = response.ok && data.ok !== false;
    return {
      ok,
      message: readString(data.message)
        || readString(data.error)
        || (ok ? '模型配置可用' : '模型连接检测失败'),
    };
  } catch {
    return { ok: false, message: '模型连接检测失败' };
  }
};
```

- [ ] **Step 4: Verify GREEN**

Run the service test command again. Expected: PASS.

### Task 2: Header Observability Provider Alert Actions

**Files:**
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [ ] **Step 1: Write failing Header tests**

Add tests:
- `opens settings from provider issue observability alert`
- `checks model connectivity from observability provider alert`
- `shows model connectivity check failure from observability provider alert`

Test shape:
- Mock `checkDefaultLlmConfig` from `../../services/configService`.
- Use existing `OBSERVABILITY_SUMMARY` fixture because it includes `providerIssueCount: 1`.
- Open `更多操作` -> `运行统计`.
- Assert `打开模型设置` and `检测连接` appear inside alert area.
- Clicking `打开模型设置` should make `useStore.getState().isSettingsOpen` true.
- Clicking `检测连接` should call `checkDefaultLlmConfig` and render the returned message.

- [ ] **Step 2: Verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx -t "observability provider alert"
```

Expected: FAIL because Header has no provider alert actions.

- [ ] **Step 3: Implement Header actions**

Implementation constraints:
- Import `checkDefaultLlmConfig`.
- Add local state for provider alert check result, e.g. `{ status: 'idle' | 'checking' | 'success' | 'error'; message: string | null }`.
- Add `handleOpenSettingsFromObservabilityAlert` that calls `setSettingsOpen(true)`.
- Add `handleCheckProviderConfigFromObservabilityAlert` that sets checking state, awaits `checkDefaultLlmConfig`, then renders success/error.
- Render the buttons only when `alert.id === 'provider-issues'`.
- Keep other alert cards unchanged.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/configService.test.ts src/components/__tests__/Header.test.tsx
```

Expected: PASS.

### Task 3: Todo And Quality Gates

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: Update todo progress**

Append under P1 #6:
- slice name: `运行统计供应商告警动作链`
- result: provider issue alert can open settings and run connection check.
- verification commands.
- remaining: DOCX/PDF visual export and Artifact merge enhancements remain separate.

- [ ] **Step 2: Run final gates**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

- [ ] **Step 3: Commit**

Commit:

```bash
git add docs/todos/new-agents-ux-professionalization.md docs/superpowers/plans/2026-06-20-new-agents-observability-alert-actions.md docs/superpowers/specs/2026-06-20-new-agents-observability-alert-actions-design.md tools/new-agents/frontend/src/components/Header.tsx tools/new-agents/frontend/src/components/__tests__/Header.test.tsx tools/new-agents/frontend/src/services/configService.ts tools/new-agents/frontend/src/services/__tests__/configService.test.ts
git commit -m "feat(new-agents): 增强运行统计模型告警操作"
```
