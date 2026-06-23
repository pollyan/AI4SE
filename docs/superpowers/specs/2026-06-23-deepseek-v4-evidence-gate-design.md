# DeepSeek V4 结构化输出证据闭环设计

## 背景

`docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 记录了 DeepSeek V4 Flash 兼容的结构化产物数据改造。当前 17 个在线 workflow stage 已迁移到 `artifact_data -> 后端 deterministic renderer -> artifact contract -> typed SSE` 路径，DeepSeek V4 Flash capability 也已收束为 `json_object_only`，并关闭 thinking。

剩余缺口不再是单个阶段 schema，而是维护者缺少一个可诊断、可留痕的 DeepSeek V4 证据闭环。没有这个闭环时，本地 deterministic tests 只能证明 fixture 与 renderer，不足以回答“真实 DeepSeek 配置是否能按当前结构化协议运行”。

## 自问自答

- 问：这个能力包真正服务的用户意图是什么？
  答：维护者需要判断 DeepSeek V4 Flash 是否能作为 New Agents 结构化产物主路径模型，而不是继续按阶段补局部 renderer。
- 问：哪些相邻缺口必须同轮并入，否则用户仍无法完成任务？
  答：环境配置诊断、DeepSeek V4 capability 检查、代表性 raw JSON streaming 调用、artifact_data 渲染/contract 结果、证据 JSON 落盘、无凭证 skip 记录和 todo 更新必须同轮并入。
- 问：哪些缺口本轮明确不做，为什么不属于同一能力包？
  答：不新增前端 UI、不新增 DeepSeek 专属 runtime、不新增阶段 schema、不默认调用真实模型。它们分别属于产品展示、架构扩展、已完成迁移或外部凭证问题。
- 问：失败时用户或调用方如何知道原因并继续推进？
  答：证据记录必须区分 missing env、model mismatch、runtime model error、schema/contract/renderer error，并写出 evidence path。
- 问：哪些本地验证最接近 CI，本轮为什么足够？
  答：默认 deterministic pytest 覆盖配置诊断和证据写入；真实 DeepSeek smoke 只在 `NEW_AGENTS_SMOKE_*` 齐备且模型为 `deepseek-v4-*` 时运行。

## 用户故事

作为维护者，当我准备把 DeepSeek V4 Flash 作为 New Agents 结构化产物主路径模型时，我可以运行一个可诊断、可留证的验证入口，确认真实模型链路可用，或明确知道缺少什么配置、模型或外部条件，从而避免把 mock/fixture 通过误认为真实环境通过。

## 设计

新增后端 evidence helper，复用现有 Agent Runtime、raw JSON streaming、`resolve_structured_output_capability()`、`build_model_settings()` 和 `validate_agent_turn()` 路径，不新增 DeepSeek 专属 runtime/API/store/renderer。

证据闭环包含两层：

1. Readiness evidence：不调用外部模型，汇总 DeepSeek V4 capability、thinking disabled、response format、已启用 artifact_data renderer 的 stage 列表和环境配置状态。
2. Live smoke evidence：当 `NEW_AGENTS_SMOKE_API_KEY`、`NEW_AGENTS_SMOKE_BASE_URL`、`NEW_AGENTS_SMOKE_MODEL` 齐备且模型以 `deepseek-v4-` 开头时，运行代表性 `TEST_DESIGN/CLARIFY` raw JSON streaming，要求模型返回 `artifact_data`，由后端渲染并通过 contract，再写入证据 JSON。

证据文件写入目录：

- 默认：`tmp/new-agents/deepseek-v4-smoke/`，该目录已被 `.gitignore` 忽略。
- 可覆盖：`NEW_AGENTS_SMOKE_EVIDENCE_DIR`

## 文件范围

- 新增 `tools/new-agents/backend/deepseek_v4_smoke_evidence.py`
- 新增 `tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py`
- 修改 `tools/new-agents/backend/agent_runtime.py`，公开已迁移 `artifact_data` stage 列表，供 readiness evidence 使用
- 修改 `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- 按需修改 `docs/todos/refactor/README.md`

## 验收条件

1. 未配置 `NEW_AGENTS_SMOKE_*` 时，evidence helper 能报告缺失变量，并写入 `status=skipped` 的证据 JSON。
2. 配置模型不是 `deepseek-v4-*` 时，helper 能报告 model mismatch，不把非 DeepSeek 模型当作 DeepSeek evidence。
3. readiness evidence 能列出 17 个已启用 `artifact_data` 的 workflow/stage，并记录 `json_object_only`、`{"type": "json_object"}` 和 thinking disabled。
4. fake runtime 测试能证明 live smoke 成功时会写入 workflow/stage、artifact 标题摘要、token usage 和 evidence path。
5. 真实 DeepSeek 调用只在环境变量齐备时运行；缺少凭证、网络或额度时不伪造成功。

## 风险

- 真实模型调用依赖外部网络、凭证和额度，本轮不能把它作为默认本地门禁。
- 代表性 live smoke 只覆盖 `TEST_DESIGN/CLARIFY`，全 17 阶段的真实模型逐阶段调用成本高，留作手动扩展。
- 证据文件默认写入 ignored artifacts 目录，避免污染仓库；提交时不得包含真实凭证或真实模型输出里的敏感业务数据。

## 验证计划

- `python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q`
- `python3 -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q`
- `python3 -m py_compile tools/new-agents/backend/deepseek_v4_smoke_evidence.py tools/new-agents/backend/agent_runtime.py`
- `python3 tools/new-agents/backend/deepseek_v4_smoke_evidence.py`
- `git diff --check`
- 可选真实 smoke：`NEW_AGENTS_SMOKE_API_KEY=... NEW_AGENTS_SMOKE_BASE_URL=... NEW_AGENTS_SMOKE_MODEL=deepseek-v4-flash python3 tools/new-agents/backend/deepseek_v4_smoke_evidence.py`
