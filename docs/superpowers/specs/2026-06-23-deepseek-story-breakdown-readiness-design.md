# DeepSeek V4 Story Breakdown Readiness 收口 Spec

> 日期: 2026-06-23
> 状态: 已完成

## 背景

DeepSeek V4 主线格式化输出收口已把 17 个既有在线 stage 迁移到 `artifact_data` 模式，并归档为完成项。上一轮新增 Alex `STORY_BREAKDOWN` workflow 后，系统在线 stage 增加了四个 Story Breakdown stage。这些 stage 已接入共享 runtime、renderer 和 artifact contract，但 DeepSeek V4 readiness fixture 仍只覆盖旧的 17 个 stage。

当前失败证据:

```text
tools/new-agents/backend/tests/test_deepseek_v4_readiness.py::test_deepseek_readiness_covers_every_manifest_stage
Extra items in the right set:
('STORY_BREAKDOWN', 'INPUT_ANALYSIS')
('STORY_BREAKDOWN', 'EPIC_MAPPING')
('STORY_BREAKDOWN', 'STORY_BACKLOG')
('STORY_BREAKDOWN', 'SPRINT_PLAN')
```

这意味着新 workflow 虽然已具备 renderer，但 DeepSeek readiness gate 还不能证明它在 fake DeepSeek raw JSON streaming 下同样只输出业务 JSON 数据，并由后端确定性渲染 Markdown / Mermaid / `ai4se-visual`。

## 用户故事

作为使用 DeepSeek V4 Flash 的 New Agents 用户，当新增 Alex 用户故事拆解 workflow 后，我希望它继续遵守“模型输出 `artifact_data`，后端负责最终格式”的主线规则，避免新 workflow 重新引入模型直写 Markdown、Mermaid 或 fenced block 的格式不稳定风险。

## 范围

本轮包含:

- 为 `STORY_BREAKDOWN` 四个 stage 补齐 DeepSeek readiness fixtures。
- 证明 readiness gate 覆盖所有 manifest online stage、renderer stage key、structured output instruction 和 fake DeepSeek raw JSON stream。
- 更新 DeepSeek V4 归档记录，说明当前覆盖已包含 `STORY_BREAKDOWN` 四阶段，旧的 17 stage 表述不再代表最新完成态。
- 保持 refactor README 与最新已验证分支事实一致。

本轮不包含:

- 不调用真实 DeepSeek V4 Flash smoke。该验证需要显式凭证、网络和额度。
- 不新增或修改 workflow runtime、API path、SSE path、store 或 bespoke renderer。
- 不改变 `STORY_BREAKDOWN` artifact schema / renderer 业务字段。
- 不合并主工作区 `master` 的未提交改动。

## 验收标准

- `test_deepseek_readiness_covers_every_manifest_stage` 从 RED 转 GREEN，`ARTIFACT_DATA_FIXTURES` 覆盖 manifest 中所有在线 stage。
- `STORY_BREAKDOWN` 四阶段在 readiness 测试中均通过:
  - `render_agent_turn_from_artifact_data()`
  - `validate_agent_turn()`
  - `build_structured_output_instruction()` 包含 `artifact_data` 且不包含 `artifact_update.markdown`
  - fake DeepSeek raw JSON streaming 使用 `response_format={"type":"json_object"}` 和 `thinking disabled`
- DeepSeek archive 文档记录当前完成态包含原 17 stage 加 `STORY_BREAKDOWN` 四阶段。
- 本轮只在隔离 worktree 修改本轮文件，不覆盖主工作区未提交改动。

## 风险

- 如果只补 fixture 不更新文档，后续目标模式仍可能把归档 DS todo 误判为未完成。
- 如果补测试时只枚举 Story Breakdown，而不继续要求 fixture set 等于 manifest stage set，未来新增 workflow 仍可能漏进 readiness gate。
- 真实模型输出质量无法由本轮本地 fake stream 完全证明；真实 smoke 仍保留为显式凭证条件下的可选验证。

## 完成记录

- RED: `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py::test_deepseek_readiness_covers_every_manifest_stage -q` 失败，缺 `STORY_BREAKDOWN` 四阶段 readiness fixture。
- GREEN: `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q` 通过，`64 passed`。
- 文档: DeepSeek V4 归档记录已从旧 17 stage 完成态更新为当前 21 stage 覆盖态，新增 Story Breakdown 四阶段 readiness 收口说明。
