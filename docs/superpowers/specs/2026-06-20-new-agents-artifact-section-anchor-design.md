# New Agents Artifact 重复标题章节锚点设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/store.ts`、`tools/new-agents/frontend/src/core/types.ts`、`tools/new-agents/frontend/src/services/runSnapshotService.ts`、`tools/new-agents/backend/models.py`、`tools/new-agents/backend/app.py`、`tools/new-agents/backend/run_persistence.py` 及相关测试。
- 子 Agent 事实源：Epicurus 只读审计指出重复标题精确锚点是移动语义自动合并和更复杂冲突解析的前置能力。
- 按需未展开：PDF/DOCX 导出细节，本轮不修改导出链路。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 重复标题精确锚点 | Artifact 协作剩余：重复标题精确锚点、移动语义自动合并前置能力 | 用户打开章节锁定 -> 锁定第二个同名章节 -> 系统只保护被锁定的具体章节 -> 保存/恢复后仍可区分 | 只加字段没有用户价值；必须接到 UI、store、服务端 snapshot 和保存校验 | ArtifactPane/store/runSnapshot/backend 测试 |
| DOCX/PDF 更多高保真导出 | Artifact 导出剩余：更多 Mermaid 类型和 PDF 图片级嵌入 | 用户下载交付物 -> Word/PDF 看到更接近预览的图形 | 已完成 DOCX flowchart SVG，本轮再扩会偏离协作主线 | docx/pdf 导出测试 |

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 重复标题精确锚点 | Todo P1 #7、Epicurus 审计 | 同名章节可分别锁定、保存、恢复，并只阻断对应章节改写 | 章节锁按 `heading` 去重和查找；重复标题无法区分 | 用户在专业文档中常见重复小节，当前锁定容易误伤或漏保护 | 提升协作可信度，为移动语义自动合并铺路 | 跨前后端 schema，但字段可选、兼容旧数据 | 单测和后端 API 测试可覆盖 | 本轮 |
| 更多 Mermaid DOCX/PDF 嵌入 | Todo P1 #7、Zeno 审计 | 更多图表类型作为图形嵌入 | DOCX flowchart SVG 已完成，PDF 多种轻量矢量已完成 | 复杂图仍降级 | 专业交付物继续增强 | 导出复杂度高 | 导出包/XML/PDF 测试 | 下一轮候选 |

排序结论：
1. 选择重复标题精确锚点，因为它解除 Artifact 协作中“同名章节不能可靠锁定”的基础缺口，且是后续移动语义自动合并的前置条件。
2. 更多导出增强暂缓，因为上轮刚完成 DOCX SVG 嵌入，本轮切换到协作可信度能覆盖另一条剩余主线。

切片准入判断：
- 用户可感知动作链：右侧产物 -> 章节锁定 -> 锁定第二个同名章节 -> 编辑第一个同名章节可保存，编辑第二个被阻断 -> 历史 run 恢复后锁仍指向同一章节。
- 相邻缺口合并：本轮合并 UI 锚点、store、snapshot service、后端持久化和初始化迁移；不做移动自动合并。
- Superpowers 成本合理性：跨层状态一致性影响人工校准可信度，值得完整 TDD/验证。
- 过薄风险检查：不是单字段；完成后用户能准确锁定同名章节。
- 能力增量句：完成后，用户现在可以在含重复标题的 Artifact 中锁定具体某一个章节，而不会误锁其他同名章节。

切片厚度门禁：
- 入口：ArtifactPane 的 `章节锁定` 面板。
- 动作：用户锁定同名章节中的某一项，并编辑产出物。
- 处理：系统为章节生成稳定 `sectionAnchor`，保存和恢复章节锁时携带该锚点，校验时优先按锚点匹配。
- 可见结果：同名章节各自有独立锁定状态；只改未锁定同名章节不被误阻断，改锁定章节会被阻断。
- 状态承接：`artifactSectionLocks`、run snapshot、collaboration API 都保留 `sectionAnchor`；旧锁没有锚点时继续按 heading 兼容。
- 失败反馈：锚点缺失或不匹配时回退到现有 heading/content 保护，不静默放开锁。
- 证据：前端 ArtifactPane/store/service 测试，后端 persistence/API/init_db 测试，lint/build。
- 结论：通过。

## 用户故事

作为正在校准右侧产出物的用户，当文档里出现多个同名章节时，我可以锁定其中一个具体章节。后续我或模型修改其他同名章节时，系统不会误判；如果修改的是被锁定的具体章节，保存会被阻断并提示先解锁。

## 验收条件

1. Given Artifact 中有两个 `## 验收口径`
   When 用户锁定第二个 `验收口径`
   Then `artifactSectionLocks` 中保存 `sectionAnchor`，UI 只显示第二个同名章节已锁定。

2. Given 第二个同名章节已锁定
   When 用户只修改第一个同名章节并保存
   Then 保存成功，当前产物更新。

3. Given 第二个同名章节已锁定
   When 用户修改第二个同名章节并保存
   Then 保存被阻断，当前产物、阶段产物和历史不被污染。

4. Given 章节锁同步到服务端
   When 恢复 run snapshot
   Then `sectionAnchor` 保留，前端仍能区分同名章节。

## 边界

- 不做完整三方 merge 引擎。
- 不做章节移动语义自动合并；本轮只把 section identity 做实。
- 不新增 Lisa/Alex/workflow 专属分支。
- 旧数据没有 `sectionAnchor` 时保持兼容，不强制迁移所有历史锁。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts src/services/__tests__/runSnapshotService.test.ts`
- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_api.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py`
- `cd tools/new-agents/frontend && npm run lint`
- `cd tools/new-agents/frontend && npm run build`
- `git diff --check`
