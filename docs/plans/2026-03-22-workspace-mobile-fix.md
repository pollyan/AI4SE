# Plan: Workspace 移动端显示逻辑修复

## 问题
ChatPane 在手机端完全不显示，因为 clsx 条件逻辑写反了。

## 任务列表

### Task 1: 修复 Workspace.tsx 的 clsx 条件
文件: `tools/new-agents/frontend/src/pages/Workspace.tsx`

**修改 ChatPane section:**
找到:
```tsx
<section className={clsx(
    "flex flex-col w-full lg:w-[40%] bg-[#0B1120] border-r border-[#1e293b] relative shadow-[10px_0_30px_-10px_rgba(0,0,0,0.5)] z-20 h-full",
    mobileTab !== 'chat' && "md:hidden",
    "hidden md:flex"
)}>
```

改为:
```tsx
<section className={clsx(
    "flex flex-col w-full lg:w-[40%] bg-[#0B1120] border-r border-[#1e293b] relative shadow-[10px_0_30px_-10px_rgba(0,0,0,0.5)] z-20 h-full",
    mobileTab === 'chat' ? "flex md:hidden" : "hidden md:flex"
)}>
```

**修改 ArtifactPane section:**
找到:
```tsx
<section className={clsx(
    "flex flex-col w-full lg:w-[60%] bg-[#0B0F17] text-gray-300 relative shadow-2xl overflow-hidden bg-grid-pattern h-full",
    mobileTab !== 'artifact' && "md:hidden",
    "hidden md:flex"
)}>
```

改为:
```tsx
<section className={clsx(
    "flex flex-col w-full lg:w-[60%] bg-[#0B0F17] text-gray-300 relative shadow-2xl overflow-hidden bg-grid-pattern h-full",
    mobileTab === 'artifact' ? "flex md:hidden" : "hidden md:flex"
)}>
```

### Task 2: 构建验证
```bash
cd ~/Documents/myProgram/AI4SE/tools/new-agents/frontend && npm run build
```

### Task 3: 本地 Docker 测试 ⚠️ 必须执行
```bash
cd ~/Documents/myProgram/AI4SE
docker-compose -f docker-compose.dev.yml up -d new-agents
sleep 20
docker-compose -f docker-compose.dev.yml ps
```

验证 http://localhost 正常：
1. 手机尺寸下 ChatPane 全屏显示
2. Tab 切换正常

### Task 4: Git 提交
```bash
cd ~/Documents/myProgram/AI4SE && git add . && git commit -m "fix(new-agents): fix mobile tab display logic in Workspace"
```
