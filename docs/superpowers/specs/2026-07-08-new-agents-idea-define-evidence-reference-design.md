# New Agents IDEA DEFINE 证据引用稳定化设计

## 目标承接检查

事实源快照：

- 已读取 `AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-ci-verification.md`、`docs/TESTING.md`。
- 已读取当前待办 `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` 与已完成路线 `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`。
- 已读取 `tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/agent_runtime.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py` 中 `IDEA_BRAINSTORM/DEFINE` 相关实现和测试。
- 当前工作区存在大量无关删除、修改和未跟踪文件，按 playbook 保护，不纳入本轮提交。

已确认目标来源：

- 来源：`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` 第 4 轮。
- 本轮承接：`IDEA_BRAINSTORM/DEFINE` 根问题与证据一致性治理。
- 上一轮状态：第 3 轮首个 `VALUE_DISCOVERY/ELEVATOR` 派生字段后端化已完成并提交推送；DeepSeek tool calling 第 0 轮仍保留为独立 spike，不改变当前正式 workflow 主链路。

改道条件检查：

- 用户新增反馈：目标模式完成独立价值后要批量验证、commit 并 push。当前 playbook 已包含该规则，本轮继续遵守。
- 新 P0/P1：无新的生产阻断；当前打开 P0 仍是结构化产出失败治理。
- 外部阻塞：DeepSeek tool calling spike 需要外部 provider 事实和可能的真实模型调用，不适合作为当前不依赖外部条件的主线实现切片。
- 架构冲突：本轮继续复用共享 Agent Runtime、artifact_data schema、deterministic renderer、typed SSE 和现有测试矩阵，不新增 Alex 专属 runtime / API / store / renderer。

结论：继续承接第 4 轮，但把切片收敛为 `IDEA_BRAINSTORM/DEFINE` 的 root problem、evidence、problem-user-fit 引用稳定化。

## Brainstorming 自问自答

Explore Project Context：

- 当前 `IdeaDefineArtifactData` 已有严格 schema、重复 ID 检查、`problem_user_fit.evidence_ids` 引用检查、stage gate 检查。
- 真实失败样本集中在 `IDEA_BRAINSTORM/DEFINE`，已有记录显示 partial streaming 能提前输出，但最终因 root-problem 覆盖 contract 失败。
- 现有 root coverage 依赖 `root_problem in evidence_items.related_problem` 或 `root_problem in problem_user_fit.evidence_or_assumption`，这要求模型复制完整中文文本，脆弱且不符合“模型只输出语义事实，后端维护引用一致性”的治理方向。

Clarifying Questions：

- 用户是谁：使用 Alex 从模糊 idea 梳理问题域的产品经理或创业者。
- 成功状态：模型不用原样复制根问题文本，也能通过稳定 ID 表达“哪些证据支撑根问题”；后端能严格校验引用完整性和 root coverage。
- 输入来源：`IDEA_BRAINSTORM/DEFINE` 的结构化 `artifact_data`。
- 失败路径：未知 evidence id、未知 problem id、缺少 root problem 支撑证据、重复 ID、无 checked stage gate 继续显式失败。
- 下游承接：右侧 Markdown、Mermaid mindmap、partial artifact streaming、最终 contract 和 run persistence 仍消费同一 normalized artifact_data。
- 不做事项：不放宽 schema、不用 fallback 草稿、不让模型手写 Mermaid、不接入 DeepSeek tool calling。

Approaches：

1. 推荐方案：给 `problem_landscape` 增加稳定 `root_problem_id`，给 `evidence_items` 增加 `related_problem_ids`，后端校验这些 ID 只能引用 root 或 subproblem，且至少一条 evidence 必须引用 root。`problem_user_fit` 继续通过 `evidence_ids` 引用 evidence，形成 `problem_user_fit -> evidence -> root/subproblem` 的链路。
2. 备选方案：继续保留字符串包含校验，只在 prompt 里进一步强调复制 root problem。这个改动小，但真实失败已经证明模型仍会漂移，不解决结构性问题。
3. 备选方案：完全由后端根据语义相似度自动匹配 root problem 和 evidence。这个会引入非确定性或启发式，难以解释，且可能掩盖模型输出缺失。

采纳方案 1。它把脆弱的中文文本复制要求改成稳定 ID 引用要求，同时仍保持严格失败。

## 设计

### Schema

`IdeaProblemLandscape` 增加 `root_problem_id`，模型输出建议使用 `P-ROOT`。`IdeaEvidenceItem` 增加 `related_problem_ids: list[str]`，每个值必须等于 `root_problem_id` 或存在于 `problem_landscape.subproblems[].problem_id`。

后端 validator 执行：

- `evidence_items.evidence_id` 唯一。
- `problem_landscape.root_problem_id` 不能与 subproblem id 重复。
- `problem_landscape.subproblems.problem_id` 唯一。
- `evidence_items.related_problem_ids` 不能引用未知 problem id。
- 至少一个 evidence item 的 `related_problem_ids` 包含 `root_problem_id`。
- `problem_user_fit.evidence_ids` 只能引用已存在 evidence id。
- 至少一个 problem-user-fit 条目必须引用到支撑 root problem 的 evidence id。
- `stage_gate` 至少一个 checked。

### Rendering

Markdown 仍以用户可读内容为主，但在问题域和证据表中展示稳定 ID：

- 问题域全景表增加 root problem 行，显示 `root_problem_id`、根问题文本和类型。
- 证据表增加“关联问题 ID”，并继续保留“关联问题”自然语言描述，避免用户只看到机器 ID。
- 问题-用户-场景匹配仍展示关联证据 ID；其 root coverage 由后端通过 evidence chain 校验。

### Prompt / Runtime

`IDEA_DEFINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` 同步结构：

- 示例中加入 `root_problem_id` 和 `related_problem_ids`。
- 删除“原样包含 root_problem”的要求。
- 明确模型使用 ID 维护覆盖关系，后端负责确定性渲染和校验。

### Partial Streaming

partial renderer 在 `problem_landscape` 关闭时可先渲染问题域；在 `evidence_items` 关闭后可渲染证据表。若 evidence item 中出现未知 problem id，partial renderer 不输出该新章节，最终 full validation 仍显式失败。

### 验收

1. 给出一个不再原样复制 `root_problem` 文本、但通过 `related_problem_ids=["P-ROOT"]` 与 `problem_user_fit.evidence_ids=["EV-001"]` 建立 root coverage 的 payload，`IdeaDefineArtifactData` 应通过校验。
2. evidence 引用未知 problem id 时，`IdeaDefineArtifactData` 应显式失败。
3. 没有任何 evidence 引用 root problem id 时，`IdeaDefineArtifactData` 应显式失败。
4. prompt 不再要求模型原样包含 root problem，而要求输出 `root_problem_id` / `related_problem_ids`。
5. `render_agent_turn_from_artifact_data` 和 raw JSON streaming 测试继续生成合法 DEFINE artifact，且最终 contract 通过。

## 风险

- 这是当前 `IDEA_BRAINSTORM/DEFINE` 的 schema 变更，旧测试 fixture 需要同步更新。旧 run 的 Markdown snapshot 不受影响；后续重新用旧 artifact_data 走 renderer 时会按新 contract 校验失败，这是严格 contract 的预期行为。
- 本轮不声称真实 DeepSeek 成功率已提升到某个数值；只证明已知脆弱 contract 被确定性 ID 引用替代。
