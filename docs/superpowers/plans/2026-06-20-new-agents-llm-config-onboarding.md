# New Agents 首次模型配置自检与修复闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让默认 LLM 缺失的用户可以在 New Agents 工作区内直接完成配置、保存、连接检测和阻断解除。

**Architecture:** 继续复用全局 `SettingsModal` 和后端 `/new-agents/api/config` 契约。新增一个轻量的前端 store 事件计数器，用于让 `SettingsModal` 保存/检测成功后通知 `Workspace` 重新检查默认配置，不进入持久化 snapshot，也不引入 workflow-specific 模型分支。

**Tech Stack:** React 19、Zustand store、Vitest、Testing Library、Flask 既有 config API。

---

## 文件职责

- `tools/new-agents/frontend/src/store.ts`：新增非持久化 `configRefreshSeq` 和 `notifyDefaultLlmConfigChanged` action。
- `tools/new-agents/frontend/src/pages/Workspace.tsx`：把默认 LLM 配置检查抽成可复用函数；遮罩提供打开设置和重新检查；监听 `configRefreshSeq` 后复检。
- `tools/new-agents/frontend/src/components/SettingsModal.tsx`：保存成功或检测成功后调用 `notifyDefaultLlmConfigChanged`。
- `tools/new-agents/frontend/src/pages/__tests__/Workspace.test.tsx`：覆盖缺配置遮罩打开设置、手动复检、保存后自动关闭。
- `tools/new-agents/frontend/src/components/__tests__/SettingsModal.test.tsx`：覆盖保存成功和检测成功通知 store。
- `docs/todos/new-agents-ux-professionalization.md`：记录本轮完成和验证。

## 预计 commit 边界

- 一个聚焦 commit：`feat(new-agents): 打通首次模型配置修复闭环`
- 包含前端代码、测试、spec、plan 和 todo 记录。若 diff 超过 playbook 阈值，再按“测试+store/Workspace”和“Settings/todo”拆 checkpoint。

### Task 1: RED - Workspace 首次配置闭环测试

**Files:**
- Modify: `tools/new-agents/frontend/src/pages/__tests__/Workspace.test.tsx`

- [ ] **Step 1: 写失败测试**

新增测试覆盖三件事：

```tsx
it('opens model settings from the missing default LLM onboarding overlay', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ hasDefault: false }) });
    render(<BrowserRouter><Workspace /></BrowserRouter>);

    expect(await screen.findByText(/后端默认 LLM 未配置/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '打开模型设置' }));

    expect(useStore.getState().isSettingsOpen).toBe(true);
});
```

新增保存成功后重新检查的测试：

```tsx
it('hides onboarding after settings report a usable default LLM config', async () => {
    mockFetch
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ hasDefault: false }) })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ hasDefault: true }) });
    render(<BrowserRouter><Workspace /></BrowserRouter>);

    expect(await screen.findByText(/后端默认 LLM 未配置/)).toBeTruthy();
    act(() => {
        useStore.getState().notifyDefaultLlmConfigChanged();
    });

    await waitFor(() => {
        expect(screen.queryByText(/后端默认 LLM 未配置/)).toBeNull();
    });
});
```

- [ ] **Step 2: 运行 RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/Workspace.test.tsx
```

Expected: FAIL，原因是 overlay 没有 `打开模型设置`，store 也没有 `notifyDefaultLlmConfigChanged`。

### Task 2: RED - SettingsModal 成功通知测试

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/SettingsModal.test.tsx`

- [ ] **Step 1: 写失败测试**

新增保存成功通知测试：

```tsx
it('notifies workspace after saving default backend config', async () => {
    const notifySpy = vi.fn();
    useStore.setState({ notifyDefaultLlmConfigChanged: notifySpy });
    // mock GET false, POST true，填写表单并点击保存配置
    expect(notifySpy).toHaveBeenCalledTimes(1);
});
```

新增检测成功通知测试：

```tsx
it('notifies workspace after a successful model connectivity check', async () => {
    const notifySpy = vi.fn();
    useStore.setState({ notifyDefaultLlmConfigChanged: notifySpy });
    // mock GET true, POST /config/check ok true，点击检测连接
    expect(notifySpy).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 2: 运行 RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/SettingsModal.test.tsx
```

Expected: FAIL，原因是 `SettingsModal` 还没有读取或调用该 store action。

### Task 3: GREEN - Store 和 Workspace 配置复检

**Files:**
- Modify: `tools/new-agents/frontend/src/store.ts`
- Modify: `tools/new-agents/frontend/src/pages/Workspace.tsx`

- [ ] **Step 1: store 增加轻量事件**

在 store state 类型中加入：

```ts
configRefreshSeq: number;
notifyDefaultLlmConfigChanged: () => void;
```

实现：

```ts
configRefreshSeq: 0,
notifyDefaultLlmConfigChanged: () => set((state) => ({
  configRefreshSeq: state.configRefreshSeq + 1,
})),
```

不要把这个字段写入任何持久化 snapshot。

- [ ] **Step 2: Workspace 监听并复检**

在 `Workspace` 读取 `isSettingsOpen`、`setSettingsOpen` 和 `configRefreshSeq`。将 config check 抽成 `checkDefaultConfig`，在以下场景调用：

- 首次进入且 `chatHistory.length === 0`。
- `configRefreshSeq` 增加时。
- 用户点击 overlay 的 `重新检查配置`。

overlay 增加：

- `打开模型设置`：调用 `setSettingsOpen(true)`。
- `重新检查配置`：调用同一个 config check。
- 检查中显示 `正在检查默认模型配置...`。

- [ ] **Step 3: 运行 GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/Workspace.test.tsx
```

Expected: PASS。

### Task 4: GREEN - SettingsModal 通知 Workspace

**Files:**
- Modify: `tools/new-agents/frontend/src/components/SettingsModal.tsx`

- [ ] **Step 1: 保存成功通知**

从 store 取出 `notifyDefaultLlmConfigChanged`，在 `handleSaveConfig` 成功后调用一次。

- [ ] **Step 2: 检测成功通知**

在 `handleCheckConfig` 中，只有 `data.ok === true` 时调用 `notifyDefaultLlmConfigChanged`。检测失败只显示错误，不触发 overlay 关闭。

- [ ] **Step 3: 运行 GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/SettingsModal.test.tsx
```

Expected: PASS。

### Task 5: 文档记录与验证

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: 更新 todo**

在 P1 #6 进展记录追加“首次模型配置自检与修复闭环”，写明：

- 缺配置 overlay 可打开模型设置并重新检查。
- Settings 保存/检测成功会触发 Workspace 复检。
- 不新增 workflow-specific 模型分支。
- 验证命令。

- [ ] **Step 2: 聚焦验证**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/Workspace.test.tsx src/components/__tests__/SettingsModal.test.tsx
```

Expected: PASS。

- [ ] **Step 3: 扩大验证**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/configService.test.ts src/components/__tests__/Header.test.tsx src/components/__tests__/ChatPane.test.tsx
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

Expected: all PASS。

- [ ] **Step 4: 提交**

Run:

```bash
git add docs/superpowers/specs/2026-06-20-new-agents-llm-config-onboarding-design.md docs/superpowers/plans/2026-06-20-new-agents-llm-config-onboarding.md docs/todos/new-agents-ux-professionalization.md tools/new-agents/frontend/src/store.ts tools/new-agents/frontend/src/pages/Workspace.tsx tools/new-agents/frontend/src/pages/__tests__/Workspace.test.tsx tools/new-agents/frontend/src/components/SettingsModal.tsx tools/new-agents/frontend/src/components/__tests__/SettingsModal.test.tsx
git commit -m "feat(new-agents): 打通首次模型配置修复闭环"
```
