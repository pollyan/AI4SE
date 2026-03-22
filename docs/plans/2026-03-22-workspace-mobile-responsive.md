# Plan: 智能体工作页面手机端适配

## 目标
修复 Workspace 页面在手机端（<768px）无法正常使用的问题。

## 任务列表

### Task 1: Header.tsx - 添加手机端阶段下拉选择器
**文件:** `tools/new-agents/frontend/src/components/Header.tsx`
**修改:**
- 找到 `hidden md:flex` 的横向阶段条容器
- 在其**前或后**添加手机端专用下拉选择器 `<div className="flex md:hidden ...">`
- 下拉菜单使用 `stages` 数据渲染选项
- 选中时调用 `setStageIndex(idx)`

### Task 2: ChatPane.tsx - 移除最小宽度约束
**文件:** `tools/new-agents/frontend/src/components/ChatPane.tsx`
**修改:**
- 找到 `min-w-[360px]` 并删除
- 验证其他样式不影响手机端显示

### Task 3: 构建验证
**命令:**
```bash
cd ~/Documents/myProgram/AI4SE/tools/new-agents/frontend && npm run build
```
确保构建通过，无 TypeScript/ESLint 错误。

### Task 4: Git 提交
**命令:**
```bash
cd ~/Documents/myProgram/AI4SE
git add .
git commit -m "fix(new-agents): add mobile responsive support for Workspace page"
```

## 执行顺序
1. Task 1 (Header)
2. Task 2 (ChatPane)
3. Task 3 (Build)
4. Task 4 (Commit)
