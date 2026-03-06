# 产出物字段级 Inline Diff 需求文档

> 日期: 2026-02-11
> 状态: 已确认

## 1. 背景

当前 Lisa 智能体在更新产出物（结构化需求文档）时，通过 `_diff: "added" | "modified"` 标记哪些条目被新增或修改，前端以颜色高亮展示。但用户**只能知道"这里变了"，看不到"从什么变成了什么"**。

## 2. 目标

在产出物的结构化视图中，对被修改的字段以 **IDE 风格** inline 展示变更前后的内容，让用户无需额外操作即可直观对比。

## 3. 需求共识

### 3.1 对比粒度

**字段级（Fine-grained）**：在每个被修改的字段旁边，直接 inline 显示旧值和新值。

### 3.2 覆盖范围

所有显示在结构化产出物中的文本字段：

| 数据类型 | 字段 |
|---|---|
| Rule | `desc`, `source` |
| Feature | `name`, `desc`, `priority`, `acceptance[]` |
| Assumption | `question`, `status`, `priority`, `note` |
| Scope | `scope[]`, `out_of_scope[]` |

> **明确排除**: Mermaid 图表暂不处理。

### 3.3 显示风格

采用代码 IDE 的红绿对比规则：

- **红色背景 + 删除线** = 旧值（被删除/替换的内容）
- **绿色背景** = 新值（新增/替换后的内容）
- 旧值和新值在同一行内联显示

示例效果：
```
规则描述: [红底删除线]用户必须登录[/红底] → [绿底]用户必须通过 SSO 登录[/绿底]
```

### 3.4 行为规则

- `_diff: "added"` 的条目：整条绿色高亮（无旧值，保持现有行为）
- `_diff: "modified"` 的条目：逐字段对比，仅变化的字段显示红绿 diff
- 无 `_diff` 的条目：正常渲染，无任何标记
- diff 标记为**瞬态**（transient）：下一轮更新时自动清除

## 4. 技术方案

### 4.1 后端改动（~15 行）

在 `artifact_patch.py` 的 `_merge_lists` 中，当标记 `_diff: "modified"` 时，同时将变化字段的旧值存入 `_prev` 字典：

```python
new_item["_diff"] = "modified"
prev = {}
for field, new_val in new_item.items():
    if field.startswith("_") or field == "id":
        continue
    old_val = old_item.get(field)
    if old_val != new_val:
        prev[field] = old_val
if prev:
    new_item["_prev"] = prev
```

### 4.2 前端改动（~50 行）

- **类型定义**：给 `FeatureItem`、`RuleItem`、`AssumptionItem` 加 `_prev?: Record<string, any>`
- **DiffField 组件**：通用的字段 diff 渲染组件
- **CSS**：`.diff-deleted`（红底删除线）和 `.diff-inserted`（绿底）

### 4.3 不涉及的改动

- 数据库 schema 无变化（`_prev` 仅存在于运行时 state，不持久化）
- 后端 API 接口无变化（`_prev` 随 `structured_artifacts` 透传）
- Markdown 视图无变化（仅影响结构化视图）
