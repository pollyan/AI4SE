# New Agents Artifact Conflict Merge Audit Design

## Current State Gap Analysis

Artifact 已支持人工编辑、服务端版本冲突提示、冲突版本对比，以及对草稿新增行的 `采纳` / `丢弃`。但这些合并决策只体现在当前编辑草稿里，用户稍后打开历史面板时，看不到冲突合并过程中做过哪些人工判断。

候选能力包：

- 行级合并轨迹：复用现有 Artifact 活动轨迹，在用户采纳或丢弃冲突草稿行时记录本地审计事件。
- 完整三方 merge 模型：记录 base/server/draft 三方、块级操作、保存后服务端审计事件，复杂度更高。
- 独立合并会话 UI：新增冲突合并时间线和会话状态，当前切片过重。

本轮选择行级合并轨迹。

## User Story

作为 New Agents 用户，当我在保存冲突里采纳或丢弃草稿行后，可以在 Artifact 历史面板的活动轨迹里看到这次合并决策，便于回溯人工校准过程。

## Scope

- Store 新增本地 `addArtifactAuditEvent` action，复用既有 `ArtifactAuditEvent` 数据结构。
- `采纳到草稿` 写入 `artifact_merge_line_accepted` 活动事件。
- `丢弃此行` 写入 `artifact_merge_line_discarded` 活动事件。
- 活动摘要使用 `合并轨迹：采纳/丢弃草稿行「...」` 格式，长行做截断。
- 历史版本面板继续复用现有 `活动轨迹` 区块，无新增顶栏入口。

## Non-Goals

- 不实现完整三方 merge 算法。
- 不持久化本地合并事件到服务端审计表。
- 不新增块级接受/拒绝。
- 不改变现有冲突保存 API。

## Acceptance

1. 采纳冲突草稿行后，历史面板活动轨迹显示对应合并摘要。
2. 丢弃冲突草稿行后，store 中记录对应合并摘要。
3. 非当前 workflow stage 的本地审计事件不会写入。
4. 既有 Artifact 编辑、冲突、历史、批注和导出测试不退化。

## Verification

- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts`
- `npm run lint`
- `npm run build`
- `git diff --check`
