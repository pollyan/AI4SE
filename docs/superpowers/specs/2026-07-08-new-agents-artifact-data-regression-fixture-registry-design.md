# New Agents Artifact Data Regression Fixture Registry Design

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/index.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-ci-verification.md`、`docs/TESTING.md`、`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`、`tools/new-agents/backend/agent_runtime.py`、`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_contracts.py`、`tools/new-agents/backend/tests/test_workflow_contract_sync.py`。
- 当前工作区：`git status -sb` 干净，`HEAD` 与 `origin/codex/structured-failure-diagnostics` 同步。

已确认目标来源：

- 来源：`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` 的第 8 轮“全工作流失败回归门禁与文档收口”。
- 本轮承接：第 8 轮首个工程信任闭环，建立所有在线 `artifact_data` 阶段的固定 fixture registry，并让 renderer / runtime 回归矩阵从同一登记表取得阶段清单和样例数据。
- 上一轮状态：第 7 轮补充 `ai4se-visual` 写入前校验已完成并通过全量验证，提交 `6ad81d98` 已推送。

改道条件检查：

- 新 P0/P1 或用户新目标：无。其他活跃 todo 中 Alex handoff、partial streaming、strategy chart hardening 已完成。
- 未关闭质量门：无。上一轮非沙箱 `./scripts/test/test-local.sh all` 退出码为 `0`。
- LLM judge：本轮不启用或引用新的真实模型 / judge 分数。
- 架构冲突：无。本轮只改共享后端测试基线和文档，不新增 agent / workflow 专属 runtime、API、store 或渲染管线。
- 子智能体决策：已尝试派发只读 explorer；第一次参数格式错误未生成 agent，第二次成功派发 `Dirac`，范围为第 8 轮证据缺口审查。`Dirac` 返回结论：已有 21 阶段 streaming / renderer / contract 覆盖，但缺少机械证明手写 21 阶段矩阵等于 manifest / backend 阶段集合，且缺少 manifest `visualContract` 与后端 required Mermaid / structured visual maps 的反向同步测试。本轮纳入这些审查结论。

结论：继续承接第 8 轮，不升级为完整 CGA。

## Brainstorming 自问自答

### Explore Project Context

当前系统已有 21 个在线 `artifact_data` 阶段。`docs/TESTING.md` 已文档化这些阶段的 streaming、partial renderer 和 contract 验证口径；`test_agent_runtime.py` 手写了 `ARTIFACT_DATA_STREAMING_STAGES`；`test_artifact_data_renderers.py` 分散定义了 `VALID_*_ARTIFACT_DATA` 样例，并用多组局部测试验证 renderer。缺口是这些样例没有被提升为单一登记表，因此新增阶段或改动 runtime 支持列表时，可能只更新其中一处，导致第 8 轮所谓“全工作流回归门禁”仍依赖人工同步。

旁路审查还指出：`workflow_manifest.json` 已为各阶段声明 `visualContract`，但当前同步测试只验证前端模板包含后端 required visual 示例，没有反向证明 manifest `visualContract` 与后端 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` / `REQUIRED_ARTIFACT_STRUCTURED_VISUALS` 完全一致。该漂移风险也属于第 8 轮回归门禁缺口。

### Visual Companion Decision

本轮是后端测试基线和文档收口，不涉及 UI 视觉设计问题，不需要视觉伴随工具。

### Clarifying Questions

1. 用户是谁？
   - 后续维护 New Agents workflow / artifact_data contract 的工程师，以及目标模式后续轮次。
2. 用户要完成什么动作？
   - 当新增或修改在线 `artifact_data` 阶段时，能通过一个固定 fixture registry 看到该阶段是否具备样例、确定性渲染、contract 验证和 raw JSON streaming 覆盖。
3. 成功状态是什么？
   - 所有 `supports_artifact_data_rendering()` 返回 true 的阶段都必须存在 registry fixture；registry fixture 能渲染为正式 artifact，并通过 `validate_agent_turn()`；runtime instruction 阶段矩阵不再维护独立手写阶段列表；manifest `visualContract` 与后端 visual contract maps 不允许漂移。
4. 失败路径是什么？
   - 若新增支持阶段但未补 fixture，测试必须失败并指出缺失 stage key；若 fixture 无法渲染或 contract 失败，聚焦测试失败，不允许把缺口留到人工检查。
5. 不做什么？
   - 不迁移 20 个阶段的 `artifactDataContract` 到 manifest；不改生产 runtime 行为；不引入真实模型 smoke；不改变第 7 轮视觉运行时门禁。

### Approaches

推荐方案：在后端测试层建立 `ARTIFACT_DATA_STAGE_FIXTURES` 单一登记表，并补充 manifest visual contract 反向同步测试。

- 优点：小而厚，直接服务第 8 轮回归门禁；能用 TDD 快速落地；不改变生产行为；既防 fixture / streaming stage 漏登记，也防 manifest visual contract 与后端 contract 漂移；后续可逐步承接 artifactDataContract 单源同步。
- 缺点：仍是测试侧 registry，不解决生产代码里 renderer 分支和 instruction 分支重复的问题。

备选方案 A：立即把 21 个阶段的 `artifactDataContract` 全部迁入 `workflow_manifest.json`。

- 优点：更接近最终单源同步目标。
- 缺点：一次性触碰大量 workflow contract / prompt / manifest，破坏面大，不适合作为当前连续目标模式切片。

备选方案 B：只更新 `docs/TESTING.md` 表格。

- 优点：成本最低。
- 缺点：不能形成可执行门禁，无法防止回退。

## 设计

### Architecture

在 `tools/new-agents/backend/tests/test_artifact_data_renderers.py` 中新增测试侧 registry：

- key 为 `(workflow_id, stage_id)`。
- value 至少包含 `artifact_data` 固定样例；后续可扩展为 `expected_markers`、`stream_member_names`、`stage_action`。
- registry 必须覆盖所有 `agent_runtime.supports_artifact_data_rendering()` 支持的 stage key。

`test_agent_runtime.py` 的 `ARTIFACT_DATA_STREAMING_STAGES` 从 registry keys 派生，避免 runtime instruction 顺序测试和 renderer fixture 覆盖测试各自维护阶段列表。

`test_workflow_contract_sync.py` 新增反向同步测试，从 `workflow_manifest.json` 提取每个 stage 的 `visualContract.requiredMermaidDiagrams` 和 `visualContract.requiredStructuredVisuals`，分别与后端 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` / `REQUIRED_ARTIFACT_STRUCTURED_VISUALS` 精确比较。

### Components

- `test_artifact_data_renderers.py`
  - 新增 `ARTIFACT_DATA_STAGE_FIXTURES`。
  - 新增 `test_artifact_data_stage_fixture_registry_covers_runtime_supported_stages`。
  - 新增 `test_artifact_data_stage_fixture_registry_renders_contract_valid_outputs`。
- `test_agent_runtime.py`
  - 从 registry 派生 `ARTIFACT_DATA_STREAMING_STAGES`。
- `test_workflow_contract_sync.py`
  - 新增 manifest visual contract 与后端 visual maps 的反向同步测试。
- `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
  - 记录第 8 轮首个回归门禁切片、RED / GREEN / 验证证据和残余风险。

### Data Flow

1. 测试读取 `WORKFLOW_STAGES` 与 `supports_artifact_data_rendering()` 计算当前 runtime 支持的 artifact-data stage keys。
2. 测试比较该集合与 `ARTIFACT_DATA_STAGE_FIXTURES` keys。
3. 每个 fixture 经 `render_agent_turn_from_artifact_data()` 转为 `AgentTurnOutput`。
4. 测试调用 `validate_agent_turn()` 证明渲染结果满足当前工作流 artifact contract。
5. runtime instruction 顺序测试使用 registry keys 参数化，防止新增支持阶段漏掉 visible streaming instruction 门禁。
6. manifest visual contract sync 测试读取 manifest stage visual contract，并与后端 required visual maps 做双向精确比较。

### Error Handling

- 缺 fixture：测试失败，输出缺失 stage key。
- fixture 无效：Pydantic validation 或 contract validation 失败。
- renderer 未配置：`render_agent_turn_from_artifact_data()` 抛出未配置错误。
- manifest / backend visual contract 漂移：同步测试失败，输出差异 stage key 和 visual type 列表。

### Testing

本轮按 TDD 执行：

1. 先新增 registry 覆盖测试并运行，预期因 `ARTIFACT_DATA_STAGE_FIXTURES` 不存在而失败。
2. 新增 registry 并接入 runtime test 阶段列表。
3. 先新增 manifest visual contract sync 失败测试并运行，预期当前代码缺少该测试而 RED。
4. 运行聚焦后端测试：
   - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_covers_runtime_supported_stages tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_stage_fixture_registry_renders_contract_valid_outputs -q`
   - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming -q`
   - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_shared_workflow_manifest_visual_contract_matches_backend_required_visuals -q`
5. 扩大到 New Agents 后端相关回归：
   - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q`
5. 收尾前按 goal-mode playbook 运行全量本地验证或记录环境阻塞。

## Scope Review

本轮是工程信任闭环，不是用户可见 UI 功能。它解除的是第 8 轮最大的证据缺口：所有在线 `artifact_data` 阶段的固定回归样例必须被一个可执行矩阵统一证明，且 manifest visual contract 不能与后端 required visual maps 漂移。完成后，后续维护者现在可以新增 artifact-data 阶段时被测试立即提醒补齐 fixture、renderer、contract 和 streaming instruction 覆盖，也会在修改 manifest 可视化契约时被测试提醒同步后端 contract。
