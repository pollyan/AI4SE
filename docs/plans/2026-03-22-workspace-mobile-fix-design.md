# Design Doc: Workspace 移动端显示逻辑修复

## 背景

**问题：** ChatPane 在手机端完全不显示（内容区全黑）。根因是 clsx 条件逻辑写反了。

## 根因分析

### 当前代码（错误）
```tsx
<section className={clsx(
    "flex flex-col w-full lg:w-[40%] bg-[#0B1120] ...",
    mobileTab !== 'chat' && "md:hidden",  // ❌ 逻辑反了
    "hidden md:flex"                      // ❌ 永远生效
)}>
```

当 `mobileTab === 'chat'` 时：
- `mobileTab !== 'chat'` → `false`，`"md:hidden"` 不生效
- `"hidden md:flex"` **永远生效**
- 结果：手机上 classes = `hidden md:flex` → **ChatPane 被 hidden**

### 正确逻辑
- `mobileTab === 'chat'` → 手机端显示（`flex`），桌面端隐藏（`md:hidden`）
- `mobileTab !== 'chat'` → 手机端隐藏（`hidden`），桌面端显示（`md:flex`）

## 修复方案

### Workspace.tsx 修改

**ChatPane section:**
```tsx
<section className={clsx(
    "flex flex-col w-full lg:w-[40%] bg-[#0B1120] border-r border-[#1e293b] relative shadow-[10px_0_30px_-10px_rgba(0,0,0,0.5)] z-20 h-full",
    mobileTab === 'chat' ? "flex md:hidden" : "hidden md:flex"
)}>
```

**ArtifactPane section:**
```tsx
<section className={clsx(
    "flex flex-col w-full lg:w-[60%] bg-[#0B0F17] text-gray-300 relative shadow-2xl overflow-hidden bg-grid-pattern h-full",
    mobileTab === 'artifact' ? "flex md:hidden" : "hidden md:flex"
)}>
```

---

## 风险评估

- **风险:** 低
- **影响范围:** 仅 Workspace.tsx 的 className 条件
- **回滚:** `git revert`

---

## 验收标准

- [ ] 手机端 (375px) `mobileTab === 'chat'` 时，ChatPane 全屏显示
- [ ] 手机端 (375px) `mobileTab === 'artifact'` 时，ArtifactPane 全屏显示
- [ ] 桌面端 (1024px+) 左右分栏显示
- [ ] `npm run build` 通过
