# Workflow Schema Dry-run 工程信任闭环设计

## 背景

近期 New Agents 连续上线 `PRD_REVIEW`、`STORY_BREAKDOWN` 和全 workflow `artifact_data` renderer。每个 workflow/stage 都必须同步 `workflow_manifest.json`、前端 `WORKFLOWS` prompt/template 映射、后端 `WORKFLOW_STAGES`、artifact heading contract、Mermaid/`ai4se-visual` contract、DeepSeek `artifact_data` readiness、renderer stage keys、handoff prompt 和容器打包路径。当前已有多条同步测试，但测试逻辑分散，并且 `test_workflow_contract_sync.py` 仍维护一份硬编码 prompt 文件表，新增 workflow 时容易漏改或得到不够聚合的失败信息。

本轮把 E12 的平台化缺口先落成一个本地可执行的 dry-run 门禁：开发者在新增或修改 workflow 前，可以运行一个命令，一次性看到 workflow/stage 在 manifest、前端、后端、renderer 和测试证据之间的同步缺口。

## 用户故事

作为 New Agents workflow 维护者，当我新增或修改 workflow/stage 时，我希望能运行一个本地 dry-run，快速知道哪些配置面还没有同步，而不是等到运行时、前端构建或分散测试里才发现缺 prompt、contract、renderer 或 handoff 配置。

## 范围

1. 新增共享校验模块 `scripts/validation/new_agents_workflow_dry_run.py`。
2. 校验模块从真实仓库加载以下事实：
   - `tools/new-agents/workflow_manifest.json` 的 workflows/stages/handoffs。
   - 后端 `WORKFLOW_STAGES`、`REQUIRED_ARTIFACT_HEADINGS`、`REQUIRED_ARTIFACT_MERMAID_DIAGRAMS`、`REQUIRED_ARTIFACT_STRUCTURED_VISUALS`。
   - DeepSeek `get_artifact_data_ready_stages()` 和 `get_artifact_data_renderer_stage_keys()`。
   - 前端 `workflow_manifest.json` promptTemplateId 对应的 prompt 文件路径。
   - 前端 `workflows.ts` 中 `STAGE_CONTENT_BY_TEMPLATE_ID` 的 template id 映射。
   - handoff `HANDOFF_PROMPT_TEMPLATES`。
   - backend/frontend Dockerfile 和 dev compose 对 manifest 的打包/挂载。
3. 提供 CLI 输出：全部通过时打印 summary；存在缺口时逐条打印 `code`、`workflow/stage` 和可操作 message，并以非 0 退出。
4. 后端测试调用同一 dry-run 模块，覆盖当前仓库通过和至少两个负例：
   - manifest stage 缺 prompt/template 映射时失败。
   - artifact_data renderer/readiness 未覆盖 manifest stage 时失败。
5. 旧同步测试改为复用 dry-run 推导出的 prompt 文件，不再维护独立硬编码表。
6. 更新 todo 入口，记录 E12 已完成 dry-run 门禁，不声称完成完整 scaffold 生成器。

## 非目标

- 不生成新 workflow 代码、prompt、schema 或 renderer。
- 不调用真实 DeepSeek、OpenAI 或 LLM judge。
- 不新增 Lisa/Alex/DeepSeek 专属 runtime、API path、store 或 renderer。
- 不把 dry-run 接入 CI workflow；本轮只提供本地命令和测试证据。

## Dry-run 检查规则

### Stage 一致性

- manifest stage keys 必须与 `WORKFLOW_STAGES` 完全一致。
- manifest stage keys 必须与 `REQUIRED_ARTIFACT_HEADINGS` 完全一致。
- `get_artifact_data_ready_stages()` 必须覆盖全部 manifest stage keys。
- `get_artifact_data_renderer_stage_keys()` 必须覆盖全部 manifest stage keys。

### 前端 prompt/template 一致性

- 每个 manifest stage 必须声明非空 `promptTemplateId`。
- `promptTemplateId` 必须符合 `<folder>.<file>` 格式，并能映射到 `tools/new-agents/frontend/src/core/prompts/<folder>/<file>.ts`。
- 映射出的 prompt 文件必须存在，并同时包含 `_PROMPT` 与 `_TEMPLATE` export 内容。
- `tools/new-agents/frontend/src/core/workflows.ts` 的 `STAGE_CONTENT_BY_TEMPLATE_ID` 必须包含全部 manifest `promptTemplateId`，且不得包含 manifest 未使用的 runtime template id。

### 可视化 contract 一致性

- 对 `REQUIRED_ARTIFACT_STRUCTURED_VISUALS` 中的每个 stage，prompt 文件必须包含 `ai4se-visual` 示例、对应 `type`、`columns` 和 `rows`，并不得把 visual 包成旧式 `data` 或 `matrix`。
- 对 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` 中的每个 stage，prompt 文件必须包含 `mermaid` 和所需 diagram type。

### Handoff 与打包

- 每个 manifest handoff 的 source/target workflow/stage 必须存在。
- `targetAgentId` 必须等于 target workflow 的 `agentId`。
- `promptTemplateId` 必须存在于 `HANDOFF_PROMPT_TEMPLATES`。
- 后端 Dockerfile、前端 Dockerfile、`docker-compose.dev.yml`、`docker-compose.dev-cn.yml` 必须继续打包/挂载共享 manifest。

## 验收条件

1. 当前仓库运行 dry-run 返回通过。
2. 删除某个前端 `STAGE_CONTENT_BY_TEMPLATE_ID` 映射的负例会产生 `FRONTEND_TEMPLATE_MAPPING_MISSING`。
3. 删除某个 renderer/readiness stage key 的负例会产生 `ARTIFACT_DATA_RENDERER_MISSING` 或 `ARTIFACT_DATA_READY_MISSING`。
4. `test_workflow_contract_sync.py` 不再维护硬编码 `FRONTEND_PROMPT_FILES`，而是使用 dry-run loader 的推导结果。
5. 验证命令覆盖 dry-run CLI、后端同步测试、DeepSeek readiness 关键测试和 `git diff --check`。

## 风险与处理

- 风险：Python 解析 TypeScript 映射只能基于当前 `workflows.ts` 的稳定文本结构。处理：dry-run 只解析 `STAGE_CONTENT_BY_TEMPLATE_ID` object 的字符串 key，若结构变化会显式失败，提醒同步 dry-run。
- 风险：完整 scaffold 生成器范围过大。处理：本轮只做诊断型 dry-run；生成器保留为后续 E12 子能力。
- 风险：旧测试与新 dry-run 检查重复。处理：保留少量高价值旧断言，但 prompt 文件推导统一由 dry-run loader 提供。
