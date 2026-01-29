# 产出物生成状态指示器实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在产出物面板添加"生成中"状态指示，并在生成期间保持显示旧内容。

**Architecture:** 修改 `ArtifactPanel` 组件，新增三态状态标签（待生成/生成中/已生成），简化内容渲染逻辑以保持旧内容显示。

**Tech Stack:** React 19, TypeScript, Vitest, lucide-react (Loader2 图标), Tailwind CSS

---

## Task 1: 添加 ArtifactPanel 状态指示器测试

**Files:**
- Create: `tools/ai-agents/frontend/tests/ArtifactPanel.test.tsx`

**Step 1: 编写测试文件**

```tsx
// tools/ai-agents/frontend/tests/ArtifactPanel.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ArtifactPanel } from '../components/ArtifactPanel';

describe('ArtifactPanel', () => {
  const defaultProps = {
    artifactProgress: {
      template: [{ stageId: 'stage1', artifactKey: 'doc1', name: '需求文档' }],
      completed: [],
      generating: null,
    },
    selectedStageId: null,
    currentStageId: 'stage1',
    artifacts: {},
    streamingArtifactKey: null,
    streamingArtifactContent: null,
    onBackToCurrentStage: vi.fn(),
  };

  describe('状态标签显示', () => {
    it('无内容且未生成时显示"待生成"', () => {
      render(<ArtifactPanel {...defaultProps} />);
      expect(screen.getByText('待生成')).toBeInTheDocument();
    });

    it('正在生成时显示"生成中..."', () => {
      render(
        <ArtifactPanel
          {...defaultProps}
          streamingArtifactKey="doc1"
          streamingArtifactContent="# 正在生成..."
        />
      );
      expect(screen.getByText('生成中...')).toBeInTheDocument();
    });

    it('有内容时显示"已生成"', () => {
      render(
        <ArtifactPanel
          {...defaultProps}
          artifacts={{ doc1: '# 完整文档' }}
        />
      );
      expect(screen.getByText('已生成')).toBeInTheDocument();
    });
  });

  describe('内容区显示逻辑', () => {
    it('生成中时保持显示旧内容而非流式内容', () => {
      render(
        <ArtifactPanel
          {...defaultProps}
          artifacts={{ doc1: '# 旧版本内容' }}
          streamingArtifactKey="doc1"
          streamingArtifactContent="# 新版本正在生成..."
        />
      );
      // 应该显示旧内容
      expect(screen.getByText('旧版本内容')).toBeInTheDocument();
      // 不应该显示流式新内容
      expect(screen.queryByText('新版本正在生成...')).not.toBeInTheDocument();
    });

    it('无旧内容时生成中显示占位符', () => {
      render(
        <ArtifactPanel
          {...defaultProps}
          streamingArtifactKey="doc1"
          streamingArtifactContent="# 首次生成..."
        />
      );
      expect(screen.getByText('完成当前阶段对话后，将在此生成产出物')).toBeInTheDocument();
    });
  });
});
```

**Step 2: 运行测试验证失败**

Run: `cd tools/ai-agents/frontend && npx vitest run tests/ArtifactPanel.test.tsx`

Expected: FAIL - 测试会失败因为当前代码没有"生成中..."状态

---

## Task 2: 实现状态指示器功能

**Files:**
- Modify: `tools/ai-agents/frontend/components/ArtifactPanel.tsx`

**Step 3: 修改导入语句**

在文件顶部的 lucide-react 导入中添加 `Loader2`:

```tsx
// 原代码 (第11行)
import { FileText, Clock, CheckCircle, ChevronLeft, ChevronRight, List } from 'lucide-react';

// 修改为
import { FileText, Clock, CheckCircle, ChevronLeft, ChevronRight, List, Loader2 } from 'lucide-react';
```

**Step 4: 简化内容选择逻辑**

修改内容计算逻辑 (第96-100行):

```tsx
// 原代码
const content = isGenerating && streamingArtifactContent
    ? streamingArtifactContent
    : isCompleted && effectiveKey
        ? artifacts[effectiveKey]
        : null;

// 修改为: 生成中时保持显示旧内容
const content = effectiveKey && artifacts[effectiveKey]
    ? artifacts[effectiveKey]
    : null;
```

**Step 5: 修改状态标签渲染**

修改状态标签部分 (第128-138行):

```tsx
// 原代码
{content ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full">
        <CheckCircle size={12} />
        已生成
    </span>
) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400 rounded-full">
        <Clock size={12} />
        待生成
    </span>
)}

// 修改为: 三态显示
{isGenerating ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 rounded-full">
        <Loader2 size={12} className="animate-spin" />
        生成中...
    </span>
) : content ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full">
        <CheckCircle size={12} />
        已生成
    </span>
) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400 rounded-full">
        <Clock size={12} />
        待生成
    </span>
)}
```

**Step 6: 运行测试验证通过**

Run: `cd tools/ai-agents/frontend && npx vitest run tests/ArtifactPanel.test.tsx`

Expected: PASS - 所有测试通过

---

## Task 3: 运行完整测试套件

**Step 7: 运行所有前端测试**

Run: `cd tools/ai-agents/frontend && npm run test`

Expected: 所有测试通过，无回归

**Step 8: 检查 LSP 诊断**

Run: `cd tools/ai-agents/frontend && npx tsc --noEmit`

Expected: 无类型错误

---

## Task 4: 提交代码

**Step 9: 提交更改**

```bash
cd tools/ai-agents/frontend
git add tests/ArtifactPanel.test.tsx components/ArtifactPanel.tsx
git commit -m "feat(artifact-panel): 添加生成中状态指示器

- 新增三态状态标签: 待生成/生成中.../已生成
- 生成中时保持显示旧内容，用户可继续阅读
- 添加 Loader2 旋转动画提示用户系统正在工作"
```

---

## 验收标准

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | 产出物生成时显示 Spinner 和"生成中..." | 视觉检查 |
| 2 | 生成期间保持显示上一轮产出物 | 测试用例 |
| 3 | 生成完成后切换为新内容 | 测试用例 |
| 4 | 深色模式样式正确 | 视觉检查 |
| 5 | 所有测试通过 | `npm run test` |

---

## 文件改动汇总

| 文件 | 操作 | 行数 |
|------|------|------|
| `tests/ArtifactPanel.test.tsx` | 新建 | ~60行 |
| `components/ArtifactPanel.tsx` | 修改 | ~15行 |
