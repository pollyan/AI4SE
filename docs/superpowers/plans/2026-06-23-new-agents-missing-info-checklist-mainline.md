# E02 阶段缺失信息清单闭环 Implementation Plan

## Milestone

交付一个共享前端缺失信息清单闭环：从当前阶段 artifact 中抽取待澄清/缺失/阻断项，并在 ArtifactPane 和 ChatPane 中同步呈现。

## TDD 步骤

1. RED：新增共享解析函数测试。
   - 表格章节应抽取问题、阻断性、责任方、状态、下一步。
   - 列表章节应抽取阻断项与下一步。
   - 无相关章节时返回 `null`。

2. RED：新增 ArtifactPane 测试。
   - 当前 artifact 有缺失信息表格时展示“阶段缺失信息清单”、阻断统计、问题和下一步。
   - 空产物或无相关章节时不展示清单。

3. RED：新增 ChatPane 测试。
   - 当前 artifact 有缺失信息时展示轻量提醒、阻断数量和首个下一步。
   - 其他普通 artifact 不展示提醒。

4. GREEN：实现最小共享解析与 UI。
   - 新增或扩展共享 core helper，避免在组件内复制解析逻辑。
   - ArtifactPane 使用完整 checklist。
   - ChatPane 使用同一 checklist 的摘要。

5. REFACTOR：收紧命名、样式和边界。
   - 保持共享 UI 基础设施，不引入 agent/workflow 分支。
   - 避免改动 runtime、SSE/API、持久化模型。

6. 验证与记录。
   - 运行聚焦 Vitest。
   - 运行 `npm run lint`。
   - 运行 `git diff --check`。
   - 更新 `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 和 README。
   - 提交聚焦 commit。
