# DeepSeek V4 结构化输出证据门禁设计

## Superpowers Brainstorming 自问自答

### Explore Project Context

问: 当前代码、文档、测试和 git 状态说明了什么？

答: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 记录 17 个在线 workflow stage 已完成 `artifact_data` 迁移；当前 `agent_runtime.py` 的 `supports_artifact_data_rendering()` 也覆盖 `TEST_DESIGN`、`REQ_REVIEW`、`VALUE_DISCOVERY`、`INCIDENT_REVIEW`、`IDEA_BRAINSTORM` 共 17 个阶段。DeepSeek V4 Flash 已通过 `resolve_structured_output_capability()` 标记为 `json_object_only`，`build_model_settings()` 对 `deepseek-v4-*` 关闭 thinking。主线尚无 `deepseek_v4_smoke_evidence.py` 或对应测试，说明缺口不是再迁移某个 stage，而是缺少一个可复用 evidence gate 证明格式化输出链路没有回退。

问: 当前需求是否过大，需要拆分？

答: 不需要拆分。它是一个单一工程信任闭环：检查 DeepSeek V4 provider 配置、17 stage renderer coverage、本地 deterministic raw JSON smoke、真实 smoke 前置条件和结构化结果表达。内部可拆成多个测试和 helper，但用户可感知能力是“我能运行一个门禁判断 DS 格式化输出链路是否可信”。

问: 当前有哪些约束？

答: 必须复用共享 Agent Runtime、`artifact_data` renderer、artifact contract 和现有 pytest；不能新增 DeepSeek 专属 runtime、API path、store 或 renderer；不能把缺凭证/网络的真实模型 smoke 伪造成 passed；主工作区有既有脏文件，本轮在隔离 worktree `codex/deepseek-v4-evidence-gate-mainline` 实施。

### Visual Companion Decision

问: 是否需要视觉辅助？

答: 不需要。本轮是后端证据门禁和测试，不改前端 UI、ArtifactPane、工作流选择或可视化布局。文本 spec、JSON evidence summary 和 pytest 输出就是合适载体。

### Clarifying Questions

问: 用户是谁？

答: 维护 AI4SE New Agents 的开发者、目标模式执行者、CI reviewer，以及关心 DeepSeek V4 格式化输出是否稳定的负责人。

问: 用户要完成什么真实任务？

答: 在提交或发布前回答：当前 DeepSeek V4 是否仍按 `json_object_only + thinking disabled -> artifact_data -> deterministic renderer -> artifact contract` 运行；如果真实 DeepSeek smoke 没跑，原因是缺凭证、缺网络还是配置错误。

问: 成功状态是什么？

答: 本地运行 evidence gate 时至少能得到 provider 配置 passed、17 stage coverage passed、本地 deterministic smoke passed；缺真实 smoke 凭证时得到 skipped 且列出缺失环境变量；如果请求参数、renderer 或 contract 回归，则返回 failed 并能被测试捕获。

问: 输入来源是什么？

答: provider/config 检查来自 `agent_runtime.py` 的公共 helper；stage coverage 来自预期 stage 清单和 `supports_artifact_data_rendering()` / `build_structured_output_instruction()`；local smoke 用 fake stream 返回代表性 `artifact_data` fixture；optional real smoke 从环境变量读取 API key、base URL、model。

问: 失败路径如何处理？

答: 所有检查都返回 `EvidenceResult`。缺真实 smoke 环境是 `skipped`；provider 配置不匹配、stage coverage 缺失、runtime schema/contract/JSON 失败是 `failed`；只有实际执行并通过的检查才是 `passed`。

问: 本轮不做什么？

答: 不调用真实 DeepSeek API，不新增前端入口，不新增专属 runtime，不合并 `deepseek-v4-mainline-closure` 大范围历史分支，不做 artifact_data 持久化、confidence consolidation 或 prompt boundary hardening，不处理 Alex Story/PRD 主线收敛。

### Approaches

方案 A: 只更新 todo，说明真实 smoke 需要凭证。  
优点: 成本低。  
缺点: 没有可运行门禁，不能挡住 provider capability、stage coverage 或 renderer 回归。  
结论: 不选。

方案 B: 新增后端 evidence module，覆盖 provider 配置、stage coverage、本地 deterministic smoke 和 optional real smoke skip/fail/pass。  
优点: 无凭证环境可稳定运行，能纳入 CI 等价验证；真实 smoke 状态不会被伪造成通过。  
缺点: 需要维护一个预期 stage 清单。  
结论: 推荐并采用。

方案 C: 把真实 DeepSeek 网络 smoke 做成强制 CI 门禁。  
优点: 外部证据最强。  
缺点: 需要凭证、网络、额度和供应商稳定性，当前目标模式没有这些授权，容易让 CI 因环境问题失败。  
结论: 不选，本轮只提供 optional real smoke。

### Presented Design

Architecture: 新增 `tools/new-agents/backend/deepseek_v4_smoke_evidence.py`，复用 `agent_runtime` 的 provider helper、raw JSON runtime、artifact_data renderer 和 artifact contract。模块不暴露 API endpoint，不改前端，不新增 DeepSeek 专属运行时。

Components: `EvidenceStatus` 表示 `passed` / `failed` / `skipped`；`EvidenceResult` 表示 name/status/reason/details；`collect_deepseek_v4_evidence()` 聚合 provider、coverage、local smoke 和 optional real smoke；`run_local_deepseek_v4_evidence()` 用 fake/可注入 runtime 跑代表性 stage；`run_optional_real_deepseek_v4_smoke()` 先检查环境变量，缺失时 skipped。

Data flow: 调用 evidence collector -> provider helper 生成配置证据 -> stage coverage helper 遍历 17 stage -> local smoke 通过 raw JSON stream 解析 `artifact_data` 并渲染 artifact -> contract 校验 -> optional real smoke 根据 env 决定 skipped 或执行 -> 输出 JSON summary。

Error handling: JSON 解析、schema、renderer、contract、runtime model 等异常收敛为 failed；缺真实 smoke 环境收敛为 skipped；CLI 只在存在 failed 时返回非零，skipped 不阻塞默认本地验证。

Testing: 先写导入不存在模块的 RED tests，再实现模块。测试覆盖 provider 配置、17 stage coverage、local smoke request payload、contract failure、缺凭证 skip、错误 model fail、collector summary。验证还要运行 `test_agent_runtime.py`、`test_agent_contracts.py`、`py_compile` 和 `git diff --check`。

## 用户故事

作为维护 New Agents DeepSeek V4 输出链路的开发者，我希望有一个本地可运行、真实 smoke 可选的证据门禁，这样我可以在没有外部凭证时仍证明结构化格式链路没有回退，并在需要真实模型验证时清楚知道缺哪些环境条件。

## 范围

本轮包含:

- 新增 backend evidence module 和 CLI JSON summary。
- 检查 DeepSeek V4 provider capability、response_format、thinking disabled 和 retries。
- 检查 17 个已迁移 workflow stage 都支持 `artifact_data` renderer 且 instruction 要求 `artifact_data`。
- 本地 deterministic smoke 使用 fake raw JSON stream 验证 request payload、renderer、artifact contract。
- optional real smoke 缺环境变量时返回 skipped，配置错误时 failed。
- 新增 pytest 覆盖和 todo 记录。

本轮不包含:

- 不实际调用 DeepSeek 网络 API。
- 不新增或修改前端 UI。
- 不新增 DeepSeek 专属 runtime、API path、store 或 renderer。
- 不合并大范围历史分支。
- 不新增 artifact_data 持久化或 prompt 版本管理。

## 验收条件

1. 当运行 DeepSeek V4 provider evidence 时，结果为 passed，details 中能看到 `json_object_only`、`{"type":"json_object"}`、thinking disabled 和 retries。
2. 当运行 stage coverage evidence 时，17 个预期 stage 全部被覆盖；如果移除任一 stage，测试能失败。
3. 当 fake stream 返回合法 `REQ_REVIEW/REPORT` `artifact_data` 时，local smoke passed，捕获到请求参数使用 JSON object mode 和 thinking disabled，最终 artifact 标题为 `# 需求评审报告`。
4. 当 fake stream 返回非法 `artifact_data` 时，local smoke failed，reason 指向 validation/schema/contract 问题。
5. 当真实 smoke 环境变量缺失时，optional real smoke skipped，并列出缺失变量，不返回 passed。
6. CLI 输出合法 JSON；存在 failed 时退出码为 1，仅 skipped 不导致默认失败。
7. `docs/todos/` 记录 evidence gate 已补齐，真实 DeepSeek smoke 仍需显式凭证/网络/额度。

## 风险与控制

- 风险: local smoke 被误读为真实模型验证。控制: 结果名称区分 `local-deterministic` 与 `optional-real-smoke`，todo 和收尾说明明确真实 smoke 未默认运行。
- 风险: 预期 stage 清单与 runtime coverage 将来漂移。控制: 测试固定清单，新增 stage 时必须同步 evidence gate。
- 风险: 门禁逻辑复制 runtime 行为。控制: 复用 `agent_runtime` helper 和 runtime entry，不重新实现 provider adapter。
- 风险: CLI 因缺凭证阻塞 CI。控制: 缺凭证为 skipped，只有 failed 才非零退出。

## 验证计划

- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q`
- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py -q`
- `.venv/bin/python -m py_compile tools/new-agents/backend/deepseek_v4_smoke_evidence.py tools/new-agents/backend/agent_runtime.py`
- `git diff --check`

真实 DeepSeek V4 网络 smoke 不作为默认门禁；需要 `NEW_AGENTS_DEEPSEEK_V4_SMOKE_API_KEY`、`NEW_AGENTS_DEEPSEEK_V4_SMOKE_BASE_URL`、`NEW_AGENTS_DEEPSEEK_V4_SMOKE_MODEL` 且需要联网/额度。
