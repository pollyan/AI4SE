# New Agents Artifact Section Move Merge Design

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-ux-professionalization.md`。
- 已读取代码：`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`。
- 当前主工作区状态：`master...origin/master`，仅有两个无关 zip 修改：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`。本切片在独立 worktree `codex/new-agents-artifact-section-move-merge` 中执行。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| Artifact 唯一章节移动自动合并 | todo P1 #7 剩余“移动语义自动合并、完整三方 merge 的更复杂冲突解析” | 用户编辑右侧 artifact 调整章节顺序 -> 保存时遇到服务端新版本 -> 系统发现双方没有改同一章节 -> 一键自动合并服务端改写和用户移动顺序 -> 活动轨迹记录 | 只做按钮或只做纯函数都无法形成用户动作链；必须覆盖冲突卡片入口、合并结果和审计轨迹 | `ArtifactPane.test.tsx` RED/GREEN 测试 |
| 更完整三方 merge | 删除/改写/移动混合、段落级移动、重复标题、跨层级重组 | 复杂冲突 -> 系统更智能合并或解释不能合并 | 范围大，容易误合并，应在移动 MVP 之后继续做 | 后续更多负例与解析测试 |
| 左侧自然对话视觉证据 | todo P1 #5 可读性尾项 | 长回复 -> 左侧可扫描 | 已有 prompt/contract 基线，当前价值低于 Artifact merge | 后续 ChatPane/截图测试 |

排序结论：
1. 选择 Artifact 唯一章节移动自动合并，因为它是当前 Artifact 协作剩余项中最直接的用户痛点：用户已经可以手动合并行/块和非重叠改写，但“只是调整章节顺序”仍会降级为人工冲突处理。
2. 更完整三方 merge 暂不选，因为需要段落级移动、重复标题、跨层级重组等更高风险语义判断。
3. 左侧自然对话视觉证据暂不选，因为它不是当前最高价值缺口。

切片厚度门禁：
- 入口：保存人工编辑后的 Artifact 时，服务端返回 artifact conflict。
- 动作：用户在冲突卡片点击 `自动合并非重叠变更`。
- 处理：系统比较 base/server/draft 的 Markdown 标题章节，确认标题唯一、章节集合不变、同一章节未被双方不同改写，并将安全移动顺序与非冲突章节改写合并。
- 可见结果：编辑草稿更新为自动合并后的 Markdown，保留用户移动后的章节顺序和服务端非冲突改写。
- 状态承接：记录 `artifact_auto_merge_applied` 活动轨迹，继续走现有保存流程，不改变服务端 API。
- 失败反馈：重复标题、章节集合变化、双方移动不同顺序、双方改同一章节时不显示自动合并入口，继续使用现有人工对比处理。
- 证据：`ArtifactPane.test.tsx` 覆盖成功路径和至少一个保守降级负例。
- 结论：通过。该切片形成完整冲突恢复动作链。

## 用户故事

作为正在校准右侧产出物的用户，当我只是把一个 Markdown 章节移动到更合适的位置，而服务端同时更新了另一个章节内容时，我希望系统能识别这是非重叠变更并一键合并，而不是要求我逐行处理整段冲突。

## 目标行为

支持受控的章节移动自动合并：

1. Base、Server、Draft 都必须能解析为 Markdown 标题章节。
2. 所有标题必须唯一。
3. 三方章节标题集合必须一致，不能新增、删除或重命名章节。
4. 允许一方或双方采用同一个新章节顺序；如果双方章节顺序都变化但不同，则不自动合并。
5. 对每个章节内容：
   - 仅 Server 改写：采用 Server 章节内容。
   - 仅 Draft 改写：采用 Draft 章节内容。
   - 双方都未改写：采用 Base 章节内容。
   - 双方都改写且结果不同：不自动合并。
6. 合并后的章节顺序：
   - 如果 Draft 移动了章节，优先采用 Draft 顺序。
   - 否则如果 Server 移动了章节，采用 Server 顺序。
   - 否则该逻辑不产生结果，由现有非重叠章节改写逻辑处理。
7. 合并成功后 summary 使用 `合并轨迹：自动合并服务端与草稿的非重叠章节移动`。

## 非目标

- 不支持重复标题章节移动。
- 不支持段落级移动、列表项移动、跨标题层级重组。
- 不支持章节新增/删除/重命名的自动合并。
- 不改变 `updateRunArtifact` API 或服务端冲突契约。
- 不新增 Lisa/Alex 或 workflow 专属分支。

## 验收条件

1. Given Base 包含三个唯一章节 A/B/C
   And Server 改写 A 但保持章节顺序
   And Draft 将 C 移动到 B 前且不改写 A
   When 保存触发 artifact conflict
   Then 冲突卡片显示 `自动合并非重叠变更`
   And 点击后草稿采用 Draft 的章节顺序，同时保留 Server 对 A 的改写。

2. Given Base/Server/Draft 的唯一章节集合一致
   And Server 与 Draft 都改写同一章节且内容不同
   When 保存触发 artifact conflict
   Then 不显示 `自动合并非重叠变更`。

3. Given Base 中存在重复标题
   When 保存触发 artifact conflict
   Then 不显示 `自动合并非重叠变更`。

4. Given 自动合并成功
   Then store 中新增 `artifact_auto_merge_applied` 活动轨迹，summary 为 `合并轨迹：自动合并服务端与草稿的非重叠章节移动`。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section movement"`
- `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `cd tools/new-agents/frontend && npm run build`
- `git diff --check`
