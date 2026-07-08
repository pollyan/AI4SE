# New Agents Value Elevator 评分汇总后端化设计

## 目标承接检查

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/TESTING.md`、`docs/api-contracts.md`。
- 已读取：`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`、`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`、`docs/todos/2026-06-25-new-agents-strategy-chart-generator-schema-hardening.md`。
- 已读取：`tools/new-agents/backend/agent_runtime.py`、`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`。
- 工作区状态：存在大量无关删除和修改，包括 `.agent/`、`.claude/`、`.opencode/`、`_bmad/`、`README.md`、`docs/index.md`、intent-tester 生成包和 `docs/mockups/`；本轮只触碰 New Agents 结构化产出失败治理相关文件，不回滚、不格式化、不 stage 无关改动。

承接结论：
- 当前 P0 待办是 `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`。
- 第 1 轮结构化失败诊断透明化和第 2 轮严格失败闭环已完成。
- 第 0 轮 DeepSeek tool-calling spike 是能力研究，不改变正式 workflow 主链路；当前主线更需要先降低模型结构化输出中的可计算字段负担。
- 本轮承接第 3 轮“可计算字段后端化首个纵切”，选择 `VALUE_DISCOVERY/ELEVATOR` 的 `score_summary.total_score` 和 `score_summary.average_score`，因为它们由 `score_matrix[].score` 完全派生，且与 Alex 需求梳理链路更贴近。

质量门与改道检查：
- 未发现新的 LLM judge 低于 80 分记录需要先改道。
- 已完成的 Alex `VALUE_DISCOVERY/BLUEPRINT -> USER_STORY_BREAKDOWN` handoff 不在本轮回改范围。
- `TEST_DESIGN/STRATEGY` 的 `rpn` 已完成后端派生，作为本轮复用模式。

子智能体 / 旁路审查决策：
- 不分发子智能体。本轮修改集中在同一后端 schema、prompt 和测试文件，且当前工具约束下没有用户明确要求启动子智能体；并行写入会增加冲突风险。

## 用户故事

作为 Alex 价值发现工作流用户，当我在价值定位阶段生成右侧价值定位分析时，我希望模型只输出评分维度、分数、依据和结论判断，不再负责计算总分和平均分；系统由后端确定性计算汇总并生成正式 artifact，从而减少结构化校验失败，同时在错误输入时仍显式失败。

## 验收条件

1. Given `VALUE_DISCOVERY/ELEVATOR` 的 `artifact_data.score_matrix` 有合法评分且 `score_summary` 只包含 `judgement`
   When 后端解析并渲染最终 artifact
   Then `score_summary.total_score` 与 `score_summary.average_score` 由后端计算，评分表、`score-matrix` 视觉块和评分结论正常渲染。

2. Given 模型仍显式输出错误的 `score_summary.total_score` 或 `score_summary.average_score`
   When 后端验证 artifact data
   Then 继续抛出字段级 `ValidationError`，不持久化正式产物、不生成假成功结果。

3. Given raw JSON streaming 在 final `agent_turn` 前已闭合 `score_matrix` 和 `score_summary`
   When 共享 Agent Runtime 生成 partial artifact delta
   Then 右侧 partial Markdown 可包含评分章节，且 final artifact 仍通过完整 contract。

4. Given 构建 `VALUE_DISCOVERY/ELEVATOR` structured output instruction
   When 模型读取输出要求
   Then prompt 示例不再要求输出 `total_score` 和 `average_score`，并明确总分、平均分由后端根据 `score_matrix` 计算。

## Brainstorming 自问自答

Explore Project Context：
- New Agents 必须复用共享 Agent Runtime、typed SSE、artifact renderer、run persistence、workflow manifest 和前端 store。
- `VALUE_DISCOVERY/ELEVATOR` 当前 schema 要求模型输出 `score_summary.total_score`、`average_score` 和 `judgement`，后端再校验它们与 `score_matrix` 一致。
- `STRATEGY` 已有 `rpn` 可选输入、缺省时后端派生、显式错误时失败的模式，可作为直接参考。
- `docs/TESTING.md` 已把 `VALUE_DISCOVERY/ELEVATOR` 纳入 partial streaming 覆盖矩阵；本轮不能破坏 `score_matrix + score_summary` 成对渲染。

Clarifying Questions：
- 用户是谁？使用 Alex 价值发现流程梳理产品价值定位的人。
- 用户要完成什么？拿到可继续画像和需求蓝图的价值定位分析。
- 成功状态是什么？右侧 artifact 中评分总分和平均分稳定出现，但模型不再承担计算一致性。
- 失败路径是什么？显式错误汇总、非法评分、空字段、未知 value flow 引用继续失败。
- 下游承接是什么？PERSONA/JOURNEY/BLUEPRINT 和后续 user story handoff 继续消费规范化后的 artifact data。
- 不做什么？不接入 DeepSeek tool calling，不改前端 store，不新增 workflow 专属 runtime，不用 fallback 草稿隐藏失败。

Approaches：
- 方案 A：将 `ValueScoreSummary.total_score` 和 `average_score` 改为可选输入，validator 缺省时计算，显式错误时失败，并同步 prompt 与测试。优点是范围小、复用现有 STRATEGY 模式；缺点是只覆盖一个阶段的一组派生字段。推荐。
- 方案 B：完全移除 `score_summary` 对象，只保留 `judgement` 顶层字段。优点是模型负担更小；缺点是会改动 artifact data contract 形状和下游 snapshot 数据，迁移面更大。
- 方案 C：先做通用派生字段 normalizer 框架。优点是可扩展；缺点是当前只有少数字段需要马上治理，抽象会拖大第 3 轮范围。

Presented Design：
- Architecture：继续使用 `artifact_data -> Pydantic model -> deterministic renderer -> AgentTurnOutput` 链路。
- Components：修改 `ValueScoreSummary`，让 `total_score` 和 `average_score` 可选；修改 `ValueDiscoveryElevatorArtifactData.validate_value_consistency`，缺省时写入计算值，显式错误时保留失败；修改 `VALUE_ELEVATOR_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`。
- Data Flow：模型输出 `score_matrix[].score` 与 `score_summary.judgement`；Pydantic 模型计算 `total_score=sum(score)`、`average_score=round(total/len(score_matrix), 2)`；renderer 使用模型实例中的规范化汇总。
- Error Handling：缺省派生字段合法；显式错误派生字段失败；所有最终失败仍走已有 typed `SCHEMA_VALIDATION_FAILED` 和 diagnostic 链路。
- Testing：先写失败测试覆盖 final parse、schema、runtime instruction 和 partial renderer，再实现最小代码。

## 实现边界

允许写入：
- `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- `docs/superpowers/specs/2026-07-08-new-agents-value-elevator-derived-score-summary-design.md`
- `docs/superpowers/plans/2026-07-08-new-agents-value-elevator-derived-score-summary.md`
- `tools/new-agents/backend/artifact_data_renderers.py`
- `tools/new-agents/backend/agent_runtime.py`
- `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- `tools/new-agents/backend/tests/test_agent_runtime.py`

不触碰：
- Lisa/Alex 专属 runtime、SSE path、frontend store 或 ArtifactPane 通用渲染管线。
- `workflow_manifest.json`，除非后续验证发现 contract 文案必须同步。
- 当前工作区中的无关删除、生成包、mockup 和用户修改。
