# Design Doc: 智能体工作页面手机端适配

## 背景与目标

**问题：** 智能体工作页面（Workspace）在手机端分辨率下无法正常使用。

**目标：** 在 375px~428px 宽度（主流手机）下提供可用体验。

---

## 当前问题清单

| 问题 | 文件 | 当前代码 | 影响 |
|------|------|----------|------|
| Stages 导航条隐藏 | Header.tsx | `hidden md:flex` | 手机端无法切换阶段 |
| ChatPane 最小宽度 | ChatPane.tsx | `min-w-[360px]` | 小屏幕水平溢出 |
| 无移动端阶段选择器 | Header.tsx | 无 | 手机端用户无法切换工作阶段 |

---

## 修复方案

### 核心策略
采用**渐进增强**响应式方案，保持大屏左右分栏，手机端用下拉菜单切换阶段。

### 具体修改

#### 1. Header.tsx - 阶段选择器响应式改造

**大屏幕 (md+):** 保持现有横向阶段条
```tsx
<div className="hidden md:flex flex-1 max-w-2xl mx-8">
  {/* 横向阶段条 */}
</div>
```

**小屏幕 (<md):** 添加阶段下拉选择器
```tsx
<div className="flex md:hidden flex-1 mx-4">
  <select 
    value={stageIndex}
    onChange={(e) => setStageIndex(Number(e.target.value))}
    className="flex-1 h-10 px-3 rounded-lg bg-[#0f1623] border border-[#1e293b] text-white text-sm"
  >
    {stages.map((stage, idx) => (
      <option key={stage.id} value={idx}>{stage.name}</option>
    ))}
  </select>
</div>
```

#### 2. ChatPane.tsx - 移除最小宽度约束

**修改前:**
```tsx
<section className="flex flex-col w-full lg:w-[40%] min-w-[360px] ...">
```

**修改后:**
```tsx
<section className="flex flex-col w-full lg:w-[40%] ...">
```

#### 3. Workspace.tsx - 验证容器溢出处理

确保父容器 `overflow-hidden` 生效，防止子元素溢出。

---

## 测试要点

1. **375px 宽度:** 阶段下拉正常，ChatPane 无溢出
2. **768px 宽度:** 横向阶段条出现，下拉消失
3. **1024px+ 宽度:** 左右分栏正常
4. **横屏手机:** 阶段切换正常

---

## 风险评估

- **风险:** 低
- **影响范围:** 仅 Header.tsx、ChatPane.tsx
- **回滚方案:** revert git commit

---

## 验收标准

- [ ] 手机端 (375px) 可通过下拉菜单切换阶段
- [ ] 手机端 ChatPane 无水平滚动条
- [ ] 平板/桌面端行为不变
- [ ] `npm run build` 通过
