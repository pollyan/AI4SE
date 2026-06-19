# New Agents Persistent Artifact Summary Design

## Current State Gap Analysis

事实源快照：

- 已读取：`docs/todos/new-agents-evolution.md`、`docs/strategy/goal-mode-playbook.md`、`tools/new-agents/backend/models.py`、`tools/new-agents/backend/run_persistence.py`、`tools/new-agents/backend/context_builder.py`、`tools/new-agents/backend/tests/test_run_persistence.py`、`tools/new-agents/backend/tests/test_context_builder.py`。
- 按需未展开：前端 snapshot 恢复、分享权限、LLM 语义摘要生成；本轮只做服务端确定性 artifact summary 持久化。

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| artifact summary 持久化表 | P1 #6 | artifact 摘要有服务端持久化来源，可审计可复用 | context builder 运行时临时裁剪 artifact | 摘要不能被 snapshot、judge、恢复流程复用 | 补齐摘要机制第一张表，支撑后续扩展 | 中：新增模型和 repository 写入 | repository/context builder 单测 | 本轮 |
| 用户补充/阶段结论/决策摘要 | P1 #6 | 多类型上下文摘要可结构化保存 | 只有 messages/artifacts | 需要抽取时机和数据契约 | 长期价值高 | 中高 | 需要更多业务用例 | 后续 |
| snapshot 恢复工作台 | P1 #5/#6 | 前端可从服务端恢复工作台 | snapshot API 已存在 | 没有 UI/store hydration | 用户可见价值高 | 中 | 前端测试 | 后续 |

排序结论：

1. 选择 artifact summary 持久化表，因为它直接延续刚完成的 artifact context summary，能把运行时摘要沉淀为可复用数据。
2. 多类型摘要暂不选，因为需要定义用户补充、阶段结论、决策的抽取来源和更新时机。
3. snapshot 恢复暂不选，因为它依赖服务端可复用摘要和 snapshot 数据进一步稳定。

## Chosen Design

新增通用 `agent_context_summaries` 表，首轮只写入 artifact current summary：

- `run_id`: 所属 run。
- `source_type`: 首轮使用 `artifact`。
- `source_stage_id`: artifact 所属 stage，例如 `CLARIFY`。
- `summary_type`: 首轮使用 `current_artifact`。
- `content`: 确定性生成的 bounded Markdown 摘要。

`record_artifact_version` 在写入 artifact current version 时同步 upsert summary，同一 run/stage 只保留一条 current artifact summary。`get_run_snapshot` 返回 `contextSummaries`，供 context builder、后续恢复 UI 和 judge 复用。

摘要格式 helper 从 `context_builder.py` 中抽出到后端共享模块，避免 `run_persistence.py` 和 `context_builder.py` 循环依赖。

`context_builder.py` 优先使用 snapshot 中的 persisted `contextSummaries` 构造 `[已保存阶段产物摘要]`；如果旧数据没有 summary，则回退到 artifact current content 的确定性摘要，保证兼容。

## Requirements

- 记录 artifact version 时必须创建或更新对应 `current_artifact` summary。
- 同一 run/stage 多次记录 artifact version 时，不新增重复 summary，而是更新 content。
- `get_run_snapshot` 必须返回 `contextSummaries`，包含 source type、stage、summary type 和 content。
- context builder 优先使用 persisted summary，旧数据缺 summary 时仍能从 artifacts fallback。
- 不新增 runtime endpoint，不新增前端行为，不调用 LLM 生成摘要。

## Non-Goals

- 本轮不实现用户补充、阶段结论和决策的独立摘要。
- 本轮不做数据库迁移脚本。
- 本轮不实现前端 snapshot 恢复。
- 本轮不改变 artifact version API response。

## Verification

- `test_run_persistence.py` 覆盖 summary 创建、更新和 snapshot 输出。
- `test_context_builder.py` 覆盖 context builder 使用 persisted summary。
- 后端聚焦测试和全量测试通过。
- `git diff --check` 通过。
