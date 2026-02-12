---
title: '优化 Inline Diff 显示粒度至句子级'
slug: 'inline-diff-sentence-level'
created: '2026-02-12'
status: 'deployed'
stepsCompleted: [1, 2, 3, 4, 5, 6]
tech_stack: ['React', 'fast-diff', 'diff (npm)']
files_to_modify: ['tools/ai-agents/frontend/package.json', 'tools/ai-agents/frontend/src/components/common/DiffField.tsx']
code_patterns: ['Frontend Component', 'Utility function']
test_patterns: ['Component Test', 'Jest']
---

# 技术规格：优化 Inline Diff 显示粒度至句子级

## 概览

### 问题陈述

当前的字符级 Diff（由 `fast-diff` 提供）会将文本从字符维度拆分，导致片段细碎、不可读，尤其是在中文内容或发生单词替换时。这使得用户难以快速扫描和理解变更内容。

### 解决方案

将差异比对的粒度从“字符级”切换为“句子级”。
核心策略：如果一个句子已发生任何变化（哪怕只改了一个字），则将整个旧句子标记为删除，整个新句子标记为新增。这种整句替换的方式能极大提升变更内容的可读性。

### 范围

**范围内:**
- 替换 `DiffField.tsx` 中的 `fast-diff` 库为 `diff` 库的 `diffSentences`。
- 更新 `package.json` 引入新依赖。
- 更新 `DiffField.test.tsx` 测试用例以适应新的句子级逻辑。

**范围外:**
- 不涉及后端逻辑变更。
- 不涉及 `fast-diff` 以外的其他 Diff 算法优化（如单词级）。

## 开发上下文

### 代码库模式

- **Frontend Component**: React 函数式组件。
- **Presentation Component**: `DiffField` 仅负责展示，不处理业务逻辑。

### 参考文件

| 文件 | 用途 |
| ---- | ------- |
| `tools/ai-agents/frontend/package.json` | 依赖管理 |
| `tools/ai-agents/frontend/src/components/common/DiffField.tsx` | 核心组件 |
| `tools/ai-agents/frontend/src/components/common/__tests__/DiffField.test.tsx` | 测试文件 |

### 技术决策

- **库选型**: 采用 `diff` (https://www.npmjs.com/package/diff) 库，使用其 `diffSentences` 功能。
- **粒度**: 严格的句子级 (Strict Sentence Level)。即使句子只变动这一个字符，也显示整句 Diff。
- **回退策略**: 为了体验一致性，文本字段完全替换为句子级 Diff。

## 实施计划

### 任务分解

- [x] Task 1: 安装依赖
  - File: `tools/ai-agents/frontend/package.json`
  - Action: `npm install diff @types/diff`
  - Notes: 记得移除 `fast-diff` 及 `@types/fast-diff` (如果不再使用)。考虑到项目其他地方可能用到，如果不冲突可以先保留 `fast-diff`，但在本组件中不再引用。

- [x] Task 2: 重构 DiffField 组件
  - File: `tools/ai-agents/frontend/src/components/common/DiffField.tsx`
  - Action: 
    - 移除 `fast-diff` 引用。
    - 引入 `import { diffSentences } from 'diff';`
    - 修改 `useMemo` 逻辑，调用 `diffSentences(oldValue, value)`。
    - 处理 `diffSentences` 返回的数据结构（`Change` 对象数组：`{ value: string, added?: boolean, removed?: boolean }`）。
    - 渲染逻辑：`removed` -> `.diff-deleted`, `added` -> `.diff-inserted`, 其他 -> 原样渲染。

- [x] Task 3: 更新单元测试
  - File: `tools/ai-agents/frontend/src/components/common/__tests__/DiffField.test.tsx`
  - Action:
    - 验证句子级替换效果。例如 "Hello world." -> "Hello output."。期望：整句 "Hello world." 标记删除，整句 "Hello output." 标记新增。
    - 验证多句情况。
    - 验证无变化情况。

### 验收标准

- [x] AC 1: 给定文本 "我喜欢猫。", 当更新为 "我喜欢狗。" 时，应该显示为 `<del>我喜欢猫。</del><ins>我喜欢狗。</ins>`（整句替换），而不是 `<del>猫</del><ins>狗</ins>`（字符级）。
- [x] AC 2: 给定多句文本 "你好。再见。", 当更新为 "你好。拜拜。" 时，"你好。" 保持原样，"再见。" 标记删除，"拜拜。" 标记新增。
- [x] AC 3: 组件能够正确处理 `oldValue` 为 null/undefined 的情况（即新增字段），直接显示新内容。
- [x] AC 4: 对于完全相同的长文本，渲染时不包含任何 `.diff-inserted` 或 `.diff-deleted` 标签。

## 附加上下文

### 依赖

- `diff` (npm package) v5.x 或更高版本。
- `@types/diff` 类型定义。

### 测试策略

- **Unit Test**: 使用 Jest + React Testing Library 验证 `DiffField` 的渲染输出类名。
- **Manual Verification**: 启动前端，查看 Rules/Features 中的长文本字段 Diff 效果是否符合预期。

### 备注

- `diff` 库的 `diffSentences` 基于标点符号切分。对于中文，通常支持 `。！？` 等全角标点。需验证其在中文环境下的标点识别能力。如果库本身对中文分句支持不佳，可能需要自定义 `tokenize` 逻辑，但 MVP 阶段先尝试默认行为。
