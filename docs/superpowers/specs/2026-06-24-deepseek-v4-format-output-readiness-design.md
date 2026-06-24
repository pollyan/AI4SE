# DeepSeek V4 格式化输出信任闭环设计

## 背景

`docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 的核心目标是让 DeepSeek V4 Flash 只输出 JSON 业务数据，由后端确定性渲染 Markdown、Mermaid 和 `ai4se-visual`。当前 `TEST_DESIGN`、`REQ_REVIEW`、`VALUE_DISCOVERY`、`INCIDENT_REVIEW`、`IDEA_BRAINSTORM` 共 17 个在线 stage 已逐步迁移到 `artifact_data`，代码中也已有逐 stage renderer 和 runtime 测试。

剩余缺口不是继续迁移单个 stage，而是缺少一个全局可复验的完成门禁：后续新增或修改 workflow/stage 时，必须能自动证明它没有回退到“模型直接拼完整 Markdown/Mermaid/表格”的旧格式化模式。

## Superpowers 头脑风暴自问自答

### Explore Project Context

- 问：当前代码和文档说明了什么？
  答：DeepSeek todo 已记录 17 个 stage 完成结构化产物迁移；`agent_runtime.py` 的 `supports_artifact_data_rendering()`、`build_structured_output_instruction()` 和 `artifact_data_renderers.py` 的 renderer 分派都覆盖这些 stage。`test_agent_runtime.py` 已有逐 stage streaming/rendering 测试，基线运行结果是 85 passed。
- 问：当前需求是否过大？
  答：不能再按单 stage 迁移切片推进，否则粒度过小；也不能把真实模型 smoke、prompt 版本治理和专业方法库一起并入，否则需要外部凭证或扩大为平台工程。合适边界是本地确定性 readiness gate。
- 问：当前 git 风险是什么？
  答：主工作区有未提交文档和 zip 改动；本轮在独立 worktree `codex/deepseek-v4-format-output-readiness` 中执行，避免覆盖主工作区。

### Visual Companion Decision

- 问：是否需要视觉辅助？
  答：不需要。本轮不改变 UI 布局或交互视觉，关注后端格式化输出链路、测试门禁和 todo 状态记录。

### Clarifying Questions

- 问：真实用户是谁？
  答：使用 New Agents 且主要依赖 DeepSeek V4 Flash 的本地开发/演示用户，以及后续维护 workflow/stage 的工程人员。
- 问：用户要完成什么？
  答：确认 DeepSeek V4 不再承担最终产物格式化职责；模型只输出合法 JSON 业务数据，后端统一生成完整 Markdown、Mermaid 和结构化视觉块。
- 问：成功状态是什么？
  答：有一条本地自动化测试矩阵覆盖全部在线 stage，证明每个 stage 都支持 `artifact_data`、instruction 不要求 `artifact_update.markdown`、retry prompt 要求修 `artifact_data` 而不是重写 Markdown、renderer 输出能通过现有 artifact contract。
- 问：输入来源是什么？
  答：权威 stage 列表来自 `agent_contracts.WORKFLOW_STAGES`，渲染和 contract 使用当前测试 fixture 与 `validate_agent_turn()`。
- 问：失败路径是什么？
  答：新增 stage 未加 renderer、instruction 回退到文本模式、retry prompt 继续要求 Markdown、renderer 输出不满足 artifact contract，都应在本地 pytest 中失败。
- 问：下游如何承接？
  答：该 gate 作为 DeepSeek 格式化输出完成证据，后续新增 workflow/stage 或 prompt 版本治理可复用它判断是否破坏格式化边界。
- 问：本轮不做什么？
  答：不调用真实 DeepSeek，不新增 runtime/API/store/renderer，不重构所有 renderer，不做 E05 章节级重生成，不合并所有历史 worktree。

### Approaches

1. 推荐方案：在 `test_agent_runtime.py` 添加 manifest/stage matrix readiness gate。
   - 优点：最小侵入，直接覆盖真实 runtime 分派、retry prompt 和 artifact contract；不改变产品行为。
   - 代价：仍复用现有 fixture，不等同于真实 DeepSeek smoke。
2. 备选方案：新增生产代码 registry，把支持 stage、instruction、fixture/schema 全部集中声明。
   - 优点：长期可维护性更强。
   - 代价：会触及 runtime 分派结构，风险高于本轮“完成证明”目标。
3. 备选方案：运行真实 DeepSeek V4 Flash smoke 并记录证据。
   - 优点：外部模型信心最高。
   - 代价：需要凭证、网络和额度，不符合目标模式默认自动执行边界。

推荐方案是 1；它用最小代码面补足当前真正缺少的本地防回归证据，真实 smoke 继续作为可选发布前验证。

### Presented Design

- Architecture：沿用共享 Agent Runtime、DeepSeek `json_object_only` capability、现有 `artifact_data` renderer、`AgentTurnOutput`、artifact contract 和 pytest；不新增 DeepSeek 专属路径。
- Components：
  - `test_agent_runtime.py` 增加 stage matrix fixture，列出全部在线 stage 与对应 `artifact_data` fixture。
  - 新增测试确保全部在线 stage 均支持 `artifact_data` renderer。
  - 新增测试确保全部在线 stage 的 structured instruction 请求 `artifact_data`，且不请求 `artifact_update.markdown`、完整 Markdown、Mermaid 代码块或表格。
  - 新增测试确保全部在线 stage 的 retry prompt 进入数据纠错路径。
  - 新增测试确保全部在线 stage 的 renderer 输出通过 `validate_agent_turn()`。
- Data Flow：stage matrix -> `supports_artifact_data_rendering()` / `build_structured_output_instruction()` / `build_raw_json_retry_prompt()` / `render_agent_turn_from_artifact_data()` -> `validate_agent_turn()`。
- Error Handling：任何 stage 缺 renderer、缺 instruction、误用 Markdown retry 或 renderer 输出契约失败，pytest 直接失败并指出 workflow/stage。
- Testing：遵循 TDD，先加入失败测试，确认当前缺少全局 gate 或断言失败；再做最小实现。若当前代码已满足 gate，则实现可能只保留测试和 todo completion 记录。

## 用户故事

作为主要使用 DeepSeek V4 Flash 的 New Agents 用户，我希望系统能自动证明所有在线 workflow stage 都不再要求模型直接生成完整 Markdown/Mermaid/表格，而是由后端确定性渲染最终产物，从而降低“格式不完整 / 结构化输出生成失败”的回归风险。

## 范围

本轮包含：

- 添加 DeepSeek V4 格式化输出 readiness gate。
- 复用现有 `artifact_data` fixture 验证全部在线 stage 的 renderer 输出能通过 artifact contract。
- 验证 structured instruction 和 retry prompt 都保持数据纠错边界。
- 更新 DeepSeek todo 和 README 状态，明确结构化格式化输出改造已完成，真实 DeepSeek smoke 仍是显式凭证条件下的可选验证。

本轮不包含：

- 不调用真实 DeepSeek V4 Flash。
- 不新增 workflow、agent、runtime、API path、store 或 renderer。
- 不合并历史 worktree。
- 不处理 E05/E10/E11/E12 等 New Agents 后续增强。

## 验收条件

1. Given 当前在线 workflow stage 列表  
   When 运行 readiness gate  
   Then 每个 stage 都必须命中 `supports_artifact_data_rendering()`。

2. Given 任一在线 workflow stage  
   When 构造 structured output instruction  
   Then instruction 必须要求 `artifact_data`，且不得要求 `artifact_update.markdown`、完整 Markdown、Mermaid 代码块或表格由模型输出。

3. Given 任一在线 workflow stage 的 schema/contract 错误  
   When 构造 raw JSON retry prompt  
   Then prompt 必须要求修正 `artifact_data`，不得要求重写 Markdown。

4. Given 任一在线 workflow stage 的有效 `artifact_data` fixture  
   When 后端 renderer 生成 `AgentTurnOutput`  
   Then 输出必须通过 `validate_agent_turn()`。

5. Given DeepSeek V4 Flash model name  
   When runtime resolve capability / settings  
   Then 继续使用 `response_format={"type":"json_object"}`，thinking disabled，且不使用 strict JSON Schema 参数。

## 验证计划

- RED/GREEN 聚焦测试：`/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q`
- Renderer contract 回归：`/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_contracts.py -q`
- Python 语法：`/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py`
- Whitespace：`git diff --check`

## 风险

- 本地 readiness gate 不能替代真实 DeepSeek smoke；真实 smoke 仍依赖 API key、网络和额度。
- 测试 fixture 证明确定性 renderer 与 contract 正确，不证明模型在真实上下文下一定能一次生成合格 JSON。
- `supports_artifact_data_rendering()` 与 `build_structured_output_instruction()` 仍是手工分派；本轮先加门禁防回归，不做 registry 重构。

## Spec 自检

- Placeholder scan：无 `TODO` / `TBD` / 未决占位。
- 一致性检查：设计只扩展本地测试和文档，不改变 runtime 行为。
- 范围检查：单一 milestone，聚焦 DeepSeek V4 格式化输出信任闭环。
- 歧义检查：真实模型 smoke 明确为非默认门禁，需要凭证时另行执行。
