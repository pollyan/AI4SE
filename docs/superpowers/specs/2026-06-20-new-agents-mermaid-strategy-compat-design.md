# New Agents 策略 Mermaid 语法兼容设计

## 背景

回顾历史 worktree 时发现 `codex/fix-new-agents-mermaid-parse` 分支保留了一个未进入 `master` 的提交：`fix(new-agents): 兼容策略产物 Mermaid 语法变体`。该分支已明显落后主干，不能直接合并，否则会回退大量后续 New Agents 改造。

当前主干已具备基础 `mermaidSanitizer` 和 Mermaid 重复渲染缓存，但仍存在两个缺口：

- 结构化 Agent Runtime 在校验 artifact Mermaid fenced block 时，直接把原始代码传给 `mermaid.parse`，没有复用 sanitizer。
- `TEST_DESIGN/STRATEGY` 模板中的 `block-beta` 示例不够保守，且 prompt 未明确约束 `quadrantChart` 和 `block-beta` 的稳定输出格式。

## 用户价值

用户在测试策略阶段更少遇到“右侧产物因为 Mermaid 语法细节失败”的中断。模型生成的常见可修正变体会先被共享 sanitizer 规范化；真正无法证明安全的语法仍走现有结构化失败恢复路径。

## 设计约束

- 复用共享 New Agents 前端核心，不新增 Lisa/Alex 或 workflow 专属渲染分支。
- sanitizer 只处理可证明安全的语法形态：`quadrantChart` 标签断行/引号、`block-beta` 分组语法降级为普通节点。
- 不吞掉 Mermaid parse 错误；sanitizer 后仍无法通过的图继续显式失败。
- 不直接 merge 旧分支，按当前主干重新实现有效差异。

## 验收

- sanitizer 能规范化 `quadrantChart` 单行轴/象限标签和 `block-beta block["..."] { ... }` 分组变体。
- `llm.ts` 的 Mermaid 预校验调用 `mermaid.parse` 时使用 sanitized diagram。
- `TEST_DESIGN/STRATEGY` 的 `block-beta` 模板示例可被 Mermaid 解析。
- 相关 Vitest、lint、build 和 diff check 通过。
