# DeepSeek V4 格式化输出完成态收口 Spec

> 日期: 2026-06-23
> 状态: 已完成

## 背景

DeepSeek V4 兼容的结构化产物数据改造已经在代码和待办文档中记录了完整进展: 17 个在线 workflow stage 均迁移到 `artifact_data`，DeepSeek V4 Flash 明确走 `json_object_only`，后端 Pydantic schema 和 deterministic renderer 负责 Markdown、Mermaid 与 `ai4se-visual` 产物格式，且 readiness gate、持久化闭环、真实 smoke gate 适配和 prompt 边界硬化都已完成。

当前缺口不是继续新增 DeepSeek runtime 分支，而是工作池状态不一致:

- `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 仍标为 `活动候选`。
- `docs/todos/refactor/README.md` 写着“当前没有活跃重构 todo / 当前入口 暂无”，但目录内仍存在活动候选文件。
- 目标模式后续轮次会从 `docs/todos/` 工作池选择任务，如果索引状态不可信，就会把已完成的 DeepSeek 需求反复识别为实现缺口。
- 格式化输出已由共享 runtime 的 `artifact_data` 指令和后端 renderer 接管，但原先缺少一个显式防回退门禁来保证所有在线 stage 都继续使用 `artifact_data`，且 retry prompt 不再要求模型修复完整 Markdown 文档。

## 用户故事

作为 AI4SE 维护者，当我继续执行目标模式时，我希望 DeepSeek V4 格式化输出需求能基于新鲜验证被明确归档，并且 `docs/todos/refactor/README.md` 能准确列出剩余活动候选，这样后续轮次不会把已完成的 DeepSeek 改造误判为待实现能力。

## 范围

本轮包含:

- 为 `docs/todos/refactor/README.md` 增加活动候选索引一致性验收测试。
- 为所有在线 workflow stage 增加共享 runtime 格式化输出防回退验收，确保 structured output instruction 使用 `artifact_data`，不再要求 `artifact_update.markdown`。
- 增加 runtime 指令 registry 与 renderer stage key registry 的一致性验收，防止新增/迁移 stage 只改一侧。
- 将 DeepSeek V4 结构化产物数据 todo 从 refactor 活动池归档到 `docs/todos/archive/`。
- 更新归档文档状态与完成态验收记录。
- 更新 refactor README 的当前入口与已归档清单。
- 运行 DeepSeek 相关后端、prompt、文档一致性验证。

本轮不包含:

- 不新增 Lisa、Alex、DeepSeek 或未来 agent 专属 runtime、API path、store 或 renderer。
- 不改变共享 `/api/agent/runs/stream` typed Agent Runtime、workflow manifest、artifact contract、持久化模型或共享 UI 基础设施。
- 不执行真实 DeepSeek V4 网络 smoke，除非本地显式提供凭证、网络和额度。
- 不处理 New Agents enhancement diagnostic 中 E04 之后的增强项；它们作为下一轮候选保留。

## 设计

### 文档索引一致性验收

新增根级 pytest:

- 扫描 `docs/todos/refactor/*.md`，排除 `README.md`。
- 将包含 `> 状态: 活动候选` 的文件视为活动候选。
- 如果没有活动候选，README 可以写“暂无”。
- 如果存在活动候选，README 不能写“当前入口 暂无”，并且必须包含每一个活动候选文件名。

该测试在当前状态下应先失败，因为 README 声称暂无活动入口，但 DeepSeek 和 enhancement diagnostic 文件仍为活动候选。

### DeepSeek todo 归档

将 `2026-06-23-deepseek-v4-structured-artifact-data.md` 移动到 `docs/todos/archive/`，并将状态改为:

`> 状态: 已完成 / 已归档`

在归档文档中补充完成态验收记录，明确本轮的收口证据:

- 17 个在线 stage 已迁移到 `artifact_data`。
- DeepSeek V4 Flash 继续使用 `response_format={"type":"json_object"}` 与 thinking disabled。
- readiness gate、artifact_data persistence、真实 smoke gate 适配和 prompt 边界硬化已完成。
- 本轮运行的本地验证命令作为归档证据。

### 格式化输出防回退门禁

新增后端 pytest 覆盖:

- 从 `workflow_manifest.json` 枚举所有在线 workflow stage。
- 对每个在线 stage 校验 `build_structured_output_instruction()` 返回包含 `artifact_data` 的 stage-specific 指令。
- 校验这些指令不包含 `artifact_update.markdown` 或“完整 Markdown 文档”等模型直写最终产物格式要求。
- 对每个在线 stage 校验 `build_raw_json_retry_prompt()` 要求修复 `artifact_data` schema/contract/renderer 错误，而不是修复 Markdown 文档。
- 校验 `ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS` 的 stage key 与 `artifact_data_renderers.get_artifact_data_renderer_stage_keys()` 完全一致。

该门禁只强化共享 Agent Runtime 与共享 renderer 的契约，不新增 DeepSeek 专属 runtime、API path、store 或 renderer。

### refactor README 更新

README 的当前入口改为只列出仍活动的 `2026-06-23-new-agents-enhancement-diagnostic.md`，并在已归档清单中加入 DeepSeek V4 结构化输出归档文件。

## 验收标准

- 新增文档索引测试先失败，再在归档和 README 更新后通过。
- DeepSeek V4 相关 readiness、runtime、contract、endpoint、persistence 和真实 smoke skip/执行门禁测试通过。
- 所有 manifest 在线 stage 的 runtime structured output instruction 与 retry prompt 均通过 `artifact_data` 防回退门禁。
- runtime 指令 registry 与 renderer stage key registry 保持一致。
- 前端 prompt 测试确认已迁移 stage 不再注入 Markdown 直写格式要求。
- `docs/todos/refactor/README.md` 与实际活动候选文件保持一致。
- git diff 只包含本轮 spec、plan、测试和 docs/todos 收口改动。
