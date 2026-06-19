# New Agents 稳定文档校准首轮设计

## 背景

`docs/todos/new-agents-evolution.md` P1 #9 要求让 `AGENTS.md`、架构、API、测试、组件等稳定文档持续反映当前代码。本轮目标模式已经落地 LLM judge trace/rubric、artifact contract 字段收紧、Mermaid contract、ChatPane Markdown 样式和共享 workflow manifest。若稳定文档不更新，后续目标模式会继续读取过期事实，例如 `component-inventory.md` 仍将 `core/workflows.ts` 描述为唯一工作流定义来源。

## 用户故事

作为后续维护者或目标模式 Agent，当我阅读稳定文档时，我希望能看到 New Agents 当前真实的运行时配置源、typed SSE 契约、artifact/visualization contract、LLM judge 和 ChatPane Markdown 职责，从而减少误读和重复探索。

## 范围

进入本轮：

- 更新 `AGENTS.md` 的 New Agents 配置同步原则，加入 `workflow_manifest.json`、Mermaid contract 和 LLM judge 证据。
- 更新 `docs/ARCHITECTURE.md` 的 New Agents 前后端事实，加入共享 manifest、ChatPane Markdown、artifact contract/Mermaid contract。
- 更新 `docs/api-contracts.md` 的 `/api/agent/runs/stream` 示例，避免用必需 artifact 阶段返回 `artifact_update.type=none` 的误导示例。
- 更新 `docs/TESTING.md` 的 New Agents 分层和审计清单，加入 manifest sync、Mermaid contract、E2E judge trace/verdict。
- 更新 `docs/component-inventory.md` 的 workflow/config 模块说明。
- 更新 `docs/todos/new-agents-evolution.md` P1 #9 进展记录。

不进入本轮：

- 不做全仓文档重写。
- 不修改自动生成 `docs/index.md`。
- 不修改代码行为。

## 验收条件

1. 稳定文档明确 `tools/new-agents/workflow_manifest.json` 是在线 workflow 首轮共享元数据源。
2. 测试文档明确 Mermaid 可视化契约和 LLM judge 完整 trace/verdict 证据。
3. API 文档中的 Agent Runtime SSE 示例展示 `replace` artifact 更新和 `none` 的适用边界。
4. 组件清单不再把 `core/workflows.ts` 描述为独占工作流定义来源。
5. todo P1 #9 有本轮校准记录和验证命令。

## 验证计划

- 使用 `rg` 检查关键表述存在。
- 使用 `rg` 确认旧的误导性 `core/workflows.ts` 独占描述已消除。
- 运行 `git diff --check`。
