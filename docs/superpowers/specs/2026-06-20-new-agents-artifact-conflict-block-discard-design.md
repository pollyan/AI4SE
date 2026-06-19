# New Agents Artifact Conflict Block Discard Design

## Current State Gap Analysis

Artifact 冲突对比已经支持对草稿新增行逐行 `采纳` / `丢弃`，并记录行级合并轨迹。但当用户一次补充了多行连续内容时，需要逐行点击，效率低，也不容易把这些连续行理解为同一个人工变更块。

候选能力包：

- 连续新增块丢弃：识别 conflict diff 中连续的 `added` 行，在块起点提供 `丢弃块` 操作，并记录块级合并轨迹。
- 连续新增块采纳：将多行一次性附加到服务端版本，仍需处理插入位置和重复行语义。
- 完整三方/块级 merge：支持 base/server/draft 块语义、修改块、删除块和服务端持久化，复杂度更高。

本轮选择连续新增块丢弃。

## User Story

作为 New Agents 用户，当保存冲突中出现多行连续草稿新增内容时，可以一次丢弃整个变更块，而不是逐行操作，并能在活动轨迹里看到这次块级合并决策。

## Scope

- 从现有 `conflictDraftDiff` 派生连续非空 `added` block。
- block 长度大于 1 时，在第一行旁显示 `丢弃块` 操作。
- 点击后从编辑草稿中逐项移除该 block 的所有行。
- 记录 `artifact_merge_block_discarded` 本地活动轨迹。
- 保留现有逐行 `采纳` / `丢弃` 操作。

## Non-Goals

- 不实现块级采纳。
- 不实现完整三方 merge。
- 不处理修改块/删除块的语义合并。
- 不持久化本地合并轨迹到服务端审计表。

## Acceptance

1. 连续两行以上草稿新增行显示 `丢弃块` 操作。
2. 点击 `丢弃块` 后，整个新增块从编辑草稿中移除。
3. Store 中记录 `artifact_merge_block_discarded` 活动事件。
4. 既有逐行采纳/丢弃、冲突对比、历史、批注和导出测试不退化。

## Verification

- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts`
- `npm run lint`
- `npm run build`
- `git diff --check`
