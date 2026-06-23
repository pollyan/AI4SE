# DeepSeek V4 结构化输出证据门禁设计

## 背景

`docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 已记录 17 个在线 workflow stage 完成 `artifact_data` 迁移：模型输出业务 JSON 数据，后端用 Pydantic schema 和 deterministic renderer 生成 Markdown、Mermaid 与 `ai4se-visual`。当前 DeepSeek V4 Flash 能力层级已明确为 `json_object_only`，请求只发送 OpenAI-compatible `response_format={"type":"json_object"}` 并保持 thinking disabled。

剩余缺口不是继续改某一个 stage，而是缺少一个可复用证据门禁：在本地或 CI 合并前确认 DeepSeek V4 链路没有回退到 Markdown 直出、strict schema 参数或 silent fallback；同时在没有真实凭证、网络或额度时，门禁要明确跳过真实 smoke，而不是伪造成功。

## Superpowers 头脑风暴记录

本节按 Superpowers `brainstorming` skill 的问题链执行。目标模式自动执行授权将用户确认节点改为 Agent 基于当前仓库事实、todo 和测试证据的自问自答裁决；该裁决不替代 TDD、验证和收尾证据。

### Explore Project Context

问：当前代码、文档、测试和 git 状态说明了什么？
答：`docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 记录了 17 个在线 workflow stage 已完成 `artifact_data` 迁移，DeepSeek V4 Flash 被明确为 `json_object_only`，请求只应发送 `response_format={"type":"json_object"}` 并保持 thinking disabled。当前风险不再是某个阶段 renderer 缺失，而是目标模式、CI 或 reviewer 缺少一个可复用证据门禁来区分“本地确定性 contract 测试通过”和“真实 DeepSeek V4 smoke 通过”。主工作区有既有未提交改动，本轮在隔离 worktree `codex/deepseek-v4-evidence-goal-mainline` 中推进，并已 rebase 到当前 `master` 的最新 playbook 规则。

问：这个需求是否过大，需要拆成多个独立子项目？
答：不需要拆分。它是一个单一工程信任闭环：给 DeepSeek V4 结构化输出链路提供本地 deterministic evidence 和可选真实 smoke evidence 的统一结果模型。它不跨 UI、外部项目管理、工作流新增或多 agent 能力；内部可以用测试、helper、CLI 和文档分步实现，但 milestone 边界应保持为一个 evidence gate。

问：哪些相邻缺口需要同轮并入？
答：必须同轮并入本地 deterministic evidence、可选真实 smoke 的凭证检查、DeepSeek V4 request payload 断言、artifact_data renderer/contract 断言、结构化 `passed` / `failed` / `skipped` 结果、失败原因、CLI/JSON summary 和 todo 记录。只补 pytest 不告诉维护者如何使用；只补 smoke 脚本会在无凭证环境误阻塞；只写文档无法防止 runtime request 参数回归。

### Visual Companion Decision

问：本轮是否需要浏览器视觉辅助来做 mockup、布局或视觉方案比较？
答：不需要。本轮是后端工程验证门禁，不改 New Agents 页面布局、ArtifactPane、工作流选择或可视化呈现。输出是机器可读 JSON evidence summary 和测试结果，用文本 spec 与测试更直接。

### Clarifying Questions

问：这个能力包真正服务的用户是谁？
答：维护 New Agents 的开发者、目标模式执行者、CI/发布前 reviewer，以及需要判断 DeepSeek V4 结构化输出是否真实验证过的负责人。

问：用户要完成的真实任务是什么？
答：在提交或发布前回答“DeepSeek V4 格式化输出链路是否仍然按 JSON mode -> artifact_data -> renderer -> contract 运行”，并明确真实模型 smoke 是通过、失败，还是因为缺凭证/网络未执行。

问：成功状态是什么？
答：调用本地 evidence gate 时能得到 `passed`，并证明 fake DeepSeek V4 raw JSON stream 捕获到 `response_format={"type":"json_object"}`、prompt 要求 `artifact_data`、最终 artifact 通过现有 contract；调用可选真实 smoke 且缺凭证时得到 `skipped`，不会伪造 `passed`。

问：输入来源是什么？
答：本地 deterministic gate 使用 fake client 和代表性 stage fixture；可选真实 smoke 从环境变量读取 API key/base URL/model 等外部条件。缺少外部条件时只记录 skipped。

问：约束是什么？
答：必须复用共享 Agent Runtime、provider capability、artifact_data renderer 和 artifact contract；不能新增 DeepSeek 专属 runtime、API path、store 或 renderer；不能把真实 smoke 设为默认强制联网门禁；不能用 fake client 的通过结果包装成真实模型通过。

问：失败路径应如何处理？
答：输出结构化 `EvidenceResult`，用 `passed`、`failed`、`skipped` 区分状态。请求参数错误、renderer/contract/schema 失败、fake output malformed 都是 `failed`；缺真实 smoke 凭证、网络或必要环境变量是 `skipped`；只有实际执行的 local deterministic gate 或真实 runtime 成功才是 `passed`。

问：哪些内容本轮明确不做？
答：不继续迁移新的 workflow stage；不强制真实 DeepSeek 网络调用；不新增前端 UI；不新增 Alex/DeepSeek 专属 runtime；不把 Story Breakdown 或 PRD Review 纳入本门禁；不处理 Artifact diagnostics 或 Lisa 资产质量闭环。

问：本轮验证怎样覆盖 CI 风险？
答：核心验证是 `test_deepseek_v4_smoke_evidence.py`，覆盖 fake DeepSeek V4 raw JSON stream、request payload、artifact_data 渲染、contract validation、缺凭证 skip 和 malformed output failed。再运行 `test_agent_runtime.py`、`test_agent_contracts.py`、`py_compile` 和 `git diff --check`，覆盖共享 runtime、contract、语法和格式风险。真实 smoke 需要凭证、网络和额度，不作为默认本地门禁。

### Approaches

方案 A：只在 todo 中记录真实 smoke 需要凭证，代码不新增门禁。
取舍：成本最低，但无法防止 request 参数、capability 或 renderer 回归；后续仍会把“未运行真实 smoke”混在文字说明里。结论：不选。

方案 B：新增本地 deterministic evidence gate，并提供 env-gated 可选真实 smoke。
取舍：能在无凭证环境稳定运行，覆盖 request 参数、artifact_data、renderer 和 contract；同时明确真实 smoke 未执行时是 `skipped` 而不是 `passed`。结论：推荐并采用。

方案 C：把真实 DeepSeek V4 smoke 做成强制 CI 门禁。
取舍：证据最强，但需要网络、凭证、额度和外部服务稳定性，当前目标模式没有授权；会让普通本地验证和 CI 因环境缺失失败。结论：不选，保留为后续显式配置的可选门禁。

### Presented Design

Architecture：新增 backend evidence module `deepseek_v4_smoke_evidence.py`，通过共享 Agent Runtime 的 raw JSON path 和现有 artifact contract 生成证据；不新增 API path、不改前端、不新增 DeepSeek 专属 runtime。模块提供 Python API 和 CLI JSON summary，供本地、CI 或目标模式收尾引用。

Components：`EvidenceResult` 表达 name/status/reason/details；`run_local_deepseek_v4_evidence()` 使用 fake stream client 和合法 `artifact_data` fixture 验证 DeepSeek V4 request、prompt 和 final artifact；`run_optional_real_deepseek_v4_smoke(env)` 检查环境变量，缺失时返回 skipped，齐全时才调用真实 runtime；测试文件覆盖 passed/failed/skipped 语义。

Data flow：调用方运行 local evidence -> fake DeepSeek V4 client 捕获 runtime request -> runtime 解析 raw JSON -> renderer 生成 artifact -> `validate_agent_turn()` 校验 contract -> evidence module 输出 JSON summary。调用 optional real smoke -> 先检查 env -> 缺失返回 skipped -> 齐全才执行真实 runtime -> 结果写入 evidence summary。

Error handling：所有异常必须收敛为结构化 evidence，不允许吞掉错误或返回假成功。schema/contract/runtime/request 错误进入 `failed`，缺配置进入 `skipped`，成功路径携带 provider/model/workflow/stage/request assertions 等 details。

Testing：先写导入不存在的 RED tests，再实现 module；GREEN 后运行 evidence tests、共享 runtime tests、agent contract tests、py_compile 和 diff check。真实 DeepSeek 网络 smoke 不默认执行，但 spec、todo 和收尾记录保留运行条件。

## 目标

新增一个 backend 级 DeepSeek V4 evidence gate，使调用方可以：

- 使用 fake DeepSeek V4 client 在本地证明 JSON mode request、artifact_data renderer、contract validation 和 final output 链路走通。
- 在环境具备 `NEW_AGENTS_DEEPSEEK_V4_SMOKE_API_KEY` 等凭证时，选择性运行真实 DeepSeek V4 smoke。
- 在缺凭证或网络未授权时得到明确 skipped 结果。
- 把门禁命令写入 todo，作为后续目标模式和 CI 映射依据。

## 范围

进入本轮：

- 新增 `tools/new-agents/backend/deepseek_v4_smoke_evidence.py`。
- 新增 backend tests 覆盖 evidence gate。
- 如必要，收窄 `agent_runtime.py` 的公共 helper，让 gate 能复用现有 DeepSeek capability / request 构造逻辑。
- 更新 `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 和 `docs/todos/refactor/README.md`。
- 新增本轮 spec / plan。

不进入本轮：

- 不强制真实 DeepSeek 网络调用。
- 不新增 agent-specific runtime、API path、store 或 renderer。
- 不新增 frontend UI。
- 不继续迁移新的 workflow stage。

## 设计

Evidence gate 提供一个可测试的 Python API 和 CLI：

- `run_local_deepseek_v4_evidence()`：使用 fake stream client，运行一个代表性 stage 的 raw JSON turn，断言 DeepSeek V4 使用 `json_object_only`、thinking disabled、`response_format={"type":"json_object"}`，并确认最终 artifact 通过 contract。
- `run_optional_real_deepseek_v4_smoke(env=os.environ)`：检查凭证和 base URL/model；缺失时返回 skipped；齐全时调用现有 runtime 运行真实 smoke。
- `EvidenceResult`：包含 `name`、`status`、`reason`、`details`。
- CLI 输出 JSON summary，便于 CI 或人工读取。

代表性 stage 选择现有 `REQ_REVIEW/REPORT` 或 `TEST_DESIGN/CLARIFY`。选择标准是：已有稳定 fixture、包含 artifact_data renderer、contract 能验证 required headings/visual。门禁不伪造真实 provider 成功；fake client 只用于 deterministic 本地证据。

## 验收条件

1. Given 未实现 evidence gate
   When 运行新增测试导入 `deepseek_v4_smoke_evidence`
   Then 测试失败，原因是模块或函数不存在。

2. Given fake DeepSeek V4 stream 返回合法 `artifact_data`
   When 运行 local evidence gate
   Then 结果为 passed，且 fake client 捕获到 `response_format={"type":"json_object"}`、model settings 关闭 thinking、最终 artifact 含 required headings。

3. Given 缺少真实 DeepSeek V4 smoke 凭证
   When 运行 optional real smoke
   Then 结果为 skipped，reason 说明缺少哪些环境变量，不返回 passed。

4. Given fake client 收到非 JSON object request 或 renderer/contract 失败
   When 运行 evidence gate
   Then 结果为 failed，details 指向请求参数或 contract 错误。

5. Given 本轮完成
   When 查看 todo
   Then DeepSeek V4 todo 记录 evidence gate 已消化，真实 smoke 仍是显式凭证/网络条件下的可选门禁。

## 风险与控制

- 风险：fake smoke 被误认为真实模型证明。控制：命名和输出明确区分 local deterministic evidence 与 optional real smoke。
- 风险：新增脚本复制 runtime 逻辑。控制：复用 `agent_runtime` 现有 public helper 和 runtime entry，不新增 DeepSeek 专属 runtime。
- 风险：CI 因缺凭证失败。控制：缺凭证时 skipped；只有显式配置真实 smoke 才联网。
- 风险：门禁覆盖太窄。控制：选一个代表性 stage 覆盖 request params、artifact_data、renderer、contract；已有 17 stage 的分层测试继续覆盖各 stage schema。
