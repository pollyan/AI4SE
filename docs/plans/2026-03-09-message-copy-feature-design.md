# 消息复制功能设计

## 需求概述

在智能体对话框中为每条消息添加复制功能，点击即可复制当前消息的 Markdown 源码内容。

## 功能规格

### 交互设计

1. **按钮位置**：消息气泡底部，与重试按钮并排（如有）
2. **按钮样式**：图标 + 文字，与重试按钮风格一致
3. **复制内容**：Markdown 源码（保留格式）
4. **反馈机制**：
   - 按钮图标变对勾 ✓，文字变 "已复制"，颜色变绿色
   - 同时弹出 Toast 提示 "已复制到剪贴板"
   - 2 秒后恢复原状

### 显示规则

| 消息类型 | 复制按钮 | 重试按钮 |
|---------|---------|---------|
| 用户消息 | ✅ 显示 | ❌ 不显示 |
| 助手消息（非最后一条） | ✅ 显示 | ❌ 不显示 |
| 助手消息（最后一条） | ✅ 显示 | ✅ 显示 |

### UI 布局

```
┌─────────────────────────────────┐
│  消息内容 (Markdown 渲染)        │
└─────────────────────────────────┘
│  ─────────────────────────────  │  ← 分隔线
│           [📋 复制] [🔄 重试]    │  ← 右对齐
└─────────────────────────────────┘
```

## 技术实现

### 修改文件

`tools/new-agents/frontend/src/components/ChatPane.tsx`

### 实现步骤

1. **添加 import**
   ```tsx
   import { Copy, Check } from 'lucide-react';
   ```

2. **添加状态**
   ```tsx
   const [copiedId, setCopiedId] = useState<string | null>(null);
   const [toast, setToast] = useState<string | null>(null);

   const handleCopy = async (content: string, msgId: string) => {
     await navigator.clipboard.writeText(content);
     setCopiedId(msgId);
     setToast('已复制到剪贴板');
     setTimeout(() => {
       setCopiedId(null);
       setToast(null);
     }, 2000);
   };
   ```

3. **消息底部工具栏**

   在消息气泡 `<div>` 内部末尾添加工具栏，根据条件显示复制和重试按钮。

4. **Toast 渲染**
   ```tsx
   {toast && (
     <div className="fixed bottom-20 left-1/2 -translate-x-1/2 bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg z-50">
       {toast}
     </div>
   )}
   ```

### 按钮样式

```tsx
<button className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-blue-400 transition-colors">
  <Copy className="w-3.5 h-3.5" />
  <span>复制</span>
</button>
```

复制成功时：
```tsx
<button className="flex items-center gap-1.5 text-xs text-green-400 transition-colors">
  <Check className="w-3.5 h-3.5" />
  <span>已复制</span>
</button>
```

## 验收条件

1. ✅ 每条消息（用户 + 助手）底部都有复制按钮
2. ✅ 点击复制按钮，消息 Markdown 源码被复制到剪贴板
3. ✅ 复制成功后按钮变为绿色对勾 + "已复制"
4. ✅ 同时显示 Toast 提示 "已复制到剪贴板"
5. ✅ 2 秒后按钮和 Toast 恢复原状
6. ✅ 最后一条助手消息同时显示复制和重试按钮
7. ✅ 按钮样式与现有重试按钮一致