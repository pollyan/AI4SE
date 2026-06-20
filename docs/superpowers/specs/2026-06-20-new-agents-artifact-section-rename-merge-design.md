# New Agents Artifact 章节重命名自动合并设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`、近期 Artifact section add/delete / move / rewrite specs 和 plans。
- 按需未展开：后端 artifact update API、workflow prompt、DOCX/PDF 导出。当前切片只扩展 ArtifactPane 的保存冲突自动合并，不修改 runtime、SSE、后端接口或导出链路。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| A. 保守章节重命名自动合并 | P1.7 剩余“章节重命名”；当前 add/delete helper 明确把重命名降级人工 | 用户编辑右侧产物 -> 只改章节标题 -> 保存遇到服务端改写其他章节 -> 点击 `自动合并非重叠变更` -> 草稿保留新标题和服务端非冲突改写 -> 活动轨迹可追踪 | 只做 heading 检测没有用户价值；必须接入冲突卡片、合并草稿和轨迹才形成完整动作链 | `ArtifactPane.test.tsx` 覆盖 draft rename、server rename、双方同向 rename 和负例 |
| B. 段落级移动自动合并 | P1.7 剩余“段落级移动” | 用户移动段落 -> 系统保留另一侧非冲突改写 | 段落锚点、重复段落和列表层级歧义更高，需单独设计 | 后续需更细解析测试 |
| C. PDF Mermaid 图片级嵌入 | P1.7 剩余 PDF 图片级高保真 | 用户导出 PDF -> 图表以更高保真图片呈现 | 与冲突协作链路不同，应另起导出切片 | PDF 结构/渲染验证 |

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. 保守章节重命名自动合并 | todo 第四十三块剩余、当前 `ArtifactPane` helpers | 安全 rename 可自动合并 | 重命名被 section add/delete veto，必须人工处理 | 只改标题且正文不变的常见校准不能自动合并 | 降低人工校准冲突成本，补齐章节集合变化三方 merge 的最后安全子类 | 中等，必须避免把新增+删除误判为 rename | 组件测试可构造 409 冲突 | 本轮 |
| B. 段落级移动 | todo 剩余 | 段落移动可自动合并 | 当前只支持章节级移动 | 细粒度重排仍需手工处理 | 中 | 高 | 可测但误合并风险高 | 下一轮候选 |
| C. PDF 图片级嵌入 | todo 剩余 | PDF 图表更高保真 | 已有 PDF 矢量投影和 DOCX SVG 嵌入 | PDF 仍非图片级嵌入 | 中 | 中高 | 需要 PDF 对象/截图验证 | 下一轮候选 |

排序结论：
1. 选择 A，因为它紧接已完成的章节增删自动合并，能消化同一用户冲突处理动作链下的明确剩余项。
2. B 暂不选，因为段落级移动需要更复杂锚点和重复内容处理。
3. C 暂不选，因为导出高保真是另一条用户动作链。

切片厚度门禁：
- 入口：保存冲突卡片中的 `自动合并非重叠变更`。
- 动作：用户点击自动合并。
- 系统处理：三方 Markdown 章节解析，识别“旧 heading -> 新 heading”且正文不变的 rename。
- 可见结果：编辑草稿更新为合并后 Markdown。
- 状态承接：继续走现有保存流程，写入 `artifact_auto_merge_applied` 活动轨迹。
- 失败反馈：不确定 rename 不显示自动合并入口，保留对比服务端和手工合并能力。
- 证据：RED/GREEN 组件测试、完整 ArtifactPane 测试、lint、build、diff check。

## 用户故事

作为 Lisa / Alex 的工作流用户，当我只把右侧产出物中的章节标题改得更准确，而服务端同时更新了其他章节时，我希望系统能识别这是安全的章节重命名并自动合并，避免我手工逐行处理标题改名和服务端内容更新。

## 范围

进入本轮：
- draft 侧重命名：用户把 `## 验收口径` 改为 `## 质量口径`，章节正文不变；服务端改写其他章节。
- server 侧重命名：服务端把某章节标题改名，draft 改写其他章节。
- 双方同向重命名：双方把同一个旧标题改为同一个新标题，另一侧还有非冲突改写。
- 自动合并 summary：`合并轨迹：自动合并服务端与草稿的非重叠章节重命名`。

不进入本轮：
- 不自动合并正文同时变化的 rename。
- 不自动合并双方把同一旧标题重命名为不同新标题。
- 不自动合并一方重命名、另一方改写同一旧章节正文。
- 不自动合并一方重命名、另一方同时移动并改写其他章节。
- 不处理重复标题、跨层级重组、段落级移动、语义相似度判断。
- 不改变服务端 API、artifact history schema、workflow runtime 或导出能力。

## 安全识别规则

- 三方都必须能被 `parseMarkdownSectionsForAutoMerge` 解析，且无重复 heading。
- preamble 必须一致。
- rename 只在某一侧相对 base “删除 1 个旧 heading、新增 1 个新 heading”时考虑。
- 新旧章节除 heading 行外的正文行必须完全一致。
- 如果另一侧仍保留旧 heading，它不能改写该旧章节正文。
- 如果另一侧仍保留旧 heading，它必须保持 base 章节顺序；章节重命名不与章节移动混合自动合并。
- 如果双方都 rename 同一个旧 heading，目标新 heading 必须一致，且正文必须一致。
- 如果任一侧还有其他章节新增/删除，与本轮 rename helper 不混合处理，交给现有 add/delete 或人工处理。

## 验收条件

1. draft rename + server 改写其他章节时显示 `自动合并非重叠变更`，点击后保留 draft 新标题和 server 改写。
2. server rename + draft 改写其他章节时显示 `自动合并非重叠变更`，点击后保留 server 新标题和 draft 改写。
3. 双方同向 rename 同一章节时可以合并。
4. 双方 rename 到不同标题、rename 同时改写正文、或另一侧改写被 rename 的旧章节时不显示自动合并入口。
5. 现有 section add/delete veto 仍有效，不允许 unsafe 场景落到 line-level insertion fallback。

## 验证计划

- RED：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section rename"`
- GREEN：同命令通过。
- 回归：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`
- 静态检查：`npm run lint`
- 构建：`npm run build`
- 空白检查：`git diff --check`
