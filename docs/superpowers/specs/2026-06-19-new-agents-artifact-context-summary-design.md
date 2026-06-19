# New Agents Artifact Context Summary Design

## Current State Gap Analysis

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-evolution.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、`tools/new-agents/backend/context_builder.py`、`tools/new-agents/backend/run_persistence.py`、`tools/new-agents/backend/tests/test_context_builder.py`。
- 按需未展开：前端恢复 UI、run list、分享权限、持久化摘要表 schema；这些属于后续切片，不进入本轮。

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 前序 artifact 服务端摘要 | P1 #6 | 后续模型轮次能看到已保存阶段产物的短摘要 | snapshot 已返回 current artifacts，context builder 只拼 messages | artifact 不进入服务端上下文，跨阶段推进仍可能遗忘关键产物 | 直接提升跨阶段连续性，改动集中 | 中低：需控制 prompt 体积和重复注入 | 后端 context builder 单测验证 | 本轮 |
| 持久化摘要表 | P1 #6 | 数据库保存用户补充、阶段结论、产物摘要和决策 | 只有 messages/artifacts 原文 | 需要新 schema、写入时机和迁移策略 | 长期价值高 | 中高：会扩展数据模型和 API | 需要 repository/API 测试 | 后续 |
| 基于 snapshot 恢复工作台 | P1 #5/#6 | 前端可从服务端 snapshot 重建对话和 artifact | 已有只读 snapshot API | 还没有恢复入口和 store hydration | 用户可见价值高 | 中：涉及 UI/store/localStorage 边界 | 前端 store/组件/API 测试 | 后续 |

排序结论：

1. 选择前序 artifact 服务端摘要，因为它复用已存在的 snapshot 数据，不新增 runtime 分支，也能补上 P1 #6 中“让模型基于摘要稳定跨阶段推进”的最短闭环。
2. 持久化摘要表暂不选，因为需要 schema 设计、摘要生成时机和迁移策略，适合作为下一轮独立切片。
3. snapshot 恢复 UI 暂不选，因为它更偏用户界面恢复流程，依赖当前服务端上下文和 snapshot 基础先稳定。

## Chosen Design

扩展 `context_builder.py`，让它在构造 runtime prompt 时从 `get_run_snapshot(run_id)["artifacts"]` 读取当前 run 已保存的 artifact current version，并在存在 artifact 时插入一个服务端生成的“已保存阶段产物摘要”上下文块。

摘要规则保持确定性，不调用模型：

- 每个 artifact 使用 `stageId` 标记来源阶段。
- 对 Markdown 原文做轻量规范化：去掉多余空白，保留标题、列表、表格文本等可读内容。
- 每个 artifact 最多保留固定字符数，超过时追加“已截断”提示。
- artifact 摘要块整体参与同一个 `max_chars` 预算；预算不足时优先保留当前用户输入和最近消息，旧消息和 artifact 块可以被裁剪。

上下文顺序：

1. 已保存阶段产物摘要块。
2. 持久化历史 messages。
3. 当前用户输入。

这样模型先看到稳定产物摘要，再看到最近对话，最后看到本轮请求。无 artifact 时 prompt 与当前行为保持一致。

## Requirements

- 无 artifact 的 run 继续返回当前已有 prompt 结构，不新增空标题。
- 有 artifact 的 run 会在 prompt 中包含“已保存阶段产物摘要”和对应 `stageId`。
- artifact 原文过长时只保留短摘要，并在摘要内标明该 artifact 内容被截断。
- 总 prompt 超过预算时，仍返回 `context_truncated` warning，并优先保留当前用户输入。
- 不新增 API endpoint，不新增 agent-specific runtime，不改变 frontend prompt 边界。

## Non-Goals

- 本轮不新增数据库摘要表。
- 本轮不调用 LLM 生成语义摘要。
- 本轮不实现 snapshot 恢复 UI。
- 本轮不改变 artifact version 存储模型。

## Verification

- 后端 `test_context_builder.py` 覆盖 artifact 摘要注入、无 artifact 兼容、artifact 摘要截断和总预算截断 warning。
- 后端 `test_stream_services.py` 保持通过，证明 stream 主链路仍通过 persistence adapter 使用 context builder。
- 后端全量 New Agents 测试通过。
- `git diff --check` 无 whitespace 问题。
