# New Agents Artifact 段落级移动自动合并设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/todos/new-agents-ux-professionalization.md`、近期 Artifact 章节改写/移动/增删/重命名记录、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`。
- 当前 Artifact 保存冲突已经支持行级插入/安全删除、章节级非重叠改写、章节移动、章节增删和章节重命名自动合并。
- 当前 `buildAutoMergedSectionRewriteResult` 能处理“一侧移动段落所在章节、另一侧改写其他章节”的场景，因为双方修改落在不同章节。
- 当前缺口是：同一 Markdown 章节内，一侧只移动一个段落块，另一侧改写同章节内另一个段落块。章节级 helper 会把它判定为双方修改同一章节并降级人工处理。

能力包聚合：

| 能力包 | 原始缺口 | 用户动作链 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| A. 同章节唯一段落移动自动合并 | P1.7 剩余“段落级移动” | 用户在右侧产物中调整同一章节内段落顺序；服务端同时更新同章节另一段；用户点击自动合并 | 只检测移动没有用户价值，必须接入冲突卡片、编辑草稿和活动轨迹 | `ArtifactPane.test.tsx` 覆盖正例、负例和 summary |
| B. 跨章节段落移动 | 同属段落级移动 | 用户把段落从一个章节挪到另一个章节 | 涉及章节语义变化和上下文归属，误合并风险高 | 后续单独设计 |
| C. 列表项/表格行移动 | 更细粒度重排 | 用户调整列表或表格顺序 | 需要结构化 Markdown AST 或更强锚点，不适合混在本轮 | 后续单独设计 |

排序结论：
1. 选择 A，因为它补齐当前章节级三方 merge 的最后一个高频窄缺口。
2. B/C 暂不做，避免把语义迁移或结构化块重排误判为普通段落移动。

## 用户故事

作为 Lisa / Alex 的工作流用户，当我把右侧产出物同一章节里的一个段落调整到更合理的位置，而系统同时更新了同章节里的另一个段落时，我希望系统能识别这两个操作不冲突，并自动合并，而不是要求我逐行处理整个章节冲突。

## 范围

进入本轮：
- 同一章节内，draft 移动一个唯一段落块，server 改写同章节内另一个段落块。
- 同一章节内，server 移动一个唯一段落块，draft 改写同章节内另一个段落块。
- 双方把同一个唯一段落块移动到同一个目标位置，且不混入该章节内的段落改写。
- 自动合并 summary：`合并轨迹：自动合并服务端与草稿的非重叠段落移动`。

不进入本轮：
- 跨章节段落移动。
- 重复段落块。
- 移动段落本身被另一侧改写。
- 双方移动不同段落，或同一段落移动到不同位置。
- 列表项、表格行、代码块、Mermaid fenced block、`ai4se-visual` fenced block 内部重排。
- 分裂或合并段落块，例如一侧把一个段落拆成两个段落。
- 后端 API、artifact history schema、workflow runtime、导出能力变更。

## 安全识别规则

- 三方都必须能被 `parseMarkdownSectionsForAutoMerge` 解析，且章节标题唯一。
- preamble、章节数量、章节标题和章节顺序必须一致；本轮不混合章节级移动、增删或重命名。
- 段落块按空行分隔；一个段落块是连续非空行。
- 移动侧必须只在一个章节内改变段落块顺序，且所有段落块内容与 base 完全一致。
- 非移动侧在该章节内必须保持 base 段落顺序和段落数量；它可以改写非移动段落，但不能改写被移动段落。
- 如果双方都移动，必须移动同一个 base 段落块并得到同一个目标段落顺序；同章节内再混入段落改写时仍交给人工处理。
- 如果段落块重复、段落拆分/合并、代码/可视化 fenced block 涉及移动，返回 `null`，继续人工冲突处理。
- 章节级非重叠改写自动合并前必须先识别移动语义：安全段落移动交给 paragraph movement helper；跨章节移动、列表项/表格行/fenced block 重排不得被章节级 helper 当作普通章节改写自动合并。

## 验收条件

1. draft 移动同章节唯一段落、server 改写同章节另一个段落时显示 `自动合并非重叠变更`，点击后保留 draft 段落顺序和 server 段落改写。
2. server 移动同章节唯一段落、draft 改写同章节另一个段落时显示 `自动合并非重叠变更`，点击后保留 server 段落顺序和 draft 段落改写。
3. 双方同向移动同一个段落时可以合并。
4. 重复段落、移动段落被另一侧改写、双方移动不同段落、跨章节移动、列表项/表格行/fenced block 移动不显示自动合并入口，即使另一侧只改写其他章节也不能通过章节级 helper 绕过。
5. 现有章节改写、移动、增删、重命名和 section set veto 行为不回退。

## 验证计划

- RED：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "paragraph movement"`
- GREEN：同命令通过。
- 回归：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`
- 静态检查：`npm run lint`
- 构建：`npm run build`
- 空白检查：`git diff --check`
