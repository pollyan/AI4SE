# New Agents Artifact Conflict Block Accept Design

## Current State Gap Analysis

Artifact 冲突对比已经支持连续新增块的 `丢弃块`，也支持单行 `采纳`。但当用户连续补充了多行有效内容时，仍需要逐行采纳，容易遗漏，也无法在活动轨迹里体现“这个块整体被采纳”的决策。

候选能力包：

- 连续新增块采纳：识别已有 added block，在块起点提供 `采纳块`，以服务端当前版本为基准追加该块，并记录块级轨迹。
- 位置保持型块采纳：尝试按原草稿上下文恢复插入位置，需要更复杂的三方上下文。
- 完整三方/修改块合并：处理 base/server/draft 修改块、删除块和冲突标记，复杂度更高。

本轮选择连续新增块采纳。

## User Story

作为 New Agents 用户，当保存冲突中出现多行连续草稿新增内容，并且这些内容仍然有效时，可以一次采纳整个变更块，而不是逐行采纳。

## Scope

- 复用 `conflictDraftAddedBlocks` 识别出的连续新增块。
- 在块起始行显示 `采纳块` 操作。
- 点击后以服务端版本为基准，把该块中尚未出现在服务端的行追加到编辑草稿。
- 写入 `artifact_merge_block_accepted` 活动轨迹。
- 保留现有逐行 `采纳` / `丢弃` 与 `丢弃块` 操作。

## Non-Goals

- 不保留原草稿插入位置。
- 不处理修改块/删除块语义合并。
- 不实现完整三方 merge。
- 不持久化本地合并轨迹到服务端审计表。

## Acceptance

1. 连续两行以上草稿新增行显示 `采纳块` 操作。
2. 点击 `采纳块` 后，编辑草稿基于服务端版本并包含整个新增块。
3. Store 中记录 `artifact_merge_block_accepted` 活动事件。
4. 既有逐行采纳/丢弃、块级丢弃、冲突对比、历史和导出测试不退化。

## Verification

- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts`
- `npm run lint`
- `npm run build`
- `git diff --check`
