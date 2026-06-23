# DeepSeek V4 主线格式化输出收口 Spec

> 日期: 2026-06-23
> 状态: 已完成

## 背景

`master` 当前已经包含 DeepSeek V4 结构化产物数据的 17 个在线 stage 实现，但 `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 仍在活动池中，`docs/todos/refactor/README.md` 也继续把它列为当前入口。上一轮在 `codex/deepseek-v4-completion-closure` 上形成过完成态提交，但该分支相对 `master` 带有多个其他 milestone 的祖先改动，直接合并会把非本轮的大量 New Agents 增强一起带入。

本轮目标是在新的 `master` 基线隔离 worktree 中，形成一个聚焦、可验证、可合入的 DeepSeek V4 完成态收口提交：补齐主线缺失的 DeepSeek readiness、artifact_data persistence、real smoke skip gate 与信任闭环记录；主线 todo 池不再误报 DeepSeek 为活动候选；同时共享 Agent Runtime 增加格式化输出防回退门禁，确保在线 stage 继续要求模型输出 `artifact_data`，由后端 renderer 确定性生成 Markdown、Mermaid 和 `ai4se-visual`。

## 用户故事

作为 AI4SE 维护者，当我从 `master` 继续运行目标模式时，我希望 DeepSeek V4 格式化输出需求已经在主线完成态闭环中，而不是继续出现在活动 todo 池里；同时我希望新增 workflow stage 或 renderer 时，如果有人把输出要求回退成模型直写 Markdown，测试能立即失败。

## 范围

本轮包含:

- 在 `master` 基线隔离 worktree 中新增 refactor todo 索引一致性测试。
- 从已验证的 DeepSeek confidence / prompt boundary 分支移植 DeepSeek 专属 readiness gate、artifact_data persistence、real smoke gate、prompt 边界硬化和对应 spec/plan 记录。
- 将 DeepSeek V4 结构化产物数据 todo 从 `docs/todos/refactor/` 归档到 `docs/todos/archive/`。
- 更新 `docs/todos/refactor/README.md`，只列仍活动的 New Agents enhancement diagnostic。
- 在共享 `agent_runtime.py` 中建立 `ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS` registry。
- 让 `supports_artifact_data_rendering()` 同时要求 runtime 指令 registry 与 renderer stage key registry 存在。
- 增加 manifest 在线 stage 的 structured output instruction、retry prompt 和 renderer registry 同步测试。
- 更新本轮 spec/plan 和归档记录，写明验证证据。

本轮不包含:

- 不合并 `codex/deepseek-v4-completion-closure` 整条历史分支，也不引入其中的 artifact quality / missing-info / Alex workflow 等非 DeepSeek 增强。
- 不处理 New Agents enhancement diagnostic 中的 E02/E03/E04/E13/E14。
- 不改变 `/api/agent/runs/stream`、typed SSE 或共享 UI 基础设施；持久化变更仅限已验证的 `artifact_data` 随 artifact version 保存和 run snapshot 暴露。
- 不新增 DeepSeek、Lisa、Alex 或未来 agent 专属 runtime、API path、store 或 renderer。
- 不运行真实 DeepSeek V4 网络 smoke，除非环境显式具备凭证、网络和额度。

## 设计

### 文档工作池一致性

新增根级 pytest 扫描 `docs/todos/refactor/*.md`，排除 `README.md`，把包含 `> 状态: 活动候选` 的文件视为活动候选。README 必须列出每个活动候选文件名；如果没有活动候选，README 可以写“暂无”。

当前 `master` 下该测试会先失败，因为 DeepSeek 和 enhancement diagnostic 都是活动候选，而 README 的状态可能与实际文件不一致。实现后 DeepSeek 被归档，README 只保留 enhancement diagnostic。

### Runtime 格式化输出防回退

`agent_runtime.py` 当前通过多个 `if` 分支选择 stage-specific artifact_data 指令，但没有一个可测试的 registry 能与 renderer registry 直接比对。本轮把这些映射集中到:

`ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS: dict[tuple[str, str], str]`

并用测试约束:

- `workflow_manifest.json` 中所有在线 stage 都存在于 runtime 指令 registry。
- 所有在线 stage 都存在于 `artifact_data_renderers.get_artifact_data_renderer_stage_keys()`。
- `build_structured_output_instruction()` 对每个在线 stage 返回包含 `artifact_data` 的指令。
- 指令不得包含 `artifact_update.markdown` 或要求模型输出完整 Markdown 的旧格式。
- `build_raw_json_retry_prompt()` 对每个在线 stage 要求修复 `artifact_data`，不得回退到 `artifact_update.type 必须为 replace` 的 Markdown 修复路径。
- runtime 指令 registry 与 renderer stage key registry 完全一致。

### DeepSeek 信任闭环主线化

`master` 基线缺少文档已声称完成的 DeepSeek readiness/persistence/smoke gate 证据。本轮只移植 DeepSeek 专属信任闭环，不带入其他 New Agents 增强:

- readiness gate: 从 manifest 枚举在线 stage，验证 renderer、fixture、artifact contract、structured output instruction、fake DeepSeek raw JSON stream、response_format 和 thinking disabled。
- artifact_data persistence: renderer 返回的 validated `artifact_data` 随 artifact version 保存，当前 run snapshot 暴露 `artifactData`；旧版本和手工编辑版本返回 `artifactData: null`。
- real smoke gate: 无凭证时明确 skip；配置 DeepSeek 或兼容 smoke 环境变量后验证 raw JSON streaming、schema、renderer 和 artifact contract。
- prompt boundary: 已迁移 `artifact_data` stage 的前端 system prompt 不再注入 `<mark>`、`artifact_update`、完整 Markdown 重写要求或 Mermaid fence 参考，避免和后端 DeepSeek `artifact_data` 指令冲突。

### 归档记录

DeepSeek todo 归档文档记录:

- 17 个在线 stage 已完成 `artifact_data` 迁移。
- DeepSeek V4 Flash 继续使用 `json_object_only` capability、OpenAI-compatible `response_format={"type":"json_object"}` 和 thinking disabled。
- readiness gate、persistence、real smoke gate、prompt boundary hardening 和本轮 format guard 的验证结果。

## 验收标准

- RED: 新增索引测试在实现前失败，证明活动 todo/README 状态不一致会被捕获。
- RED: 新增 runtime format guard 测试在实现前失败，证明主线尚无统一 `ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS` registry。
- GREEN: 上述测试在实现后通过。
- DeepSeek 相关后端扩展测试通过，至少覆盖 readiness、renderer、runtime、contract、endpoint、persistence 和 real smoke skip gate。
- 前端 prompt 测试通过，证明已迁移 stage 不注入模型直写 Markdown 要求。
- TypeScript lint、Python black check、`py_compile` 和 `git diff --check` 通过。
- git diff 只包含本轮 DeepSeek mainline closure 相关文件。

## 风险

- `master` 工作树有未提交改动，因此本轮必须在隔离 worktree 中完成，不触碰主工作树脏文件。
- 真实 DeepSeek smoke 需要外部凭证和网络；默认只能验证 skip gate 与 deterministic renderer 链路。
- 归档 todo 会改变目标模式后续选题入口；需要用索引测试保证 README 与实际活动文件同步。
