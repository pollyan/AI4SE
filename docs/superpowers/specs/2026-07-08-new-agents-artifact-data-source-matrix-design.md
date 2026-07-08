# New Agents Artifact Data Source Matrix Design

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/index.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-ci-verification.md`、`docs/TESTING.md`、`docs/todos/*.md`、`docs/superpowers/specs/2026-07-08-new-agents-artifact-data-regression-fixture-registry-design.md`、`docs/superpowers/plans/2026-07-08-new-agents-artifact-data-regression-fixture-registry.md`、`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`、`tools/new-agents/backend/tests/test_agent_contracts.py`、`tools/new-agents/backend/tests/test_workflow_contract_sync.py`、`tools/new-agents/workflow_manifest.json`。
- 当前工作区：`git status -sb` 干净，`HEAD` 与 `origin/codex/structured-failure-diagnostics` 同步。

已确认目标来源：

- 来源：`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` 第 8 轮“全工作流失败回归门禁与文档收口”。
- 本轮承接：第 8B 轮文档收口矩阵，消化第 8A 残余风险“模型输出字段 / 后端派生字段 / 视觉协议来源的完整全阶段矩阵仍属第 8 轮后续文档收口候选”。
- 上一轮状态：第 8A 轮 `ARTIFACT_DATA_STAGE_FIXTURES`、runtime instruction matrix 和 manifest visualContract reverse sync 已完成，提交 `25614c84` 已推送。

改道条件检查：

- 新 P0/P1 或用户新目标：无。`docs/todos/` 中 strategy chart hardening 已完成，partial streaming 已完成实现与文档收口，Alex requirement-to-user-story handoff 已完成；当前唯一执行中 P0 是结构化产出失败治理。
- 未关闭质量门：无。上一轮非沙箱 `./scripts/test/test-local.sh all` 退出码为 `0`；默认沙箱失败已记录为端口 / Chromium 权限限制。
- LLM judge：本轮不启用或引用新的真实模型 / judge 分数。
- 架构冲突：无。本轮只更新测试策略文档和 todo 状态，不新增 Lisa/Alex/workflow 专属 runtime、API、store 或渲染管线。
- 工作区冲突：无未提交变更。
- 子智能体 / 旁路审查决策：已派发只读 explorer `019f4147-43b5-78e0-8e71-070bb0490c3e`，范围为 21 个 artifact-data 阶段的模型字段、后端派生字段和视觉来源审查。主 Agent 并行推进文档设计，待 explorer 返回后用于校准矩阵和残余风险。

结论：继续承接第 8 轮，不升级为完整 CGA。

## Brainstorming 自问自答

### Explore Project Context

第 8A 轮已经把全阶段 fixture、renderer contract、runtime instruction stage list 和 manifest visualContract reverse sync 变成可执行门禁。当前缺口不在运行时，而在工程认知：后续维护者无法从一个稳定文档快速判断每个阶段的 `artifact_data` 中哪些字段仍由模型负责，哪些字段已由后端确定性派生，哪些视觉是 `ai4se-visual` 结构化协议，哪些仍是后端从结构化数据编译出的 Mermaid。

如果缺少这个矩阵，后续继续做“可计算字段后端化”“ID 与引用关系收敛”“视觉协议分层”时，很容易重复调研或误把 validation gate 当作 derived field。本轮文档收口能把第 8 轮剩余的证据描述补齐，同时保持不扩大运行时改动范围。

### Visual Companion Decision

本轮是文档矩阵和测试策略说明，不涉及 UI 视觉设计问题，不需要视觉伴随工具。

### Clarifying Questions

1. 用户是谁？
   - 后续维护 `artifact_data` contract、prompt、renderer 和测试矩阵的工程师，以及继续目标模式治理的 Agent。
2. 用户要完成什么动作？
   - 在一个位置查清 21 个在线阶段的模型输入职责、后端派生职责、视觉生成来源和证明证据。
3. 成功状态是什么？
   - `docs/TESTING.md` 有全阶段矩阵；`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` 记录第 8B 完成证据；文档明确不把 validation-only 误称为后端派生，不把 Mermaid 编译目标误称为模型直写。
4. 失败路径是什么？
   - 如果后续字段来源或 visual contract 变化，矩阵可能过期；因此本轮必须同时记录维护入口：以 `ARTIFACT_DATA_STAGE_FIXTURES`、`REQUIRED_ARTIFACT_MERMAID_DIAGRAMS`、`REQUIRED_ARTIFACT_STRUCTURED_VISUALS`、renderer tests 和 `workflow_manifest.json` 为事实源。
5. 不做什么？
   - 不迁移 20 个阶段的 `artifactDataContract` 到 manifest；不新增 backend Mermaid JS parse 或 `mmdc`；不修改生产 renderer、schema、prompt 或前端运行时；不声称所有派生字段都已后端化。

### Approaches

推荐方案：在 `docs/TESTING.md` 增加“artifact_data 字段来源与视觉协议矩阵”，并在 todo 中记录第 8B 的执行证据。

- 优点：直接消化第 8A 残余文档缺口；不改变运行时；后续目标模式能以该矩阵做下一轮 CGA 输入。
- 缺点：矩阵是人工维护文档，不能替代第 8A 已建立的可执行门禁。

备选方案 A：把矩阵生成成 Python 脚本或测试输出。

- 优点：更自动化，降低过期风险。
- 缺点：当前字段来源包含大量人工语义判断，例如 validation-only 与 derived field 的区别，脚本无法可靠推断；会把本轮从文档收口扩大成工具开发。

备选方案 B：立即迁移全部 `artifactDataContract`。

- 优点：更接近 schema / prompt / contract 单源同步终态。
- 缺点：一次性触碰 20 个阶段的 manifest、prompt 和同步测试，破坏面过大，不适合作为第 8B 文档收口切片。

## 设计

### Architecture

本轮只更新目标模式和测试策略文档：

- `docs/TESTING.md`：在第 8 轮 fixture registry 段落之后新增矩阵，列出每个 stage 的模型负责字段、后端派生字段、后端视觉生成来源、现有证据。
- `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`：更新顶部状态、第 8 轮条目进展和第 8B 执行记录。
- `docs/superpowers/specs/...` 与 `docs/superpowers/plans/...`：保存本轮设计和执行步骤。

### Matrix Columns

矩阵列固定为：

- `Workflow / Stage`
- `模型负责的 artifact_data`
- `后端派生 / 归一化`
- `视觉来源`
- `证据`

矩阵中的判断规则：

- “模型负责”只描述模型仍需输出的语义字段或原子事实，不逐字段穷举每个文本字段。
- “后端派生 / 归一化”只记录后端实际计算、补齐或规范化的字段；纯 validator 拒绝重复 ID、未知引用或统计不一致时，写成“校验，不派生”。
- “视觉来源”必须区分 `ai4se-visual` 与 Mermaid；如果 Mermaid 是后端 deterministic renderer 从结构化数据生成，明确写“后端由 X 生成 Mermaid Y”，不能写成模型直接输出 Mermaid。
- “证据”引用测试名、contract map 或 manifest sync，而不是口头判断。

### Error Handling

文档不改变 runtime 失败行为。矩阵必须保留以下失败边界：

- `SCHEMA_VALIDATION_FAILED`、artifact contract failure 和 visual validation failure 仍必须显式失败。
- 第 8B 不新增 fallback、草稿成功、自动 repair 成功路径或视觉缓存替代路径。
- `artifactDataContract` 仍只有 `IDEA_BRAINSTORM/CONVERGE` 完成 manifest 同步迁移，其他阶段不能在文档中写成已完成。

### Testing

本轮是纯文档切片，不运行全量代码测试，使用文档核对清单：

1. `git diff --check -- docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/superpowers/specs/2026-07-08-new-agents-artifact-data-source-matrix-design.md docs/superpowers/plans/2026-07-08-new-agents-artifact-data-source-matrix.md`
2. `rg -n "T[B]D|T[O]DO|implement[ ]later|<填[入]|待[补]" docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/superpowers/specs/2026-07-08-new-agents-artifact-data-source-matrix-design.md docs/superpowers/plans/2026-07-08-new-agents-artifact-data-source-matrix.md`
3. `rg -n "模型负责的 artifact_data|后端派生 / 归一化|视觉来源|第 8B" docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
4. `git status -sb`、`git diff --shortstat`、`git diff --cached --name-only` 做提交归属检查。

因为本轮不改代码、manifest、测试或运行时，`./scripts/test/test-local.sh all` 按 playbook 纯文档例外不运行；上一轮第 8A 已在最终代码状态下完成非沙箱全量验证。

## Scope Review

本轮是工程信任闭环，不是用户可见 UI 功能。完成后，维护者现在可以在 `docs/TESTING.md` 一次性看到 21 个 artifact-data 阶段的字段来源和视觉协议来源，后续继续做可计算字段后端化、ID 收敛、`artifactDataContract` 迁移或 `mmdc` 门禁时，不需要重新从大型 renderer 文件中人工拼事实，也不容易把 validation gate 误读成后端派生能力。
