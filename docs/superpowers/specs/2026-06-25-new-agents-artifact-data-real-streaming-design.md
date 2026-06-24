# New Agents Artifact Data Real Streaming Design

## CGA 摘要

目标模式入口确认 `docs/todos/refactor/2026-06-25-new-agents-artifact-streaming-not-working-p0.md` 是当前第一优先级。该 todo 要求右侧 Artifact 在最终 `agent_turn` 前显示真实、正式、逐段更新的内容，并且明确禁止假进度页、workflow 专属分支和本地模拟内容。

本轮候选用户故事评估如下：

- 选中：Artifact data 真实流式渲染。它是 P0，直接阻塞位置 indicator、文档信息密度和批注体验优化。
- 暂缓：阶段推进成熟度门禁。它是主路径正确性问题，但不阻塞右侧 Artifact 是否能流式出现。
- 暂缓：LLM 配置检测假失败。它边界清晰，但不是当前 README 标记的 P0。
- 暂缓：批注创建 500、阶段选择持久化、文档信息密度、框架深化。它们依赖或受益于稳定的 Artifact 主链路。

## 用户故事

作为 New Agents 用户，在会生成右侧 Artifact 的共享 Agent Runtime 工作流中，我发起生成后，右侧 Artifact 能在最终 `agent_turn` 前显示正式 Markdown 增量；最终输出到达后，右侧 Artifact 与最终 renderer 输出收敛一致。

## 当前证据

- P0 todo 要求生成过程中右侧产出物随有效增量逐步更新，并且 final 后收敛。
- position indicator todo 的前提是后端已经能在 final 前发送 `agent_delta.artifact_update`，但当前代码事实不满足该前提。
- `tools/new-agents/backend/agent_runtime.py` 当前 raw JSON streaming 每个 chunk 后只调用 `build_partial_agent_delta(accumulated)`，而该函数只抽取 `chat` 和 `markdown` 字符串。
- 当前 structured artifact prompt 要求模型输出 `artifact_data`，不是 `artifact_update.markdown`。
- 前端 `tools/new-agents/frontend/src/core/llm.ts` 已能消费 `agent_delta.output.artifact_update`。若后端 final 前发出正式 Markdown delta，现有 parser/store 主链路已有入口。

## 设计

后端在共享 raw JSON streaming 路径增加对完整 `artifact_data` JSON 对象的局部抽取。抽取规则只在对象已经完整、能被 `json.JSONDecoder().raw_decode` 解析时成立；半截对象、字段不完整或 renderer validation 失败时，不生成 artifact delta。

当局部 `artifact_data` 完整且当前 `workflow_id/current_stage_id` 有共享 renderer 时，后端复用 `render_agent_turn_from_artifact_data` 生成正式 Markdown，并把它作为 `AgentTurnDeltaOutput.artifact_update.replace` 发出。这个 delta 使用最终产物同一 deterministic renderer，不输出调试进度页、字段名进度或裸 JSON。

最终 `agent_turn` 仍走现有完整 JSON parse、contract validation 和 renderer 链路。前端收到过 renderable artifact delta 时，继续使用现有 final chunk 路径，不再用最终结果做合成揭示。

## 边界

包含：

- `TEST_DESIGN/CLARIFY` 和 `TEST_DESIGN/STRATEGY` 代表阶段的 final 前 artifact delta 回归测试。
- 半截 `artifact_data` 不得生成 artifact delta 的回归测试。
- 共享 `agent_runtime.py` 局部 JSON 对象抽取和 renderer 复用。

不包含：

- 流式位置 indicator。
- ArtifactPane 信息架构重做。
- 单个 workflow/agent 专属 runtime、API path、store 或 renderer。
- 真实外部模型 smoke 作为默认本地门禁。

## 验收

- 后端测试证明完整 `artifact_data` 对象在 final 前到达时，会先产生正式 Markdown `agent_delta.artifact_update.replace`。
- 后端测试证明半截 `artifact_data` 不会伪造成进度页或 artifact delta。
- 代表性第一阶段和第二阶段均覆盖，不只修 CLARIFY。
- 现有 frontend parser 流式 artifact delta 测试保持通过。
- 完成型故事提交前运行聚焦验证，并在可行时运行 `./scripts/test/test-local.sh all`。
