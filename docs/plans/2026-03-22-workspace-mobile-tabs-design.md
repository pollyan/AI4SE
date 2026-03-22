# Design Doc: Workspace 页面移动端 Tab 切换

## 背景

**问题：** Workspace 页面在手机端显示混乱，ChatPane 和 ArtifactPane 并排导致两边都被压缩到无法使用。

**目标：** 手机端用户可在"对话"和"产出物"两个 Tab 之间切换，每次只显示一个。

---

## 当前问题

| 问题 | 位置 | 说明 |
|------|------|------|
| 并排布局 | Workspace.tsx | `<main>` 直接渲染两个 pane，无移动端适配 |
| ArtifactPane 占据右侧 | ArtifactPane.tsx | `w-full lg:w-[60%]` 导致手机端全宽显示，与 ChatPane 冲突 |

---

## 修复方案

### 核心策略
在 Workspace.tsx 添加移动端 Tab 切换，手机端 (< md) 全屏切换，桌面端保持左右分栏。

### Workspace.tsx 修改

#### 1. 添加状态
```tsx
const [mobileTab, setMobileTab] = useState<'chat' | 'artifact'>('chat');
```

#### 2. 移动端 Tab 切换栏（插入到 `<main>` 后）
```tsx
{/* 移动端 Tab 切换栏 */}
<div className="flex md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#0B1120] border-t border-[#1e293b] px-4 py-2">
  <div className="flex w-full bg-[#0f1623] rounded-xl p-1">
    <button
      onClick={() => setMobileTab('chat')}
      className={clsx(
        "flex-1 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2",
        mobileTab === 'chat'
          ? "bg-blue-600 text-white shadow-md"
          : "text-slate-400 hover:text-white"
      )}
    >
      💬 对话
    </button>
    <button
      onClick={() => setMobileTab('artifact')}
      className={clsx(
        "flex-1 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2",
        mobileTab === 'artifact'
          ? "bg-blue-600 text-white shadow-md"
          : "text-slate-400 hover:text-white"
      )}
    >
      📋 产出物
    </button>
  </div>
</div>
```

#### 3. 修改 ChatPane 容器
```tsx
{/* ChatPane: 手机端全屏，桌面端左 40% */}
<section className={clsx(
  "flex flex-col bg-[#0B1120] border-r border-[#1e293b] relative shadow-[10px_0_30px_-10px_rgba(0,0,0,0.5)] z-20 h-full transition-transform",
  // 移除 min-w-[360px]
  // 手机端全屏显示或隐藏
  "w-full lg:w-[40%]",
  mobileTab !== 'chat' && "md:hidden", // 手机端非 chat tab 时隐藏
  // 平板以上始终显示
  "hidden md:flex"
)}>
```

#### 4. 修改 ArtifactPane 容器
```tsx
{/* ArtifactPane: 手机端全屏，桌面端右 60% */}
<section className={clsx(
  "flex flex-col bg-[#0B0F17] text-gray-300 relative shadow-2xl overflow-hidden bg-grid-pattern h-full",
  // 手机端全屏显示或隐藏
  "w-full lg:w-[60%]",
  mobileTab !== 'artifact' && "md:hidden", // 手机端非 artifact tab 时隐藏
  // 平板以上始终显示
  "hidden md:flex"
)}>
```

#### 5. 调整 main 内边距（为底部 Tab 栏留空间）
```tsx
<main className="flex flex-1 overflow-hidden relative mb-14 md:mb-0">
```

---

## 风险评估

- **风险:** 中
- **影响范围:** Workspace.tsx（新增 Tab 逻辑）
- **兼容性问题:** 平板 (768px~1024px) 需要测试

---

## 验收标准

- [ ] 手机端 (375px) 默认显示"对话"Tab，ChatPane 全屏
- [ ] 手机端切换到"产出物"Tab，ArtifactPane 全屏
- [ ] 桌面端 (1024px+) 左右分栏，Tab 切换栏不显示
- [ ] 平板 (768px~1024px) 行为正确
- [ ] `npm run build` 通过
