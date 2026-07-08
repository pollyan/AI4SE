# TEST_DESIGN STRATEGY 内部引用门禁设计

## 目标承接检查

- 当前目标：继续消化 `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` 中第 6 轮 `TEST_DESIGN/STRATEGY` 剩余高失败阶段。
- 已排除：`docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md` 当前状态为已完成，不作为本轮改动输入。
- 工作区状态：存在大量与本轮无关的用户 / 生成文件脏改动；本轮只允许写入 STRATEGY schema / renderer / prompt / 测试 / 本 spec / 本 plan / 结构化治理 todo。
- 子智能体决策：本片触达范围集中在 New Agents 后端 artifact-data renderer、runtime prompt 和少量 prompt 文案，引用规则需要主线连续 TDD 判断；不分发子智能体。

## 问题

`TEST_DESIGN/STRATEGY` 已经把 `risks.rpn` 改为后端派生，但内部 ID 与引用关系仍主要由模型自由维护：

- `quality_goals.goal_id`、`risks.risk_id`、`test_techniques.technique_id`、`test_points.point_id` 没有统一唯一性校验。
- `test_points.quality_goal`、`test_points.risk`、`test_points.technique` 可以引用不存在的 `QG/R/TS`。
- `test_techniques.target` / `applies_to`、`test_layers.related` 可以写出不存在的 `QG/R/TP`。
- partial renderer 会在后续 `test_points` 尚未到齐时提前展示测试技术或分层章节，导致右侧可能预览最终 validator 应拒绝的引用链。

这会削弱 `STRATEGY -> CASES` 的需求衔接：后续用例设计拿到的是看似完整、但内部追溯不可信的测试策略蓝图。

## 用户故事

作为 Lisa 测试设计用户，我希望测试策略蓝图中的质量目标、风险、测试技术和测试点引用关系在进入用例设计前已经自洽，这样后续生成测试用例时不会基于漂移的 ID 或不存在的风险 / 技术继续扩散错误。

## 设计

本轮采用“引用门禁，不改字段形态”的最小纵切：

1. 后端在 `StrategyArtifactData` 增加 after validator。
2. validator 先校验 `QG/R/TS/TP` 四类 ID 唯一。
3. validator 从自由文本字段中提取形如 `QG-001`、`R-001`、`TS-001`、`TP-001` 的 ID。
4. 下列字段必须至少包含对应类型的一个已存在 ID，且不能包含同类型未知 ID：
   - `test_points[].quality_goal` -> 已存在 `quality_goals[].goal_id`
   - `test_points[].risk` -> 已存在 `risks[].risk_id`
   - `test_points[].technique` -> 已存在 `test_techniques[].technique_id`
   - `test_techniques[].target` -> 已存在 `QG` / `R` / `TP` 中至少一种
   - `test_techniques[].applies_to` -> 已存在 `R` / `TP` 中至少一种
   - `test_layers[].related` -> 已存在 `QG` / `R` / `TP` 中至少一种
5. `strategy_summary.basis`、`quality_goals.source`、`risks.source` 暂不做强校验，因为它们引用的是上游 CLARIFY 阶段事实 / 规则 / 链路 / 问题 ID，不在本阶段结构化模型内。
6. partial renderer 继续允许先展示 `strategy_summary`、`quality_goals` 和 `risks`；`test_techniques`、`test_layers`、`test_points` 必须三者到齐并通过引用校验后，才一起展示章节 4-6。
7. 如果章节 4-6 的引用校验失败，partial renderer 返回上一段可信内容，不预览错误的技术 / 分层 / 测试点章节。
8. structured output instruction 和前端 STRATEGY prompt 增加明确约束：所有 `QG/R/TS/TP` 引用必须引用当前 artifact_data 中已经定义的 ID。

## 非目标

- 不改变 STRATEGY artifact 的 JSON 字段名、Markdown 标题或视觉类型。
- 不把 `quality_goals.source` / `risks.source` 强校验到 CLARIFY 上游 ID。
- 不做后端确定性分配 `QG/R/TS/TP` ID；本轮只校验模型输出的显式 ID 是否自洽。
- 不修改 Lisa handoff、测试资产实体化、ArtifactPane 或共享 Agent Runtime 主链路。

## 验收

- final `StrategyArtifactData` 拒绝重复 `goal_id`、`risk_id`、`technique_id`、`point_id`。
- final `StrategyArtifactData` 拒绝测试点引用不存在的质量目标、风险或测试技术。
- final `StrategyArtifactData` 拒绝测试技术和测试分层引用不存在的 `QG/R/TP`。
- partial renderer 在 `test_techniques` 或 `test_layers` 单独到达时不提前展示章节 4-6。
- partial renderer 在 `test_techniques + test_layers + test_points` 到齐且引用有效时一次性展示章节 4-6。
- partial renderer 在章节 4-6 引用无效时停在已可信章节，不输出错误章节。
- raw JSON streaming 在 `test_points` 到达后才展示章节 4-6，最终仍通过完整 workflow contract。
- Lisa 现有 STRATEGY contract、CASES、New Agents shared regression 不回归。

## 验证计划

- RED：新增 STRATEGY 引用门禁和 partial 分组测试，确认旧实现失败。
- GREEN：实现 validator / partial renderer / prompt 后，新增测试通过。
- 聚焦回归：运行 STRATEGY final、partial、raw streaming 相关测试。
- 共享回归：运行 New Agents 后端共享 regression。
- 提交前：运行 `./scripts/test/test-local.sh new-agents` 和 `./scripts/test/test-local.sh all`；若沙箱限制浏览器或端口，按 playbook 记录环境失败并用非沙箱复跑。
