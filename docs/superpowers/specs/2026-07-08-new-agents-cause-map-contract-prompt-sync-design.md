# ROOT_CAUSE cause-map Contract Prompt 同步设计

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-subagents.md`、`docs/strategy/goal-mode-ci-verification.md`、`docs/index.md`、`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`、`docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`、`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`、`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/tests/test_agent_contracts.py`、`tools/new-agents/backend/tests/test_workflow_contract_sync.py`、`tools/new-agents/frontend/src/core/prompts/incident_review/root_cause.ts`、`tests/e2e/new_agents_browser/conftest.py`。
- 当前工作区：`HEAD` 与 `origin/codex/structured-failure-diagnostics` 同步在 `e8d33f9a`；工作区存在大量无关删除、文档、mockup、zip 和测试结果改动，本轮不触碰、不 stage。

已确认目标来源：

- 来源：`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` 的第 7 轮视觉产物稳定化专项。
- 上一轮状态：`INCIDENT_REVIEW/ROOT_CAUSE.cause-map` 已从表格型 `columns/rows` 迁移为节点 / 边型 `nodes/edges`，并提交 `e8d33f9a`。
- 本轮承接：修复上一轮后暴露出的 contract prompt 遗留矛盾。当前 `STRUCTURED_VISUAL_SCHEMA_PROMPTS["cause-map"]` 仍要求 `columns/rows`，会让 `build_artifact_contract_prompt()` 在 ROOT_CAUSE fallback / retry / Markdown contract 场景中提示旧协议。

改道条件检查：

- 新 P0/P1 或用户新目标：无新目标。当前发现属于同一 P0 视觉协议稳定化路线中的未关闭契约矛盾。
- 未关闭质量门：上一轮聚焦验证、New Agents 验证和非沙箱全量验证已通过；本轮没有引用新的 LLM judge。
- 架构冲突：无。修复只更新共享 contract prompt 和测试，不新增 workflow 专属 runtime、store、SSE 或 renderer。
- 工作区冲突：无。本轮允许写入路径限定为 `agent_contracts.py`、后端 contract 测试、Browser E2E fixture、本 spec / plan 和结构化失败治理 todo。
- 子智能体 / 旁路审查决策：不派发。缺口已经定位到单个共享 prompt registry 与对应 contract test，写入范围很小，分发成本高于收益；后续用聚焦测试和全量验证兜底。

边界复核：

- 本轮纳入：`cause-map` 在后端 artifact contract prompt 中的 schema 文案必须与当前 `nodes/edges` 协议一致，并由测试防止回退。
- 本轮排除：不新增新的 `ai4se-visual` 类型；不迁移 ROOT_CAUSE 的 Mermaid mindmap；不实现运行时 Mermaid parse 门禁；不改 Lisa handoff。
- 厚度门禁：这是工程信任闭环例外。入口是后端 `build_artifact_contract_prompt()`，动作是为 ROOT_CAUSE 构造 artifact Markdown contract，处理是拼接 required structured visual schema，结果是模型 / retry prompt 不再收到旧 `columns/rows` 指令，失败路径由 contract tests 显式拒绝回退，证据为 RED/GREEN contract tests 和 New Agents 回归。

结论：继续承接第 7 轮视觉稳定化路线，先关闭 `cause-map` contract prompt 矛盾，再考虑更广泛的视觉门禁。

提交前质量门修复：

- 提交前全量验证暴露 New Agents Browser E2E fixture 的页面加载等待不稳定：在非沙箱 `./scripts/test/test-local.sh all` 中，`page.goto()` / `page.reload()` 等默认 `load` 事件偶发 30 秒超时；同一 E2E 套件单独非沙箱运行通过。
- 根因判断：测试并不依赖浏览器 `load` 事件，只依赖 React 首页已经可交互；默认 `load` 等待在全量串行后的资源状态下会把外部资源 / 页面 load 事件时序误判为用户主路径不可用。
- 处理边界：只修改 `tests/e2e/new_agents_browser/conftest.py` 的首页打开等待条件，改为 `domcontentloaded` 后等待 `选择你的 AI 助手` 标题出现；不改产品代码、不改 agent runtime、不改 workflow 行为。

## Superpowers 自问自答

### Explore Project Context

`agent_contracts.py` 中 `is_valid_structured_visual_block()` 已经对 `cause-map` 走 `nodes/edges` 校验，前端 `ROOT_CAUSE_TEMPLATE` 也已改为 `nodes/edges`。但同一文件里的 `STRUCTURED_VISUAL_SCHEMA_PROMPTS["cause-map"]` 仍使用旧 `columns/rows` 示例。`build_artifact_contract_prompt()` 会把该文案拼入 Markdown artifact contract，因此模型在某些非 `artifact_data` 或 retry 场景里仍会被引导输出旧协议。

### Visual Companion Decision

本轮是协议文本与 contract test 同步，不涉及 UI 布局、图形样式或交互视觉取舍，因此不使用视觉伴随设计。

### Clarifying Questions

- 用户是谁？后端 Agent Runtime、retry / fallback contract prompt 的调用方，以及依赖 ROOT_CAUSE artifact 稳定输出的用户。
- 成功状态是什么？ROOT_CAUSE 的 artifact contract prompt 明确要求 `cause-map` 使用 `nodes/edges`，并且不再出现旧的 `columns/rows` cause-map 示例。
- 输入来源是什么？`REQUIRED_ARTIFACT_STRUCTURED_VISUALS[("INCIDENT_REVIEW", "ROOT_CAUSE")] == ["cause-map"]`。
- 失败路径是什么？如果后续有人把 `cause-map` prompt 改回矩阵协议，contract test 失败。
- 下游承接是什么？真实模型、retry prompt、后端 validation、前端 template 和导出链路对 `cause-map` 使用同一协议。

### Approaches

方案 A：只改 `STRUCTURED_VISUAL_SCHEMA_PROMPTS["cause-map"]` 文案。实现最小，但没有测试保护，容易再次回退。

方案 B：新增一个聚焦 contract prompt 测试，再更新 `cause-map` schema prompt。它直接验证 `build_artifact_contract_prompt("INCIDENT_REVIEW", "ROOT_CAUSE")` 包含 `nodes` / `edges` / `source` / `target`，且不包含旧 `"columns": ["层级", "问题", "回答"`。这是推荐方案，范围小但覆盖真实入口。

方案 C：把所有 structured visual schema prompt 统一迁到 manifest 或独立 registry。长期更好，但会触发较多 workflow 和同步测试，超出本轮“关闭已知矛盾”的边界。

本轮采用方案 B；方案 C 保留给后续 schema / prompt / contract 单源同步路线。

## 设计

修改 `tools/new-agents/backend/agent_contracts.py` 中 `STRUCTURED_VISUAL_SCHEMA_PROMPTS["cause-map"]`：

- 示例 JSON 使用 `nodes` 和 `edges`。
- `nodes` 说明必须是非空对象数组，每个 node 包含非空唯一 `id`、非空 `label`、非空 `title`。
- 可选 node 字段包括 `description`、`category`、`evidence`、`confidence`、`status`，如果出现必须是非空字符串。
- `edges` 说明必须是对象数组，每条 edge 包含非空 `source` 和 `target`，并引用已存在 node；`label` 可选但如果出现必须非空。
- 文案明确禁止把 `cause-map` 写成 `columns/rows` 表格协议。

新增后端测试：

- `test_build_artifact_contract_prompt_requires_cause_map_node_edge_contract`
- 调用 `build_artifact_contract_prompt("INCIDENT_REVIEW", "ROOT_CAUSE")`
- 断言包含 `cause-map`、`"nodes"`、`"edges"`、`"source"`、`"target"`、`id` 唯一或等价中文说明。
- 断言不包含旧的 `"columns": ["层级", "问题", "回答"` 示例。

更新 todo 执行记录，明确上一轮后续补丁已关闭 backend contract prompt 矛盾。

提交前验证中补充 E2E fixture 稳定性修复：

- `new_agents_page` 打开首页时使用 `wait_until="domcontentloaded"`。
- 等待 Agent 选择页标题 `选择你的 AI 助手` 出现后再清理 localStorage 和继续测试。
- reload 后复用同一标题可见性作为 React 首页可交互证据。

## 验收标准

1. Given ROOT_CAUSE 需要 `cause-map`
   When 后端构造 artifact contract prompt
   Then prompt 要求 `nodes/edges` 协议并禁止旧矩阵协议
   Evidence: `test_build_artifact_contract_prompt_requires_cause_map_node_edge_contract`

2. Given 现有矩阵类 visual type 仍在线
   When 运行后端 contract 测试
   Then 其他 visual type 的 `columns/rows` contract 不受影响
   Evidence: `tools/new-agents/backend/tests/test_agent_contracts.py`

3. Given 本轮只修共享 contract 文案
   When 运行 New Agents 回归
   Then 后端 contract sync、frontend template sync 和 existing Lisa/Alex workflows 不回归
   Evidence: `./scripts/test/test-local.sh new-agents`

4. Given 全量验证需要稳定覆盖 Browser E2E
   When `new_agents_page` fixture 打开或重载 New Agents 首页
   Then 等待 React 首页可交互，而不是等待不稳定的浏览器 `load` 事件
   Evidence: `./scripts/test/test-local.sh e2e` and `./scripts/test/test-local.sh all`
