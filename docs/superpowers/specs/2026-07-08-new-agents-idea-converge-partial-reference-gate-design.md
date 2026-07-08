# New Agents IDEA DIVERGE / CONVERGE Partial 引用门禁设计

## 目标

让 `IDEA_BRAINSTORM/DIVERGE` 和 `IDEA_BRAINSTORM/CONVERGE` 的流式 partial artifact preview 与最终 Pydantic validator 使用同一批关键引用不变量，避免右侧预览先展示“看似有效”的章节，最终却因已知跨引用错误失败。

本轮不改变正式 workflow 主链路、不降低 final schema 严格性、不新增 Agent 专属 runtime / API / store / renderer。它只增强共享 deterministic partial renderer 的拒绝边界。

## 当前事实

- `IdeaDivergeArtifactData` final validator 已拒绝重复 `idea_id`、重复 `source_id`、重复 `record_id`、landscape 未知 idea 引用、source 未知 idea 引用和无 checked stage gate。
- `IdeaConvergeArtifactData` final validator 已拒绝重复 idea、重复 rank、错误 ICE 分、未知 recommended idea、decision item 未知 idea、experiment 未知 idea、merge path 未知 idea、推荐不一致和无 checked stage gate。
- 当前 partial renderer 只做局部 Pydantic 校验。DIVERGE 的 `idea_sources` 未知引用会被预览；CONVERGE 的决策矩阵、validation experiments、merge paths 也可能在引用未知 idea 时被预览。
- 这些 false preview 不会持久化为最终 artifact，但会削弱“右侧产物失败显式、过程可信”的用户体验。

## 自问自答 Brainstorming 记录

**Explore Project Context**

结构化失败治理主线正在减少模型维护跨字段一致性的压力。第 4 轮已把 DEFINE 的证据关系改为稳定 ID 引用，并让 partial renderer 在未知引用时停止预览对应章节。本轮把同样原则扩展到 DIVERGE / CONVERGE，但只处理 partial preview 和 final validator 已有的不变量对齐。

**Visual Companion Decision**

本轮不涉及视觉设计。Mermaid quadrant / mindmap 的稳定性留到视觉专项。

**Clarifying Questions**

- 用户是谁：正在与 Alex 交互并看右侧流式产物的产品经理，以及后续依赖 artifact 的工程实现者。
- 成功状态是什么：当模型 partial JSON 已经包含未知 idea 引用或错误 ICE score 时，右侧不会展示对应错误章节。
- 失败怎么表现：partial renderer 返回上一段可信章节或 `None`；最终完整输出仍由 final validator 显式报错。
- 不做什么：不让模型少输出字段，不改正式 workflow 阶段，不接入 tool calls，不做 CASES/STRATEGY。

**Approaches**

1. 推荐方案：抽取 final validator 中的引用校验 helper，让 final 和 partial 共用关键不变量。优点是行为一致、改动小、测试直接。
2. 只在 partial renderer 里复制校验逻辑。优点是快；缺点是未来 final/partial 容易漂移。
3. 让 partial renderer 等完整 artifact_data 才渲染。优点是最安全；缺点是破坏当前流式预览体验。

采用方案 1。DIVERGE 对 landscape/source 引用逐段校验；CONVERGE 对初始 decision matrix + ICE evaluations 做完整启动门禁，对 experiments / merge paths 做逐段引用门禁。

## 行为设计

DIVERGE partial：

- 只要 `divergence_method` 合法，就继续显示方法说明。
- `idea_landscape` + `idea_cards` 阶段必须通过 duplicate idea 和 landscape idea 引用校验，否则只显示方法说明。
- `idea_sources` 阶段必须通过 source id 去重和 source idea 引用校验，否则停在创意卡片库。

CONVERGE partial：

- `decision_matrix` + `ice_evaluations` 是最小启动单元。
- 启动单元必须通过 duplicate idea、duplicate rank、ICE score、recommended idea、decision item idea、推荐一致性校验，否则 partial 返回 `None`。
- `validation_experiments` 必须只引用已知 ICE idea，否则停在敏感性分析。
- `merge_paths` 必须只引用已知 ICE idea，否则停在验证实验。

## 验收

1. RED 测试先证明当前 DIVERGE partial 会展示未知 `idea_sources.idea_ids` 的来源章节。
2. RED 测试先证明当前 CONVERGE partial 会展示未知 recommended idea、错误 ICE score、未知 experiment idea 或未知 merge path idea。
3. GREEN 后，上述错误不再预览错误章节；最终 validators 仍保持原错误行为。
4. 聚焦回归覆盖 IDEA DIVERGE / CONVERGE renderer、runtime structured output instruction 和 raw JSON stream partial 路径。
