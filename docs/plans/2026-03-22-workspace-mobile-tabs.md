# Plan: Workspace 页面移动端 Tab 切换

## 目标
修复 Workspace 页面手机端体验，添加"对话"和"产出物"Tab 切换。

## 任务列表

### Task 1: 修改 Workspace.tsx
文件: `tools/new-agents/frontend/src/pages/Workspace.tsx`

**1. 添加 useState 导入和 mobileTab 状态:**
```tsx
import React, { useEffect, useState } from 'react';
// ...
const [mobileTab, setMobileTab] = useState<'chat' | 'artifact'>('chat');
```

**2. 修改 main 容器的 className:**
```tsx
<main className="flex flex-1 overflow-hidden relative mb-14 md:mb-0">
```

**3. 在 main 后添加移动端 Tab 切换栏:**
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

**4. 修改 ChatPane 的 className:**
在现有 className 基础上，找到并修改:
- `w-full lg:w-[40%` (注意去掉 min-w-[360px] 如果还有)
- 添加 `mobileTab !== 'chat' && "md:hidden"` 
- 添加 `hidden md:flex`（桌面端始终显示）

**5. 修改 ArtifactPane 的 className:**
- 保持 `w-full lg:w-[60%]` 
- 添加 `mobileTab !== 'artifact' && "md:hidden"`
- 添加 `hidden md:flex`

### Task 2: 构建验证
```bash
cd ~/Documents/myProgram/AI4SE/tools/new-agents/frontend && npm run build
```

### Task 3: 本地 Docker 测试 ⚠️ 必须执行
```bash
cd ~/Documents/myProgram/AI4SE
docker-compose -f docker-compose.dev.yml build new-agents
docker-compose -f docker-compose.dev.yml up -d new-agents
sleep 20
docker-compose -f docker-compose.dev.yml ps
```

用浏览器访问 http://localhost 验证：
1. 手机尺寸 (375px) 下是否显示底部 Tab 切换栏
2. 切换 Tab 是否正常
3. 桌面端 (1024px+) 是否保持左右分栏

### Task 4: Git 提交
```bash
cd ~/Documents/myProgram/AI4SE && git add . && git commit -m "fix(new-agents): add mobile tab switcher for Workspace page"
```
