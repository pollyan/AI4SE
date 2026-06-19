# New Agents Artifact 模型生成遵守章节锁设计

## Current State Gap Analysis

事实源快照：
- 已读取：`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/backend/context_builder.py`、`tools/new-agents/backend/tests/test_context_builder.py`、`tools/new-agents/frontend/src/services/chatService.ts`、`tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`、`tools/new-agents/frontend/src/core/agentCore.ts`。
- 按需未展开：Mermaid/PDF/DOCX 导出。本切片只处理 artifact 生成时的锁定章节约束。

能力包聚合：
| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 模型生成遵守章节锁 | 章节锁定 MVP 剩余、模型生成阶段的锁定遵守、人工校准不被后续生成覆盖 | 用户锁定已确认章节 -> 发起下一轮生成 -> 模型被提示不能改 -> 前端应用产物时仍保留锁定章节 | 只加 prompt 不能防止模型失误；只前端合并又缺少模型约束。两者一起才形成可信保护链 | 后端 context builder 测试、前端 chatService 测试 |
| 重复标题精确锚点 | 章节锁定 MVP 剩余 | 多个同名章节也能精确锁定 | 需要 section anchor/id 策略和 UI 迁移 | 后续 |
| 服务端审阅轨迹 | 协作深化 | 记录模型或人工何时触碰锁定章节 | 需要审计模型和 API，范围较大 | 后续 |

候选 gap：
| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 模型生成遵守章节锁 | Todo P1.7 | 生成过程中锁定章节不被模型或 artifact update 覆盖 | 手工编辑保存会阻断锁定章节修改 | 模型流式产物仍可能覆盖锁定章节 | 高 | 中 | 高 | 本轮 |
| 重复标题锚点 | Todo P1.7 | 同名标题也能锁准 | 当前按 heading 匹配 | 重复标题可能误锁 | 中 | 中 | 中 | 后续 |
| 服务端审阅轨迹 | Todo P1.7 | 行级审阅/锁定操作有服务端轨迹 | 当前本地/metadata 状态 | 审计不足 | 中 | 中高 | 高 | 后续 |

排序结论：
1. 选择模型生成遵守章节锁，因为它直接补齐“用户锁定已确认内容后，后续 Agent 不应覆盖”的信任闭环。
2. 重复标题锚点和审阅轨迹暂不选，因为它们是锁定保护稳定后的增强。

切片准入判断：
- 用户可感知动作链：锁定章节 -> 继续生成 -> 锁定章节保持原文。
- 相邻缺口合并：同时做服务端 prompt 约束和前端 artifact 合并保护。
- Superpowers 成本合理性：跨前后端，关系到用户对人工校准是否会被模型覆盖的核心信任。
- 过薄风险检查：不是单 helper；包含上下文、生成应用、测试和 todo 更新。
- 能力增量句：完成后，用户现在可以锁定已确认章节，并让后续模型生成保持这些章节不变。

切片厚度门禁：
- 入口：ArtifactPane 章节锁定。
- 动作：用户继续发送消息触发 Agent Runtime 生成。
- 处理：后端 context prompt 带锁定章节约束；前端应用 artifact update 时保留锁定章节。
- 可见结果：右侧 artifact 中锁定章节内容不被替换。
- 状态承接：锁仍保留在 store / run snapshot 中；新 artifact version 使用保护后的内容。
- 失败反馈：重复标题精确锚点不在本轮，仍按 heading 匹配。
- 证据：后端 `test_context_builder`，前端 `chatService`，lint/build/diff check。
- 结论：通过。

## 用户故事

作为已经人工确认部分产出物内容的用户，当我锁定一个章节后继续让 Lisa / Alex 生成后续内容时，我希望该章节保持原样，即使模型新产物里改写了它，也不会覆盖我锁定的确认结果。

## 验收条件

1. Given run snapshot 中存在当前阶段章节锁，When 构建下一轮 run context，Then prompt 包含锁定章节和“不得修改”的明确约束。
2. Given 当前 artifact 中有锁定章节，When 模型返回的新 artifact 改写该章节，Then 前端最终 artifact 保留锁定章节原文，同时允许其他章节更新。
3. Given 模型返回新 artifact，When 保存 artifact history，Then history 中保存的是保护后的 artifact。

## 文件范围

- 修改：`tools/new-agents/backend/context_builder.py`
- 修改：`tools/new-agents/backend/tests/test_context_builder.py`
- 修改：`tools/new-agents/frontend/src/services/chatService.ts`
- 修改：`tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`
- 修改：`docs/todos/new-agents-ux-professionalization.md`

## 非目标

- 不解决重复标题的精确锚点。
- 不记录服务端审阅轨迹。
- 不改变 artifact contract 或 workflow manifest。
- 不为 Lisa/Alex 添加专属分支。
