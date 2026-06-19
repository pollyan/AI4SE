# New Agents Artifact Comments Design

## Current State Gap Analysis

ArtifactPane 已支持人工编辑、历史版本、冲突对比和导出，但 todo 中的“批注”仍未闭环。当前用户如果想记录“这里需要业务确认”或“这个风险要后续跟进”，只能修改 artifact 正文，容易把协作备注和正式产出物混在一起。

候选能力包：

- Artifact 批注 MVP：在 ArtifactPane 工具栏提供批注入口，用户能为当前阶段产物新增、查看、删除批注。该能力形成完整用户动作链，且不改变现有服务端 artifact 保存语义。
- 章节锁定：需要章节解析、编辑保护和模型后续写入约束，适合后续独立切片。
- 逐行接受/拒绝：需要 diff 应用和版本合并语义，风险更高，放到批注之后。

本轮选择 Artifact 批注 MVP。

## User Story

作为 Lisa/Alex 工作区用户，当我审阅右侧产出物时，我可以给当前阶段产物留下批注，之后能看到并删除这些批注，从而把协作备注和正式产出物正文分开。

## Scope

- 批注绑定当前 workflow stage。
- 批注包含 id、stageId、content、createdAt 和 artifactExcerpt。
- 批注保存在前端 workspace store，并随持久化工作区状态保留。
- 切换 workflow、清空历史时清理批注，避免跨工作流污染。
- ArtifactPane 工具栏新增批注入口，打开后可新增、查看、删除当前阶段批注。

## Non-Goals

- 不把批注写入服务端 run snapshot。
- 不做正文选区锚点。
- 不把批注送入模型上下文。
- 不实现评论回复、解决状态或权限。

## Acceptance

1. 给定当前阶段 artifact，用户打开批注面板并输入批注后，批注显示在当前阶段批注列表。
2. 切换阶段后，只展示目标阶段自己的批注。
3. 用户可以删除单条批注。
4. 清空历史或切换 workflow 会清空批注。
5. 现有 artifact 编辑、历史、导出测试不退化。

## Verification

- `npm run test -- --run src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx`
- `npm run lint`
- `npm run build`
- `git diff --check`
